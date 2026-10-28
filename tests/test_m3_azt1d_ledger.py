"""Synthetic-only tests for durable AZT1D evaluation-access accounting."""

import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

from experiments.m3.azt1d.common import ROOT
from experiments.m3.azt1d.ledger import (
    create_ledger,
    record_access,
    snapshot_ledger,
    verify_evidence,
    verify_snapshot,
)

IDENTITY = {"study": "synthetic", "source": "a" * 64, "allocation": "b" * 64, "split": [20, 5]}
DISCLOSURE = {"reviewed": True, "status": "none", "reference": ""}
FREEZE = "c" * 64


def _concurrent_append(path, index):
    return record_access(path, IDENTITY, FREEZE, "before_execution", f"fixture_{index}")


class AccessLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "access.jsonl"
        self.genesis = create_ledger(self.path, IDENTITY, DISCLOSURE, "synthetic")

    def test_genesis_and_prefix_receipts_reveal_later_events(self):
        initial = verify_evidence(self.path, IDENTITY, self.genesis)
        self.assertEqual(initial["event_count"], 0)
        normalized = record_access(self.path, IDENTITY, FREEZE, "before_normalization", "fixture")
        executed = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        repeated = record_access(self.path, IDENTITY, "d" * 64, "before_execution", "fixture")
        self.assertEqual(normalized["sequence"], 1)
        self.assertEqual(normalized["prior_event_count"], 0)
        self.assertEqual(executed["prior_event_count"], 1)
        self.assertEqual(executed["prior_person_event_count"], 1)
        self.assertFalse(executed["repeated_event"])
        self.assertEqual(repeated["prior_event_count"], 2)
        self.assertEqual(repeated["prior_person_event_count"], 2)
        self.assertEqual(repeated["prior_same_event_count"], 1)
        self.assertTrue(repeated["repeated_event"])
        for evidence in (self.genesis, normalized, executed, repeated):
            current = verify_evidence(self.path, IDENTITY, evidence)
            self.assertEqual(current["event_count"], 3)
            self.assertEqual(current["head_sequence"], 3)
            self.assertEqual(current["head_sha256"], repeated["event_sha256"])
            self.assertEqual(current["prior_access"], DISCLOSURE)
            self.assertEqual(current["evidence"], evidence)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_snapshot_can_be_copied_but_live_path_cannot(self):
        event = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        copied = Path(self.temp.name) / "copy.jsonl"
        copied.write_bytes(self.path.read_bytes())
        self.assertEqual(verify_snapshot(copied.read_bytes(), IDENTITY, event)["event_count"], 1)
        with self.assertRaisesRegex(ValueError, "path changed"):
            verify_evidence(copied, IDENTITY, event)
        with self.assertRaisesRegex(ValueError, "path changed"):
            record_access(copied, IDENTITY, FREEZE, "before_execution", "fixture")

    def test_snapshot_validates_path_identity_receipt_and_entire_chain(self):
        event = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        raw = snapshot_ledger(self.path, IDENTITY, self.genesis)
        self.assertEqual(raw, self.path.read_bytes())
        self.assertEqual(verify_snapshot(raw, IDENTITY, event)["event_count"], 1)
        with self.assertRaises(ValueError):
            snapshot_ledger(self.path, IDENTITY | {"source": "e" * 64}, self.genesis)
        with self.assertRaises(ValueError):
            snapshot_ledger(self.path, IDENTITY, event | {"event_sha256": "0" * 64})
        copied = Path(self.temp.name) / "snapshot-copy.jsonl"
        copied.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "path changed"):
            snapshot_ledger(copied, IDENTITY, self.genesis)
        self.path.write_bytes(raw + b"{incomplete append")
        with self.assertRaisesRegex(ValueError, "history"):
            snapshot_ledger(self.path, IDENTITY, self.genesis)

    def test_snapshot_waits_for_concurrent_append_to_finish(self):
        partial_written, release_writer, reader_started = Event(), Event(), Event()
        original_write = os.write
        calls = 0

        def split_write(fd, raw):
            nonlocal calls
            calls += 1
            if calls == 1:
                written = original_write(fd, raw[: len(raw) // 2])
                partial_written.set()
                return written
            if not release_writer.wait(timeout=5):
                raise OSError("Synthetic append barrier expired")
            return original_write(fd, raw)

        def snapshot():
            reader_started.set()
            return snapshot_ledger(self.path, IDENTITY, self.genesis)

        with patch("experiments.m3.azt1d.ledger.os.write", side_effect=split_write):
            with ThreadPoolExecutor(max_workers=2) as pool:
                writer = pool.submit(_concurrent_append, self.path, 1)
                try:
                    self.assertTrue(partial_written.wait(timeout=5))
                    reader = pool.submit(snapshot)
                    self.assertTrue(reader_started.wait(timeout=5))
                    with self.assertRaises(TimeoutError):
                        reader.result(timeout=0.05)
                finally:
                    release_writer.set()
                receipt = writer.result(timeout=5)
                raw = reader.result(timeout=5)
        context = verify_snapshot(raw, IDENTITY, receipt)
        self.assertEqual(context["event_count"], 1)
        self.assertEqual(raw, self.path.read_bytes())

    def test_reinitialization_never_erases_history(self):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "I/O failed"):
            create_ledger(self.path, IDENTITY, DISCLOSURE, "synthetic")
        self.assertEqual(self.path.read_bytes(), before)
        empty = Path(self.temp.name) / "empty.jsonl"
        empty.touch()
        with self.assertRaisesRegex(ValueError, "I/O failed"):
            create_ledger(empty, IDENTITY, DISCLOSURE, "synthetic")
        with self.assertRaisesRegex(ValueError, "history"):
            record_access(empty, IDENTITY, FREEZE, "before_execution", "fixture")

    def test_identity_and_bad_access_arguments_refuse_append(self):
        before = self.path.read_bytes()
        for identity in ({**IDENTITY, "source": "e" * 64}, {}, {"not_json": (1, 2)}, {1: "key"}):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                record_access(self.path, identity, FREEZE, "before_execution", "fixture")
        for kwargs in (
            {"freeze_sha": "bad"},
            {"event": "after_execution"},
            {"person": "fixture/invalid"},
            {"phase": "development"},
        ):
            args = dict(freeze_sha=FREEZE, event="before_execution", person="fixture") | kwargs
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                record_access(self.path, IDENTITY, **args)
        self.assertEqual(self.path.read_bytes(), before)

    def test_wrong_and_mutated_receipts_fail(self):
        evidence = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        for key, value in (
            ("genesis_sha256", "0" * 64),
            ("event_sha256", "0" * 64),
            ("sequence", 9),
            ("sequence", True),
            ("prior_event_count", False),
            ("ledger_path", "/different"),
            ("repeated_event", 0),
            ("freeze_sha256", "d" * 64),
        ):
            altered = evidence | {key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_evidence(self.path, IDENTITY, altered)
        with self.assertRaises(ValueError):
            verify_evidence(self.path, {**IDENTITY, "split": [19, 6]}, evidence)

    def test_chain_tampering_reordering_truncation_and_bad_suffix_fail(self):
        event = record_access(self.path, IDENTITY, FREEZE, "before_normalization", "fixture")
        record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        raw = self.path.read_bytes()
        lines = raw.splitlines(keepends=True)
        mutations = (
            raw.replace(b"before_normalization", b"before_execution", 1),
            lines[0] + lines[2] + lines[1],
            b"".join(lines[:1]),
            raw[:-1],
            raw + b"{bad record}\n",
            raw + b"\n",
            raw.replace(b'"sequence":1', b'"sequence":true'),
            raw.replace(b'"schema":', b'"schema":null,"schema":', 1),
        )
        for mutated in mutations:
            with self.subTest(length=len(mutated)), self.assertRaises(ValueError):
                verify_snapshot(mutated, IDENTITY, event)
        self.path.write_bytes(raw + b"{bad record}\n")
        with self.assertRaises(ValueError):
            record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")

    def test_full_snapshot_verification_checks_beyond_receipt(self):
        record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        raw = self.path.read_bytes()
        self.assertEqual(verify_snapshot(raw, IDENTITY, self.genesis)["event_count"], 1)
        with self.assertRaisesRegex(ValueError, "history"):
            verify_snapshot(raw.replace(FREEZE.encode(), b"d" * 64), IDENTITY, self.genesis)

    def test_human_history_requires_explicit_reviewed_disclosure(self):
        human = Path(self.temp.name) / "human-policy-synthetic-history.jsonl"
        with self.assertRaisesRegex(ValueError, "disclosure reference"):
            create_ledger(human, IDENTITY, DISCLOSURE, "human")
        disclosure = {"reviewed": True, "status": "unknown", "reference": "synthetic-test-review"}
        evidence = create_ledger(human, IDENTITY, disclosure, "human")
        disclosure["status"] = "none"
        current = verify_evidence(human, IDENTITY, evidence)
        self.assertEqual(current["prior_access"]["status"], "unknown")
        self.assertEqual(current["kind"], "human")
        event = record_access(human, IDENTITY, FREEZE, "before_execution", "fixture")
        self.assertEqual(event["prior_access"]["status"], "unknown")
        for prior in (
            {**DISCLOSURE, "reviewed": False},
            {**DISCLOSURE, "reviewed": 1},
            {**DISCLOSURE, "status": "unseen"},
            {**DISCLOSURE, "additional": "undeclared"},
        ):
            with self.subTest(prior=prior), self.assertRaises(ValueError):
                create_ledger(Path(self.temp.name) / "refused.jsonl", IDENTITY, prior, "synthetic")

    def test_human_ledger_in_repository_refused_before_creation(self):
        target = ROOT / "synthetic-policy-ledger-must-not-be-created.jsonl"
        self.assertFalse(target.exists())
        with self.assertRaisesRegex(ValueError, "outside repository"):
            create_ledger(target, IDENTITY, DISCLOSURE | {"reference": "test"}, "human")
        self.assertFalse(target.exists())

    def test_concurrent_threads_do_not_lose_or_duplicate_sequences(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            receipts = list(pool.map(lambda index: _concurrent_append(self.path, index), range(24)))
        self.assertEqual(sorted(item["sequence"] for item in receipts), list(range(1, 25)))
        self.assertEqual(verify_evidence(self.path, IDENTITY, self.genesis)["event_count"], 24)
        for evidence in receipts:
            verify_evidence(self.path, IDENTITY, evidence)

    def test_concurrent_processes_share_lock(self):
        with ProcessPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_concurrent_append, str(self.path), index) for index in range(9)]
            receipts = [future.result() for future in futures]
        self.assertEqual(sorted(item["sequence"] for item in receipts), list(range(1, 10)))
        self.assertEqual(verify_evidence(self.path, IDENTITY, self.genesis)["event_count"], 9)

    def test_fsync_failure_returns_no_receipt_and_preserves_written_history(self):
        with patch("experiments.m3.azt1d.ledger.os.fsync", side_effect=OSError("private detail")):
            with self.assertRaisesRegex(ValueError, "I/O failed") as caught:
                record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        self.assertNotIn("private detail", str(caught.exception))
        self.assertEqual(verify_evidence(self.path, IDENTITY, self.genesis)["event_count"], 1)
        event = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        self.assertTrue(event["repeated_event"])

    def test_partial_write_fails_closed_without_repair(self):
        original_write = os.write
        calls = 0

        def interrupted(fd, raw):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(fd, raw[:13])
            raise OSError("private detail")

        before = self.path.read_bytes()
        with patch("experiments.m3.azt1d.ledger.os.write", side_effect=interrupted):
            with self.assertRaisesRegex(ValueError, "I/O failed"):
                record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        after = self.path.read_bytes()
        self.assertEqual(after[: len(before)], before)
        self.assertGreater(len(after), len(before))
        with self.assertRaisesRegex(ValueError, "history"):
            verify_evidence(self.path, IDENTITY, self.genesis)
        with self.assertRaisesRegex(ValueError, "history"):
            record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        self.assertEqual(self.path.read_bytes(), after)

    def test_creation_fsync_failure_leaves_file_and_refuses_reset(self):
        failed = Path(self.temp.name) / "failed.jsonl"
        with patch("experiments.m3.azt1d.ledger.os.fsync", side_effect=OSError("private detail")):
            with self.assertRaisesRegex(ValueError, "I/O failed"):
                create_ledger(failed, IDENTITY, DISCLOSURE, "synthetic")
        self.assertTrue(failed.exists())
        before = failed.read_bytes()
        with self.assertRaises(ValueError):
            create_ledger(failed, IDENTITY, DISCLOSURE, "synthetic")
        self.assertEqual(failed.read_bytes(), before)

    def test_symbolic_and_hard_links_are_refused(self):
        symbolic = Path(self.temp.name) / "symlink.jsonl"
        symbolic.symlink_to(self.path)
        with self.assertRaises(ValueError):
            verify_evidence(symbolic, IDENTITY, self.genesis)
        hard = Path(self.temp.name) / "hardlink.jsonl"
        os.link(self.path, hard)
        with self.assertRaisesRegex(ValueError, "regular file"):
            verify_evidence(self.path, IDENTITY, self.genesis)
        with self.assertRaises(ValueError):
            record_access(hard, IDENTITY, FREEZE, "before_execution", "fixture")

    def test_errors_do_not_echo_record_content(self):
        private_marker = "SYNTHETIC_SECRET_MARKER"
        malformed = (
            ('{"' + private_marker + '":1,"' + private_marker + '":2}\n').encode(),
            b'"' + private_marker.encode() + b'"\n',
            b"\xff\n",
        )
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(ValueError) as caught:
                verify_snapshot(raw, IDENTITY, self.genesis)
            self.assertNotIn(private_marker, str(caught.exception))

    def test_ledger_holds_only_identity_hash_and_access_metadata(self):
        event = record_access(self.path, IDENTITY, FREEZE, "before_execution", "fixture")
        records = [json.loads(line) for line in self.path.read_bytes().splitlines()]
        self.assertNotIn("allocation", records[0]["payload"])
        self.assertNotIn("source", records[0]["payload"])
        self.assertEqual(records[1]["payload"]["freeze_sha256"], FREEZE)
        altered = copy.deepcopy(event)
        altered["prior_access"]["status"] = "present"
        with self.assertRaises(ValueError):
            verify_snapshot(self.path.read_bytes(), IDENTITY, altered)


if __name__ == "__main__":
    unittest.main()
