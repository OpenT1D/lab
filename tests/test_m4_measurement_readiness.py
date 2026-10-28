"""BC-015 evidence gates, privacy boundary and artifact reconstruction."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.m4.measurement_readiness.run import (
    HERE,
    assess,
    digest,
    execute,
    protocol,
    reconstruct,
    write,
)


class MeasurementReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = protocol()
        cls.candidate = json.loads((HERE / "candidate-cit07.json").read_text())

    def test_cit07_catalogue_does_not_imply_joined_dynamic_cpeptide_or_access(self):
        result = assess(self.candidate, self.design)
        self.assertEqual(result["counts"], {"supported": 2, "unverified": 5, "contradicted": 1})
        self.assertEqual(
            result["requirements"]["early_and_late_cpeptide"]["decision"], "contradicted"
        )
        self.assertEqual(result["requirements"]["same_visit_dynamic_gic"]["decision"], "unverified")
        self.assertFalse(result["metadata_packet_for_design_review"])
        self.assertFalse(result["human_execution_authorized"])

    def test_complete_synthetic_metadata_can_only_become_reviewable(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["id"] = "synthetic-complete"
        candidate["access"] = "synthetic"
        for evidence in candidate["evidence"].values():
            evidence.update(
                finding="supported",
                basis="release_metadata",
                url="https://example.invalid/synthetic-metadata",
            )
        result = assess(candidate, self.design)
        self.assertEqual(result["counts"]["supported"], len(self.design["requirements"]))
        self.assertTrue(result["metadata_packet_for_design_review"])
        self.assertFalse(result["human_execution_authorized"])
        candidate["evidence"]["same_visit_dynamic_gic"]["basis"] = "catalogue"
        result = assess(candidate, self.design)
        self.assertFalse(result["metadata_packet_for_design_review"])
        self.assertEqual(result["requirements"]["same_visit_dynamic_gic"]["decision"], "unverified")

    def test_patient_fields_and_token_bearing_urls_are_rejected(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["participant_id"] = "private"
        with self.assertRaises(ValueError):
            assess(candidate, self.design)
        del candidate["participant_id"]
        candidate["evidence"]["same_visit_dynamic_gic"]["value"] = 123.0
        with self.assertRaises(ValueError):
            assess(candidate, self.design)
        del candidate["evidence"]["same_visit_dynamic_gic"]["value"]
        candidate["source_url"] += "?token=private"
        with self.assertRaises(ValueError):
            assess(candidate, self.design)

    def test_archive_reconstructs_and_rehashed_forged_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            archive = directory / "archive"
            self.assertEqual(execute(HERE / "candidate-cit07.json", archive), reconstruct(archive))
            with self.assertRaises(FileExistsError):
                execute(HERE / "candidate-cit07.json", archive)
            report = json.loads((archive / "report.json").read_text())
            report["human_execution_authorized"] = True
            write(archive / "report.json", report)
            manifest = json.loads((archive / "manifest.json").read_text())
            manifest["files"]["report.json"] = digest(archive / "report.json")
            write(archive / "manifest.json", manifest)
            with self.assertRaises(ValueError):
                reconstruct(archive)

    def test_extra_archive_file_and_linked_candidate_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            candidate_link = directory / "candidate.json"
            candidate_link.symlink_to(HERE / "candidate-cit07.json")
            with self.assertRaises(ValueError):
                execute(candidate_link, directory / "rejected")
            self.assertFalse((directory / "rejected").exists())
            archive = directory / "archive"
            execute(HERE / "candidate-cit07.json", archive)
            (archive / "extra.json").write_text("{}")
            with self.assertRaises(ValueError):
                reconstruct(archive)


if __name__ == "__main__":
    unittest.main()
