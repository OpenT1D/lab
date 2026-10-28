"""Numerical and artifact-failure checks for the synthetic schedule comparison."""

import copy
import json
import unittest
from pathlib import Path

import numpy as np

from .analysis import grids, ode_truth, predict, run_analysis
from .report import summarize

HERE = Path(__file__).resolve().parent


class SamplingWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((HERE / "protocol.json").read_text())
        cls.output = run_analysis(cls.protocol)

    def test_source_clock_and_analytical_independence(self):
        early = grids(self.protocol)["early"]
        self.assertEqual(early[0], 1.5)
        self.assertEqual(early[-1], 10.5)
        full = grids(self.protocol)["early_plus_hypothetical_late"]
        self.assertEqual(full[-1], 180.5)
        self.assertTrue(np.array_equal(full[: len(early)], early))
        for theta in ([1, 1], [0.5, 1.5], [1.5, 0.5]):
            ode, states = ode_truth(self.protocol, full, theta)
            exact = predict(self.protocol, full, theta)
            self.assertLess(np.max(abs(ode - exact)), 1e-4)
            self.assertLess(
                abs(states[-1, 0] + states[-1, 1] + states[-1, 2] - states[-1, 3]), 1e-7
            )

    def test_truncated_or_changed_observation_is_rejected(self):
        original = self.output
        broken = copy.deepcopy(original["observations"])
        broken["draws"][str(self.protocol["observation"]["noise_seed_first"])]["observed_pmol_l"][
            0
        ] += 1
        with self.assertRaisesRegex(ValueError, "reference plus error"):
            summarize(
                self.protocol,
                original["checks"],
                original["sensitivities"],
                broken,
                original["cases"],
            )
        broken = copy.deepcopy(original["cases"])
        broken.pop(next(iter(broken)))
        with self.assertRaisesRegex(ValueError, "planned fit case"):
            summarize(
                self.protocol,
                original["checks"],
                original["sensitivities"],
                original["observations"],
                broken,
            )

    def test_invalid_candidate_and_schedule_fail_closed(self):
        full = grids(self.protocol)["early_plus_hypothetical_late"]
        for bad in ([0.49, 1], [1, float("nan")], [1]):
            with self.assertRaises(ValueError):
                predict(self.protocol, full, bad)
        changed = copy.deepcopy(self.protocol)
        changed["observation"]["hypothetical_late_clock_min"][0] = 9
        with self.assertRaisesRegex(ValueError, "Sampling clocks"):
            grids(changed)


if __name__ == "__main__":
    unittest.main()
