"""Real synthetic sampling HTTP, native-reader and owned-process verification."""

import copy
import csv
import io
import json
import shutil
import time
import unittest

from experiments.gui.library_sampling import validate_report
from experiments.gui.service import ROOT, Service, inventory
from tests import test_gui_observations as gui_tests


class SamplingGUITests(unittest.TestCase):
    setUp = gui_tests.ObservationGUITests.setUp
    tearDown = gui_tests.ObservationGUITests.tearDown
    request = gui_tests.ObservationGUITests.request
    wait = gui_tests.ObservationGUITests.wait

    def configure(self, case="information-loss", draws=32, poison=False, display_name=None):
        for name in (
            "0068-synthetic-observation-analysis-contract.md",
            "0069-mmtt-sampling-reuse.md",
        ):
            shutil.copyfile(ROOT / "docs/decisions" / name, self.root / "docs/decisions" / name)
        status, job = self.request("POST", "sampling/example", {"case": case})
        self.assertEqual(status, 202, job)
        prepared = self.wait(job)
        self.assertEqual(prepared["state"], "completed", prepared)
        paths = prepared["result"]["input_paths"]
        if poison:
            path = self.root / paths["csv"]
            rows = list(csv.DictReader(io.StringIO(path.read_text())))
            for row in rows:
                if row["participant_id"] == "invented-evaluation-01" and row["time_min"] == "15":
                    row["cpeptide_nmol_l"] = "poisoned-omitted-cell"
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            path.write_text(stream.getvalue())
        status, inspected = self.request("POST", "sampling/inspect", paths)
        self.assertEqual(status, 201, inspected)
        self.assertEqual(inspected["display_name"], prepared["result"]["display_name"])
        settings = copy.deepcopy(inspected["settings"])
        settings["uncertainty"]["draws"] = draws
        body = {**paths, "settings": settings, "input_sha256": inspected["input_sha256"]}
        if display_name is not None:
            body["display_name"] = display_name
        status, config = self.request("POST", "sampling/configurations", body)
        self.assertEqual(status, 201, config)
        status, job = self.request("POST", f"sampling/configurations/{config['id']}/freeze", {})
        self.assertEqual(status, 202, job)
        frozen = self.wait(job)
        self.assertEqual(frozen["state"], "completed", frozen)
        return self.service.sampling.get_configuration(config["id"])

    def execute(self, config):
        status, job = self.request("POST", f"sampling/configurations/{config['id']}/run", {})
        self.assertEqual(status, 202, job)
        completed = self.wait(job)
        return completed, self.service.sampling.get(completed["sampling_entry_id"])

    def test_four_controls_actual_reports_reconstruction_and_library(self):
        names = {
            "constant": "Constant control",
            "information-loss": "Constructed direction reversal",
            "incomplete": "Low / censored control",
            "steep-response": "Boundary failure control",
        }
        for case in ("constant", "information-loss", "incomplete", "steep-response"):
            with self.subTest(case=case):
                config = self.configure(case)
                job, entry = self.execute(config)
                self.assertEqual(config["display_name"], names[case])
                self.assertEqual(entry["display_name"], names[case])
                self.assertEqual(
                    entry["report_completeness"],
                    "complete" if case in ("constant", "information-loss") else "incomplete",
                    job,
                )
                status, wrapper = self.request("GET", f"sampling/entries/{entry['id']}/report")
                self.assertEqual(status, 200, wrapper)
                report = validate_report(wrapper["native_report"])
                self.assertEqual(report["coverage"]["planned_variant_pairs"], 60)
                self.assertEqual(len(report["visit_comparisons"]), 90)
                if case == "information-loss":
                    self.assertEqual(
                        report["comparisons"]["evaluation"]["three-times"]["nominal"]["directions"][
                            "direction_reversal"
                        ],
                        3,
                    )
                archive = self.service.sampling.folder(entry) / "archive"
                before = inventory(archive)
                status, checking = self.request(
                    "POST", f"sampling/entries/{entry['id']}/reconstruct", {}
                )
                self.assertEqual(status, 202, checking)
                self.assertEqual(self.wait(checking)["verification"], "native_reader_verified")
                for name in ("report.json", "report.md"):
                    status, raw = self.request(
                        "GET", f"sampling/entries/{entry['id']}/artifacts/{name}", raw=True
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(raw, (archive / name).read_bytes())
                exported = self.root / "exports" / case
                exported.parent.mkdir(exist_ok=True)
                shutil.copytree(archive, exported)
                indexed = self.wait(
                    self.service.add_archive(
                        {
                            "root_id": self.service.library.roots()[0]["id"],
                            "task": "mmtt-sampling",
                            "path": "exports/" + case,
                        }
                    )
                )
                self.assertEqual(indexed["state"], "completed", indexed)
                ident = indexed["request"]["entry"]["id"]
                checked = self.wait(self.service.verify_archive(ident))
                self.assertEqual(checked["verification"], "native_reader_verified", checked)
                self.assertEqual(self.service.library.report(ident)["native_report"], report)
                self.assertEqual(inventory(archive), before)

    def test_invalid_full_analyte_does_not_block_valid_reduced_children(self):
        config = self.configure(poison=True)
        self.assertFalse(config["validation"]["valid"])
        _, entry = self.execute(config)
        report = self.service.sampling.report(entry["id"])["native_report"]
        self.assertFalse(report["schedules"]["full"]["report"]["coverage"]["complete_cohort"])
        for name in ("five-times", "four-times", "three-times"):
            self.assertTrue(report["schedules"][name]["report"]["coverage"]["complete_cohort"])

    def test_selection_changed_inputs_and_task_crossing_are_refused(self):
        config = self.configure()
        paths = config["input_paths"]
        status, inspected = self.request("POST", "sampling/inspect", paths)
        self.assertEqual(status, 201, inspected)
        design_path = self.root / paths["design"]
        design = json.loads(design_path.read_text())
        design["selection_rationale"] += " Changed after inspection."
        design_path.write_text(json.dumps(design))
        body = {
            **paths,
            "settings": inspected["settings"],
            "input_sha256": inspected["input_sha256"],
        }
        status, error = self.request("POST", "sampling/configurations", body)
        self.assertEqual(status, 400, error)
        design["selection_participants"] = ["invented-evaluation-01"]
        design_path.write_text(json.dumps(design))
        self.assertEqual(self.request("POST", "sampling/inspect", paths)[0], 400)
        self.assertEqual(
            self.request("POST", f"observations/configurations/{config['id']}/run", {})[0], 400
        )
        self.assertEqual(self.request("GET", "sampling/bootstrap", token=False)[0], 403)

    def test_edit_saved_plan_with_frozen_fingerprints_keeps_original_and_checks_changed_bytes(self):
        config = self.configure("constant", display_name="First comparison")
        frozen = inventory(self.service.sampling.folder(config) / "frozen")
        settings = copy.deepcopy(config["settings"])
        settings["variants"][0]["volume_l"] = 9.17
        body = {
            **config["input_paths"],
            "settings": settings,
            "display_name": "Changed volume",
            "input_sha256": {
                **{
                    key: config["inputs_sha256"][key]
                    for key in ("package.json", "observations.csv", "design.json")
                },
                "development_import": config["development_identity"],
            },
        }
        status, edited = self.request("POST", "sampling/configurations", body)
        self.assertEqual(status, 201, edited)
        self.assertEqual(edited["display_name"], "Changed volume")
        status, job = self.request("POST", f"sampling/configurations/{edited['id']}/freeze", {})
        self.assertEqual(status, 202, job)
        self.assertEqual(self.wait(job)["state"], "completed")
        self.assertEqual(edited["settings"]["variants"][0]["volume_l"], 9.17)
        self.assertEqual(self.service.sampling.get_configuration(config["id"]), config)
        self.assertEqual(inventory(self.service.sampling.folder(config) / "frozen"), frozen)
        design = self.root / config["input_paths"]["design"]
        design.write_bytes(design.read_bytes() + b"\n")
        status, refused = self.request("POST", "sampling/configurations", body)
        self.assertEqual(status, 400, refused)
        self.assertIn("bytes changed", refused["error"])

    def test_cancel_preserves_all_denominators_and_reconstructs(self):
        config = self.configure(draws=1024)
        status, job = self.request("POST", f"sampling/configurations/{config['id']}/run", {})
        self.assertEqual(status, 202)
        entry = self.service.sampling.get(job["sampling_entry_id"])
        phase = self.service.sampling.folder(entry) / "archive/studies/full/execution.json"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if phase.is_file() and json.loads(phase.read_text()).get("phase") == "analysis":
                break
            time.sleep(0.01)
        else:
            self.fail("Native analysis phase not observed")
        self.assertEqual(self.request("POST", "observations/example", {"case": "increase"})[0], 400)
        self.service.cancel(job["id"])
        final = self.wait(job)
        self.assertEqual(final["state"], "cancelled", final)
        entry = self.service.sampling.get(entry["id"])
        report = self.service.sampling.report(entry["id"])["native_report"]
        self.assertEqual(report["execution_status"], "interrupted")
        self.assertEqual(report["coverage"]["planned_variant_pairs"], 60)
        self.assertGreater(report["coverage"]["not_attempted_draw_pairs"], 0)
        status, checking = self.request("POST", f"sampling/entries/{entry['id']}/reconstruct", {})
        self.assertEqual(status, 202, checking)
        self.assertEqual(self.wait(checking)["verification"], "native_reader_verified")

    def test_restarted_manager_retains_both_task_histories(self):
        config = self.configure("constant", display_name="My reduced-schedule comparison")
        job, entry = self.execute(config)
        self.assertNotIn("display_name", job["request"])
        self.service.close()
        restored = Service(self.root, python=self.service.python)
        try:
            self.assertIn(job["id"], restored.jobs)
            self.assertEqual(
                restored.sampling.get(entry["id"])["plan_identity"], config["plan_identity"]
            )
            self.assertEqual(
                restored.sampling.get(entry["id"])["display_name"], "My reduced-schedule comparison"
            )
            self.assertEqual(
                restored.sampling.get_configuration(config["id"])["display_name"],
                "My reduced-schedule comparison",
            )
            self.assertEqual(
                restored.sampling.inspect(config["input_paths"])["display_name"],
                "My reduced-schedule comparison",
            )
        finally:
            restored.close()
