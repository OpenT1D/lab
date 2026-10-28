"""Guard the public registry audit against false pairing and silent relabeling."""

import copy
import unittest

from experiments.m4.measurement_readiness.registry_aggregate import assess_record


class RegistryAggregateTest(unittest.TestCase):
    def setUp(self):
        self.protocol = {
            "source": {"nct_id": "NCTfixture"},
            "required_outcome_title_prefixes": {
                "glucose": "Glucose MMTT",
                "insulin": "Insulin MMTT",
                "c_peptide": "C-peptide MMTT",
            },
            "expected_units": {"glucose": "mg/dL", "insulin": "µU/mL", "c_peptide": "ng/mL"},
            "expected_visit_labels": ["day 75 - Transplant 1"],
            "expected_sample_labels": ["Basal", "120 min"],
        }
        outcomes = []
        for signal, title in self.protocol["required_outcome_title_prefixes"].items():
            outcomes.append(
                {
                    "title": title,
                    "unitOfMeasure": self.protocol["expected_units"][signal],
                    "groups": [
                        {"id": "OG000", "title": "Treatment"},
                        {"id": "OG001", "title": "Control"},
                    ],
                    "classes": [
                        self.row("Basal - day 75 - Transplant 1"),
                        self.row("120 min - day 75 - Transplant 2"),
                    ],
                }
            )
        self.record = {
            "protocolSection": {"identificationModule": {"nctId": "NCTfixture"}},
            "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": outcomes}},
        }

    @staticmethod
    def row(label):
        return {
            "title": label,
            "denoms": [
                {
                    "units": "Participants",
                    "counts": [
                        {"groupId": "OG000", "value": "10"},
                        {"groupId": "OG001", "value": "8"},
                    ],
                }
            ],
            "categories": [
                {
                    "measurements": [
                        {"groupId": "OG000", "value": "1.0"},
                        {"groupId": "OG001", "value": "2.0"},
                    ]
                }
            ],
        }

    def test_mislabelled_visit_does_not_become_a_complete_series(self):
        report = assess_record(self.record, self.protocol)
        self.assertEqual(report["common_expected_labels"], 1)
        self.assertEqual(report["common_labels"], 2)
        for channel in report["published_group_summaries"].values():
            self.assertEqual(
                channel["missing_expected_labels"], ["120 min - day 75 - Transplant 1"]
            )
            self.assertEqual(channel["unexpected_labels"], ["120 min - day 75 - Transplant 2"])
        self.assertFalse(report["human_execution_authorized"])

    def test_different_denominators_are_reported_not_paired(self):
        record = copy.deepcopy(self.record)
        cpeptide = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][2]
        cpeptide["classes"][0]["denoms"][0]["counts"][0]["value"] = "9"
        report = assess_record(record, self.protocol)
        self.assertEqual(
            report["group_count_disagreements"],
            [
                {
                    "label": "Basal - day 75 - Transplant 1",
                    "group": "OG000",
                    "counts": {"glucose": 10, "insulin": 10, "c_peptide": 9},
                }
            ],
        )

    def test_missing_group_summary_is_rejected(self):
        record = copy.deepcopy(self.record)
        insulin = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][1]
        insulin["classes"][0]["categories"][0]["measurements"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete insulin group summary"):
            assess_record(record, self.protocol)


if __name__ == "__main__":
    unittest.main()
