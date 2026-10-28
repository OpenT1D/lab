"""Real resistant descendants and nested cleanup, without numerical simulation."""

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from experiments.campaigns.process import OUTER_GRACE_SECONDS, Control, supervise


@unittest.skipUnless(os.name == "posix", "Process-group ownership requires POSIX")
class CampaignProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.worker = self.directory / "worker.py"
        self.worker.write_text(
            "import os, signal, sys, time\n"
            "from pathlib import Path\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "Path(sys.argv[1]).write_text(str(os.getpid()))\n"
            "while True: time.sleep(0.02)\n"
        )

    def tearDown(self):
        # A failing process test must not leave its deliberately resistant child.
        marker = self.directory / "worker.pid"
        if marker.exists():
            try:
                os.kill(int(marker.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.temporary.cleanup()

    def live(self, pid):
        state = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=False
        ).stdout.strip()
        return bool(state) and not state.startswith("Z")

    def test_outer_grace_preserves_inner_ten_second_forcekill_and_reap(self):
        self.assertGreater(OUTER_GRACE_SECONDS, 10)
        marker = self.directory / "worker.pid"
        reaped = self.directory / "reaped"
        coordinator = self.directory / "coordinator.py"
        coordinator.write_text(
            "import os, signal, subprocess, time\n"
            "from pathlib import Path\n"
            "stopped = None\n"
            "def stop(signum, frame):\n"
            " global stopped\n"
            " if stopped is None: stopped = time.monotonic()\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            f"child = subprocess.Popen({[sys.executable, '-B', str(self.worker), str(marker)]!r}, "
            "start_new_session=True)\n"
            "try:\n"
            " while child.poll() is None:\n"
            "  if stopped is not None and time.monotonic() - stopped >= 10:\n"
            "   os.killpg(child.pid, signal.SIGKILL)\n"
            "   child.wait()\n"
            f"   Path({str(reaped)!r}).write_text('reaped')\n"
            "  time.sleep(0.02)\n"
            "finally:\n"
            " if child.poll() is None: os.killpg(child.pid, signal.SIGKILL)\n"
            " child.wait()\n"
        )
        control = Control()
        started = time.monotonic()
        code, error = supervise(
            [sys.executable, "-B", str(coordinator)], self.directory / "command.log", 1, control
        )
        self.assertEqual((code, error), (0, "WorkerDeadline"))
        self.assertTrue(reaped.is_file())
        self.assertFalse(self.live(int(marker.read_text())))
        self.assertGreaterEqual(time.monotonic() - started, 11)
        self.assertIsNone(control.active)

    def test_leader_exit_does_not_release_resistant_same_group_descendant(self):
        marker = self.directory / "worker.pid"
        leader = self.directory / "leader.py"
        leader.write_text(
            "import subprocess, time\n"
            "from pathlib import Path\n"
            f"subprocess.Popen({[sys.executable, '-B', str(self.worker), str(marker)]!r})\n"
            f"while not Path({str(marker)!r}).exists(): time.sleep(0.01)\n"
        )
        control = Control()
        code, error = supervise(
            [sys.executable, "-B", str(leader)],
            self.directory / "command.log",
            5,
            control,
            grace_seconds=0.2,
        )
        self.assertEqual((code, error), (0, "UnreapedWorkerGroup"))
        pid = int(marker.read_text())
        for _ in range(20):
            if not self.live(pid):
                break
            time.sleep(0.02)
        self.assertFalse(self.live(pid))
        self.assertIsNone(control.active)
