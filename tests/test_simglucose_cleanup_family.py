"""Fixed fake ownership clocks across the related cleanup adapters; no OS I/O."""

import io
import unittest
from unittest import mock

from experiments.simglucose_audit import (
    gh_error_review,
    gh_verifier_probe,
    intake_collector,
    pbs_intake,
    pbs_production_inspection,
    retained_source_review,
    verifier_preparation,
)

DEADLINE_ADAPTERS = (
    (pbs_intake, False),
    (retained_source_review, True),
    (gh_verifier_probe, True),
    (verifier_preparation, False),
)


class Clock:
    def __init__(self, start=0.0):
        self.value, self.sleeps = start, []

    def now(self):
        return self.value

    def sleep(self, seconds):
        if not 0 <= seconds <= 0.005:
            raise AssertionError("bounded nonnegative observation sleep")
        self.sleeps.append(seconds)
        self.value += seconds


def process():
    value = mock.Mock(pid=12345, returncode=0)
    value.poll.side_effect = lambda: value.returncode
    value.wait.side_effect = lambda timeout: value.returncode
    value.stdout, value.stdin = io.BytesIO(), io.BytesIO()
    return value


class CleanupFamilyTests(unittest.TestCase):
    def test_deadline_adapters_wait_for_delayed_empty_without_promoting_forced_receipt(self):
        for module, _close_on_failure in DEADLINE_ADAPTERS:
            with self.subTest(module=module.__name__):
                child, clock = process(), Clock()
                with (
                    mock.patch.object(module.time, "monotonic", side_effect=clock.now),
                    mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
                    mock.patch.object(
                        module.platform_process,
                        "tree_exists",
                        side_effect=lambda _: clock.value < 0.01,
                    ),
                    mock.patch.object(module.platform_process, "force_tree") as force,
                    mock.patch.object(module.platform_process, "close_tree") as close,
                ):
                    self.assertTrue(module._stop(child, None, None, True, 0.05))
                self.assertTrue(clock.sleeps)
                self.assertLess(clock.value, 0.05)
                force.assert_called_once_with(child)
                close.assert_called_once_with(child)
                self.assertTrue(child.stdout.closed and child.stdin.closed)

    def test_deadline_adapters_refuse_persistent_or_expired_group(self):
        for module, close_on_failure in DEADLINE_ADAPTERS:
            for start in (0.0, 1.0):
                with self.subTest(module=module.__name__, start=start):
                    child, clock = process(), Clock(start)
                    with (
                        mock.patch.object(module.time, "monotonic", side_effect=clock.now),
                        mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
                        mock.patch.object(
                            module.platform_process, "tree_exists", return_value=True
                        ),
                        mock.patch.object(module.platform_process, "force_tree") as force,
                        mock.patch.object(module.platform_process, "close_tree") as close,
                        self.assertRaisesRegex(ValueError, "^owned-cleanup-failed$"),
                    ):
                        module._stop(child, None, None, True, 0.02)
                    self.assertGreaterEqual(clock.value, 0.02)
                    self.assertLessEqual(len(clock.sleeps), 5)
                    if start:
                        self.assertEqual(clock.sleeps, [])
                    force.assert_called_once_with(child)
                    self.assertEqual(close.call_count, int(close_on_failure))
                    self.assertTrue(child.stdout.closed and child.stdin.closed)

    def test_deadline_adapters_keep_wait_join_and_observation_errors_sticky(self):
        for module, _close_on_failure in DEADLINE_ADAPTERS:
            for fault in ("wait", "join", "observation"):
                with self.subTest(module=module.__name__, fault=fault):
                    child, reader = process(), None
                    if fault == "wait":
                        child.wait.side_effect = module.subprocess.TimeoutExpired("invented", 0.01)
                    if fault == "join":
                        reader = mock.Mock(ident=1)
                        reader.join.side_effect = RuntimeError("invented join refusal")
                        reader.is_alive.return_value = False
                    with (
                        mock.patch.object(module.time, "monotonic", return_value=0),
                        mock.patch.object(
                            module.platform_process, "tree_exists", return_value=False
                        ) as tree,
                        mock.patch.object(module.platform_process, "close_tree"),
                        self.assertRaisesRegex(ValueError, "^owned-cleanup-failed$"),
                    ):
                        if fault == "observation":
                            tree.side_effect = OSError("invented observation refusal")
                        module._stop(child, reader, None, True, 0.05)
                    self.assertTrue(child.stdout.closed and child.stdin.closed)

    def test_error_review_delegates_to_the_qualified_retained_stop(self):
        self.assertIs(gh_error_review.previous, retained_source_review)
        self.assertIs(gh_error_review.previous._stop, retained_source_review._stop)

    def test_original_stop_allowances_cover_delayed_empty_including_readerless_path(self):
        for name in ("intake-reader", "generated-reader"):
            with self.subTest(adapter=name):
                child, clock = process(), Clock()
                module = (
                    pbs_production_inspection if name == "generated-reader" else intake_collector
                )
                reader = mock.Mock() if name == "intake-reader" else None
                if reader is not None:
                    reader.is_alive.return_value = False
                with (
                    mock.patch.object(module.time, "monotonic", side_effect=clock.now),
                    mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
                    mock.patch.object(
                        module.platform_process,
                        "tree_exists",
                        side_effect=lambda _: clock.value < 0.01,
                    ),
                    mock.patch.object(module.platform_process, "force_tree") as force,
                    mock.patch.object(module.platform_process, "close_tree") as close,
                ):
                    if name == "generated-reader":
                        result = module._stop(child, 5)
                    else:
                        result = module._finish_process(child, reader, True)
                    self.assertIsNone(result)
                self.assertTrue(clock.sleeps)
                close.assert_called_once_with(child)
                if name == "generated-reader":
                    force.assert_called_once_with(child)
                else:
                    force.assert_not_called()  # Never signal a reaped intake leader.
                    self.assertTrue(child.stdout.closed)

    def test_stop_allowances_do_not_restart_after_wait_consumes_them(self):
        for module, seconds in ((intake_collector, 1), (pbs_production_inspection, 2)):
            with self.subTest(module=module.__name__):
                child, clock = process(), Clock()
                child.returncode = None

                def wait(timeout):
                    self.assertLessEqual(timeout, seconds)
                    clock.value = seconds + 0.1
                    child.returncode = -9
                    return -9

                child.wait.side_effect = wait
                with (
                    mock.patch.object(module.time, "monotonic", side_effect=clock.now),
                    mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
                    mock.patch.object(module.platform_process, "tree_exists", return_value=True),
                    mock.patch.object(module.platform_process, "force_tree"),
                    mock.patch.object(module.platform_process, "close_tree"),
                ):
                    if module is intake_collector:
                        result = module._finish_process(child, None, True)
                    else:
                        result = module._stop(child, 5)
                self.assertEqual(clock.sleeps, [])
                self.assertIn("owned-tree-remains", result)

    def test_reader_start_failure_uses_the_same_intake_stop_window(self):
        module, child, clock = intake_collector, process(), Clock()
        child.returncode = None

        def force(_child):
            self.assertIs(_child, child)
            child.returncode = -9

        with (
            mock.patch.object(module.time, "monotonic", side_effect=clock.now),
            mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
            mock.patch.object(module.platform_process, "spawn", return_value=child),
            mock.patch.object(module.platform_process, "force_tree", side_effect=force),
            mock.patch.object(module.platform_process, "close_tree") as close,
            mock.patch.object(
                module.platform_process, "tree_exists", side_effect=lambda _: clock.value < 0.01
            ),
            mock.patch.object(
                module.threading.Thread, "start", side_effect=RuntimeError("invented")
            ),
            mock.patch.object(module, "_finish_process", wraps=module._finish_process) as finish,
        ):
            result = module._supervise({"whole_seconds": 1, "case": "ok"})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["error"], "controller-protocol-failure")
        self.assertIsNone(result["owned_cleanup_error"])
        self.assertIsNone(result["receipt_sha256"])
        finish.assert_called_once_with(child, None, True)
        close.assert_called_once_with(child)
        self.assertTrue(child.stdout.closed and child.stdin.closed)

    def test_generated_finish_block_cannot_promote_complete_frame_after_forced_cleanup(self):
        module, child, clock = pbs_production_inspection, process(), Clock()
        child.returncode = None
        body = iter((b'{"status":"invented-core-completed"}', b""))
        child.stdout.fileno = lambda: 73

        def read(fd, _maximum):
            self.assertEqual(fd, 73)
            return next(body)

        def force(_child):
            self.assertIs(_child, child)
            # Even a late zero exit cannot erase the already reached deadline.
            child.returncode = 0

        calls = [0]

        def now():
            calls[0] += 1
            if calls[0] > 1 and clock.value < 0.31:
                clock.value = 0.31
            return clock.value

        with (
            mock.patch.object(module.time, "monotonic", side_effect=now),
            mock.patch.object(module.time, "sleep", side_effect=clock.sleep),
            mock.patch.object(module, "_identity", return_value={"invented": "source"}),
            mock.patch.object(module.platform_process, "spawn", return_value=child),
            mock.patch.object(module.platform_process, "force_tree", side_effect=force),
            mock.patch.object(module.platform_process, "close_tree"),
            mock.patch.object(
                module.platform_process, "tree_exists", side_effect=lambda _: clock.value < 0.32
            ),
            mock.patch.object(module.os, "read", side_effect=read),
        ):
            result = module._supervise("finish-block", "/invented/unused", 3.3)
        self.assertEqual(result["worker"], {"status": "invented-core-completed"})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["error"], "whole-budget")
        self.assertIsNone(result["issued_completion_pin"])
        self.assertIsNone(result["cleanup_error"])
        self.assertTrue(result["reader_joined"] and result["reader_eof"])
        self.assertLess(clock.value, 2.31)


if __name__ == "__main__":
    unittest.main()
