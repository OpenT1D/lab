"""Independent equilibrium and signed-source fixtures for the feedback specification."""

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.feedback.contract import baseline, secretion_terms, validate
from experiments.m4.feedback.preflight import HERE, VERSION, assess, execute, read, reconstruct


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")
        self.sp = self.p["source"]["parameters"]
        # Hand-balanced insulin system: SC input 4, Ip=16, Il=0.4, SC=(2,1).
        self.params = {
            "u2ss": 4,
            "m1": 2,
            "m30": 6,
            "m2": 0.2,
            "m4": 0.1,
            "ka1": 1,
            "kd": 1,
            "ka2": 2,
            "BW": 100,
            "Vi": 0.1,
            "Vg": 2,
        }
        self.state = [0, 0, 0, 200, 100, 16, 0, 160, 160, 0.4, 2, 1, 200]

    def test_basal_replacement_balances_both_compartments(self):
        result = baseline(self.params, self.state, 0.25, 0.5)
        self.assertEqual(result["u_sc_pmol_kg_min"], 3)
        self.assertEqual(result["Sb_pmol_kg_min"], 4)  # Not the 1 removed from SC.
        self.assertEqual(result["P_pmol_kg"], 8)
        self.assertAlmostEqual(result["state"][9], 0.9)
        self.assertEqual(result["state"][10:12], [1.5, 0.75])
        self.assertEqual(result["state"][5], 16)
        ip, liver, s1, s2 = [result["state"][i] for i in (5, 9, 10, 11)]
        self.assertAlmostEqual(-0.3 * ip + 2 * liver + s1 + 2 * s2, 0)
        self.assertAlmostEqual(-8 * liver + 0.2 * ip + 4, 0)
        self.assertAlmostEqual(3 + 4 - 0.1 * ip - 6 * liver, 0)
        self.assertEqual(self.state[9:12], [0.4, 2, 1])

    def test_zero_fraction_exact_identity_and_full_replacement(self):
        zero = baseline(self.params, self.state, 0, 0.5)
        self.assertEqual(zero["state"], self.state)
        self.assertEqual(zero["Sb_pmol_kg_min"], 0)
        full = baseline(self.params, self.state, 1, 0.5)
        self.assertEqual(full["u_sc_pmol_kg_min"], 0)
        self.assertEqual(full["state"][10:12], [0, 0])
        self.assertEqual(full["Sb_pmol_kg_min"], 16)

    def test_amount_and_activity_conversions_are_distinct(self):
        result = baseline(self.params, self.state, 0.25, 0.5)
        self.assertEqual(result["action_insulin_u_min"], 0.05)
        self.assertEqual(result["h_mg_dl"], 100)
        self.assertEqual(result["Sb_pmol_kg_min"], 4)

    def test_invalid_baselines_rejected(self):
        for value in (-0.1, 1.1, True, float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                baseline(self.params, self.state, value, 0.5)
        for key in ("BW", "m1", "u2ss"):
            with self.assertRaises(ValueError):
                baseline({**self.params, key: 0}, self.state, 0.25, 0.5)
        with self.assertRaises(ValueError):
            baseline(self.params, self.state[:-1], 0.25, 0.5)

    def terms(self, g, dg, z=0.7, portal=3, sb=1.1, gain=1):
        return secretion_terms(g, dg, z, portal, sb, 100, gain, self.sp)

    def test_below_basal_signed_Y_is_not_clipped_to_zero(self):
        v = self.terms(40, -2)
        self.assertEqual(v["target"], 0)
        self.assertAlmostEqual(v["Z_dot"], -0.035)
        self.assertEqual(v["pancreatic"], 0.7)
        self.assertEqual(v["liver"], 1.5)
        self.assertAlmostEqual(v["P_dot"], -0.8)

    def test_rising_and_falling_have_distinct_dynamic_response(self):
        up, down = self.terms(110, 2), self.terms(110, -2)
        self.assertAlmostEqual(up["target"], 2.2)
        self.assertAlmostEqual(up["pancreatic"], 5.3)
        self.assertAlmostEqual(down["pancreatic"], 0.7)
        self.assertEqual(up["liver"], down["liver"])  # Transport state is not the source rate.

    def test_floor_boundary_is_continuous(self):
        values = [self.terms(90 + offset, 0)["Z_dot"] for offset in (-1e-8, 0, 1e-8)]
        for value in values:
            self.assertAlmostEqual(value, -0.035, places=9)

    def test_basal_stationarity_and_no_responsivity(self):
        result = self.terms(100, 0, z=1.1, portal=2.2)
        self.assertEqual(result["Z_dot"], 0)
        self.assertEqual(result["P_dot"], 0)
        zero = self.terms(250, 5, z=1.1, portal=2.2, gain=0)
        self.assertEqual(zero, result)

    def test_invalid_source_measurements_and_states_rejected(self):
        for value in (True, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.terms(100, value)
        with self.assertRaises(ValueError):
            self.terms(100, 0, z=-0.1)

    def test_protocol_cannot_silently_change_claims_or_limits(self):
        validate(self.p)
        for key, value in (("status", "completed"), ("horizon_min", 360)):
            changed = copy.deepcopy(self.p)
            changed[key] = value
            with self.assertRaisesRegex(ValueError, "frozen"):
                validate(changed)

    def hand_probe(self):
        p = self.p
        identity = {
            k: p["upstream"][k] for k in ("profile", "patient_file_sha256", "parameter_file_sha256")
        }
        identity["upstream_revision"] = p["upstream"]["revision"]
        cases = [
            {
                "id": c["id"],
                "initial": baseline(self.params, self.state, c["fraction"], 0.5),
                "native_derivative": [0] * 13,
            }
            for c in p["cases"]
        ]
        probes = []
        for liver in (0.4, 0, -1):
            state = self.state.copy()
            state[9] = liver
            added = [0] * 13
            added[9] = 1.5 if liver >= 0 else 0
            probes.append(
                {"state": state, "q": 1.5, "native": [0] * 13, "zero": [0] * 13, "added": added}
            )
        return {
            "schema": VERSION,
            "runtime": {**p["runtime"], "python": "3.12.13"},
            "native_identity": identity,
            "parameters": self.params,
            "initial": self.state,
            "native_derivative": [0] * 13,
            "cases": cases,
            "locality_probes": probes,
        }

    def test_report_detects_changed_derivative_and_nonlocal_inlet(self):
        data = self.hand_probe()
        self.assertTrue(assess(self.p, data)["passed"])
        data["cases"][1]["native_derivative"][9] = 1
        result = assess(self.p, data)
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["metrics"]["insulin_inventory_derivative_balance"], 1)
        data = self.hand_probe()
        data["locality_probes"][0]["added"][5] = 1.5
        result = assess(self.p, data)
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["native_derivative_locality_error"], 1.5)

    def test_report_rejects_missing_case_and_changed_pin(self):
        data = self.hand_probe()
        data["cases"].pop()
        with self.assertRaises(ValueError):
            assess(self.p, data)
        data = self.hand_probe()
        data["native_identity"]["upstream_revision"] = "different"
        with self.assertRaises(ValueError):
            assess(self.p, data)


class RecorderTests(unittest.TestCase):
    def test_failure_and_interruption_preserve_artifacts_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i, error in enumerate(
                (KeyboardInterrupt(), subprocess.CalledProcessError(1, ["probe"]))
            ):
                output = Path(tmp) / str(i)
                with patch("experiments.m4.feedback.preflight.command", side_effect=error):
                    with self.assertRaises(type(error)):
                        execute(output)
                manifest = read(output / "manifest.json")
                self.assertEqual(manifest["status"], "failed")
                self.assertTrue((output / "source-contract.py").is_file())
                with self.assertRaises(ValueError):
                    reconstruct(output)
                with self.assertRaises(FileExistsError):
                    execute(output)
                self.assertEqual(read(output / "manifest.json"), manifest)


if __name__ == "__main__":
    unittest.main()
