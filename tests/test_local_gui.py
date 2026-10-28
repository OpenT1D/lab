"""Local-control security, immutable inputs and actual owned-process lifecycle."""

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from experiments.gui.ownership import Ownership
from experiments.gui.server import Server, create_server
from experiments.gui.service import TASK, Service, digest, encode, inventory, read_json


class ProcessService(Service):
    script = "import json; print(json.dumps({'ready':True}))"
    budget = 2

    def commands(self, _job, _configuration, _archive):
        return [([sys.executable, "-B", "-S", "-c", self.script], self.budget)]


@unittest.skipUnless(os.name == "posix", "Real POSIX journal publication regression")
class JournalPublicationTests(unittest.TestCase):
    def test_pending_symlink_preserves_unrelated_bytes_and_recovers_running_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = Service(root)
            try:
                job = {
                    "schema": "opent1d.gui-job/1",
                    "id": "job-preserved",
                    "task": TASK,
                    "operation": "check",
                    "state": "queued",
                    "commands": [],
                    "result": None,
                    "error": None,
                }
                folder = service.data / job["id"]
                folder.mkdir()
                journal = folder / "job.json"
                pending = folder / "job.tmp"
                service.persist(job)
                saved = journal.read_bytes()
                unrelated = root / "unrelated.txt"
                unrelated.write_bytes(b"preserve unrelated bytes\x00\xff\n")
                original = unrelated.read_bytes()
                pending.symlink_to(unrelated)
                changed = {**job, "state": "running", "pid": os.getpid()}
                with journal.open("rb") as previous:
                    service.persist(changed)
                    self.assertEqual(previous.read(), saved)
                self.assertEqual(unrelated.read_bytes(), original)
                self.assertTrue(pending.is_symlink())
                self.assertEqual(pending.readlink(), unrelated)
                self.assertFalse(journal.is_symlink())
                self.assertEqual(journal.stat().st_nlink, 1)
                self.assertEqual(journal.read_bytes(), encode(changed))
                self.assertEqual(
                    sorted(path.name for path in folder.iterdir()), ["job.json", "job.tmp"]
                )

                service.close()
                service = Service(root)
                recovered = service.jobs[job["id"]]
                self.assertEqual(recovered["state"], "failed")
                self.assertEqual(
                    recovered["error"], "Previous server stopped; ownership not adopted"
                )
                self.assertIsNone(service.active)
                self.assertIsNone(service.process)
                self.assertFalse(journal.is_symlink())
                self.assertEqual(journal.stat().st_nlink, 1)
                self.assertEqual(journal.read_bytes(), encode(recovered))
                self.assertEqual(unrelated.read_bytes(), original)
                self.assertTrue(pending.is_symlink())
                self.assertEqual(pending.readlink(), unrelated)
                self.assertEqual(
                    sorted(path.name for path in folder.iterdir()), ["job.json", "job.tmp"]
                )
                service.close()
                service = Service(root)
                self.assertEqual(service.jobs[job["id"]], recovered)
                self.assertEqual(unrelated.read_bytes(), original)
            finally:
                service.close()


class LocalGUITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "model.py").write_text(
            "raise RuntimeError('must not execute during configuration')\n"
        )
        (self.root / "model.json").write_text("{}")
        self.service = ProcessService(self.root)
        self.config = self.service.defaults()
        self.config["sources"] = [
            {"id": name, "model": "model.py", "declaration": "model.json"}
            for name in ("left", "right")
        ]

    def tearDown(self):
        self.service.close()
        self.temporary.cleanup()

    def configured(self):
        return self.service.configure(self.config)

    def finished(self, identity):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = self.service.get_job(identity)
            if job["state"] not in {"queued", "running", "cancelling"}:
                return job
            time.sleep(0.01)
        self.fail("Owned operation did not terminate")

    @unittest.skipUnless(os.name == "posix", "Real POSIX process ownership regression")
    def test_post_spawn_journal_failure_reaps_worker_and_closes_log(self):
        self.assert_admission_journal_failure(False)

    @unittest.skipUnless(os.name == "posix", "Real POSIX process ownership regression")
    def test_persistent_journal_failure_reaps_worker_and_allows_shutdown(self):
        self.assert_admission_journal_failure(True)
        self.assertTrue(self.service.closing)
        self.service.close()
        self.service = ProcessService(self.root)

    def assert_admission_journal_failure(self, persistent):
        self.service.script = "import time; time.sleep(60)"
        configured = self.configured()
        persist, popen = self.service.persist, subprocess.Popen
        children, logs, injected = [], [], False

        def launch(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            logs.append(kwargs["stdout"])
            self.addCleanup(kwargs["stdout"].close)
            self.addCleanup(child.wait, timeout=5)
            self.addCleanup(lambda: child.poll() is None and child.kill())
            return child

        def fail_once(job):
            nonlocal injected
            if (job.get("pid") is not None and not injected) or (persistent and injected):
                if not injected:
                    self.assertIsNone(self.service.process.poll())
                injected = True
                raise OSError("Injected admitted journal write failure")
            persist(job)

        with (
            patch("experiments.gui.service.subprocess.Popen", side_effect=launch),
            patch.object(self.service, "persist", side_effect=fail_once),
        ):
            job = self.service.start("check", configured["id"])
            finished = self.finished(job["id"])
            self.service.thread.join(5)
        self.assertTrue(injected)
        self.assertEqual(finished["state"], "failed")
        self.assertIn("Injected admitted journal write failure", finished["error"])
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertTrue(logs[0].closed)
        self.assertIsNone(self.service.process)
        self.assertIsNone(self.service.active)

    def test_post_spawn_journal_failure_releases_live_windows_job(self):
        configured = self.configured()
        persist = self.service.persist
        process, owner = Mock(pid=123), Mock()
        process.launch_record = {
            "requested_argv": ["requested-python", "-S", "-m", "experiments.workflows"],
            "argv": ["actual-python", "-S", "-m", "experiments.gui.windows_worker"],
            "selection": "current-cpython-stdlib-base",
        }
        process.poll.return_value = None
        process.wait.return_value = 1
        owner.observe.return_value = {123: {"authority": "live-windows-job"}}
        owner.cleanup.return_value = (False, [])
        owner.receipt.return_value = []
        logs, injected = [], False

        def launch(_args, **kwargs):
            logs.append(kwargs["stdout"])
            self.addCleanup(kwargs["stdout"].close)
            return process, owner

        def fail_once(job):
            nonlocal injected
            if job.get("pid") is not None or injected:
                injected = True
                raise OSError("Injected Windows journal write failure")
            persist(job)

        host = SimpleNamespace(**{**vars(os), "name": "nt"})
        with (
            patch("experiments.gui.service.os", host),
            patch("experiments.gui.windows_process.spawn_owned", side_effect=launch),
            patch.object(self.service, "persist", side_effect=fail_once),
        ):
            job = self.service.start("check", configured["id"])
            finished = self.finished(job["id"])
            self.service.thread.join(5)
        self.assertTrue(injected)
        self.assertEqual(finished["state"], "failed")
        self.assertIn("Injected Windows journal write failure", finished["error"])
        owner.cleanup.assert_called_once()
        owner.close.assert_called_once_with()
        self.assertTrue(self.service.closing)
        self.assertEqual(finished["commands"][0]["windows_launch"], process.launch_record)
        self.assertTrue(logs[0].closed)
        self.assertIsNone(self.service.process)
        self.assertIsNone(self.service.active)

    def test_configuration_is_passive_and_snapshots_both_sources(self):
        record = self.configured()
        frozen = Path(record["config"]["sources"][0]["model"])
        self.assertNotEqual(frozen, self.root / "model.py")
        self.assertEqual(frozen.read_bytes(), (self.root / "model.py").read_bytes())
        self.assertFalse(record["ready"])
        self.assertEqual(self.service.list_jobs(), [])

    def test_optional_windows_launch_journal_is_accounting_and_never_execution_authority(self):
        configured = self.configured()
        job = self.service.start("check", configured["id"])
        finished = self.finished(job["id"])
        self.service.thread.join(5)
        marker = self.root / "recorded-command-must-not-run"
        for included in (False, True):
            with self.subTest(windows_launch=included):
                command = self.service.jobs[job["id"]]["commands"][0]
                if included:
                    command["windows_launch"] = {
                        "requested_argv": ["untrusted-recorded-request"],
                        "argv": [sys.executable, "-c", f"open({str(marker)!r},'w').write('bad')"],
                        "selection": "historical-accounting-only",
                    }
                self.service.persist(self.service.jobs[job["id"]])
                self.service.close()
                with patch("experiments.gui.service.subprocess.Popen") as launch:
                    self.service = ProcessService(self.root)
                    restored = self.service.get_job(job["id"])
                    launch.assert_not_called()
                self.assertEqual(restored["state"], finished["state"])
                self.assertEqual(restored["commands"][0], command)
                self.assertFalse(marker.exists())
                self.assertIsNone(self.service.active)
                self.assertIsNone(self.service.process)

    def test_restart_restores_own_frozen_study_without_saved_readiness(self):
        original = self.configured()
        self.service.configurations[original["id"]]["ready"] = True
        self.service.close()
        self.service = ProcessService(self.root)
        restored = self.service.resolve_configuration(original["id"])
        self.assertFalse(restored["ready"])
        self.assertEqual(restored["sha256"], original["sha256"])
        self.assertEqual(restored["config"], original["config"])

    def test_restored_source_pointer_must_belong_to_its_own_configuration(self):
        original = self.configured()
        self.service.close()
        path = self.service.data / original["id"] / "frozen.json"
        record = read_json(path)
        record["config"]["sources"][0]["model"] = str(self.root / "model.py")
        path.write_bytes(encode(record))
        self.service = ProcessService(self.root)
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.service.resolve_configuration(original["id"])
        self.assertNotIn(original["id"], self.service.configurations)

    def test_install_attempt_invalidates_all_study_readiness(self):
        left, right = self.configured(), self.configured()
        for configuration in self.service.configurations.values():
            configuration["ready"] = True
        job = self.service.start("install", left["id"])
        self.finished(job["id"])
        self.assertFalse(self.service.configurations[left["id"]]["ready"])
        self.assertFalse(self.service.configurations[right["id"]]["ready"])

    def test_changed_original_and_frozen_sources_refuse_dispatch(self):
        for change_original in (True, False):
            with self.subTest(change_original=change_original):
                record = self.configured()
                path = (
                    self.root / "model.py"
                    if change_original
                    else Path(record["config"]["sources"][0]["model"])
                )
                path.write_text("a different changed source" if not change_original else "changed")
                with self.assertRaisesRegex(ValueError, "Frozen source changed"):
                    self.service.start("check", record["id"])
                self.assertIsNone(self.service.active)

    def test_paths_symlinks_hidden_files_and_byte_limits_are_refused(self):
        (self.root / "linked.py").symlink_to(self.root / "model.py")
        (self.root / ".hidden.py").write_text("hidden")
        for path in ("../outside.py", "linked.py", ".hidden.py"):
            self.config["sources"][0]["model"] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.configured()
        self.config["sources"][0]["model"] = "model.py"
        (self.root / "model.py").write_bytes(b"x" * 1048577)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            self.configured()

    def test_task_conditions_and_budgets_reject_unknown_or_nonfinite_inputs(self):
        for key, value in (
            ("scenarios", []),
            ("scenarios", ["fasting", "fasting"]),
            ("timeout_seconds", True),
            ("timeout_seconds", 1801),
            ("source_timeout_seconds", float("nan")),
            ("schema", "legacy"),
        ):
            config = {**self.config, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.service.configure(config)

    def test_passive_check_is_needed_before_run(self):
        record = self.configured()
        with self.assertRaisesRegex(ValueError, "Check this configuration"):
            self.service.start("run", record["id"])
        checked = self.service.start("check", record["id"])
        self.assertEqual(self.finished(checked["id"])["state"], "completed")
        running = self.service.start("run", record["id"])
        self.assertEqual(self.finished(running["id"])["exit_code"], 0)

    def test_install_ready_does_not_replace_the_configuration_check(self):
        record = self.configured()
        install = self.service.start("install", record["id"])
        self.assertEqual(self.finished(install["id"])["state"], "completed")
        self.assertFalse(self.service.configurations[record["id"]]["ready"])
        with self.assertRaisesRegex(ValueError, "Check this configuration"):
            self.service.start("run", record["id"])

    def test_actual_second_process_is_refused_before_loading_active_journals(self):
        self.service.script = "import time; time.sleep(60)"
        job = self.service.start("check", self.configured()["id"])
        deadline = time.monotonic() + 5
        while self.service.get_job(job["id"])["pid"] is None:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        journal = self.service.data / job["id"] / "job.json"
        saved = journal.read_bytes()
        script = (
            "import sys; from pathlib import Path; "
            "from experiments.gui.service import Service; "
            "service=Service(Path(sys.argv[1])); service.close()"
        )
        refused = subprocess.run(
            [sys.executable, "-B", "-S", "-c", script, str(self.root)],
            capture_output=True,
            timeout=5,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn(b"Another GUI server", refused.stderr)
        self.assertEqual(journal.read_bytes(), saved)
        self.assertEqual(self.service.get_job(job["id"])["state"], "running")
        self.assertFalse(os.get_inheritable(self.service.manager.descriptor))
        self.service.cancel(job["id"])
        self.finished(job["id"])
        self.service.close()
        accepted = subprocess.run(
            [sys.executable, "-B", "-S", "-c", script, str(self.root)],
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        reopened = ProcessService(self.root)
        reopened.close()

    def test_symlink_and_nonregular_manager_locks_are_refused_without_writes(self):
        self.service.close()
        path = self.service.data / ".manager.lock"
        path.unlink()
        external = self.root / "external-lock"
        external.write_bytes(b"preserve this file")
        path.symlink_to(external)
        with self.assertRaises(OSError):
            ProcessService(self.root)
        self.assertEqual(external.read_bytes(), b"preserve this file")
        path.unlink()
        os.mkfifo(path)
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError, "regular file"):
            ProcessService(self.root)
        self.assertLess(time.monotonic() - started, 2)
        path.unlink()

    def test_init_and_server_bind_failures_release_the_manager_lock(self):
        self.service.close()
        with patch.object(Service, "load_journals", side_effect=ValueError("invalid startup")):
            with self.assertRaisesRegex(ValueError, "invalid startup"):
                ProcessService(self.root)
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            with patch("experiments.gui.server.Service", lambda: ProcessService(self.root)):
                with self.assertRaises(OSError):
                    create_server(occupied.getsockname()[1])
        reopened = ProcessService(self.root)
        reopened.close()

    def test_actual_sighup_shutdown_cleans_worker_and_releases_manager_lock(self):
        self.service.close()
        script = """
import sys
from pathlib import Path
from experiments.gui.service import Service
from experiments.gui.server import Server
import experiments.gui.__main__ as entry
class WorkerService(Service):
    def commands(self, *_args):
        return [([sys.executable, '-B', '-S', '-c', 'import time; time.sleep(60)'], 60)]
service = WorkerService(Path(sys.argv[1]))
config = service.defaults()
for source in config['sources']:
    source.update(model='model.py', declaration='model.json')
record = service.configure(config)
service.start('check', record['id'])
server = Server(service)
entry.create_server = lambda _port: server
sys.argv = ['gui', '--no-browser']
entry.main()
"""
        output = self.root / "server-output.log"
        with output.open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, "-B", "-S", "-c", script, str(self.root)],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            try:
                deadline, worker = time.monotonic() + 5, None
                while time.monotonic() < deadline:
                    journals = list(self.service.data.glob("job-*/job.json"))
                    if journals:
                        try:
                            receipt = read_json(journals[0])
                        except (OSError, ValueError):
                            # Startup replaces its journal atomically; wait for a stable
                            # bounded read rather than weakening the production reader.
                            pass
                        else:
                            worker = receipt.get("pid")
                    if worker and b"local study interface" in output.read_bytes():
                        break
                    self.assertIsNone(process.poll(), output.read_text())
                    time.sleep(0.01)
                self.assertIsNotNone(worker, output.read_text())
                self.assertIn(b"local study interface", output.read_bytes())
                process.send_signal(signal.SIGHUP)
                self.assertEqual(process.wait(timeout=5), 0, output.read_text())
                with self.assertRaises(ProcessLookupError):
                    os.kill(worker, 0)
                self.assertEqual(read_json(journals[0])["state"], "cancelled")
                reopened = ProcessService(self.root)
                reopened.close()
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)

    def test_actual_sighup_waits_for_transient_journal_replacement(self):
        reads = []
        stable_read = read_json

        def replaced_once(path):
            reads.append(path)
            if len(reads) == 1:
                raise ValueError("File changed while reading")
            return stable_read(path)

        with patch(__name__ + ".read_json", side_effect=replaced_once):
            self.test_actual_sighup_shutdown_cleans_worker_and_releases_manager_lock()
        self.assertGreater(len(reads), 1)

    def test_actual_cancel_stops_owner_and_preserves_job_receipt(self):
        self.service.script = "import time; time.sleep(60)"
        job = self.service.start("check", self.configured()["id"])
        while self.service.get_job(job["id"])["pid"] is None:
            time.sleep(0.01)
        pid = self.service.get_job(job["id"])["pid"]
        with self.assertRaisesRegex(ValueError, "One active"):
            self.service.start("check", job["configuration"])
        self.service.cancel(job["id"])
        final = self.finished(job["id"])
        self.assertEqual(final["state"], "cancelled")
        self.assertTrue(final["cancel_requested"])
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        receipt = self.root / "results/gui" / job["id"] / "job.json"
        self.assertEqual(json.loads(receipt.read_bytes())["state"], "cancelled")

    def test_cancel_signals_once_during_cooperative_finalization(self):
        receipt = self.root / "signal-count.json"
        ready = self.root / "signal-handler-ready"
        self.service.script = f"""
import json, signal, time
from pathlib import Path
count = 0
def stop(signum, frame):
    global count
    count += 1
signal.signal(signal.SIGTERM, stop)
Path({str(ready)!r}).write_text("ready")
while count == 0:
    time.sleep(0.01)
time.sleep(0.2)
Path({str(receipt)!r}).write_text(json.dumps({{"count": count}}))
"""
        job = self.service.start("check", self.configured()["id"])
        deadline = time.monotonic() + 5
        while not ready.is_file():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        self.service.cancel(job["id"])
        self.service.cancel(job["id"])
        final = self.finished(job["id"])
        self.assertEqual(final["state"], "cancelled")
        self.assertFalse(final["cleanup_forced"])
        self.assertEqual(json.loads(receipt.read_text())["count"], 1)

    def test_deadline_forcekill_reaps_term_resistant_owner(self):
        self.service.script = (
            "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"
        )
        self.service.budget = 0.15
        with patch("experiments.gui.service.CLEANUP_SECONDS", 0.15):
            job = self.service.start("check", self.configured()["id"])
            final = self.finished(job["id"])
        self.assertEqual(final["state"], "failed")
        self.assertTrue(final["cleanup_forced"])
        self.assertEqual(final["exit_code"], -9)
        self.assertIn("deadline", final["error"])

    def test_unsealed_or_active_study_cannot_be_reconstructed(self):
        record = self.configured()
        self.service.configurations[record["id"]]["ready"] = True
        run = self.service.start("run", record["id"])
        self.finished(run["id"])
        with self.assertRaisesRegex(ValueError, "no sealed archive"):
            self.service.start("reconstruct", archive_job=run["id"])

    def test_restart_retains_incomplete_evidence_without_adopting_pid(self):
        directory = self.service.data / "job-preserved"
        directory.mkdir()
        (directory / "job.json").write_bytes(
            encode(
                {
                    "schema": "opent1d.gui-job/1",
                    "id": directory.name,
                    "task": TASK,
                    "operation": "run",
                    "state": "running",
                    "pid": os.getpid(),
                }
            )
        )
        self.service.close()
        restarted = ProcessService(self.root)
        try:
            self.assertIsNone(restarted.active)
            self.assertEqual(restarted.get_job(directory.name)["state"], "failed")
            os.kill(os.getpid(), 0)
        finally:
            restarted.close()

    def test_restart_skips_invalid_symlink_and_oversized_journals(self):
        external = self.root / "outside-journal.json"
        external.write_bytes(b"[]")
        for name, raw in (
            ("job-array", b"[]"),
            ("job-null", b"null"),
            ("job-duplicate", b'{"id":1,"id":2}'),
        ):
            directory = self.service.data / name
            directory.mkdir()
            (directory / "job.json").write_bytes(raw)
        linked = self.service.data / "job-symlink"
        linked.mkdir()
        (linked / "job.json").symlink_to(external)
        large = self.service.data / "job-large"
        large.mkdir()
        with (large / "job.json").open("wb") as stream:
            stream.truncate(100000000)
        self.service.close()
        restarted = ProcessService(self.root)
        try:
            self.assertEqual(restarted.list_jobs(), [])
            self.assertEqual(external.read_bytes(), b"[]")
        finally:
            restarted.close()

    def verified_reports(self):
        source_id, rebuilt_id = "job-source", "job-rebuilt"
        report = {"schema": "test-report", "passed": True, "sources": {}, "scenarios": []}
        for identity, operation, folder in (
            (source_id, "run", "archive"),
            (rebuilt_id, "reconstruct", "reconstructed"),
        ):
            destination = self.service.data / identity / folder
            destination.mkdir(parents=True)
            (destination / "report.json").write_bytes(encode(report))
            (destination / "figure.svg").write_text("<svg />")
            (destination / "report.md").write_text("# Recorded report\n")
            self.service.jobs[identity] = {
                "schema": "opent1d.gui-job/1",
                "id": identity,
                "task": TASK,
                "operation": operation,
                "state": "completed",
                "verification": "native_reader_verified",
                "archive_job": source_id if operation == "reconstruct" else None,
                "verified_inventory": inventory(destination),
                "verified_artifacts_sha256": {
                    name: digest((destination / name).read_bytes())
                    for name in ("report.json", "figure.svg", "report.md")
                },
                "commands": [],
                "result": None,
            }
        self.service.jobs[rebuilt_id]["verified_source_inventory"] = self.service.jobs[source_id][
            "verified_inventory"
        ]
        return source_id, rebuilt_id

    def test_reconstructed_report_tamper_withdraws_verified_display_and_download(self):
        _source, rebuilt = self.verified_reports()
        path = self.service.data / rebuilt / "reconstructed/report.json"
        initial = self.service.report(rebuilt)
        self.assertEqual(initial["verification"], "native_reader_verified")
        path.write_bytes(encode({"passed": False, "sources": {}}))
        changed = self.service.report(rebuilt)
        self.assertEqual(changed["verification"], "changed_since_verification")
        self.assertNotEqual(changed["report_sha256"], initial["report_sha256"])
        self.assertFalse(changed["passed"])
        self.assertEqual(self.service.report_bytes(rebuilt, "report.json"), path.read_bytes())

    def test_source_or_figure_change_withdraws_job_listing_and_file_verification(self):
        source, rebuilt = self.verified_reports()
        (self.service.data / rebuilt / "reconstructed/figure.svg").write_text("<svg>changed</svg>")
        self.service.report_bytes(rebuilt, "figure.svg")
        self.assertEqual(
            self.service.get_job(rebuilt)["verification"], "changed_since_verification"
        )
        (self.service.data / source / "archive/changed.txt").write_text("changed source")
        self.service.list_jobs()
        self.assertEqual(self.service.get_job(source)["verification"], "changed_since_verification")

    def test_restart_never_promotes_persisted_verification_to_live_attestation(self):
        source, _rebuilt = self.verified_reports()
        self.service.persist(self.service.jobs[source])
        self.service.close()
        restarted = ProcessService(self.root)
        try:
            self.assertEqual(restarted.get_job(source)["verification"], "recorded_verification")
        finally:
            restarted.close()

    def test_nonregular_source_and_oversized_report_fail_without_reading_body(self):
        fifo = self.root / "pipe.py"
        os.mkfifo(fifo)
        self.config["sources"][0]["model"] = str(fifo)
        with self.assertRaises(ValueError):
            self.configured()
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError, "nonregular"):
            read_json(fifo)
        self.assertLess(time.monotonic() - started, 2)
        _source, rebuilt = self.verified_reports()
        path = self.service.data / rebuilt / "reconstructed/report.json"
        with path.open("wb") as stream:
            stream.truncate(100000000)
        with self.assertRaisesRegex(ValueError, "display limit"):
            self.service.report_bytes(rebuilt, "report.json")

    def test_malformed_native_report_and_source_metadata_are_cleanly_rejected(self):
        _source, rebuilt = self.verified_reports()
        path = self.service.data / rebuilt / "reconstructed/report.json"
        for value in (
            None,
            [],
            {"sources": []},
            {"sources": {"source": []}},
            {"sources": {"source": {"declaration": []}}},
        ):
            path.write_bytes(encode(value))
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "object"):
                self.service.report(rebuilt)

    def test_raw_artifact_substitution_cannot_borrow_a_verified_inventory(self):
        source, rebuilt = self.verified_reports()
        from experiments.gui import service as backend

        genuine_read = backend.bounded_bytes
        for name, raw in (
            ("report.json", encode({"passed": False, "sources": {}})),
            ("figure.svg", b"<svg>forged</svg>"),
            ("report.md", b"# Forged report\n"),
        ):
            self.service.jobs[rebuilt]["verification"] = "native_reader_verified"
            target = self.service.data / rebuilt / "reconstructed" / name

            def swapped(path, maximum):
                return raw if path == target else genuine_read(path, maximum)

            with patch("experiments.gui.service.bounded_bytes", side_effect=swapped):
                if name == "report.json":
                    view = self.service.report(rebuilt)
                    self.assertFalse(view["passed"])
                else:
                    self.assertEqual(self.service.report_bytes(rebuilt, name), raw)
            self.assertEqual(
                self.service.get_job(rebuilt)["verification"], "changed_since_verification"
            )
            self.assertEqual(self.service.get_job(source)["verification"], "native_reader_verified")

    def test_overgrown_frozen_configuration_is_refused_before_dispatch(self):
        record = self.configured()
        path = self.service.data / record["id"] / "config.json"
        with path.open("wb") as stream:
            stream.truncate(100000000)
        with self.assertRaisesRegex(ValueError, "byte limit"):
            self.service.start("check", record["id"])

    def wait_owned(self, identity, count):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            observed = self.service.get_job(identity).get("owned_processes", [])
            if len(observed) >= count:
                return observed
            time.sleep(0.01)
        self.fail("Descendant start identity was not observed")

    def descendant_script(self, *, exit_owner=False, resistant=False):
        child = (
            "import signal,time; "
            + ("signal.signal(signal.SIGTERM,signal.SIG_IGN); " if resistant else "")
            + "time.sleep(60)"
        )
        return (
            "import subprocess,sys,time,signal; "
            + (
                "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                if resistant and not exit_owner
                else ""
            )
            + f"subprocess.Popen([sys.executable,'-S','-c',{child!r}],start_new_session=True); "
            + ("time.sleep(0.3)" if exit_owner else "time.sleep(60)")
        )

    def assert_not_live(self, observed):
        from experiments.gui.ownership import ProcessTable

        table = ProcessTable()
        for old in observed:
            current = table.one(old["pid"])
            self.assertTrue(
                current is None or current["start"] != old["start"] or not current["alive"]
            )

    def test_cancel_cleans_observed_separate_session_child_after_entry_exit(self):
        self.service.script = self.descendant_script()
        with patch("experiments.gui.service.CLEANUP_SECONDS", 0.2):
            job = self.service.start("check", self.configured()["id"])
            observed = self.wait_owned(job["id"], 2)
            self.service.cancel(job["id"])
            final = self.finished(job["id"])
        self.assertEqual(final["state"], "cancelled")
        self.assertEqual(final["remaining_owned_processes"], [])
        self.assert_not_live(observed)

    def test_early_successful_owner_exit_still_cleans_resistant_descendant(self):
        self.service.script = self.descendant_script(exit_owner=True, resistant=True)
        with patch("experiments.gui.service.CLEANUP_SECONDS", 0.15):
            job = self.service.start("check", self.configured()["id"])
            observed = self.wait_owned(job["id"], 2)
            final = self.finished(job["id"])
        self.assertEqual(final["state"], "failed")
        self.assertTrue(final["cleanup_forced"])
        self.assertIn("live descendants", final["error"])
        self.assert_not_live(observed)

    def test_deadline_cleans_resistant_separate_session_descendant(self):
        self.service.script = self.descendant_script(resistant=True)
        self.service.budget = 0.3
        with patch("experiments.gui.service.CLEANUP_SECONDS", 0.15):
            job = self.service.start("check", self.configured()["id"])
            observed = self.wait_owned(job["id"], 2)
            final = self.finished(job["id"])
        self.assertEqual(final["state"], "failed")
        self.assertTrue(final["cleanup_forced"])
        self.assertEqual(final["remaining_owned_processes"], [])
        self.assert_not_live(observed)

    def test_changed_pid_start_identity_is_never_signalled(self):
        root = {"pid": 101, "ppid": os.getpid(), "pgid": 101, "start": "original", "alive": True}

        class Table:
            value = root

            def one(self, _pid):
                return self.value

            def snapshot(self):
                return {101: self.value}

        table = Table()
        ownership = Ownership(type("Owner", (), {"pid": 101})(), table)
        table.value = {**root, "start": "reused"}
        with (
            patch("experiments.gui.ownership.os.killpg") as group,
            patch("experiments.gui.ownership.os.kill") as single,
        ):
            ownership.signal(15)
        group.assert_not_called()
        single.assert_not_called()

    def test_transport_rejects_foreign_host_origin_missing_token_and_large_body(self):
        server = Server(self.service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host = f"127.0.0.1:{server.server_port}"
        origin = "http://" + host

        def request(method, route, body=None, **headers):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request(method, route, body=body, headers={"Host": host, **headers})
            response = connection.getresponse()
            status, response_headers, raw = response.status, response.headers, response.read()
            connection.close()
            return status, response_headers, raw

        try:
            for asset, kind in (
                ("workspace.js", "text/javascript"),
                ("workspace.css", "text/css"),
                ("ux.js", "text/javascript"),
            ):
                with self.subTest(asset=asset):
                    status, response_headers, raw = request("GET", "/" + asset)
                    self.assertEqual(status, 200)
                    self.assertEqual(response_headers["Content-Type"], kind + "; charset=utf-8")
                    self.assertEqual(
                        raw,
                        (
                            Path(__file__).resolve().parents[1] / "experiments/gui/static" / asset
                        ).read_bytes(),
                    )
                    self.assertEqual(request("GET", "/" + asset, Host="attacker.example")[0], 403)
            self.assertEqual(request("GET", "/api/v1/bootstrap")[0], 403)
            self.assertEqual(
                request(
                    "GET",
                    "/api/v1/bootstrap",
                    Host="attacker.example",
                    **{"X-OpenT1D-Token": server.token},
                )[0],
                403,
            )
            headers = {"Content-Type": "application/json", "X-OpenT1D-Token": server.token}
            self.assertEqual(
                request("GET", "/api/v1/bootstrap", **{"X-OpenT1D-Token": "caf\xe9"})[0], 403
            )
            for body in (b'{"schema":1,"schema":2}', b"[" * 1100 + b"{}" + b"]" * 1100):
                self.assertEqual(
                    request("POST", "/api/v1/configurations", body, Origin=origin, **headers)[0],
                    400,
                )
            self.assertEqual(
                request("POST", "/api/v1/configurations", encode(self.config), **headers)[0], 403
            )
            self.assertEqual(
                request(
                    "POST",
                    "/api/v1/configurations",
                    encode(self.config),
                    Origin="https://attacker.example",
                    **headers,
                )[0],
                403,
            )
            self.assertEqual(
                request("POST", "/api/v1/configurations", b"x" * 65537, Origin=origin, **headers)[
                    0
                ],
                400,
            )
            status, response_headers, raw = request(
                "POST", "/api/v1/configurations", encode(self.config), Origin=origin, **headers
            )
            self.assertEqual(status, 201)
            configuration_id = json.loads(raw)["id"]
            route = "/api/v1/configurations/" + configuration_id
            self.assertEqual(request("GET", route)[0], 403)
            status, _, saved = request("GET", route, **headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(saved)["id"], configuration_id)
            self.assertFalse(json.loads(saved)["ready"])
            self.assertEqual(self.service.list_jobs(), [])
            for identity in ("not-owned", "config-" + "0" * 32):
                self.assertEqual(
                    request("GET", "/api/v1/configurations/" + identity, **headers)[0], 400
                )
            self.assertEqual(
                request("GET", route, Origin="https://attacker.example", **headers)[0], 403
            )
            self.assertEqual(response_headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("frame-ancestors 'none'", response_headers["Content-Security-Policy"])
            self.assertEqual(
                request(
                    "GET",
                    "/api/v1/files?directory=../&kind=model",
                    **{"X-OpenT1D-Token": server.token},
                )[0],
                400,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
