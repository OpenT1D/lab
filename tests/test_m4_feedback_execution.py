"""Artifact-side checks; no numerical runtime or generated results required."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.feedback import report, run
from experiments.m4.feedback.common import read


class FeedbackArtifactTests(unittest.TestCase):
    def setUp(self):
        self.p = {"horizon_min": 1, "sample_step_min": 1, "glucose_envelope_mg_dl": [40, 500]}
        self.params = dict(
            Vg=1, Vi=1, kp1=1, kp2=0, kp3=0, f=1, kabs=1, BW=1, Fsnc=1, ke1=0, ke2=999, k1=0, k2=0
        )
        first = [0.0] * 20
        for i, v in {3: 100, 4: 50, 5: 7, 6: -0.1, 9: 3, 10: 9, 11: 11, 13: 2, 14: 4}.items():
            first[i] = v
        second = first.copy()
        second[9] = 4
        second[15:] = [1, 2, 2, 1, 1]
        self.data = dict(
            status="completed",
            failure=None,
            times=[0, 1],
            initial=first,
            states=[first, second],
            source_rates=[[2, 2], [2, 2]],
            source_active=True,
            source_parameters=dict(gain=1, K=0, gamma=0.5),
            baseline={"u_sc_pmol_kg_min": 1},
            glucose_flux_integrals=[[0] * 5, [1, 0, 1, 0, 0]],
            glucose_quadrature_error_bounds=[0, 1e-10],
            quadrature=dict(
                method="quad_vec",
                epsabs=1e-9,
                epsrel=1e-9,
                norm="max",
                flux_order=["EGP", "Ra", "Uii", "Uid", "renal"],
            ),
        )

    def test_independent_balances_and_signed_action(self):
        result = report.inspect_trajectory(self.data, self.p, self.params)
        self.assertEqual(result["insulin_mass_error"], 0)
        self.assertEqual(result["glucose_mass_error"], 0)
        self.assertEqual(result["negative"], 0)

    def test_liver_double_counting_detected(self):
        self.data["states"][1][9] += 2
        self.assertEqual(
            report.inspect_trajectory(self.data, self.p, self.params)["insulin_mass_error"], 2
        )

    def test_portal_transit_ledger_discrepancy_detected(self):
        self.data["states"][1][17] += 1
        self.assertEqual(
            report.inspect_trajectory(self.data, self.p, self.params)["insulin_mass_error"], 1
        )

    def test_glucose_balance_is_not_fitted_to_output(self):
        self.data["glucose_flux_integrals"][1][0] += 0.25
        self.assertEqual(
            report.inspect_trajectory(self.data, self.p, self.params)["glucose_mass_error"], 0.25
        )

    def test_rate_state_is_excluded_from_physical_inventory(self):
        self.data["states"][1][13] += 10
        self.data["source_rates"][1][0] += 10
        self.assertEqual(
            report.inspect_trajectory(self.data, self.p, self.params)["insulin_mass_error"], 0
        )

    def test_wrong_source_boundary_rejected(self):
        self.data["source_rates"][1][1] = 3
        with self.assertRaisesRegex(ValueError, "Source output"):
            report.inspect_trajectory(self.data, self.p, self.params)

    def test_incomplete_failed_nonfinite_and_uncertain_flux_rejected(self):
        changes = (
            {"status": "failed"},
            {"times": [0]},
            {"glucose_quadrature_error_bounds": [0, 2e-6]},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                report.inspect_trajectory(self.data | change, self.p, self.params)
        self.data["states"][1][3] = float("nan")
        with self.assertRaises(ValueError):
            report.inspect_trajectory(self.data, self.p, self.params)

    def test_signed_auc_and_extrema(self):
        states = [[0, 0, 0, g] for g in [100, 110, 90]]
        self.assertEqual(
            report.outcomes([0, 1, 2], states, 1),
            dict(auc_above_initial_mg_min_dl=5, peak_mg_dl=110, nadir_mg_dl=90, final_mg_dl=90),
        )

    def test_attempt_preserved_on_worker_failure_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "failed"
            with (
                patch.object(run.subprocess, "check_output", side_effect=["test-head", b""]),
                patch.object(
                    run.subprocess, "run", side_effect=RuntimeError("test worker failure")
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "test worker failure"):
                    run.execute(output)
            saved = read(output / "manifest.json")
            self.assertEqual(saved["status"], "failed")
            self.assertIn("protocol.json", saved["files"])
            failed = report.reconstruct(output, allow_failed=True)
            self.assertFalse(failed["passed"])
            self.assertEqual(failed["scenarios"], {})
            self.assertTrue(failed["missing_evidence"])
            before = (output / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run.execute(output)
            self.assertEqual(before, (output / "manifest.json").read_bytes())

    def test_frozen_protocol_is_unchanged(self):
        from experiments.m4.feedback.contract import validate

        p = read(run.HERE / "protocol.json")
        validate(p)
        changed = copy.deepcopy(p)
        changed["cases"][2]["gain"] = 0.2
        with self.assertRaises(ValueError):
            validate(changed)
        self.assertEqual(json.dumps(p), json.dumps(read(run.HERE / "protocol.json")))

    def test_source_fixtures_cannot_be_tuned_after_execution(self):
        from experiments.m4.feedback.common import validate_source_cases

        spec = read(run.HERE / "source-cases.json")
        validate_source_cases(spec)
        spec["cases"][0]["initial"][0] += 0.1
        with self.assertRaises(ValueError):
            validate_source_cases(spec)
