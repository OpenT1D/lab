"""Exercise actual subprocess signals, timeout and retained native checkpoints."""

import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd
from run import HERE

PROBE = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import run
from simglucose.simulation.sim_engine import SimObj
from simglucose.controller.basal_bolus_ctrller import BBController
from simglucose.simulation.env import T1DSimEnv
from simglucose.sensor.cgm import CGMSensor
from simglucose.actuator.pump import InsulinPump
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.simulation.scenario import CustomScenario
out = Path(sys.argv[2])
def paused(self):
    self.controller.reset()
    obs, reward, done, info = self.env.reset()
    for _ in range(3):
        action = self.controller.policy(obs, reward, done, **info)
        obs, reward, done, info = self.env.step(action)
    (out / 'ready').write_text('three completed intervals')
    time.sleep(60)
SimObj.simulate = paused
run.execute(out, timeout_seconds=float(sys.argv[3]))
"""


class InterruptionTests(unittest.TestCase):
    def test_signals_and_deadline_preserve_completed_native_intervals(self):
        for mode in [signal.SIGTERM, signal.SIGINT, signal.SIGKILL, "timeout"]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "run"
                with (Path(tmp) / "child.log").open("w+") as log:
                    child = subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            PROBE,
                            str(HERE),
                            str(output),
                            "3" if mode == "timeout" else "30",
                        ],
                        stdout=log,
                        stderr=log,
                    )
                    try:
                        deadline = time.monotonic() + 25
                        while not (output / "ready").exists():
                            if child.poll() is not None or time.monotonic() >= deadline:
                                log.seek(0)
                                self.fail(f"Probe did not reach completed intervals: {log.read()}")
                            time.sleep(0.05)
                        if mode != "timeout":
                            child.send_signal(mode)
                        self.assertNotEqual(child.wait(timeout=10), 0)
                        progress = pd.read_csv(output / "first/progress.csv")
                        self.assertEqual(len(progress), 4)
                        self.assertTrue(progress.BG.notna().all())
                        manifest = json.loads((output / "manifest.json").read_text())
                        if mode == signal.SIGKILL:
                            # A killed process cannot finalize metadata; its prefix survives.
                            self.assertEqual(manifest["status"], "started")
                        else:
                            self.assertEqual(manifest["status"], "interrupted")
                            reason = "timeout" if mode == "timeout" else mode.name
                            self.assertIn(reason, manifest["error"])
                            partial = output / "first/partial.csv"
                            self.assertEqual(
                                partial.read_bytes(), (output / "first/progress.csv").read_bytes()
                            )
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.wait()
