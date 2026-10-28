"""Real catalogue/setup callers retain evidence after owned-worker cleanup."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core as catalogue
from experiments.catalogue import storage
from experiments.setup import core as setup

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "Real POSIX process-group ownership required")
class CatalogueSetupSupervisionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.owned = []
        self.addCleanup(self.cleanup_workers)
        self.worker = self.base / "synthetic-worker.py"
        self.worker.write_text(
            "import json, os, signal, subprocess, sys, time\n"
            "from pathlib import Path\n"
            "mode, marker = sys.argv[1], Path(sys.argv[2])\n"
            "def publish(path, value):\n"
            " pending = path.with_suffix('.pending')\n"
            " pending.write_text(json.dumps(value)); pending.replace(path)\n"
            "if mode == 'child':\n"
            " print('synthetic descendant ready', flush=True)\n"
            " publish(marker, os.getpid())\n"
            " while True: time.sleep(0.02)\n"
            "child_marker = marker.with_suffix('.child')\n"
            "child = subprocess.Popen([sys.executable, '-B', '-S', __file__, "
            "'child', str(child_marker)])\n"
            "deadline = time.monotonic() + 10\n"
            "while not child_marker.exists():\n"
            " if time.monotonic() > deadline: raise RuntimeError('child not ready')\n"
            " time.sleep(0.01)\n"
            "print('synthetic leader ' + mode, flush=True)\n"
            "if len(sys.argv) > 3:\n"
            " output = Path(sys.argv[3]); output.mkdir(parents=True, exist_ok=True)\n"
            " (output / 'report.json').write_text(json.dumps({'study_status': 'completed'}))\n"
            "publish(marker, [os.getpid(), json.loads(child_marker.read_text())])\n"
            "if mode == 'normal': raise SystemExit(0)\n"
            "if mode == 'crash': raise SystemExit(7)\n"
            "while True: time.sleep(0.02)\n"
        )
        self.unrelated = subprocess.Popen(
            [sys.executable, "-B", "-S", "-c", "import time; time.sleep(60)"],
            start_new_session=True,
        )
        self.addCleanup(self.stop_unrelated)

    def stop_unrelated(self):
        if self.unrelated.poll() is None:
            self.unrelated.kill()
        self.unrelated.wait()

    def cleanup_workers(self):
        # Retain cleanup even when an old implementation leaves the child live.
        for process in self.owned:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def live(self, pid):
        observed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False
        )
        state, error = observed.stdout.strip(), observed.stderr.strip()
        if observed.returncode == 0 and state and not error:
            return not state.startswith("Z")
        if observed.returncode == 1 and not state and not error:
            return False
        raise RuntimeError(f"Could not observe synthetic process {pid}: {observed!r}")

    def test_process_observation_errors_cannot_claim_successful_cleanup(self):
        for code, output, error in (
            (2, "", "invalid ps arguments"),
            (1, "", "Operation not permitted"),
            (0, "", ""),
        ):
            with self.subTest(code=code, error=error):
                with (
                    patch.object(
                        subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess([], code, output, error),
                    ),
                    self.assertRaisesRegex(RuntimeError, "Could not observe synthetic process"),
                ):
                    self.live(123)

    def wait_for_marker(self, marker):
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.is_file(), "Synthetic worker and descendant did not become ready")

    def supervise_case(self, mode, marker, operation):
        waiting = threading.Event()
        original_spawn = storage.spawn
        original_supervise = storage.supervise

        def spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            self.owned.append(process)
            original_wait = process.wait

            def wait(*args, **kwargs):
                # Begin the real deadline/cancellation only after the descendant
                # has published readiness, with supervise's process assigned.
                if not waiting.is_set():
                    self.wait_for_marker(marker)
                    waiting.set()
                return original_wait(*args, **kwargs)

            process.wait = wait
            return process

        def supervise(args, logfile, cwd, env, timeout):
            return original_supervise(
                args, logfile, cwd, env, 0.1 if mode == "timeout" else timeout
            )

        def cancel():
            if waiting.wait(timeout=10):
                os.kill(os.getpid(), signal.SIGTERM)

        sender = threading.Thread(target=cancel) if mode == "cancel" else None
        previous = {value: signal.getsignal(value) for value in storage.handled_signals()}
        with (
            patch.object(storage, "spawn", side_effect=spawn),
            patch.object(storage, "CLEANUP_GRACE_SECONDS", 0.2, create=True),
            patch.object(catalogue, "supervise", side_effect=supervise),
            patch.object(setup, "supervise", side_effect=supervise),
        ):
            if sender is not None:
                sender.start()
            try:
                result = operation()
            finally:
                if sender is not None:
                    sender.join(timeout=11)
        self.assertEqual({value: signal.getsignal(value) for value in previous}, previous)
        self.assertTrue(waiting.is_set(), "Caller did not run the real supervisor")
        return result

    def assert_owned_stopped(self, marker):
        self.assertIsNone(self.unrelated.poll(), "Cleanup terminated an unrelated process")
        for process in self.owned:
            self.assertIsNotNone(process.returncode, "Supervisor did not reap its direct child")
        pids = json.loads(marker.read_bytes())
        deadline = time.monotonic() + 1
        while any(self.live(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(
            any(self.live(pid) for pid in pids),
            "Caller returned with a live owned leader or descendant",
        )

    def archive(self, directory):
        archive = directory / "source"
        archive.mkdir()
        storage.dump(
            archive / "workflow.json",
            {
                "schema": "opent1d.p1-external-workflow/1",
                "profile": "synthetic-profile",
                "seed": 101,
                "controller": {"name": "synthetic-controller", "source_sha256": "a" * 64},
                "implementation_sha256": {"synthetic": "b" * 64},
            },
        )
        storage.dump(
            archive / "study.json",
            {"schema": "opent1d.p1-external-workflow/1", "cases": ["A"], "status": "completed"},
        )
        return archive

    def test_catalogue_verification_retains_receipts_and_cleans_each_lifecycle(self):
        for mode in ("normal", "crash", "timeout", "cancel"):
            with self.subTest(mode=mode):
                directory = self.base / ("catalogue-" + mode)
                directory.mkdir()
                archive = self.archive(directory)
                before = storage.inventory(archive)
                request = directory / "request.json"
                storage.dump(
                    request,
                    {
                        "schema": catalogue.REQUEST,
                        "entries": [
                            {
                                "id": identity,
                                "task": "p1-controller",
                                "archive": str(archive),
                                "tags": [],
                            }
                            for identity in (["first", "later"] if mode == "cancel" else ["first"])
                        ],
                    },
                )
                indexed = directory / "index"
                catalogue.index(request, indexed)
                marker = directory / "worker.json"
                output = directory / "verified"
                with patch.object(
                    catalogue,
                    "reconstruction_args",
                    side_effect=lambda task, archive, output, allow_failed: [
                        str(self.worker),
                        mode,
                        str(marker),
                        str(output),
                    ],
                ) as command:
                    result = self.supervise_case(
                        mode, marker, lambda: catalogue.verify(indexed, output)
                    )
                verification = result["entries"][0]["verification"]
                self.assertEqual(
                    verification["source_archive_sha256"], storage.digest(storage.encoded(before))
                )
                self.assertEqual(
                    verification["status"],
                    "verified_reconstruction" if mode == "normal" else "failed",
                )
                self.assertEqual(verification["complete"], mode == "normal")
                if mode in ("normal", "crash"):
                    self.assertEqual(verification["reader_exit_code"], 0 if mode == "normal" else 7)
                elif mode == "timeout":
                    self.assertIsNone(verification["reader_exit_code"])
                    self.assertIn("TimeoutExpired", verification["error"])
                else:
                    self.assertEqual(verification["interruption_signal"], signal.SIGTERM)
                    self.assertEqual(verification["reader_exit_code"], -signal.SIGTERM)
                    self.assertIn("not attempted", result["entries"][1]["verification"]["error"])
                    self.assertEqual(command.call_count, 1)
                self.assertEqual(catalogue.load(output)[1], result)
                self.assertEqual(storage.inventory(archive), before)
                log = (output / "reconstruction/first.log").read_text()
                self.assertIn("synthetic leader " + mode, log)
                self.assertIn("synthetic descendant ready", log)
                self.assert_owned_stopped(marker)

    def test_setup_execution_retains_receipts_and_cleans_each_lifecycle(self):
        checkout = self.base / "checkout"
        for project in (".", setup.NATIVE, setup.OBSERVER):
            destination = checkout / project
            destination.mkdir(parents=True, exist_ok=True)
            for name in ("uv.lock", "pyproject.toml"):
                shutil.copyfile(ROOT / project / name, destination / name)
        shutil.copyfile(ROOT / ".python-version", checkout / ".python-version")
        for mode in ("normal", "crash", "timeout", "cancel"):
            with self.subTest(mode=mode):
                directory = self.base / ("setup-" + mode)
                directory.mkdir()
                marker = directory / "worker.json"
                identity = {"path": sys.executable, "sha256": "c" * 64, "version": "synthetic uv"}
                with (
                    patch.object(setup, "ROOT", checkout),
                    patch.object(setup, "uv_identity", return_value=identity),
                    patch.object(
                        setup,
                        "install_argv",
                        return_value=["uv", str(self.worker), mode, str(marker)],
                    ),
                ):
                    plan = directory / "plan"
                    data = setup.plan("m4-study" if mode == "cancel" else "mmtt-sensitivity", plan)
                    output = directory / "installed"
                    owned_before = len(self.owned)
                    result = self.supervise_case(
                        mode, marker, lambda: setup.execute(plan, output, install=True)
                    )
                    self.assertEqual(setup.load(plan)[1], data)
                installed = result["projects"][0]["installation"]
                self.assertFalse(result["ready"])
                self.assertFalse(result["numerical_validation"])
                self.assertFalse(result["source_or_model_executed"])
                self.assertEqual(result["plan_sha256"], storage.digest(storage.encoded(data)))
                if mode in ("normal", "crash"):
                    self.assertEqual(
                        installed,
                        {
                            "status": "completed" if mode == "normal" else "failed",
                            "exit_code": 0 if mode == "normal" else 7,
                        },
                    )
                elif mode == "timeout":
                    self.assertEqual(
                        installed,
                        {"status": "failed", "exit_code": None, "error_type": "TimeoutExpired"},
                    )
                else:
                    self.assertEqual(installed["status"], "interrupted")
                    self.assertEqual(installed["signal"], signal.SIGTERM)
                    self.assertEqual(result["interruption_signal"], signal.SIGTERM)
                    self.assertEqual(result["projects"][0]["reason"], "installation_interrupted")
                    for later in result["projects"][1:]:
                        self.assertEqual(later["reason"], "global_interruption")
                        self.assertEqual(
                            later["installation"], {"status": "not_attempted", "exit_code": None}
                        )
                    self.assertEqual(len(self.owned) - owned_before, 1)
                storage.load_sealed(output)
                self.assertEqual(storage.read(output / "setup.json"), result)
                self.assertEqual(storage.read(output / "plan.json"), data)
                log = (output / "root.log").read_text()
                self.assertIn("synthetic leader " + mode, log)
                self.assertIn("synthetic descendant ready", log)
                self.assertFalse((checkout / ".venv").exists())
                self.assert_owned_stopped(marker)


if __name__ == "__main__":
    unittest.main()
