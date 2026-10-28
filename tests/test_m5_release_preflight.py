"""OT-027 synthetic visit-linkage checks and archive integrity."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.m5.release_preflight.run import HERE, assess, digest, execute, reconstruct, write


class M5ReleasePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.intent = json.loads((HERE / "intent-synthetic.json").read_text())
        cls.packet = json.loads((HERE / "packet-synthetic.json").read_text())

    def test_complete_incomplete_and_intervening_treatment_remain_visible(self):
        report = assess(self.intent, self.packet)
        self.assertEqual(report["participant_count"], 3)
        self.assertEqual(report["candidate_linkage_count"], 2)
        self.assertEqual(report["intervening_infusion_count"], 1)
        self.assertEqual(report["participants"][1]["intervening_infusion_days"], [150])
        self.assertEqual(
            report["participants"][2]["issues"],
            ["seven_consecutive_previsit_diary_days_unverified"],
        )
        self.assertFalse(report["human_execution_authorized"])

    def test_ambiguous_landmark_and_below_limit_sample_cannot_pass(self):
        packet = copy.deepcopy(self.packet)
        packet["mmtt"].append(copy.deepcopy(packet["mmtt"][0]))
        packet["mmtt"][-1]["visit_id"] = "V3"
        report = assess(self.intent, packet)
        self.assertIn("missing_or_ambiguous_day75_mmtt", report["participants"][0]["issues"])
        packet["mmtt"].pop()
        packet["mmtt"][0]["samples"][1]["c_peptide"] = "below_limit"
        report = assess(self.intent, packet)
        self.assertIn("missing_observed_paired_mmtt_samples", report["participants"][0]["issues"])

    def test_first_infusion_clock_and_person_link_are_checked(self):
        packet = copy.deepcopy(self.packet)
        packet["infusions"][0]["day"] = 1
        report = assess(self.intent, packet)
        self.assertIn("first_or_duplicate_infusion", report["participants"][0]["issues"])
        packet["infusions"][0]["alias"] = "SYN999"
        with self.assertRaisesRegex(ValueError, "outside the roster"):
            assess(self.intent, packet)

    def test_summary_without_daily_coverage_is_unverified(self):
        packet = copy.deepcopy(self.packet)
        packet["insulin"][0]["diary_days"] = []
        report = assess(self.intent, packet)
        self.assertIn(
            "seven_consecutive_previsit_diary_days_unverified", report["participants"][0]["issues"]
        )
        packet["insulin"][0]["semantics"] = "pump_delivered_u"
        with self.assertRaisesRegex(ValueError, "reported daily total"):
            assess(self.intent, packet)

    def test_future_function_and_composite_predictor_fields_are_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet["mmtt"][0]["beta_score"] = 7
        with self.assertRaisesRegex(ValueError, "MMTT visit"):
            assess(self.intent, packet)
        del packet["mmtt"][0]["beta_score"]
        packet["participants"][0]["day365_c_peptide"] = "observed"
        with self.assertRaisesRegex(ValueError, "Participant"):
            assess(self.intent, packet)

    def test_human_intent_is_rejected_before_packet_is_read(self):
        with tempfile.TemporaryDirectory() as root:
            intent = Path(root) / "intent.json"
            write(intent, {**self.intent, "data_kind": "human"})
            with self.assertRaisesRegex(ValueError, "Only the invented"):
                execute(intent, Path(root) / "does-not-exist.json", Path(root) / "archive")
            self.assertFalse((Path(root) / "archive").exists())

    def test_archive_reconstructs_and_rehashed_forgery_fails(self):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "archive"
            report = execute(
                HERE / "intent-synthetic.json", HERE / "packet-synthetic.json", archive
            )
            self.assertEqual(report, reconstruct(archive))
            altered = json.loads((archive / "report.json").read_text())
            altered["human_execution_authorized"] = True
            write(archive / "report.json", altered)
            manifest = json.loads((archive / "manifest.json").read_text())
            manifest["files"]["report.json"] = digest(archive / "report.json")
            write(archive / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "differs"):
                reconstruct(archive)


if __name__ == "__main__":
    unittest.main()
