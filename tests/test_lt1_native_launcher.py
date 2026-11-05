"""Invented data and fixed Python processes only; no candidate runtime starts."""

import copy
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_lt1_host_context import invented_context

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import native_launcher as launch
from experiments.lt1_diagnostic import native_supervisor as supervisor
from experiments.shared_services import execution


def wire(value):
    return json.dumps(value, sort_keys=True).encode()


@unittest.skipUnless(os.name == "posix", "POSIX native qualification boundary required")
class NativeLauncherDataTests(unittest.TestCase):
    def test_unknown_authority_refuses_before_paths_capture_or_spawn(self):
        class NoPath:
            def __fspath__(self):
                raise AssertionError("unknown request reached supplied path")

        with (
            patch.object(launch.host_context, "capture") as capture,
            patch.object(launch, "supervise") as spawn,
        ):
            with self.assertRaisesRegex(ValueError, "no reviewed execution grants"):
                launch.launch_native(b"malformed", b"malformed", *[NoPath()] * 4)
            capture.assert_not_called()
            spawn.assert_not_called()

    def test_missing_setup_authority_refuses_even_admitted_execution_before_paths(self):
        raw = wire({"setup_receipt_sha256": "a" * 64})
        registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": [],
            "execution": [launch.storage.digest(raw)],
        }
        with (
            patch.object(launch, "_admissions", return_value=registry),
            patch.object(launch, "Path") as paths,
        ):
            with self.assertRaisesRegex(ValueError, "actual setup receipt"):
                launch.launch_native(raw, raw, None, None, None, None)
            paths.assert_not_called()

    def test_registry_boolean_or_unknown_second_grant_cannot_be_adopted(self):
        raw = b"invented"
        registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": [],
            "execution": [launch.storage.digest(raw)],
        }
        with patch.object(launch, "_admissions", return_value=registry):
            with self.assertRaisesRegex(ValueError, "execution grants"):
                launch.authority(raw, b"different")
            registry["execution"] = [True]
            with self.assertRaisesRegex(ValueError, "authority identities"):
                launch.authority(raw, raw)

    def test_background_native_owner_refuses_before_path_intake(self):
        raw = wire({"setup_receipt_sha256": "a" * 64})
        registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": ["a" * 64],
            "execution": [launch.storage.digest(raw)],
        }
        with (
            patch.object(launch, "_admissions", return_value=registry),
            patch.object(launch.threading, "current_thread", return_value=object()),
            patch.object(launch, "Path") as paths,
        ):
            with self.assertRaisesRegex(ValueError, "main-thread owner"):
                launch.launch_native(raw, raw, None, None, None, None)
            paths.assert_not_called()

    def test_live_owner_and_oldest_capture_time_are_required(self):
        value = invented_context()
        now = datetime.now(UTC).isoformat()
        value.update(observed_from=now, observed_to=now)
        value["observer"]["pid"] = os.getpid()
        value["observer"]["posix_session"] = os.getsid(0)
        value["host"]["uid"] = os.getuid()
        with patch.object(launch.host_context, "capture", return_value=copy.deepcopy(value)):
            launch._owner(value, 60)
            value["observer"]["start"] = "different"
            with self.assertRaisesRegex(ValueError, "owner/boot/source"):
                launch._owner(value, 60)
            value["observed_from"] = "2020-01-01T00:00:00Z"
            with self.assertRaisesRegex(ValueError, "stale or unknown"):
                launch._owner(value, 60)

    def test_fixed_profile_has_no_network_or_arbitrary_write_allow(self):
        text = launch.profile(
            Path("/invented/stage"), Path("/invented/packet"), Path("/invented/output")
        )
        self.assertIn("(deny default)", text)
        self.assertIn('(allow file-write* (subpath "/invented/output"))', text)
        self.assertNotIn("allow network", text)
        self.assertNotIn('(subpath "/System")', text)
        self.assertIn("/invented/stage/runtime/bin/node", text)
        for source in (*launch.WORKER, *launch.INTEGRATION, "native-admissions.json"):
            self.assertIn(json.dumps(os.path.normpath(launch.HERE / source)), text)
        current = launch.journal_reader.identity(b"")
        for mapping in (current["implementation"], current["protocol"]["implementation_sha256"]):
            for source in mapping:
                self.assertIn(json.dumps(str(launch.ROOT / source)), text)

    def test_owner_context_cannot_expire_during_capture(self):
        value = invented_context()
        first = datetime.now(UTC)
        value.update(observed_from=first.isoformat(), observed_to=first.isoformat())
        value["observer"].update(pid=os.getpid(), posix_session=os.getsid(0))
        value["host"]["uid"] = os.getuid()
        with (
            patch.object(launch, "datetime") as clock,
            patch.object(launch.host_context, "capture", return_value=copy.deepcopy(value)),
        ):
            clock.now.side_effect = [first + timedelta(seconds=59), first + timedelta(seconds=61)]
            with self.assertRaisesRegex(ValueError, "stale or unknown"):
                launch._owner(value, 60)

    def test_byte_source_alias_and_unsafe_tree_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            file = root / "file.py"
            file.write_bytes(b"invented")
            (root / "alias.py").symlink_to(file)
            with self.assertRaisesRegex(ValueError, "canonical source"):
                launch._source(root / "alias.py")
            root.chmod(0o500)
            try:
                from contextlib import ExitStack

                with ExitStack() as stack:
                    with self.assertRaisesRegex(ValueError, "staging file"):
                        launch._inventory(root, stack)
            finally:
                root.chmod(0o700)

    def test_checkout_and_mutual_directory_case_aliases_are_not_private_roots(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            checkout = base / "Checkout"
            checkout.mkdir(mode=0o700)
            inside = checkout / "private"
            inside.mkdir(mode=0o700)
            separate = [base / name for name in ("stage", "packet", "output", "evidence")]
            for path in separate:
                path.mkdir(mode=0o700)
            alias = base / "checkout/private"
            if not alias.exists():
                alias = inside
            with patch.object(launch, "ROOT", checkout):
                self.assertEqual(launch._roots(separate), separate)
                with self.assertRaisesRegex(ValueError, "outside checkout"):
                    launch._roots([*separate[:3], alias])
                alias = base / "OUTPUT"
                if not alias.exists():
                    alias = separate[2]
                with self.assertRaisesRegex(ValueError, "separate roots"):
                    launch._roots([*separate[:3], alias])


@unittest.skipUnless(os.name == "posix", "POSIX invented intake controls required")
class NativeLauncherPacketTests(unittest.TestCase):
    """Whole pre-start intake with invented payload and mocked OS/native backend."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.base.chmod(0o700)
        self.stage = self.base / "materialization/payload"
        self.stage.mkdir(parents=True)
        self.packet, self.output, self.evidence = [
            self.base / name for name in ("packet", "output", "evidence")
        ]
        for folder in (self.packet, self.output, self.evidence):
            folder.mkdir(mode=0o700)
        self.files = {}
        for name in launch.ENTRIES:
            path = self.stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = ("invented " + name).encode()
            path.write_bytes(raw)
            path.chmod(0o500 if name == "runtime/bin/node" else 0o400)
            self.files[name] = launch.storage.digest(raw)
        for folder in (self.stage, *[p for p in self.stage.rglob("*") if p.is_dir()]):
            folder.chmod(0o500)
        self.sandbox, self.dyld = self.base / "sandbox", self.base / "dyld.sb"
        self.sandbox.write_bytes(b"invented host tool, never executed")
        self.dyld.write_bytes(b"invented imported profile")
        self.patches = []
        for target, name, value in (
            (launch, "SANDBOX", self.sandbox),
            (launch, "DYLD", self.dyld),
            (launch.host_context.sys, "flags", SimpleNamespace(isolated=True, no_site=True)),
            (launch.host_context.sys, "platform", "darwin"),
            (launch.host_context.platform, "machine", lambda: "arm64"),
            (launch.host_context.socket, "gethostname", lambda: "invented-host"),
        ):
            patched = patch.object(target, name, value)
            patched.start()
            self.patches.append(patched)
        patched = patch.dict(
            launch.native_preflight.RUNTIME, {"executable_sha256": self.files["runtime/bin/node"]}
        )
        patched.start()
        self.patches.append(patched)
        self.context = invented_context()
        self.context.update(
            observed_from=datetime.now(UTC).isoformat(), observed_to=datetime.now(UTC).isoformat()
        )
        self.context["observer"].update(pid=os.getpid(), posix_session=os.getsid(0))
        self.context["host"]["uid"] = os.getuid()
        self.blobs = {
            name + ".json": wire({"kind": "invented", "name": name}) for name in launch.RECEIPTS
        }
        self.blobs["plan.json"] = (launch.HERE / "plan.json").read_bytes()
        self.engine = {
            "schema": "opent1d.lt1-native-grant/1",
            "source_revision": launch.native_preflight.REVISION,
            **{key: launch.native_preflight.RUNTIME[key] for key in ("node", "platform", "arch")},
            "host": "invented-host",
            "staging_root": str(self.stage),
            "mode": "wrapped",
            **{
                name + "_sha256": launch.storage.digest(self.blobs[name + ".json"])
                for name in launch.RECEIPTS
            },
            "files": self.files,
            "worker_files": launch._worker(launch.WORKER),
        }
        self.host = {
            "schema": "opent1d.lt1-prestart-host/1",
            "purpose": "qualification-only",
            "owner_context": self.context,
            "launcher_identity": launch.identity(launch.__file__),
            "roots": {
                role: {"path": str(path), "identity": list(launch._signature(path.stat()))}
                for role, path in zip(
                    ("stage", "packet", "output", "evidence"),
                    (self.stage, self.packet, self.output, self.evidence),
                )
            },
            "profile_sha256": launch.storage.digest(
                launch.profile(self.stage, self.packet, self.output).encode()
            ),
            "sandbox_sha256": launch.storage.digest(self.sandbox.read_bytes()),
            "dyld_sha256": launch.storage.digest(self.dyld.read_bytes()),
            "timeout_seconds": 1,
            "grace_seconds": 0.1,
            "max_context_age_seconds": 60,
            "materialization_request_sha256": "d" * 64,
            "materialization_manifest_sha256": "e" * 64,
        }
        # The reviewed packet root is frozen only after all invented bytes are written.
        self.host["roots"]["packet"]["identity"][3] = 0o500
        self.integration = {
            "schema": "opent1d.lt1-integration-grant/1",
            "engine_grant_sha256": None,
            "host_receipt_sha256": None,
            "output_root": str(self.output),
            "attempt": "invented-one",
            "owner_pid": os.getpid(),
            "reader_identity": launch.journal_reader.identity(self.blobs["plan.json"]),
            "implementation": launch._worker(launch.INTEGRATION),
        }
        self.reseal()
        self.started = []

    def tearDown(self):
        for patched in reversed(self.patches):
            patched.stop()
        for path in self.base.rglob("*"):
            if not path.is_symlink():
                path.chmod(0o700 if path.is_dir() else 0o600)
        self.temp.cleanup()

    def reseal(self):
        self.packet.chmod(0o700)
        self.engine_raw = wire(self.engine)
        self.integration["engine_grant_sha256"] = launch.storage.digest(self.engine_raw)
        self.blobs["integration_host_receipt.json"] = wire(self.host)
        self.integration["host_receipt_sha256"] = launch.storage.digest(
            self.blobs["integration_host_receipt.json"]
        )
        self.integration_raw = wire(self.integration)
        self.blobs.update(
            {"grant.json": self.engine_raw, "integration-grant.json": self.integration_raw}
        )
        for name, raw in self.blobs.items():
            path = self.packet / name
            if path.exists():
                path.chmod(0o600)
            path.write_bytes(raw)
            path.chmod(0o400)
        self.packet.chmod(0o500)
        self.registry = {
            "schema": "opent1d.lt1-native-admissions/1",
            "setup": [self.engine["setup_receipt_sha256"]],
            "execution": [
                launch.storage.digest(self.engine_raw),
                launch.storage.digest(self.integration_raw),
            ],
        }

    def invoke(self, *, at_last_capture=None):
        captures = []

        def observed():
            captures.append(True)
            if len(captures) == 2 and at_last_capture:
                at_last_capture()
            return copy.deepcopy(self.context)

        def backend(argv, log_path, **kwargs):
            self.assertEqual(
                argv,
                [
                    str(self.sandbox),
                    "-p",
                    launch.profile(self.stage, self.packet, self.output),
                    str(self.stage / "runtime/bin/node"),
                    str(launch.HERE / "integration_worker.mjs"),
                    str(self.stage),
                    str(self.packet),
                    str(self.output),
                ],
            )
            self.assertEqual(kwargs["environment"], launch.host_context.ENVIRONMENT)
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            result = {
                "argv": argv,
                "status": "completed",
                "exit_code": 0,
                "error": None,
                "remaining_owned_processes": [],
                "owned_processes": [],
                "received_signals": [],
            }
            with log_path.open("xb") as log:
                try:
                    kwargs["before_spawn"](log)
                except (ValueError, OSError) as error:
                    result.update(status="failed", exit_code=None, error=str(error))
                    return result
            self.started.append(argv)
            return result

        materialization = {
            "kind": "native",
            "files": {name: {"sha256": sha} for name, sha in self.files.items()},
        }
        with (
            patch.object(launch, "_admissions", return_value=self.registry),
            patch.object(launch.host_context, "capture", side_effect=observed),
            patch.object(launch.storage, "inspect_materialized", return_value=materialization),
            patch.object(launch, "supervise", side_effect=backend),
        ):
            return launch.launch_native(
                self.engine_raw,
                self.integration_raw,
                self.stage,
                self.packet,
                self.output,
                self.evidence,
            )

    def test_complete_invented_packet_reaches_only_mocked_native_backend(self):
        result = self.invoke()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(self.started), 1)
        self.assertEqual(list(self.output.iterdir()), [])
        for key in launch.AUTHORITY:
            self.assertIs(result[key], False)

    def test_foreign_owner_does_not_reach_backend(self):
        self.integration["owner_pid"] += 1
        self.reseal()
        with self.assertRaisesRegex(ValueError, "owner/bindings"):
            self.invoke()
        self.assertEqual(self.started, [])
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_rehashed_wrong_reader_and_plan_still_refuse(self):
        self.integration["reader_identity"]["protocol"]["source_revision"] = "0" * 40
        self.reseal()
        with self.assertRaisesRegex(ValueError, "integration/reader bytes"):
            self.invoke()
        self.assertEqual(self.started, [])

    def test_changed_plan_cannot_be_accepted_by_rehashing_its_receipt(self):
        data = json.loads(self.blobs["plan.json"])
        data["seed"] += 1
        self.blobs["plan.json"] = wire(data)
        self.engine["plan_sha256"] = launch.storage.digest(self.blobs["plan.json"])
        self.integration["reader_identity"] = launch.journal_reader.identity(
            self.blobs["plan.json"]
        )
        self.reseal()
        with self.assertRaisesRegex(ValueError, "identity"):
            self.invoke()
        self.assertEqual(self.started, [])

    def test_extra_packet_entry_and_private_mode_are_not_adopted(self):
        path = self.packet / "plan.json"
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "private packet"):
            self.invoke()
        path.chmod(0o400)
        self.packet.chmod(0o700)
        (self.packet / "ambient.json").write_bytes(b"invented extra")
        self.packet.chmod(0o500)
        with self.assertRaisesRegex(ValueError, "closed packet"):
            self.invoke()
        self.assertEqual(self.started, [])

    def test_context_expiring_during_last_byte_checks_prevents_start(self):
        first = launch.host_context.stamp(self.context["observed_from"])
        with patch.object(launch, "datetime") as clock:
            clock.now.side_effect = [first + timedelta(seconds=59)] * 5 + [
                first + timedelta(seconds=61)
            ]
            result = self.invoke()
        self.assertEqual(result["status"], "failed")
        self.assertIn("stale or unknown", result["error"])
        self.assertEqual(self.started, [])

    def test_missing_or_changed_staging_bytes_are_refused(self):
        path = self.stage / "runtime/bin/node"
        path.chmod(0o700)
        path.write_bytes(b"changed invented executable")
        path.chmod(0o500)
        with self.assertRaisesRegex(ValueError, "selected staging bytes"):
            self.invoke()
        self.assertEqual(self.started, [])

    def test_executable_change_during_final_capture_is_refused(self):
        path = self.stage / "runtime/bin/node"

        def changed():
            path.chmod(0o700)
            path.write_bytes(b"late invented executable change")
            path.chmod(0o500)

        result = self.invoke(at_last_capture=changed)
        self.assertEqual(result["status"], "failed")
        self.assertIn("selected staging bytes", result["error"])
        self.assertEqual(self.started, [])

    def test_late_packet_byte_change_is_not_a_namespace_only_check(self):
        path = self.packet / "plan.json"

        def changed():
            path.chmod(0o600)
            path.write_bytes(path.read_bytes() + b" ")
            path.chmod(0o400)

        result = self.invoke(at_last_capture=changed)
        self.assertEqual(result["status"], "failed")
        self.assertIn("packet changed", result["error"])
        self.assertEqual(self.started, [])

    def test_late_tool_change_refuses_before_spawn(self):
        def changed():
            self.sandbox.write_bytes(b"late tool change")

        result = self.invoke(at_last_capture=changed)
        self.assertEqual(result["status"], "failed")
        self.assertIn("host mechanism changed", result["error"])
        self.assertEqual(self.started, [])

    def test_late_log_replacement_is_not_accepted_as_bound_log(self):
        def changed():
            path = self.evidence / "launch.log"
            path.unlink()
            path.write_bytes(b"invented replacement")
            path.chmod(0o600)

        result = self.invoke(at_last_capture=changed)
        self.assertEqual(result["status"], "failed")
        self.assertIn("bound log", result["error"])
        self.assertEqual(self.started, [])


@unittest.skipUnless(os.name == "posix", "POSIX invented process controls required")
class NativePrestartProcessTests(unittest.TestCase):
    def case(self, mode, *, cancellation=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            root.chmod(0o700)
            fd = os.open(root / "invented-inheritable", os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            os.set_inheritable(fd, True)
            info = os.fstat(fd)
            (root / "fixture.json").write_bytes(
                wire({"fd": fd, "identity": [info.st_dev, info.st_ino]})
            )
            cancel, done = threading.Event(), threading.Event()
            watcher = None
            unrelated = subprocess.Popen(
                [sys.executable, "-I", "-S", "-c", "import time; time.sleep(30)"],
                start_new_session=True,
            )
            if cancellation:

                def after_ready():
                    while not done.wait(0.01):
                        if (root / "ready").exists():
                            cancel.set()
                            return

                watcher = threading.Thread(target=after_ready, daemon=True)
                watcher.start()
            fixture = launch.ROOT / "tests/lt1_prestart_fixture.py"
            pinned = launch.storage.digest(fixture.read_bytes())
            guard_calls = []
            started_arguments = []
            real_spawn = execution.spawn

            def recorded_spawn(*args, **kwargs):
                started_arguments.append(kwargs)
                return real_spawn(*args, **kwargs)

            def guard(log):
                guard_calls.append(True)
                self.assertEqual(stat.S_IMODE(os.fstat(log.fileno()).st_mode), 0o600)
                self.assertEqual(launch.storage.digest(fixture.read_bytes()), pinned)
                self.assertEqual(os.fstat(log.fileno()).st_ino, (root / "launch.log").stat().st_ino)

            try:
                with (
                    patch.dict(
                        os.environ,
                        {
                            "NODE_OPTIONS": "--require=must-not-run",
                            "DYLD_INSERT_LIBRARIES": "must-not-load",
                        },
                        clear=True,
                    ),
                    patch.object(execution, "spawn", side_effect=recorded_spawn),
                ):
                    result = launch._run(
                        [sys.executable, "-I", "-S", "-B", str(fixture), "parent", mode, str(root)],
                        root / "launch.log",
                        6 if cancellation or mode != "deadline" else 2,
                        0.15,
                        guard,
                        cancel,
                    )
                self.assertEqual(len(guard_calls), 1)
                self.assertEqual(len(started_arguments), 1)
                self.assertEqual(started_arguments[0]["stdin"], subprocess.DEVNULL)
                self.assertIs(started_arguments[0]["close_fds"], True)
                self.assertEqual(started_arguments[0]["env"], launch.host_context.ENVIRONMENT)
                self.assertEqual(
                    result["status"],
                    "completed"
                    if mode == "complete"
                    else "interrupted"
                    if cancellation
                    else "failed",
                )
                self.assertEqual(
                    result["error"],
                    "Cancelled"
                    if cancellation
                    else "WorkerDeadline"
                    if mode == "deadline"
                    else None,
                )
                self.assertEqual(result["remaining_owned_processes"], [])
                self.assertEqual(result["received_signals"], [])
                self.assertIsNone(unrelated.poll())
                child = json.loads((root / "child.json").read_bytes())
                parent = json.loads((root / "parent.json").read_bytes())
                self.assertEqual(child["ppid"], parent["pid"])
                self.assertNotEqual(parent["sid"], os.getsid(0))
                self.assertEqual(child["sid"], parent["sid"])
                owned = {row["pid"]: row for row in result["owned_processes"]}
                self.assertIn(child["pid"], owned)
                self.assertTrue(owned[child["pid"]]["start"])
                current = ProcessTable().one(child["pid"])
                self.assertTrue(current is None or not current["alive"])
                for observed in (parent, child):
                    environment = dict(observed["environment"])
                    if sys.platform == "darwin":
                        runtime_added = environment.pop("__CF_USER_TEXT_ENCODING", None)
                        if runtime_added is not None:
                            self.assertIsNotNone(
                                re.fullmatch(r"0x[0-9a-fA-F]+(?::0x[0-9a-fA-F]+){2}", runtime_added)
                            )
                    self.assertEqual(environment, launch.host_context.ENVIRONMENT)
                    self.assertTrue(observed["stdin_eof"])
                    self.assertFalse(observed["fixture_fd_inherited"])
                    self.assertTrue(observed["isolated"] and observed["no_site"])
                first = (root / "heartbeat").read_bytes()
                time.sleep(0.06)
                self.assertEqual((root / "heartbeat").read_bytes(), first)
                self.assertEqual((root / "finished").exists(), mode == "complete")
                if mode == "failure":
                    self.assertEqual(result["exit_code"], 23)
                for key in launch.AUTHORITY:
                    self.assertIs(result[key], False)
            finally:
                os.close(fd)
                done.set()
                if watcher:
                    watcher.join(timeout=1)
                unrelated.terminate()
                unrelated.wait(timeout=2)

    def test_complete_fixed_python_parent_and_child(self):
        self.case("complete")

    def test_primary_failure_does_not_become_completion(self):
        self.case("failure")

    def test_deadline_reaps_term_ignoring_descendant(self):
        self.case("deadline")

    def test_cancel_reaps_term_ignoring_descendant(self):
        self.case("cancel", cancellation=True)

    def test_prestart_cancel_and_failed_last_guard_spawn_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            cancel = threading.Event()
            cancel.set()
            with patch.object(execution, "spawn") as spawn:
                result = launch._run(
                    ["must-not-start"], root / "never.log", 1, 0, lambda log: None, cancel
                )
                self.assertEqual(result["status"], "interrupted")
                self.assertEqual(result["received_signals"], [])
                self.assertEqual(result["remaining_owned_processes"], [])
                self.assertFalse((root / "never.log").exists())
                spawn.assert_not_called()

            def refused(log):
                raise ValueError("controlled changed source at final guard")

            with patch.object(execution, "spawn") as spawn:
                result = launch._run(["must-not-start"], root / "failed.log", 1, 0, refused, None)
                self.assertEqual(result["status"], "failed")
                self.assertIn("changed source", result["error"])
                self.assertEqual(result["remaining_owned_processes"], [])
                spawn.assert_not_called()

    def test_cancellation_at_last_guard_and_legacy_default_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            cancel = threading.Event()
            with patch.object(execution, "spawn") as spawn:
                result = launch._run(
                    ["must-not-start"], root / "cancel.log", 1, 0, lambda log: cancel.set(), cancel
                )
                self.assertEqual(result["status"], "interrupted")
                spawn.assert_not_called()
            with patch.object(
                execution, "spawn", side_effect=OSError("controlled no worker")
            ) as spawn:
                result = execution.supervise(
                    ["fixed-legacy"], root / "legacy.log", timeout=1, cancel=cancel
                )
                self.assertEqual(result["status"], "failed")
                spawn.assert_called_once()
                self.assertNotIn("stdin", spawn.call_args.kwargs)
                self.assertNotIn("close_fds", spawn.call_args.kwargs)


@unittest.skipUnless(os.name == "posix", "POSIX task-local supervisor controls required")
class NativeSupervisorTests(unittest.TestCase):
    def test_views_keep_canonical_code_defaults_and_only_isolate_spawn(self):
        base = execution.supervise
        before = dict(base.__globals__)
        first_spawn, second_spawn = lambda *a, **k: None, lambda *a, **k: None
        first = supervisor._supervisor_view(first_spawn)
        second = supervisor._supervisor_view(second_spawn)
        for view, spawn in ((first, first_spawn), (second, second_spawn)):
            self.assertIs(view.__code__, base.__code__)
            self.assertIs(view.__defaults__, base.__defaults__)
            self.assertIs(view.__closure__, base.__closure__)
            self.assertEqual(view.__kwdefaults__, base.__kwdefaults__)
            self.assertIsNot(view.__kwdefaults__, base.__kwdefaults__)
            self.assertEqual(view.__globals__.keys(), before.keys())
            self.assertIs(view.__globals__["spawn"], spawn)
            for name in before.keys() - {"spawn"}:
                self.assertIs(view.__globals__[name], before[name])
        self.assertIsNot(first.__globals__, second.__globals__)
        self.assertEqual(execution.supervise.__globals__.keys(), before.keys())
        for name in before:
            self.assertIs(execution.supervise.__globals__[name], before[name])

    def test_two_views_keep_spawn_and_signal_observations_separate(self):
        original_spawn = execution.spawn
        signals = {signum: signal.getsignal(signum) for signum in execution.handled_signals()}
        called = []

        def recorder(label):
            def spawn(*args, **kwargs):
                called.append(label)
                raise OSError(label)

            return spawn

        first = supervisor._supervisor_view(recorder("first"))
        second = supervisor._supervisor_view(recorder("second"))
        with tempfile.TemporaryDirectory() as folder:
            for index, (view, label) in enumerate(
                ((first, "first"), (second, "second"), (first, "first"))
            ):
                result = view(["never-start"], Path(folder) / str(index), timeout=1)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["error"], "OSError: " + label)
                self.assertEqual(result["received_signals"], [])
                self.assertEqual(result["remaining_owned_processes"], [])
                self.assertEqual({s: signal.getsignal(s) for s in signals}, signals)
        self.assertEqual(called, ["first", "second", "first"])
        self.assertIs(execution.spawn, original_spawn)

    def test_cancel_does_not_mask_ordinary_guard_or_spawn_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            for index, kind in enumerate((ValueError, OSError)):
                cancel = threading.Event()

                def failed_guard(log):
                    cancel.set()
                    raise kind("ordinary guard failure")

                with patch.object(execution, "spawn") as spawn:
                    result = launch._run(
                        ["never-start"], Path(folder) / str(index), 1, 0, failed_guard, cancel
                    )
                    spawn.assert_not_called()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["error"], kind.__name__ + ": ordinary guard failure")
            cancel = threading.Event()

            def failed_spawn(*args, **kwargs):
                cancel.set()
                raise OSError("ordinary spawn failure")

            with patch.object(execution, "spawn", side_effect=failed_spawn):
                result = launch._run(
                    ["never-start"], Path(folder) / "spawn", 1, 0, lambda log: None, cancel
                )
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"], "OSError: ordinary spawn failure")

    def test_replaced_canonical_function_is_refused_before_log_or_spawn(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "never.log"
            with (
                patch.object(execution, "supervise", lambda *a, **k: None),
                patch.object(execution, "spawn") as spawn,
            ):
                with self.assertRaisesRegex(ValueError, "provenance"):
                    launch._run(["never-start"], path, 1, 0, lambda log: None, None)
                spawn.assert_not_called()
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
