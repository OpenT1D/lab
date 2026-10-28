"""Scientific process ownership and portable recorded execution locations."""

import copy
import os
import signal
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from experiments import platform_process
from experiments.m0.simglucose.recording import interruption
from experiments.m3.researcher.common import digest, save
from experiments.m3.researcher.study import markdown, reconstruct, run_study, seal
from experiments.m4.secure_study import locations
from experiments.m4.secure_study.common import NATIVE_PROJECT, OBSERVER_PROJECT
from experiments.m4.secure_study.report import expected_stage
from experiments.maintained_campaigns.run import command
from tests.test_m3_researcher_study import configuration


class ScientificPortabilityTests(unittest.TestCase):
    def test_windows_tree_controls_use_only_live_ownership_and_release_it(self):
        process, owner = Mock(), Mock()
        process._opent1d_ownership = owner
        owner.observe.return_value = {123: {"authority": "live-windows-job"}}
        owner.cleanup.return_value = (False, [])
        with patch.object(platform_process, "os", SimpleNamespace(name="nt")):
            platform_process.signal_tree(process, signal.SIGTERM)
            self.assertTrue(platform_process.tree_exists(process))
            platform_process.force_tree(process)
            platform_process.close_tree(process)
        self.assertEqual(owner.signal.call_args_list[0].args, (signal.SIGTERM,))
        self.assertEqual(owner.signal.call_args_list[1].args, (9,))
        owner.cleanup.assert_called_once_with(0)
        process.kill.assert_not_called()

    def test_external_deadline_context_works_without_windows_alarm_apis(self):
        from experiments.m0.simglucose import recording

        with patch.object(recording, "os", SimpleNamespace(name="nt")):
            with interruption(1, arm_timer=False):
                self.assertTrue(callable(signal.getsignal(signal.SIGINT)))
            with self.assertRaisesRegex(ValueError, "owning worker deadline"):
                with interruption(1):
                    self.fail("An unsupported deadline must not silently be ignored")

    def test_recorded_windows_locations_reconstruct_without_live_installation(self):
        runtime = {
            "schema": locations.SCHEMA,
            "executables": {
                NATIVE_PROJECT: r"C:\Users\Test User\OpenT1D\runtimes\native\python.exe",
                OBSERVER_PROJECT: r"C:\Users\Test User\OpenT1D\runtimes\observer\python.exe",
            },
        }
        plan = {
            "archive_original_path": r"D:\Research outputs\study",
            "provenance": {"checkout_path": r"C:\Users\Test User\OpenT1D\app"},
            "coordinator_executable": r"C:\Users\Test User\OpenT1D\runtime\python.exe",
            "configuration": {"timeout_seconds": 600},
            "execution_locations": runtime,
        }
        args, _ = expected_stage(plan, "historical")
        self.assertEqual(args[6], r"D:\Research outputs\study\historical")
        args, _ = expected_stage(plan, "observer_repeat", "model")
        self.assertEqual(args[0], runtime["executables"][OBSERVER_PROJECT])
        self.assertEqual(args[6], plan["archive_original_path"])
        wrong = copy.deepcopy(runtime)
        wrong["executables"][OBSERVER_PROJECT] = "relative/python.exe"
        with self.assertRaises(ValueError):
            locations.validate(wrong)
        legacy = {key: value for key, value in plan.items() if key != "execution_locations"}
        self.assertEqual(
            expected_stage(legacy, "source_primary", "model")[0][0],
            legacy["provenance"]["checkout_path"] + "/" + NATIVE_PROJECT + "/.venv/bin/python",
        )
        args = command(
            r"D:\Research outputs\campaign",
            2,
            {"cell": "cell", "id": "cell--r001"},
            coordinator=plan["coordinator_executable"],
        )
        self.assertEqual(args[0], plan["coordinator_executable"])
        self.assertEqual(
            args[-1],
            r"D:\Research outputs\campaign\sessions\session-0002\attempts\cell--r001\archive",
        )

    def test_researcher_archive_with_foreign_original_paths_never_opens_them(self):
        from experiments.m3.common import encoded
        from experiments.m3.researcher.common import read

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, _ = configuration(root / "inputs", people=1)
            archive = root / "archive"
            original = run_study(config, archive, timeout=10)
            self.assertEqual(
                (archive / "report.md").read_bytes(), markdown(original).encode("utf-8")
            )
            plan, _ = read(archive / "plan.json")
            plan["config"]["predictor"] = r"Z:\unavailable\predictor.json"
            for person in plan["config"]["people"]:
                person["input"]["file"] = rf"Z:\unavailable\{person['id']}.json"
            declaration = plan["predictor"]
            declaration["source"]["file"] = r"Z:\unavailable\source.py"
            declaration["settings"]["file"] = r"Z:\unavailable\settings.json"
            plan["config_sha256"] = digest(encoded(plan["config"]))
            save(archive / "plan.json", plan)
            save(archive / "predictor/declaration.json", declaration)
            seal(archive)
            rebuilt = reconstruct(archive, root / "rebuilt")
            self.assertEqual(rebuilt["evaluation"], original["evaluation"])
            self.assertEqual(
                (root / "rebuilt/report.md").read_bytes(), markdown(rebuilt).encode("utf-8")
            )

    @unittest.skipUnless(os.name == "nt", "Actual Windows Job deadline required")
    def test_nested_predictor_deadline_is_archived_and_root_reaped(self):
        from experiments.m3.researcher import study
        from experiments.m3.researcher.common import read

        roots = []
        original_spawn = study.spawn

        def capture_spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            roots.append(process)
            self.addCleanup(process._opent1d_ownership.close)
            return process

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "descendant.pid"
            source = (
                "import subprocess,sys,time\n"
                "spawned=False\n"
                "def predict(request, settings):\n"
                " global spawned\n"
                " if not spawned:\n"
                "  p=subprocess.Popen([sys.executable,'-S','-c',"
                "'import time;time.sleep(30)'])\n"
                f"  open({str(marker)!r},'w').write(str(p.pid))\n"
                "  spawned=True\n"
                " time.sleep(30)\n"
                " return request['values_mg_dl'][-1]\n"
            )
            config, value = configuration(root / "inputs", source=source, people=1)
            archive = root / "archive"
            with patch.object(study, "spawn", side_effect=capture_spawn):
                result = run_study(config, archive, timeout=2)
            person = value["people"][0]["id"]
            state, _ = read(archive / "cases" / person / "state.json")
            plan, _ = read(archive / "plan.json")
            self.assertEqual(plan["timeout_seconds"], 2)
            self.assertEqual(
                result["evaluation"]["people"][person]["execution_status"], "interrupted"
            )
            self.assertEqual(state["status"], "interrupted")
            self.assertEqual(state["error_type"], "TimeoutExpired")
            self.assertEqual(len(roots), 1)
            self.assertIsNotNone(roots[0].poll())
            self.assertTrue(roots[0]._opent1d_ownership.closed)
            # A valid deadline can expire during imports, before predict starts.
            # The separate handshake test proves live nested-child ownership.

    @unittest.skipUnless(os.name == "nt", "Actual Windows Job inheritance required")
    def test_nested_predictor_stdin_and_live_descendant_are_owned(self):
        import ctypes
        import inspect
        from ctypes import wintypes

        from experiments.m3.researcher import study
        from experiments.m3.researcher.common import read

        worker_timeout = inspect.signature(study.run_study).parameters["timeout"].default

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, arguments, result in (
            ("OpenProcess", (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD), wintypes.HANDLE),
            ("WaitForSingleObject", (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
            (
                "IsProcessInJob",
                (wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)),
                wintypes.BOOL,
            ),
            ("CloseHandle", (wintypes.HANDLE,), wintypes.BOOL),
        ):
            function = getattr(kernel, name)
            function.argtypes, function.restype = arguments, result
        stopped = threading.Event()
        witnesses, errors, roots, observers = [], [], [], []
        original_spawn = study.spawn
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker, marker_pending = root / "descendant.pid", root / "descendant.pending"
            acknowledgement, ack_pending = root / "observed.ack", root / "observed.pending"
            # A natural child exit must not satisfy the final cleanup assertion.
            # Only owned cleanup should release this indefinitely waiting child.
            source = (
                "import os,subprocess,sys,time\n"
                "spawned=False\n"
                "def predict(request, settings):\n"
                " global spawned\n"
                " if not spawned:\n"
                "  p=subprocess.Popen([sys.executable,'-S','-c',"
                "'import threading;threading.Event().wait()'])\n"
                f"  with open({str(marker_pending)!r},'w') as receipt: receipt.write(str(p.pid))\n"
                f"  os.replace({str(marker_pending)!r},{str(marker)!r})\n"
                f"  while not os.path.isfile({str(acknowledgement)!r}): time.sleep(0.01)\n"
                "  spawned=True\n"
                " return request['values_mg_dl'][-1]\n"
            )
            config, value = configuration(root / "inputs", source=source, people=1)

            def observe_child(process, admitted_at):
                handle = None
                try:
                    # Freezing configuration can be slow. This bound starts only
                    # after the real worker has been spawned and assigned its Job.
                    deadline = admitted_at + worker_timeout
                    while not stopped.is_set() and time.monotonic() < deadline:
                        if marker.is_file():
                            pid = int(marker.read_text())  # Atomically published.
                            handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)
                            if not handle:
                                raise ctypes.WinError(ctypes.get_last_error())
                            member = wintypes.BOOL()
                            job = process.job.handle
                            if not job or not kernel.IsProcessInJob(
                                handle, job, ctypes.byref(member)
                            ):
                                raise RuntimeError("Cannot verify nested child's owned Job")
                            if not member.value or kernel.WaitForSingleObject(handle, 0) != 258:
                                raise RuntimeError("Nested child was not alive in the owned Job")
                            witnesses.append(handle)
                            handle = None  # Retain this exact handle through product cleanup.
                            ack_pending.write_bytes(b"live-owned-child-observed")
                            ack_pending.replace(acknowledgement)
                            return
                        stopped.wait(0.01)
                    raise AssertionError(
                        "Nested child did not reach live admission before deadline"
                    )
                except BaseException as error:
                    errors.append(error)
                finally:
                    if handle:
                        kernel.CloseHandle(handle)

            def capture_spawn(*args, **kwargs):
                process = original_spawn(*args, **kwargs)
                roots.append(process)
                self.addCleanup(process._opent1d_ownership.close)
                observer = threading.Thread(
                    target=observe_child, args=(process, time.monotonic()), daemon=True
                )
                observers.append(observer)
                observer.start()
                return process

            try:
                with patch.object(study, "spawn", side_effect=capture_spawn):
                    # Exercise normal successful execution, not a shorter speed budget.
                    result = run_study(config, root / "archive")
            finally:
                stopped.set()
                for observer in observers:
                    observer.join(timeout=5)
                for handle in witnesses:
                    self.addCleanup(kernel.CloseHandle, handle)
            self.assertTrue(all(not observer.is_alive() for observer in observers))
            self.assertEqual(errors, [])
            self.assertEqual(len(roots), 1)
            self.assertEqual(len(witnesses), 1)
            self.assertTrue(acknowledgement.is_file())
            plan, _ = read(root / "archive" / "plan.json")
            self.assertEqual(plan["timeout_seconds"], worker_timeout)
            person = value["people"][0]["id"]
            self.assertEqual(
                result["evaluation"]["people"][person]["execution_status"], "completed"
            )
            self.assertIsNotNone(roots[0].poll())
            self.assertTrue(roots[0]._opent1d_ownership.closed)
            # No PID-based control: this is the same handle observed alive above.
            self.assertEqual(kernel.WaitForSingleObject(witnesses[0], 0), 0)


if __name__ == "__main__":
    unittest.main()
