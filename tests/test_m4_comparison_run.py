"""Metadata freeze, full-roster coordination and owned cancellation without SciPy."""

import copy
import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.comparison import common, run


def configuration(root, *, source=None):
    root = Path(root)
    root.mkdir()
    sources = []
    model = common.ROOT / "experiments/m4/causal_secretion/example_model.py"
    declaration = common.read(model.with_suffix(".json"))
    for identity in ("first", "second"):
        folder = root / identity
        folder.mkdir()
        raw = model.read_bytes() if source is None else source.encode()
        (folder / "model.py").write_bytes(raw)
        common.dump(folder / "model.json", declaration | {"source_sha256": common.digest(raw)})
        sources.append(
            {
                "id": identity,
                "model": f"{identity}/model.py",
                "declaration": f"{identity}/model.json",
            }
        )
    config = {
        "schema": common.CONFIG_SCHEMA,
        "sources": sources,
        "timeout_seconds": 600,
        "source_timeout_seconds": 3600,
    }
    common.dump(root / "comparison.json", config)
    return root / "comparison.json", config


def saved_state(output, write_to=None, allow_failed=False):
    state = common.read(Path(output) / "state.json")
    return {"passed": state["status"] == "completed", "state": state}


class ComparisonRunTests(unittest.TestCase):
    def test_passive_intake_freezes_raw_hashes_without_source_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "imported"
            path, config = configuration(
                root / "prepare",
                source=f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
            )
            result = common.check(path)
            self.assertEqual(result["source_order"], ["first", "second"])
            self.assertFalse(result["source_executed"])
            self.assertFalse(marker.exists())
            output, plan, ref = run.freeze(path, root / "archive")
            self.assertIsNone(ref)
            self.assertEqual(plan["config"], config)
            self.assertEqual(plan["config_sha256"], common.sha256(path))
            self.assertEqual((output / "config.json").read_bytes(), path.read_bytes())
            self.assertEqual(plan["protocol"], common.protocol())
            for source in config["sources"]:
                identity = source["id"]
                frozen = output / "frozen" / identity
                self.assertEqual(
                    common.sha256(frozen / "model.py"), result["source_sha256"][identity]
                )
                self.assertEqual(common.read(frozen / "config.json")["timeout_seconds"], 600)
            original = (root / "prepare/first/model.py").read_bytes()
            (root / "prepare/first/model.py").write_text("changed original source\n")
            run.verify_frozen(output, plan)
            (root / "prepare/first/model.py").write_bytes(original)
            with self.assertRaises(FileExistsError):
                run.freeze(path, output)

    def test_config_rejects_unsupported_rosters_budgets_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, config = configuration(Path(tmp) / "prepare")
            edits = [
                {"sources": config["sources"][:1]},
                {"sources": [config["sources"][0]] * 2},
                {"timeout_seconds": True},
                {"timeout_seconds": 1801},
                {"source_timeout_seconds": 0},
                {"source_timeout_seconds": 10801},
                {"extra": 1},
            ]
            for edit in edits:
                with self.subTest(edit=edit), self.assertRaises(ValueError):
                    common.validate_config(config | edit)
            for identity in ("../unsafe", "bc008_reference", "host_constant_basal", "FIRST"):
                changed = copy.deepcopy(config)
                changed["sources"][0]["id"] = identity
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    common.validate_config(changed)
            path.write_text('{"schema":"first","schema":"second"}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                common.intake(path)

    def test_changed_model_symlink_and_invalid_reference_fail_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, config = configuration(root / "prepare")
            model = path.parent / config["sources"][0]["model"]
            original = model.read_bytes()
            model.write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "source hash"):
                run.run_study(path, root / "output")
            self.assertFalse((root / "output").exists())
            model.write_bytes(original)
            linked = model.with_name("linked.py")
            linked.symlink_to(model)
            config["sources"][0]["model"] = "first/linked.py"
            common.dump(path, config)
            with self.assertRaisesRegex(ValueError, "regular file"):
                run.run_study(path, root / "output")
            config["sources"][0]["model"] = "first/model.py"
            common.dump(path, config)
            with self.assertRaises(ValueError):
                run.run_study(path, root / "output", root / "missing-reference")
            self.assertFalse((root / "output").exists())

    def test_frozen_dispatch_rechecks_child_config_and_plan_before_source_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = configuration(root / "prepare")
            output, plan, _ = run.freeze(path, root / "output")
            child_config = output / "frozen/first/config.json"
            original = child_config.read_bytes()
            common.dump(
                child_config,
                plan["sources"]["first"]["effective_config"]
                | {
                    "timeout_seconds": 1,
                },
            )
            with self.assertRaisesRegex(ValueError, "Frozen child config"):
                run.verify_frozen(output, plan)
            child_config.write_bytes(original)
            common.dump(output / "plan.json", plan | {"extra": "changed"})
            with self.assertRaisesRegex(ValueError, "Frozen plan"):
                run.verify_frozen(output, plan)

    def test_worker_environment_refuses_uv_and_active_python_selectors(self):
        inherited = {
            "UV_PROJECT": "/different/project",
            "UV_PYTHON": "/different/python",
            "UV_NO_SYNC": "0",
            "PYTHONPATH": "/different/packages",
            "VIRTUAL_ENV": "/different/env",
        }
        with patch.dict(os.environ, inherited):
            env = run.worker_environment()
        self.assertNotIn("UV_PROJECT", env)
        self.assertNotIn("UV_PYTHON", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("VIRTUAL_ENV", env)
        self.assertEqual(env["UV_NO_SYNC"], "1")
        self.assertEqual(env["UV_OFFLINE"], "1")
        self.assertEqual(env["UV_PYTHON_DOWNLOADS"], "never")

    def test_entire_roster_is_frozen_before_reference_then_sources_dispatch_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, config = configuration(root / "prepare")
            output = root / "output"
            dispatched = []

            def worker(args, logfile, timeout, control):
                plan = common.read(output / "plan.json")
                self.assertEqual(plan["config"], config)
                for item in config["sources"]:
                    self.assertTrue((output / "frozen" / item["id"] / "model.py").is_file())
                archive = Path(args[args.index("--output") + 1])
                archive.mkdir()
                common.dump(archive / "manifest.json", {"status": "completed"})
                logfile.write_text("Controlled worker\n")
                dispatched.append((archive.name, timeout))
                return (1, "WorkerExit") if archive.name == "first" else (0, None)

            with (
                patch.object(run, "supervise", side_effect=worker),
                patch.object(
                    run, "verify_reference", return_value=(None, None, None, {"passed": True})
                ),
                patch.object(run, "reconstruct_child", return_value={"passed": True}),
                patch("experiments.m4.comparison.report.reconstruct", side_effect=saved_state),
            ):
                result = run.run_study(path, output)
            self.assertEqual(dispatched, [("reference", 600), ("first", 3600), ("second", 3600)])
            self.assertFalse(result["passed"])
            self.assertEqual(result["state"]["sources"]["first"]["status"], "failed")
            self.assertEqual(result["state"]["sources"]["second"]["status"], "completed")
            self.assertEqual(result["state"]["reference"]["status"], "completed")
            self.assertIsNotNone(result["state"]["sources"]["first"]["manifest_sha256"])
            manifest = common.read(output / "manifest.json")
            self.assertEqual(
                manifest["files"],
                {name: common.digest(raw) for name, raw in common.inventory(output).items()},
            )

    def test_reference_failure_retains_all_unattempted_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = configuration(root / "prepare")
            with (
                patch.object(run, "supervise", return_value=(1, "WorkerExit")) as worker,
                patch("experiments.m4.comparison.report.reconstruct", side_effect=saved_state),
            ):
                result = run.run_study(path, root / "output")
            self.assertEqual(worker.call_count, 1)
            self.assertEqual(result["state"]["reference"]["status"], "failed")
            self.assertEqual(
                [item["status"] for item in result["state"]["sources"].values()],
                ["not_attempted", "not_attempted"],
            )

    def test_global_signal_preserves_interrupted_and_unattempted_source_roster(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = configuration(root / "prepare")

            def worker(args, logfile, timeout, control):
                archive = Path(args[args.index("--output") + 1])
                archive.mkdir()
                common.dump(archive / "manifest.json", {"status": "failed"})
                if archive.name != "reference":
                    control.stop(signal.SIGTERM)
                    return -int(signal.SIGTERM), "GlobalInterruption"
                return 0, None

            with (
                patch.object(run, "supervise", side_effect=worker),
                patch.object(
                    run, "verify_reference", return_value=(None, None, None, {"passed": True})
                ),
                patch("experiments.m4.comparison.report.reconstruct", side_effect=saved_state),
            ):
                result = run.run_study(path, root / "output")
            self.assertEqual(result["state"]["status"], "interrupted")
            self.assertEqual(result["state"]["interruption_signal"], int(signal.SIGTERM))
            self.assertEqual(result["state"]["sources"]["first"]["status"], "interrupted")
            self.assertEqual(result["state"]["sources"]["second"]["status"], "not_attempted")

    def test_final_boundary_signal_reconciles_global_state_without_dropping_completed_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = configuration(root / "prepare")
            previous_signal = signal.signal
            installed = {}

            def transition(signum, handler):
                if signum not in installed:
                    installed[signum] = handler
                elif signum == signal.SIGINT:
                    installed[signum](int(signum), None)
                return previous_signal(signum, handler)

            def worker(args, logfile, timeout, control):
                archive = Path(args[args.index("--output") + 1])
                archive.mkdir()
                common.dump(archive / "manifest.json", {"status": "completed"})
                return 0, None

            with (
                patch.object(run, "supervise", side_effect=worker),
                patch.object(
                    run, "verify_reference", return_value=(None, None, None, {"passed": True})
                ),
                patch.object(run, "reconstruct_child", return_value={"passed": True}),
                patch("experiments.m4.comparison.report.reconstruct", side_effect=saved_state),
                patch.object(run.signal, "signal", side_effect=transition),
            ):
                result = run.run_study(path, root / "output")
            self.assertEqual(result["state"]["status"], "interrupted")
            self.assertEqual(result["state"]["interruption_signal"], int(signal.SIGINT))
            self.assertEqual(
                {item["status"] for item in result["state"]["sources"].values()}, {"completed"}
            )

    def test_signal_during_reference_verification_does_not_dispatch_next_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _ = configuration(root / "prepare")
            checks = 0

            def verify(_archive):
                nonlocal checks
                checks += 1
                if checks == 2:
                    signal.raise_signal(signal.SIGTERM)
                return (None, None, None, {"passed": True})

            def worker(args, logfile, timeout, control):
                archive = Path(args[args.index("--output") + 1])
                archive.mkdir()
                common.dump(archive / "manifest.json", {"status": "completed"})
                return 0, None

            with (
                patch.object(run, "supervise", side_effect=worker) as dispatch,
                patch.object(run, "verify_reference", side_effect=verify),
                patch("experiments.m4.comparison.report.reconstruct", side_effect=saved_state),
            ):
                result = run.run_study(path, root / "output")
            self.assertEqual(dispatch.call_count, 1)
            self.assertEqual(result["state"]["reference"]["status"], "completed")
            self.assertEqual(result["state"]["status"], "interrupted")
            self.assertEqual(
                {item["status"] for item in result["state"]["sources"].values()}, {"not_attempted"}
            )

    @unittest.skipUnless(os.name == "posix", "POSIX supervision")
    def test_deadline_allows_supervisor_to_reap_its_separate_worker_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cleanup, worker_pid = root / "cleanup", root / "worker-pid"
            script = f"""import os, signal, subprocess, sys, time
from pathlib import Path
worker = subprocess.Popen(
    [sys.executable, '-B', '-S', '-c', 'import time; time.sleep(60)'], start_new_session=True
)
Path({str(worker_pid)!r}).write_text(str(worker.pid))
def stop(signum, frame):
    os.killpg(worker.pid, signal.SIGKILL)
    worker.wait()
    Path({str(cleanup)!r}).write_text('reaped')
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
while True:
    time.sleep(0.02)
"""
            code, error = run.supervise(
                [sys.executable, "-B", "-S", "-c", script], root / "worker.log", 1, run.Control()
            )
            self.assertEqual((code, error), (0, "WorkerDeadline"))
            header = json.loads((root / "worker.log").read_text().splitlines()[0])
            self.assertEqual(header["argv"], [sys.executable, "-B", "-S", "-c", script])
            self.assertEqual(header["timeout_seconds"], 1)
            self.assertEqual(cleanup.read_text(), "reaped")
            with self.assertRaises(ProcessLookupError):
                os.kill(int(worker_pid.read_text()), 0)


if __name__ == "__main__":
    unittest.main()
