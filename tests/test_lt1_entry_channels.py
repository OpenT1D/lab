"""Actual tooling-Node process channels; no selected native runtime or LT1."""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from experiments.lt1_diagnostic import reader
from experiments.shared_services.execution import supervise

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@unittest.skipUnless(os.name == "posix" and NODE, "POSIX tooling Node required")
class EntryChannelProcessTests(unittest.TestCase):
    def descriptor_case(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            folder.chmod(0o700)
            left, peer = socket.socketpair()
            other, other_peer = socket.socketpair()
            file_fd = os.open(folder / "ordinary", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                ack = left.fileno()
                frame = (
                    ack
                    if mode == "same-socket"
                    else file_fd
                    if mode == "regular-file"
                    else other.fileno()
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-B",
                        str(ROOT / "tests/lt1_entry_descriptor_exec.py"),
                        NODE,
                        str(ROOT / "tests/lt1_entry_channels_fixture.mjs"),
                        str(folder),
                        mode,
                        str(ack),
                        str(frame),
                    ],
                    pass_fds=tuple({ack, frame}),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads((folder / "descriptor.json").read_bytes())["descriptors_retained"],
                    True,
                )
            finally:
                for stream in (left, peer, other, other_peer):
                    stream.close()
                os.close(file_fd)

    def case(self, behavior, *, cancel=False):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp).resolve()
            folder.chmod(0o700)
            stopped, done = threading.Event(), threading.Event()

            def watch():
                while not done.wait(0.01):
                    if (folder / "ready.json").is_file():
                        stopped.set()
                        return

            thread = threading.Thread(target=watch) if cancel else None
            if thread:
                thread.start()
            unrelated = subprocess.Popen(
                [NODE, "-e", "setInterval(()=>{},1000)"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                outer = supervise(
                    [
                        NODE,
                        str(ROOT / "tests/lt1_entry_channels_fixture.mjs"),
                        "parent",
                        behavior,
                        str(folder),
                    ],
                    folder / "process.log",
                    timeout=4 if behavior == "hang" else 10,
                    grace=0.2,
                    cancel=stopped,
                    environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                )
                self.assertIsNone(unrelated.poll(), "unrelated process must survive")
            finally:
                done.set()
                if thread:
                    thread.join(timeout=1)
                unrelated.terminate()
                unrelated.wait(timeout=5)
            self.assertEqual(outer["remaining_owned_processes"], [])
            self.assertEqual(outer["received_signals"], [])
            if behavior == "closed-gate":
                self.assertEqual(outer["status"], "completed")
                self.assertTrue(json.loads((folder / "gate.json").read_bytes())["refused"])
                self.assertFalse((folder / "entry.json").exists())
                return
            if behavior == "callback-error":
                self.assertEqual(outer["status"], "completed")
                self.assertTrue(
                    json.loads((folder / "callback.json").read_bytes())["primary_preserved"]
                )
                return
            result = json.loads((folder / "entry.json").read_bytes())
            for key in (
                "native_host_qualified",
                "native_acceptance",
                "setup_admitted",
                "native_execution_authorized",
                "effective_erasure_verified",
                "phase_verified",
                "endpoint_identity_verified",
                "endpoint_close_verified",
                "new_authority_granted",
            ):
                self.assertIs(result[key], False, key)
            self.assertEqual(result["kind"], "invented")
            frame = base64.b64decode(result["frame_raw"], validate=True)
            ack = base64.b64decode(result["ack_raw"], validate=True)
            self.assertEqual(result["frame_sha256"], reader.digest(frame))
            self.assertEqual(result["ack_sha256"], reader.digest(ack))
            if behavior == "hang":
                self.assertEqual(result["status"], "acknowledged")
                self.assertTrue((folder / "ready.json").is_file())
                self.assertEqual(outer["error"], "Cancelled" if cancel else "WorkerDeadline")
                self.assertEqual(outer["status"], "interrupted" if cancel else "failed")
                self.assertFalse((folder / "parent.json").exists())
                child = result["fixture_process"]
                owned = {item["pid"]: item for item in outer["owned_processes"]}
                self.assertIn(child["pid"], owned)
                self.assertEqual(owned[child["pid"]]["ppid"], child["ppid"])
            else:
                parent = json.loads((folder / "parent.json").read_bytes())
                self.assertTrue(parent["frame_eof"])
                self.assertEqual(parent["frame_sha256"], result["frame_sha256"])
                self.assertEqual(parent["stdout"], "tooling-entry-stdout\n")
                self.assertEqual(parent["stderr"], "tooling-entry-stderr\n")
                expected = {"complete": "acknowledged", "no-eof": "timeout", "cancel": "cancelled"}
                self.assertEqual(result["status"], expected.get(behavior, "failed"))
                self.assertEqual(
                    outer["status"], "completed" if behavior == "complete" else "failed"
                )

    def test_actual_two_channels_fragmented_ack_and_stdio_separation(self):
        self.case("complete")

    def test_current_gate_refuses_before_missing_descriptor_intake(self):
        self.case("closed-gate")

    def test_wrong_ack_does_not_complete(self):
        self.case("wrong-ack")

    def test_ack_without_eof_times_out(self):
        self.case("no-eof")

    def test_closed_ack_channel_does_not_complete(self):
        self.case("close")

    def test_entry_cancellation_retains_frame_and_ack(self):
        self.case("cancel")

    def test_owner_deadline_after_ack_cleans_descendants(self):
        self.case("hang")

    def test_owner_cancel_after_ack_cleans_descendants(self):
        self.case("hang", cancel=True)

    def test_same_socket_alias_refuses_without_adopting_descriptors(self):
        self.descriptor_case("same-socket")

    def test_regular_file_refuses_without_adopting_descriptors(self):
        self.descriptor_case("regular-file")

    def test_stdio_socket_alias_refuses_without_adopting_descriptors(self):
        self.descriptor_case("stdio-alias")

    def test_callback_close_error_stays_owned_and_preserves_primary_error(self):
        self.case("callback-error")
