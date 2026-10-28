"""Hand-calculable BC-002 archives; no numerical runtime or real run is required."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_m4_beta_cell_artifacts import fixture as beta_fixture
from test_m4_beta_cell_artifacts import table

from experiments.m4.kinetic_inlet import report

CHECK_NAMES = (
    "native_zero_extension",
    "primary_oracle_agreement",
    "primary_mass_balance",
    "primary_input_integrals",
    "positivity",
    "repeatability",
    "conversion_anchor",
    "source_oracle_agreement",
    "source_mass_balance",
    "communication_amount",
    "communication_refinement",
    "equal_area_baseline",
    "gain_linearity",
    "zero_gain",
    "route_contrast_resolution",
)
BW = 102.32
VI = 0.054906
FACTOR = 1_000_000 / (5808 * BW)
UPSTREAM = {
    "revision": "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc",
    "profile": "adult#001",
    "patient_file_sha256": "7ad1302fbf064805e2294bbcffd482e55448e37e48b63e629a1ed7f11c701547",
    "parameter_file_sha256": "662f3b684d160fdf485edd1d7196dd1cd85c14b53650b030fdb86aaa05bb2e50",
}


def verification_fixture():
    """Explicit synthetic values for each field in the archived-check contract."""
    checks = {name: {"passed": True} for name in CHECK_NAMES}
    checks["native_zero_extension"].update(
        derivative_max_error=0.0,
        trajectory_max_error=0.0,
        fresh_max_error=0.0,
        reset_max_error=0.0,
        derivative_tolerance=0.0,
        trajectory_tolerance=0.0,
        samples=61,
        states_per_sample=13,
        basal_action_u_min=0.02,
        guarded_probes=30,
        solver_successful=True,
    )
    for name in ("primary_oracle_agreement", "source_oracle_agreement"):
        checks[name].update(
            max_insulin_state_error_pmol_kg=0.0,
            max_plasma_error_pmol_l=0.0,
            state_tolerance_pmol_kg=1e-7,
            plasma_tolerance_pmol_l=1e-6,
            compared_methods=["tight", "reference"],
        )
    for name in (
        "primary_mass_balance",
        "primary_input_integrals",
        "source_mass_balance",
        "communication_amount",
    ):
        checks[name].update(max_error_pmol_kg=0.0, tolerance_pmol_kg=1e-8)
    checks["primary_input_integrals"]["expected_integrals_pmol_kg"] = {
        "zero": 0.0,
        "constant": 100.0,
        "pulse": 20.8,
        "ramp": 100.0,
    }
    checks["positivity"].update(minimum_state_pmol_kg=0.0, negative_tolerance_pmol_kg=1e-9)
    checks["repeatability"].update(max_absolute_state_error=0.0, tolerance=0.0)
    checks["conversion_anchor"].update(
        relative_error=0.0,
        tolerance=1e-12,
        source_microgram_per_min=5.808,
        expected_pmol_per_min=1000.0,
        converted_pmol_kg_min=1000 / BW,
        body_weight_kg=BW,
    )
    checks["communication_refinement"].update(
        routes={
            route: {"finest_error_pmol_l": 0.0001, "fine_to_coarse_error_ratio": 0.1}
            for route in ("liver", "peripheral")
        },
        finest_tolerance_pmol_l=0.01,
        ratio_tolerance=0.35,
    )
    checks["equal_area_baseline"].update(
        max_amount_error_pmol_kg=0.0, total_input_pmol_kg=3 * FACTOR, tolerance_pmol_kg=1e-8
    )
    checks["gain_linearity"].update(max_state_error_pmol_kg=0.0, tolerance_pmol_kg=1e-7)
    checks["zero_gain"].update(max_absolute_state_pmol_kg=0.0, tolerance=0.0)
    checks["route_contrast_resolution"].update(
        max_route_contrast_pmol_l=FACTOR / VI,
        max_numerical_error_pmol_l=0.0,
        numerical_error_fraction=0.0,
        maximum_fraction=0.01,
    )
    return {
        "schema": "m4-kinetic-inlet-verification/1",
        "protocol": "synthetic-kinetic-archive-fixture",
        "passed": True,
        "checks": checks,
        "claim": "synthetic archive-contract measurements, not numerical verification",
        "source_integral_pmol_kg": 3 * FACTOR,
        "human_validation": "not performed",
        "glucose_control_evaluation": "not performed",
    }


def fixture(directory):
    """An archive-contract fixture, explicitly not a solution of kinetic equations."""
    directory.mkdir()
    beta_fixture(directory / "bc001")
    protocol = {
        "schema": "m4-kinetic-inlet-protocol/1",
        "id": "synthetic-kinetic-archive-fixture",
        "claim": "hand-calculable reader fixture; no numerical execution",
        "horizon_min": 2,
        "sample_step_min": 1,
        "additional_sample_times_min": [],
        "initial_state": [0, 0, 0, 0, 0],
        "added_basal_pmol_kg_min": 0,
        "upstream": UPSTREAM,
        "native_zero_extension": {"horizon_min": 60, "sample_step_min": 1},
        "trace_bridge": {"molar_mass_g_mol": 5808.0},
        "criteria": {
            "native_zero_derivative_error": 0,
            "native_zero_trajectory_error": 0,
            "max_insulin_state_error_pmol_kg": 1e-7,
            "max_plasma_error_pmol_l": 1e-6,
            "max_mass_balance_error_pmol_kg": 1e-8,
            "negative_state_tolerance_pmol_kg": 1e-9,
            "repeat_state_error": 0,
            "conversion_relative_error": 1e-12,
            "max_communication_amount_error_pmol_kg": 1e-8,
            "fine_communication_plasma_error_pmol_l": 0.01,
            "fine_to_coarse_communication_error_ratio": 0.35,
            "numerical_error_fraction_of_route_contrast": 0.01,
        },
        "excluded_claims": ["numerical solution", "human validation"],
    }
    report.dump(directory / "protocol.json", protocol)
    report.dump(
        directory / "native-identity.json",
        {
            "upstream_revision": UPSTREAM["revision"],
            "profile": UPSTREAM["profile"],
            "patient_file_sha256": UPSTREAM["patient_file_sha256"],
            "parameter_file_sha256": UPSTREAM["parameter_file_sha256"],
            "body_weight_kg": BW,
            "kinetic_parameters": {
                "BW": BW,
                "Vi": VI,
                "m1": 0.15446,
                "m2": 0.225027424083,
                "m4": 0.090010969633,
                "m30": 0.23169,
            },
            "claim": "archive fixture only; no upstream execution",
        },
    )
    report.dump(directory / "verification.json", verification_fixture())
    table(
        directory / "source-input.csv",
        ("time_min", "secretion_ug_per_min", "q_pmol_kg_min"),
        [(0, 1, FACTOR), (1, 2, 2 * FACTOR), (2, 1, FACTOR)],
    )
    report.dump(
        directory / "source-forcing.json",
        {
            "edges": [0, 1, 2],
            "left": [FACTOR, 2 * FACTOR],
            "right": [2 * FACTOR, FACTOR],
            "units": "pmol/(kg min)",
        },
    )
    # Quantities below are multiples of FACTOR. Each row independently conserves
    # total input. Concentrations divide the separately specified plasma amount by Vi.
    states = {
        "source-liver": [(0.25, 0.75, 0.25, 0.25), (0.5, 1, 0.75, 0.75)],
        "source-peripheral": [(1, 0.25, 0.125, 0.125), (1.5, 0.5, 0.5, 0.5)],
        "matched-constant-liver": [(0.3, 0.7, 0.2, 0.3), (0.6, 0.9, 0.75, 0.75)],
        "zero-liver": [(0, 0, 0, 0), (0, 0, 0, 0)],
    }
    for name, samples in states.items():
        rows = [[0] * len(report.COLUMNS)]
        for time, (ip, il, hepatic, peripheral) in enumerate(samples, 1):
            amount = 0 if name == "zero-liver" else 1.5 * time
            rows.append(
                [time]
                + [v * FACTOR for v in (ip, il, hepatic, peripheral, amount)]
                + [ip * FACTOR / VI, ip * FACTOR, il * FACTOR, ip * FACTOR / VI]
            )
        table(directory / f"{name}.csv", report.COLUMNS, rows)
    report.dump(directory / "report.json", {"fixture": "not numerical execution"})
    (directory / "figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
    for name in report.SOURCE_FILES:
        (directory / f"source-{name}").write_text(
            "raise RuntimeError('archived source must never be executed')\n"
        )
    (directory / "native-uv.lock").write_text("# synthetic archive fixture\n")
    (directory / "native-pyproject.toml").write_text("# synthetic archive fixture\n")
    report.dump(
        directory / "manifest.json",
        {
            "schema": "bc002-run/1",
            "status": "completed",
            "files": {
                path.relative_to(directory).as_posix(): report.digest(path)
                for path in sorted(directory.rglob("*"))
                if path.is_file()
            },
        },
    )


class KineticArtifacts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "run"
        fixture(self.run)

    def edit_json(self, name, update, *, rehash=True):
        path = self.run / name
        value = json.loads(path.read_text())
        update(value)
        report.dump(path, value)
        if rehash and name != "manifest.json":
            self.rehash(name)

    def rehash(self, name):
        self.edit_json(
            "manifest.json",
            lambda value: value["files"].update({name: report.digest(self.run / name)}),
        )

    def edit_rows(self, name, update, *, rehash=True):
        path = self.run / name
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        update(rows)
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
        if rehash:
            self.rehash(name)

    def assert_cannot_pass(self):
        try:
            result = report.reconstruct(self.run)
        except ValueError:
            return
        self.assertFalse(result["passed"])

    def test_hand_calculated_input_mass_concentration_and_auc(self):
        result = report.reconstruct(self.run)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["source_input_amount_pmol_kg"], 3 * FACTOR)
        liver = result["cases"]["source-liver"]
        self.assertAlmostEqual(liver["peak_incremental_plasma_pmol_l"], 0.5 * FACTOR / VI)
        self.assertAlmostEqual(liver["trapezoid_plasma_auc_pmol_min_l"], 0.5 * FACTOR / VI)
        self.assertLess(liver["max_mass_balance_error_pmol_kg"], 1e-14)
        peripheral = result["cases"]["source-peripheral"]
        self.assertAlmostEqual(peripheral["trapezoid_plasma_auc_pmol_min_l"], 1.75 * FACTOR / VI)
        self.assertEqual(result["cases"]["zero-liver"]["final_input_pmol_kg"], 0)

    def test_module_reader_uses_no_site_packages_and_never_executes_archived_source(self):
        output = self.root / "reconstructed.json"
        command = [
            sys.executable,
            "-S",
            "-m",
            "experiments.m4.kinetic_inlet.report",
            str(self.run),
            "--output",
            str(output),
        ]
        repository = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            command, cwd=repository, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text()), report.reconstruct(self.run))
        original = output.read_bytes()
        repeated = subprocess.run(
            command, cwd=repository, capture_output=True, text=True, check=False
        )
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_required_artifacts_cannot_be_missing_or_undeclared(self):
        original_manifest = (self.run / "manifest.json").read_bytes()
        for name in ("source-liver.csv", "source-native.py", "report.json", "figure.svg"):
            with self.subTest(name=name, defect="missing"):
                path = self.run / name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaises(ValueError):
                    report.reconstruct(self.run)
                path.write_bytes(original)
            with self.subTest(name=name, defect="undeclared"):
                self.edit_json("manifest.json", lambda value: value["files"].pop(name))
                with self.assertRaises(ValueError):
                    report.reconstruct(self.run)
                (self.run / "manifest.json").write_bytes(original_manifest)

    def test_changed_artifact_is_rejected_without_rehash(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(1, "999"), rehash=False)
        with self.assertRaisesRegex(ValueError, "changed"):
            report.reconstruct(self.run)

    def test_changed_nested_archive_is_rejected(self):
        (self.run / "bc001" / "source-model.py").write_text("corrupted\n")
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_nested_archive_still_requires_its_own_integrity(self):
        path = self.run / "bc001" / "source-model.py"
        path.write_text("corrupted\n")
        self.rehash("bc001/source-model.py")
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_nested_directory_symlink_is_rejected_even_with_matching_content(self):
        nested = self.run / "bc001"
        external = self.root / "copied-source"
        nested.rename(external)
        nested.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "[Ss]ymlink"):
            report.reconstruct(self.run)

    def test_nested_file_symlink_is_rejected_even_with_matching_content(self):
        path = self.run / "bc001" / "trace.csv"
        external = self.root / "trace.csv"
        path.rename(external)
        path.symlink_to(external)
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_manifest_rejects_path_escape_and_unexpected_nested_directory(self):
        original = (self.run / "manifest.json").read_bytes()
        for name in ("../trace.csv", str(self.root / "trace.csv"), "other/trace.csv"):
            with self.subTest(name=name):
                (self.run / "manifest.json").write_bytes(original)
                self.edit_json(
                    "manifest.json", lambda value: value["files"].update({name: "0" * 64})
                )
                with self.assertRaises(ValueError):
                    report.reconstruct(self.run)

    def test_failed_started_and_calculated_attempts_are_not_completed(self):
        for status in ("started", "failed", "calculated", "interrupted"):
            with self.subTest(status=status):
                self.edit_json("manifest.json", lambda value: value.update(status=status))
                with self.assertRaises(ValueError):
                    report.reconstruct(self.run)

    def test_calculated_core_requires_explicit_internal_finalization(self):
        self.edit_json("manifest.json", lambda value: value.update(status="calculated"))
        for name in ("report.json", "figure.svg"):
            (self.run / name).unlink()
            self.edit_json("manifest.json", lambda value: value["files"].pop(name))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)
        self.assertTrue(report.reconstruct(self.run, allow_pending=True)["passed"])

    def test_rehashed_missing_interior_grid_point_is_rejected(self):
        for name in ("source-liver", "source-peripheral", "matched-constant-liver", "zero-liver"):
            self.edit_rows(f"{name}.csv", lambda rows: rows.pop(2))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_duplicate_time_is_rejected(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(0, "0"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_incomplete_source_forcing_cannot_pass(self):
        self.edit_rows("source-input.csv", lambda rows: rows.pop(2))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_secretion_cannot_diverge_from_nested_source(self):
        def altered_source(rows):
            # Equal AUC: perturb both endpoint rates and the centre in opposite directions.
            for row, secretion in zip(rows[1:], (1.5, 1.5, 1.5)):
                row[1:] = [str(secretion), str(secretion * FACTOR)]

        self.edit_rows("source-input.csv", altered_source)
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_wrong_mass_to_mole_conversion_is_rejected_after_rehash(self):
        self.edit_rows("source-input.csv", lambda rows: rows[2].__setitem__(2, "2"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_forcing_units_cannot_change(self):
        self.edit_json("source-forcing.json", lambda value: value.update(units="pmol/min"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_rehashed_native_identity_must_match_protocol(self):
        self.edit_json("native-identity.json", lambda value: value.update(profile="adult#002"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_wrong_amount_to_concentration_conversion_is_rejected_after_rehash(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(6, "2"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_mass_error_cannot_be_hidden_by_passing_verification_flags(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(3, "1"))
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_oracle_error_cannot_be_hidden_by_passing_verification_flags(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(9, "999"))
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_oracle_amount_error_cannot_hide_behind_consistent_plasma(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(8, "999"))
        self.assert_cannot_pass()

    def test_zero_input_case_cannot_contain_balanced_nonzero_input(self):
        (self.run / "zero-liver.csv").write_bytes((self.run / "source-liver.csv").read_bytes())
        self.rehash("zero-liver.csv")
        self.assert_cannot_pass()

    def test_nonzero_initial_amount_cannot_hide_in_balanced_inventory(self):
        def initial_inventory(rows):
            row = rows[1]
            row[1] = row[5] = row[7] = "1"
            row[6] = row[9] = str(1 / VI)

        self.edit_rows("source-liver.csv", initial_inventory)
        self.assert_cannot_pass()

    def test_missing_required_check_cannot_be_hidden_by_passing_summary(self):
        self.edit_json("verification.json", lambda value: value["checks"].pop("repeatability"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_false_summary_or_check_remains_failed(self):
        self.edit_json("verification.json", lambda value: value.update(passed=False))
        self.assertFalse(report.reconstruct(self.run)["passed"])
        self.edit_json("verification.json", lambda value: value.update(passed=True))
        self.edit_json(
            "verification.json", lambda value: value["checks"]["repeatability"].update(passed=False)
        )
        self.assertFalse(report.reconstruct(self.run)["passed"])

    def test_measured_failure_overrides_passing_flags(self):
        self.edit_json(
            "verification.json",
            lambda value: value["checks"]["repeatability"].update(max_absolute_state_error=0.1),
        )
        self.assert_cannot_pass()

    def test_missing_measurement_cannot_be_hidden_by_passing_flags(self):
        self.edit_json(
            "verification.json",
            lambda value: value["checks"]["repeatability"].pop("max_absolute_state_error"),
        )
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_boolean_is_not_a_zero_measurement(self):
        self.edit_json(
            "verification.json",
            lambda value: value["checks"]["repeatability"].update(max_absolute_state_error=False),
        )
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_measured_failure_cannot_raise_its_own_tolerance(self):
        self.edit_json(
            "verification.json",
            lambda value: value["checks"]["repeatability"].update(
                max_absolute_state_error=0.1, tolerance=1.0
            ),
        )
        self.assert_cannot_pass()

    def test_rehashed_nonfinite_trace_is_rejected(self):
        self.edit_rows("source-liver.csv", lambda rows: rows[2].__setitem__(1, "nan"))
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)

    def test_invalid_native_volume_is_rejected(self):
        self.edit_json(
            "native-identity.json", lambda value: value["kinetic_parameters"].update(Vi=0)
        )
        with self.assertRaises(ValueError):
            report.reconstruct(self.run)


if __name__ == "__main__":
    unittest.main()
