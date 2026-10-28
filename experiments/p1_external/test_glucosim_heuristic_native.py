"""Method-specific checks against the pinned GlucoSim proportional agent."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glucosim.agents import heuristic

from experiments.m1.contracts import Observation
from experiments.p1_external.intake import SuppliedController, declaration

SOURCE = Path(__file__).with_name("glucosim_heuristic")


class PinnedHeuristicTests(unittest.TestCase):
    def test_upstream_proportional_law_held_cgm_units_and_reset(self):
        controller = SuppliedController(SOURCE, declaration(SOURCE), seed=101)
        controller.reset()
        # Upstream: clip(1 + 0.005*(CGM - 120), 0, 3) U/hour.
        # P1 receives that rate divided by 60, with no announced-meal action.
        cases = (
            (Observation(0, 120, 0, True), 1.0 / 60),
            (Observation(3, 220, 3, True), 1.5 / 60),
            (Observation(6, 220, 3, False), 1.5 / 60),
            (Observation(9, 1000, 9, True), 3.0 / 60),
        )
        for observation, expected in cases:
            with self.subTest(minute=observation.time_min):
                result = controller.command(observation, 40.0)
                self.assertAlmostEqual(result.basal_u_min, expected)
                self.assertEqual(result.bolus_u_min, 0.0)
        with self.assertRaisesRegex(ValueError, "advance by three minutes"):
            controller.command(Observation(15, 120, 15, True), 0.0)
        controller.reset()
        self.assertAlmostEqual(
            controller.command(Observation(0, 120, 0, True), 0.0).basal_u_min,
            1.0 / 60,
        )

    def test_upstream_source_hash_must_match(self):
        with tempfile.TemporaryDirectory() as root:
            wrong = Path(root) / "heuristic.py"
            wrong.write_text("changed\n")
            with patch.object(heuristic, "__file__", str(wrong)):
                with self.assertRaisesRegex(ValueError, "differs from the pinned revision"):
                    SuppliedController(SOURCE, declaration(SOURCE), seed=101)


if __name__ == "__main__":
    unittest.main()
