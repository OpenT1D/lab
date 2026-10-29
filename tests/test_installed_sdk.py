"""Noneditable wheel use outside checkout, retained readers and adverse artifacts."""

import hashlib
import http.client
import importlib.util
import json
import marshal
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import digest, encoded
from experiments.gui.ownership import Ownership
from experiments.shared_services.store import opened
from scripts import build_sdk
from scripts.build_windows_installer import source_inventory

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12),
    "Installed SDK currently selects POSIX CPython3.12",
)
class InstalledSDK(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="opent1d-installed-sdk-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name).resolve()
        cls.environ = {**os.environ, "UV_CACHE_DIR": str(cls.base / "cache")}
        cls.environ.pop("PYTHONPATH", None)
        cls.candidates = {}
        for label in ("a", "b"):
            receipt = build_sdk.build(
                cls.base / ("build-" + label), allow_dirty=True, build_label=label
            )
            environment = cls.base / ("environment-" + label)
            subprocess.run(
                ["uv", "venv", "--offline", "--python", sys.executable, str(environment)],
                env=cls.environ,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--offline",
                    "--no-deps",
                    "--link-mode=copy",
                    "--python",
                    str(environment / "bin/python"),
                    receipt["wheel"],
                ],
                env=cls.environ,
                capture_output=True,
                check=True,
            )
            cls.candidates[label] = environment

    def setUp(self):
        self.root = self.base / self._testMethodName
        self.root.mkdir()
        self.poison = self.root / "poison"
        self.poison.mkdir()
        self.marker = self.root / "unexpected-execution"
        for name in ("sitecustomize.py", "usercustomize.py"):
            (self.poison / name).write_text(
                f"from pathlib import Path\nPath({str(self.marker)!r}).touch()\n"
            )
        (self.poison / "experiments").mkdir()
        (self.poison / "experiments/__init__.py").write_text(
            (self.poison / "sitecustomize.py").read_text()
        )
        for name in ("uv", "git", "file", "uname"):
            (self.poison / name).write_text(f"#!/bin/sh\ntouch '{self.marker}'\nexit 9\n")
            (self.poison / name).chmod(0o755)
        self.env = {
            **self.environ,
            "PYTHONPATH": str(self.poison),
            "PATH": str(self.poison) + os.pathsep + self.environ["PATH"],
        }

    def call(self, *args, candidate="a", expected=0):
        command = self.candidates[candidate] / "bin/opent1d-lab"
        result = subprocess.run(
            [str(command), *map(str, args)],
            cwd=self.poison,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())
        return json.loads(result.stdout)

    def prepared(self, *, case="complete", suffix=""):
        inputs = self.call(
            "example",
            "--task",
            "mmtt-sensitivity",
            "--case",
            case,
            "--output",
            self.root / ("inputs" + suffix),
        )["inputs"]
        project = self.root / ("project" + suffix)
        self.call("create", "--project", project, "--name", "invented installed study")
        flags = [
            "--task",
            "mmtt-sensitivity",
            "--package",
            inputs["package.json"],
            "--csv",
            inputs["observations.csv"],
            "--settings",
            inputs["settings.json"],
        ]
        self.assertFalse(self.call("validate", *flags)["estimation_performed"])
        plan = self.call("freeze", "--project", project, *flags)["plan"]
        return project, plan

    def native(self, project, attempt):
        with opened(project) as store:
            return store.finishes[attempt][1] / "native"

    def test_api_metadata_helpers_use_trusted_system_path(self):
        code = (
            "import json,opent1d_lab as lab\n"
            f"p=lab.create_project({str(self.root / 'api-project')!r},'invented API control')\n"
            f"inputs=lab.example('mmtt-sensitivity',{str(self.root / 'api-inputs')!r})['inputs']\n"
            "plan=p.freeze('mmtt-sensitivity',inputs)['plan']\n"
            "assert p.check(plan)['runtimes_ready']\n"
            "result=p.run(plan)\n"
            "print(json.dumps(result))\n"
        )
        result = subprocess.run(
            [str(self.candidates["a"] / "bin/python"), "-I", "-B", "-c", code],
            cwd=self.poison,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"]["completeness"], "complete")
        self.assertFalse(self.marker.exists())

    def test_thin_gui_shares_ledger_parent_ids_and_two_file_mmtt_reader(self):
        workspace = self.root / "gui-workspace"
        logfile = self.root / "gui.log"
        process = owner = None
        with logfile.open("wb") as output:
            try:
                process = subprocess.Popen(
                    [
                        str(self.candidates["a"] / "bin/opent1d-lab"),
                        "gui",
                        "--workspace",
                        str(workspace),
                    ],
                    cwd=self.poison,
                    env=self.env,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = Ownership(process)
                deadline = time.monotonic() + 20
                match = None
                while time.monotonic() < deadline:
                    owner.observe()
                    match = re.search(r"http://127\.0\.0\.1:(\d+)", logfile.read_text())
                    if match or process.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(match, logfile.read_text())
                port = int(match[1])
                token = None

                def request(route, body=None, expected=200):
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
                    headers = {"X-OpenT1D-Token": token} if token else {}
                    if body is not None:
                        headers.update(
                            Origin=f"http://127.0.0.1:{port}",
                            **{"Content-Type": "application/json"},
                        )
                    try:
                        connection.request(
                            "POST" if body is not None else "GET",
                            route,
                            json.dumps(body) if body is not None else None,
                            headers,
                        )
                        response = connection.getresponse()
                        raw = response.read()
                        self.assertEqual(response.status, expected, raw)
                        return raw
                    finally:
                        connection.close()

                html = request("/")
                token = re.search(rb'name="opent1d-token" content="([a-f0-9]{64})"', html)[
                    1
                ].decode()

                def action(operation, arguments, project=None):
                    job = json.loads(
                        request(
                            "/api/actions",
                            {
                                "request_id": uuid.uuid4().hex,
                                "operation": operation,
                                "project": project,
                                "arguments": arguments,
                            },
                            202,
                        )
                    )
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        owner.observe()
                        job = json.loads(request("/api/jobs/" + job["id"]))
                        if job["status"] != "running":
                            self.assertEqual(job["status"], "done", job)
                            return job
                        time.sleep(0.05)
                    self.fail("Installed GUI action did not finish: " + operation)

                handle = action("create", {"name": "Invented shared GUI project"})["project"]
                draft = action("prepare", {"task": "mmtt-sensitivity", "case": "complete"}, handle)[
                    "result"
                ]
                plan = action(
                    "freeze",
                    {"draft": draft["id"], "name": "Original invented pair", "parent": None},
                    handle,
                )["result"]["plan"]
                state = json.loads(request("/api/state"))
                folder = Path(next(p["path"] for p in state["projects"] if p["id"] == handle))
                head = (folder / "HEAD.json").read_bytes()
                detail = action("plan", {"plan": plan}, handle)["result"]
                self.assertIsNone(detail["parent"])
                self.assertEqual(
                    detail["scientific_input"]["settings"]["uncertainty"]["draws"], 128
                )
                self.assertEqual((folder / "HEAD.json").read_bytes(), head)
                self.assertTrue(action("check", {"plan": plan}, handle)["result"]["runtimes_ready"])
                result = action("run", {"plan": plan, "retry_of": None}, handle)["result"]
                self.assertEqual(result["result"]["completeness"], "complete")
                self.assertEqual(result["receipt"]["remaining_owned_processes"], [])
                attempt = result["attempt"]
                cli = self.call("info", "--project", folder)
                self.assertEqual(cli["plans"][0]["id"], plan)
                self.assertEqual(cli["attempts"][0]["id"], attempt)
                inputs = self.call(
                    "example",
                    "--task",
                    "mmtt-sensitivity",
                    "--case",
                    "censored",
                    "--output",
                    self.root / "cli-example",
                )["inputs"]
                child = self.call(
                    "freeze",
                    "--project",
                    folder,
                    "--task",
                    "mmtt-sensitivity",
                    "--package",
                    inputs["package.json"],
                    "--csv",
                    inputs["observations.csv"],
                    "--settings",
                    inputs["settings.json"],
                    "--parent",
                    plan,
                )["plan"]
                action("refresh", {}, handle)
                info = next(
                    p["info"]
                    for p in json.loads(request("/api/state"))["projects"]
                    if p["id"] == handle
                )
                self.assertEqual(next(p["parent"] for p in info["plans"] if p["id"] == child), plan)
                verified = action("verify", {"attempt": attempt, "allow_failed": False}, handle)[
                    "result"
                ]
                self.assertEqual(set(verified["report_sha256"]), {"report.json", "report.md"})
                report = verified["report"]
                head = (folder / "HEAD.json").read_bytes()
                for name, expected in verified["report_sha256"].items():
                    self.assertEqual(
                        hashlib.sha256(request(f"/api/reports/{report}/{name}")).hexdigest(),
                        expected,
                    )
                request("/api/state")
                self.assertEqual((folder / "HEAD.json").read_bytes(), head)
                moved = self.root / "moved-gui-project"
                action("relocate", {"output": str(moved)}, handle)
                self.assertEqual(self.call("info", "--project", moved)["plans"], info["plans"])
                copy = workspace / "reports" / report / "report.md"
                copy.write_bytes(b"changed report copy")
                request(f"/api/reports/{report}/report.md", expected=409)
                request("/api/shutdown", {}, 202)
                process.wait(timeout=45)
                self.assertEqual(process.returncode, 0, logfile.read_text())
                self.assertEqual(owner.cleanup(0)[1], [])
                self.assertFalse(self.marker.exists())
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.terminate()
                    if owner is not None:
                        owner.cleanup(45)
                    process.wait(timeout=3)

    def test_installed_run_retry_relocation_and_wrapper_upgrade(self):
        project, plan = self.prepared()
        self.assertTrue(self.call("check", "--project", project, "--plan", plan)["runtimes_ready"])
        first = self.call("run", "--project", project, "--plan", plan)
        second = self.call(
            "run",
            "--project",
            project,
            "--plan",
            plan,
            "--retry-of",
            first["attempt"],
            candidate="b",
        )
        self.assertEqual(second["result"]["completeness"], "complete")
        moved = self.root / "moved-project"
        self.call("relocate", "--project", project, "--output", moved)
        shutil.rmtree(project)
        output = self.root / "rebuilt-by-b"
        rebuilt = self.call(
            "reconstruct",
            "--project",
            moved,
            "--attempt",
            first["attempt"],
            "--output",
            output,
            candidate="b",
        )
        self.assertEqual(rebuilt["application"]["build_label"], "b")
        manifests = {
            key: json.loads(
                (
                    environment / "lib/python3.12/site-packages/opent1d_lab/_manifest.json"
                ).read_bytes()
            )
            for key, environment in self.candidates.items()
        }
        self.assertEqual(
            rebuilt["application"]["descriptor_sha256"], digest(encoded(manifests["b"]))
        )
        for name in ("report.json", "report.md"):
            self.assertEqual(
                (self.native(moved, first["attempt"]) / name).read_bytes(),
                (output / name).read_bytes(),
            )
        with opened(moved) as store:
            self.assertEqual(
                store.attempts[first["attempt"]]["host"]["application"]["build_label"], "a"
            )
            artifact = json.loads((store.plans[plan][1] / "application.json").read_bytes())
            self.assertEqual(artifact["artifact"], manifests["a"])
            self.assertEqual(artifact["identity"]["build_label"], "a")
            self.assertEqual(
                artifact["identity"]["descriptor_sha256"], digest(encoded(artifact["artifact"]))
            )
            self.assertEqual(
                store.attempts[second["attempt"]]["host"]["application"]["descriptor_sha256"],
                digest(encoded(manifests["b"])),
            )
        script = (
            "import json,sys,opent1d_lab as sdk; p=sdk.open_project(sys.argv[1]); "
            "print(json.dumps({'attempts':len(p.info()['attempts']),"
            "'payload_not_in_host':not any(n=='experiments' or "
            "n.startswith('experiments.') for n in sys.modules)}))"
        )
        result = subprocess.run(
            [str(self.candidates["b"] / "bin/python"), "-I", "-B", "-c", script, str(moved)],
            cwd=self.poison,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"attempts": 2, "payload_not_in_host": True})

    def test_incomplete_and_interrupted_native_evidence_stay_reconstructible(self):
        from experiments.observation_analysis.run import run

        project, plan = self.prepared(case="censored")
        incomplete = self.call("run", "--project", project, "--plan", plan, expected=1)
        self.assertEqual(incomplete["result"]["execution_status"], "completed")
        self.call(
            "reconstruct",
            "--project",
            project,
            "--attempt",
            incomplete["attempt"],
            "--output",
            self.root / "refused",
            expected=2,
        )
        self.call(
            "reconstruct",
            "--project",
            project,
            "--attempt",
            incomplete["attempt"],
            "--output",
            self.root / "rebuilt",
            "--allow-failed",
            candidate="b",
        )
        complete_project, complete_plan = self.prepared(suffix="-interrupt")
        with opened(complete_project) as store:
            frozen = store.plans[complete_plan][1] / "input"
        archive = self.root / "trusted-interrupted"
        with patch("experiments.observation_analysis.run.evaluate", side_effect=KeyboardInterrupt):
            run(frozen, archive)
        imported = self.call(
            "import", "--project", complete_project, "--plan", complete_plan, "--archive", archive
        )
        self.assertEqual(set(imported["result"]["slot_statuses"].values()), {"unavailable"})
        self.call(
            "reconstruct",
            "--project",
            complete_project,
            "--attempt",
            imported["attempt"],
            "--output",
            self.root / "interrupt-rebuilt",
            "--allow-failed",
            candidate="b",
        )
        for name in ("report.json", "report.md"):
            self.assertEqual(
                (archive / name).read_bytes(), (self.root / "interrupt-rebuilt" / name).read_bytes()
            )

    def test_m4_two_plans_policy_failure_and_trusted_failed_reader(self):
        project = self.root / "m4-project"
        self.call("create", "--project", project, "--name", "invented M4 intake")
        plans = []
        for case in ("fasting", "gastric_load_15g"):
            inputs = self.call(
                "example", "--task", "m4-study-secure", "--case", case, "--output", self.root / case
            )["inputs"]
            flags = ["--task", "m4-study-secure", "--config", inputs["config.json"]]
            self.call("validate", *flags)
            parent = ["--parent", plans[0]] if plans else []
            plans.append(self.call("freeze", "--project", project, *flags, *parent)["plan"])
        self.assertFalse(
            self.call("check", "--project", project, "--plan", plans[0])["runtimes_ready"]
        )
        unavailable = self.call("run", "--project", project, "--plan", plans[0], expected=1)
        self.assertEqual(unavailable["result"]["payload"], "forensic")
        self.assertEqual(set(unavailable["result"]["slot_statuses"].values()), {"unavailable"})
        with opened(project) as store:
            config = store.plans[plans[0]][1] / "input/config.json"
        archive = self.root / "controlled-failed-native"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-S",
                "-m",
                "tests.shared_service_worker",
                "m4-fail",
                str(config),
                str(archive),
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        imported = self.call(
            "import",
            "--project",
            project,
            "--plan",
            plans[0],
            "--archive",
            archive,
            "--retry-of",
            unavailable["attempt"],
        )
        self.call(
            "reconstruct",
            "--project",
            project,
            "--attempt",
            imported["attempt"],
            "--output",
            self.root / "failed-rebuilt",
            "--allow-failed",
            candidate="b",
        )
        for name in ("report.json", "report.md", "figure.svg"):
            self.assertEqual(
                (archive / name).read_bytes(), (self.root / "failed-rebuilt" / name).read_bytes()
            )

    def test_m4_successor_requires_explicit_attachment_and_protects_store_outputs(self):
        project = self.root / "successor-project"
        self.call("create", "--project", project, "--name", "Invented reviewed M4 successor")
        plans = []
        for case in ("fasting", "gastric_load_15g"):
            inputs = self.call(
                "example",
                "--task",
                "m4-study-installed",
                "--case",
                case,
                "--output",
                self.root / case,
            )["inputs"]
            flags = ["--task", "m4-study-installed", "--config", inputs["config.json"]]
            self.call("validate", *flags)
            parent = ["--parent", plans[0]] if plans else []
            plans.append(self.call("freeze", "--project", project, *flags, *parent)["plan"])
        self.assertFalse(
            self.call("check", "--project", project, "--plan", plans[0])["runtimes_ready"]
        )
        failed = self.call("run", "--project", project, "--plan", plans[0], expected=1)
        self.assertEqual(failed["result"]["payload"], "forensic")
        self.assertEqual(set(failed["result"]["slot_statuses"].values()), {"unavailable"})
        before = self.call("info", "--project", project)["head"]
        refused = self.call(
            "attach-runtimes",
            "--native-site",
            self.root / "absent-native",
            "--observer-site",
            self.root / "absent-observer",
            "--output",
            project / "attachment.json",
            expected=2,
        )
        self.assertIn("inside an existing project store", refused["error"])
        self.assertEqual(self.call("info", "--project", project)["head"], before)

    def test_fresh_outputs_cannot_corrupt_any_existing_project(self):
        project, plan = self.prepared()
        attempt = self.call("run", "--project", project, "--plan", plan)["attempt"]
        other = self.root / "other-project"
        before = self.call("create", "--project", other, "--name", "protected project")["head"]
        for command in (
            ["example", "--task", "mmtt-sensitivity", "--output", other / "inputs"],
            ["create", "--project", other / "nested", "--name", "refused"],
            [
                "reconstruct",
                "--project",
                project,
                "--attempt",
                attempt,
                "--output",
                other / "report",
            ],
            ["relocate", "--project", project, "--output", other / "copy"],
        ):
            self.call(*command, expected=2)
            self.assertEqual(self.call("info", "--project", other)["head"], before)
        self.assertEqual(
            {path.name for path in other.iterdir()},
            {"HEAD.json", ".lock", "events", "work", "pending"},
        )

    def test_forged_facade_bytecode_is_inert_and_fifo_refuses_promptly(self):
        package = self.root / "opent1d_lab"
        source = self.candidates["a"] / "lib/python3.12/site-packages/opent1d_lab"
        shutil.copytree(source, package)
        target = package / "cli.py"
        cache = package / "__pycache__/cli.cpython-312.pyc"
        cache.parent.mkdir(exist_ok=True)
        code = compile(
            "from pathlib import Path\ndef main():\n"
            f" Path({str(self.marker)!r}).touch()\n"
            " print('unverified cache')\n return 0\n",
            str(target),
            "exec",
        )
        cache.write_bytes(
            importlib.util.MAGIC_NUMBER
            + struct.pack("<III", 0, int(target.stat().st_mtime), target.stat().st_size)
            + marshal.dumps(code)
        )
        command = [
            str(self.candidates["a"] / "bin/python"),
            "-I",
            "-B",
            "-S",
            str(package / "launcher.py"),
            "installation",
        ]
        result = subprocess.run(
            command, cwd=self.poison, env=self.env, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["schema"], "opent1d.installed-sdk/2")
        self.assertFalse(self.marker.exists())
        victim = package / "_payload/app/experiments/shared_services/store.py"
        victim.unlink()
        os.mkfifo(victim)
        result = subprocess.run(
            command, cwd=self.poison, env=self.env, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_incompatible_reader_candidate_refuses_without_changing_project(self):
        project, _ = self.prepared()
        package = self.root / "incompatible-env/lib/python3.12/site-packages/opent1d_lab"
        package.parent.mkdir(parents=True)
        shutil.copytree(self.candidates["b"] / "lib/python3.12/site-packages/opent1d_lab", package)
        command = [
            str(self.candidates["b"] / "bin/python"),
            "-I",
            "-B",
            "-S",
            str(package / "launcher.py"),
            "info",
            "--project",
            str(project),
        ]
        before = self.call("info", "--project", project)["head"]
        control = subprocess.run(
            command, cwd=self.poison, env=self.env, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(control.returncode, 0, control.stdout + control.stderr)
        self.assertEqual(json.loads(control.stdout)["head"], before)
        reader = package / "_payload/app/experiments/observation_analysis/report.py"
        reader.write_bytes(reader.read_bytes() + b"\n# Deliberately incompatible reader fixture.\n")
        manifest = json.loads((package / "_manifest.json").read_bytes())
        manifest["files"][reader.relative_to(package).as_posix()] = {
            "sha256": digest(reader.read_bytes()),
            "bytes": reader.stat().st_size,
        }
        manifest["source"]["dirty"] = True
        manifest["build_label"] = "incompatible-reader-fixture"
        (package / "_manifest.json").write_bytes(encoded(manifest))
        result = subprocess.run(
            command,
            cwd=self.poison,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn(
            "Frozen task/source/runtime identity differs", json.loads(result.stdout)["error"]
        )
        self.assertEqual(self.call("info", "--project", project)["head"], before)

    def test_constructor_failure_cleans_owned_child_and_preserves_unrelated(self):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "tests.sdk_ownership_probe",
                str(self.candidates["a"] / "lib/python3.12/site-packages"),
            ],
            cwd=ROOT,
            env=self.environ,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {"direct_reaped": True, "child_alive": False, "unrelated_alive": True},
        )

    def test_installed_cancel_retains_attempt_and_cleans_live_owned_processes(self):
        project, plan = self.prepared()
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "tests.sdk_cancel_probe",
                str(self.candidates["a"] / "lib/python3.12/site-packages"),
                str(project),
                plan,
            ],
            cwd=ROOT,
            env=self.environ,
            capture_output=True,
            text=True,
            timeout=25,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        evidence = json.loads(result.stdout)
        self.assertTrue(evidence["stopped_live_native_child"])
        self.assertTrue(evidence["unrelated_alive"])
        self.assertEqual(evidence["remaining_owned_processes"], [])
        self.assertEqual(evidence["receipt_status"], "interrupted")
        info = self.call("info", "--project", project)
        self.assertEqual(len(info["attempts"]), 1)
        self.assertEqual(info["attempts"][0]["id"], evidence["attempt"])
        self.assertNotEqual(info["attempts"][0]["outcome"], "unfinished")

    def test_early_cancel_seals_attempt_without_launching_native_worker(self):
        project, plan = self.prepared()
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "tests.sdk_early_cancel_probe",
                str(self.candidates["a"] / "lib/python3.12/site-packages"),
                str(project),
                plan,
            ],
            cwd=ROOT,
            env=self.environ,
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["receipt"]["owned_processes"], [])
        self.assertFalse((Path(outcome["evidence"]) / "worker.log").exists())
        info = self.call("info", "--project", project)
        self.assertEqual(len(info["attempts"]), 1)
        self.assertEqual(info["attempts"][0]["id"], outcome["attempt"])
        self.assertEqual(info["attempts"][0]["outcome"]["execution_status"], "interrupted")

    def test_builder_refuses_facade_changed_after_clean_snapshot(self):
        source = self.root / "disposable-source"
        source.mkdir()
        shutil.copytree(ROOT / "packaging/sdk", source / "packaging/sdk")
        shutil.copyfile(ROOT / "LICENSE", source / "LICENSE")
        for args in (
            ["init", "--quiet"],
            ["add", "."],
            [
                "-c",
                "user.name=SDK fixture",
                "-c",
                "user.email=sdk-fixture@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "Disposable build-race fixture",
            ],
        ):
            subprocess.run(["git", *args], cwd=source, check=True, capture_output=True)

        def snapshot_then_change(root, *, allow_dirty=False):
            snapshot = source_inventory(root, allow_dirty=allow_dirty)
            self.assertFalse(snapshot["dirty"])
            target = source / "packaging/sdk/opent1d_lab/api.py"
            target.write_bytes(target.read_bytes() + b"\n# Controlled post-snapshot edit.\n")
            return snapshot

        output = self.root / "refused-build"
        with (
            patch.object(build_sdk, "ROOT", source),
            patch.object(build_sdk, "source_closure", return_value=[]),
            patch(
                "scripts.build_windows_installer.source_inventory", side_effect=snapshot_then_change
            ),
            self.assertRaisesRegex(
                ValueError, "Source changed during SDK staging: packaging/sdk/opent1d_lab/api.py"
            ),
        ):
            build_sdk.build(output)
        self.assertFalse((output / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
