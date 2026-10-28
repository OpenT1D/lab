"""The trained-reference boundary retains missing and failed smoke attempts."""

import unittest
from unittest.mock import patch

from experiments.c1 import g2p2c_reference_readiness as readiness


class G2P2CReferenceReadinessTests(unittest.TestCase):
    def test_both_profiles_and_repeats_are_required(self):
        def report(source, profile, *, repeat):
            return {"profile": profile, "integration_gate_pass": True, "trace_sha256": profile}

        with patch.object(readiness, "verify_saved", side_effect=report):
            result = readiness.audit("source")
        self.assertTrue(result["technical_m1_boundary_pass"])
        self.assertFalse(result["eligible_m1_comparator"])
        self.assertEqual([len(profile["attempts"]) for profile in result["profiles"]], [2, 2])

        def changed_repeat(source, profile, *, repeat):
            if profile == "adult#002" and repeat:
                return {
                    "profile": profile,
                    "integration_gate_pass": True,
                    "trace_sha256": "changed",
                }
            return report(source, profile, repeat=repeat)

        with patch.object(readiness, "verify_saved", side_effect=changed_repeat):
            result = readiness.audit("source")
        self.assertFalse(result["technical_m1_boundary_pass"])
        self.assertFalse(result["profiles"][1]["fresh_process_repeat_identical"])

        def missing_repeat(source, profile, *, repeat):
            if profile == "adult#001" and repeat:
                raise FileNotFoundError("missing repeated smoke")
            return report(source, profile, repeat=repeat)

        with patch.object(readiness, "verify_saved", side_effect=missing_repeat):
            result = readiness.audit("source")
        self.assertFalse(result["technical_m1_boundary_pass"])
        self.assertEqual(result["profiles"][0]["attempts"][1]["status"], "unverifiable")

        def failed_verification(source, profile, *, repeat):
            if profile == "adult#002" and repeat:
                raise RuntimeError("checkpoint cannot be loaded")
            return report(source, profile, repeat=repeat)

        with patch.object(readiness, "verify_saved", side_effect=failed_verification):
            result = readiness.audit("source")
        self.assertFalse(result["technical_m1_boundary_pass"])
        self.assertEqual(result["profiles"][1]["attempts"][1]["status"], "unverifiable")
        self.assertEqual(result["profiles"][1]["attempts"][1]["error_type"], "RuntimeError")

        def malformed_report(source, profile, *, repeat):
            if profile == "adult#002" and repeat:
                return {"profile": profile, "integration_gate_pass": "yes"}
            return report(source, profile, repeat=repeat)

        with patch.object(readiness, "verify_saved", side_effect=malformed_report):
            result = readiness.audit("source")
        self.assertFalse(result["technical_m1_boundary_pass"])
        self.assertEqual(result["profiles"][1]["attempts"][1]["status"], "unverifiable")
        self.assertEqual(result["profiles"][1]["attempts"][1]["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
