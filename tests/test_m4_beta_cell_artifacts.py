"""Hand-calculable archive fixtures; no simulator, solver or numerical imports."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.m4.beta_cell.runtime import report


def table(path, columns, rows):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def verification_fixture():
    """Explicit synthetic measurements for the archived-check contract."""
    checks = {name: {"passed": True} for name in report.REQUIRED_CHECKS}
    for name, field in (
        ("solver_sensitivity", "tight_reference_max_sr_error_ug_per_min"),
        ("deterministic_repeat", "maximum_absolute_state_error"),
        ("capacity_linearity", "maximum_absolute_state_error"),
        ("zero_capacity", "maximum_absolute_state"),
        ("basal_threshold", "maximum_absolute_state"),
        ("glucose_conversion", "maximum_absolute_state_error"),
        ("initialization", "independent_expression_absolute_error"),
        ("capacity_amplitude_confounding", "maximum_absolute_state_difference"),
    ):
        checks[name][field] = 0.0
    checks["constant_forcing_closed_form"]["maximum_absolute_state_errors"] = {
        "distinct_rates": 0.0,
        "equal_rates": 0.0,
        "nearly_equal_rates": 0.0,
    }
    checks["positivity"]["minimum_state"] = 0.0
    checks["published_algebraic_relationships"].update(
        maximum_independent_expression_error=0.0,
        asymptote_absolute_error=0.0,
        minimum_grid_delay_min=12.5,
        maximum_grid_delay_min=12.5,
    )
    checks["glucose_conversion"]["anchor_90_mg_dl_in_mmol_l"] = 5.0
    checks["invalid_input_rejection"].update(attempted=10, rejected=10)
    return {
        "passed": True,
        "checks": checks,
        "sensitivity": {
            "m": {"minus_auc_ug": 3.0, "plus_auc_ug": 3.0, "normalized_central_sensitivity": 0.0},
        },
        "baseline_auc_ug": 3.0,
        "evidence_scope": "synthetic archive-contract fixture only",
        "human_validation": "not performed",
        "published_dynamic_figure_reproduction": "not performed",
    }


def fixture(directory):
    """A synthetic archive-contract fixture, not a claimed solution of BC-001."""
    directory.mkdir()
    protocol = {
        "schema": "m4-beta-cell-protocol/1",
        "id": "synthetic-archive-fixture",
        "claim": "hand-calculable reader fixture; no numerical execution",
        "horizon_min": 2,
        "sample_step_min": 1,
        "parameters": {"m": 0.5},
        "capacity_values": [0, 0.25, 0.5, 1],
        "reference_glucose_grid": {"start": 0, "stop": 2, "step": 1},
        "criteria": {
            "max_solver_secretion_error_ug_per_min": 1e-6,
            "capacity_linearity_error": 1e-8,
            "negative_state_tolerance": 1e-9,
            "repeat_absolute_error": 0,
            "constant_input_closed_form_error": 1e-6,
            "reference_grid_absolute_error": 1e-12,
            "published_delay_min_bounds": [12, 12.6],
        },
        "sensitivity": {"parameters": ["m"]},
        "empirical_evaluation": "not performed in fixture",
        "published_dynamic_figure_reproduction": "not performed in fixture",
    }
    report.dump(directory / "protocol.json", protocol)
    table(directory / "input.csv", ("time_min", "glucose_mmol_per_L"), [(0, 9), (1, 8), (2, 7)])
    table(
        directory / "trace.csv",
        report.TRACE_COLUMNS,
        [
            [
                t,
                glucose,
                secretion * 2,
                0,
                secretion,
                secretion,
                secretion,
                0,
                secretion / 4,
                secretion / 2,
                secretion,
                secretion * 3,
            ]
            for t, glucose, secretion in [(0, 9, 1), (1, 8, 2), (2, 7, 1)]
        ],
    )
    table(
        directory / "reference-functions.csv",
        ("glucose_mmol_per_L", "rho_per_min", "y_infinity_ug_per_min", "delay_min"),
        [(0, 0.08, 0, 12.5), (1, 0.08, 1, 12.5), (2, 0.08, 2, 12.5)],
    )
    report.dump(directory / "verification.json", verification_fixture())
    report.dump(directory / "report.json", {"fixture": "synthetic archived report"})
    (directory / "figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
    for name in report.SOURCE_FILES:
        # Reader must hash these bytes, not import/execute archived source.
        (directory / f"source-{name}").write_text(
            "raise RuntimeError('synthetic archived source must never execute')\n"
        )
    report.dump(
        directory / "manifest.json",
        {
            "schema": "m4-beta-cell-run/1",
            "status": "completed",
            "source_identity": "synthetic fixture only",
            "files": {path.name: report.sha256(path) for path in sorted(directory.iterdir())},
        },
    )


class BetaCellArtifacts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run"
        fixture(self.run)

    def manifest(self, update):
        path = self.run / "manifest.json"
        value = json.loads(path.read_text())
        update(value)
        report.dump(path, value)

    def rehash(self, name):
        self.manifest(lambda value: value["files"].update({name: report.sha256(self.run / name)}))

    def edit_verification(self, update):
        path = self.run / "verification.json"
        value = json.loads(path.read_text())
        update(value)
        report.dump(path, value)
        self.rehash("verification.json")

    def edit_rows(self, name, update, *, rehash=True):
        path = self.run / name
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        update(rows)
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        if rehash:
            self.rehash(name)

    def test_metrics_are_independently_hand_calculable(self):
        result = report.reconstruct(self.run)
        self.assertTrue(result["passed"])
        self.assertEqual(result["time_points"], 3)
        self.assertEqual(result["trapezoid_evoked_secretion_auc_ug"], 3)
        self.assertEqual(result["sampled_peak_evoked_secretion_ug_per_min"], 2)
        self.assertEqual(result["sampled_peak_time_min"], 1)
        self.assertEqual(result["reference_delay_range_min"], [12.5, 12.5])

    def test_reader_runs_without_site_packages_and_does_not_execute_archive(self):
        output = self.root / "reconstructed.json"
        command = [
            sys.executable,
            "-S",
            str(Path(report.__file__)),
            str(self.run),
            "--output",
            str(output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(output.read_text()), report.reconstruct(self.run))
        original = output.read_bytes()
        repeated = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_missing_trace_is_not_zero_secretion(self):
        (self.run / "trace.csv").unlink()
        with self.assertRaisesRegex(ValueError, "Invalid/missing local artifact"):
            report.reconstruct(self.run)

    def test_manifest_cannot_omit_required_trace(self):
        self.manifest(lambda value: value["files"].pop("trace.csv"))
        with self.assertRaisesRegex(ValueError, "omits required"):
            report.reconstruct(self.run)

    def test_completed_archive_requires_final_report_and_figure_files(self):
        for name in ("report.json", "figure.svg"):
            with self.subTest(name=name):
                path = self.run / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Invalid/missing local artifact"):
                    report.reconstruct(self.run)
                path.write_bytes(original)

    def test_completed_manifest_requires_final_report_and_figure_hashes(self):
        original = (self.run / "manifest.json").read_bytes()
        for name in ("report.json", "figure.svg"):
            with self.subTest(name=name):
                (self.run / "manifest.json").write_bytes(original)
                self.manifest(lambda value: value["files"].pop(name))
                with self.assertRaisesRegex(ValueError, "omits required"):
                    report.reconstruct(self.run)

    def test_calculated_core_is_available_only_to_explicit_finalization(self):
        self.manifest(lambda value: value.update(status="calculated"))
        for name in ("report.json", "figure.svg"):
            (self.run / name).unlink()
            self.manifest(lambda value: value["files"].pop(name))
        with self.assertRaisesRegex(ValueError, "complete BC-001 manifest"):
            report.reconstruct(self.run)
        self.assertTrue(report.reconstruct(self.run, allow_pending=True)["passed"])

    def test_changed_trace_without_rehash_is_detected(self):
        self.edit_rows("trace.csv", lambda rows: rows[1].__setitem__(4, "42"), rehash=False)
        with self.assertRaisesRegex(ValueError, "Changed artifact: trace.csv"):
            report.reconstruct(self.run)

    def test_removing_same_interior_sample_from_both_tables_and_rehashing_fails(self):
        for name in ("trace.csv", "input.csv"):
            self.edit_rows(name, lambda rows: rows.pop(2))
        with self.assertRaisesRegex(ValueError, "Incomplete output grid"):
            report.reconstruct(self.run)

    def test_rehashed_duplicate_time_fails_even_when_input_agrees(self):
        for name in ("trace.csv", "input.csv"):
            self.edit_rows(name, lambda rows: rows[2].__setitem__(0, "0"))
        with self.assertRaisesRegex(ValueError, "Invalid output time grid"):
            report.reconstruct(self.run)

    def test_rehashed_input_output_disagreement_fails(self):
        self.edit_rows("input.csv", lambda rows: rows[2].__setitem__(1, "8.25"))
        with self.assertRaisesRegex(ValueError, "Input/output glucose differs"):
            report.reconstruct(self.run)

    def test_rehashed_reference_truncation_fails(self):
        self.edit_rows("reference-functions.csv", lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, "Incomplete published-function grid"):
            report.reconstruct(self.run)

    def test_rehashed_reference_grid_shift_fails(self):
        self.edit_rows("reference-functions.csv", lambda rows: rows[2].__setitem__(0, "1.2"))
        with self.assertRaisesRegex(ValueError, "Invalid published-function grid"):
            report.reconstruct(self.run)

    def test_rehashed_reciprocal_delay_error_fails(self):
        self.edit_rows("reference-functions.csv", lambda rows: rows[2].__setitem__(3, "13"))
        with self.assertRaisesRegex(ValueError, "Invalid delay"):
            report.reconstruct(self.run)

    def test_rehashed_consistent_reciprocal_cannot_hide_impossible_delay(self):
        def impossible_delay(rows):
            rows[2][1] = "0.01"
            rows[2][3] = "100"

        self.edit_rows("reference-functions.csv", impossible_delay)
        with self.assertRaisesRegex(ValueError, "Invalid published-function range"):
            report.reconstruct(self.run)

    def test_rehashed_negative_provision_is_rejected(self):
        self.edit_rows("reference-functions.csv", lambda rows: rows[2].__setitem__(2, "-0.1"))
        with self.assertRaisesRegex(ValueError, "Invalid published-function range"):
            report.reconstruct(self.run)

    def test_failed_and_incomplete_attempts_cannot_be_reported_as_complete(self):
        for status in ("failed", "started", "calculated", "interrupted", "terminated"):
            with self.subTest(status=status):
                self.manifest(lambda value: value.update(status=status))
                with self.assertRaisesRegex(ValueError, "complete BC-001 manifest"):
                    report.reconstruct(self.run)

    def test_archived_source_corruption_is_detected(self):
        path = self.run / "source-model.py"
        path.write_text("changed model\n")
        with self.assertRaisesRegex(ValueError, "Changed artifact: source-model.py"):
            report.reconstruct(self.run)

    def test_archived_source_cannot_be_omitted(self):
        self.manifest(lambda value: value["files"].pop("source-model.py"))
        with self.assertRaisesRegex(ValueError, "omits required"):
            report.reconstruct(self.run)

    def test_artifact_path_escape_is_rejected(self):
        original = (self.run / "manifest.json").read_bytes()
        for name in (
            "../source-model.py",
            str(self.root / "source-model.py"),
            "nested/source-model.py",
        ):
            with self.subTest(name=name):
                (self.run / "manifest.json").write_bytes(original)
                self.manifest(lambda value: value["files"].update({name: "0" * 64}))
                with self.assertRaisesRegex(ValueError, "Invalid/missing local artifact"):
                    report.reconstruct(self.run)

    def test_source_symlink_is_rejected_even_with_matching_content(self):
        path = self.run / "source-model.py"
        outside = self.root / "source-model.py"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Invalid/missing local artifact"):
            report.reconstruct(self.run)

    def test_rehashed_failed_verification_remains_failed(self):
        self.edit_verification(lambda value: value.update(passed=False))
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_archived_checks_cannot_be_omitted_even_with_passing_summary(self):
        self.edit_verification(lambda value: value["checks"].pop("zero_capacity"))
        with self.assertRaisesRegex(ValueError, "Missing or unexpected verification checks"):
            report.reconstruct(self.run)

    def test_archived_failed_check_overrides_passing_summary(self):
        self.edit_verification(lambda value: value["checks"]["zero_capacity"].update(passed=False))
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_archived_measurement_overrides_passing_flags(self):
        self.edit_verification(
            lambda value: value["checks"]["deterministic_repeat"].update(
                maximum_absolute_state_error=0.1,
            )
        )
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_archived_missing_measurement_is_rejected(self):
        self.edit_verification(
            lambda value: value["checks"]["deterministic_repeat"].pop(
                "maximum_absolute_state_error",
            )
        )
        with self.assertRaisesRegex(ValueError, "Incomplete verification measurements"):
            report.reconstruct(self.run)

    def test_archived_boolean_is_not_a_zero_error_measurement(self):
        self.edit_verification(
            lambda value: value["checks"]["deterministic_repeat"].update(
                maximum_absolute_state_error=False,
            )
        )
        with self.assertRaisesRegex(ValueError, "Boolean used as verification measurement"):
            report.reconstruct(self.run)

    def test_archived_sensitivity_cannot_disappear(self):
        self.edit_verification(lambda value: value["sensitivity"].clear())
        with self.assertRaisesRegex(ValueError, "Missing sensitivity cases"):
            report.reconstruct(self.run)

    def test_numerical_mismatches_cannot_be_hidden_by_a_passing_verification_flag(self):
        original = (self.run / "trace.csv").read_bytes()
        for field, changed in (
            ("tight_ug_per_min", "1.01"),
            ("capacity_0.25_ug_per_min", "0.75"),
            ("x_ug", "20"),
        ):
            with self.subTest(field=field):
                (self.run / "trace.csv").write_bytes(original)
                self.edit_rows(
                    "trace.csv",
                    lambda rows: rows[1].__setitem__(report.TRACE_COLUMNS.index(field), changed),
                )
                self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_rehashed_nonfinite_trace_is_rejected(self):
        self.edit_rows("trace.csv", lambda rows: rows[1].__setitem__(3, "nan"))
        with self.assertRaisesRegex(ValueError, "Missing/nonfinite"):
            report.reconstruct(self.run)


if __name__ == "__main__":
    unittest.main()
