"""Owned bundle removal composes existing controls on fresh invented data only."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import lt1_bundle_removal_fixture as fixture

from experiments.lt1_diagnostic import bundle_registration as registration
from experiments.shared_services.execution import supervise

removal, wire = fixture.removal, fixture.wire
ROOT = Path(__file__).resolve().parents[1]


class BundleCycleGateTests(unittest.TestCase):
    def test_production_gate_precedes_request_or_private_path_intake(self):
        with patch.object(removal, "_request", side_effect=AssertionError("private intake")):
            with self.assertRaisesRegex(ValueError, "no reviewed removal request"):
                removal.remove(b"invented invalid request", object())

    def test_fixture_never_consumes_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            sentinel = parent / "request.json"
            sentinel.write_bytes(b"existing invented request must not be consumed")
            with patch.object(removal, "_remove_reviewed", side_effect=AssertionError("removal")):
                with self.assertRaisesRegex(ValueError, "Fresh empty"):
                    fixture.prepare(parent)
            self.assertEqual(
                sentinel.read_bytes(), b"existing invented request must not be consumed"
            )
            # The old two-argument CLI cannot start construction or private intake.
            with (
                patch.object(sys, "argv", ["fixture", str(parent), "complete"]),
                patch.object(fixture, "prepare", side_effect=AssertionError("construction")),
                patch.object(fixture, "load_owned", side_effect=AssertionError("private intake")),
            ):
                with self.assertRaisesRegex(ValueError, "Bounded external"):
                    fixture.main()
            import lt1_reconciliation_packet_fixture as producer

            pins = {
                "schema": "opent1d.invented-bundle-cycle-worker/1",
                "kind": "invented",
                "helper_sha256": wire.digest(Path(fixture.__file__).read_bytes()),
                "prepared": object(),
            }
            for key, wrong in (
                ("schema", "foreign"),
                ("kind", "private"),
                ("helper_sha256", "0" * 64),
            ):
                with (
                    self.subTest(pin=key),
                    patch.object(producer, "load_prepared", side_effect=AssertionError("intake")),
                ):
                    with self.assertRaisesRegex(ValueError, "fixed bundle worker pin"):
                        fixture.load_owned(parent, {**pins, key: wrong})


@unittest.skipUnless(os.name == "posix", "POSIX owned bundle removal fixture required")
class BundleRemovalCycleTests(unittest.TestCase):
    def case(self, phase):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder).resolve()
            parent.chmod(0o700)
            started = time.monotonic()
            pins = fixture.prepare_owned(parent)
            preparation_seconds = time.monotonic() - started
            cancel, done = threading.Event(), threading.Event()

            def watcher():
                while not done.wait(0.01):
                    if (parent / "ready").is_file():
                        cancel.set()
                        return

            thread = (
                threading.Thread(target=watcher, daemon=True) if phase == "quarantined" else None
            )
            if thread:
                thread.start()
            # The supervisor's log lives outside the required-empty fixture root.
            with tempfile.TemporaryDirectory() as logs:
                try:
                    started = time.monotonic()
                    outer = supervise(
                        [
                            sys.executable,
                            "-I",
                            "-S",
                            "-B",
                            str(ROOT / "tests/lt1_bundle_removal_fixture.py"),
                            str(parent),
                            phase,
                            wire.encoded(pins).decode(),
                        ],
                        Path(logs) / "process.log",
                        timeout=20 if phase == "removed" else 30,
                        grace=0.2,
                        cancel=cancel,
                        environment={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
                    )
                    owned_seconds = time.monotonic() - started
                finally:
                    done.set()
                    if thread:
                        thread.join(timeout=1)
                log = (Path(logs) / "process.log").read_bytes()
            print(
                f"bundle-cycle phase={phase} preparation_seconds={preparation_seconds:.3f} "
                f"owned_removal_seconds={owned_seconds:.3f}",
                flush=True,
            )
            complete = phase == "complete"
            self.assertEqual(
                outer["status"],
                "completed" if complete else "interrupted" if phase == "quarantined" else "failed",
                log,
            )
            self.assertEqual(
                outer["error"],
                None if complete else "Cancelled" if phase == "quarantined" else "WorkerDeadline",
            )
            self.assertEqual(outer["remaining_owned_processes"], [])
            self.assertEqual(outer["received_signals"], [])
            self.assertIsNone(outer.get("cleanup_error"))
            self.assertEqual(len(outer["owned_processes"]), 1)
            cycle = json.loads((parent / "cycle.json").read_bytes())
            self.assertEqual(cycle["kind"], "invented")
            self.assertTrue(cycle["production_gate_refused"])
            self.assertTrue(cycle["successor_cannot_rebase_bundle"])
            self.assertEqual(cycle["isolated"], bool(sys.flags.isolated))
            self.assertEqual(cycle["no_site"], bool(sys.flags.no_site))
            worker = json.loads((parent / "worker.json").read_bytes())
            self.assertEqual(worker["kind"], "invented")
            for key in ("isolated", "no_site", "dont_write_bytecode", "production_gate_refused"):
                self.assertIs(worker[key], True)
            self.assertFalse(cycle["proposal_saved_or_approved"])
            self.assertFalse(cycle["global_copy_coverage_verified"])
            self.assertTrue(all(value is False for value in cycle["proposal_flags"].values()))
            self.assertTrue(all(value is False for value in cycle["prepared_flags"].values()))
            for name, expected in cycle["retained_sha256"].items():
                self.assertEqual(wire.digest((parent / name).read_bytes()), expected)
            self.assertEqual((parent / "original-object.txt").read_bytes(), fixture.ORIGINAL)
            base_raw = (parent / "base-register.json").read_bytes()
            proposed_raw = (parent / "proposed-register.json").read_bytes()
            base, proposed = json.loads(base_raw), json.loads(proposed_raw)
            allocation = json.loads((parent / "allocation.json").read_bytes())
            self.assertEqual(wire.digest(base_raw), cycle["base_register_sha256"])
            self.assertEqual(wire.digest(proposed_raw), cycle["proposal_register_sha256"])
            self.assertEqual(proposed["previous_sha256"], cycle["base_register_sha256"])
            self.assertEqual(proposed["policy_sha256"], base["policy_sha256"])
            self.assertEqual(
                proposed["coverage"]["context_sha256"], base["coverage"]["context_sha256"]
            )
            for subject_id, old in base["subjects"].items():
                new = proposed["subjects"][subject_id]
                for key in ("retained_since", "origin_evidence_sha256", "hold"):
                    self.assertEqual(new[key], old[key])
                for copy_id, record in old["copies"].items():
                    self.assertEqual(new["copies"][copy_id], record)
                copy_id = allocation["copies"][subject_id]
                provenance = (parent / (copy_id + ".json")).read_bytes()
                self.assertEqual(
                    new["copies"][copy_id],
                    {"state": "present", "evidence_sha256": wire.digest(provenance)},
                )
                self.assertEqual(
                    json.loads(provenance)["manifest_sha256"], cycle["manifest_sha256"]
                )
            self.assertEqual(proposed["coverage"]["recoverable_until"], "2026-12-01T00:00:00Z")
            self.assertIsNone(proposed["subjects"]["unknown-object"]["retained_since"])
            self.assertTrue(proposed["subjects"]["unknown-object"]["hold"])
            for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
                self.assertIs(proposed["coverage"][key], False)
            policy_raw = (parent / "policy.json").read_bytes()
            assessment = registration.retention.plan(
                proposed_raw,
                wire.digest(proposed_raw),
                policy_raw,
                wire.digest(policy_raw),
                "2026-11-05T12:00:00Z",
                base["coverage"]["context_sha256"],
                previous_raw=base_raw,
                expected_previous_sha256=wire.digest(base_raw),
            )
            self.assertEqual(assessment["deadlines"], cycle["proposal_deadlines"])
            self.assertEqual(
                assessment["deadlines"],
                {"object-one": "2026-11-08T00:00:00Z", "unknown-object": None},
            )
            self.assertEqual(assessment["status"], "blocked")
            self.assertFalse(assessment["effective_erasure_verified"])
            raw, context = (
                (parent / "request.json").read_bytes(),
                (parent / "context.txt").read_bytes(),
            )
            request = json.loads(raw)
            self.assertEqual(
                request["files"][fixture.bundle.MANIFEST]["sha256"], cycle["manifest_sha256"]
            )
            names = sorted(request["files"])
            attempt = parent / "reports/remove-derived-bundle"
            journal = (attempt / "events.jsonl").read_bytes()
            report = removal.inspect(raw, wire.digest(raw), context, wire.digest(journal), outer)
            self.assertEqual(report["status"], "completed" if complete else "incomplete")
            self.assertFalse(report["truncated_journal"])
            self.assertTrue(all(report[key] is False for key in removal.AUTHORITY))
            expected_target = [] if complete else names[1:]
            expected_quarantine = [names[0]] if phase == "quarantined" else []
            expected_removed = names if complete else [names[0]] if phase == "removed" else []
            self.assertEqual(report["target_present"], expected_target)
            self.assertEqual(report["quarantined"], expected_quarantine)
            self.assertEqual(report["recorded_removed"], expected_removed)
            for location, expected in (
                (parent / "bundle", expected_target),
                (attempt / "quarantine", expected_quarantine),
            ):
                self.assertEqual(sorted(p.name for p in location.iterdir()), expected)
                for name in expected:
                    value = (location / name).read_bytes()
                    self.assertEqual(wire.digest(value), request["files"][name]["sha256"])
                    self.assertEqual(len(value), request["files"][name]["bytes"])
            if complete:
                outcome = json.loads((parent / "outcome.json").read_bytes())
                self.assertEqual(outcome["status"], "namespace-absence-observed")
                self.assertTrue(all(outcome[key] is False for key in removal.AUTHORITY))
                failed = {**outer, "status": "failed", "error": "invented outer failure"}
                self.assertEqual(
                    removal.inspect(raw, wire.digest(raw), context, wire.digest(journal), failed)[
                        "status"
                    ],
                    "incomplete",
                )
            else:
                ready = json.loads((parent / "ready").read_bytes())
                self.assertEqual(ready, {"event": phase, "name": names[0]})
                self.assertFalse((parent / "outcome.json").exists())

    def test_complete_owned_bundle_removal_preserves_originals_and_pending_register(self):
        self.case("complete")

    def test_deadline_after_first_unlink_retains_exact_registered_bundle_prefix(self):
        self.case("removed")

    def test_cancel_after_quarantine_keeps_copy_present_and_exact_retained_bytes(self):
        self.case("quarantined")
