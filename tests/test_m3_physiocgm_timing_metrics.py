"""Invented inputs only: timing traces, comparison invariants and weighting."""

import copy
import unittest
from unittest.mock import patch

from experiments.m3.azt1d.data import forecast_rows as exact_forecast_rows
from experiments.m3.external.metrics import summarize_case as exact_case
from experiments.m3.external.metrics import summarize_study as exact_study
from experiments.m3.physiocgm_timing.common import MINUTE, RADII_US
from experiments.m3.physiocgm_timing.forecast import forecast_rows, legacy_projection
from experiments.m3.physiocgm_timing.metrics import (
    compare_variants,
    summarize_case,
    summarize_study,
)


def rows(count=400, value=100, jitter=False):
    output = {}
    for index in range(count):
        shift = (0, 1_000_000, 0, 5_000_000, 0)[index % 5] if jitter else 0
        time = index * 5 * MINUTE + shift
        output[time] = {
            "time_us": time,
            "available_us": time,
            "segment": "invented-clock",
            "raw_time": f"invented-time-{index}",
            "status": "measured",
            "value": value,
            "bound": None,
            "source_rows": [index + 1],
        }
    return output


def model():
    # Hand-authored arithmetic fixture, never fitted to observations.
    return {"intercept": 100, "coef": [0] * 6, "mean": [0] * 6, "scale": [1] * 6}


def case(source, radius=0, person="invented-a", status="completed", trace=None):
    bounds = [0, max(source) + 5 * MINUTE]
    records = (
        list(forecast_rows(source, person, bounds, model(), radius)) if trace is None else trace
    )
    return summarize_case(
        sorted(source), records, execution_status=status, bounds_us=bounds, radius_us=radius
    )


def campaign(sources):
    bounds = {person: [0, max(source) + 5 * MINUTE] for person, source in sources.items()}
    traces = {
        radius: {
            person: list(forecast_rows(source, person, bounds[person], model(), radius))
            for person, source in sources.items()
        }
        for radius in RADII_US
    }
    kwargs = {
        "planned_origins_by_person": {person: sorted(source) for person, source in sources.items()},
        "bounds_by_person": bounds,
        "execution_statuses_by_radius_by_person": {
            radius: dict.fromkeys(sources, "completed") for radius in RADII_US
        },
    }
    return traces, kwargs


class TimingForecastTests(unittest.TestCase):
    def test_zero_radius_is_exact_legacy_trace_and_arithmetic(self):
        source = rows(jitter=True)
        source[sorted(source)[30]].update(status="censored_low", value=None, bound=40)
        source[sorted(source)[50]]["available_us"] += MINUTE
        bounds = [0, max(source) + 5 * MINUTE]
        old = list(exact_forecast_rows(source, "invented-a", "evaluation", bounds, model()))
        new = list(forecast_rows(source, "invented-a", bounds, model(), 0))
        self.assertEqual(old, [legacy_projection(trace) for trace in new])
        old_summary = exact_case(
            sorted(source), old, execution_status="completed", bounds_us=bounds
        )
        new_summary = case(source, trace=new)
        for key, value in old_summary.items():
            if key != "metric":
                self.assertEqual(value, new_summary[key], key)

    def test_forecast_precedes_future_lookup_and_keeps_model_object(self):
        source = rows(count=20)
        events, expected_model = [], model()
        from experiments.m3.physiocgm_timing.data import TimeIndex

        original_target = TimeIndex.target

        def target(index, origin, radius):
            events.append(("target", origin))
            return original_target(index, origin, radius)

        def predict(given_model, features):
            self.assertIs(given_model, expected_model)
            events.append(("predict", features[-1]))
            return 100

        with (
            patch.object(TimeIndex, "target", target),
            patch("experiments.m3.estimator.predict", predict),
        ):
            traces = list(
                forecast_rows(source, "invented-a", [0, 100 * MINUTE], expected_model, 1_000_000)
            )
        self.assertEqual(sum(trace["forecasts"] is not None for trace in traces), 8)
        for index, event in enumerate(events):
            if event[0] == "predict":
                self.assertEqual(events[index + 1][0], "target")

    def test_future_values_cannot_change_historical_forecast(self):
        source = rows(count=40, jitter=True)
        origin = sorted(source)[20]
        first = {
            trace["origin_us"]: trace
            for trace in forecast_rows(source, "invented-a", [0, 200 * MINUTE], model(), 5_000_000)
        }
        changed = copy.deepcopy(source)
        for time, point in changed.items():
            if time > origin:
                point["value"] += 200
        second = {
            trace["origin_us"]: trace
            for trace in forecast_rows(changed, "invented-a", [0, 200 * MINUTE], model(), 5_000_000)
        }
        self.assertIsNotNone(first[origin]["forecasts"])
        self.assertEqual(first[origin]["forecasts"], second[origin]["forecasts"])
        self.assertEqual(first[origin]["features"], second[origin]["features"])
        self.assertNotEqual(first[origin]["target"], second[origin]["target"])

    def test_timing_metadata_and_features_are_validated(self):
        source = rows(count=40, jitter=True)
        traces = list(
            forecast_rows(source, "invented-a", [0, max(source) + 5 * MINUTE], model(), 5_000_000)
        )
        position = next(i for i, row in enumerate(traces) if row["forecasts"] is not None)
        mutations = (
            lambda row: row["timing"]["history"][0].update(offset_us=987),
            lambda row: row["features"].__setitem__(0, 999),
            lambda row: row["history_rows"][-1].update(time_us=row["origin_us"] + 1),
            lambda row: row.update(reason="history_gap"),
            lambda row: row["timing"].update(radius_us=True),
            lambda row: row["target"].update(status="outside_split", value=None),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                altered = copy.deepcopy(traces)
                mutate(altered[position])
                with self.assertRaises(ValueError):
                    case(source, 5_000_000, trace=altered)


class TimingMetricTests(unittest.TestCase):
    def test_equal_person_primary_matches_legacy_with_unequal_counts(self):
        sources = {"invented-a": rows(400, 100), "invented-b": rows(800, 120)}
        cases = {person: case(source, person=person) for person, source in sources.items()}
        result = summarize_study(cases)
        self.assertEqual(result["primary"]["mean_person_mae_difference"], 10)
        self.assertEqual(result["equal_person_metrics"]["ridge"]["mae"], 10)
        self.assertEqual(result["primary"]["participant_bootstrap_95"], [0, 20])
        old_cases = {}
        for person, source in sources.items():
            bounds = [0, max(source) + 5 * MINUTE]
            records = exact_forecast_rows(source, person, "evaluation", bounds, model())
            old_cases[person] = exact_case(
                sorted(source), records, execution_status="completed", bounds_us=bounds
            )
        old = exact_study(old_cases)
        self.assertEqual(old["primary"], result["primary"])
        self.assertEqual(old["equal_person_metrics"], result["equal_person_metrics"])

    def test_empty_failed_person_is_retained_without_zero_imputation(self):
        source = rows()
        failed = case(source, status="failed", trace=[])
        self.assertIsNone(failed["ridge"]["mae"])
        self.assertEqual(failed["not_attempted"], len(source))
        result = summarize_study({"invented-a": case(source), "invented-b": failed})
        self.assertEqual(result["planned_people"], 2)
        self.assertEqual(result["contributing_people"], 1)
        self.assertFalse(result["complete_cohort"])
        self.assertEqual(result["primary"]["excluded_people"], ["invented-b"])
        self.assertIsNone(result["primary"]["participant_bootstrap_95"])
        self.assertEqual(
            sum(group["planned"] for group in failed["origin_strata"].values()), len(source)
        )

    def test_288_windows_and_full_day_are_both_required(self):
        self.assertFalse(case(rows(count=306))["eligible_for_primary"])
        self.assertTrue(case(rows(count=307))["eligible_for_primary"])

    def test_comparison_nested_coverage_added_groups_and_timing_offsets(self):
        sources = {
            "invented-a": rows(400, 100, True),
            "invented-b": rows(600, 120, True),
            "invented-empty": rows(10),
        }
        traces, kwargs = campaign(sources)
        result = compare_variants(traces, **kwargs)
        self.assertTrue(result["complete_execution_cohort"])
        for label, low, high in (
            ("S1-S0", 0, 1_000_000),
            ("S5-S0", 0, 5_000_000),
            ("S5-S1", 1_000_000, 5_000_000),
        ):
            group = result["added_groups"][label]
            self.assertEqual(group["planned_people"], 3)
            self.assertNotIn("participant_bootstrap_95", group)
            self.assertFalse(group["people"]["invented-empty"]["contributes"])
            self.assertIsNone(group["people"]["invented-empty"]["ridge"]["mae"])
            self.assertEqual(
                group["scored"],
                sum(
                    result["variants"][str(high)]["people"][person]["scored"]
                    - result["variants"][str(low)]["people"][person]["scored"]
                    for person in sources
                ),
            )
            if group["scored"]:
                self.assertEqual(group["mean_person_mae_difference"], 10)
        offsets = result["variants"]["5000000"]["people"]["invented-a"]["timing_offsets"]
        self.assertEqual(offsets["target"]["maximum_absolute_us"], 5_000_000)

    def test_shared_prediction_tamper_is_rejected(self):
        traces, kwargs = campaign({"invented-a": rows(400)})
        trace = next(row for row in traces[1_000_000]["invented-a"] if row["forecasts"] is not None)
        trace["forecasts"]["ridge"] += 1
        with self.assertRaisesRegex(ValueError, "Shared prediction changed"):
            compare_variants(traces, **kwargs)

    def test_existing_prediction_may_gain_a_target_without_changing_its_inputs(self):
        source = rows(count=40)
        nominal = 90 * MINUTE
        moved = source.pop(nominal)
        moved.update(time_us=nominal + 1_000_000, available_us=nominal + 1_000_000)
        source[moved["time_us"]] = moved
        traces, kwargs = campaign({"invented-a": source})
        origin = 60 * MINUTE
        first = next(row for row in traces[0]["invented-a"] if row["origin_us"] == origin)
        second = next(row for row in traces[1_000_000]["invented-a"] if row["origin_us"] == origin)
        self.assertIsNotNone(first["forecasts"])
        self.assertEqual(first["forecasts"], second["forecasts"])
        self.assertEqual(first["target"]["status"], "missing")
        self.assertEqual(second["target"]["status"], "measured")
        result = compare_variants(traces, **kwargs)
        self.assertGreater(result["added_groups"]["S1-S0"]["scored"], 0)

    def test_bool_feature_cannot_masquerade_as_one(self):
        source = rows(count=20, value=1)
        traces = list(forecast_rows(source, "invented-a", [0, 100 * MINUTE], model(), 0))
        next(row for row in traces if row["forecasts"] is not None)["features"][0] = True
        with self.assertRaises(ValueError):
            case(source, trace=traces)

    def test_shared_target_tamper_is_rejected(self):
        traces, kwargs = campaign({"invented-a": rows(400)})
        trace = next(
            row
            for row in traces[1_000_000]["invented-a"]
            if row["forecasts"] is not None and row["target"]["status"] == "measured"
        )
        trace["target"]["value"] += 1
        with self.assertRaisesRegex(ValueError, "Shared scored target changed"):
            compare_variants(traces, **kwargs)

    def test_missing_later_prefix_fails_nested_prediction_control(self):
        traces, kwargs = campaign({"invented-a": rows(400)})
        traces[1_000_000]["invented-a"] = []
        kwargs["execution_statuses_by_radius_by_person"][1_000_000]["invented-a"] = "failed"
        with self.assertRaisesRegex(ValueError, "Prediction sets not nested"):
            compare_variants(traces, **kwargs)

    def test_missing_person_is_not_dropped_silently(self):
        traces, kwargs = campaign({"invented-a": rows(20), "invented-b": rows(20)})
        del traces[1_000_000]["invented-b"]
        with self.assertRaisesRegex(ValueError, "omits a planned participant"):
            compare_variants(traces, **kwargs)

    def test_wrong_person_and_false_completion_rejected(self):
        traces, kwargs = campaign({"invented-a": rows(20)})
        traces[0]["invented-a"][0]["person"] = "wrong-invented-person"
        with self.assertRaisesRegex(ValueError, "Wrong participant"):
            compare_variants(traces, **kwargs)
        with self.assertRaisesRegex(ValueError, "False case completion"):
            case(rows(20), trace=[])


if __name__ == "__main__":
    unittest.main()
