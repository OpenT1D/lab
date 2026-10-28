"""Contract and failure tests for researcher supplied M4 secretion."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from experiments.m4.external_secretion.common import declaration, samples
from experiments.m4.external_secretion.run import execute, model_command


class ExternalSecretionContractTests(unittest.TestCase):
    def setUp(self):
        self.times = [0.0, 0.25, 0.5]
        self.glucose = [10.0, 9.0, 8.0]
        self.output = {
            "schema": "m4-model-samples/1",
            "times_min": self.times,
            "glucose_mmol_l": self.glucose,
            "secretion_pmol_kg_min": [1.0, 0.5, 0.0],
            "unit": "pmol/(kg min)",
        }

    def test_sample_contract_and_integral(self):
        forcing = samples(self.output, self.times, self.glucose)
        self.assertAlmostEqual(forcing.integral(), 0.25)
        for bad in ([1.0, 0.5], [1.0, -0.1, 0.0], [1.0, 1001.0, 0.0], [1.0, True, 0.0]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                samples({**self.output, "secretion_pmol_kg_min": bad}, self.times, self.glucose)
        with self.assertRaises(ValueError):
            samples({**self.output, "unit": "ug/min"}, self.times, self.glucose)
        with self.assertRaises(ValueError):
            samples({**self.output, "glucose_mmol_l": [10.0, 9.0, 7.0]}, self.times, self.glucose)

    def test_declaration_requires_identity_and_units(self):
        data = {
            "schema": "m4-model/1",
            "model_id": "invented/1",
            "source_sha256": hashlib.sha256(b"x").hexdigest(),
            "rights_basis": "local author",
            "dependencies": "Python standard library",
            "output_unit": "pmol/(kg min)",
        }
        self.assertEqual(declaration(data), data)
        with self.assertRaises(ValueError):
            declaration({**data, "output_unit": "ug/min"})
        with self.assertRaises(ValueError):
            declaration({**data, "source_sha256": "bad"})

    def test_model_host_executes_and_records_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / "model.py"
            request = root / "input.json"
            result = root / "result.json"
            request.write_text(
                json.dumps({"times_min": self.times, "glucose_mmol_l": self.glucose})
            )
            model.write_text(
                "def secretion(times_min, glucose_mmol_l):\n"
                "    return [g / 10 for g in glucose_mmol_l]\n"
            )
            host = (
                Path(__file__).resolve().parents[1]
                / "experiments/m4/external_secretion/model_host.py"
            )
            model_command(
                [sys.executable, "-I", str(host), str(model), str(request), str(result)], root, 5
            )
            self.assertEqual(
                json.loads(result.read_text())["secretion_pmol_kg_min"], [1.0, 0.9, 0.8]
            )
            model.write_text(
                "def secretion(times_min, glucose_mmol_l):\n    raise RuntimeError('bad model')\n"
            )
            failure = root / "failure"
            failure.mkdir()
            with self.assertRaisesRegex(RuntimeError, "Researcher model failed"):
                model_command(
                    [
                        sys.executable,
                        "-I",
                        str(host),
                        str(model),
                        str(request),
                        str(failure / "failed.json"),
                    ],
                    failure,
                    5,
                )
            self.assertIn("bad model", (failure / "model.log").read_text())

    def test_symlink_source_is_rejected_before_reference_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "model.py"
            link = root / "linked.py"
            original.write_text("def secretion(times_min, glucose_mmol_l):\n    return []\n")
            link.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "regular Python source"):
                execute(
                    root / "output", link, root / "missing.json", root / "reference", sys.executable
                )
            self.assertFalse((root / "output").exists())

    def test_source_hash_mismatch_is_rejected_before_reference_access(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / "model.py"
            declared = root / "model.json"
            model.write_text("def secretion(times_min, glucose_mmol_l):\n    return []\n")
            declared.write_text(
                json.dumps(
                    {
                        "schema": "m4-model/1",
                        "model_id": "invented/1",
                        "source_sha256": "0" * 64,
                        "rights_basis": "local author",
                        "dependencies": "Python standard library",
                        "output_unit": "pmol/(kg min)",
                    }
                )
            )
            (root / "reference").mkdir()
            with self.assertRaisesRegex(ValueError, "source hash differs"):
                execute(root / "output", model, declared, root / "reference", sys.executable)
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
