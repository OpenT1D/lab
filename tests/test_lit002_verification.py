"""Unit, history and artifact-boundary checks for native SC verification."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from experiments.literature.lit002.kinetics import (
    CAMBRIDGE,
    FAGGIONATO,
    matched_cambridge,
    simulate,
    steady_state,
)
from experiments.literature.lit002.verification import verify_case

ROOT = Path(__file__).resolve().parents[1]


def fixture(case: Path, arm: str = "faggionato_sc") -> dict:
    protocol = json.loads((ROOT / "experiments/literature/lit002/protocol.json").read_text())
    protocol["horizon_min"] = 20
    segments = [
        {"start_min": 1.3, "end_min": 3.7, "extra_u_h": 3},
        {"start_min": 2, "end_min": 4.7, "extra_u_h": 4},
    ]
    meals = [{"start_min": 5, "duration_min": 5, "grams": 20}]
    protocol["scenarios"] = [{"id": "synthetic_test", "insulin_segments": segments, "meals": meals}]
    config = {
        key: copy.deepcopy(protocol[key])
        for key in (
            "horizon_min",
            "sample_step_min",
            "max_step_min",
            "relative_tolerance",
            "equilibrium_glucose_mg_dl",
            "absorption",
        )
    }
    config.update(arm=arm, insulin_segments=segments, meals=meals)
    p = {
        "cambridge_native": CAMBRIDGE,
        "cambridge_mean_matched": matched_cambridge(),
        "faggionato_sc": FAGGIONATO,
    }[arm]
    weight, basal = 70, 1.2
    prior = basal * 1000 / 60 / weight

    def rate(time):
        return basal + sum(
            segment["extra_u_h"]
            for segment in segments
            if segment["start_min"] <= time < segment["end_min"]
        )

    knots = sorted({0, *(s[key] for s in segments for key in ("start_min", "end_min"))})
    schedule = [(t, rate(t) * 1000 / 60 / weight) for t in knots]
    sample_ms = {i * 60000 for i in range(21)}
    for knot in knots[1:]:
        sample_ms.add(round(knot * 60000))
        sample_ms.add(round((knot + FAGGIONATO.delay_min) * 60000))
    times = [t / 60000 for t in sorted(sample_ms)]
    samples = simulate(times, schedule, prior, p)
    initial = dict.fromkeys(("Q1", "Q2", "I", "x1", "x2", "x3", "D1", "D2"), 1.0)
    initial.update(zip(("S1", "S2"), (x * weight for x in steady_state(prior, p))))
    settings = {
        "arm": arm,
        "native_parameters": {"BW": weight, "tmaxI": 1 / p.kd if arm != "faggionato_sc" else 55},
        "basal_u_h": basal,
        "absorption_parameters": config["absorption"],
        "initial_state": initial,
    }
    runtime = {"settings": settings, "upstream_revision": protocol["native_revision"]}
    rows = []
    for sample in samples:
        time = sample.time_min
        state = {**initial, "S1": sample.sc1 * weight, "S2": sample.sc2 * weight}
        delayed_time = (round(time * 60000) - round(p.delay_min * 60000)) / 60000
        rows.append(
            {
                "time_min": time,
                "glucose_mg_dl": 125,
                "insulin_mU_L": state["I"],
                "appearance_mU_min": sample.appearance * weight,
                "delivered_u_h": rate(time),
                "delayed_delivered_u_h": rate(delayed_time),
                "intake_g_min": 4 if 5 <= time < 10 else 0,
                "depot_mU": state["S1"] + state["S2"],
                "delay_queue_mU": sample.delay_inventory * weight,
                "total_subcutaneous_mU": (sample.sc1 + sample.sc2 + sample.delay_inventory)
                * weight,
                "cumulative_delivered_mU": sample.cumulative_delivered * weight,
                "cumulative_delayed_delivered_mU": (
                    sample.cumulative_delivered - sample.delay_inventory + prior * p.delay_min
                )
                * weight,
                "cumulative_carbohydrates_g": max(0, min(time - 5, 5)) * 4,
                "balance_derived_absorbed_mU": sample.cumulative_absorbed * weight,
                "state": state,
            }
        )
    for name, obj in (
        ("config.json", config),
        ("runtime.json", runtime),
        ("result.json", {"status": "completed", "rows": len(rows), "final_minute": 20}),
    ):
        (case / name).write_text(json.dumps(obj))
    write_rows(case, rows)
    return protocol


def read_rows(case):
    return [json.loads(line) for line in (case / "trace.jsonl").read_text().splitlines()]


def write_rows(case, rows):
    (case / "trace.jsonl").write_text("".join(json.dumps(row) + chr(10) for row in rows))


class SCVerificationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.case = Path(directory.name)
        self.protocol = fixture(self.case)

    def test_normalized_oracle_accepts_whole_body_states_and_overlapping_pulses(self):
        for arm in ("cambridge_native", "cambridge_mean_matched", "faggionato_sc"):
            with self.subTest(arm=arm):
                protocol = fixture(self.case, arm)
                report = verify_case(self.case, protocol)
                self.assertTrue(report["all_passed"], report["checks"])
                self.assertLess(report["max_sc_state_error_mU_per_kg"], 1e-12)
                self.assertLess(report["max_mass_residual_mU_per_kg"], 1e-10)
                expected_delivered = (1.2 * 20 + 3 * 2.4 + 4 * 2.7) * 1000 / 60
                self.assertAlmostEqual(
                    read_rows(self.case)[-1]["cumulative_delivered_mU"], expected_delivered
                )

    def test_unit_mismatch_does_not_pass(self):
        rows = read_rows(self.case)
        for row in rows:
            row["state"]["S1"] /= 70
            row["state"]["S2"] /= 70
        write_rows(self.case, rows)
        report = verify_case(self.case, self.protocol)
        self.assertFalse(report["all_passed"])
        self.assertGreater(report["max_sc_state_error_mU_per_kg"], 0.005)

    def test_delay_queue_and_prior_basal_cannot_be_omitted(self):
        rows = read_rows(self.case)
        self.assertGreater(rows[0]["delay_queue_mU"], 0)
        rows[0]["delay_queue_mU"] = 0
        write_rows(self.case, rows)
        report = verify_case(self.case, self.protocol)
        self.assertFalse(report["checks"]["sc_states_and_delay_inventory_match_independent_oracle"])

    def test_appearance_and_delivered_input_are_checked_separately(self):
        rows = read_rows(self.case)
        rows[8]["appearance_mU_min"] *= 2
        rows[10]["cumulative_delivered_mU"] += 70
        rows[9]["delayed_delivered_u_h"] += 1
        write_rows(self.case, rows)
        checks = verify_case(self.case, self.protocol)["checks"]
        self.assertFalse(checks["appearance_matches_independent_oracle"])
        self.assertFalse(checks["delivered_amount_matches_declared_schedule"])
        self.assertFalse(checks["instantaneous_inputs_and_cumulative_carbs_match_schedule"])

    def test_negative_states_return_failed_check(self):
        rows = read_rows(self.case)
        rows[3]["state"]["Q1"] = -1
        write_rows(self.case, rows)
        self.assertFalse(
            verify_case(self.case, self.protocol)["checks"]["nonnegative_native_states_and_outputs"]
        )

    def test_missing_duplicate_nonfinite_and_shape_fail_closed(self):
        original = read_rows(self.case)
        variants = []
        variants.append(original[:-1])
        duplicate = copy.deepcopy(original)
        duplicate[3]["time_min"] = duplicate[2]["time_min"]
        variants.append(duplicate)
        nonfinite = copy.deepcopy(original)
        nonfinite[3]["state"]["S1"] = float("nan")
        variants.append(nonfinite)
        missing = copy.deepcopy(original)
        del missing[3]["state"]["I"]
        variants.append(missing)
        for rows in variants:
            write_rows(self.case, rows)
            with self.assertRaises(ValueError):
                verify_case(self.case, self.protocol)

    def test_failed_result_and_changed_frozen_source_fail_closed(self):
        (self.case / "result.json").write_text(json.dumps({"status": "failed"}))
        with self.assertRaisesRegex(ValueError, "not completed"):
            verify_case(self.case, self.protocol)
        fixture(self.case)
        config = json.loads((self.case / "config.json").read_text())
        config["absorption"]["tau_min"] = 0
        (self.case / "config.json").write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "frozen"):
            verify_case(self.case, self.protocol)

    def test_unregistered_scenario_and_invalid_body_weight_fail(self):
        runtime = json.loads((self.case / "runtime.json").read_text())
        runtime["settings"]["native_parameters"]["BW"] = 0
        (self.case / "runtime.json").write_text(json.dumps(runtime))
        with self.assertRaisesRegex(ValueError, "native BW"):
            verify_case(self.case, self.protocol)
        fixture(self.case)
        config = json.loads((self.case / "config.json").read_text())
        config["insulin_segments"][0]["extra_u_h"] = 5
        (self.case / "config.json").write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "Unregistered input"):
            verify_case(self.case, self.protocol)


if __name__ == "__main__":
    unittest.main()
