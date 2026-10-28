"""Self-authored native-layout probes; no actual PhysioCGM records are used."""

import csv
import datetime as dt
import io
import unittest
from unittest.mock import patch

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.azt1d.data import history, target, validate_observations
from experiments.m3.physiocgm.intake import (
    EVENT,
    GLUCOSE,
    REQUIRED,
    TIME,
    convert_csv,
    validate_header,
)


class PhysioCGMIntakeTests(unittest.TestCase):
    def csv(self, records, *, header=None):
        header = list(REQUIRED) if header is None else header
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(records)
        return stream.getvalue().encode("utf-8")

    def row(self, minute, glucose="100", *, event="EGV", index="1"):
        timestamp = dt.datetime(2021, 1, 1) + dt.timedelta(minutes=minute)
        return [index, timestamp.isoformat(), event, glucose]

    def convert(self, records, *, header=None):
        header = list(REQUIRED) if header is None else header
        return convert_csv(
            self.csv(records, header=header),
            person="synthetic-external-1",
            expected_header=header,
            kind="synthetic",
        )

    def test_non_egv_events_cannot_supply_glucose_or_define_clock_origin(self):
        records = [
            ["", "unparsed device metadata", "Calibration", "999"],
            self.row(10, "101", index="7"),
            self.row(-100, "5", event="Meter", index="7"),
            self.row(15, "102", index="7"),
            ["", "invalid ignored timestamp", "egv", "103"],
        ]
        document, audit = self.convert(records)
        self.assertEqual(document["clock"], "local_elapsed")
        self.assertEqual(document["unit"], "mg/dL")
        self.assertEqual(document["bounds_us"], [0, 10 * MINUTE])
        self.assertEqual([row["time_us"] for row in document["rows"]], [0, 5 * MINUTE])
        self.assertEqual([row["value"] for row in document["rows"]], [101, 102])
        self.assertEqual([row["source_rows"] for row in document["rows"]], [[2], [4]])
        self.assertEqual(audit["source_record_count"], 5)
        self.assertEqual(audit["egv_record_count"], 2)
        self.assertEqual(audit["excluded_non_egv_records"], 3)
        self.assertEqual(audit["registered_origins"], 2)
        self.assertEqual(audit["duplicate_egv_records"], 0)
        self.assertEqual(audit["statuses"], {"measured": 2})
        self.assertFalse(audit["release_files_verified"])

    def test_lineage_counts_csv_records_not_device_index_or_physical_lines(self):
        header = list(REQUIRED) + ["Declared extra field"]
        document, _ = self.convert(
            [self.row(0, index="same") + ["first\nsecond"], self.row(5, index="same") + [""]],
            header=header,
        )
        self.assertEqual([row["source_rows"] for row in document["rows"]], [[1], [2]])

    def test_unavailable_and_censored_points_keep_origins_without_fabricated_numbers(self):
        signals = ["", "NA", "N/A", "Low", "High", "NaN", "Inf", "40", "400", "39", "401"]
        document, audit = self.convert([self.row(5 * i, v) for i, v in enumerate(signals)])
        expected = ["missing"] * 3 + ["censored_low", "censored_high"] + ["invalid"] * 6
        self.assertEqual([row["status"] for row in document["rows"]], expected)
        self.assertEqual(audit["registered_origins"], len(signals))
        self.assertTrue(all(row["value"] is None for row in document["rows"]))
        self.assertTrue(all(row["bound"] is None for row in document["rows"]))
        self.assertEqual(
            [row["time_us"] for row in document["rows"]], list(range(0, 55 * MINUTE, 5 * MINUTE))
        )

    def test_ordinary_numeric_spellings_remain_point_measurements(self):
        document, _ = self.convert(
            [
                self.row(0, "40.5"),
                self.row(5, "399.5"),
                self.row(10, "1.25e2"),
                self.row(15, " 100 "),
            ]
        )
        self.assertEqual([row["value"] for row in document["rows"]], [40.5, 399.5, 125, 100])
        self.assertTrue(all(row["status"] == "measured" for row in document["rows"]))

    def test_equivalent_decimal_duplicates_merge_with_complete_record_lineage(self):
        document, audit = self.convert(
            [self.row(0, "100"), self.row(0, "1e2"), self.row(0, "100.000"), self.row(5, "101")]
        )
        self.assertEqual(document["rows"][0]["status"], "measured")
        self.assertEqual(document["rows"][0]["value"], 100)
        self.assertEqual(document["rows"][0]["source_rows"], [1, 2, 3])
        self.assertEqual(audit["egv_record_count"], 4)
        self.assertEqual(audit["registered_origins"], 2)
        self.assertEqual(audit["duplicate_egv_records"], 2)

    def test_duplicate_conflicts_are_detected_before_float_rounding_and_stay_ambiguous(self):
        self.assertEqual(float("100.00000000000000000001"), float("100"))
        document, audit = self.convert(
            [self.row(0, "100"), self.row(0, "100.00000000000000000001"), self.row(0, "100")]
        )
        self.assertEqual(len(document["rows"]), 1)
        self.assertEqual(document["rows"][0]["status"], "ambiguous")
        self.assertIsNone(document["rows"][0]["value"])
        self.assertEqual(document["rows"][0]["source_rows"], [1, 2, 3])
        self.assertEqual(audit["statuses"], {"ambiguous": 1})

    def test_censor_duplicates_agree_but_censor_or_point_conflicts_remain_unscored(self):
        document, _ = self.convert(
            [self.row(0, "Low"), self.row(0, "Low"), self.row(5, "High"), self.row(5, "399")]
        )
        self.assertEqual([row["status"] for row in document["rows"]], ["censored_low", "ambiguous"])
        self.assertTrue(
            all(row["value"] is None and row["bound"] is None for row in document["rows"])
        )

    def test_exact_local_microseconds_survive_origin_subtraction_and_admin_endpoint(self):
        records = [
            ["1", "2021-01-01T23:59:00.123455", "EGV", "100"],
            ["2", "2021-01-02 00:04:00.123456", "EGV", "101"],
        ]
        document, _ = self.convert(records)
        self.assertEqual(document["rows"][1]["time_us"], 5 * MINUTE + 1)
        self.assertEqual(document["rows"][1]["available_us"], 5 * MINUTE + 1)
        self.assertEqual(document["rows"][1]["raw_time"], records[1][1])
        self.assertEqual(document["bounds_us"], [0, 10 * MINUTE + 1])

    def test_single_digit_hours_preserve_native_spelling_and_exact_elapsed_seconds(self):
        records = [["", f"2040-02-29 {hour}:05:01", "EGV", "100"] for hour in range(10)]
        records += [
            ["", "2040-02-29 10:05:00", "EGV", "101"],
            ["", "2040-02-29T23:59:59.999999", "EGV", "102"],
            ["", "2040-03-01 0:00:00", "EGV", "103"],
        ]
        document, audit = self.convert(records)
        rows = document["rows"]
        self.assertEqual([row["raw_time"] for row in rows], [record[1] for record in records])
        self.assertEqual(rows[9]["time_us"], 9 * 60 * MINUTE)
        self.assertEqual(rows[10]["time_us"], 10 * 60 * MINUTE - 1_000_000)
        self.assertEqual(rows[-1]["time_us"] - rows[-2]["time_us"], 1)
        self.assertTrue(all(row["available_us"] == row["time_us"] for row in rows))
        self.assertEqual(audit["format_variants"]["single_digit_hour_egv_records"], 11)

    def test_mixed_hour_spellings_merge_duplicates_without_losing_conflicts_or_lineage(self):
        records = [
            ["", "2040-01-01 9:55:00", "EGV", "100"],
            ["", "2040-01-01T09:55:00", "EGV", "1e2"],
            ["", "2040-01-01 9:55:00", "EGV", "101"],
            ["", "2040-01-01 10:00:00", "EGV", "102"],
        ]
        equivalent, _ = self.convert(records[:2])
        self.assertEqual(len(equivalent["rows"]), 1)
        self.assertEqual(equivalent["rows"][0]["status"], "measured")
        self.assertEqual(equivalent["rows"][0]["value"], 100)
        self.assertEqual(equivalent["rows"][0]["source_rows"], [1, 2])
        document, audit = self.convert(records)
        self.assertEqual(document["rows"][0]["source_rows"], [1, 2, 3])
        self.assertEqual(document["rows"][0]["raw_time"], records[0][1])
        self.assertEqual(document["rows"][0]["status"], "ambiguous")
        self.assertEqual(document["rows"][1]["time_us"], 5 * MINUTE)
        self.assertEqual(audit["format_variants"]["single_digit_hour_egv_records"], 2)
        with self.assertRaisesRegex(ValueError, "backwards"):
            self.convert(records[-1:] + records[:1])

    def test_single_hour_extension_does_not_guess_other_timestamp_formats(self):
        for timestamp in (
            "2040-01-01T9:05:00",
            "2040-01-01 9:05",
            "2040-01-01 9:5:00",
            "2040-01-01 9:05:0",
            "2040-1-01 9:05:00",
            "2040-01-01 9:05:00.1",
            "2040-01-01 9:05:00Z",
            "2040-01-01 9:05:00+01:00",
            "2040-01-01 24:00:00",
            "2040-02-30 9:05:00",
            "2040-01-01 ٩:05:00",
            "2040-01-01 9:05:00 ",
        ):
            with (
                self.subTest(timestamp=timestamp),
                self.assertRaisesRegex(ValueError, "Invalid local timestamp"),
            ):
                self.convert([["", timestamp, "EGV", "100"]])

    def test_microsecond_jitter_and_missing_origins_are_not_repaired_for_external_windows(self):
        records = [self.row(minute) for minute in range(0, 100, 5) if minute != 20]
        next(record for record in records if "T00:45:" in record[1])[1] += ".000001"
        next(record for record in records if "T01:30:" in record[1])[1] += ".000001"
        document, _ = self.convert(records)
        rows = validate_observations(document, document["person"], *document["bounds_us"])
        self.assertNotIn(20 * MINUTE, rows)
        self.assertNotIn(45 * MINUTE, rows)
        self.assertIn(45 * MINUTE + 1, rows)
        self.assertEqual(history(rows, 60 * MINUTE, 0, "evaluation"), (None, "history_gap"))
        self.assertEqual(target(rows, 60 * MINUTE, document["bounds_us"][1])["status"], "missing")

    def test_backward_egv_timestamps_fail_without_silent_sorting(self):
        with self.assertRaisesRegex(ValueError, "backwards"):
            self.convert([self.row(0), self.row(10), self.row(5)])

    def test_timezone_suffix_and_excess_fractional_precision_are_not_reinterpreted(self):
        for timestamp in (
            "2021-01-01T00:00:00Z",
            "2021-01-01T00:00:00+01:00",
            "2021-01-01T00:00:00.1234567",
            "2021-02-30T00:00:00",
        ):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                self.convert([["1", timestamp, "EGV", "100"]])

    def test_declared_header_order_and_extras_are_exact_but_may_be_reordered_explicitly(self):
        header = [EVENT, GLUCOSE, "Explicit extra", TIME, "Index"]
        raw = self.csv([["EGV", "123", "", "2021-01-01T00:00:00", "1"]], header=header)
        document, _ = convert_csv(raw, person="invented", expected_header=header, kind="synthetic")
        self.assertEqual(document["rows"][0]["value"], 123)
        with self.assertRaisesRegex(ValueError, "header differs"):
            convert_csv(raw, person="invented", expected_header=list(REQUIRED), kind="synthetic")

    def test_duplicate_missing_or_conflicting_unit_headers_fail(self):
        for header in (
            list(REQUIRED) + ["Index"],
            [name for name in REQUIRED if name != GLUCOSE],
            list(REQUIRED) + ["Glucose Value (mmol/L)"],
            list(REQUIRED) + ["", ""],
            list(REQUIRED) + [" "],
        ):
            with self.subTest(header=header), self.assertRaises(ValueError):
                validate_header(header)

    def test_one_declared_unnamed_column_is_checked_without_changing_record_lineage(self):
        original = [self.row(0), self.row(1, event="Calibration"), self.row(5)]
        for position in (0, 2, len(REQUIRED)):
            header = list(REQUIRED)
            header.insert(position, "")
            records = [row[:position] + [""] + row[position:] for row in original]
            with self.subTest(position=position):
                document, audit = self.convert(records, header=header)
                self.assertEqual([row["source_rows"] for row in document["rows"]], [[1], [3]])
                self.assertEqual([row["value"] for row in document["rows"]], [100, 100])
                self.assertEqual(
                    audit["format_variants"],
                    {
                        "empty_unnamed_column": True,
                        "empty_unnamed_records": 3,
                        "single_digit_hour_egv_records": 0,
                    },
                )
        _, audit = self.convert(original)
        self.assertFalse(audit["format_variants"]["empty_unnamed_column"])
        self.assertEqual(audit["format_variants"]["empty_unnamed_records"], 0)

    def test_nonempty_unnamed_field_fails_even_in_late_excluded_event_without_echoing_data(self):
        for event in ("EGV", "Calibration", "Meter"):
            for text in ("private-unexpected", " ", "\t", "\n", "0"):
                with self.subTest(event=event, text=text), self.assertRaises(ValueError) as error:
                    self.convert(
                        [self.row(0) + [""], self.row(5, event=event) + [text]],
                        header=list(REQUIRED) + [""],
                    )
                self.assertEqual(str(error.exception), "Declared unnamed column contains data")

    def test_unnamed_column_cannot_be_undeclared_or_have_ragged_rows(self):
        header = list(REQUIRED) + [""]
        with self.assertRaisesRegex(ValueError, "header differs"):
            convert_csv(
                self.csv([self.row(0) + [""]], header=header),
                person="invented",
                expected_header=list(REQUIRED),
                kind="synthetic",
            )
        for record in (self.row(0), self.row(0) + ["", ""]):
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, "record width"):
                self.convert([record], header=header)

    def test_ragged_even_excluded_records_malformed_csv_and_no_egv_fail(self):
        for records in (
            [self.row(0)[:-1]],
            [self.row(0) + ["extra"]],
            [["1", "ignored", "Calibration"]],
            [self.row(0, event="Calibration")],
            [],
        ):
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.convert(records)
        for raw in (self.csv([]) + b'1,"unfinished', b"\xff\xfe"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                convert_csv(
                    raw, person="invented", expected_header=list(REQUIRED), kind="synthetic"
                )

    def test_utf8_bom_is_accepted_without_changing_declared_header(self):
        raw = b"\xef\xbb\xbf" + self.csv([self.row(0)])
        document, _ = convert_csv(
            raw, person="invented", expected_header=list(REQUIRED), kind="synthetic"
        )
        self.assertEqual(document["rows"][0]["value"], 100)

    def test_human_kind_is_rejected_before_header_or_input_interpretation(self):
        with patch("experiments.m3.physiocgm.intake.validate_header") as header_check:
            with self.assertRaisesRegex(ValueError, "Human PhysioCGM"):
                convert_csv(object(), person="model", expected_header=None, kind="human")
            header_check.assert_not_called()

    def test_reserved_and_invalid_aliases_are_rejected(self):
        for person in ("model", "../invented", "", 1):
            with self.subTest(person=person), self.assertRaisesRegex(ValueError, "alias"):
                convert_csv(
                    self.csv([self.row(0)]),
                    person=person,
                    expected_header=list(REQUIRED),
                    kind="synthetic",
                )


if __name__ == "__main__":
    unittest.main()
