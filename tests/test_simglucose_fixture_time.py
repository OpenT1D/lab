"""Invented calendar isolation, including fixed owned children after real expiry."""

import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from experiments.simglucose_audit import fixture_time as clock
from experiments.simglucose_audit import intake_collector, pbs_intake, verifier_preparation
from experiments.simglucose_audit import pbs_production_inspection as production

FUTURE = datetime(2050, 1, 1, tzinfo=UTC)


class FixtureTimeTests(unittest.TestCase):
    def test_fixed_calendar_is_scoped_and_actual_mode_cannot_inherit_it(self):
        @clock.actual
        def actual():
            return clock.now()

        with patch.object(clock, "_real_now", return_value=FUTURE):
            self.assertEqual(clock.now(), FUTURE)
            with clock.use(True):
                self.assertEqual(clock.now(), clock.FIXTURE_UTC)
                self.assertEqual(actual(), FUTURE)
                self.assertEqual(clock.now(), clock.FIXTURE_UTC)
                with self.assertRaisesRegex(RuntimeError, "fixed failure"):
                    with clock.use(False):
                        self.assertEqual(clock.now(), FUTURE)
                        raise RuntimeError("fixed failure")
                self.assertEqual(clock.now(), clock.FIXTURE_UTC)
            self.assertEqual(clock.now(), FUTURE)

    def test_invented_calendar_does_not_change_another_threads_actual_clock(self):
        observed = []
        with patch.object(clock, "_real_now", return_value=FUTURE), clock.use(True):
            thread = threading.Thread(target=lambda: observed.append(clock.now()))
            thread.start()
            thread.join(timeout=1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(observed, [FUTURE])
            self.assertEqual(clock.now(), clock.FIXTURE_UTC)

    def test_only_exact_fixture_boolean_selects_calendar(self):
        @clock.selected(0)
        def selected(fixture=False):
            return clock.now()

        with patch.object(clock, "_real_now", return_value=FUTURE):
            self.assertEqual(selected(), FUTURE)
            self.assertEqual(selected(True), clock.FIXTURE_UTC)
            self.assertEqual(selected(fixture=True), clock.FIXTURE_UTC)
            for invalid in (0, 1, None, "invented"):
                with (
                    self.subTest(invalid=invalid),
                    self.assertRaisesRegex(ValueError, "exact-invented-clock-mode"),
                ):
                    selected(invalid)
            self.assertEqual(clock.now(), FUTURE)

    def test_fixture_calendar_does_not_extend_real_monotonic_deadline(self):
        expiry = clock.FIXTURE_UTC + timedelta(minutes=1)
        with clock.use(True), patch.object(pbs_intake.time, "monotonic", return_value=2):
            with self.assertRaisesRegex(ValueError, "current-deadline"):
                pbs_intake._live(expiry, 1)

    def test_actual_executor_clears_enclosing_fixture_clock_before_approval_gate(self):
        def gate(*_args):
            self.assertEqual(intake_collector._now(), FUTURE)
            raise LookupError("actual gate reached without material I/O")

        with (
            patch.object(clock, "_real_now", return_value=FUTURE),
            clock.use(True),
            patch.object(pbs_intake, "_gate", side_effect=gate),
            self.assertRaisesRegex(LookupError, "actual gate reached"),
        ):
            pbs_intake._execute(None, None, None, None)

    def test_invented_gate_survives_future_calendar_and_old_clock_control_refuses(self):
        root = Path(tempfile.mkdtemp(prefix="ot062-clock-gate-")).resolve()
        with patch.object(clock, "_real_now", return_value=FUTURE):
            inputs = pbs_intake.fixture_inputs(root / "invented-intake")
            pbs_intake._gate(*inputs, fixture=True, headroom=True)
            # Reproduce the old live-calendar path without changing stored source.
            with patch.object(clock, "now", side_effect=clock._real_now):
                with self.assertRaisesRegex(ValueError, "origin-timing-basis"):
                    pbs_intake._gate(*inputs, fixture=True, headroom=True)
        self.assertFalse((root / "invented-intake").exists())

    def test_fixed_calendar_reaches_owned_intake_and_discovery_children(self):
        root = Path(tempfile.mkdtemp(prefix="ot062-clock-child-")).resolve()
        with patch.object(clock, "_real_now", return_value=FUTURE):
            for name, module in (("pbs", pbs_intake), ("discovery", verifier_preparation)):
                parent = root / name
                parent.mkdir(mode=0o700)
                result = module.run_fixture(parent / "invented-intake")
                with self.subTest(name=name):
                    self.assertEqual(result["status"], "completed")
                    self.assertEqual(result["kind"], "invented")
                    self.assertEqual(result["ended_utc"], "2026-11-10T14:00:00Z")

    def test_generated_fixture_child_uses_same_calendar_but_no_actual_admission(self):
        root = Path(tempfile.mkdtemp(prefix="ot062-clock-generated-")).resolve()
        with patch.object(clock, "_real_now", return_value=FUTURE):
            report = production.qualify_invented_scenario("small", root / "generated")
            self.assertEqual(report["status"], "invented-owned-route-completed")
            self.assertEqual(report["worker"]["issued_utc"], "2026-11-10T14:00:00Z")
            self.assertFalse(report["worker"]["actual_crypto_verified"])
            raw = production.encode(report)
            self.assertEqual(
                production.inspect_fixture_metadata(
                    raw, production.digest(raw), report["issued_completion_pin"]
                )["payload_reopened_or_rehashed"],
                False,
            )


if __name__ == "__main__":
    unittest.main()
