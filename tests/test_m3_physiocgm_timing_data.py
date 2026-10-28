"""Invented observations for causal integer-time matching and exact compatibility."""

import copy
import unittest

from experiments.m3.azt1d.data import history as exact_history
from experiments.m3.azt1d.data import target as exact_target
from experiments.m3.physiocgm_timing.common import MINUTE, RADII_US, SECOND
from experiments.m3.physiocgm_timing.data import TimeIndex


def row(time, **changes):
    value = {
        "time_us": time,
        "available_us": time,
        "segment": "invented-clock",
        "raw_time": f"invented-{time}",
        "status": "measured",
        "value": 100.0 + (time // MINUTE) % 20,
        "bound": None,
        "source_rows": [1],
    }
    value.update(changes)
    return value


def observations(points):
    """Assign unique invented source rows without relaxing duplicate-time checks."""
    output = {}
    for number, point in enumerate(sorted(points, key=lambda item: item["time_us"]), 1):
        if point["time_us"] in output:
            raise ValueError("Duplicate invented time")
        output[point["time_us"]] = dict(point, source_rows=[number])
    return output


def regular(start=0, minutes=200):
    return observations([row(start + time * MINUTE) for time in range(0, minutes, 5)])


def shifted(rows, old, new, **changes):
    updated = copy.deepcopy(rows)
    point = updated.pop(old)
    point.update(time_us=new, available_us=new, raw_time=f"invented-{new}", **changes)
    updated[new] = point
    return observations(updated.values())


class TimingMatchingContract(unittest.TestCase):
    def assert_exact_compatibility(self, rows, start=0, end=200 * MINUTE):
        index = TimeIndex(rows, start, end)
        for origin in rows:
            with self.subTest(origin=origin):
                selected = index.history(origin, 0)
                self.assertEqual(
                    (selected["features"], selected["reason"]),
                    exact_history(rows, origin, start, "evaluation"),
                )
                self.assertEqual(
                    selected["history_rows"],
                    [rows.get(origin - offset * MINUTE) for offset in (25, 20, 15, 10, 5, 0)],
                )
                self.assertEqual(index.target(origin, 0)["target"], exact_target(rows, origin, end))

    def test_zero_radius_differential_against_historical_oracle(self):
        base = regular()
        cases = [base]
        missing = copy.deepcopy(base)
        del missing[40 * MINUTE]
        cases.append(missing)
        cases.append(shifted(base, 35 * MINUTE, 35 * MINUTE + 1))
        for status in (
            "missing",
            "invalid",
            "ambiguous",
            "unsupported",
            "censored_low",
            "censored_high",
        ):
            changed = copy.deepcopy(base)
            changed[40 * MINUTE].update(
                status=status, value=None, bound=40 if status == "censored_low" else None
            )
            changed[90 * MINUTE].update(status=status, value=None, bound=None)
            cases.append(changed)
        late = copy.deepcopy(base)
        late[40 * MINUTE]["available_us"] = 70 * MINUTE
        cases.append(late)
        clock = copy.deepcopy(base)
        for time, point in clock.items():
            if time >= 50 * MINUTE:
                point["segment"] = "second-invented-clock"
        cases.append(clock)
        for rows in cases:
            self.assert_exact_compatibility(rows)

    def test_zero_radius_is_exact_beyond_float_integer_precision(self):
        start = 2**53 + 1
        rows = regular(start)
        rows = shifted(rows, start + 35 * MINUTE, start + 35 * MINUTE + 1)
        self.assert_exact_compatibility(rows, start, start + 200 * MINUTE)
        match = TimeIndex(rows, start, start + 200 * MINUTE).history(start + 60 * MINUTE, SECOND)
        self.assertEqual(match["matches"][0]["offset_us"], 1)

    def test_radius_boundaries_are_inclusive_to_one_microsecond(self):
        for radius in (SECOND, 5 * SECOND):
            for sign in (-1, 1):
                for extra, reason in ((0, None), (1, "history_gap")):
                    moved = 35 * MINUTE + sign * (radius + extra)
                    rows = shifted(regular(), 35 * MINUTE, moved)
                    result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, radius)
                    self.assertEqual(result["reason"], reason)
                    match = result["matches"][0]
                    self.assertEqual(match["nearest_us"], [moved])
                    self.assertEqual(match["distance_us"], radius + extra)
                    self.assertEqual(match["selected_us"], moved if not extra else None)
                    self.assertEqual(match["offset_us"], sign * radius if not extra else None)

    def test_target_radius_boundaries_and_effective_horizon(self):
        for radius in (SECOND, 5 * SECOND):
            for sign in (-1, 1):
                for extra, status in ((0, "measured"), (1, "missing")):
                    moved = 90 * MINUTE + sign * (radius + extra)
                    rows = shifted(regular(), 90 * MINUTE, moved)
                    result = TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, radius)
                    self.assertEqual(result["target"]["status"], status)
                    self.assertEqual(result["match"]["nominal_us"], 90 * MINUTE)
                    self.assertEqual(result["match"]["selected_us"], moved if not extra else None)

    def test_ties_rejected_without_status_based_selection(self):
        rows = regular()
        del rows[35 * MINUTE]
        rows = observations(
            list(rows.values())
            + [
                row(35 * MINUTE - SECOND, status="invalid", value=None),
                row(35 * MINUTE + SECOND),
            ]
        )
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, SECOND)
        self.assertEqual(result["reason"], "history_matching_ambiguity")
        self.assertEqual(
            result["matches"][0]["nearest_us"], [35 * MINUTE - SECOND, 35 * MINUTE + SECOND]
        )
        self.assertIsNone(result["matches"][0]["selected_us"])
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 0)["reason"], "history_gap"
        )

    def test_target_tie_is_distinct_from_source_conflict(self):
        rows = regular()
        del rows[90 * MINUTE]
        rows = observations(
            list(rows.values()) + [row(90 * MINUTE - SECOND), row(90 * MINUTE + SECOND)]
        )
        result = TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, SECOND)
        self.assertEqual(
            result["target"], {"status": "matching_ambiguity", "value": None, "bound": None}
        )
        rows = shifted(regular(), 90 * MINUTE, 90 * MINUTE + SECOND, status="ambiguous", value=None)
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, SECOND)["target"]["status"],
            "ambiguous",
        )

    def test_nearest_unusable_record_is_not_replaced_by_farther_measurement(self):
        rows = shifted(regular(), 35 * MINUTE, 35 * MINUTE + SECOND, status="invalid", value=None)
        rows = observations(list(rows.values()) + [row(35 * MINUTE + 2 * SECOND)])
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["reason"], "history_unmeasured")
        self.assertEqual(result["matches"][0]["selected_us"], 35 * MINUTE + SECOND)
        self.assertIsNone(result["features"])

    def test_exact_unusable_record_is_not_replaced_either(self):
        rows = regular()
        rows[35 * MINUTE].update(status="censored_low", value=None, bound=40)
        rows = observations(list(rows.values()) + [row(35 * MINUTE + SECOND)])
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["reason"], "history_unmeasured")
        self.assertEqual(result["history_rows"][0]["bound"], 40)

    def test_target_has_no_status_based_fallback_and_preserves_censor_bound(self):
        rows = shifted(
            regular(),
            90 * MINUTE,
            90 * MINUTE + SECOND,
            status="censored_high",
            value=None,
            bound=400,
        )
        rows = observations(list(rows.values()) + [row(90 * MINUTE + 2 * SECOND)])
        result = TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["target"], {"status": "censored_high", "value": None, "bound": 400})
        self.assertEqual(result["match"]["selected_us"], 90 * MINUTE + SECOND)

    def test_late_candidate_stays_rejected_without_fallback(self):
        rows = shifted(regular(), 35 * MINUTE, 35 * MINUTE + SECOND)
        rows[35 * MINUTE + SECOND]["available_us"] = 60 * MINUTE + 1
        rows = observations(list(rows.values()) + [row(35 * MINUTE + 2 * SECOND)])
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["reason"], "history_unavailable")
        rows[35 * MINUTE + SECOND]["available_us"] = 60 * MINUTE
        self.assertIsNone(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)["reason"]
        )

    def test_current_observation_stays_exact_and_future_never_fills_it(self):
        rows = regular()
        rows[60 * MINUTE]["available_us"] = 60 * MINUTE + 1
        rows = observations(list(rows.values()) + [row(60 * MINUTE + 1)])
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["reason"], "history_unavailable")
        self.assertEqual(result["matches"][-1]["selected_us"], 60 * MINUTE)
        self.assertTrue(
            all(
                point is None or point["time_us"] <= 60 * MINUTE for point in result["history_rows"]
            )
        )

    def test_clock_discontinuity_is_checked_after_nearest_selection(self):
        rows = shifted(regular(), 35 * MINUTE, 35 * MINUTE - SECOND)
        rows = observations(list(rows.values()) + [row(35 * MINUTE + 2 * SECOND)])
        for time, point in rows.items():
            if time >= 35 * MINUTE:
                point["segment"] = "later-clock"
        result = TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["reason"], "clock_discontinuity")
        self.assertEqual(result["matches"][0]["selected_us"], 35 * MINUTE - SECOND)

    def test_target_clock_checked_but_target_arrival_does_not_gate(self):
        rows = regular()
        rows[90 * MINUTE]["available_us"] = 250 * MINUTE
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, 0)["target"]["status"], "measured"
        )
        for time, point in rows.items():
            if time >= 85 * MINUTE:
                point["segment"] = "later-clock"
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).target(60 * MINUTE, 0)["target"]["status"],
            "clock_discontinuity",
        )

    def test_reason_precedence_keeps_overlapping_problems_distinct(self):
        rows = regular()
        rows[35 * MINUTE].update(status="invalid", value=None)
        rows[40 * MINUTE]["available_us"] = 100 * MINUTE
        del rows[45 * MINUTE]
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)["reason"],
            "history_gap",
        )
        rows = observations(list(rows.values()) + [row(45 * MINUTE)])
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)["reason"],
            "history_unmeasured",
        )
        rows[35 * MINUTE].update(status="measured", value=120)
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 5 * SECOND)["reason"],
            "history_unavailable",
        )

    def test_gap_precedes_other_position_tie(self):
        rows = regular()
        del rows[35 * MINUTE]
        del rows[40 * MINUTE]
        rows = observations(
            list(rows.values()) + [row(35 * MINUTE - SECOND), row(35 * MINUTE + SECOND)]
        )
        self.assertEqual(
            TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, SECOND)["reason"], "history_gap"
        )

    def test_warmup_is_inclusive_at_sixty_minutes_and_keeps_matches(self):
        rows = regular()
        result = TimeIndex(rows, 0, 200 * MINUTE).history(15 * MINUTE, 0)
        self.assertEqual(result["reason"], "evaluation_warmup")
        self.assertEqual(len(result["matches"]), 6)
        self.assertEqual(result["matches"][0]["nominal_us"], -10 * MINUTE)
        self.assertEqual(result["history_rows"][:2], [None, None])
        self.assertIsNone(TimeIndex(rows, 0, 200 * MINUTE).history(60 * MINUTE, 0)["reason"])
        just_before = shifted(regular(), 60 * MINUTE, 60 * MINUTE - 1)
        self.assertEqual(
            TimeIndex(just_before, 0, 200 * MINUTE).history(60 * MINUTE - 1, 5 * SECOND)["reason"],
            "evaluation_warmup",
        )

    def test_outside_nominal_target_never_borrows_inside_candidate(self):
        rows = observations([row(60 * MINUTE), row(90 * MINUTE - 1)])
        result = TimeIndex(rows, 0, 90 * MINUTE).target(60 * MINUTE, 5 * SECOND)
        self.assertEqual(result["target"]["status"], "outside_split")
        self.assertEqual(result["match"]["nearest_us"], [])
        self.assertIsNone(result["match"]["selected_us"])
        inside = TimeIndex(rows, 0, 90 * MINUTE + 1).target(60 * MINUTE, 5 * SECOND)
        self.assertEqual(inside["target"]["status"], "measured")

    def test_nesting_preserves_every_previous_success_and_its_selected_rows(self):
        points = []
        for position, minute in enumerate(range(0, 200, 5)):
            jitter = (0, 0, 1, SECOND, 4 * SECOND)[position % 5]
            points.append(row(minute * MINUTE + jitter))
        rows = observations(points)
        index = TimeIndex(rows, 0, 200 * MINUTE)
        for origin in rows:
            histories = [index.history(origin, radius) for radius in RADII_US]
            targets = [index.target(origin, radius) for radius in RADII_US]
            for smaller, larger in zip(histories, histories[1:]):
                if smaller["reason"] is None:
                    self.assertIsNone(larger["reason"])
                    self.assertEqual(smaller["history_rows"], larger["history_rows"])
                    self.assertEqual(smaller["features"], larger["features"])
            for smaller, larger in zip(targets, targets[1:]):
                if smaller["target"]["status"] == "measured":
                    self.assertEqual(smaller, larger)

    def test_input_is_copied_and_unsorted_mapping_has_deterministic_order(self):
        rows = regular()
        index = TimeIndex(dict(reversed(list(rows.items()))), 0, 200 * MINUTE)
        before = copy.deepcopy(rows)
        index.history(60 * MINUTE, SECOND)
        index.target(60 * MINUTE, SECOND)
        self.assertEqual(rows, before)
        rows[60 * MINUTE]["source_rows"].append(999)
        rows[60 * MINUTE]["value"] = 999
        self.assertEqual(index.rows[60 * MINUTE], before[60 * MINUTE])
        self.assertEqual(index.times, sorted(before))

    def test_interval_row_key_and_origin_validation(self):
        base = regular()
        for start, end in (
            (True, 200 * MINUTE),
            (0, 0),
            (1, 200 * MINUTE),
            (0, 195 * MINUTE),
            (0, 1.0),
        ):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                TimeIndex(base, start, end)
        bad_key = dict(base)
        bad_key[1] = bad_key.pop(0)
        with self.assertRaises(ValueError):
            TimeIndex(bad_key, 0, 200 * MINUTE)
        float_key = dict(base)
        del float_key[0]
        float_key[0.0] = row(0)
        with self.assertRaises(ValueError):
            TimeIndex(float_key, 0, 200 * MINUTE)
        index = TimeIndex(base, 0, 200 * MINUTE)
        for origin in (True, 0.0, 1, -1, 200 * MINUTE):
            for method in (index.history, index.target):
                with self.subTest(origin=origin), self.assertRaises(ValueError):
                    method(origin, 0)

    def test_only_fixed_integer_radii_are_supported(self):
        index = TimeIndex(regular(), 0, 200 * MINUTE)
        for radius in (True, 0.0, -1, 1, 2 * SECOND, 6 * SECOND, None, "1000000"):
            for method in (index.history, index.target):
                with self.subTest(radius=radius), self.assertRaises(ValueError):
                    method(60 * MINUTE, radius)

    def test_empty_interval_index_cannot_invent_an_origin(self):
        index = TimeIndex({}, 0, MINUTE)
        self.assertEqual(index.times, [])
        with self.assertRaises(ValueError):
            index.history(0, 0)


if __name__ == "__main__":
    unittest.main()
