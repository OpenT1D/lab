"""Source declaration, causal callback and fail-closed contract checks."""

import json
import math
import tempfile
import unittest
from pathlib import Path

from experiments.m4.causal_secretion.common import (
    declaration,
    evaluate,
    load_model,
    preflight,
    protocol,
    read,
)
from experiments.m4.causal_secretion.run import execute

HERE = Path(__file__).resolve().parents[1] / "experiments/m4/causal_secretion"
BC = Path(__file__).resolve().parents[1] / "experiments/m4/feedback/protocol.json"


class CausalSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.task = protocol(read(HERE / "protocol.json"), read(BC))
        self.declared = declaration(read(HERE / "example_model.json"))

    def test_example_baseline_and_out_of_order_purity(self):
        fn = load_model(HERE / "example_model.py")
        check = preflight(fn, 0.8, 138.56, self.declared["parameters"], self.task)
        self.assertTrue(check["passed"])
        self.assertEqual(check["equilibrium_error"], 0)

    def test_changed_protocol_and_units_are_refused(self):
        with self.assertRaises(ValueError):
            protocol({**self.task, "max_rate_pmol_kg_min": 2000}, read(BC))
        with self.assertRaises(ValueError):
            declaration({**self.declared, "output_unit": "ug/min"})
        with self.assertRaises(ValueError):
            declaration({**self.declared, "parameters": {"gain": math.nan}})

    def test_bad_source_results_and_hidden_state_fail_preflight(self):
        args = (0.0, 138.56, 0.0, 0.8, 0.8, 138.56, {}, self.task)
        for result in ([0], [0, -1], [0, math.nan], [True, 0.8], [2000, 0.8]):
            with self.subTest(result=result), self.assertRaises(ValueError):
                evaluate(lambda *unused: result, *args)
        calls = 0

        def hidden(*unused):
            nonlocal calls
            calls += 1
            return [0, 0.8 + calls * 0.01]

        with self.assertRaisesRegex(ValueError, "out-of-order"):
            preflight(hidden, 0.8, 138.56, {}, self.task)

    def test_bad_source_hash_rejected_before_reference_read(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "model.py"
            declared = folder / "model.json"
            source.write_text("def evaluate(*args):\n    return [0, 0]\n")
            declared.write_text(json.dumps({**self.declared, "source_sha256": "0" * 64}))
            (folder / "reference").mkdir()
            with self.assertRaisesRegex(ValueError, "source hash differs"):
                execute(folder / "result", source, declared, folder / "reference")
            self.assertFalse((folder / "result").exists())

    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "model.py"
            link = folder / "linked.py"
            source.write_text("def evaluate(*args):\n    return [0, 0]\n")
            link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "regular Python source"):
                execute(folder / "result", link, folder / "missing.json", folder / "missing")


if __name__ == "__main__":
    unittest.main()
