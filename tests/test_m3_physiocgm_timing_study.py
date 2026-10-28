"""Synthetic artifact and execution-boundary checks, without human-file access."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.analysis import _Snapshot
from experiments.m3.common import ROOT, digest, encoded
from experiments.m3.physiocgm_timing import study
from experiments.m3.physiocgm_timing.common import RADII_US, SCHEMA


class TimingSyntheticStudy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "example"

    def completed(self):
        with patch("experiments.m3.estimator.fit", side_effect=AssertionError("No fitting")):
            study.demo(self.output)
        return self.output

    def reseal(self, name):
        path = self.output / "inventory.json"
        inventory = json.loads(path.read_bytes())
        inventory["files"][name] = digest((self.output / name).read_bytes())
        path.write_bytes(encoded(inventory))

    def test_demo_and_fresh_process_reconstruction_without_site_packages(self):
        self.completed()
        result = json.loads((self.output / "result.json").read_bytes())
        self.assertTrue(result["complete_execution_cohort"])
        for person in ("invented-a", "invented-b"):
            counts = [result["variants"][str(r)]["people"][person]["scored"] for r in RADII_US]
            self.assertLess(counts[0], counts[1])
            self.assertLess(counts[1], counts[2])
        process = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m3.physiocgm_timing",
                "verify",
                "--study",
                str(self.output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        verified = json.loads(process.stdout)
        self.assertTrue(verified["zero_radius_equivalence"])
        self.assertTrue(verified["nested_sets_verified"])
        self.assertFalse(verified["model_refitted"])

    def test_human_plan_is_rejected_before_payload_reads(self):
        self.output.mkdir()
        (self.output / "plan.json").write_bytes(encoded({"schema": SCHEMA, "kind": "human"}))
        (self.output / "model.json").write_text("must remain unopened")
        reads = []
        original = _Snapshot.read

        def protected(snapshot, name):
            reads.append(name)
            self.assertEqual(name, "plan.json")
            return original(snapshot, name)

        with patch.object(_Snapshot, "read", protected), self.assertRaises(ValueError):
            study.verify(self.output)
        self.assertEqual(reads, ["plan.json"])

    def test_changed_plan_is_rejected_before_payload_reads(self):
        self.completed()
        plan = json.loads((self.output / "plan.json").read_bytes())
        plan["rules"]["radii_us"] = [0, 1_000_000, 30_000_000]
        (self.output / "plan.json").write_bytes(encoded(plan))
        original = _Snapshot.read

        def protected(snapshot, name):
            self.assertEqual(name, "plan.json")
            return original(snapshot, name)

        with patch.object(_Snapshot, "read", protected), self.assertRaises(ValueError):
            study.verify(self.output)

    def test_changed_trace_is_rejected_even_with_updated_inventory(self):
        self.completed()
        name = "invented-a/radius-1000000.jsonl"
        path = self.output / name
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        row = next(row for row in rows if row["forecasts"] is not None)
        row["forecasts"]["ridge"] += 1
        path.write_bytes(b"".join(json.dumps(row).encode() + b"\n" for row in rows))
        self.reseal(name)
        with self.assertRaisesRegex(ValueError, "forecast or timing"):
            study.verify(self.output)

    def test_changed_fixed_model_is_rejected_even_with_updated_inventory(self):
        self.completed()
        path = self.output / "model.json"
        model = json.loads(path.read_bytes())
        model["intercept"] += 1
        path.write_bytes(encoded(model))
        self.reseal("model.json")
        with self.assertRaisesRegex(ValueError, "fixed invented input"):
            study.verify(self.output)

    def test_failure_keeps_prefix_and_repeated_attempt_cannot_replace_it(self):
        actual = study.forecast_rows

        def failing(*args):
            for index, row in enumerate(actual(*args)):
                if index == 2:
                    raise ValueError("Invented failure")
                yield row

        with patch.object(study, "forecast_rows", failing), self.assertRaises(ValueError):
            study.demo(self.output)
        state = json.loads((self.output / "state.json").read_bytes())
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["cases"]["0"]["invented-a"], "failed")
        self.assertEqual(state["cases"]["0"]["invented-b"], "not_attempted")
        self.assertEqual(
            len((self.output / "invented-a/radius-0.jsonl").read_bytes().splitlines()), 2
        )
        self.assertTrue((self.output / "inventory.json").is_file())
        before = {str(p): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        with self.assertRaises(ValueError):
            study.demo(self.output)
        self.assertEqual(
            before, {str(p): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        )
        with self.assertRaises(ValueError):
            study.verify(self.output)

    def test_zero_discrepancy_prevents_any_wider_variant(self):
        actual = study.exact_forecasts

        def corrupted(*args):
            for row in actual(*args):
                row = copy.deepcopy(row)
                row["reason"] = "invented-disagreement"
                yield row

        with patch.object(study, "exact_forecasts", corrupted), self.assertRaises(ValueError):
            study.demo(self.output)
        state = json.loads((self.output / "state.json").read_bytes())
        for radius in RADII_US[1:]:
            self.assertEqual(set(state["cases"][str(radius)].values()), {"not_attempted"})
            self.assertFalse(list(self.output.rglob(f"radius-{radius}.jsonl")))


if __name__ == "__main__":
    unittest.main()
