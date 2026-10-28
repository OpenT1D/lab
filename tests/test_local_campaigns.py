"""Frozen native configurations, immutable resume, exact coverage and failure evidence."""

import json
import shutil
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.campaigns import common, native, report, run


def preparation(path):
    path = Path(path).absolute()
    config = common.read(path)
    if config["schema"] != "m4-initial-load-config/1":
        raise ValueError("Invalid native configuration")
    sources = {}
    for source in config["sources"]:
        model, declaration = (path.parent / source[name] for name in ("model", "declaration"))
        declared = common.read(declaration)
        if declared["source_sha256"] != common.digest(model.read_bytes()):
            raise ValueError("Source hash differs")
        sources[source["id"]] = {
            "declaration": declared,
            "source_sha256": declared["source_sha256"],
            "declaration_sha256": common.digest(declaration.read_bytes()),
            "model_path": str(model),
            "declaration_path": str(declaration),
        }
    locks = [
        f"{project}/{name}"
        for project in (
            "experiments/m0/simglucose",
            "experiments/m4/beta_cell/runtime",
        )
        for name in ("uv.lock", "pyproject.toml")
    ]
    return {
        "schema": "m4-initial-load-preparation/1",
        "configuration": config,
        "config_sha256": common.digest(path.read_bytes()),
        "source_order": [source["id"] for source in config["sources"]],
        "sources": sources,
        "scenarios": [
            {"id": identity, "initial_gastric_solid_mg": 0} for identity in config["scenarios"]
        ],
        "protocol": {"id": "M4-STUDY/1", "test_fixture": True},
        "protocol_sha256": "a" * 64,
        "runtime_files_sha256": {
            name: common.digest((common.ROOT / name).read_bytes()) for name in locks
        },
        "implementation_sources_sha256": {
            "experiments/m4/causal_secretion/common.py": common.digest(
                (common.ROOT / "experiments/m4/causal_secretion/common.py").read_bytes()
            )
        },
    }


def native_reader(directory):
    directory = Path(directory)
    manifest = common.read(directory / "manifest.json")
    config = common.read(directory / "config.json")
    return {
        "schema": "m4-initial-load-report/1",
        "passed": manifest["status"] == "completed",
        "status": manifest["status"],
        "protocol": "M4-STUDY/1",
        "configuration": config,
        "scenarios": [
            {"id": scene, "initial_gastric_solid_mg": 0} for scene in config["scenarios"]
        ],
        "sources": {
            source["id"]: {
                "status": manifest["status"],
                "accepted": manifest["status"] == "completed",
            }
            for source in config["sources"]
        },
        "denominators": {
            "source_scenarios": len(config["sources"]) * len(config["scenarios"]),
            "accepted_source_scenarios": len(config["sources"]) * len(config["scenarios"])
            if manifest["status"] == "completed"
            else 0,
        },
    }


def runtimes():
    return {
        project: {"python": "3.12.13", "implementation": "CPython", "packages": packages}
        for project, packages in (
            (".", {}),
            ("experiments/m0/simglucose", common.NATIVE_VERSIONS),
            ("experiments/m4/beta_cell/runtime", common.OBSERVER_VERSIONS),
        )
    }


def configuration(directory, *, cells=2, repeats=2, source=None):
    directory.mkdir()
    model = common.ROOT / "experiments/m4/causal_secretion/example_model.py"
    raw = model.read_bytes() if source is None else source.encode()
    (directory / "model.py").write_bytes(raw)
    common.dump(
        directory / "model.json",
        common.read(model.with_suffix(".json")) | {"source_sha256": common.digest(raw)},
    )
    roster = []
    for index in range(cells):
        identity = f"cell{index + 1}"
        child = {
            "schema": "m4-initial-load-config/1",
            "sources": [
                {"id": name, "model": "model.py", "declaration": "model.json"}
                for name in ("one", "two")
            ],
            "scenarios": ["fasting"],
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }
        common.dump(directory / (identity + ".json"), child)
        roster.append({"id": identity, "config": identity + ".json"})
    config = {
        "schema": common.CONFIG_SCHEMA,
        "task": "m4-study",
        "cells": roster,
        "repeats": repeats,
        "timeout_seconds": 10800,
    }
    common.dump(directory / "campaign.json", config)
    return directory / "campaign.json", config


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.patches = [
            patch.object(native, "prepare", side_effect=preparation),
            patch.object(native, "reconstruct", side_effect=native_reader),
            patch.object(common, "runtime_identity", side_effect=runtimes),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.directory.cleanup()

    def worker(self, argv, logfile, timeout, control, *, failed=False):
        archive = Path(argv[argv.index("--output") + 1])
        archive.mkdir()
        source_config = Path(argv[argv.index("--config") + 1])
        (archive / "config.json").write_bytes(source_config.read_bytes())
        common.dump(archive / "manifest.json", {"status": "failed" if failed else "completed"})
        logfile.write_text(json.dumps({"argv": argv, "timeout_seconds": timeout}) + "\n")
        return (1, "WorkerExit") if failed else (0, None)

    def test_passive_check_and_standalone_freeze_do_not_import_source(self):
        marker = self.root / "imported"
        path, config = configuration(
            self.root / "inputs",
            source=f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
        )
        checked = common.check(path)
        self.assertFalse(checked["source_executed"])
        self.assertEqual(checked["planned_slots"], 4)
        campaign = run.freeze(path, self.root / "campaign")
        original = (campaign / "manifest.json").read_bytes()
        shutil.rmtree(path.parent)
        plan, summary = report.inspect(campaign)
        self.assertEqual(plan["configuration"], config)
        self.assertEqual(summary["planned_source_scenarios"], 8)
        self.assertEqual(summary["accepted_slots"], 0)
        self.assertFalse(marker.exists())
        self.assertEqual((campaign / "manifest.json").read_bytes(), original)

    def test_config_rejects_unknown_task_unsafe_roster_budgets_and_large_matrix(self):
        _, config = configuration(self.root / "inputs")
        for edit in (
            {"task": "m3-forecast"},
            {"extra": True},
            {"repeats": True},
            {"repeats": 9},
            {"timeout_seconds": 0},
            {"timeout_seconds": 10801},
            {"cells": []},
            {"cells": config["cells"] * 2},
        ):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                common.validate_config(config | edit)
        too_many = config | {
            "cells": [{"id": f"c{i}", "config": "x"} for i in range(32)],
            "repeats": 8,
        }
        with self.assertRaisesRegex(ValueError, "128 slots"):
            common.validate_config(too_many)
        for identity in ("../escape", "Bad", "", "same/other"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                common.validate_config(config | {"cells": [{"id": identity, "config": "x"}]})

    def test_initial_cell_major_schedule_accepts_all_and_reconstruction_is_exact(self):
        path, _ = configuration(self.root / "inputs")
        dispatched = []

        def worker(argv, log, budget, control):
            dispatched.append(Path(argv[-1]).parent.name)
            return self.worker(argv, log, budget, control)

        with patch.object(run, "supervise", side_effect=worker):
            result = run.run_study(path, self.root / "campaign")
        self.assertEqual(dispatched, ["cell1--r001", "cell1--r002", "cell2--r001", "cell2--r002"])
        self.assertTrue(result["passed"])
        self.assertEqual(result["accepted_slots"], result["planned_slots"])
        self.assertEqual(result["accepted_source_scenarios"], 8)
        compact = result["slots"][0]["attempts"][0]["native_report"]
        self.assertEqual(compact["denominators"]["source_scenarios"], 2)
        self.assertEqual(compact["configuration"]["scenarios"], ["fasting"])
        self.assertEqual(set(compact["sources"]), {"one", "two"})
        self.assertTrue(all(source["accepted"] for source in compact["sources"].values()))
        rebuilt = self.root / "rebuilt"
        self.assertEqual(report.reconstruct(self.root / "campaign", rebuilt), result)
        for name in common.REPORTS:
            self.assertEqual(
                (rebuilt / name).read_bytes(),
                (self.root / "campaign/sessions/session-0001" / name).read_bytes(),
            )

    def test_failed_attempt_is_retained_retry_links_manifest_and_accepted_slots_are_reused(self):
        path, _ = configuration(self.root / "inputs")
        calls = 0

        def first(argv, log, budget, control):
            nonlocal calls
            calls += 1
            return self.worker(argv, log, budget, control, failed=calls == 1)

        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=first):
            original_report = run.run_study(path, campaign)
        self.assertFalse(original_report["passed"])
        self.assertEqual(original_report["accepted_slots"], 3)
        root_bytes = (campaign / "manifest.json").read_bytes()
        previous_bytes = common.inventory(campaign / "sessions/session-0001")
        with patch.object(run, "supervise", side_effect=self.worker) as worker:
            resumed = run.resume(campaign)
        self.assertEqual(worker.call_count, 1)
        self.assertTrue(resumed["passed"])
        attempts = resumed["slots"][0]["attempts"]
        self.assertEqual(len(attempts), 2)
        self.assertEqual(
            attempts[1]["previous_attempt_manifest_sha256"], attempts[0]["manifest_sha256"]
        )
        self.assertEqual(attempts[0]["outcome"]["status"], "failed")
        self.assertEqual((campaign / "manifest.json").read_bytes(), root_bytes)
        self.assertEqual(common.inventory(campaign / "sessions/session-0001"), previous_bytes)

    def test_global_interruption_then_explicit_resume_retains_full_denominator(self):
        path, _ = configuration(self.root / "inputs")

        def interrupted(argv, log, budget, control):
            result = self.worker(argv, log, budget, control)
            signal.raise_signal(signal.SIGTERM)
            return result

        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=interrupted) as worker:
            initial = run.run_study(path, campaign)
        self.assertEqual(worker.call_count, 1)
        self.assertEqual(initial["status"], "interrupted")
        self.assertEqual(initial["accepted_slots"], 0)
        self.assertEqual(initial["planned_slots"], 4)
        self.assertEqual(initial["slots"][0]["attempts"][0]["outcome"]["status"], "interrupted")
        self.assertEqual([len(slot["attempts"]) for slot in initial["slots"]], [1, 0, 0, 0])
        with patch.object(run, "supervise", side_effect=self.worker) as worker:
            resumed = run.resume(campaign)
        self.assertEqual(worker.call_count, 4)
        self.assertTrue(resumed["passed"])
        self.assertEqual([len(slot["attempts"]) for slot in resumed["slots"]], [2, 1, 1, 1])

    def test_failed_reconstruction_needs_opt_in_and_preserves_null_native_evidence(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=OSError("controlled launch failure")):
            initial = run.run_study(path, campaign)
        self.assertFalse(initial["passed"])
        attempt = initial["slots"][0]["attempts"][0]
        self.assertIsNone(attempt["native_report"])
        self.assertIsNone(attempt["outcome"]["native_manifest_sha256"])
        with self.assertRaisesRegex(ValueError, "allow-failed"):
            report.reconstruct(campaign)
        self.assertEqual(report.reconstruct(campaign, self.root / "failed-rebuilt", True), initial)

    def test_existing_and_overlapping_outputs_cannot_be_replaced(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = run.freeze(path, self.root / "campaign")
        with self.assertRaises(FileExistsError):
            run.freeze(path, campaign)
        with self.assertRaises(ValueError):
            run.freeze(path, path.parent)
        with self.assertRaises(ValueError):
            report.reconstruct(campaign, campaign / "nested", True)
        with self.assertRaises(ValueError):
            report.reconstruct(campaign, self.root, True)

    def test_unsealed_hard_kill_session_is_retained_but_cannot_resume(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = run.freeze(path, self.root / "campaign")
        session = campaign / "sessions/session-0001"
        session.mkdir()
        (session / "raw-evidence").write_text("unsealed")
        with self.assertRaisesRegex(ValueError, "Unsealed session"):
            run.resume(campaign)
        self.assertEqual((session / "raw-evidence").read_text(), "unsealed")

    def test_changed_frozen_source_or_output_is_rejected_before_reuse(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=self.worker):
            run.run_study(path, campaign)
        frozen = campaign / "frozen/cell1/sources/one/model.py"
        original = frozen.read_bytes()
        frozen.write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "Frozen campaign inventory"):
            run.resume(campaign)
        frozen.write_bytes(original)
        native_config = campaign / "sessions/session-0001/attempts/cell1--r001/archive/config.json"
        native_config.write_text("changed output\n")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            run.resume(campaign)
        self.assertFalse((campaign / "sessions/session-0002").exists())

    def test_changed_actual_runtime_and_native_protocol_block_resume(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=self.worker):
            run.run_study(path, campaign)
        changed = runtimes()
        changed["."]["python"] = "3.12.99"
        with (
            patch.object(common, "runtime_identity", return_value=changed),
            self.assertRaisesRegex(ValueError, "runtime identity changed"),
        ):
            run.resume(campaign)

        def amended(path):
            result = preparation(path)
            result["protocol"] = {"id": "M4-STUDY/2"}
            return result

        with (
            patch.object(native, "prepare", side_effect=amended),
            self.assertRaisesRegex(ValueError, "identity differs"),
        ):
            run.resume(campaign)
        self.assertFalse((campaign / "sessions/session-0002").exists())

    def test_resealed_wrong_retry_link_or_native_config_fails_semantically(self):
        path, _ = configuration(self.root / "inputs", cells=1, repeats=1)
        campaign = self.root / "campaign"
        with patch.object(run, "supervise", side_effect=self.worker):
            run.run_study(path, campaign)
        session = campaign / "sessions/session-0001"
        state = common.read(session / "plan.json")
        state["schedule"][0]["previous_attempt_manifest_sha256"] = "b" * 64
        common.dump(session / "plan.json", state)
        common.seal(session, common.REPORTS)
        with self.assertRaisesRegex(ValueError, "retry link"):
            report.reconstruct(campaign)


if __name__ == "__main__":
    unittest.main()
