"""Local tool ownership persists after its leader exits, without native runtimes."""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from experiments.catalogue.storage import ROOT


@unittest.skipUnless(os.name == "posix", "POSIX session ownership requires POSIX")
class LocalToolProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.child = self.directory / "child.py"
        self.child.write_text(
            "import os, signal, sys, time\n"
            "from pathlib import Path\n"
            "def stop(signum, frame):\n"
            " Path(sys.argv[2] + '.stopping').write_text('stopping')\n"
            " time.sleep(0.05)\n"
            " Path(sys.argv[2]).write_text('child cleanup completed')\n"
            " sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stop if sys.argv[3] == 'graceful' "
            "else signal.SIG_IGN)\n"
            "print('child-ready', flush=True)\n"
            "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
            "while True: time.sleep(0.02)\n"
        )

    def live(self, pid):
        state = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False
        ).stdout.strip()
        return bool(state) and not state.startswith("Z")

    def exercise(self, route, outcome, *, graceful=False):
        folder = self.directory / f"{route}-{outcome}"
        folder.mkdir()
        marker, partial = folder / "child.pid", folder / "partial.txt"
        leader = folder / "leader.py"
        child_args = [
            sys.executable,
            "-B",
            str(self.child),
            str(marker),
            str(partial),
            "graceful" if graceful else "resistant",
        ]
        leader.write_text(
            "import subprocess, sys, time\n"
            "from pathlib import Path\n"
            f"subprocess.Popen({child_args!r})\n"
            f"while not Path({str(marker)!r}).exists(): time.sleep(0.01)\n"
            "print('leader-ready', flush=True)\n"
            + ("time.sleep(60)\n" if outcome in {"timeout", "cancel", "spawn_cancel"} else "")
            + f"sys.exit({7 if outcome == 'crash' else 0})\n"
        )
        logfile, resultfile = folder / "tool.log", folder / "result.json"
        budget = 0.3 if outcome == "timeout" else 10
        invocation = (
            f"supervise({[sys.executable, '-B', str(leader)]!r}, "
            f"Path({str(logfile)!r}), ROOT, os.environ.copy(), {budget!r})"
            if route == "catalogue"
            else f"setup.install_project({[sys.executable, '-B', str(leader)]!r}, "
            f"Path({str(logfile)!r}), {str(folder / 'cache')!r}, True)"
        )
        script = (
            "import json, os, signal, subprocess, time\n"
            "from pathlib import Path\n"
            "from experiments.catalogue import storage\n"
            "from experiments.catalogue.storage import ROOT, supervise\n"
            "from experiments.setup import core as setup\n"
            "storage.CLEANUP_GRACE_SECONDS = 0.2\n"
            "previous = {s: signal.getsignal(s) for s in storage.handled_signals()}\n"
            "original_spawn = storage.spawn\n"
            "def observed_spawn(*args, **kwargs):\n"
            " process = original_spawn(*args, **kwargs)\n"
            f" Path({str(folder / 'leader.pid')!r}).write_text(str(process.pid))\n"
            + (
                " deadline = time.monotonic() + 10\n"
                f" while not Path({str(marker)!r}).exists() and time.monotonic() < deadline:\n"
                "  time.sleep(0.01)\n"
                f" assert Path({str(marker)!r}).exists(), 'Owned child did not start'\n"
                if outcome in {"timeout", "spawn_cancel"}
                else ""
            )
            + (" signal.raise_signal(signal.SIGTERM)\n" if outcome == "spawn_cancel" else "")
            + " return process\n"
            "storage.spawn = observed_spawn\n"
            # Keep the real installer entry and environment, shortening only its 1800s budget.
            "def short_budget(args, log, cwd, env, timeout):\n"
            f" return supervise(args, log, cwd, env, {budget!r})\n"
            "setup.supervise = short_budget\n"
            "try:\n"
            f" result = {invocation}\n"
            "except subprocess.TimeoutExpired:\n"
            " result = {'exception': 'TimeoutExpired'}\n"
            "assert all(signal.getsignal(s) == handler for s, handler in previous.items())\n"
            f"Path({str(resultfile)!r}).write_text(json.dumps(result))\n"
        )
        unrelated = subprocess.Popen([sys.executable, "-B", "-c", "import time;time.sleep(60)"])
        process = subprocess.Popen([sys.executable, "-B", "-S", "-c", script], cwd=ROOT)
        try:
            if outcome in {"cancel", "cleanup_cancel"}:
                ready = marker if outcome == "cancel" else Path(str(partial) + ".stopping")
                deadline = time.monotonic() + 10
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), "Owned child did not reach the cancellation phase")
                process.send_signal(signal.SIGTERM)
                process.send_signal(signal.SIGTERM)
            self.assertEqual(process.wait(timeout=15), 0)
            result = json.loads(resultfile.read_bytes())
            if outcome == "timeout":
                self.assertEqual(result, {"exception": "TimeoutExpired"})
            elif outcome in {"cancel", "spawn_cancel", "cleanup_cancel"}:
                self.assertEqual(result["status"], "interrupted")
                self.assertEqual(result["signal"], signal.SIGTERM)
            else:
                self.assertEqual(
                    result,
                    {
                        "status": "failed" if outcome == "crash" else "completed",
                        "exit_code": 7 if outcome == "crash" else 0,
                    },
                )
            self.assertTrue(marker.exists(), "Leader returned without starting the owned child")
            pid = int(marker.read_text())
            deadline = time.monotonic() + 2
            while self.live(pid) and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertFalse(self.live(pid), "Supervisor returned with an owned live descendant")
            self.assertIsNone(unrelated.poll(), "Supervisor terminated an unrelated process")
            self.assertIn("child-ready", logfile.read_text())
            if graceful:
                self.assertEqual(partial.read_text(), "child cleanup completed")
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            unrelated.terminate()
            unrelated.wait()
            owned = folder / "leader.pid"
            if owned.exists():
                try:
                    os.killpg(int(owned.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_normal_leader_exit_retains_ownership_in_both_tools(self):
        for route in ("catalogue", "setup"):
            with self.subTest(route=route):
                self.exercise(route, "normal")

    def test_crashed_leader_retains_ownership_in_both_tools(self):
        for route in ("catalogue", "setup"):
            with self.subTest(route=route):
                self.exercise(route, "crash")

    def test_deadline_stops_descendants_and_preserves_logs(self):
        for route in ("catalogue", "setup"):
            with self.subTest(route=route):
                self.exercise(route, "timeout")

    def test_cancellation_stops_descendants_and_preserves_logs(self):
        for route in ("catalogue", "setup"):
            with self.subTest(route=route):
                self.exercise(route, "cancel")

    def test_descendant_can_finish_partial_evidence_after_leader_exit(self):
        self.exercise("catalogue", "normal", graceful=True)

    def test_cancellation_during_launch_latches_until_ownership_is_assigned(self):
        self.exercise("catalogue", "spawn_cancel")

    def test_cancellation_during_cleanup_retains_handlers_until_descendants_finish(self):
        self.exercise("catalogue", "cleanup_cancel", graceful=True)


if __name__ == "__main__":
    unittest.main()
