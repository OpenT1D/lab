"""Actual installed SDK/HTTP concepts, exact intake, derivation and recovery."""

import contextlib
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

from experiments.mmtt_sampling.run import run as native_sampling
from experiments.shared_services.store import opened
from tests import test_installed_sampling as installed


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 SDK"
)
class EditableWorkbench(unittest.TestCase):
    setUpClass = classmethod(installed.InstalledSampling.setUpClass.__func__)
    setUp = installed.InstalledSampling.setUp
    call = installed.InstalledSampling.call

    @contextlib.contextmanager
    def server(self):
        test = self

        class App:
            def __init__(self):
                self.workspace = test.root / "workspace"
                self.process = None
                self.logs = []
                self.start()

            def start(self):
                log = (test.root / ("server-" + str(len(self.logs)) + ".log")).open("w+")
                self.logs.append(log)
                self.process = subprocess.Popen(
                    [str(test.cli), "gui", "--workspace", str(self.workspace)],
                    cwd=test.root,
                    env=test.env,
                    stdout=log,
                    stderr=log,
                )
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    log.seek(0)
                    output = log.read()
                    match = re.search(r"http://127\.0\.0\.1:(\d+)", output)
                    if match:
                        self.port = int(match[1])
                        self.token = None
                        html = self.request("/")
                        self.token = re.search(
                            rb'name="opent1d-token" content="([a-f0-9]{64})"', html
                        )[1].decode()
                        return
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.02)
                raise AssertionError("Installed server not ready: " + output)

            def stop(self):
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=20)

            def restart(self):
                self.stop()
                self.start()

            def request(self, route, body=None, expected=200):
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
                headers = {"X-OpenT1D-Token": self.token} if self.token else {}
                if body is not None:
                    headers.update(
                        Origin=f"http://127.0.0.1:{self.port}",
                        **{"Content-Type": "application/json"},
                    )
                try:
                    connection.request(
                        "GET" if body is None else "POST",
                        route,
                        json.dumps(body) if body is not None else None,
                        headers,
                    )
                    response = connection.getresponse()
                    raw = response.read()
                    test.assertEqual(response.status, expected, raw)
                    return raw
                finally:
                    connection.close()

            def state(self):
                return json.loads(self.request("/api/state"))

            def action(self, operation, arguments, project=None, expected="done"):
                if operation == "draft_create":
                    arguments = {"parent": None, **arguments}
                route = (
                    "/api/drafts" if operation in {"draft_create", "draft_save"} else "/api/actions"
                )
                job = json.loads(
                    self.request(
                        route,
                        {
                            "request_id": uuid.uuid4().hex,
                            "operation": operation,
                            "project": project,
                            "arguments": arguments,
                        },
                        202,
                    )
                )
                deadline = time.monotonic() + 60
                while job["status"] == "running" and time.monotonic() < deadline:
                    time.sleep(0.02)
                    job = json.loads(self.request("/api/jobs/" + job["id"]))
                test.assertEqual(job["status"], expected, job)
                return job["result"] if expected == "done" else job

            def draft(self, key):
                return json.loads(self.request("/api/drafts/" + key))

            def save(self, draft, raw, **changes):
                return self.action(
                    "draft_save",
                    {
                        "draft": draft["id"],
                        "revision": draft["revision"],
                        "name": changes.get("name", draft["name"]),
                        "parent": changes.get("parent", draft["parent"]),
                        "files": raw,
                    },
                    draft["project"],
                    expected=changes.get("expected", "done"),
                )

            def validate(self, draft):
                return self.action(
                    "draft_validate",
                    {"draft": draft["id"], "revision": draft["revision"]},
                    draft["project"],
                )

            def freeze(self, draft, **options):
                return self.action(
                    "freeze",
                    {
                        "draft": draft["id"],
                        "revision": draft["revision"],
                        "name": draft["name"],
                        "parent": draft["parent"],
                    },
                    draft["project"],
                    **options,
                )

        app = App()
        try:
            yield app
        finally:
            app.stop()
            for log in app.logs:
                log.close()

    def inputs(self, case, task="mmtt-sensitivity"):
        exported = self.call(
            "example", "--task", task, "--case", case, "--output", self.root / (case + "-inputs")
        )["inputs"]
        raw = {
            name: Path(value).read_bytes().decode("utf-8")
            for name, value in exported.items()
            if name != "development"
        }
        if task == "mmtt-sampling":
            for source, target in (
                ("package.json", "development-package.json"),
                ("observations.csv", "development-observations.csv"),
            ):
                raw[target] = (Path(exported["development"]) / source).read_bytes().decode("utf-8")
        if "settings.json" in raw:
            settings = json.loads(raw["settings.json"])
            settings["uncertainty"]["draws"] = 32
            raw["settings.json"] = json.dumps(settings)
        return exported, raw

    def test_own_intake_invalid_recovery_exact_bytes_parent_and_project_copy(self):
        _, raw = self.inputs("complete")
        package = json.loads(raw["package.json"])
        old = package["participants"][0]["id"]
        package["participants"][0]["id"] = "own-invented-person"
        package["provenance"] = "Researcher-chosen invented software input"
        raw["package.json"] = json.dumps(package)
        raw["observations.csv"] = "\ufeff" + raw["observations.csv"].replace(
            old, "own-invented-person"
        ).replace("\n", "\r\n")
        good = dict(raw)
        raw["settings.json"] = "{unfinished settings"
        with self.server() as app:
            project = app.action("create", {"name": "Own invented study"})["project"]
            project_path = Path(app.state()["projects"][0]["path"])
            head = (project_path / "HEAD.json").read_bytes()
            draft = app.action(
                "draft_create",
                {"task": "mmtt-sensitivity", "name": "Own synthetic pair", "files": raw},
                project,
            )
            failed = app.validate(draft)
            self.assertFalse(failed["validation"]["valid"])
            self.assertEqual(failed["files"], raw)
            app.freeze(failed, expected="error")
            self.assertEqual((project_path / "HEAD.json").read_bytes(), head)
            app.restart()
            restored = app.draft(draft["id"])
            self.assertEqual(restored["files"], raw)
            saved = app.save(restored, good)
            app.save(restored, raw, expected="error")
            checked = app.validate(saved)
            self.assertTrue(checked["validation"]["valid"])
            self.assertTrue(checked["validation"]["result"]["observations"]["valid"])
            plan = app.freeze(checked)["plan"]
            detail = self.call("plan", "--project", project_path, "--plan", plan)
            self.assertEqual(
                detail["original_sha256"]["observations.csv"],
                hashlib.sha256(good["observations.csv"].encode()).hexdigest(),
            )
            exported = self.call(
                "export-inputs",
                "--project",
                project_path,
                "--plan",
                plan,
                "--output",
                self.root / "exported-originals",
            )
            self.assertEqual(
                {
                    name: Path(value).read_bytes().decode()
                    for name, value in exported["inputs"].items()
                },
                good,
            )
            result = self.call("run", "--project", project_path, "--plan", plan)
            self.assertEqual(result["result"]["completeness"], "complete")
            verified = app.action(
                "verify", {"attempt": result["attempt"], "allow_failed": False}, project
            )
            self.assertEqual(verified["report_sha256"], result["result"]["report_sha256"])
            with opened(project_path) as store:
                original = store.plans[plan][1]
                before = {
                    p.relative_to(original).as_posix(): p.read_bytes()
                    for p in original.rglob("*")
                    if p.is_file()
                }
            rechecked = app.validate(app.draft(draft["id"]))
            self.assertEqual(rechecked["frozen_plan"], plan)
            app.freeze(rechecked, expected="error")
            auto_derived = app.save(rechecked, good, name="Edited after revalidation")
            self.assertEqual(auto_derived["parent"], plan)
            self.assertIsNone(auto_derived["frozen_plan"])
            derived = app.action("derive", {"plan": plan}, project)
            self.assertEqual(derived["files"], good)
            self.assertEqual(derived["parent"], plan)
            forked = app.action(
                "draft_create",
                {
                    "task": derived["task"],
                    "name": "Conflict copy",
                    "parent": derived["parent"],
                    "files": derived["files"],
                },
                project,
            )
            self.assertEqual(forked["parent"], plan)
            settings = json.loads(good["settings.json"])
            settings["variants"][0]["volume_l"] *= 1.1
            edited = app.save(derived, {**good, "settings.json": json.dumps(settings)})
            self.assertIsNone(edited["validation"])
            app.freeze(edited, expected="error")
            checked = app.validate(edited)
            child = app.freeze(checked)["plan"]
            self.assertNotEqual(child, plan)
            self.assertEqual(
                self.call("plan", "--project", project_path, "--plan", child)["parent"], plan
            )
            self.assertEqual(
                before,
                {
                    p.relative_to(original).as_posix(): p.read_bytes()
                    for p in original.rglob("*")
                    if p.is_file()
                },
            )
            latest = app.draft(derived["id"])
            history_length = len(latest["history"])
            moved = self.root / "moved-project"
            copied = app.action("relocate", {"output": str(moved)}, project)["project"]
            app.restart()
            project_path.rename(project_path.with_name("original-unavailable"))
            app.action("refresh", {}, copied)
            copies = [item for item in app.state()["drafts"] if item["project"] == copied]
            copied_draft = next(
                value
                for value in (app.draft(item["id"]) for item in copies)
                if value["origin"]["draft"] == latest["id"]
            )
            self.assertEqual(copied_draft["name"], latest["name"])
            self.assertEqual(
                len(copied_draft["history"]),
                history_length,
                {
                    "source": {k: latest[k] for k in ("id", "name", "revision", "history")},
                    "copy": {k: copied_draft[k] for k in ("id", "name", "revision", "history")},
                    "copies": copies,
                },
            )
            self.assertIsNone(copied_draft["validation"])
            checked_report = app.action(
                "verify", {"attempt": result["attempt"], "allow_failed": False}, copied
            )
            self.assertEqual(checked_report["report_sha256"], verified["report_sha256"])

    def test_sampling_own_design_development_boundary_and_native_incomplete_parity(self):
        exported, raw = self.inputs("incomplete", "mmtt-sampling")
        self.call(
            "prepare-development",
            "--package",
            exported["package.json"],
            "--csv",
            self.root / "must-not-read.csv",
            "--design",
            exported["design.json"],
            "--output",
            self.root / "refused-dev",
            expected=2,
        )
        design = json.loads(raw["design.json"])
        design["selection_rationale"] = "Own invented development-only schedule check"
        design["subsets"]["three-times"] = [0, 30, 120]
        raw["design.json"] = json.dumps(design)
        with self.server() as app:
            project = app.action("create", {"name": "Own invented sampling"})["project"]
            project_path = Path(app.state()["projects"][0]["path"])
            bad = {
                **raw,
                "development-package.json": raw["package.json"],
                "development-observations.csv": "not interpreted",
            }
            draft = app.action(
                "draft_create",
                {"task": "mmtt-sampling", "name": "Own schedules", "files": bad},
                project,
            )
            failed = app.validate(draft)
            self.assertFalse(failed["validation"]["valid"])
            self.assertIn("development-only", failed["validation"]["error"])
            checked = app.validate(app.save(failed, raw))
            self.assertTrue(checked["validation"]["valid"])
            self.assertTrue(
                any(
                    visit["missing_or_censored"]
                    for visit in checked["validation"]["result"]["observations"]["visits"]
                )
            )
            plan = app.freeze(checked)["plan"]
            result = self.call("run", "--project", project_path, "--plan", plan, expected=1)
            self.assertEqual(len(result["result"]["slot_statuses"]), 60)
            self.assertEqual(result["result"]["completeness"], "incomplete")
            with opened(project_path) as store:
                frozen = store.plans[plan][1] / "input"
                archive = store.finishes[result["attempt"]][1] / "native"
                direct = self.root / "direct-sampling"
                native_sampling(frozen, direct)
                for name in result["result"]["report_sha256"]:
                    self.assertEqual((archive / name).read_bytes(), (direct / name).read_bytes())
            app.action(
                "verify",
                {"attempt": result["attempt"], "allow_failed": False},
                project,
                expected="error",
            )
            report = app.action(
                "verify", {"attempt": result["attempt"], "allow_failed": True}, project
            )
            self.assertEqual(len(report["report_sha256"]), 10)

    def test_selected_m4_editing_export_and_source_refusal_need_no_native_setup(self):
        _, raw = self.inputs("fasting", "m4-study-installed")
        with self.server() as app:
            project = app.action("create", {"name": "Selected M4 concept"})["project"]
            project_path = Path(app.state()["projects"][0]["path"])
            draft = app.action(
                "draft_create",
                {"task": "m4-study-installed", "name": "Fasting", "files": raw},
                project,
            )
            checked = app.validate(draft)
            self.assertTrue(checked["validation"]["valid"])
            plan = app.freeze(checked)["plan"]
            derived = app.action("derive", {"plan": plan}, project)
            self.assertEqual(derived["files"], raw)
            config = json.loads(raw["config.json"])
            config["scenarios"] = ["gastric_load_15g"]
            edited = app.save(derived, {"config.json": json.dumps(config)})
            child = app.freeze(app.validate(edited))["plan"]
            self.assertEqual(
                self.call("plan", "--project", project_path, "--plan", child)["parent"], plan
            )
            self.assertFalse(
                self.call("check", "--project", project_path, "--plan", child)["runtimes_ready"]
            )
            head = (project_path / "HEAD.json").read_bytes()
            config["sources"][0]["model"] = "../untrusted.py"
            latest = app.draft(derived["id"])
            failed = app.validate(app.save(latest, {"config.json": json.dumps(config)}))
            self.assertFalse(failed["validation"]["valid"])
            self.assertEqual((project_path / "HEAD.json").read_bytes(), head)


if __name__ == "__main__":
    unittest.main()
