"""Study schedule, evaluation boundary and complete-pair reporting counterexamples."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest
from experiments.m2.report import comparisons, reconstruct
from experiments.m2.run import ROOT, source_hashes
from experiments.m2.simglucose import evaluation_gate, validate_config
from experiments.m2.study import cases, locks, validate_plan_data


def plan():
    return {
        "schema": "opent1d.m2-freeze/1",
        "revision": "a" * 40,
        "source_sha256": source_hashes(),
        "locks_sha256": locks(),
        "protocol_sha256": digest(ROOT / "docs/research/m2-protocol.md"),
        "development_verified": True,
        "evaluation_previously_inspected": False,
        "development_report_sha256": "b" * 64,
        "native_verification_sha256": "c" * 64,
        "cases": cases("evaluation"),
    }


class M2StudyTests(unittest.TestCase):
    def test_exact_splits_and_no_fictitious_cambridge_cohort(self):
        dev, evaluation = cases("development"), cases("evaluation")
        self.assertEqual(len(dev), 40)
        self.assertEqual(len(evaluation), 648)
        self.assertEqual(len({c["id"] for c in evaluation}), 648)
        self.assertEqual(
            sum(c["evidence_track"] == "structural_development" for c in evaluation), 8
        )
        profiles = {
            c["config"]["profile"] for c in evaluation if c["config"]["engine"] == "simglucose"
        }
        self.assertEqual(profiles, {f"adult#{p:03}" for p in range(3, 11)})
        self.assertTrue(all(c["config"]["profile"] not in profiles for c in dev))

    def test_evaluation_is_not_available_without_unchanged_frozen_sources(self):
        cfg = cases("evaluation")[0]["config"]
        validate_config(cfg)
        with self.assertRaisesRegex(ValueError, "frozen plan"):
            evaluation_gate(cfg, None)
        frozen = plan()
        validate_plan_data(frozen)
        for change in (
            {"development_verified": False},
            {"evaluation_previously_inspected": True},
            {"source_sha256": {}},
            {"locks_sha256": {}},
            {"cases": frozen["cases"][:-1]},
        ):
            with self.assertRaises(ValueError):
                validate_plan_data(frozen | change)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            write_json(path, frozen)
            with patch(
                "experiments.m2.study.subprocess.check_output",
                side_effect=[("a" * 40 + "\n"), b" M source.py"],
            ):
                with self.assertRaisesRegex(ValueError, "clean"):
                    evaluation_gate(cfg, path)

    def test_unattempted_runs_remain_visible_and_false_completion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            schedule = {
                "schema": "opent1d.m2-study/1",
                "phase": "development",
                "status": "started",
                "cases": cases("development"),
            }
            write_json(root / "study.json", schedule)
            report = reconstruct(root)
            self.assertEqual(json.loads(json.dumps(report)), report)
            self.assertEqual(report["scheduled"], 40)
            self.assertEqual(report["tracks"]["simglucose"]["status_counts"], {"scheduled": 32})
            for phase in ("completed", "finished_with_failures"):
                write_json(root / "study.json", schedule | {"status": phase})
                with self.assertRaises(ValueError):
                    reconstruct(root)
            write_json(root / "study.json", schedule | {"cases": schedule["cases"][:-1]})
            with self.assertRaisesRegex(ValueError, "entire"):
                reconstruct(root)

    def test_partial_native_run_requires_actual_interpreter_provenance(self):
        # Entirely synthetic trace/provenance fixture; no native execution claim.
        from dataclasses import asdict

        from test_m1_artifacts import Initial, native_metadata

        from experiments.m1.contracts import Row
        from experiments.m2.simglucose import read_run

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cfg = cases("development")[0]["config"]
            native = {"config": cfg}
            native_metadata(native)
            native.update(
                upstream_revision="a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc",
                python="synthetic",
                platform="synthetic",
                architecture="synthetic",
            )
            write_json(root / "config.json", cfg)
            write_json(root / "initial.json", asdict(Initial()))
            write_json(root / "warnings.json", [])
            (root / "trace.jsonl").write_text(
                json.dumps(asdict(Row(0, 3, 100, 101, True, 101, 0, 0, 0, 0.02, 0, 0.02, False)))
                + "\n"
            )
            (root / "native.jsonl").touch()
            (root / "run.log").touch()
            (root / "protocol.md").write_bytes((ROOT / "docs/research/m2-protocol.md").read_bytes())
            for name in ("uv.lock", "protocol-settings.json", "baseline.json"):
                (root / ("simglucose-" + name)).write_bytes(
                    (ROOT / "experiments/m0/simglucose" / name).read_bytes()
                )
            manifest = {
                "schema": "opent1d.simglucose-m2/1",
                "status": "failed",
                "config": cfg,
                "error": "synthetic failure",
                "elapsed_seconds": 0,
                "completed_rows": 1,
                "source_sha256": source_hashes(),
                "revision": "a" * 40,
                "worktree_dirty": False,
            }

            def seal(runtime):
                write_json(root / "runtime.json", runtime)
                manifest["files_sha256"] = {
                    p.name: digest(p) for p in root.iterdir() if p.name != "manifest.json"
                }
                write_json(root / "manifest.json", manifest)

            seal(native)
            self.assertEqual(read_run(root)["manifest"]["status"], "failed")
            for key in ("python", "platform", "architecture"):
                seal({k: v for k, v in native.items() if k != key})
                with self.assertRaisesRegex(ValueError, "native " + key):
                    read_run(root)

    def test_rank_reversals_and_insufficient_comparisons(self):
        records = []
        for c in cases("development"):
            if c["config"]["engine"] != "lt1_cambridge":
                continue
            cfg = c["config"]
            delta = (
                {"A": 10, "B": -10, "C": 0, "D": 5}[cfg["condition"]]
                if cfg["controller"] == "lt1_mpc"
                else 0
            )
            records.append(
                dict(
                    c,
                    status="completed",
                    metrics={
                        "glucose": {
                            "in_70_180_percent": 50 + delta,
                            "below_70_percent": 10 - delta,
                            "below_54_percent": 5,
                        }
                    },
                )
            )
        result = comparisons(records, "lt1_cambridge")
        self.assertTrue(
            result["rank_reversals"][0]["outcomes"]["in_70_180_percent"][
                "rank_reversal_across_conditions"
            ]
        )
        self.assertIsNone(
            result["paired"][0]["across_profiles"]["in_70_180_percent"]["sign_reversal"]
        )
        records[-1]["status"] = "failed"
        result = comparisons(records, "lt1_cambridge")
        self.assertIsNone(
            result["rank_reversals"][0]["outcomes"]["in_70_180_percent"][
                "rank_reversal_across_conditions"
            ]
        )
        self.assertEqual(len(result["paired"][-1]["excluded_pairs"]), 1)
