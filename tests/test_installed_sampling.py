"""Actual source/data-wheel sampling through CLI, Python and loopback GUI."""

import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from experiments.catalogue.storage import dump
from experiments.mmtt_sampling.run import run as direct_run
from experiments.shared_services.store import opened
from scripts import build_sdk


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 SDK"
)
class InstalledSampling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="installed-sampling-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name).resolve()
        cls.env = {**os.environ, "UV_CACHE_DIR": str(cls.base / "cache")}
        cls.env.pop("PYTHONPATH", None)
        receipt = build_sdk.build(cls.base / "build", allow_dirty=True, build_label="sampling-test")
        cls.environment = cls.base / "sdk"
        for command in (
            ["uv", "venv", "--offline", "--python", sys.executable, str(cls.environment)],
            [
                "uv",
                "pip",
                "install",
                "--offline",
                "--no-deps",
                "--link-mode=copy",
                "--python",
                str(cls.environment / "bin/python"),
                receipt["wheel"],
            ],
        ):
            subprocess.run(command, env=cls.env, capture_output=True, check=True)
        cls.cli = cls.environment / "bin/opent1d-lab"

    def setUp(self):
        self.root = self.base / self._testMethodName
        self.root.mkdir()

    def call(self, *args, expected=0):
        result = subprocess.run(
            [str(self.cli), *map(str, args)],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def prepared(self, case):
        inputs = self.call(
            "example",
            "--task",
            "mmtt-sampling",
            "--case",
            case,
            "--output",
            self.root / (case + "-inputs"),
        )["inputs"]
        settings = json.loads(Path(inputs["settings.json"]).read_bytes())
        self.assertEqual(settings["uncertainty"]["draws"], 128)
        settings["uncertainty"]["draws"] = (
            32  # Explicit small test plan; supplied control stays 128.
        )
        dump(Path(inputs["settings.json"]), settings)
        project = self.root / (case + "-project")
        self.call("create", "--project", project, "--name", "Invented sampling study")
        flags = ["--task", "mmtt-sampling"]
        for option, field in (
            ("package", "package.json"),
            ("csv", "observations.csv"),
            ("settings", "settings.json"),
            ("design", "design.json"),
            ("development-import", "development"),
        ):
            flags += ["--" + option, inputs[field]]
        self.assertFalse(self.call("validate", *flags)["estimation_performed"])
        plan = self.call("freeze", "--project", project, *flags)["plan"]
        return project, plan, inputs

    def test_all_controls_native_parity_retry_and_incomplete_reading(self):
        for case in ("information-loss", "constant", "incomplete", "steep-response"):
            with self.subTest(case=case):
                project, plan, _ = self.prepared(case)
                self.assertTrue(
                    self.call("check", "--project", project, "--plan", plan)["runtimes_ready"]
                )
                expected = 0 if case in {"information-loss", "constant"} else 1
                result = self.call("run", "--project", project, "--plan", plan, expected=expected)
                self.assertEqual(len(result["result"]["slot_statuses"]), 60)
                self.assertEqual(len(result["result"]["report_sha256"]), 10)
                with opened(project) as saved:
                    frozen = saved.plans[plan][1] / "input"
                    archive = saved.finishes[result["attempt"]][1] / "native"
                    direct = self.root / (case + "-direct")
                    report = direct_run(frozen, direct)
                    for name in result["result"]["report_sha256"]:
                        self.assertEqual(
                            (archive / name).read_bytes(), (direct / name).read_bytes()
                        )
                target = self.root / (case + "-reader")
                flags = [
                    "reconstruct",
                    "--project",
                    project,
                    "--attempt",
                    result["attempt"],
                    "--output",
                    target,
                ]
                if expected:
                    self.call(*flags, expected=2)
                    flags += ["--allow-failed"]
                rebuilt = self.call(*flags)
                self.assertEqual(rebuilt["report_sha256"], result["result"]["report_sha256"])
                self.assertEqual(report["coverage"]["planned_draw_pairs"], 60 * 32)
                if case == "information-loss":
                    cell = report["comparisons"]["evaluation"]["three-times"]["nominal"]
                    self.assertEqual(cell["directions"]["direction_reversal"], 3)
                    retry = self.call(
                        "run", "--project", project, "--plan", plan, "--retry-of", result["attempt"]
                    )
                    self.assertNotEqual(retry["attempt"], result["attempt"])
                if case == "constant":
                    for cell in report["comparisons"]["evaluation"]["three-times"].values():
                        self.assertAlmostEqual(cell["paired_changes"]["bias_pmol"], 0, places=7)

    def test_python_api_cancel_retains_owned_attempt_and_retry(self):
        code = f"""
import json, subprocess, sys, threading, time
from pathlib import Path
import opent1d_lab as lab
root=Path({str(self.root)!r})
inputs=lab.example('mmtt-sampling', root/'inputs', case='information-loss')['inputs']
project=lab.create_project(root/'project', 'Invented cancellation')
assert lab.validate('mmtt-sampling', inputs)['valid']
plan=project.freeze('mmtt-sampling', inputs)['plan']
cancel=threading.Event()
observed=threading.Event()
def stop():
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        for path in (root/'project/work').glob('*/native/execution.json'):
            try:
                state=json.loads(path.read_bytes())
            except (OSError,ValueError):
                continue
            if 'analysis' in state.get('schedules',{{}}).values():
                observed.set(); cancel.set(); return
        time.sleep(.005)
watcher=threading.Thread(target=stop)
unrelated=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
try:
    watcher.start()
    result=project.run(plan,cancel=cancel,timeout=60)
    watcher.join(timeout=35)
    assert observed.is_set(), 'Actual native analysis was never observed'
    assert not watcher.is_alive()
    assert unrelated.poll() is None
    assert result['receipt']['remaining_owned_processes']==[]
    assert result['result']['execution_status']=='interrupted'
    assert len(result['result']['slot_statuses'])==60
    assert result['result']['completeness']=='incomplete'
    if result['result']['payload']=='native':
        project.reconstruct(result['attempt'],root/'interrupted-reader',allow_failed=True)
    retry=project.run(plan,retry_of=result['attempt'],timeout=120)
    assert retry['result']['completeness']=='complete'
    assert len(project.info()['attempts'])==2
    print(json.dumps({{'observed_analysis':True,'payload':result['result']['payload']}}))
finally:
    cancel.set()
    watcher.join(timeout=35)
    unrelated.terminate(); unrelated.wait(timeout=5)
"""
        result = subprocess.run(
            [str(self.environment / "bin/python"), "-I", "-c", code],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["observed_analysis"])

    def test_gui_sampling_child_reports_restart_and_relocation(self):
        workspace = self.root / "workspace"
        processes = []

        def launch():
            logfile = (self.root / ("server-" + str(len(processes)) + ".log")).open("w+")
            process = subprocess.Popen(
                [str(self.cli), "gui", "--workspace", str(workspace)],
                cwd=self.root,
                env=self.env,
                stdout=logfile,
                stderr=logfile,
            )
            processes.append((process, logfile))
            deadline = time.monotonic() + 20
            match = None
            while time.monotonic() < deadline:
                logfile.seek(0)
                match = re.search(r"http://127\.0\.0\.1:(\d+)", logfile.read())
                if match or process.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertIsNotNone(match)
            return int(match[1])

        port, token = launch(), None

        def request(route, body=None, expected=200):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
            headers = {"X-OpenT1D-Token": token} if token else {}
            if body is not None:
                headers.update(
                    Origin=f"http://127.0.0.1:{port}", **{"Content-Type": "application/json"}
                )
            try:
                connection.request(
                    "GET" if body is None else "POST",
                    route,
                    None if body is None else json.dumps(body),
                    headers,
                )
                response = connection.getresponse()
                raw = response.read()
                self.assertEqual(response.status, expected, raw)
                return raw, dict(response.getheaders())
            finally:
                connection.close()

        def action(operation, arguments, project=None):
            raw, _ = request(
                "/api/actions",
                {
                    "request_id": uuid.uuid4().hex,
                    "operation": operation,
                    "project": project,
                    "arguments": arguments,
                },
                202,
            )
            job = json.loads(raw)
            deadline = time.monotonic() + 120
            while job["status"] == "running" and time.monotonic() < deadline:
                time.sleep(0.05)
                job = json.loads(request("/api/jobs/" + job["id"])[0])
            self.assertEqual(job["status"], "done", job)
            return job["result"]

        try:
            token = re.search(rb'name="opent1d-token" content="([a-f0-9]{64})"', request("/")[0])[
                1
            ].decode()
            handle = action("create", {"name": "Invented GUI sampling"})["project"]
            draft = action("prepare", {"task": "mmtt-sampling", "case": "information-loss"}, handle)
            plan = action(
                "freeze",
                {
                    "draft": draft["id"],
                    "revision": draft["revision"],
                    "parent": None,
                    "name": "Sampling control",
                },
                handle,
            )["plan"]
            self.assertTrue(action("check", {"plan": plan}, handle)["runtimes_ready"])
            result = action("run", {"plan": plan, "retry_of": None}, handle)
            self.assertEqual(result["result"]["completeness"], "complete")
            report = action("verify", {"attempt": result["attempt"], "allow_failed": False}, handle)
            identity = report["report"]
            self.assertEqual(len(report["report_sha256"]), 10)
            for name in report["report_sha256"]:
                raw, headers = request(f"/api/reports/{identity}/{name}")
                self.assertIn('filename="report.', headers["Content-Disposition"])
                self.assertEqual(raw, (Path(result["evidence"]) / "native" / name).read_bytes())
            info = json.loads(request("/api/state")[0])
            project_path = next(p["path"] for p in info["projects"] if p["id"] == handle)
            cli_info = self.call("info", "--project", project_path)
            self.assertEqual(cli_info["plans"][0]["id"], plan)
            self.assertEqual(cli_info["attempts"][0]["id"], result["attempt"])
            request(f"/api/reports/{identity}/studies/../report.md", expected=404)
            request(f"/api/reports/{identity}/studies/unknown/report.md", expected=409)
            child = workspace / "reports" / identity / "studies/full/report.md"
            child.write_bytes(child.read_bytes() + b"changed")
            request(f"/api/reports/{identity}/report.md", expected=409)
            request(f"/api/reports/{identity}/studies/full/report.md", expected=409)
            moved = self.root / "moved"
            moved_handle = action("relocate", {"output": str(moved)}, handle)["project"]
            request("/api/shutdown", {}, 202)
            processes[-1][0].wait(timeout=15)
            hidden = Path(project_path).with_name("original-unavailable")
            Path(project_path).rename(hidden)
            port, token = launch(), None
            token = re.search(rb'name="opent1d-token" content="([a-f0-9]{64})"', request("/")[0])[
                1
            ].decode()
            action("refresh", {}, moved_handle)
            rebuilt = action(
                "verify", {"attempt": result["attempt"], "allow_failed": False}, moved_handle
            )
            self.assertEqual(rebuilt["report_sha256"], report["report_sha256"])
        finally:
            for process, logfile in processes:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                logfile.close()


if __name__ == "__main__":
    unittest.main()
