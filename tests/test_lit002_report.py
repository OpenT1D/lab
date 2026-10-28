"""Artifact reconstruction must retain failures and detect altered evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lit002_report_tested", ROOT / "experiments/literature/lit002/report.py"
)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def reseal(study: Path) -> None:
    manifest = json.loads((study / "manifest.json").read_text())
    manifest["artifacts"] = {
        str(path.relative_to(study)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(study.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    dump(study / "manifest.json", manifest)


def fixture(study: Path) -> dict:
    """Small constant traces test reporting boundaries, not physiological behavior."""
    protocol = json.loads((ROOT / "experiments/literature/lit002/protocol.json").read_text())
    protocol["horizon_min"] = 2
    for scenario in protocol["scenarios"]:
        scenario["insulin_segments"], scenario["meals"] = [], []
    dump(study / "protocol.json", protocol)
    source_target = study / "source/experiments/literature/lit001/parameters.json"
    source_target.parent.mkdir(parents=True)
    source_target.write_bytes((ROOT / "experiments/literature/lit001/parameters.json").read_bytes())
    (study / "impulse.csv").write_text("fixture only; no impulse metrics used in report\n")
    dump(study / "impulse_metrics.json", {"fixture": True})
    cases = []
    for scenario in protocol["scenarios"]:
        for arm in protocol["arms"]:
            for resolution, step in (
                ("standard", protocol["max_step_min"]),
                ("refined", protocol["refinement_max_step_min"]),
            ):
                case_id = f"{scenario['id']}-{arm}-{resolution}"
                prefix = study / "cases" / case_id
                cases.append(
                    {
                        "id": case_id,
                        "scenario": scenario["id"],
                        "arm": arm,
                        "resolution": resolution,
                        "max_step_min": step,
                        "status": "completed",
                        "path": f"cases/{case_id}",
                        "error": None,
                    }
                )
                config = {key: protocol[key] for key in REPORT.CONFIG_SHARED}
                config.update(arm=arm, max_step_min=step, insulin_segments=[], meals=[])
                dump(prefix / "config.json", config)
                a = protocol["absorption"]
                mean = (
                    a["tau_min"]
                    + 1 / (a["ka1_per_min"] + a["kd_per_min"])
                    + a["kd_per_min"] / (a["ka1_per_min"] + a["kd_per_min"]) / a["ka2_per_min"]
                )
                tmax = mean / 2 if arm == "cambridge_mean_matched" else 55
                first = second = (1000 / 60) * tmax
                delay = a["tau_min"] if arm == "faggionato_sc" else 0
                if delay:
                    first = (1000 / 60) / (a["ka1_per_min"] + a["kd_per_min"])
                    second = a["kd_per_min"] * first / a["ka2_per_min"]
                dump(
                    prefix / "runtime.json",
                    {
                        "upstream_revision": protocol["native_revision"],
                        "node": protocol["node_version"],
                        "source_sha256": {"fixture_source": "0" * 64},
                        "settings": {
                            "arm": arm,
                            "basal_u_h": 1,
                            "native_parameters": {"BW": 70, "VI": 0.12, "ke": 0.138, "tmaxI": tmax},
                        },
                    },
                )
                rows = []
                for minute in (0, 1, 2):
                    state = {
                        "Q1": 100,
                        "Q2": 100,
                        "S1": first,
                        "S2": second,
                        "I": 10,
                        "x1": 0.1,
                        "x2": 0.1,
                        "x3": 0.1,
                        "D1": 0,
                        "D2": 0,
                    }
                    rows.append(
                        {
                            "time_min": minute,
                            "glucose_mg_dl": protocol["equilibrium_glucose_mg_dl"],
                            "insulin_mU_L": 10,
                            "appearance_mU_min": 1000 / 60,
                            "delivered_u_h": 1,
                            "delayed_delivered_u_h": 1,
                            "intake_g_min": 0,
                            "depot_mU": first + second,
                            "delay_queue_mU": delay * 1000 / 60,
                            "total_subcutaneous_mU": first + second + delay * 1000 / 60,
                            "cumulative_delivered_mU": minute * 1000 / 60,
                            "cumulative_delayed_delivered_mU": minute * 1000 / 60,
                            "cumulative_carbohydrates_g": 0,
                            "balance_derived_absorbed_mU": minute * 1000 / 60,
                            "state": state,
                        }
                    )
                (prefix / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
                dump(prefix / "result.json", {"status": "completed", "rows": 3, "final_minute": 2})
                dump(
                    prefix / "verification.json",
                    {
                        "checks": {"external_verification": True},
                        "max_sc_state_error_mU_per_kg": 0,
                        "max_appearance_error_mU_per_kg_min": 0,
                        "max_mass_residual_mU_per_kg": 0,
                    },
                )
    dump(
        study / "manifest.json",
        {
            "schema": "lit002-study/1",
            "status": "completed",
            "expected_case_count": 18,
            "cases": cases,
            "protocol_sha256": hashlib.sha256((study / "protocol.json").read_bytes()).hexdigest(),
        },
    )
    reseal(study)
    return protocol


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.study = Path(self.temp.name) / "study"
        self.protocol = fixture(self.study)

    def tearDown(self):
        self.temp.cleanup()

    def edit_trace(self, case: str, change) -> None:
        path = self.study / "cases" / case / "trace.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        change(rows)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def test_complete_reconstruction_is_deterministic_and_outputs_are_new(self):
        one, two = Path(self.temp.name) / "one", Path(self.temp.name) / "two"
        result = REPORT.write_report(self.study, one)
        self.assertTrue(result["all_passed"])
        self.assertEqual(result["completed_cases"], 18)
        self.assertEqual(len(result["comparisons"]), 18)
        self.assertEqual(len(result["contrast_refinements"]), 9)
        REPORT.write_report(self.study, two)
        self.assertEqual((one / "report.json").read_bytes(), (two / "report.json").read_bytes())
        with self.assertRaises(FileExistsError):
            REPORT.write_report(self.study, one)

    def test_changed_trace_is_rejected_before_metrics(self):
        self.edit_trace(
            "pulse-cambridge_native-standard", lambda rows: rows[1].update(glucose_mg_dl=200)
        )
        with self.assertRaisesRegex(ValueError, "changed artifact"):
            REPORT.reconstruct(self.study)

    def test_missing_arm_is_not_silently_dropped(self):
        manifest = json.loads((self.study / "manifest.json").read_text())
        manifest["cases"].pop()
        dump(self.study / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "case matrix"):
            REPORT.reconstruct(self.study)

    def test_declared_failed_case_remains_and_disables_affected_comparisons(self):
        manifest = json.loads((self.study / "manifest.json").read_text())
        case = manifest["cases"][-1]
        case.update(status="failed", error="Synthetic worker stop")
        manifest["status"] = "completed_with_failures"
        dump(self.study / "manifest.json", manifest)
        result = REPORT.reconstruct(self.study)
        self.assertFalse(result["all_passed"])
        self.assertEqual(result["failed_cases"], 1)
        self.assertEqual(result["completed_cases"], 17)
        self.assertEqual(result["failures"][0]["case_id"], case["id"])
        self.assertTrue(any(item["status"] == "unavailable" for item in result["comparisons"]))

    def test_refinement_failure_is_reported_even_if_worker_verification_passes(self):
        self.edit_trace(
            "pulse-faggionato_sc-refined", lambda rows: rows[1].update(glucose_mg_dl=125.5)
        )
        reseal(self.study)
        result = REPORT.reconstruct(self.study)
        self.assertFalse(result["all_passed"])
        self.assertFalse(result["checks"]["refinement:pulse:faggionato_sc"])
        self.assertFalse(
            result["checks"]["contrast_refinement:pulse:faggionato_sc:cambridge_native"]
        )

    def test_contrast_refinement_checked_separately_from_individual_curves(self):
        for arm, delta in (("cambridge_native", -0.075), ("faggionato_sc", 0.075)):

            def change(rows, delta=delta):
                rows[1]["glucose_mg_dl"] += delta

            self.edit_trace(f"pulse-{arm}-refined", change)
        reseal(self.study)
        result = REPORT.reconstruct(self.study)
        self.assertTrue(result["checks"]["refinement:pulse:cambridge_native"])
        self.assertTrue(result["checks"]["refinement:pulse:faggionato_sc"])
        self.assertFalse(
            result["checks"]["contrast_refinement:pulse:faggionato_sc:cambridge_native"]
        )

    def test_equal_but_wrong_input_in_all_arms_is_rejected_by_schedule_check(self):
        for arm in self.protocol["arms"]:
            self.edit_trace(f"pulse-{arm}-standard", lambda rows: rows[1].update(delivered_u_h=2))
        reseal(self.study)
        result = REPORT.reconstruct(self.study)
        self.assertFalse(result["checks"]["pulse-cambridge_native-standard:frozen_input_schedule"])
        self.assertFalse(result["all_passed"])

    def test_preparation_failure_keeps_all_eighteen_cases_without_impulse(self):
        manifest = json.loads((self.study / "manifest.json").read_text())
        for case in manifest["cases"]:
            case.update(status="failed", error="Preparation failed before native execution")
        manifest.update(
            status="completed_with_failures", preparation_error="Fixture preparation stop"
        )
        dump(self.study / "manifest.json", manifest)
        (self.study / "impulse.csv").unlink()
        (self.study / "impulse_metrics.json").unlink()
        reseal(self.study)
        result = REPORT.reconstruct(self.study)
        self.assertEqual(result["failed_cases"], 18)
        self.assertEqual(result["completed_cases"], 0)
        self.assertFalse(result["all_passed"])
        self.assertTrue(all(item["status"] == "unavailable" for item in result["comparisons"]))

    def test_source_parameter_snapshot_must_match_frozen_hash(self):
        source = self.study / "source/experiments/literature/lit001/parameters.json"
        source.write_text(source.read_text() + " ")
        reseal(self.study)
        with self.assertRaisesRegex(ValueError, "Source parameter snapshot"):
            REPORT.reconstruct(self.study)

    def test_nonfinite_complete_trace_is_rejected(self):
        self.edit_trace(
            "pulse-cambridge_native-standard",
            lambda rows: rows[1].update(glucose_mg_dl=float("nan")),
        )
        reseal(self.study)
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            REPORT.reconstruct(self.study)

    def test_hash_inventory_path_escape_is_rejected(self):
        manifest = json.loads((self.study / "manifest.json").read_text())
        manifest["artifacts"]["../outside.json"] = "0" * 64
        dump(self.study / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Unsafe artifact path"):
            REPORT.reconstruct(self.study)

    def test_omitted_trace_hash_is_rejected_even_when_file_remains(self):
        manifest = json.loads((self.study / "manifest.json").read_text())
        del manifest["artifacts"]["cases/pulse-cambridge_native-standard/trace.jsonl"]
        dump(self.study / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "absent from hash inventory"):
            REPORT.reconstruct(self.study)


if __name__ == "__main__":
    unittest.main()
