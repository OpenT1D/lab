"""Direct same-owned-PID exec and actual sockets; invented tooling Node only."""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.lt1_diagnostic import entry_transport as transport
from experiments.lt1_diagnostic import reader

NODE = shutil.which("node")
ROOT = reader.ROOT


def acknowledge(raw):
    parts = raw.split(b"\n")
    if len(parts) != 3 or parts[0] != b"OPENT1D-LT1-ENTRY-1" or parts[2]:
        raise ValueError("invented frame EOF")
    value = reader.decode(parts[1])
    if value["kind"] != "invented" or value["attempt"] != "owned-invented-entry":
        raise ValueError("invented binding")
    result = {
        "schema": "opent1d.lt1-entry-ack/1",
        "kind": "invented",
        "frame_sha256": reader.digest(raw),
        "grant_sha256": value["grant_sha256"],
        "attempt": value["attempt"],
        "nonce_sha256": value["nonce_sha256"],
    }
    return b"OPENT1D-LT1-ACK-1\n" + json.dumps(result, separators=(",", ":")).encode() + b"\n"


@unittest.skipUnless(os.name == "posix" and NODE, "POSIX tooling Node required")
class OwnedEntryTransportTests(unittest.TestCase):
    def invoke(self, folder, behavior="complete", *, extra_fd=None, **options):
        values = {
            "expected_identity": transport.source_identity(),
            "verify_frame": acknowledge,
            "timeout": 2,
            "handoff_timeout": 0.6,
            "grace": 0.1,
        }
        values.update(options)
        argv = [NODE, str(ROOT / "tests/lt1_owned_entry_fixture.mjs"), behavior, str(folder)]
        if extra_fd is not None:
            argv.append(str(extra_fd))
        return transport.supervise_entry(
            argv,
            folder / "process.log",
            **values,
        )

    def assert_unqualified(self, result):
        for key in transport.AUTHORITY:
            self.assertIs(result[key], False, key)
        self.assertFalse(result["endpoint_close_verified"])
        self.assertEqual(result["outer"]["remaining_owned_processes"], [])

    def test_complete_direct_exec_has_same_owned_pid_clean_stdio_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            folder.chmod(0o700)
            with patch.dict(os.environ, {"NODE_OPTIONS": "--invalid-inherited-option"}):
                result = self.invoke(folder)
            self.assertTrue(result["local_exchange_and_process_complete"], result)
            self.assert_unqualified(result)
            startup = json.loads((folder / "startup.json").read_bytes())
            self.assertEqual(startup["ppid"], os.getpid())
            self.assertEqual(startup["stdin_bytes"], 0)
            self.assertEqual(
                {k: startup["environment"][k] for k in transport.owner.ENVIRONMENT},
                transport.owner.ENVIRONMENT,
            )
            # Observe host runtime initialization separately; never strip it to
            # make the existing native observer accept an unqualified process.
            extras = set(startup["environment"]) - set(transport.owner.ENVIRONMENT)
            self.assertLessEqual(
                extras, {"__CF_USER_TEXT_ENCODING"} if sys.platform == "darwin" else set()
            )
            self.assertEqual(startup["exec_argv"], [])
            self.assertIn(startup["pid"], [r["pid"] for r in result["outer"]["owned_processes"]])
            child = json.loads((folder / "entry.json").read_bytes())
            self.assertEqual(child["status"], "acknowledged")
            self.assertEqual(base64.b64decode(child["frame_raw"]), result["exchange"]["frame_raw"])
            self.assertEqual(base64.b64decode(child["ack_raw"]), result["exchange"]["ack_sent_raw"])
            log = (folder / "process.log").read_bytes()
            self.assertIn(b"owned-entry-stdout", log)
            self.assertIn(b"owned-entry-stderr", log)
            self.assertNotIn(b"OPENT1D-LT1-ENTRY", log)

    def test_wrong_frame_and_oversize_keep_bounded_prefix_and_never_complete(self):
        for mode in ("bad-frame", "oversize", "closed-gate"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                result = self.invoke(Path(temp).resolve(), mode)
                self.assertFalse(result["local_exchange_and_process_complete"])
                self.assertEqual(result["exchange"]["status"], "failed")
                self.assertLessEqual(len(result["exchange"]["frame_raw"]), transport.FRAME_LIMIT)
                self.assertFalse(result["exchange"]["ack_sent"])
                self.assert_unqualified(result)

    def test_frame_without_eof_times_out_before_verifier_and_owner_cleans(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.invoke(Path(temp).resolve(), "no-eof")
            self.assertEqual(result["exchange"]["status"], "timeout")
            self.assertFalse(result["exchange"]["frame_eof"])
            self.assertFalse(result["exchange"]["verifier_started"])
            self.assertTrue(result["exchange"]["frame_raw"])
            self.assertEqual(result["outer"]["error"], "WorkerDeadline")
            self.assert_unqualified(result)

    def test_late_verifier_cannot_send_ack_after_deadline(self):
        def slow(raw):
            time.sleep(0.1)
            return acknowledge(raw)

        with tempfile.TemporaryDirectory() as temp:
            result = self.invoke(Path(temp).resolve(), verify_frame=slow, handoff_timeout=0.08)
            self.assertFalse(result["local_exchange_and_process_complete"])
            self.assertFalse(result["exchange"]["ack_sent"])
            self.assertEqual(result["exchange"]["status"], "timeout")
            self.assert_unqualified(result)

    def test_nonpreemptible_verifier_is_reported_unfinished_and_released_by_fixture(self):
        release, returned = threading.Event(), threading.Event()

        def block(raw):
            release.wait(5)
            returned.set()
            return acknowledge(raw)

        try:
            with tempfile.TemporaryDirectory() as temp:
                result = self.invoke(Path(temp).resolve(), verify_frame=block)
                self.assertEqual(result["exchange"]["status"], "unfinished")
                self.assertFalse(result["exchange"]["thread_finished"])
                self.assertFalse(result["local_exchange_and_process_complete"])
                self.assert_unqualified(result)
        finally:
            release.set()
            self.assertTrue(returned.wait(1))

    def test_cancel_before_spawn_opens_no_log_or_child(self):
        stopped = threading.Event()
        stopped.set()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            with patch.object(
                transport.owner.canonical, "spawn", side_effect=AssertionError("spawn")
            ):
                result = self.invoke(folder, cancel=stopped)
            self.assertEqual(result["outer"]["error"], "Cancelled")
            self.assertFalse((folder / "process.log").exists())
            self.assertEqual(result["exchange"]["status"], "not-started")

    def test_last_guard_cancellation_is_interrupted_without_spawn(self):
        stopped = threading.Event()
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(
                transport.owner.canonical, "spawn", side_effect=AssertionError("spawn")
            ):
                result = self.invoke(
                    Path(temp).resolve(), cancel=stopped, before_spawn=lambda _log: stopped.set()
                )
            self.assertEqual(result["outer"]["status"], "interrupted")
            self.assertEqual(result["outer"]["error"], "Cancelled")

    def test_second_socket_allocation_failure_releases_first_pair(self):
        pair = socket.socketpair()
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(
                transport.socket, "socketpair", side_effect=[pair, OSError("invented")]
            ):
                with self.assertRaises(OSError):
                    self.invoke(Path(temp).resolve())
        self.assertEqual([s.fileno() for s in pair], [-1, -1])

    def test_thread_start_failure_precedes_process_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(threading.Thread, "start", side_effect=RuntimeError("invented")):
                with patch.object(
                    transport.owner.canonical, "spawn", side_effect=AssertionError("spawn")
                ):
                    with self.assertRaisesRegex(RuntimeError, "invented"):
                        self.invoke(Path(temp).resolve())

    def test_bad_expected_source_refuses_before_resource_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(transport.socket, "socketpair", side_effect=AssertionError("socket")):
                with self.assertRaisesRegex(ValueError, "expected transport source"):
                    self.invoke(Path(temp).resolve(), expected_identity={})

    def test_guard_failure_retains_log_and_primary_without_spawn(self):
        def reject(_log):
            raise ValueError("invented guard")

        with tempfile.TemporaryDirectory() as temp:
            with patch.object(
                transport.owner.canonical, "spawn", side_effect=AssertionError("spawn")
            ):
                result = self.invoke(Path(temp).resolve(), before_spawn=reject)
            self.assertIn("invented guard", result["outer"]["error"])
            self.assertFalse(result["local_exchange_and_process_complete"])

    def test_ack_limit_refuses_verifier_output(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.invoke(Path(temp).resolve(), verify_frame=lambda _raw: b"x" * 1025)
            self.assertEqual(result["exchange"]["status"], "failed")
            self.assertEqual(result["exchange"]["ack_sent_raw"], b"")
            self.assert_unqualified(result)

    def test_unrelated_inheritable_descriptor_is_not_forwarded(self):
        import fcntl

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            low = os.open(folder / "marker", os.O_CREAT | os.O_RDWR, 0o600)
            high = fcntl.fcntl(low, fcntl.F_DUPFD, 100)
            try:
                os.set_inheritable(high, True)
                token = [str(os.fstat(high).st_dev), str(os.fstat(high).st_ino)]
                result = self.invoke(folder, extra_fd=high)
                self.assertTrue(result["local_exchange_and_process_complete"])
                startup = json.loads((folder / "startup.json").read_bytes())
                self.assertNotEqual(startup["extra_descriptor"], token)
            finally:
                os.close(high)
                os.close(low)

    def test_owner_deadline_and_cancel_after_ack_preserve_unrelated_process(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp).resolve()
                stopped, done = threading.Event(), threading.Event()

                def watch():
                    while not done.wait(0.01):
                        if (folder / "ready.json").is_file():
                            stopped.set()
                            return

                watcher = threading.Thread(target=watch) if cancel else None
                unrelated = subprocess.Popen(
                    [NODE, "-e", "setInterval(()=>{},1000)"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if watcher:
                    watcher.start()
                try:
                    result = self.invoke(folder, "hang", cancel=stopped)
                    self.assertIsNone(unrelated.poll())
                finally:
                    done.set()
                    if watcher:
                        watcher.join(timeout=1)
                    unrelated.terminate()
                    unrelated.wait(timeout=5)
                self.assertEqual(result["exchange"]["status"], "ack-sent")
                self.assertTrue((folder / "ready.json").is_file())
                self.assertEqual(
                    result["outer"]["error"], "Cancelled" if cancel else "WorkerDeadline"
                )
                self.assertFalse(result["local_exchange_and_process_complete"])
                self.assert_unqualified(result)

    def test_source_receipt_owns_its_identity_instead_of_aliasing_caller_input(self):
        pins = transport.source_identity()
        with tempfile.TemporaryDirectory() as temp:
            result = self.invoke(Path(temp).resolve(), expected_identity=pins)
        self.assertIsNot(result["source_identity"], pins)
        pins.clear()
        self.assertTrue(result["source_identity"]["implementation"])

    def test_post_spawn_close_error_still_hands_process_to_canonical_owner(self):
        actual_pair, actual_close = socket.socketpair, socket.socket.close
        pairs, injected = [], False

        def allocate():
            pair = actual_pair()
            pairs.append(pair)
            return pair

        def close(stream):
            nonlocal injected
            if len(pairs) == 2 and stream is pairs[1][1] and not injected:
                injected = True
                actual_close(stream)
                raise OSError("invented post-Popen close failure")
            return actual_close(stream)

        with tempfile.TemporaryDirectory() as temp:
            with (
                patch.object(socket, "socketpair", side_effect=allocate),
                patch.object(socket.socket, "close", close),
            ):
                result = self.invoke(Path(temp).resolve())
        self.assertTrue(injected)
        self.assertTrue(result["outer"]["owned_processes"])
        self.assertEqual(result["outer"]["remaining_owned_processes"], [])
        self.assertEqual(result["resource_close_errors"], ["OSError"])
        self.assertFalse(result["local_exchange_and_process_complete"])

    def test_partial_ack_failure_retains_confirmed_send_prefix_separately(self):
        actual_send, calls = socket.socket.send, 0

        def send(stream, data, *args):
            nonlocal calls
            calls += 1
            if calls == 1:
                return actual_send(stream, data[:17], *args)
            raise BrokenPipeError("invented ACK write failure")

        with tempfile.TemporaryDirectory() as temp:
            with patch.object(socket.socket, "send", send):
                result = self.invoke(Path(temp).resolve())
        exchange = result["exchange"]
        self.assertEqual(exchange["reason"], "BrokenPipeError")
        self.assertEqual(exchange["ack_sent_raw"], exchange["ack_raw"][:17])
        self.assertGreater(len(exchange["ack_raw"]), 17)
        self.assertFalse(exchange["ack_eof_sent"])
        self.assertFalse(result["local_exchange_and_process_complete"])
        self.assert_unqualified(result)
