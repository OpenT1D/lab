"""Admission, explicit routing and failure semantics of the checkout task entry."""

import contextlib
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.comparison.fixtures import fixture as comparison_fixture
from experiments.m3.researcher.fixtures import fixture
from experiments.m3.researcher.intake import read_regular
from experiments.m5.researcher_workflow.run import export_example
from experiments.workflows.__main__ import main, parser
from experiments.workflows.checks import check, probe_runtime, runtime_requirements
from experiments.workflows.dispatch import child_environment, command_for, execute
from experiments.workflows.registry import NATIVE_PROJECT, OBSERVER_PROJECT, ROOT, TASKS


def ready_runtime(project, packages):
    return {"project": project, "ready": True, "expected_packages": packages}


def write(path, value):
    Path(path).write_text(json.dumps(value))


def command(*args):
    return parser().parse_args(args)


@contextlib.contextmanager
def installed():
    with (
        patch("experiments.workflows.checks.probe_runtime", side_effect=ready_runtime),
        patch("experiments.workflows.checks.uv_ready", return_value={"ready": True}),
    ):
        yield


class WorkflowEntryTests(unittest.TestCase):
    def test_maintained_study_admission_is_passive_and_dispatch_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = json.loads((ROOT / "experiments/m4/secure_study/example.json").read_bytes())
            marker = directory / "source-executed"
            raw = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            for source in config["sources"]:
                model = directory / (source["id"] + ".py")
                declaration = directory / (source["id"] + ".json")
                original = ROOT / "experiments/m4/secure_study" / source["declaration"]
                declared = json.loads(original.read_bytes())
                declared["source_sha256"] = hashlib.sha256(raw).hexdigest()
                model.write_bytes(raw)
                write(declaration, declared)
                source.update(model=str(model), declaration=str(declaration))
            write(directory / "config.json", config)
            args = command("check", "m4-study-secure", "--config", str(directory / "config.json"))
            with installed():
                checked = check(TASKS[args.task], args)
            self.assertTrue(checked["ready"])
            self.assertFalse(marker.exists())
            self.assertFalse(checked["metadata"]["source_executed"])
            projects = [item["project"] for item in checked["runtimes"]]
            self.assertIn("experiments/m0/simglucose_secure", projects)
            self.assertNotIn(NATIVE_PROJECT, projects)
            run = command(
                "run", args.task, "--config", str(args.config), "--output", str(directory / "run")
            )
            argv = command_for(TASKS[args.task], run)
            self.assertIn("experiments.m4.secure_study", argv)
            reconstructed = command(
                "reconstruct",
                args.task,
                "--archive",
                str(directory / "run"),
                "--output",
                str(directory / "rebuilt"),
                "--allow-failed",
            )
            argv = command_for(TASKS[args.task], reconstructed, operation="reconstruct")
            self.assertIn("-S", argv)
            self.assertIn("--allow-failed", argv)
            self.assertIn("experiments.m4.secure_study", argv)

    def test_list_describe_and_reject_unsupported_options(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(["list"]), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(
            [task["task"] for task in result["tasks"]],
            [
                "p1-controller",
                "m3-forecast",
                "m3-compare",
                "m4-secretion",
                "m4-compare",
                "m4-study",
                "m4-study-secure",
                "m5-prognosis",
                "mmtt-sensitivity",
                "mmtt-sampling",
            ],
        )
        for task in TASKS.values():
            self.assertTrue(Path(task.describe()["guide"]).is_file())
        for arguments in (
            ("run", "m3-forecast", "--bundle", "/tmp/x", "--output", "/tmp/y"),
            ("run", "m3-compare", "--config", "/tmp/x", "--output", "/tmp/y", "--timeout", "1"),
            ("reconstruct", "m5-prognosis", "--archive", "/tmp/x", "--output", "/tmp/y"),
            ("reconstruct", "m4-secretion", "--archive", "/tmp/x"),
            ("run", "unknown-task"),
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                command(*arguments)
            self.assertEqual(error.exception.code, 2)

    def test_passive_p1_check_never_runs_the_existing_smoke(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source"
            shutil.copytree(ROOT / "experiments/p1_external/example", source)
            marker = directory / "imported"
            raw = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            (source / "controller.py").write_bytes(raw)
            declared = json.loads((source / "controller.json").read_bytes())
            declared["source_sha256"] = hashlib.sha256(raw).hexdigest()
            write(source / "controller.json", declared)
            args = command("check", "p1-controller", "--source", str(source))
            with installed(), patch("experiments.p1_external.intake.smoke") as smoke:
                result = check(TASKS[args.task], args)
            self.assertTrue(result["ready"])
            smoke.assert_not_called()
            self.assertFalse(marker.exists())

    def test_m3_metadata_check_does_not_read_observation_bytes_or_import_predictor(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = fixture(directory / "fixture")
            declaration_path = Path(config["predictor"])
            declared = json.loads(declaration_path.read_bytes())
            marker = directory / "imported"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            Path(declared["source"]["file"]).write_bytes(source)
            declared["source"]["sha256"] = hashlib.sha256(source).hexdigest()
            write(declaration_path, declared)
            args = command(
                "check", "m3-forecast", "--config", str(directory / "fixture/config.json")
            )
            observation_paths = {person["input"]["file"] for person in config["people"]}
            for path in observation_paths:
                Path(path).write_bytes(b"Invalid observations; check must not open this")

            def read_source(path, *other):
                self.assertNotIn(str(path), observation_paths)
                return read_regular(path, *other)

            with (
                installed(),
                patch("experiments.m3.researcher.intake.read_regular", side_effect=read_source),
            ):
                result = check(TASKS[args.task], args)
            self.assertTrue(result["ready"])
            self.assertFalse(result["observation_bytes_verified"])
            self.assertFalse(marker.exists())
            Path(next(iter(observation_paths))).unlink()
            with installed():
                result = check(TASKS[args.task], args)
            self.assertFalse(result["ready"])
            self.assertTrue(result["metadata_valid"])
            self.assertEqual(len(result["observation_path_issues"]), 1)

    def test_passive_m4_and_m5_check_read_frozen_sources_without_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker = directory / "imported"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            m4 = directory / "m4"
            m4.mkdir()
            (m4 / "model.py").write_bytes(source)
            declared = json.loads(
                (ROOT / "experiments/m4/causal_secretion/example_model.json").read_bytes()
            )
            declared["source_sha256"] = hashlib.sha256(source).hexdigest()
            write(m4 / "declaration.json", declared)
            write(
                m4 / "config.json",
                {
                    "schema": "m4-researcher-config/1",
                    "model": "model.py",
                    "declaration": "declaration.json",
                    "timeout_seconds": 600,
                },
            )
            export_example(directory / "m5")
            (directory / "m5/model.py").write_bytes(source)
            declared = json.loads((directory / "m5/model.json").read_bytes())
            declared["source_sha256"] = hashlib.sha256(source).hexdigest()
            write(directory / "m5/model.json", declared)
            for task_id, option, path in (
                ("m4-secretion", "--config", m4 / "config.json"),
                ("m5-prognosis", "--bundle", directory / "m5"),
            ):
                args = command("check", task_id, option, str(path))
                with installed():
                    result = check(TASKS[task_id], args)
                self.assertTrue(result["ready"])
                self.assertFalse(marker.exists())

    def test_comparison_check_is_passive_for_every_candidate_and_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = comparison_fixture(directory / "fixture")
            marker = directory / "imported"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n".encode()
            for candidate in config["candidates"]:
                path = Path(candidate["declaration"])
                declared = json.loads(path.read_bytes())
                Path(declared["source"]["file"]).write_bytes(source)
                declared["source"]["sha256"] = hashlib.sha256(source).hexdigest()
                write(path, declared)
            observation_paths = {person["input"]["file"] for person in config["people"]}
            for path in observation_paths:
                Path(path).write_bytes(b"Invalid observations; passive check must not open this")

            def read_source(path, *other):
                self.assertNotIn(str(path), observation_paths)
                return read_regular(path, *other)

            args = command(
                "check", "m3-compare", "--config", str(directory / "fixture/comparison.json")
            )
            with (
                installed(),
                patch("experiments.m3.comparison.common.read_regular", side_effect=read_source),
            ):
                result = check(TASKS[args.task], args)
            self.assertTrue(result["ready"])
            self.assertFalse(result["observation_bytes_verified"])
            self.assertFalse(result["metadata"]["candidate_executed"])
            self.assertEqual(
                result["metadata"]["candidate_order"],
                [candidate["id"] for candidate in config["candidates"]],
            )
            self.assertFalse(marker.exists())
            Path(next(iter(observation_paths))).unlink()
            with installed():
                result = check(TASKS[args.task], args)
            self.assertFalse(result["ready"])
            self.assertEqual(len(result["observation_path_issues"]), 1)

    def test_invalid_hash_and_nonfinite_timeout_refuse_before_dispatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source"
            shutil.copytree(ROOT / "experiments/p1_external/example", source)
            (source / "controller.py").write_bytes(b"changed")
            args = command(
                "run",
                "p1-controller",
                "--source",
                str(source),
                "--output",
                str(directory / "output"),
            )
            with patch("experiments.workflows.dispatch.run_process") as child:
                with self.assertRaisesRegex(ValueError, "hash"):
                    execute(TASKS[args.task], args)
            child.assert_not_called()
            self.assertFalse((directory / "output").exists())
            args = command("check", "m3-forecast", "--config", "/unused", "--timeout", "nan")
            with self.assertRaisesRegex(ValueError, "finite"):
                check(TASKS[args.task], args)

    def test_missing_runtime_and_existing_output_do_not_launch_or_create_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            export_example(directory / "model")
            args = command(
                "run",
                "m5-prognosis",
                "--bundle",
                str(directory / "model"),
                "--output",
                str(directory / "study"),
            )
            with (
                patch("experiments.workflows.checks.probe_runtime", return_value={"ready": False}),
                patch("experiments.workflows.checks.uv_ready", return_value={"ready": True}),
                patch("experiments.workflows.dispatch.run_process") as child,
            ):
                result = execute(TASKS[args.task], args)
            self.assertIsNone(result["child_exit_code"])
            child.assert_not_called()
            self.assertFalse((directory / "study").exists())
            (directory / "study").mkdir()
            with installed(), patch("experiments.workflows.dispatch.run_process") as child:
                with self.assertRaisesRegex(ValueError, "new output"):
                    execute(TASKS[args.task], args)
            child.assert_not_called()

    def test_runtime_probe_uses_existing_venv_isolated_metadata_not_distribution_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "uv.lock").touch()
            (directory / "pyproject.toml").touch()
            (directory / ".venv/bin").mkdir(parents=True)
            (directory / ".venv/bin/python").touch()
            (directory / ".venv/pyvenv.cfg").touch()
            with patch("experiments.workflows.checks.ROOT", directory):
                actual = {
                    "python": "3.12.13",
                    "implementation": "CPython",
                    "packages": {"numpy": "1.26.4"},
                }
                with patch("experiments.workflows.checks.subprocess.run") as probe:
                    probe.return_value.stdout = json.dumps(actual)
                    result = probe_runtime(".", {"numpy": "1.26.4"})
                self.assertTrue(result["ready"])
                argv = probe.call_args.args[0]
                self.assertIn("-I", argv)
                self.assertIn("importlib.metadata", argv[3])
                self.assertNotIn("import numpy", argv[3])
                actual["packages"]["numpy"] = "2.0.0"
                with patch("experiments.workflows.checks.subprocess.run") as probe:
                    probe.return_value.stdout = json.dumps(actual)
                    result = probe_runtime(".", {"numpy": "1.26.4"})
                self.assertFalse(result["ready"])
                (directory / ".venv/pyvenv.cfg").unlink()
                with patch("experiments.workflows.checks.subprocess.run") as probe:
                    result = probe_runtime(".", {})
                self.assertEqual(result["reason"], "missing_environment")
                probe.assert_not_called()

    def test_task_runtime_and_command_selection_preserve_native_contracts(self):
        for task_id, arguments in (
            ("p1-controller", ["--source", "/source", "--profile", "adult#002", "--seed", "102"]),
            ("m3-forecast", ["--config", "/config", "--timeout", "0.25"]),
            ("m3-compare", ["--config", "/config"]),
            ("m4-secretion", ["--config", "/config", "--reference", "/reference"]),
            ("m5-prognosis", ["--bundle", "/bundle", "--timeout-seconds", "0.2"]),
        ):
            task = TASKS[task_id]
            args = command("run", task_id, *arguments, "--output", "/output")
            argv = command_for(task, args)
            self.assertEqual(Path(argv[0]), ROOT / task.run_project / ".venv/bin/python")
            self.assertIn(task.run_module, argv)
            self.assertNotIn("uv", argv)
            if task_id == "m4-secretion":
                self.assertIn("/reference", argv)
            if task_id == "m3-compare":
                self.assertIn("run", argv)
                self.assertNotIn("--timeout", argv)
                self.assertNotIn("--timeout-seconds", argv)
            required = runtime_requirements(task)
            if task_id == "m4-secretion":
                self.assertEqual(set(required), {".", NATIVE_PROJECT, OBSERVER_PROJECT})
            rebuild_args = ["reconstruct", task_id, "--archive", "/archive"]
            if task.reconstruction_output:
                rebuild_args.extend(["--output", "/reconstructed"])
            if task_id == "m4-secretion":
                rebuild_args.append("--allow-failed")
            argv = command_for(task, command(*rebuild_args), operation="reconstruct")
            self.assertIn("-S", argv)
            self.assertEqual(Path(argv[0]), ROOT / ".venv/bin/python")
            self.assertEqual("--output" in argv, task.reconstruction_output)
            if task_id == "m3-compare":
                self.assertIn("reconstruct", argv)
                self.assertIn("--study", argv)

    def test_scoped_environment_drops_foreign_uv_and_python_selectors(self):
        with patch.dict(
            os.environ,
            {
                "UV_PROJECT_ENVIRONMENT": "/foreign",
                "UV_PROJECT": "/foreign",
                "UV_PYTHON": "/foreign/python",
                "UV_WORKING_DIR": "/foreign",
                "UV_ENV_FILE": "/foreign/env",
                "VIRTUAL_ENV": "/foreign",
                "UV_CONFIG_FILE": "/foreign/config.toml",
                "UV_NO_CONFIG": "0",
                "PYTHONPATH": "/foreign",
                "PYTHONHOME": "/foreign",
                "UV_NO_SYNC": "0",
                "UV_PYTHON_DOWNLOADS": "automatic",
            },
        ):
            env = child_environment()
        self.assertEqual(env["UV_NO_SYNC"], "1")
        self.assertEqual(env["UV_PYTHON_DOWNLOADS"], "never")
        self.assertEqual(env["UV_OFFLINE"], "1")
        self.assertEqual(env["UV_NO_CONFIG"], "1")
        self.assertEqual(env["PYTHONNOUSERSITE"], "1")
        for name in (
            "UV_PROJECT_ENVIRONMENT",
            "UV_PROJECT",
            "UV_PYTHON",
            "UV_WORKING_DIR",
            "UV_ENV_FILE",
            "UV_CONFIG_FILE",
            "VIRTUAL_ENV",
            "PYTHONPATH",
            "PYTHONHOME",
        ):
            self.assertNotIn(name, env)

    def test_child_zero_does_not_turn_incomplete_report_into_complete_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = command(
                "run", "m5-prognosis", "--bundle", "/unused", "--output", str(directory / "study")
            )

            def child(_argv, _env):
                Path(args.output).mkdir()
                write(Path(args.output) / "report.json", {"comparison_status": "incomplete"})
                (Path(args.output) / "report.md").touch()
                return 0, None

            readiness = {"runtimes_ready": True, "observation_path_issues": []}
            with (
                patch("experiments.workflows.dispatch.check", return_value=readiness),
                patch("experiments.workflows.dispatch.run_process", side_effect=child),
            ):
                result = execute(TASKS[args.task], args)
            self.assertEqual(result["child_exit_code"], 0)
            self.assertEqual(result["report_completeness"], "incomplete")
            self.assertEqual(
                set(path.name for path in args.output.iterdir()), {"report.json", "report.md"}
            )

    def test_missing_observation_does_not_prevent_native_failure_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = fixture(directory / "fixture")
            Path(config["people"][0]["input"]["file"]).unlink()
            args = command(
                "run",
                "m3-forecast",
                "--config",
                str(directory / "fixture/config.json"),
                "--output",
                str(directory / "study"),
            )
            with (
                installed(),
                patch(
                    "experiments.workflows.dispatch.run_process", return_value=(1, None)
                ) as child,
            ):
                result = execute(TASKS[args.task], args)
            child.assert_called_once()
            self.assertEqual(result["child_exit_code"], 1)
            self.assertEqual(len(result["observation_path_issues"]), 1)

    def test_comparison_dispatch_retains_exit_and_partial_report_separately(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            comparison_fixture(directory / "fixture")
            args = command(
                "run",
                "m3-compare",
                "--config",
                str(directory / "fixture/comparison.json"),
                "--output",
                str(directory / "study"),
            )

            def child(argv, _env):
                self.assertIn("experiments.m3.comparison", argv)
                Path(args.output).mkdir()
                write(Path(args.output) / "report.json", {"common": {"complete_cohort": False}})
                (Path(args.output) / "report.md").touch()
                return 0, None

            with (
                installed(),
                patch("experiments.workflows.dispatch.run_process", side_effect=child),
            ):
                result = execute(TASKS[args.task], args)
            self.assertEqual(result["child_exit_code"], 0)
            self.assertEqual(result["report_completeness"], "incomplete")
            self.assertEqual(result["report_status_scope"], "recorded_native_report")
            self.assertEqual(
                set(path.name for path in args.output.iterdir()), {"report.json", "report.md"}
            )

    def test_real_sigterm_is_forwarded_and_native_sealing_is_awaited(self):
        self.signal_sealing(signal.SIGTERM)

    def test_real_sighup_is_translated_for_legacy_native_cleanup(self):
        self.signal_sealing(signal.SIGHUP)

    def signal_sealing(self, incoming):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            marker, sealed = directory / "ready", directory / "sealed"
            native = directory / "native.py"
            native.write_text(
                "import signal,sys,time\nfrom pathlib import Path\n"
                "def stop(*args):\n"
                " time.sleep(0.15)\n"
                f" Path({str(sealed)!r}).touch()\n"
                " sys.exit(7)\n"
                "signal.signal(signal.SIGTERM,stop)\n"
                f"Path({str(marker)!r}).touch()\n"
                "while True: time.sleep(0.05)\n"
            )
            helper = (
                "import json,signal,sys\n"
                "from experiments.workflows.dispatch import run_process,child_environment\n"
                "before=signal.getsignal(signal.SIGTERM)\n"
                f"code,forwarded=run_process([sys.executable,{str(native)!r}],child_environment())\n"
                "print(json.dumps([code,forwarded,before==signal.getsignal(signal.SIGTERM)]))\n"
            )
            process = subprocess.Popen(
                [sys.executable, "-B", "-S", "-c", helper],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 5
                while (
                    not marker.exists() and process.poll() is None and time.monotonic() < deadline
                ):
                    time.sleep(0.02)
                self.assertTrue(marker.exists())
                process.send_signal(incoming)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout), [7, incoming, True])
                self.assertTrue(sealed.exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
