"""G2P2C training must not silently switch the M1 physiological engine."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from experiments.c1.g2p2c_training_preflight import (
    _check_equations,
    _check_hashes,
    _check_lock,
)


class G2P2CTrainingPreflightTests(unittest.TestCase):
    def test_meal_mass_and_termination_semantics_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            (package / "patient").mkdir()
            (package / "simulation").mkdir()
            patient = package / "patient/t1dpatient.py"
            env = package / "simulation/env.py"
            patient.write_text("Dbar = last_Qsto + last_foodtaken * 1000\n")
            env.write_text("done = BG < 10 or BG > 600\n")
            self.assertIn("1000", _check_equations(package, m1=True)["stomach_mass_expression"])
            with self.assertRaisesRegex(ValueError, "Unexpected meal-mass"):
                _check_equations(package, m1=False)
            patient.write_text("Dbar = last_Qsto + last_foodtaken\n")
            env.write_text("done = BG < 70 or BG > 350\n")
            self.assertEqual(
                _check_equations(package, m1=False)["termination_expression"],
                "BG < 70 or BG > 350",
            )
            with self.assertRaisesRegex(ValueError, "Unexpected meal-mass"):
                _check_equations(package, m1=True)

    def test_changed_source_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            (package / "model.py").write_bytes(b"pinned")
            expected = {"model.py": hashlib.sha256(b"pinned").hexdigest()}
            self.assertEqual(_check_hashes(package, expected), expected)
            (package / "model.py").write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "Unexpected simglucose"):
                _check_hashes(package, expected)

    def test_training_and_m0_locks_share_exact_engine_revision(self):
        root = Path(__file__).resolve().parents[1]
        _check_lock(root / "experiments/c1/g2p2c_training_source", root)


if __name__ == "__main__":
    unittest.main()
