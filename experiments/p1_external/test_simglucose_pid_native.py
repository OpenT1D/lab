"""Method-specific checks against the pinned third-party PID implementation."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from simglucose.controller import pid_ctrller

from experiments.m1.contracts import Observation
from experiments.p1_external.intake import SuppliedController, declaration

SOURCE = Path(__file__).with_name("simglucose_pid")


class PinnedPIDTests(unittest.TestCase):
    def test_upstream_equation_reset_held_sample_and_rate_bounds(self):
        controller = SuppliedController(SOURCE, declaration(SOURCE), seed=101)
        controller.reset()
        # Upstream: P*(CGM-140) + I*integral + D*(CGM-previous)/3.
        # The first derivative uses upstream's previous=0 reset convention.
        cases = (
            (Observation(0, 140, 0, True), 0.001 * 140 / 3),
            (Observation(3, 150, 3, True), 0.001 * 10 + 0.001 * 10 / 3),
            (Observation(6, 150, 3, False), 0.001 * 10 + 0.00001 * 30),
            (Observation(9, 120, 9, True), 0.0),  # negative raw rate is bounded
        )
        for observation, expected in cases:
            with self.subTest(minute=observation.time_min):
                result = controller.command(observation, 40.0)
                self.assertAlmostEqual(result.basal_u_min, expected)
                self.assertEqual(result.bolus_u_min, 0.0)
        controller.reset()
        self.assertAlmostEqual(
            controller.command(Observation(0, 140, 0, True), 0.0).basal_u_min,
            0.001 * 140 / 3,
        )
        controller.reset()
        self.assertEqual(controller.command(Observation(0, 400, 0, True), 0.0).basal_u_min, 0.2)

    def test_upstream_source_hash_must_match(self):
        with tempfile.TemporaryDirectory() as root:
            wrong = Path(root) / "pid_ctrller.py"
            wrong.write_text("changed\n")
            with patch.object(pid_ctrller, "__file__", str(wrong)):
                with self.assertRaisesRegex(ValueError, "differs from the pinned revision"):
                    SuppliedController(SOURCE, declaration(SOURCE), seed=101)


if __name__ == "__main__":
    unittest.main()
