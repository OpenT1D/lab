"""Actual noneditable comparison SDK/CLI/HTTP, native evidence and relocation."""

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

from tests import test_installed_sampling as installed
from tests import test_workbench_installed as editable


@unittest.skipUnless(
    os.name == "posix" and sys.version_info[:2] == (3, 12), "POSIX CPython 3.12 installed SDK"
)
class InstalledComparisons(unittest.TestCase):
    setUpClass = classmethod(installed.InstalledSampling.setUpClass.__func__)
    setUp = installed.InstalledSampling.setUp
    call = installed.InstalledSampling.call
    server = editable.EditableWorkbench.server
    inputs = editable.EditableWorkbench.inputs

    def definition(self, members):
        return {
            "schema": "opent1d.plan-comparison/1",
            "name": "Installed comparison",
            "question": "What changes under these frozen synthetic assumptions?",
            "baseline": members[0]["id"],
            "variants": members,
        }

    def member(self, identity, plan, selector):
        return {"id": identity, "label": identity, "plan": plan, "selector": selector}

    def prepare(self, app, task="mmtt-sensitivity", case="complete"):
        _, raw = self.inputs(case, task)
        handle = app.action("create", {"name": "Frozen comparisons"})["project"]
        draft = app.action(
            "draft_create",
            {"task": task, "name": "Invented comparison input", "files": raw},
            handle,
        )
        plan = app.freeze(app.validate(draft))["plan"]
        path = Path(next(p for p in app.state()["projects"] if p["id"] == handle)["path"])
        return handle, path, plan

    def test_installed_sdk_cli_gui_parity_snapshot_download_restart_and_move(self):
        with self.server() as app:
            handle, path, plan = self.prepare(app)
            definition = self.definition(
                [
                    self.member("baseline", plan, {"variant": "nominal"}),
                    self.member("volume", plan, {"variant": "volume-120"}),
                ]
            )
            source = self.root / "comparison.json"
            source.write_text(json.dumps(definition))
            frozen = self.call("freeze-comparison", "--project", path, "--definition", source)
            identity = frozen["comparison"]
            app.action("refresh", {}, handle)
            opened = app.action("comparison_open", {"comparison": identity, "at": None}, handle)
            self.assertEqual(opened["variants"], definition["variants"])
            self.assertEqual(opened["attempts"][plan]["status"], "unattempted")
            initial = app.action("comparison_verify", {"comparison": identity, "at": None}, handle)
            initial_tip = initial["snapshot"]["tip"]
            initial_raw = app.request("/api/reports/" + initial["report"] + "/report.json")
            self.assertEqual(json.loads(initial_raw)["coverage"]["planned_members"], 2)
            app.action("run", {"plan": plan, "retry_of": None}, handle)
            result = app.action("comparison_verify", {"comparison": identity, "at": None}, handle)
            raw = app.request("/api/reports/" + result["report"] + "/report.json")
            self.assertEqual(json.loads(raw)["completeness"], "complete")
            csv = app.request("/api/reports/" + result["report"] + "/comparison.csv")
            self.assertEqual(
                hashlib.sha256(csv).hexdigest(), result["report_sha256"]["comparison.csv"]
            )
            self.assertIn(b"volume", csv)
            app.restart()
            moved = self.root / "moved"
            copied = app.action("relocate", {"output": str(moved)}, handle)["project"]
            path.rename(path.with_name("original-unavailable"))
            replay = app.action(
                "comparison_verify", {"comparison": identity, "at": initial_tip}, copied
            )
            self.assertEqual(
                app.request("/api/reports/" + replay["report"] + "/report.json"), initial_raw
            )
            cli = self.call(
                "reconstruct-comparison",
                "--project",
                moved,
                "--comparison",
                identity,
                "--at",
                result["snapshot"]["tip"],
                "--output",
                self.root / "cli-result",
            )
            self.assertEqual(cli["report_sha256"], result["report_sha256"])
            code = (
                "import opent1d_lab as lab,json;print(json.dumps(lab.Project("
                + repr(str(moved))
                + ").comparison("
                + repr(identity)
                + ")))"
            )
            python = self.call_python(code)
            self.assertEqual(python["comparison"], identity)
            self.assertEqual(python["baseline"], "baseline")

    def call_python(self, code):
        import subprocess

        python = self.cli.parent / "python"
        result = subprocess.run(
            [str(python), "-I", "-c", code],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_sampling_selectors_and_native_child_comparison_tables(self):
        with self.server() as app:
            handle, path, plan = self.prepare(app, "mmtt-sampling", "information-loss")
            options = self.call("comparison-options", "--project", path, "--plan", plan)
            self.assertIn(
                {"schedule": "three-times", "variant": "nominal"},
                [o["selector"] for o in options["options"]],
            )
            definition = self.definition(
                [
                    self.member("full", plan, {"schedule": "full", "variant": "nominal"}),
                    self.member("reduced", plan, {"schedule": "three-times", "variant": "nominal"}),
                ]
            )
            frozen = app.action("comparison_freeze", {"definition": definition}, handle)
            self.assertTrue(
                any(c["path"] == "/selected_times_minutes" for c in frozen["changes"][1]["fields"])
            )
            app.action("run", {"plan": plan, "retry_of": None}, handle)
            report = app.action(
                "comparison_verify", {"comparison": frozen["comparison"], "at": None}, handle
            )
            value = json.loads(app.request("/api/reports/" + report["report"] + "/report.json"))
            self.assertEqual(value["coverage"]["planned_members"], 2)
            self.assertEqual(
                {r["allocation"] for m in value["members"] for r in m["rows"]},
                {"development", "evaluation"},
            )
            self.assertTrue(
                any(
                    r["difference"] != 0
                    for r in value["members"][1]["rows"]
                    if r["difference"] is not None
                )
            )

    def test_m4_supported_source_load_roster_and_missing_runtime_failure(self):
        with self.server() as app:
            handle = app.action("create", {"name": "M4 declared failure denominator"})["project"]
            path = Path(app.state()["projects"][0]["path"])
            plans = []
            for case in ("fasting", "gastric_load_15g"):
                prepared = app.action(
                    "prepare", {"task": "m4-study-installed", "case": case}, handle
                )
                plans.append(app.freeze(prepared)["plan"])
            definition = self.definition(
                [
                    self.member(
                        "fasting", plans[0], {"source": "dalla_man", "scenario": "fasting"}
                    ),
                    self.member(
                        "load", plans[1], {"source": "dalla_man", "scenario": "gastric_load_15g"}
                    ),
                    self.member("source", plans[0], {"source": "ultradian", "scenario": "fasting"}),
                ]
            )
            frozen = app.action("comparison_freeze", {"definition": definition}, handle)
            fields = frozen["changes"][1]["fields"]
            self.assertTrue(
                any(
                    c["path"] == "/selected_load/initial_gastric_solid_mg" and c["after"] == 15000
                    for c in fields
                )
            )
            app.action("run", {"plan": plans[0], "retry_of": None}, handle)
            report = app.action(
                "comparison_verify", {"comparison": frozen["comparison"], "at": None}, handle
            )
            value = json.loads(app.request("/api/reports/" + report["report"] + "/report.json"))
            self.assertEqual(
                [m["attempt"]["status"] for m in value["members"]],
                ["failed", "unattempted", "failed"],
            )
            self.assertEqual(value["coverage"]["planned_cases"], 9)
            self.assertTrue(all(r["metrics"] is None for m in value["members"] for r in m["rows"]))
            self.assertEqual(len(self.call("info", "--project", path)["attempts"]), 1)


if __name__ == "__main__":
    unittest.main()
