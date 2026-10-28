"""Cancellation cannot bypass the shared supervisor's ownership transitions."""

import ast
import inspect
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import storage


@unittest.skipUnless(os.name == "posix", "Real cancellation and group ownership require POSIX")
class SupervisionCancellationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.processes = []
        self.addCleanup(self.cleanup_workers)
        self.child = self.directory / "child.py"
        self.child.write_text(
            "import os, signal, sys, time\n"
            "from pathlib import Path\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "marker = Path(sys.argv[1])\n"
            "pending = marker.with_suffix('.pending')\n"
            "print('descendant ready', flush=True)\n"
            "pending.write_text(str(os.getpid())); pending.replace(marker)\n"
            "while True: time.sleep(0.01)\n"
        )
        self.marker = self.directory / "child.pid"
        self.leader = self.directory / "leader.py"
        self.leader.write_text(
            "import signal, subprocess, sys, time\n"
            "from pathlib import Path\n"
            "if sys.argv[1] == 'wait': signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            f"subprocess.Popen({[sys.executable, '-B', str(self.child), str(self.marker)]!r})\n"
            f"while not Path({str(self.marker)!r}).exists(): time.sleep(0.01)\n"
            "print('leader ready', flush=True)\n"
            "if sys.argv[1] == 'wait':\n"
            " while True: time.sleep(0.01)\n"
        )
        grace = patch.object(storage, "CLEANUP_GRACE_SECONDS", 0.1)
        grace.start()
        self.addCleanup(grace.stop)

    def cleanup_workers(self):
        for process in self.processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)

    def wait_for(self, predicate, message):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(predicate(), message)

    def live(self, pid):
        observed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False
        )
        state, error = observed.stdout.strip(), observed.stderr.strip()
        if observed.returncode == 0 and state and not error:
            return not state.startswith("Z")
        if observed.returncode == 1 and not state and not error:
            return False
        raise RuntimeError(f"Could not observe synthetic process {pid}: {observed!r}")

    def supervise(self, outcome="exit", timeout=5):
        original_spawn = storage.spawn
        self.logs = []

        def ready_spawn(*args, **kwargs):
            process = original_spawn(*args, **kwargs)
            self.processes.append(process)
            self.logs.append(kwargs["stdout"])
            self.wait_for(self.marker.exists, "Descendant did not publish readiness")
            return process

        with patch.object(storage, "spawn", side_effect=ready_spawn):
            return storage.supervise(
                [sys.executable, "-B", str(self.leader), outcome],
                self.directory / "worker.log",
                self.directory,
                os.environ.copy(),
                timeout,
            )

    def assert_released(self):
        pid = int(self.marker.read_text())
        self.wait_for(
            lambda: not self.live(pid), "Supervisor returned with a live owned descendant"
        )
        process = self.processes[-1]
        self.assertIsNotNone(process.returncode)
        with self.assertRaises(ChildProcessError):
            os.waitpid(process.pid, os.WNOHANG)
        self.assertTrue(self.logs[-1].closed)
        self.assertIn("descendant ready", (self.directory / "worker.log").read_text())

    def transition_line(self, phase):
        # Find ownership transitions structurally so the regression also targets
        # the pre-fix cleanup entry, before it changes its cancellation flag.
        source, first = inspect.getsourcelines(storage.supervise)
        function = ast.parse("".join(source)).body[0]
        scoped = next(node for node in function.body if isinstance(node, ast.Try))
        logging = next(node for node in scoped.body if isinstance(node, ast.With))
        owned = next(node for node in logging.body if isinstance(node, ast.Try))
        if phase == "cleanup_entry":
            return first - 1 + owned.finalbody[0].lineno
        spawn = next(
            index
            for index, node in enumerate(owned.body)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "spawn"
        )
        return first - 1 + owned.body[spawn + 1].lineno

    def exercise_transition(self, phase):
        target = self.transition_line(phase)
        delivered = False

        def cancel(frame, event, _arg):
            nonlocal delivered
            if (
                frame.f_code is storage.supervise.__code__
                and event == "line"
                and frame.f_lineno == target
                and not delivered
            ):
                delivered = True
                signal.raise_signal(signal.SIGTERM)
                signal.raise_signal(signal.SIGINT)
            return cancel

        handlers = {value: signal.getsignal(value) for value in storage.handled_signals()}
        previous_trace = sys.gettrace()
        try:
            sys.settrace(cancel)
            result = self.supervise()
        finally:
            sys.settrace(previous_trace)
        self.assertTrue(delivered)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["signal"], signal.SIGTERM)
        self.assertEqual({value: signal.getsignal(value) for value in handlers}, handlers)
        self.assert_released()

    def test_cleanup_entry_cancellation_cannot_release_a_live_descendant(self):
        self.exercise_transition("cleanup_entry")

    def test_cancellation_after_spawn_assignment_keeps_ownership(self):
        self.exercise_transition("spawn_return")

    def test_timeout_preserves_original_command_and_budget_after_cleanup(self):
        with self.assertRaises(subprocess.TimeoutExpired) as expired:
            self.supervise("wait", timeout=0.05)
        self.assertEqual(expired.exception.timeout, 0.05)
        self.assertEqual(expired.exception.cmd, [sys.executable, "-B", str(self.leader), "wait"])
        self.assert_released()

    def test_failed_reap_after_reported_force_is_bounded_and_closes_ownership(self):
        owned_pid = self.directory / "owned.pid"
        command = [sys.executable, "-B", str(self.child), str(self.marker)]
        script = (
            "import json, os, signal, subprocess, time\n"
            "from pathlib import Path\n"
            "from unittest.mock import patch\n"
            "from experiments.catalogue import storage\n"
            f"process = storage.spawn({command!r}, stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL)\n"
            f"pid_marker = Path({str(owned_pid)!r})\n"
            "pending = pid_marker.with_suffix('.pending')\n"
            "pending.write_text(str(process.pid)); pending.replace(pid_marker)\n"
            "try:\n"
            " deadline = time.monotonic() + 5\n"
            f" while not Path({str(self.marker)!r}).exists():\n"
            "  if time.monotonic() >= deadline: raise RuntimeError('Worker not ready')\n"
            "  time.sleep(0.01)\n"
            " with patch.object(storage, 'CLEANUP_GRACE_SECONDS', 0), "
            "patch.object(storage, 'CLEANUP_REAP_SECONDS', 0.05, create=True), "
            "patch.object(storage, 'force_tree'), "
            "patch.object(storage, 'close_tree', wraps=storage.close_tree) as close:\n"
            "  try: storage.cleanup(process)\n"
            "  except subprocess.TimeoutExpired as error:\n"
            "   result = {'exception': type(error).__name__, 'timeout': error.timeout}\n"
            "  else: result = {'exception': None}\n"
            "  result['closed'] = close.call_count == 1\n"
            "  print(json.dumps(result), flush=True)\n"
            "finally:\n"
            " try: os.killpg(process.pid, signal.SIGKILL)\n"
            " except ProcessLookupError: pass\n"
            " process.wait(timeout=2)\n"
        )
        driver = subprocess.Popen(
            [sys.executable, "-B", "-c", script],
            cwd=storage.ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        self.processes.append(driver)
        try:
            try:
                output, error = driver.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                self.fail("Cleanup remained in an unbounded wait after reported force")
            self.assertEqual(driver.returncode, 0, output + error)
            self.assertEqual(
                json.loads(output), {"exception": "TimeoutExpired", "timeout": 0.05, "closed": True}
            )
        finally:
            # The external deadline must also clean the deliberately ineffective
            # force counterexample on an unfixed checkout.
            if owned_pid.exists():
                try:
                    os.killpg(int(owned_pid.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if driver.poll() is None:
                driver.communicate(timeout=3)
