"""Invented process/journal controls with the trusted engine-free reader."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

from experiments.lt1_diagnostic import journal_reader as journal
from experiments.lt1_diagnostic import reader
from experiments.shared_services.execution import supervise

ROOT = reader.ROOT


class LT1JournalSourcePathTests(unittest.TestCase):
    def test_source_keys_are_canonical_posix_on_both_path_flavors(self):
        for flavor, root in ((PurePosixPath, "/study"), (PureWindowsPath, "C:/study")):
            base = flavor(root)
            path = base / "experiments/lt1_diagnostic/reader.py"
            with patch.object(journal, "ROOT", base):
                self.assertEqual(
                    journal.relative_source_name(path), "experiments/lt1_diagnostic/reader.py"
                )


@unittest.skipUnless(os.name == "posix" and shutil.which("node"), "POSIX Node fixture required")
class LT1JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.plan = self.root / "plan.json"
        self.plan.write_bytes((reader.HERE / "plan.json").read_bytes())
        self.config = self.root / "fixture.json"
        self.config.write_text(
            json.dumps(
                {
                    "plan": json.loads(self.plan.read_bytes()),
                    "identity": journal.identity(self.plan.read_bytes()),
                }
            )
        )
        self.ordinal = 0

    def run_fixture(self, behavior="complete", mode="wrapped", *, cancellation=False):
        self.ordinal += 1
        folder = self.root / str(self.ordinal)
        folder.mkdir(mode=0o700)
        path = folder / "events.jsonl"
        argv = [
            shutil.which("node"),
            str(ROOT / "tests/lt1_journal_fixture.mjs"),
            behavior,
            mode,
            str(self.config),
            str(folder),
        ]
        cancel, stop = threading.Event(), threading.Event()

        def after_prefix():
            while not stop.wait(0.01):
                if path.exists() and len(path.read_bytes().splitlines()) >= 4:
                    cancel.set()
                    return

        watcher = threading.Thread(target=after_prefix, daemon=True) if cancellation else None
        if watcher:
            watcher.start()
        try:
            receipt = supervise(
                argv,
                self.root / f"{self.ordinal}.log",
                timeout=1.5 if behavior in {"hang", "late-hang"} and not cancellation else 5,
                grace=0.1,
                cancel=cancel,
            )
        finally:
            stop.set()
            if watcher:
                watcher.join(timeout=1)
        receipt_path = self.root / f"{self.ordinal}-receipt.json"
        receipt_path.write_text(json.dumps(receipt))
        return path, receipt_path

    def inspect(self, path, receipt):
        return journal.inspect(
            path,
            self.plan,
            receipt,
            reader.digest(path.read_bytes()),
            reader.digest(receipt.read_bytes()),
        )

    def records(self, path):
        return [json.loads(line) for line in path.read_bytes().splitlines()]

    def rewrite(self, path, records):
        path.write_text("".join(json.dumps(row) + "\n" for row in records))

    def test_gate_and_writer_controls(self):
        run = subprocess.run(
            [shutil.which("node"), "--test", "tests/lt1_integration_gate.test.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_both_invented_paths_complete_and_relocate_with_exact_fractional_amount(self):
        previous_rows = None
        for mode in ("direct", "wrapped"):
            path, receipt = self.run_fixture(mode=mode)
            rows = [record["row"] for record in self.records(path) if record["type"] == "row"]
            if previous_rows is not None:
                self.assertEqual(rows, previous_rows)
            previous_rows = rows
            result = self.inspect(path, receipt)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["native_callbacks"], 32)
            self.assertEqual(result["modeled_delivered_u"], {"numerator": 25, "denominator": 48})
            self.assertFalse(result["native_acceptance"])
            moved = self.root / f"moved-{mode}"
            moved.mkdir()
            new_path, new_receipt = moved / "events.jsonl", moved / "receipt.json"
            shutil.copyfile(path, new_path)
            shutil.copyfile(receipt, new_receipt)
            shutil.rmtree(path.parent)
            self.assertEqual(result, self.inspect(new_path, new_receipt))

    def test_native_shaped_primary_and_owner_failures_retain_prefix(self):
        for behavior, cause in (
            ("failure", "fixture primary failure"),
            ("owner", "Supervisor disappeared"),
        ):
            path, receipt = self.run_fixture(behavior)
            result = self.inspect(path, receipt)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["native_callbacks"], 3)
            self.assertEqual(result["modeled_delivered_u"], {"numerator": 3, "denominator": 100})
            self.assertIn(cause, result["primary_error"])

    def test_actual_process_deadline_and_cancel_keep_fsynced_unfinished_prefix(self):
        for cancellation, expected in ((False, "failed"), (True, "interrupted")):
            path, receipt = self.run_fixture("hang", cancellation=cancellation)
            result = self.inspect(path, receipt)
            self.assertEqual(result["status"], expected)
            self.assertEqual(result["native_callbacks"], 3)
            self.assertFalse(result["worker_finish_present"])
            self.assertEqual(result["modeled_delivered_u"], {"numerator": 3, "denominator": 100})
            self.assertEqual(json.loads(receipt.read_bytes())["remaining_owned_processes"], [])

    def test_full_worker_footer_cannot_override_deadline_or_observed_signal(self):
        path, receipt = self.run_fixture("late-hang")
        result = self.inspect(path, receipt)
        self.assertTrue(result["worker_finish_present"])
        self.assertEqual(result["native_callbacks"], 32)
        self.assertEqual(result["status"], "failed")
        path, receipt = self.run_fixture()
        process = json.loads(receipt.read_bytes())
        process["received_signals"] = [15]
        receipt.write_text(json.dumps(process))
        self.assertEqual(self.inspect(path, receipt)["status"], "interrupted")

    def test_torn_last_record_is_unscored_and_completed_record_corruption_refuses(self):
        path, receipt = self.run_fixture("failure")
        records = self.records(path)
        self.rewrite(path, records[:-1])
        with path.open("ab") as stream:
            stream.write(b'{"type":"row","ordinal":3,"row":')
        result = self.inspect(path, receipt)
        self.assertEqual(result["native_callbacks"], 3)
        self.assertGreater(result["uncommitted_tail_bytes"], 0)
        self.assertEqual(result["modeled_delivered_u"], {"numerator": 3, "denominator": 100})
        self.rewrite(path, [*records[:2], {"type": "row", "ordinal": 0, "row": records[1]["row"]}])
        with self.assertRaisesRegex(ValueError, "ordinal"):
            self.inspect(path, receipt)

    def test_receipt_binding_cleanup_hashes_and_scientific_corruption_refuse(self):
        path, receipt = self.run_fixture()
        expected = reader.digest(path.read_bytes())
        with path.open("ab") as stream:
            stream.write(b"uncommitted")
        with self.assertRaisesRegex(ValueError, "journal-identity"):
            journal.inspect(path, self.plan, receipt, expected, reader.digest(receipt.read_bytes()))
        path.write_bytes(path.read_bytes()[: -len(b"uncommitted")])
        base = self.records(path)
        for mutate in (
            lambda rows: rows[0].update(owner_pid=2),
            lambda rows: rows[0].update(output_root="/unrelated/attempt"),
            lambda rows: rows[1]["row"].update(command_u_h=2),
            lambda rows: rows[0]["identity"]["implementation"].update(extra="0" * 64),
        ):
            changed = copy.deepcopy(base)
            mutate(changed)
            self.rewrite(path, changed)
            with self.assertRaises(ValueError):
                self.inspect(path, receipt)
        self.rewrite(path, base)
        process = json.loads(receipt.read_bytes())
        process["remaining_owned_processes"] = None
        receipt.write_text(json.dumps(process))
        with self.assertRaisesRegex(ValueError, "cleanup"):
            self.inspect(path, receipt)

    def test_empty_and_single_row_prefix_have_no_invented_amount(self):
        path, receipt = self.run_fixture("failure")
        records = self.records(path)
        for count in (0, 1):
            self.rewrite(path, records[: count + 1])
            result = self.inspect(path, receipt)
            self.assertEqual(result["native_callbacks"], count)
            self.assertIsNone(result["modeled_delivered_u"])
