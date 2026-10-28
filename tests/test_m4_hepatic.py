"""BC-009 artifact and scientific fault checks without a simulation runtime."""

import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.m4.feedback import source_oracle
from experiments.m4.feedback.contract import baseline
from experiments.m4.hepatic import common, report, run


class HepaticArtifactTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.HERE / "protocol.json")
        self.parent = common.read(common.ROOT / self.p["parent"])
        self.params = dict(
            Vg=1,
            Vi=1,
            BW=1,
            u2ss=4,
            m1=1,
            m30=1,
            kp1=1,
            kp2=0,
            kp3=0,
            f=1,
            kabs=1,
            Fsnc=1,
            ke1=0,
            ke2=999,
            k1=0,
            k2=0,
        )
        self.initial = [0.0] * 13
        for i, v in {3: 100, 4: 50, 5: 7, 6: -0.1, 9: 1, 10: 12, 11: 16}.items():
            self.initial[i] = v
        self.case = self.parent["cases"][-1]
        self.variant = self.p["variants"][0]
        self.scenario = self.parent["scenarios"][0]
        self.solver = self.parent["solvers"][-1]
        self.parent = self.parent | {"horizon_min": 1, "sample_step_min": 1}
        src = self.parent["source"]["parameters"]
        b = baseline(self.params, self.initial, self.case["fraction"], src["gamma_per_min"])
        first = b["state"] + [b["Z_pmol_kg_min"], b["P_pmol_kg"]] + [0.0] * 5
        last = first.copy()
        last[15:] = [3, 2, 2, 2, 3]
        self.data = dict(
            status="completed",
            failure=None,
            times=[0, 1],
            initial=first,
            states=[first, last],
            baseline=b,
            variant=self.variant,
            solver=self.solver,
            load_mg=0,
            source_rates=[[2, 2], [2, 2]],
            source_parameters=dict(
                alpha=0.05, beta=0.11, K=2.3, gamma=0.5, basal=2, threshold=100, gain=1
            ),
            glucose_flux_integrals=[[0] * 5, [1, 0, 1, 0, 0]],
            quadrature=self.p["quadrature"],
            quadrature_error_bounds=[0, 1e-10],
            hepatic=[dict(HE=0.5, m3=1, EGP=1), dict(HE=0.5, m3=1, EGP=1)],
        )

    def assess(self):
        return report.assess_case(
            self.data,
            self.p,
            self.parent,
            self.params,
            self.initial,
            self.scenario,
            self.case,
            self.variant,
            self.solver,
        )

    def test_independent_balances_and_signed_action(self):
        result = self.assess()
        for key in (
            "insulin_mass_error_pmol_kg",
            "glucose_mass_error_mg_kg",
            "negative_amount_tolerance",
            "literal_equation_error",
        ):
            self.assertEqual(result[key], 0)

    def test_stale_hepatic_loss_ledger_detected(self):
        self.data["states"][1][18] += 0.25
        self.assertEqual(self.assess()["insulin_mass_error_pmol_kg"], 0.25)

    def test_wrong_glucose_flux_balance_detected(self):
        self.data["glucose_flux_integrals"][1][0] += 0.25
        self.assertEqual(self.assess()["glucose_mass_error_mg_kg"], 0.25)

    def test_wrong_extraction_and_stale_source_rate_detected(self):
        self.data["hepatic"][1]["HE"] += 0.125
        self.assertEqual(self.assess()["literal_equation_error"], 0.125)
        self.data["source_rates"][1][0] += 0.5
        self.assertEqual(self.assess()["literal_equation_error"], 0.5)

    def test_invalid_settings_and_incomplete_calculations_rejected(self):
        for changes in (
            {"status": "failed"},
            {"times": [0]},
            {"quadrature_error_bounds": [0, 2e-6]},
            {"load_mg": 30000},
            {"solver": self.solver | {"rtol": 1}},
            {"source_parameters": self.data["source_parameters"] | {"K": 2300}},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                report.assess_case(
                    self.data | changes,
                    self.p,
                    self.parent,
                    self.params,
                    self.initial,
                    self.scenario,
                    self.case,
                    self.variant,
                    self.solver,
                )
        self.data["states"][1][3] = float("nan")
        with self.assertRaises(ValueError):
            self.assess()

    def test_frozen_protocol_and_complete_inventory(self):
        parent = common.read(common.ROOT / self.p["parent"])
        common.validate(self.p, parent)
        changed = copy.deepcopy(self.p)
        changed["source"]["m5_min_kg_pmol"] *= 2
        with self.assertRaises(ValueError):
            common.validate(changed, parent)
        self.assertEqual(len(list(common.case_specs(self.p, parent))), 24)
        self.assertEqual(len(common.numerical_files(self.p, parent)), 82)
        self.assertIn(
            "repeat/source-check/source-cases.json", common.required_files(self.p, parent)
        )

    def test_failed_attempt_kept_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "attempt"
            with (
                patch.object(run.subprocess, "check_output", side_effect=["test", b""]),
                patch.object(run.subprocess, "run", side_effect=RuntimeError("worker failure")),
            ):
                with self.assertRaisesRegex(RuntimeError, "worker failure"):
                    run.execute(out)
            failed = report.reconstruct(out, allow_failed=True)
            self.assertFalse(failed["passed"])
            self.assertEqual(failed["expected_cases"], 24)
            self.assertEqual(failed["contrasts"], {})
            self.assertTrue(failed["missing_evidence"])
            before = (out / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run.execute(out)
            self.assertEqual(before, (out / "manifest.json").read_bytes())
            with (out / "source-model.py").open("a") as stream:
                stream.write("\n# changed\n")
            with self.assertRaisesRegex(ValueError, "Changed/missing"):
                report.reconstruct(out, allow_failed=True)

    def test_source_reference_rebuilt_and_corruption_detected(self):
        parent = common.read(common.ROOT / self.p["parent"])
        spec = common.read(common.ROOT / "experiments/m4/feedback/source-cases.json")
        source = parent["source"]["parameters"]
        entries = []
        for f in spec["cases"]:
            parameters = dict(
                alpha=source["alpha_per_min"],
                beta=source["beta_pmol_kg_min_per_mg_dl"],
                K=source["K_pmol_kg_per_mg_dl"],
                gamma=f.get("gamma", source["gamma_per_min"]),
                basal=f.get("basal", spec["default_basal"]),
                threshold=spec["default_threshold"],
                gain=f.get("gain", spec["default_gain"]),
            )
            times = [
                i * spec["sample_step_min"]
                for i in range(round(f["times"][-1] / spec["sample_step_min"]) + 1)
            ]
            signal = SimpleNamespace(
                edges=f["times"],
                left=f["glucose"][:-1],
                right=f["glucose"][1:],
                segments=len(f["times"]) - 1,
            )
            exact = source_oracle.simulate(
                times, signal, f["initial"], SimpleNamespace(**parameters)
            )
            entries.append(
                dict(
                    id=f["id"],
                    parameters=parameters,
                    times=times,
                    analytic=exact,
                    solutions={name: exact for name in ("tight", "reference")},
                )
            )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name, data in (
                ("protocol", parent),
                ("source-cases", spec),
                ("source-reference", {"cases": entries}),
                (
                    "source-assessment",
                    dict(rate_error_pmol_kg_min=0, mass_error_pmol_kg=0, passed=True),
                ),
            ):
                common.dump(out / (name + ".json"), data)
            self.assertTrue(report.assess_source(out, parent)["passed"])
            changed = common.read(out / "source-reference.json")
            changed["cases"][0]["analytic"][1][1] += 0.01
            common.dump(out / "source-reference.json", changed)
            with self.assertRaisesRegex(ValueError, "analytic reference"):
                report.assess_source(out, parent)

    def test_opposite_and_unresolved_contrasts_retained(self):
        self.assertEqual(
            report.contrast(dict(coarse=-2, tight=-2, reference=-2))["classification"], "resolved"
        )
        self.assertEqual(
            report.contrast(dict(coarse=1, tight=0.01, reference=0.01))["classification"],
            "unresolved",
        )
        self.assertEqual(
            report.contrast(dict(coarse=0, tight=0, reference=0))["classification"], "zero"
        )
