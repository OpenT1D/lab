"""BC-012 independent observation-boundary checks in the frozen native lock."""

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from .model import Model
from .verify import run


class VolumeNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(Path(__file__).with_name("protocol.json").read_text())
        cls.model = Model(cls.protocol)

    def test_forward_gates(self):
        evidence = run(self.model)
        self.assertTrue(evidence["parent"]["passed"], evidence["parent"]["checks"])
        self.assertTrue(evidence["passed"], evidence["checks"])
        self.assertEqual(len(evidence["details"]["trials"]), 45)

    def test_fasting_concentration_from_molar_inventory_and_volume_units(self):
        # Analytical steady-state expression independent of integration and of
        # the wrapper concentration division: pmol/(kg min) / (1/min * L/kg).
        for theta in ([0.5, 0.5, 1.5, 0.5], [1.5, 1.5, 0.5, 1.5]):
            record = self.model.simulate(theta, load=0, solver="reference")
            sb = record["baseline"]["Sb_pmol_kg_min"]
            expected_q1 = sb / (0.052 * theta[2])
            expected_cp = expected_q1 / (65.5 / 1000 * theta[3])
            np.testing.assert_allclose(record["states"][:, 20], expected_q1, rtol=0, atol=1e-7)
            np.testing.assert_allclose(record["observations"][:, 2], expected_cp, rtol=0, atol=1e-7)
            np.testing.assert_allclose(record["observations"][:, 0], 138.56, rtol=0, atol=1e-7)
            np.testing.assert_allclose(record["observations"][:, 1], 100.25, rtol=0, atol=1e-7)

    def test_equal_basal_product_does_not_claim_dynamic_symmetry(self):
        nominal = self.model.simulate([1, 1, 1, 1], solver="reference")
        alternative = self.model.simulate([1, 1, 0.8, 1.25], solver="reference")
        self.assertAlmostEqual(nominal["observations"][0, 2], alternative["observations"][0, 2])
        # A changed removal time constant cannot be hidden by observation scale
        # over a driven transient, even though the single baseline is identical.
        self.assertGreater(
            np.max(np.abs(nominal["observations"][:, 2] - alternative["observations"][:, 2])), 1
        )

    def test_invalid_inputs_cannot_hide_behind_cached_parent_solve(self):
        # Seed a valid entry so bools or out-of-bound volume cannot alias it.
        self.model.simulate([1, 1, 1, 1])
        invalid = (
            {"theta": [1, 1, 1, True]},
            {"theta": [1, np.bool_(True), 1, 1]},
            {"theta": [1, 1, 1, "1"]},
            {"theta": [1, 1, 1, 1 + 0j]},
            {"theta": [1, 1, 1 + 0.2j, 1]},
            {"theta": np.array([1, 1, 1, 1], dtype=complex)},
            {"theta": np.array([1 + 0.1j, 1, 1, 1])},
            {"theta": np.array([1, 1, 1, np.complex64(1)], dtype=object)},
            {"theta": [1, 1, 1, np.nan]},
            {"theta": [1, 1, 1, np.inf]},
            {"theta": [1, 1, 1, 0.49]},
            {"theta": [1, 1, 1, 1.51]},
            {"theta": [1, 1, 1, 0]},
            {"theta": [1, 1, 1]},
            {"theta": [[1, 1, 1, 1]]},
            {"theta": [1, 1, 1, 1], "source_scale": True},
            {"theta": [1, 1, 1, 1], "load": True},
            {"theta": [1, 1, 1, 1], "load": -1},
            {"theta": [1, 1, 1, 1], "times": [0, 239]},
            {"theta": [1, 1, 1, 1], "solver": "missing"},
        )
        with patch("experiments.m4.joint_identifiability.model.solve_ivp") as solver:
            for kwargs in invalid:
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.model.simulate(**kwargs)
            solver.assert_not_called()

    def test_cache_detaches_all_results_and_includes_parent_arguments(self):
        model = Model(self.protocol)
        with patch.object(model.base, "simulate", wraps=model.base.simulate) as simulate:
            reference = model.simulate([1, 1, 1, 1])
            untouched = copy.deepcopy(reference)
            changed = model.simulate([1, 1, 1, 0.8])
            self.assertEqual(simulate.call_count, 1)
            changed["observations"][:] = -999
            changed["states"][:] = -999
            changed["initial"][:] = -999
            changed["times"][:] = -999
            changed["theta"][:] = -999
            changed["baseline"]["state"][0] = -999
            replay = model.simulate([1, 1, 1, 1])
            for field in ("observations", "states", "initial", "times", "theta"):
                np.testing.assert_array_equal(replay[field], untouched[field])
            self.assertEqual(replay["baseline"], untouched["baseline"])
            model.simulate([1, 1, 1, 1], solver="reference")
            model.simulate([1, 1, 1, 1], load=0)
            model.simulate([1, 1, 1, 1], times=[0, 240])
            model.simulate([1, 1, 1, 1], source_scale=2)
            self.assertEqual(simulate.call_count, 5)

    def test_cache_is_bounded_and_does_not_round_parameters(self):
        model = Model(self.protocol)
        reference = model.base.simulate([1, 1, 1])
        with patch.object(model.base, "simulate", return_value=reference) as simulate:
            # Adjacent representable floats require separate parent solves.
            model.simulate([1, 1, 1, 1])
            model.simulate([np.nextafter(1.0, 1.5), 1, 1, 1])
            self.assertEqual(simulate.call_count, 2)
            for gain in np.linspace(1.1, 1.4, model.CACHE_SIZE):
                model.simulate([gain, 1, 1, 1])
            self.assertEqual(len(model._cache), model.CACHE_SIZE)
            model.simulate([1, 1, 1, 1])
            self.assertEqual(simulate.call_count, model.CACHE_SIZE + 3)

    def test_incomplete_parent_output_is_never_cached(self):
        model = Model(self.protocol)
        times = np.arange(241)
        incomplete = SimpleNamespace(status=0, y=np.zeros((24, 240)), t=times[:-1], message="short")
        with patch("experiments.m4.joint_identifiability.model.solve_ivp", return_value=incomplete):
            with self.assertRaises(RuntimeError):
                model.simulate([1, 1, 1, 1])
        self.assertEqual(len(model._cache), 0)
        complete = model.simulate([1, 1, 1, 1])
        self.assertEqual(complete["status"], "completed")
        self.assertEqual(complete["states"].shape, (241, 24))


if __name__ == "__main__":
    unittest.main()
