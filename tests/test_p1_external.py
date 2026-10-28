"""Contract and failure checks for the bounded external-controller workflow."""

import hashlib
import importlib
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m1.contracts import Observation
from experiments.p1_external.intake import SuppliedController, declaration, smoke

p1 = importlib.import_module("experiments.p1_external.__main__")
EXAMPLE = Path(__file__).resolve().parents[1] / "experiments/p1_external/example"


def copied_source(root):
    source = Path(root) / "source"
    shutil.copytree(EXAMPLE, source)
    return source


def replace_source(source, code):
    (source / "controller.py").write_text(code)
    metadata = json.loads((source / "controller.json").read_text())
    metadata["source_sha256"] = hashlib.sha256(code.encode()).hexdigest()
    (source / "controller.json").write_text(json.dumps(metadata) + "\n")


class ExternalControllerTests(unittest.TestCase):
    def test_source_hash_capabilities_and_regular_files_are_required(self):
        with tempfile.TemporaryDirectory() as root:
            source = copied_source(root)
            metadata = declaration(source)
            self.assertEqual(metadata["step_minutes"], 3)
            (source / "controller.py").write_text("pass\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                declaration(source)
            replace_source(source, "pass\n")
            metadata = json.loads((source / "controller.json").read_text())
            metadata["missing_sensor"] = False
            (source / "controller.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "capabilities"):
                declaration(source)
            (source / "extra.py").write_text("")
            with self.assertRaisesRegex(ValueError, "exactly two"):
                declaration(source)

    def test_causal_callback_gap_and_action_shape(self):
        metadata = declaration(EXAMPLE)
        smoke(EXAMPLE, metadata)
        controller = SuppliedController(EXAMPLE, metadata, seed=101)
        controller.reset()
        fresh = controller.command(Observation(0, 200, 0, True), 0)
        held = controller.command(Observation(3, 200, 0, False), 0)
        self.assertGreater(fresh.basal_u_min, held.basal_u_min)
        self.assertEqual(held.basal_u_min, 0.02)
        self.assertEqual(held.bolus_u_min, 0)
        with self.assertRaisesRegex(ValueError, "Unexpected observation clock"):
            controller.command(Observation(9, 200, 9, True), 0)

    def test_bad_action_preserves_failed_cases_and_reconstructs(self):
        with tempfile.TemporaryDirectory() as root:
            source = copied_source(root)
            replace_source(
                source,
                "class Controller:\n"
                "    def reset(self): pass\n"
                "    def command(self, observation, announced_g):\n"
                "        return {'basal_u_min': float('nan'), 'bolus_u_min': 0}\n"
                "def make_controller(seed): return Controller()\n",
            )
            study = Path(root) / "study"
            fake_runtime = types.ModuleType("experiments.m1.runtime")

            def fake_native(_config, _checkpoint, _initial, _output, _manifest, *, controller):
                controller.reset()
                controller.command(Observation(0, 140, 0, True), 0)

            fake_runtime.native_run = fake_native
            with (
                patch.object(p1, "require_runtime"),
                patch.dict(sys.modules, {"experiments.m1.runtime": fake_runtime}),
            ):
                with self.assertRaisesRegex(RuntimeError, "cases failed"):
                    p1.run(source, study, "adult#001", 101)
            self.assertEqual(
                json.loads((study / "study.json").read_text())["status"],
                "finished_with_failures",
            )
            for condition in "ABCD":
                case = json.loads((study / condition / "manifest.json").read_text())
                self.assertEqual(case["status"], "failed")
                self.assertEqual(case["completed_rows"], 0)
                self.assertIn("finite number", case["error"])
            rebuilt = Path(root) / "rebuilt"
            p1.reconstruct(study, rebuilt)
            self.assertTrue(
                json.loads((rebuilt / "reconstruction.json").read_text())[
                    "byte_identical_to_original"
                ]
            )
            (study / "A" / "trace.jsonl").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "artifact differs"):
                p1.reconstruct(study, Path(root) / "tampered")

    def test_source_only_replay_detects_changed_action(self):
        from experiments.m1.contracts import Row
        from experiments.p1_external.intake import replay

        row = Row(
            0,
            3,
            140.0,
            140.0,
            True,
            140.0,
            0,
            0.0,
            0.0,
            0.03,
            0.0,
            0.02,
            False,
        )
        with self.assertRaisesRegex(ValueError, "replay differs"):
            replay(EXAMPLE, declaration(EXAMPLE), 101, [row])


if __name__ == "__main__":
    unittest.main()
