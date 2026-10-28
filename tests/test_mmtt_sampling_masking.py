"""Raw-row deletion before shared analyte parsing, with preserved failures."""

import csv
import io
import unittest

from experiments.mmtt_sampling.fixtures import example
from experiments.mmtt_sampling.masking import mask_csv
from experiments.observation_analysis.fixtures import csv_bytes
from experiments.observation_analysis.observations import COLUMNS, parse_csv


class SamplingMaskingTests(unittest.TestCase):
    def setUp(self):
        self.package, self.raw, _ = example()
        self.rows = list(csv.reader(io.StringIO(self.raw.decode())))[1:]

    def test_omitted_invalid_analytes_never_enter_shared_importer(self):
        expected, inventory = mask_csv(self.raw, self.package, [0, 60, 120])
        for row in self.rows:
            if float(row[3]) not in (0, 60, 120):
                row[4:] = ["NaN", "invalid glucose status", "not-a-number", "invalid status"]
        poisoned = csv_bytes(self.rows)
        self.assertFalse(parse_csv(poisoned, self.package)["valid"])
        actual, repeated_inventory = mask_csv(poisoned, self.package, [0, 60, 120])
        self.assertEqual(actual, expected)
        self.assertEqual(repeated_inventory, inventory)
        parsed = parse_csv(actual, self.package)
        self.assertTrue(parsed["valid"])
        self.assertEqual(len(parsed["visits"]), 10)
        self.assertEqual(sum(len(visit["rows"]) for visit in parsed["visits"]), 30)
        self.assertTrue(all(visit["omitted_rows"] == 3 for visit in inventory))

    def test_missing_interior_request_stays_a_preflight_failure(self):
        self.rows = [
            row
            for row in self.rows
            if not (row[0] == "invented-evaluation-01" and row[1] == "before" and row[3] == "60")
        ]
        masked, inventory = mask_csv(csv_bytes(self.rows), self.package, [0, 60, 120])
        self.assertTrue(parse_csv(masked, self.package)["valid"])
        failed = [visit for visit in inventory if visit["status"] != "complete"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["missing_requested_times_minutes"], [60])
        self.assertEqual(len(inventory), 10)

    def test_wholly_missing_visit_keeps_planned_identity_and_all_requests(self):
        self.rows = [
            row
            for row in self.rows
            if not (row[0] == "invented-evaluation-01" and row[1] == "before")
        ]
        masked, inventory = mask_csv(csv_bytes(self.rows), self.package, [0, 60, 120])
        failed = [visit for visit in inventory if visit["status"] != "complete"]
        self.assertEqual(len(inventory), 10)
        self.assertEqual(failed[0]["missing_requested_times_minutes"], [0, 60, 120])
        self.assertFalse(parse_csv(masked, self.package)["valid"])

    def test_invalid_framing_identity_and_time_structure_are_not_silently_filtered(self):
        for index, value in (
            (0, "undeclared"),
            (2, "other-challenge"),
            (3, "bad-clock"),
            (3, "NaN"),
            (3, "121"),
        ):
            rows = [row.copy() for row in self.rows]
            rows[1][index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                mask_csv(csv_bytes(rows), self.package, [0, 60, 120])
        with self.assertRaises(ValueError):
            mask_csv(csv_bytes(self.rows + [self.rows[0]]), self.package, [0, 60, 120])
        with self.assertRaises(ValueError):
            mask_csv(b"wrong,header\n", self.package, [0, 60, 120])

    def test_retained_values_are_preserved_without_interpolation_or_unit_conversion(self):
        self.rows[0][4] = " 5.500 "
        self.rows[0][6] = "0.200000"
        masked, _ = mask_csv(csv_bytes(self.rows), self.package, [0, 60, 120])
        rows = list(csv.reader(io.StringIO(masked.decode())))
        self.assertEqual(tuple(rows[0]), COLUMNS)
        self.assertEqual(rows[1], self.rows[0])
        self.assertEqual(len(rows), 31)


if __name__ == "__main__":
    unittest.main()
