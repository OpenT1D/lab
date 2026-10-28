"""Admission rechecks only completed POSIX ownership, retaining cleanup on errors."""

import itertools
import signal
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from experiments.desktop import admission


class AdmissionExitObservationTests(unittest.TestCase):
    def setUp(self):
        self.owner = admission.Admission("m3-compare", SimpleNamespace())
        self.process = Mock(pid=123)
        self.process.poll.return_value = 0
        self.process.wait.return_value = 0
        for name in ("spawn", "tree_exists", "signal_tree", "close_tree"):
            context = patch.object(admission, name)
            setattr(self, name, context.start())
            self.addCleanup(context.stop)
        self.spawn.return_value = self.process
        self.tree_exists.return_value = False
        for name, value in (("os", SimpleNamespace(name="posix")), ("GROUP_RECHECK_SECONDS", 0.02)):
            context = patch.object(admission, name, value)
            context.start()
            self.addCleanup(context.stop)

    def supervise(self):
        return self.owner.supervise(["trusted-worker"], 30, {})

    def assert_cleanup(self):
        self.process.wait.assert_any_call(timeout=admission.ROOT_WAIT_SECONDS)
        self.close_tree.assert_called_once_with(self.process)
        self.assertIsNone(self.owner.active)

    def test_denied_group_probe_reaps_then_requires_a_fresh_disappearance(self):
        self.process.poll.side_effect = itertools.chain([None], itertools.repeat(0))
        denied_at = []

        def probe(process):
            if not denied_at:
                denied_at.append(process.poll.call_count)
                raise PermissionError("unreaped completed group")
            self.assertGreater(process.poll.call_count, denied_at[0])
            return False

        self.tree_exists.side_effect = probe
        self.assertEqual(self.supervise(), (0, None))
        self.signal_tree.assert_not_called()
        self.assert_cleanup()

    def test_forwarded_term_denial_preserves_cancellation_after_observed_exit(self):
        self.owner.active = self.process
        self.signal_tree.side_effect = PermissionError("exited during TERM")
        self.owner._forward(signal.SIGTERM)
        self.assertEqual(self.owner.received, signal.SIGTERM)
        self.assertTrue(self.owner.soft_sent)
        self.signal_tree.assert_called_once_with(self.process, signal.SIGTERM)
        self.process.poll.assert_called_once_with()
        self.tree_exists.assert_called_once_with(self.process)

    def test_final_force_denial_is_cleared_only_after_fresh_group_disappearance(self):
        self.tree_exists.side_effect = [True, False, True, False]

        def send(process, number):
            if number == admission.FORCE_SIGNAL:
                raise PermissionError("exited during force")

        self.signal_tree.side_effect = send
        with self.assertRaises(admission.AdmissionFailure) as caught:
            self.supervise()
        self.assertEqual(caught.exception.error_type, "UnreapedWorkerGroup")
        self.assertEqual(
            self.signal_tree.call_args_list,
            [call(self.process, signal.SIGTERM), call(self.process, admission.FORCE_SIGNAL)],
        )
        self.assert_cleanup()

    def test_loop_term_denial_still_preserves_the_unreaped_group_failure(self):
        self.tree_exists.side_effect = [True, False, False, False]
        self.signal_tree.side_effect = PermissionError("exited during loop TERM")
        with self.assertRaises(admission.AdmissionFailure) as caught:
            self.supervise()
        self.assertEqual(caught.exception.error_type, "UnreapedWorkerGroup")
        self.signal_tree.assert_called_once_with(self.process, signal.SIGTERM)
        self.assert_cleanup()

    def test_loop_force_denial_requires_fresh_disappearance_without_erasing_failure(self):
        self.tree_exists.side_effect = [True, False, False, False]

        def send(process, number):
            if number == admission.FORCE_SIGNAL:
                raise PermissionError("exited during loop force")

        self.signal_tree.side_effect = send
        with patch.object(admission, "TERM_SECONDS", 0):
            with self.assertRaises(admission.AdmissionFailure) as caught:
                self.supervise()
        self.assertEqual(caught.exception.error_type, "UnreapedWorkerGroup")
        self.assertEqual(
            self.signal_tree.call_args_list,
            [call(self.process, signal.SIGTERM), call(self.process, admission.FORCE_SIGNAL)],
        )
        self.assert_cleanup()

    def test_persistent_probe_denial_stays_failed_and_still_waits_and_closes(self):
        self.tree_exists.side_effect = PermissionError("persistent group denial")
        with self.assertRaisesRegex(PermissionError, "persistent group denial"):
            self.supervise()
        self.assert_cleanup()

    def test_fresh_live_group_cannot_clear_an_earlier_denial(self):
        self.tree_exists.side_effect = [PermissionError("live group denial"), True, True]
        with self.assertRaisesRegex(PermissionError, "live group denial"):
            self.supervise()
        self.signal_tree.assert_called_once_with(self.process, admission.FORCE_SIGNAL)
        self.assert_cleanup()

    def test_live_leader_and_absent_group_cannot_clear_denial(self):
        self.process.poll.return_value = None
        self.tree_exists.side_effect = [PermissionError("live leader denial"), False]
        with self.assertRaisesRegex(PermissionError, "live leader denial"):
            self.supervise()
        self.signal_tree.assert_called_once_with(self.process, admission.FORCE_SIGNAL)
        self.assert_cleanup()

    def test_probe_and_force_errors_cannot_skip_retained_wait_or_close(self):
        self.process.poll.return_value = None
        self.tree_exists.side_effect = [RuntimeError("probe failed"), True]
        self.signal_tree.side_effect = PermissionError("live force denied")
        with self.assertRaisesRegex(PermissionError, "live force denied"):
            self.supervise()
        self.assert_cleanup()

    def test_failed_final_reap_reports_cleanup_deadline_and_still_closes(self):
        self.process.poll.return_value = None
        self.tree_exists.side_effect = [RuntimeError("probe failed"), True]
        self.signal_tree.side_effect = PermissionError("live force denied")
        self.process.wait.side_effect = subprocess.TimeoutExpired(["trusted-worker"], 2)
        with self.assertRaises(admission.AdmissionFailure) as caught:
            self.supervise()
        self.assertEqual(caught.exception.error_type, "OwnedCleanupDeadline")
        self.assert_cleanup()

    def test_windows_denial_does_not_reap_or_reinterpret_the_job_inventory(self):
        error = PermissionError("Windows Job query denied")
        self.tree_exists.side_effect = error
        with patch.object(admission, "os", SimpleNamespace(name="nt")):
            with self.assertRaises(PermissionError) as caught:
                admission._owned_tree_call(self.process, self.tree_exists)
        self.assertIs(caught.exception, error)
        self.process.poll.assert_not_called()
        self.assertEqual(self.tree_exists.call_count, 1)


if __name__ == "__main__":
    unittest.main()
