"""Synthetic study identity, access and subprocess failure boundaries."""

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.common import ROOT, read, save
from experiments.m3.azt1d.fixtures import generate_study
from experiments.m3.azt1d.study import (
    fit_plan,
    freeze,
    init_ledger,
    run_study,
    supervise,
    validate_registry,
)


class AZT1DStudyBoundaries(unittest.TestCase):
    def test_invalid_deadline_cannot_open_evaluation_or_its_descriptors(self):
        with patch("experiments.m3.azt1d.study.learned_read") as access:
            for timeout in (0, -1, float("nan"), float("inf"), True):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    run_study("absent-plan", "absent-fit", "absent-output", timeout)
            access.assert_not_called()

    def test_direct_human_workers_refuse_repository_output_before_data(self):
        from experiments.m3.azt1d.worker import evaluate_worker, fit_worker

        with (
            patch("experiments.m3.azt1d.worker.plan_read", return_value=({"kind": "human"}, "x")),
            patch("experiments.m3.azt1d.worker.load_conversion") as access,
        ):
            with self.assertRaisesRegex(ValueError, "outside repository"):
                fit_worker("absent-plan", ROOT / "results/forbidden-worker")
            with self.assertRaisesRegex(ValueError, "outside repository"):
                evaluate_worker(ROOT / "results/forbidden-study", "invented", ROOT / "results/run")
            access.assert_not_called()

    def test_freeze_only_reads_metadata_and_rejects_schedule_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generate_study(root / "input", people=1, days=1)
            registry, _ = read(root / "input/registry.json")
            original = Path.read_bytes

            def metadata_only(path):
                self.assertNotIn(path.name, ("source.csv", "observations.json"))
                return original(path)

            with patch.object(Path, "read_bytes", metadata_only):
                freeze(root / "input/registry.json", root / "plan")
            altered = copy.deepcopy(registry)
            altered["people"][0]["evaluation"]["origins_us"].reverse()
            with self.assertRaisesRegex(ValueError, "evaluation schedule"):
                validate_registry(altered)
            altered = copy.deepcopy(registry)
            altered["people"].append(copy.deepcopy(altered["people"][0]))
            with self.assertRaisesRegex(ValueError, "Repeated study participant"):
                validate_registry(altered)

    def test_failed_ledger_initialization_never_launches_fit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generate_study(root / "input", people=1, days=1)
            freeze(root / "input/registry.json", root / "plan")
            init_ledger(root / "plan/plan.json")
            with self.assertRaises(ValueError):
                init_ledger(root / "plan/plan.json")
            ledger = root / "input/evaluation-access.jsonl"
            ledger.write_bytes(ledger.read_bytes() + b"partial write")
            with patch("experiments.m3.azt1d.study.supervise") as launch:
                with self.assertRaises(ValueError):
                    fit_plan(root / "plan/plan.json", root / "fit")
                launch.assert_not_called()

    def test_real_deadline_retains_partial_trace_and_safe_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "timeout"
            code = (
                "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                "(p/'trace.jsonl').write_text('partial'); time.sleep(10)"
            )
            # subprocess.wait owns the deadline; signal handlers preserve cancellation.
            with self.assertRaises(subprocess.TimeoutExpired):
                supervise([sys.executable, "-c", code], output, 0.2)
            state, _ = read(output / "state.json")
            self.assertEqual(state["status"], "interrupted")
            self.assertEqual((output / "trace.jsonl").read_text(), "partial")
            self.assertIn("trace.jsonl", state["files"])

    def test_worker_success_requires_completed_result_and_zero_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "bad"
            code = (
                "import pathlib,sys; p=pathlib.Path(sys.argv[1]); "
                "(p/'result.json').write_text('{\"status\":\"completed\"}'); sys.exit(2)"
            )
            with self.assertRaisesRegex(ValueError, "exit/status"):
                supervise([sys.executable, "-c", code], output, 5)
            state, _ = read(output / "state.json")
            self.assertEqual(state["status"], "failed")

    def test_snapshot_altered_registry_cannot_change_frozen_splits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generate_study(root / "input", people=1, days=1)
            registry, _ = read(root / "input/registry.json")
            intake_path = Path(registry["people"][0]["evaluation"]["intake_reference"]["file"])
            request, _ = read(intake_path)
            request["start_us"] += 1
            save(intake_path, request)
            with self.assertRaisesRegex(ValueError, "descriptor changed"):
                freeze(root / "input/registry.json", root / "plan")
            self.assertFalse((root / "plan").exists())
