"""Independent dimensional fixtures, accounting faults and interrupted chain runs."""

import copy
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.chain.common import (
    HERE,
    ROOT,
    VERSION,
    convert,
    dump,
    grid,
    prepare,
    read,
    validate,
)
from experiments.m4.chain.report import assess_case, reconstruct, samples
from experiments.m4.chain.run import execute
from experiments.m4.kinetic_inlet.forcing import Forcing


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")
        self.b = read(ROOT / "experiments/m4/paired_observation/protocol.json")
        # 5.808 micrograms is exactly 1000 pmol at the declared molecular mass.
        self.source = {"times_min": [0, 50, 100], "secretion_ug_min": [0, 5.808, 0]}

    def case(self, name):
        c = next(c for c in self.p["cases"] if c["id"] == name)
        return prepare(self.p, self.b, c, self.source)

    def test_hand_conversion_and_triangle_area(self):
        signal = convert([0, 1, 2], [0, 5.808, 0], body_weight_kg=100, molar_mass_g_mol=5808)
        self.assertAlmostEqual(signal.evaluate(1), 10)
        self.assertAlmostEqual(signal.integral(), 10)
        self.assertAlmostEqual(signal.evaluate(0.5), 5)
        with self.assertRaises(ValueError):
            signal.evaluate(2.01)

    def test_invalid_source_and_scaling_rejected_even_at_zero_gain(self):
        for value in (True, -1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                convert([0, 1], [value, 1], body_weight_kg=100, molar_mass_g_mol=5808, gain=0)
        for key in ("body_weight_kg", "molar_mass_g_mol", "gain"):
            for value in (True, -1, float("inf")):
                args = {"body_weight_kg": 100, "molar_mass_g_mol": 5808, "gain": 1}
                args[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    convert([0, 1], [1, 1], **args)
        for times, rates in (([1, 2], [1, 1]), ([0, 0], [1, 1]), ([0, 1], [1])):
            with self.assertRaises(ValueError):
                convert(times, rates, body_weight_kg=100, molar_mass_g_mol=5808)

    def test_normalization_once_and_constant_amount_preserved(self):
        full = Forcing(**self.case("full_increment")["forcing"])
        constant = Forcing(**self.case("matched_constant_increment")["forcing"])
        self.assertAlmostEqual(full.integral(), 50000 / 102.32)
        self.assertAlmostEqual(constant.integral(), 50000 / 102.32)
        self.assertAlmostEqual(constant.evaluate(0), 500 / 102.32)
        self.assertNotEqual(full.evaluate(0), constant.evaluate(0))

    def test_evoked_gain_and_basal_have_separate_ownership(self):
        full, half, total, basal = [
            self.case(k)
            for k in ("full_increment", "half_increment", "full_synthetic_total", "basal_only")
        ]
        f, h, t, b = [Forcing(**v["forcing"]) for v in (full, half, total, basal)]
        for time in (0, 25, 50, 100):
            self.assertAlmostEqual(h.evaluate(time), f.evaluate(time) / 2)
            self.assertAlmostEqual(t.evaluate(time) - f.evaluate(time), 1.5)
            self.assertAlmostEqual(b.evaluate(time), 1.5)
        self.assertAlmostEqual(t.integral() - f.integral(), 150)
        self.assertEqual(total["initial"], basal["initial"])
        self.assertNotEqual(total["initial"]["insulin"][:2], total["initial"]["cpeptide"][:2])
        self.assertEqual(full["initial"], {"insulin": [0] * 5, "cpeptide": [0] * 4})
        for branch in ("insulin", "cpeptide"):
            self.assertEqual(sum(total["initial"][branch][2:]), 0)

    def test_scope_and_criteria_are_frozen(self):
        validate(self.p)
        for key in ("basal_pmol_min", "insulin_molar_mass_g_mol", "molar_ratio_cpeptide_insulin"):
            modified = copy.deepcopy(self.p)
            modified["boundary"][key] *= 2
            with self.assertRaisesRegex(ValueError, "frozen"):
                validate(modified)
        self.p["criteria"]["mass_error_pmol_kg"] = 1e9
        with self.assertRaises(ValueError):
            validate(self.p)


class SavedAccountingTests(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")
        self.p.update(horizon_min=1, sample_step_min=0.5)
        self.request = {
            "id": "hand_washout",
            "forcing": Forcing([0, 1], [0], [0]).to_dict(),
            "initial": {"insulin": [2, 3, 0, 0, 0]},
        }
        # Independent inventory fixture: initial 5 = retained + eliminated.
        rows = [[2, 3, 0, 0, 0], [1.5, 2, 1, 0.5, 0], [1, 1, 2, 1, 0]]
        self.data = {
            "schema": "bc007-case/1",
            "branch": "insulin",
            "request": copy.deepcopy(self.request),
            "times_min": [0, 0.5, 1],
            "volume_l_kg": 1,
            "states": {k: copy.deepcopy(rows) for k in ("tight", "reference")},
            "oracle": copy.deepcopy(rows),
            "repeated": copy.deepcopy(rows),
            "legacy": None,
        }

    def assess(self):
        return assess_case(self.data, self.request, self.p, "insulin", 1)

    def test_hand_inventory_and_concentration(self):
        report = self.assess()
        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["mass_error_pmol_kg"], 0)
        self.assertEqual(report["final_concentration_pmol_l"], 1)

    def test_ledger_loss_fails_even_if_concentration_matches(self):
        self.data["oracle"][-1][2] = 0
        result = self.assess()
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["mass_error_pmol_kg"], 2)

    def test_added_input_fails_independent_delivered_amount(self):
        for rows in [*self.data["states"].values(), self.data["oracle"], self.data["repeated"]]:
            rows[-1][-1] = 1
            rows[-1][2] += 1  # Still conserves inventory, but disagrees with forcing.
        result = self.assess()
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["input_error_pmol_kg"], 1)

    def test_repeat_and_initial_inventory_changes_detected(self):
        self.data["repeated"][-1][0] += 1
        self.assertFalse(self.assess()["passed"])
        self.data["repeated"][0] = [0] * 5
        with self.assertRaisesRegex(ValueError, "initial inventory"):
            self.assess()

    def test_request_units_and_volume_not_trusted(self):
        self.data["request"]["forcing"]["units"] = "ug/min"
        with self.assertRaises(ValueError):
            self.assess()
        self.data["request"] = copy.deepcopy(self.request)
        self.data["volume_l_kg"] = 1000
        with self.assertRaises(ValueError):
            self.assess()

    def test_missing_nonfinite_and_incomplete_states_rejected(self):
        for field in ("oracle", "repeated"):
            for replacement in ([], [[0] * 5], [[True] * 5] * 3, [[float("nan")] * 5] * 3):
                previous = self.data[field]
                self.data[field] = replacement
                with self.assertRaises(ValueError):
                    self.assess()
                self.data[field] = previous
        del self.data["states"]["tight"]
        with self.assertRaises(ValueError):
            self.assess()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_failure_and_interruption_preserve_attempt_and_reject_reconstruction(self):
        for index, error in enumerate(
            (subprocess.CalledProcessError(1, ["worker"]), KeyboardInterrupt())
        ):
            target = self.root / str(index)
            with patch("experiments.m4.chain.run.command", side_effect=error):
                with self.assertRaises(type(error)):
                    execute(target)
            manifest = read(target / "manifest.json")
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["error"]["type"], type(error).__name__)
            self.assertTrue((target / "source-common.py").is_file())
            with self.assertRaisesRegex(ValueError, "not complete"):
                reconstruct(target)
            with self.assertRaises(FileExistsError):
                execute(target)
            self.assertEqual(read(target / "manifest.json"), manifest)

    def test_missing_fine_states_and_changed_source_rejected(self):
        p = read(HERE / "protocol.json")
        sp = read(ROOT / "experiments/m4/beta_cell/protocol.json")
        (self.root / "secretion").mkdir()
        dump(self.root / "secretion/protocol.json", sp)
        levels = []
        for step in p["source"]["refinement_steps_min"]:
            times = grid(p, step)
            levels.append(
                {
                    "step_min": step,
                    "times_min": times,
                    "glucose_mmol_l": [
                        sp["input"]["g_b"]
                        + (sp["input"]["g_max"] - sp["input"]["g_b"])
                        * math.exp(-t / sp["input"]["tau_min"])
                        for t in times
                    ],
                    "secretion_ug_min": [0] * len(times),
                    "states": [[0, 0] for _ in times],
                }
            )
        del levels[0]["states"]
        levels[0]["source_manifest_sha256"] = "fixture"
        source = {k: v for k, v in levels[0].items() if k != "step_min"}
        data = {
            "schema": "bc007-source/1",
            "implementation": VERSION,
            "model": p["source"]["model"],
            "runtime": p["runtime"]["cpeptide"],
            "levels": levels,
        }
        dump(self.root / "source-samples.json", data)
        samples(self.root, p, source)
        del levels[1]["states"]
        dump(self.root / "source-samples.json", data)
        with self.assertRaises(ValueError):
            samples(self.root, p, source)
        levels[0]["secretion_ug_min"] = [1] * len(levels[0]["times_min"])
        dump(self.root / "source-samples.json", data)
        with self.assertRaisesRegex(ValueError, "differ from source"):
            samples(self.root, p, source)


if __name__ == "__main__":
    unittest.main()
