"""Actual coordinator signals during immutable sealing and report-cache writes."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from experiments.workflows.checks import safe_environment

ROOT = Path(__file__).resolve().parents[1]

DRIVER = r"""
import json, os, signal
from pathlib import Path
from unittest.mock import patch
from tests.test_maintained_campaigns import MaintainedCampaignTests, configuration
from experiments.maintained_campaigns import common, report, run

phase = PHASE
fixture = MaintainedCampaignTests()
fixture.setUp()
try:
    config, _ = configuration(fixture.root / "inputs", cells=1, repeats=1)
    campaign = (fixture.root / "campaign").resolve()
    with patch.object(run, "supervise", side_effect=fixture.worker):
        first = run.run_study(config, campaign)
    assert first["passed"]
    prior = common.inventory(campaign / "sessions/session-0001")
    destination = campaign / "sessions/session-0002"
    original_handler = signal.getsignal(signal.SIGTERM)
    sent = False
    def interrupt():
        global sent
        if not sent:
            sent = True
            os.kill(os.getpid(), signal.SIGTERM)
    original_seal, original_dump = common.seal, common.dump
    original_reconstruct, original_write = report.reconstruct, Path.write_bytes
    def seal(path, *args, **kwargs):
        if phase == "seal" and Path(path) == destination:
            interrupt()
        return original_seal(path, *args, **kwargs)
    def reconstruct(*args, **kwargs):
        if phase == "reconstruct":
            interrupt()
        return original_reconstruct(*args, **kwargs)
    def dump(path, value):
        if phase == "json-cache" and Path(path) == destination / "report.json":
            interrupt()
        return original_dump(path, value)
    def write(path, *args, **kwargs):
        if phase == "markdown-cache" and path == destination / "report.md":
            interrupt()
        return original_write(path, *args, **kwargs)
    with patch.object(common, "seal", side_effect=seal), \
            patch.object(common, "dump", side_effect=dump), \
            patch.object(report, "reconstruct", side_effect=reconstruct), \
            patch.object(Path, "write_bytes", new=write), \
            patch.object(run, "supervise", side_effect=AssertionError("New dispatch")):
        final = run.resume(campaign)
    assert sent and final["passed"]
    assert final["sessions"][-1]["scheduled_slots"] == 0
    assert common.inventory(campaign / "sessions/session-0001") == prior
    # A request after the final dispatch does not mutate sealed scientific completion.
    assert final["sessions"][-1]["status"] == "completed"
    assert common.read(destination / "report.json") == original_reconstruct(campaign)
    assert (destination / "report.md").read_bytes() == report.markdown(final).encode("utf-8")
    assert signal.getsignal(signal.SIGTERM) == original_handler
    print(json.dumps({"phase": phase, "sealed": True, "both_caches_complete": True,
                      "accepted_prior_unchanged": True, "handlers_restored": True}))
finally:
    fixture.tearDown()
"""


class CampaignFinalizationTests(unittest.TestCase):
    def test_actual_term_preserves_sealed_completion_and_both_reports(self):
        for phase in ("seal", "reconstruct", "json-cache", "markdown-cache"):
            with self.subTest(phase=phase):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-E",
                        "-s",
                        "-S",
                        "-c",
                        "PHASE=" + repr(phase) + "\n" + DRIVER,
                    ],
                    cwd=ROOT,
                    env=safe_environment(),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                evidence = json.loads(result.stdout)
                self.assertEqual(evidence["phase"], phase)
                self.assertTrue(evidence["both_caches_complete"])
                self.assertTrue(evidence["accepted_prior_unchanged"])
                self.assertTrue(evidence["handlers_restored"])


if __name__ == "__main__":
    unittest.main()
