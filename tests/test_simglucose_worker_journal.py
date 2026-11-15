"""Invented durable journal boundaries, not native or OS authentication."""

import copy
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.simglucose_audit import worker_fixture as worker
from experiments.simglucose_audit import worker_journal as journal
from experiments.simglucose_audit.contract import decode, digest, encode


class SimglucoseWorkerJournalTests(unittest.TestCase):
    def setUp(self):
        base = os.environ.get("OT062_JOURNAL_FIXTURE_PROOF_ROOT", "/private/tmp")
        self.root = Path(tempfile.mkdtemp(prefix="journal-test-", dir=base)).resolve()
        # Retain these invented fixtures: no removal/erasure operation is tested.

    def raw(self, mode="complete"):
        return encode(worker.default_request() | {"mode": mode})

    def run_attempt(self, mode="complete"):
        raw = self.raw(mode)
        receipt = journal.run_journal_fixture(raw, self.root / "attempt")
        files = journal.read_journal(self.root / "attempt")
        return raw, receipt, files

    def inspect(self, files, raw, pin=None):
        return journal.inspect_journal(
            files, digest(files["manifest.json"]) if pin is None else pin, digest(raw)
        )

    def rehash_manifest(self, files):
        files = copy.deepcopy(files)
        manifest = decode(files["manifest.json"])
        manifest["files"] = {
            name: {"bytes": len(raw), "sha256": digest(raw)}
            for name, raw in files.items()
            if name != "manifest.json"
        }
        files["manifest.json"] = encode(manifest)
        return files

    def events(self, files):
        return [decode(line) for line in files["events.jsonl"].splitlines()]

    def rechain(self, rows):
        previous, lines = None, []
        for sequence, row in enumerate(rows):
            row = row | {"sequence": sequence, "previous_sha256": previous}
            raw = encode(row) + b"\n"
            lines.append(raw)
            previous = digest(raw)
        return b"".join(lines)

    def test_complete_observed_lifecycle_raw_frames_and_external_pins(self):
        raw, receipt, files = self.run_attempt()
        checked = self.inspect(files, raw, receipt["manifest_sha256"])
        self.assertEqual(checked["status"], "completed")
        self.assertTrue(checked["completion_marker"])
        rows = self.events(files)
        launch = next(row["data"] for row in rows if row["event"] == "launch")
        self.assertEqual(launch["parent_pid"], os.getpid())
        self.assertNotEqual(launch["child_pid"], os.getpid())
        joined = next(row["data"] for row in rows if row["event"] == "io-joined")
        self.assertEqual(
            joined,
            {"reader_joined": True, "writer_joined": True, "returncode": 0, "cleanup_error": None},
        )
        self.assertEqual(files["completed.json"], files["completion-intent.json"])
        self.assertEqual(len([name for name in files if name.startswith("frame-")]), 3)
        self.assertFalse(checked["host_or_process_qualified"])
        self.assertFalse(checked["authority"]["native_execution_authorized"])
        with self.assertRaisesRegex(ValueError, "manifest-pin"):
            self.inspect(files, raw, "0" * 64)
        with self.assertRaises(ValueError):
            journal.inspect_journal(files, receipt["manifest_sha256"], "0" * 64)

    def test_cancel_deadline_and_full_science_finished_block_never_mark_complete(self):
        for mode in ("cancel", "deadline", "finish-block", "deny-network"):
            with self.subTest(mode=mode):
                destination = self.root / mode
                raw = self.raw(mode)
                receipt = journal.run_journal_fixture(raw, destination)
                files = journal.read_journal(destination)
                checked = self.inspect(files, raw, receipt["manifest_sha256"])
                self.assertNotEqual(checked["status"], "completed")
                self.assertNotIn("completed.json", files)
                if mode == "finish-block":
                    report = decode(files["report.json"])
                    self.assertEqual(report["fixture_report"]["status"], "completed")
                    self.assertEqual(len(report["fixture_report"]["rows"]), 10)
                    self.assertEqual(report["status"], "incomplete")

    def test_missing_atomic_marker_and_pinned_crash_torn_prefix_remain_incomplete(self):
        raw, _receipt, files = self.run_attempt()
        missing = {name: value for name, value in files.items() if name != "completed.json"}
        self.assertEqual(self.inspect(missing, raw)["status"], "incomplete")
        rows = self.events(files)
        prefix = {"request.bin": raw, "events.jsonl": encode(rows[0]) + b"\n" + b'{"sequence":'}
        checked = journal.inspect_journal_prefix(
            prefix, digest(prefix["events.jsonl"]), digest(raw)
        )
        self.assertEqual(checked["status"], "incomplete")
        self.assertTrue(checked["torn_tail"])
        prefix["completed.json"] = files["completed.json"]
        self.assertEqual(
            journal.inspect_journal_prefix(prefix, digest(prefix["events.jsonl"]), digest(raw))[
                "status"
            ],
            "incomplete",
        )

    def test_rehashed_source_input_rawframe_and_outer_promotions_rejected(self):
        raw, _receipt, files = self.run_attempt()
        for name in ("request.bin", "frame-1.bin", "outer.json"):
            changed = copy.deepcopy(files)
            if name == "request.bin":
                changed[name] = b" " + raw
            elif name == "frame-1.bin":
                frame = decode(changed[name])
                frame["fixture"]["rows"][0]["basal_u_min"] = 1.2
                changed[name] = encode(frame) + b"\n"
            else:
                outer = decode(changed[name])
                outer["authority"]["setup_authorized"] = True
                changed[name] = encode(outer)
            changed = self.rehash_manifest(changed)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.inspect(changed, raw)
        source = decode(files["manifest.json"])
        source["source_identity"] = {}
        changed = files | {"manifest.json": encode(source)}
        with self.assertRaisesRegex(ValueError, "binding"):
            self.inspect(changed, raw)

    def test_rehashed_sequence_reorder_force_after_exit_and_early_marker_fail(self):
        raw, _receipt, files = self.run_attempt()
        rows = self.events(files)
        mutations = []
        changed = copy.deepcopy(rows)
        changed[-2], changed[-1] = changed[-1], changed[-2]
        mutations.append(changed)
        changed = copy.deepcopy(rows)
        stop_index = next(i for i, row in enumerate(changed) if row["event"] == "stop-poll")
        changed.insert(stop_index + 1, changed[stop_index] | {"event": "force-request", "data": {}})
        mutations.append(changed)
        changed = copy.deepcopy(rows)
        joined = next(row for row in changed if row["event"] == "io-joined")
        joined["data"]["writer_joined"] = False
        mutations.append(changed)
        for changed in mutations:
            candidate = self.rehash_manifest(files | {"events.jsonl": self.rechain(changed)})
            with self.assertRaises(ValueError):
                self.inspect(candidate, raw)
        partial_raw = self.raw("finish-block")
        receipt = journal.run_journal_fixture(partial_raw, self.root / "partial")
        partial = journal.read_journal(self.root / "partial")
        self.assertIsNotNone(receipt["manifest_sha256"])
        partial["completed.json"] = files["completed.json"]
        partial["completion-intent.json"] = files["completion-intent.json"]
        with self.assertRaises(ValueError):
            self.inspect(self.rehash_manifest(partial), partial_raw)

    def test_fresh_destination_and_no_symlink_escape_or_reuse(self):
        raw, _receipt, before = self.run_attempt()
        with self.assertRaises(FileExistsError):
            journal.run_journal_fixture(raw, self.root / "attempt")
        self.assertEqual(journal.read_journal(self.root / "attempt"), before)
        (self.root / "alias").symlink_to(self.root / "attempt", target_is_directory=True)
        with self.assertRaises(OSError):
            journal.run_journal_fixture(raw, self.root / "alias" / "escaped")
        with self.assertRaises(OSError):
            journal.run_journal_fixture(raw, self.root / "alias")
        with self.assertRaises(ValueError):
            journal.run_journal_fixture(raw, self.root / ".." / "escaped")
        self.assertFalse((self.root / "attempt" / "escaped").exists())
        with (
            patch.object(journal, "_directory", side_effect=AssertionError("destination touched")),
            self.assertRaises(ValueError),
        ):
            journal.run_journal_fixture(b"{}", self.root / "never")

    def test_loader_rejects_unknown_names_and_symlink_files(self):
        fake = self.root / "fake"
        fake.mkdir(mode=0o700)
        (fake / "request.bin").symlink_to(self.root / "invented-target")
        with self.assertRaises(OSError):
            journal.read_journal(fake)
        with self.assertRaises(ValueError):
            journal.inspect_journal_prefix(
                {"request.bin": self.raw(), "events.jsonl": b"", "../escape": b""},
                "0" * 64,
                "0" * 64,
            )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation unavailable")
    def test_loader_rejects_owned_fifo_without_blocking_before_fstat(self):
        fake = self.root / "fifo"
        fake.mkdir(mode=0o700)
        os.mkfifo(fake / "request.bin", 0o600)
        start = time.monotonic()
        with self.assertRaisesRegex(ValueError, "regular-file"):
            journal.read_journal(fake)
        self.assertLess(time.monotonic() - start, 0.5)

    def test_sink_raw_record_failure_still_stops_child_and_joins_both_threads(self):
        original, processes = journal._JournalSink._record, []
        spawn = worker.platform_process.spawn

        def failed_record(sink, event, data):
            if event == "raw-frame":
                raise OSError("invented record failure")
            return original(sink, event, data)

        def record_spawn(*args, **kwargs):
            process = spawn(*args, **kwargs)
            processes.append(process)
            return process

        with (
            patch.object(journal._JournalSink, "_record", new=failed_record),
            patch.object(worker.platform_process, "spawn", side_effect=record_spawn),
        ):
            raw, receipt, files = self.run_attempt()
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["manifest_sha256"])
        self.assertEqual(receipt["journal_error"], "journal-write-failed")
        self.assertNotIn("completed.json", files)
        self.assertIsNotNone(processes[0].poll())
        self.assertFalse(
            any(thread.name.startswith("simglucose-fixture-") for thread in threading.enumerate())
        )
        self.assertEqual(
            journal.inspect_journal_prefix(files, digest(files["events.jsonl"]), digest(raw))[
                "status"
            ],
            "incomplete",
        )

    def test_post_link_fsync_failure_never_issues_success_even_if_error_record_fails(self):
        real_link, real_fsync, real_file = (
            journal.os.link,
            journal.os.fsync,
            journal._JournalSink._file,
        )
        for error_record_fails in (False, True):
            linked = [False]

            def link(*args, **kwargs):
                real_link(*args, **kwargs)
                linked[0] = True

            def fsync(fd):
                if linked[0]:
                    raise OSError("invented post-link fsync failure")
                real_fsync(fd)

            def file(sink, name, raw):
                if name == "finalization-error.json" and error_record_fails:
                    raise OSError("invented error record failure")
                return real_file(sink, name, raw)

            destination = self.root / str(error_record_fails)
            raw = self.raw()
            with (
                patch.object(journal.os, "link", side_effect=link),
                patch.object(journal.os, "fsync", side_effect=fsync),
                patch.object(journal._JournalSink, "_file", new=file),
            ):
                receipt = journal.run_journal_fixture(raw, destination)
            self.assertTrue(linked[0])
            self.assertEqual(receipt["status"], "failed")
            self.assertIsNone(receipt["manifest_sha256"])
            files = journal.read_journal(destination)
            self.assertIn("completed.json", files)  # Existence alone is no issued success pin.
            self.assertEqual(
                journal.inspect_journal_prefix(files, digest(files["events.jsonl"]), digest(raw))[
                    "status"
                ],
                "incomplete",
            )
            if not error_record_fails:
                with self.assertRaisesRegex(ValueError, "finalization-error"):
                    self.inspect(files, raw)

    def test_header_failure_refuses_spawn_and_source_failure_closes_directory(self):
        write = journal._write

        def fail_header(fd, raw):
            if b'"event":"header"' in raw:
                raise OSError("invented header failure")
            return write(fd, raw)

        with (
            patch.object(journal, "_write", side_effect=fail_header),
            patch.object(
                worker.platform_process, "spawn", side_effect=AssertionError("spawn without header")
            ),
        ):
            receipt = journal.run_journal_fixture(self.raw(), self.root / "header")
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["manifest_sha256"])
        self.assertIsNone(receipt["worker_report"])
        opened = []
        directory = journal._directory

        def capture(*args, **kwargs):
            fd = directory(*args, **kwargs)
            opened.append(fd)
            return fd

        with (
            patch.object(journal, "_directory", side_effect=capture),
            patch.object(journal, "_identity", side_effect=OSError("invented source read failure")),
            self.assertRaises(OSError),
        ):
            journal.run_journal_fixture(self.raw(), self.root / "source")
        self.assertEqual(len(opened), 1)
        with self.assertRaises(OSError):
            os.fstat(opened[0])

    def test_event_close_failure_is_sticky_and_preserves_worker_primary(self):
        close, finish = journal.os.close, journal._JournalSink._finish_events
        target, failed = [None], [False]

        def finish_events(sink):
            target[0] = sink.events_fd
            return finish(sink)

        def close_once(fd):
            close(fd)
            if fd == target[0] and not failed[0]:
                failed[0] = True
                raise OSError("invented event close failure")

        request = worker.default_request()
        request["config"].update(fault="reset-error", close_error=True)
        with (
            patch.object(journal._JournalSink, "_finish_events", new=finish_events),
            patch.object(journal.os, "close", side_effect=close_once),
        ):
            receipt = journal.run_journal_fixture(encode(request), self.root / "close")
        self.assertTrue(failed[0])
        self.assertIsNone(receipt["manifest_sha256"])
        self.assertEqual(receipt["journal_error"], "journal-close-failed")
        fixture = receipt["worker_report"]["fixture_report"]
        self.assertEqual(fixture["primary_error"], "scripted-reset-error")
        self.assertEqual(fixture["diagnostic_error"], "scripted-close-error")
        self.assertNotIn("completed.json", journal.read_journal(self.root / "close"))

    def test_final_directory_close_failure_invalidates_success_before_return(self):
        close, close_sink = journal.os.close, journal._JournalSink._close
        target, failed = [None], [False]

        def final_close(sink):
            target[0] = sink.fd
            return close_sink(sink)

        def close_once(fd):
            close(fd)
            if fd == target[0] and not failed[0]:
                failed[0] = True
                raise OSError("invented final directory close failure")

        with (
            patch.object(journal._JournalSink, "_close", new=final_close),
            patch.object(journal.os, "close", side_effect=close_once),
        ):
            raw, receipt, files = self.run_attempt()
        self.assertTrue(failed[0])
        self.assertEqual(receipt["status"], "failed")
        self.assertIsNone(receipt["manifest_sha256"])
        self.assertEqual(receipt["journal_error"], "journal-close-failed")
        self.assertEqual(
            journal.inspect_journal_prefix(files, digest(files["events.jsonl"]), digest(raw))[
                "status"
            ],
            "incomplete",
        )

    def test_malformed_fixed_scripted_child_preserves_exact_raw_bytes(self):
        spawn = worker.platform_process.spawn
        malformed = b'{"phase":NaN}\n'

        def malformed_child(_args, **kwargs):
            return spawn(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    "import sys; sys.stdin.buffer.read(); "
                    "sys.stdout.buffer.write(b'{\"phase\":NaN}\\n'); sys.stdout.buffer.flush()",
                ],
                **kwargs,
            )

        with patch.object(worker.platform_process, "spawn", side_effect=malformed_child):
            raw, receipt, files = self.run_attempt()
        self.assertEqual(receipt["worker_report"]["primary_error"], "invalid-worker-frame")
        self.assertEqual(files["frame-0.bin"], malformed)
        self.assertNotIn("completed.json", files)
        self.assertEqual(self.inspect(files, raw, receipt["manifest_sha256"])["status"], "failed")

    def test_cold_reader_never_acts_on_persisted_pid_or_launches_engine(self):
        raw, receipt, files = self.run_attempt()
        with (
            patch.object(worker.platform_process, "spawn", side_effect=AssertionError("launch")),
            patch.object(
                worker.platform_process, "force_tree", side_effect=AssertionError("saved PID")
            ),
            patch.object(worker, "_run_worker_fixture", side_effect=AssertionError("engine")),
        ):
            self.assertEqual(
                self.inspect(files, raw, receipt["manifest_sha256"])["status"], "completed"
            )


if __name__ == "__main__":
    unittest.main()
