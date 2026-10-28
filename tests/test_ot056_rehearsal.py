"""Real two-task software acceptance, relocation, fresh execution and forgery refusal."""

import shutil
import tempfile
import unittest
from pathlib import Path

from experiments.catalogue.storage import dump, read, seal
from experiments.ot056_pilot.rehearsal import rehearse, verify
from experiments.ot056_pilot.sampling import task2, verify_task2
from experiments.ot056_pilot.technical import task1


def reseal(path):
    (path / "manifest.json").unlink()
    seal(path)


class CombinedRehearsalTests(unittest.TestCase):
    def test_both_actual_chains_relocate_repeat_and_reject_resealed_forgery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = rehearse(root / "original")
            self.assertTrue(result["technical_complete"])
            self.assertEqual(result["task1_cases"], 11)
            self.assertEqual(len(result["task2_comparisons"]), 11)
            self.assertEqual(result["human_sessions"], 0)
            self.assertEqual(result["human_pilot"], "open")
            self.assertIsNone(result["product_decision"])
            self.assertTrue(all(result["registered_tasks_ready"].values()))
            shutil.move(root / "original", root / "relocated")
            archive = root / "relocated"
            self.assertFalse((root / "original").exists())
            self.assertEqual(verify(archive, root / "checked"), result)

            # Both repeat executions invoke fresh native CLI processes. Compare
            # scientific content, preserving each route's distinct process logs.
            first = task1(
                archive / "task1/control-increase-inputs",
                archive / "task1/control-increase-inputs/settings.json",
                root / "task1-repeat",
            )
            saved = read(archive / "task1/technical.json")
            self.assertEqual(
                first["matched_sha256"], saved["comparisons"]["control-increase"]["matched_sha256"]
            )
            second = task2(
                archive / "task2-inputs/information-loss",
                archive / "task1/settings.json",
                root / "task2-repeat",
            )
            self.assertEqual(
                second["matched_sha256"],
                result["task2_comparisons"]["information-loss"]["matched_sha256"],
            )

            trap = archive / "task2-inputs/invalid-omitted-cells/observations.csv"
            original = trap.read_bytes()
            trap.write_bytes(original + b"changed\n")
            reseal(archive / "task2-inputs")
            reseal(archive)
            with self.assertRaisesRegex(ValueError, "trusted synthetic construction"):
                verify(archive, root / "wrong-trap")
            trap.write_bytes(original)
            reseal(archive / "task2-inputs")
            reseal(archive)

            snapshot = archive / "task2/task2-A/inputs/observations.csv"
            original = snapshot.read_bytes()
            snapshot.write_bytes(original + b"changed\n")
            reseal(archive / "task2/task2-A")
            reseal(archive)
            with self.assertRaisesRegex(ValueError, "named canonical case"):
                verify(archive, root / "wrong-case")
            snapshot.write_bytes(original)
            reseal(archive / "task2/task2-A")
            reseal(archive)

            comparison = root / "task2-repeat"
            receipt = read(comparison / "comparison.json")
            receipt["coverage"]["planned_people"] += 1
            dump(comparison / "comparison.json", receipt)
            reseal(comparison)
            with self.assertRaisesRegex(ValueError, "coverage or scientific hashes"):
                verify_task2(comparison, root / "wrong-coverage")

            result["human_sessions"] = 6
            result["product_decision"] = "go"
            dump(archive / "technical.json", result)
            reseal(archive)
            with self.assertRaisesRegex(ValueError, "cannot supply human or product acceptance"):
                verify(archive, root / "invented-humans")


if __name__ == "__main__":
    unittest.main()
