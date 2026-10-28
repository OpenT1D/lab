"""Tamper, provenance and denominator checks from a valid synthetic format fixture."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from m3_fixture import study_fixture

from experiments.m3.analysis import reconstruct
from experiments.m3.common import read, save
from experiments.m3.workflow import seal


class M3Artifacts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = study_fixture(Path(temp.name) / "study")

    def test_complete_reconstruction_without_original_inputs(self):
        report = reconstruct(self.root)
        self.assertEqual(report["study_status"], "completed")
        self.assertEqual(report["primary"]["mean_person_mae_difference"], 0)
        self.assertEqual(report["primary"]["participant_bootstrap_95"], [0, 0])
        self.assertEqual(sum(p["planned"] for p in report["people"]), 80)
        self.assertEqual(sum(p["not_attempted"] for p in report["people"]), 0)
        self.assertEqual(report, reconstruct(self.root))

    def test_actual_bytes_and_missing_provenance(self):
        trace = self.root / "p0/trace.jsonl"
        original = trace.read_bytes()
        trace.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            reconstruct(self.root)
        trace.write_bytes(original)
        state, _ = read(self.root / "p0/state.json")
        state["provenance"]["sources"] = {}
        save(self.root / "p0/state.json", state)
        with self.assertRaisesRegex(ValueError, "Source/lock"):
            reconstruct(self.root)

    def test_false_completion_even_after_resealing(self):
        case = self.root / "p0"
        trace = case / "trace.jsonl"
        trace.write_bytes(b"".join(trace.read_bytes().splitlines(keepends=True)[:-1]))
        state, _ = read(case / "state.json")
        seal(case, state)
        with self.assertRaisesRegex(ValueError, "completion"):
            reconstruct(self.root)

    def test_causal_audit_rejects_future_after_resealing(self):
        case = self.root / "p0"
        trace = case / "trace.jsonl"
        rows = [json.loads(line) for line in trace.read_text().splitlines()]
        row = next(r for r in rows if r["features"] is not None)
        row["history_rows"][-1]["available"] = row["origin"] + 5
        trace.write_text("".join(json.dumps(r) + "\n" for r in rows))
        state, _ = read(case / "state.json")
        seal(case, state)
        with self.assertRaisesRegex(ValueError, "Causal"):
            reconstruct(self.root)

    def test_study_and_case_status_agree(self):
        case = self.root / "p0"
        state, _ = read(case / "state.json")
        state.update(status="interrupted", error={"type": "RunInterrupted", "frames": []})
        seal(case, state)
        with self.assertRaisesRegex(ValueError, "status differs"):
            reconstruct(self.root)
        study, _ = read(self.root / "study.json")
        study["cases"][0]["status"] = "interrupted"
        save(self.root / "study.json", study)
        with self.assertRaisesRegex(ValueError, "False study"):
            reconstruct(self.root)
        study["status"] = "finished_with_failures"
        save(self.root / "study.json", study)
        result = reconstruct(self.root)
        self.assertEqual(result["primary"]["paired_people"], 1)
        self.assertIsNone(result["primary"]["participant_bootstrap_95"])

    def test_unattempted_case_stays_in_denominator(self):
        shutil.rmtree(self.root / "p1")
        study, _ = read(self.root / "study.json")
        study.update(status="interrupted")
        study["cases"][1]["status"] = "not_attempted"
        save(self.root / "study.json", study)
        result = reconstruct(self.root)
        self.assertEqual(result["people"][1]["not_attempted"], 40)
        self.assertEqual(result["people"][1]["predicted"], 0)
        self.assertEqual(result["primary"]["excluded_people"], ["p1"])
        self.assertEqual(
            sum(group["planned"] for group in result["people"][1]["origin_strata"].values()),
            40,
        )

    def test_partial_fragment_preserved_and_counted(self):
        case = self.root / "p0"
        trace = case / "trace.jsonl"
        trace.write_bytes(
            b"".join(trace.read_bytes().splitlines(keepends=True)[:15]) + b'{"partial":'
        )
        state, _ = read(case / "state.json")
        state.update(status="interrupted", error={"type": "RunInterrupted"})
        seal(case, state)
        study, _ = read(self.root / "study.json")
        study["status"] = "interrupted"
        study["cases"][0]["status"] = "interrupted"
        save(self.root / "study.json", study)
        result = reconstruct(self.root)
        self.assertEqual(result["people"][0]["attempted"], 15)
        self.assertEqual(result["people"][0]["not_attempted"], 25)
        self.assertTrue(result["people"][0]["partial_fragment"])
        self.assertEqual(result["people"][0]["planned"], 40)

    def test_unbound_model_and_changed_split(self):
        plan, _ = read(self.root / "plan.json")
        plan["registry"]["people"][0]["train"]["end"] = 700
        save(self.root / "plan.json", plan)
        with self.assertRaises(ValueError):
            reconstruct(self.root)
