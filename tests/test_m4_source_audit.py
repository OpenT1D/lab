"""Independent algebraic anchors and durable source-audit failure boundaries."""

import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.source_audit.audit import burst, inventories, phi
from experiments.m4.source_audit.run import execute, matrix, read, reconstruct


class SourceAuditTests(unittest.TestCase):
    def test_pre_and_post_activation_are_different_pools(self):
        result = inventories(100, 0.5, {"p_plus": 0.2, "p_minus": 0.1, "f": 0.9})
        self.assertEqual(result["pre_bolus_recruited_ug"], 100)
        self.assertEqual(result["printed_qss_ug"], 10)
        self.assertEqual(result["finite_fusion_delivered_limit_ug"], 90)
        self.assertEqual(result["pre_to_qss_factor"], 10)

    def test_activation_threshold_and_half(self):
        self.assertEqual(phi(5, 5, 8), 0)
        self.assertEqual(phi(8, 5, 8), 0.5)

    def test_equal_rate_erlang_anchor(self):
        # H -> F -> released, both rates 2/min, no return. Poisson P(N<2).
        t = 0.7
        values = burst(t, 3, 2, 0, 2)
        self.assertAlmostEqual(values[0], 3 * math.exp(-2 * t))
        self.assertAlmostEqual(values[1], 3 * 2 * t * math.exp(-2 * t))
        self.assertAlmostEqual(values[2], 3 * (1 - (1 + 2 * t) * math.exp(-2 * t)))
        self.assertEqual(values[3], 0)

    def test_fusion_zero_returns_everything(self):
        values = burst(10, 4, 0, 1, 0.5)
        self.assertEqual(values[1:3], [0, 0])
        self.assertAlmostEqual(values[0] + values[3], 4)
        self.assertEqual(burst(0, 4, 2, 1, 0.5), [4, 0, 0, 0])

    def test_near_equal_rates_and_mass(self):
        for rate in (2 - 1e-12, 2 + 1e-12):
            values = burst(1, 3, 2, 0, rate)
            self.assertAlmostEqual(values[1], 6 * math.exp(-2), places=11)
            self.assertAlmostEqual(sum(values), 3, places=14)

    def test_invalid_inventory_and_rates(self):
        for bad in (-1, True, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                burst(1, bad, 2, 0, 1)
        with self.assertRaises(ValueError):
            inventories(1, 1.1, {"p_plus": 1, "p_minus": 1, "f": 1})
        with self.assertRaises(ValueError):
            burst(1, 1, 0, 0, 1)

    def test_nonfinite_boolean_or_incomplete_rows(self):
        for rows in ([[True, 0]], [[float("nan"), 0]], [[1]], []):
            with self.assertRaises(ValueError):
                matrix(rows, 1, 2)

    def test_failed_process_and_interruption_preserved(self):
        for exc in (subprocess.CalledProcessError(2, ["worker"]), KeyboardInterrupt()):
            with self.subTest(error=type(exc).__name__), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "run"
                with (
                    patch("experiments.m4.source_audit.run.subprocess.run", side_effect=exc),
                    patch(
                        "experiments.m4.source_audit.run.subprocess.check_output",
                        return_value="fixture",
                    ),
                ):
                    with self.assertRaises(type(exc)):
                        execute(output)
                m = read(output / "manifest.json")
                self.assertEqual(m["status"], "failed")
                self.assertIn("sources.json", m["files"])
                with self.assertRaises(ValueError):
                    reconstruct(output)

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "keep").write_text("original")
            with self.assertRaises(FileExistsError):
                execute(output)
            self.assertEqual((output / "keep").read_text(), "original")
