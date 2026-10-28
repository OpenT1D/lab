"""Real owned observation CLI jobs and HTTP boundaries, using invented inputs."""

import copy
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from experiments.gui.library_observations import validate_report
from experiments.gui.observations import Observations
from experiments.gui.server import Server
from experiments.gui.service import ROOT, Service, encode, inventory
from experiments.observation_analysis.fixtures import analysis_settings, csv_bytes, package


class ObservationGUITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        shutil.copytree(
            ROOT / "experiments",
            self.root / "experiments",
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "node_modules", "results"),
        )
        target = self.root / "docs/decisions"
        target.mkdir(parents=True)
        shutil.copyfile(
            ROOT / "docs/decisions/0067-mmtt-feasibility-boundary.md",
            target / "0067-mmtt-feasibility-boundary.md",
        )
        for name in ("uv.lock", "pyproject.toml", ".python-version"):
            shutil.copyfile(ROOT / name, self.root / name)
        (self.root / ".venv/bin").mkdir(parents=True)
        (self.root / ".venv/bin/python").symlink_to(sys.executable)
        (self.root / ".venv/pyvenv.cfg").write_text((ROOT / ".venv/pyvenv.cfg").read_text())
        self.service = Service(self.root, python=sys.executable)
        self.server = Server(self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.service.close()
        self.server.server_close()
        self.thread.join(2)
        self.temporary.cleanup()

    def request(self, method, path, body=None, *, token=True, origin=True, raw=False):
        headers = {}
        if token:
            headers["X-OpenT1D-Token"] = self.server.token
        if origin:
            headers["Origin"] = self.origin
        if body is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(body)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        try:
            connection.request(method, "/api/v1/" + path, body, headers)
            response = connection.getresponse()
            content = response.read()
            return response.status, content if raw else json.loads(content)
        finally:
            connection.close()

    def wait(self, job):
        self.service.thread.join(20)
        self.assertFalse(self.service.thread.is_alive(), self.service.get_job(job["id"]))
        final = self.service.get_job(job["id"])
        self.assertFalse(final.get("remaining_owned_processes"), final)
        self.assertFalse(final["cleanup_forced"], final)
        return final

    def configure(self, case="increase", display_name=None):
        status, job = self.request("POST", "observations/example", {"case": case})
        self.assertEqual(status, 202, job)
        prepared = self.wait(job)
        self.assertEqual(prepared["state"], "completed", prepared)
        paths = prepared["result"]["input_paths"]
        status, inspected = self.request("POST", "observations/inspect", paths)
        self.assertEqual(status, 201, inspected)
        self.assertEqual(inspected["display_name"], prepared["result"]["display_name"])
        status, config = self.request(
            "POST",
            "observations/configurations",
            {
                "package": paths["package"],
                "csv": paths["csv"],
                "settings": inspected["settings"],
                "input_sha256": inspected["input_sha256"],
                **({"display_name": display_name} if display_name is not None else {}),
            },
        )
        self.assertEqual(status, 201, config)
        status, job = self.request("POST", f"observations/configurations/{config['id']}/freeze", {})
        self.assertEqual(status, 202, job)
        frozen = self.wait(job)
        self.assertEqual(frozen["state"], "completed", frozen)
        return self.service.observations.get_configuration(config["id"])

    def execute(self, config):
        status, job = self.request("POST", f"observations/configurations/{config['id']}/run", {})
        self.assertEqual(status, 202, job)
        completed = self.wait(job)
        return completed, self.service.observations.get(completed["observation_entry_id"])

    def test_actual_four_case_http_flow_native_reports_and_reconstruction(self):
        expected = {
            "increase": "consistent within investigated assumptions",
            "assumption-dependent": "assumption-dependent",
            "unresolved": "insufficiently determined",
            "censored": "insufficiently determined",
        }
        names = {
            "increase": "Consistent increase control",
            "assumption-dependent": "Assumption-dependent control",
            "unresolved": "Unresolved change control",
            "censored": "Censored observation control",
        }
        for case, label in expected.items():
            with self.subTest(case=case):
                config = self.configure(case)
                self.assertTrue(config["ready"])
                completed, entry = self.execute(config)
                self.assertEqual(config["display_name"], names[case])
                self.assertEqual(entry["display_name"], names[case])
                self.assertEqual(completed["task"], "mmtt-sensitivity")
                self.assertEqual(
                    completed["report_completeness"],
                    "incomplete" if case == "censored" else "complete",
                )
                status, wrapper = self.request("GET", f"observations/entries/{entry['id']}/report")
                self.assertEqual(status, 200, wrapper)
                report = wrapper["native_report"]
                self.assertEqual(report["people"]["invented-01"]["classification"], label)
                self.assertEqual(report["coverage"]["planned_variant_pairs"], 3)
                archive = self.service.observations.folder(entry) / "archive"
                before = inventory(archive)
                status, job = self.request(
                    "POST", f"observations/entries/{entry['id']}/reconstruct", {}
                )
                self.assertEqual(status, 202, job)
                verified = self.wait(job)
                self.assertEqual(verified["state"], "completed", verified)
                self.assertEqual(inventory(archive), before)
                self.assertEqual(
                    self.service.observations.get(entry["id"])["verification"],
                    "native_reader_verified",
                )
                for name in ("report.json", "report.md"):
                    status, raw = self.request(
                        "GET", f"observations/entries/{entry['id']}/artifacts/{name}", raw=True
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(raw, (archive / name).read_bytes())
                    self.assertEqual(
                        raw, (self.service.data / job["id"] / "reconstructed" / name).read_bytes()
                    )
                if case in {"increase", "censored"}:
                    exported = self.root / "exports" / case
                    exported.parent.mkdir(exist_ok=True)
                    shutil.copytree(archive, exported)
                    snapshot = inventory(exported)
                    root_id = self.service.library.roots()[0]["id"]
                    status, indexed = self.request(
                        "POST",
                        "library/entries",
                        {"root_id": root_id, "path": f"exports/{case}", "task": "mmtt-sensitivity"},
                    )
                    self.assertEqual(status, 202, indexed)
                    self.assertEqual(self.wait(indexed)["state"], "completed")
                    ident = indexed["request"]["entry"]["id"]
                    status, verifying = self.request("POST", f"library/entries/{ident}/verify", {})
                    self.assertEqual(status, 202, verifying)
                    final = self.wait(verifying)
                    self.assertEqual(final["state"], "completed", final)
                    status, bound = self.request("GET", f"library/entries/{ident}/report")
                    self.assertEqual(status, 200, bound)
                    self.assertEqual(bound["native_report"], report)
                    self.assertEqual(
                        bound["report_completeness"],
                        "incomplete" if case == "censored" else "complete",
                    )
                    self.assertEqual(inventory(exported), snapshot)
        self.assertEqual(len(self.service.observations.list()), 4)

    def test_display_names_persist_outside_native_evidence_and_legacy_records_still_open(self):
        name = "My <paired> comparison – first pass"
        config = self.configure(display_name="  " + name + "  ")
        self.assertEqual(config["display_name"], name)
        paths = config["input_paths"]
        status, inspected = self.request("POST", "observations/inspect", paths)
        self.assertEqual(status, 201, inspected)
        self.assertEqual(inspected["display_name"], name)
        body = {
            "package": paths["package"],
            "csv": paths["csv"],
            "settings": inspected["settings"],
            "input_sha256": inspected["input_sha256"],
        }
        before = len(self.service.observations.configs)
        for invalid in ("x" * 121, 123, None, "two\nlines", "control\x7f", "line\u2028separator"):
            with self.subTest(invalid=repr(invalid)):
                status, result = self.request(
                    "POST", "observations/configurations", {**body, "display_name": invalid}
                )
                self.assertEqual(status, 400, result)
                self.assertIn("Analysis name", result["error"])
        self.assertEqual(len(self.service.observations.configs), before)
        status, cloned = self.request(
            "POST", "observations/configurations", {**body, "display_name": " "}
        )
        self.assertEqual(status, 201, cloned)
        self.assertEqual(cloned["display_name"], name)
        self.assertEqual(cloned["inputs_sha256"], config["inputs_sha256"])
        original_frozen = inventory(self.service.observations.folder(config) / "frozen")
        edited_settings = copy.deepcopy(config["settings"])
        edited_settings["variants"][0]["volume_l"] = 9.17
        # Use the saved fingerprints as the GUI does; changing settings needs no reinspection.
        edited_body = {
            **body,
            "settings": edited_settings,
            "input_sha256": {
                key: config["inputs_sha256"][key] for key in ("package.json", "observations.csv")
            },
            "display_name": "Changed volume",
        }
        status, edited = self.request("POST", "observations/configurations", edited_body)
        self.assertEqual(status, 201, edited)
        status, freeze = self.request(
            "POST", f"observations/configurations/{edited['id']}/freeze", {}
        )
        self.assertEqual(status, 202, freeze)
        self.assertEqual(self.wait(freeze)["state"], "completed")
        self.assertEqual(edited["settings"]["variants"][0]["volume_l"], 9.17)
        self.assertEqual(self.service.observations.get_configuration(config["id"]), config)
        self.assertEqual(
            inventory(self.service.observations.folder(config) / "frozen"), original_frozen
        )
        completed, entry = self.execute(config)
        self.assertNotIn("display_name", completed["request"])
        self.assertEqual(entry["display_name"], name)
        native = self.service.observations.folder(entry) / "archive"
        snapshot = inventory(native)
        self.assertNotIn("display_name", json.loads((self.root / paths["settings"]).read_text()))
        self.assertNotIn(
            "display_name", self.service.observations.report(entry["id"])["native_report"]
        )
        restored = Observations(self.service)
        self.assertEqual(restored.get_configuration(config["id"])["display_name"], name)
        self.assertEqual(restored.get(entry["id"])["display_name"], name)
        # Older records have no metadata name. Reading them must not modify scientific bytes.
        restored.configs[config["id"]].pop("display_name")
        restored.entries[entry["id"]].pop("display_name")
        restored.persist(restored.configs[config["id"]])
        restored.persist(restored.entries[entry["id"]])
        legacy = Observations(self.service)
        self.assertEqual(
            legacy.get_configuration(config["id"])["display_name"], "Paired meal-test analysis"
        )
        self.assertEqual(legacy.get(entry["id"])["display_name"], "Paired meal-test analysis")
        self.assertEqual(inventory(native), snapshot)
        input_csv = self.root / paths["csv"]
        input_csv.write_bytes(input_csv.read_bytes() + b"\n")
        status, refused = self.request("POST", "observations/configurations", edited_body)
        self.assertEqual(status, 400, refused)
        self.assertIn("Input bytes changed", refused["error"])

    def test_input_changes_human_declarations_paths_and_unknown_operations_refused(self):
        self.assertEqual(self.request("GET", "observations/bootstrap", token=False)[0], 403)
        self.assertEqual(
            self.request("POST", "observations/example", {"case": "increase"}, origin=False)[0], 403
        )
        self.assertEqual(
            self.request("POST", "observations/example", {"command": "arbitrary"})[0], 400
        )
        folder = self.root / "inputs"
        folder.mkdir()
        (folder / "package.json").write_bytes(encode(package()))
        (folder / "settings.json").write_bytes(encode(analysis_settings()))
        (folder / "observations.csv").write_bytes(csv_bytes())
        paths = {
            "package": "inputs/package.json",
            "csv": "inputs/observations.csv",
            "settings": "inputs/settings.json",
        }
        _, inspected = self.request("POST", "observations/inspect", paths)
        (folder / "observations.csv").write_bytes(csv_bytes() + b"\n")
        self.assertEqual(
            self.request(
                "POST",
                "observations/configurations",
                {
                    "package": paths["package"],
                    "csv": paths["csv"],
                    "settings": inspected["settings"],
                    "input_sha256": inspected["input_sha256"],
                },
            )[0],
            400,
        )
        human = package()
        human["data_kind"] = "human"
        (folder / "package.json").write_bytes(encode(human))
        status, result = self.request(
            "POST", "observations/inspect", {**paths, "csv": "absent.csv"}
        )
        self.assertEqual(status, 400)
        self.assertIn("synthetic", result["error"])
        self.assertEqual(self.request("GET", "observations/files?directory=..")[0], 400)
        (folder / "link.json").symlink_to(folder / "package.json")
        self.assertEqual(
            self.request("POST", "observations/inspect", {**paths, "package": "inputs/link.json"})[
                0
            ],
            400,
        )
        self.assertIsNone(self.service.active)

    def test_actual_native_cancellation_retains_roster_and_cannot_own_second_operation(self):
        config = self.configure()
        # Create a longer permitted synthetic run, without importing a supplied method.
        original = self.service.observations.folder(config) / "inputs"
        people = package()
        base, rows = people["participants"][0], []
        people["participants"] = []
        for index in range(8):
            person = copy.deepcopy(base)
            person["id"] = f"invented-{index:02d}"
            people["participants"].append(person)
            rows.extend(
                [
                    [person["id"], v, "meal-01", t, 5.5, "observed", 0.2, "observed"]
                    for v in ("before", "after")
                    for t in (0, 30, 60, 90, 120)
                ]
            )
        inputs = self.root / "long-input"
        inputs.mkdir()
        (inputs / "package.json").write_bytes(encode(people))
        (inputs / "observations.csv").write_bytes(csv_bytes(rows))
        settings = analysis_settings()
        settings["uncertainty"]["draws"] = 1024
        (inputs / "settings.json").write_bytes(encode(settings))
        self.assertTrue(original.is_dir())
        paths = {
            "package": "long-input/package.json",
            "csv": "long-input/observations.csv",
            "settings": "long-input/settings.json",
        }
        _, inspected = self.request("POST", "observations/inspect", paths)
        _, configured = self.request(
            "POST",
            "observations/configurations",
            {
                "package": paths["package"],
                "csv": paths["csv"],
                "settings": inspected["settings"],
                "input_sha256": inspected["input_sha256"],
            },
        )
        _, job = self.request("POST", f"observations/configurations/{configured['id']}/freeze", {})
        self.assertEqual(self.wait(job)["state"], "completed")
        _, job = self.request("POST", f"observations/configurations/{configured['id']}/run", {})
        entry = self.service.observations.get(job["observation_entry_id"])
        execution = self.service.observations.folder(entry) / "archive/execution.json"
        deadline, phase = time.monotonic() + 10, None
        while self.service.active and time.monotonic() < deadline:
            try:
                phase = json.loads(execution.read_text())["phase"]
            except (OSError, ValueError, KeyError):
                pass
            if phase == "analysis":
                break
            time.sleep(0.005)
        self.assertEqual(phase, "analysis")
        self.assertEqual(self.service.observations.get(entry["id"])["state"], "running")
        self.assertEqual(self.request("POST", "observations/example", {"case": "increase"})[0], 400)
        self.assertEqual(self.request("POST", "m3/fixture", {})[0], 400)
        status, _ = self.request("POST", f"jobs/{job['id']}/cancel", {})
        self.assertEqual(status, 202)
        final = self.wait(job)
        self.assertEqual(final["state"], "cancelled", final)
        report = self.service.observations.report(entry["id"])["native_report"]
        self.assertEqual(report["execution_status"], "interrupted")
        self.assertEqual(report["coverage"]["planned_people"], 8)
        self.assertEqual(len(report["unavailable_participants"]), 8)
        self.assertFalse(report["coverage"]["complete_cohort"])
        self.assertIsNone(self.service.active)
        for observed in final.get("owned_processes", []):
            if isinstance(observed, dict) and isinstance(observed.get("pid"), int):
                with self.assertRaises(ProcessLookupError):
                    os.kill(observed["pid"], 0)

    def test_report_tampering_withdraws_downloads_and_restored_bytes_can_be_rechecked(self):
        _, entry = self.execute(self.configure())
        archive = self.service.observations.folder(entry) / "archive"
        original = (archive / "report.json").read_bytes()
        for mutation in ("count", "label", "interval"):
            report = json.loads(original)
            variant = report["people"]["invented-01"]["variants"]["nominal"]
            if mutation == "count":
                variant["completed_draws"] = "128"
            elif mutation == "label":
                report["people"]["invented-01"]["classification"] = "assumption-dependent"
            else:
                variant["conditional_interval_pmol"] = [2, 1]
            with self.assertRaises(ValueError):
                validate_report(report)
        (archive / "report.json").write_bytes(original + b"\n")
        self.assertEqual(self.request("GET", f"observations/entries/{entry['id']}/report")[0], 400)
        self.assertEqual(
            self.request("GET", f"observations/entries/{entry['id']}/artifacts/report.md")[0], 400
        )
        (archive / "report.json").write_bytes(original)
        _, job = self.request("POST", f"observations/entries/{entry['id']}/reconstruct", {})
        self.assertEqual(self.wait(job)["state"], "completed")
        self.assertEqual(self.request("GET", f"observations/entries/{entry['id']}/report")[0], 200)
        restored = Observations(self.service)
        self.assertEqual(restored.get(entry["id"])["verification"], "recorded_verification")

    def test_invalid_csv_freeze_retains_every_declared_visit_and_actionable_errors(self):
        folder = self.root / "invalid-input"
        folder.mkdir()
        (folder / "package.json").write_bytes(encode(package()))
        # A duplicated actual time is invalid; the other visit must remain visible.
        raw = csv_bytes()
        (folder / "observations.csv").write_bytes(raw + raw.splitlines(keepends=True)[1])
        (folder / "settings.json").write_bytes(encode(analysis_settings()))
        paths = {
            "package": "invalid-input/package.json",
            "csv": "invalid-input/observations.csv",
            "settings": "invalid-input/settings.json",
        }
        _, inspected = self.request("POST", "observations/inspect", paths)
        self.assertFalse(inspected["validation"]["valid"])
        self.assertEqual(len(inspected["validation"]["visits"]), 2)
        _, config = self.request(
            "POST",
            "observations/configurations",
            {
                "package": paths["package"],
                "csv": paths["csv"],
                "settings": inspected["settings"],
                "input_sha256": inspected["input_sha256"],
            },
        )
        _, job = self.request("POST", f"observations/configurations/{config['id']}/freeze", {})
        self.assertEqual(self.wait(job)["state"], "failed")
        config = self.service.observations.get_configuration(config["id"])
        self.assertFalse(config["ready"])
        self.assertEqual(len(config["validation"]["visits"]), 2)
        self.assertTrue(any(v["errors"] for v in config["validation"]["visits"]))
        self.assertTrue(
            (self.service.observations.folder(config) / "validation/manifest.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
