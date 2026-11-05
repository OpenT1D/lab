"""Fixed-query mocks and fresh invented local files; no system query/candidate."""

import base64
import hashlib
import os
import plistlib
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.lt1_diagnostic import recovery_probe as probe


class RecoveryProbeTests(unittest.TestCase):
    def fake_capture(self, *, targets=(), sources=None, tools=None, devices=None, readbacks=None):
        source = {"implementation": {"experiments/lt1_diagnostic/recovery_probe.py": "a" * 64}}
        tool = {"diskutil": "b" * 64, "tmutil": "c" * 64}
        with (
            patch.object(probe, "ROOT", Path("/invented/repo")),
            patch.object(probe, "_inside_checkout", return_value=False),
            patch.object(
                probe, "__file__", "/invented/repo/experiments/lt1_diagnostic/recovery_probe.py"
            ),
            patch.object(probe.sys, "platform", "darwin"),
            patch.object(probe.platform, "machine", return_value="arm64"),
            patch.object(probe, "_source_identity", side_effect=sources or [source, source]),
            patch.object(probe, "_tool_identity", side_effect=tools or [tool, tool]),
            patch.object(probe, "_data_device", side_effect=devices or [123, 123]),
            patch.object(
                probe, "_query", return_value={"status": "response-observed", "returncode": 0}
            ) as query,
            patch.object(probe, "_readback", side_effect=readbacks) as readback,
        ):
            result = probe.capture(targets=targets)
            return result, query, readback

    def test_three_successful_queries_are_observations_never_complete_coverage(self):
        report, query, readback = self.fake_capture()
        self.assertEqual(report["status"], "observed")
        self.assertEqual([c.args[0] for c in query.call_args_list], list(probe.COMMANDS))
        readback.assert_not_called()
        self.assertTrue(all(v is False for v in report["coverage"].values()))
        self.assertTrue(all(v is False for v in report["authorizations"].values()))

    def test_source_tool_or_data_mapping_change_refuses(self):
        for kwargs in (
            {"sources": [{"invented": 1}, {"invented": 2}]},
            {"tools": [{"diskutil": "a", "tmutil": "b"}, {"diskutil": "x", "tmutil": "b"}]},
            {"devices": [123, 456]},
        ):
            with self.assertRaisesRegex(ValueError, "changed"):
                self.fake_capture(**kwargs)

    def test_missing_tool_or_data_mapping_stays_partial(self):
        tool = {"diskutil": None, "tmutil": "c" * 64}
        report, query, _ = self.fake_capture(tools=[tool, tool])
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["queries"]["apfs_snapshots"]["error"], "tool-unavailable")
        self.assertEqual(query.call_count, 2)
        report, _, _ = self.fake_capture(devices=[None, None])
        self.assertEqual(report["status"], "partial")
        self.assertIsNone(report["data_device"])

    def test_failed_reads_also_consume_the_shared_byte_budget(self):
        outcomes = [({"state": "unknown"}, 3), ({"state": "unknown"}, 1)]
        with patch.object(probe, "TOTAL_LIMIT", 4):
            report, _, readback = self.fake_capture(
                targets=("/invented/a", "/invented/b"), readbacks=outcomes
            )
        self.assertEqual([c.args[2] for c in readback.call_args_list], [4, 1])
        self.assertEqual(report["status"], "partial")

    def test_offtree_unsupported_and_bad_target_inputs_make_no_query(self):
        with (
            patch.object(probe, "__file__", "/invented/offtree.py"),
            patch.object(probe, "_query") as query,
        ):
            with self.assertRaisesRegex(ValueError, "canonical"):
                probe.capture()
            query.assert_not_called()
        for kwargs in (
            {"targets": ("/invented/a", "/invented/a")},
            {"targets": ["/invented/a"] * (probe.MAX_TARGETS + 1)},
            {"targets": ("relative",)},
        ):
            with self.assertRaises(ValueError):
                self.fake_capture(**kwargs)
        with (
            patch.object(probe, "ROOT", Path("/invented/repo")),
            patch.object(
                probe, "__file__", "/invented/repo/experiments/lt1_diagnostic/recovery_probe.py"
            ),
            patch.object(probe.sys, "platform", "linux"),
            patch.object(probe, "_query") as query,
        ):
            with self.assertRaisesRegex(ValueError, "Darwin"):
                probe.capture()
            query.assert_not_called()

    def test_queries_have_only_fixed_read_argv_and_clean_environment(self):
        for name, (tool, *args) in probe.COMMANDS.items():
            raw = (
                b"Snapshots for invented volume:\n"
                if name == "time_machine_snapshots"
                else plistlib.dumps({"Invented": []})
            )
            result = SimpleNamespace(returncode=0, stdout=raw, stderr=b"")
            with patch.object(probe.subprocess, "run", return_value=result) as run:
                report = probe._query(name)
                self.assertEqual(run.call_args.args[0], [str(probe.TOOLS[tool]), *args])
                self.assertEqual(run.call_args.kwargs["env"], probe.ENVIRONMENT)
                self.assertEqual(report["status"], "response-observed")
                self.assertEqual(base64.b64decode(report["stdout_base64"]), raw)
                self.assertEqual(report["stdout_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            set(probe.COMMANDS),
            {"apfs_snapshots", "time_machine_snapshots", "configured_destinations"},
        )
        with patch.object(probe.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "fixed query"):
                probe._query("listbackups")
            run.assert_not_called()

    def test_nonzero_empty_bad_plist_timeout_and_oversize_do_not_pass(self):
        for code, raw in (
            (1, plistlib.dumps({})),
            (0, b""),
            (0, b"<plist><broken>"),
            (0, b"x" * (probe.QUERY_LIMIT + 1)),
        ):
            with patch.object(
                probe.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=code, stdout=raw, stderr=b""),
            ):
                result = probe._query("apfs_snapshots")
                self.assertEqual(result["status"], "unavailable")
                self.assertLessEqual(
                    len(base64.b64decode(result["stdout_base64"])), probe.QUERY_LIMIT
                )
        with patch.object(
            probe.subprocess, "run", side_effect=subprocess.TimeoutExpired(["invented"], 5)
        ):
            self.assertEqual(probe._query("apfs_snapshots")["status"], "unavailable")

    def test_empty_destination_array_is_an_observed_response_not_backup_coverage(self):
        raw = plistlib.dumps([])
        result = SimpleNamespace(returncode=0, stdout=raw, stderr=b"")
        with patch.object(probe.subprocess, "run", return_value=result):
            observed = probe._query("configured_destinations")
        self.assertEqual(observed["status"], "response-observed")
        self.assertTrue(observed["plist_valid"])
        self.assertTrue(all(v is False for v in probe.COVERAGE.values()))


@unittest.skipUnless(os.name == "posix", "POSIX exact file readback required")
class LocalReadbackTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.device = self.root.stat().st_dev
        self.file = self.root / "invented.txt"
        self.file.write_bytes(b"invented-only")
        self.file.chmod(0o600)

    def read(self, path=None, device=None, budget=probe.TOTAL_LIMIT):
        return probe._readback(path or self.file, self.device if device is None else device, budget)

    def test_exact_present_and_absent_are_only_local_observations(self):
        report, consumed = self.read()
        self.assertEqual(report["state"], "present")
        self.assertEqual(consumed, len(b"invented-only"))
        self.assertTrue(report["data_device_matches"])
        self.assertEqual(report["sha256"], hashlib.sha256(b"invented-only").hexdigest())
        self.assertEqual(self.file.read_bytes(), b"invented-only")
        report, consumed = self.read(self.root / "not-created.txt")
        self.assertEqual(report["state"], "absence-observed")
        self.assertEqual(consumed, 0)
        self.assertNotIn("effective_erasure_verified", report)

    def test_checkout_case_alias_refuses_before_source_or_query_collection(self):
        checkout = self.root / "Checkout"
        checkout.mkdir(mode=0o700)
        target = checkout / "record.txt"
        target.write_bytes(b"invented private record")
        target.chmod(0o600)
        alias = self.root / "checkout/record.txt"
        if not alias.exists():
            alias = target
        with (
            patch.object(probe, "ROOT", checkout),
            patch.object(
                probe, "__file__", str(checkout / "experiments/lt1_diagnostic/recovery_probe.py")
            ),
            patch.object(probe.sys, "platform", "darwin"),
            patch.object(probe.platform, "machine", return_value="arm64"),
            patch.object(probe, "_source_identity") as source,
            patch.object(probe, "_query") as query,
        ):
            with self.assertRaisesRegex(ValueError, "outside checkout"):
                probe.capture(targets=(alias,))
            source.assert_not_called()
            query.assert_not_called()

    def test_unknown_checkout_identity_is_not_classified_as_outside(self):
        actual = Path.stat

        def denied(path, *args, **kwargs):
            if path == probe.ROOT:
                raise PermissionError("controlled missing checkout identity")
            return actual(path, *args, **kwargs)

        with (
            patch.object(Path, "stat", new=denied),
            patch.object(probe.sys, "platform", "darwin"),
            patch.object(probe.platform, "machine", return_value="arm64"),
            patch.object(probe, "_source_identity") as source,
            patch.object(probe, "_query") as query,
        ):
            with self.assertRaisesRegex(ValueError, "checkout ancestry unavailable"):
                probe.capture(targets=(self.file,))
            source.assert_not_called()
            query.assert_not_called()

    def test_readback_interval_does_not_invent_an_absence_start(self):
        first = datetime.now(UTC)
        last = first + timedelta(seconds=2)
        with patch.object(probe, "datetime") as clock:
            clock.now.side_effect = [first, last]
            report, _ = self.read(self.root / "not-created.txt")
        self.assertEqual(report["state"], "absence-observed")
        self.assertEqual(report["observed_from"], first.isoformat())
        self.assertEqual(report["observed_to"], last.isoformat())
        self.assertNotIn("absent_since", report)
        self.assertNotIn("observed_at", report)

    def test_data_mismatch_unknown_and_byte_bound_never_read_content(self):
        with patch.object(probe.os, "read") as read:
            for device, budget in ((self.device + 1, 100), (self.device, 1)):
                report, consumed = self.read(device=device, budget=budget)
                self.assertEqual(report["state"], "unknown")
                self.assertEqual(consumed, 0)
            read.assert_not_called()
        report, _ = probe._readback(self.file, None, 100)
        self.assertEqual(report["state"], "unknown")

    def test_symlink_fifo_hardlink_and_nonprivate_mode_are_not_adopted(self):
        link = self.root / "alias.txt"
        link.symlink_to(self.file)
        self.assertEqual(self.read(link)[0]["state"], "unknown")
        fifo = self.root / "fifo"
        os.mkfifo(fifo, 0o600)
        self.assertEqual(self.read(fifo)[0]["state"], "unknown")
        hard = self.root / "hard.txt"
        os.link(self.file, hard)
        self.assertEqual(self.read(hard)[0]["state"], "unknown")
        hard.unlink()
        self.file.chmod(0o644)
        self.assertEqual(self.read()[0]["state"], "unknown")

    def test_growth_is_retained_unknown_and_failed_bytes_are_charged(self):
        original = probe.os.read
        changed = False

        def grow(fd, size):
            nonlocal changed
            raw = original(fd, size)
            if raw and not changed:
                changed = True
                with self.file.open("ab") as out:
                    out.write(b"changed")
            return raw

        with patch.object(probe.os, "read", side_effect=grow):
            report, consumed = self.read()
        self.assertEqual(report["state"], "unknown")
        self.assertGreater(consumed, 0)
        self.assertNotIn("sha256", report)

    def test_parent_rebinding_does_not_turn_open_fd_into_named_path_proof(self):
        folder = self.root / "scope"
        folder.mkdir(mode=0o700)
        path = folder / "invented.txt"
        path.write_bytes(b"invented")
        path.chmod(0o600)
        original = probe.os.read
        changed = False

        def rebind(fd, size):
            nonlocal changed
            raw = original(fd, size)
            if raw and not changed:
                changed = True
                folder.rename(self.root / "moved-scope")
            return raw

        with patch.object(probe.os, "read", side_effect=rebind):
            report, consumed = self.read(path)
        self.assertEqual(report["state"], "unknown")
        self.assertGreater(consumed, 0)
        self.assertNotIn("sha256", report)


if __name__ == "__main__":
    unittest.main()
