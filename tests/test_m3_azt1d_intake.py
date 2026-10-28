"""Synthetic-only tests for the AZT1D phase and native-meaning boundaries."""

import csv
import io
import unittest
from unittest.mock import patch

from experiments.m3.azt1d import intake

ORIGIN = "2001-01-01 00:00:00"
EXACT = {"numeric_boundary": "verified_exact", "reference": "synthetic convention"}
EXCLUDE = {
    "numeric_boundary": "exclude",
    "lower": 40,
    "upper": 400,
    "reference": "synthetic conservative boundary exclusion",
}


def native(rows, header=intake.HEADER):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(header)
    for time, glucose in rows:
        values = {column: "not interpreted" for column in header}
        values["EventDateTime"] = time
        values["CGM" if "CGM" in header else intake.MIXED_COLUMN] = glucose
        writer.writerow([values[column] for column in header])
    return output.getvalue().encode()


def convert(rows, **overrides):
    arguments = {
        "person": "synthetic-person",
        "origin_local": ORIGIN,
        "start_us": 0,
        "end_us": 3_600_000_000,
        "row_start": 1,
        "row_stop": len(rows) + 1,
        "policy": EXACT,
    }
    arguments.update(overrides)
    return intake.convert_csv(native(rows), **arguments)


class AZT1DIntakeTests(unittest.TestCase):
    def test_exact_microseconds_and_causal_metadata(self):
        result = convert(
            [
                (ORIGIN, "100"),
                ("2001-01-01T00:00:00.000001", "101.25"),
                ("2001-01-01 00:05:00.123456", "102"),
            ]
        )
        self.assertEqual(result["bounds_us"], [0, 3_600_000_000])
        self.assertEqual(result["clock"], "local_elapsed")
        self.assertEqual(result["unit"], "mg/dL")
        self.assertEqual([row["time_us"] for row in result["rows"]], [0, 1, 300_123_456])
        self.assertEqual(
            result["rows"][1],
            {
                "time_us": 1,
                "available_us": 1,
                "segment": "local",
                "raw_time": "2001-01-01T00:00:00.000001",
                "status": "measured",
                "value": 101.25,
                "bound": None,
                "source_rows": [2],
            },
        )

    def test_future_poison_is_neither_parsed_nor_returned(self):
        source = [(ORIGIN, "100"), ("2001-01-01 00:05:00", "private-future-poison")]
        with patch.object(intake, "_signal", wraps=intake._signal) as parse:
            result = convert(source, row_stop=2, end_us=300_000_000)
        self.assertEqual(parse.call_count, 1)
        self.assertEqual(parse.call_args.args[0], "100")
        self.assertNotIn("private-future-poison", str(result))
        changed = [(ORIGIN, "100"), ("2001-01-01 00:05:00", "9e99999999")]
        self.assertEqual(result, convert(changed, row_stop=2, end_us=300_000_000))

    def test_past_poison_is_not_parsed_for_later_block(self):
        source = [(ORIGIN, "private-past-poison"), ("2001-01-01 00:05:00", "101")]
        with patch.object(intake, "_signal", wraps=intake._signal) as parse:
            result = convert(source, row_start=2, start_us=300_000_000)
        self.assertEqual(parse.call_count, 1)
        self.assertEqual(result["rows"][0]["source_rows"], [2])

    def test_numeric_equal_duplicates_preserve_all_source_rows(self):
        result = convert([(ORIGIN, "100"), (ORIGIN, "100.0"), (ORIGIN, "1e2")])
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["status"], "measured")
        self.assertEqual(result["rows"][0]["source_rows"], [1, 2, 3])

    def test_conflicts_remain_ambiguous_even_if_last_matches_first(self):
        for readings in [("100", "101", "100"), ("100", "NA", "100"), ("0", "-1", "0")]:
            with self.subTest(readings=readings):
                row = convert([(ORIGIN, value) for value in readings])["rows"][0]
                self.assertEqual(
                    (row["status"], row["value"], row["bound"]), ("ambiguous", None, None)
                )
                self.assertEqual(row["source_rows"], [1, 2, 3])

    def test_float_rounding_does_not_hide_native_duplicate_conflict(self):
        row = convert([(ORIGIN, "100"), (ORIGIN, "100.00000000000000001")])["rows"][0]
        self.assertEqual(row["status"], "ambiguous")

    def test_missing_nonfinite_and_overflow_are_safe_statuses(self):
        values = [
            "",
            " NA ",
            "n/a",
            "NaN",
            "inf",
            "-Infinity",
            "1e99999999",
            "1e-99999999",
            "0",
            "-2",
        ]
        source = [(f"2001-01-01 00:00:{i:02d}", value) for i, value in enumerate(values)]
        result = convert(source)
        self.assertEqual(
            [row["status"] for row in result["rows"]], ["missing"] * 3 + ["invalid"] * 7
        )
        self.assertTrue(all(row["value"] is None for row in result["rows"]))

    def test_numeric_boundaries_excluded_without_censor_claim(self):
        source = [
            (f"2001-01-01 00:00:{i:02d}", value)
            for i, value in enumerate(["39", "40", "41", "399", "400", "401"])
        ]
        rows = convert(source, policy=EXCLUDE)["rows"]
        self.assertEqual(
            [row["status"] for row in rows],
            ["invalid", "invalid", "measured", "measured", "invalid", "invalid"],
        )
        self.assertTrue(all(row["bound"] is None for row in rows))

    def test_censor_tokens_require_explicit_bound_policy(self):
        source = [(ORIGIN, "LOW"), ("2001-01-01 00:05:00", "HIGH")]
        self.assertEqual([row["status"] for row in convert(source)["rows"]], ["invalid"] * 2)
        policy = {
            **EXACT,
            "tokens": {
                "LOW": {"status": "censored_low", "bound": 40},
                "HIGH": {"status": "censored_high", "bound": 400},
            },
        }
        rows = convert(source, policy=policy)["rows"]
        self.assertEqual([row["status"] for row in rows], ["censored_low", "censored_high"])
        self.assertEqual([row["bound"] for row in rows], [40, 400])
        self.assertTrue(all(row["value"] is None for row in rows))

    def test_mixed_reordered_schema_never_coerces_to_cgm(self):
        header = (intake.MIXED_COLUMN, *reversed(intake.HEADER[:-1]))
        with patch.object(intake, "_signal", side_effect=AssertionError("must not parse")):
            result = intake.convert_csv(
                native([(ORIGIN, "123"), (ORIGIN, "999")], header),
                person="synthetic-person",
                origin_local=ORIGIN,
                start_us=0,
                end_us=300_000_000,
                row_start=1,
                row_stop=3,
                policy=EXACT,
            )
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["status"], "unsupported")
        self.assertIsNone(result["rows"][0]["value"])
        self.assertEqual(result["rows"][0]["source_rows"], [1, 2])

    def test_time_block_and_complete_duplicate_group_must_match(self):
        source = [(ORIGIN, "100"), ("2001-01-01 00:05:00", "101"), ("2001-01-01 00:05:00", "101")]
        for override in [
            {"row_stop": 3},
            {"row_start": 3, "start_us": 300_000_000},
            {"row_stop": 2},
            {"row_stop": 4, "end_us": 300_000_000},
            {"row_stop": 5},
        ]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                convert(source, **override)
        self.assertEqual(len(convert(source, row_stop=2, end_us=300_000_000)["rows"]), 1)
        self.assertEqual(len(convert(source, row_start=2, start_us=300_000_000)["rows"]), 1)

    def test_empty_block_has_unique_declared_native_slice(self):
        source = [(ORIGIN, "100"), ("2001-01-01 00:05:00", "101")]
        result = convert(source, start_us=1, end_us=100, row_start=2, row_stop=2)
        self.assertEqual(result["rows"], [])
        with self.assertRaises(ValueError):
            convert(source, start_us=1, end_us=100, row_start=1, row_stop=1)

    def test_bad_future_shape_or_time_still_blocks_without_glucose_parse(self):
        examples = [
            native([(ORIGIN, "100")]) + b"2001-01-01 00:05:00,private-shape-poison\n",
            native([(ORIGIN, "100"), ("private-time-poison", "private-glucose-poison")]),
            native([(ORIGIN, "100"), ("2000-12-31 23:59:59", "private-glucose-poison")]),
        ]
        for raw in examples:
            with self.subTest(raw=raw[:0]), patch.object(intake, "_signal") as parse:
                with self.assertRaises(ValueError) as caught:
                    intake.convert_csv(
                        raw,
                        person="synthetic-person",
                        origin_local=ORIGIN,
                        start_us=0,
                        end_us=1,
                        row_start=1,
                        row_stop=2,
                        policy=EXACT,
                    )
                parse.assert_not_called()
                self.assertNotIn("poison", str(caught.exception))

    def test_time_formats_and_backwards_order_are_not_repaired(self):
        for time in [
            "2001-01-01",
            "2001-01-01 00:00",
            "2001-01-01T00:00:00Z",
            "2001-01-01T00:00:00+00:00",
            "2001-01-01 00:00:00.0000001",
            "2001-02-30 00:00:00",
            "2001-01-01 00:00:60",
        ]:
            with self.subTest(time=time), self.assertRaises(ValueError):
                convert([(time, "100")])
        with self.assertRaises(ValueError):
            convert([("2001-01-01 00:05:00", "101"), (ORIGIN, "100")])

    def test_origin_is_bound_to_first_source_timestamp_in_every_phase(self):
        source = [(ORIGIN, "100"), ("2001-01-01 00:05:00", "101")]
        for origin in ["2000-12-31 23:59:59.999999", "2001-01-01 00:00:00.000001"]:
            with self.subTest(origin=origin), self.assertRaisesRegex(ValueError, "origin"):
                convert(source, origin_local=origin, row_start=2, start_us=300_000_000)

    def test_invalid_policy_and_arguments_fail_without_patient_content(self):
        policies = [
            None,
            {},
            {"numeric_boundary": "verified_exact"},
            {**EXACT, "lower": 40},
            {**EXCLUDE, "upper": 40},
            {**EXCLUDE, "lower": True},
            {**EXCLUDE, "upper": float("inf")},
            {**EXACT, "tokens": {"LOW": {"status": "measured", "bound": 40}}},
            {**EXACT, "tokens": {"LOW": {"status": "censored_low", "bound": -1}}},
        ]
        for policy in policies:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                convert([(ORIGIN, "100")], policy=policy)
        for args in [
            {"start_us": True},
            {"row_start": True},
            {"person": "../unsafe"},
            {"start_us": -1},
            {"end_us": 0},
            {"row_start": 0},
            {"row_stop": 0},
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                convert([(ORIGIN, "100")], **args)

    def test_unreviewed_schema_and_encoding_fail_safely(self):
        raws = [b"wrong,header\n", b"", b"\xff", native([])]
        for raw in raws:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                intake.convert_csv(
                    raw,
                    person="synthetic-person",
                    origin_local=ORIGIN,
                    start_us=0,
                    end_us=1,
                    row_start=1,
                    row_stop=1,
                    policy=EXACT,
                )


if __name__ == "__main__":
    unittest.main()
