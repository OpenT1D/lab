"""Positive audit controls and specified transcript mutations, not native tests."""

import copy
import hashlib
import json
import subprocess
import sys
import unittest

from experiments.adapter_audit.check import HERE, check_case, digest

ROOT = HERE.parents[1]


class AdapterAuditTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((HERE / "cases.json").read_bytes())
        self.pins = json.loads((HERE / "pins.json").read_bytes())

    def reject(self, mutate, reason):
        for name, control in self.cases.items():
            with self.subTest(engine=name):
                check_case(control, self.pins)
                changed = copy.deepcopy(control)
                mutate(changed)
                with self.assertRaisesRegex(ValueError, f"^{reason}$"):
                    check_case(changed, self.pins)

    def test_positive_controls_and_pinned_lock_bytes(self):
        for name, case in self.cases.items():
            self.assertEqual(check_case(case, self.pins)["completed_intervals"], 4)
            pin = self.pins[name]
            self.assertEqual(
                hashlib.sha256((ROOT / pin["path"]).read_bytes()).hexdigest(), pin["sha256"]
            )
        # Independent amount arithmetic: actual modeled rates, not commanded rates.
        self.assertEqual(self.cases["simglucose"]["delivered_u"], 0.054 + 0.060 + 0.060 + 0.075)
        self.assertEqual(self.cases["lt1_cambridge"]["delivered_u"], 0.075 + 0.100 + 0.100 + 0.125)

    def test_reset_transcript_repetition_and_stale_state(self):
        for case in self.cases.values():
            first = check_case(case, self.pins)
            self.assertEqual(check_case(copy.deepcopy(case), self.pins), first)
        self.reject(lambda c: c["rows"][0].update(previous_mg_dl=60), "controller-state")

    def test_future_measurement_and_raw_hidden_value(self):
        self.reject(
            lambda c: c["rows"][2]["observation"].update(**c["input"]["samples"][2], fresh=True),
            "causal-observation",
        )
        self.reject(lambda c: c["rows"][1].update(patient_state=[1] * 13), "row-fields")

    def test_unavailable_future_input_change_preserves_prefix(self):
        for case in self.cases.values():
            changed = copy.deepcopy(case)
            # Source at the last tick is only available at the horizon, outside all calls.
            changed["input"]["samples"][-1]["glucose_mg_dl"] = 999
            changed["identity"]["input_sha256"] = digest(changed["input"])
            self.assertNotEqual(changed["identity"], case["identity"])
            self.assertEqual(changed["rows"], case["rows"])
            check_case(changed, self.pins)

    def test_delay_freshness_and_measurement_time(self):
        self.reject(lambda c: c["rows"][2]["observation"].update(fresh=True), "causal-observation")
        self.reject(
            lambda c: c["rows"][3]["observation"].update(measured_min=c["rows"][3]["time_min"]),
            "causal-observation",
        )
        self.reject(lambda c: c["rows"][0]["observation"].update(fresh=1), "causal-observation")
        for field in ("measured_min", "available_min"):
            self.reject(
                lambda c: c["rows"][0]["observation"].update({field: False}),
                "causal-observation",
            )

    def test_initial_sample_does_not_replace_reset_memory_and_clamps(self):
        for control in self.cases.values():
            for glucose, command, native_rate in ((180, 1.8, 0.03), (1000, 3, 0.05), (0, 0, 0)):
                case = copy.deepcopy(control)
                case["input"]["samples"][0]["glucose_mg_dl"] = glucose
                case["identity"]["input_sha256"] = digest(case["input"])
                case["rows"][0]["observation"]["glucose_mg_dl"] = glucose
                second = case["rows"][1]
                second.update(previous_mg_dl=glucose, command_u_h=command)
                second["native_action"]["rate"] = (
                    native_rate if case["input"]["engine"] == "simglucose" else command
                )
                check_case(case, self.pins)
                # Using the initial measurement as the pre-command reset memory fails.
                case["rows"][0]["previous_mg_dl"] = glucose
                with self.assertRaisesRegex(ValueError, "^controller-state$"):
                    check_case(case, self.pins)

    def test_changed_controller_definition_is_not_audit_1(self):
        for control in self.cases.values():
            for field, value in (("target_mg_dl", 121), ("gain", 0.02), ("max_u_h", 4)):
                changed = copy.deepcopy(control)
                changed["input"][field] = value
                changed["identity"]["input_sha256"] = digest(changed["input"])
                with self.assertRaisesRegex(ValueError, "^controller-settings$"):
                    check_case(changed, self.pins)

    def test_lower_clamp_has_a_strictly_negative_preclip_control(self):
        for control in self.cases.values():
            case = copy.deepcopy(control)
            case["input"]["basal_u_h"] = 0.6
            case["input"]["samples"][0]["glucose_mg_dl"] = 0
            case["identity"]["input_sha256"] = digest(case["input"])
            case["rows"][0]["observation"]["glucose_mg_dl"] = 0
            case["rows"][1]["previous_mg_dl"] = 0
            # Tick 1 before clipping: .6 + .01*(0-120) = -.6 U/h.
            for row, command, native_rate in zip(
                case["rows"], (0.6, 0, 0.6, 1.2), (0.01, 0, 0.01, 0.02), strict=True
            ):
                row["command_u_h"] = command
                row["native_action"]["rate"] = (
                    native_rate if case["input"]["engine"] == "simglucose" else command
                )
                row["delivered_rate"] = row["native_action"]["rate"]
            case["delivered_u"] = 0.12 if case["input"]["engine"] == "simglucose" else 0.2
            check_case(case, self.pins)

    def test_announcement_early_or_repeated(self):
        self.reject(
            lambda c: c["rows"][0].update(new_announcements=["announce-1"]), "announcement-delivery"
        )
        self.reject(
            lambda c: c["rows"][2].update(new_announcements=["announce-1"]), "announcement-delivery"
        )

    def test_actual_event_is_not_the_announced_amount(self):
        for case in self.cases.values():
            changed = copy.deepcopy(case)
            changed["input"]["actual_events"][0]["grams"] = 80
            changed["identity"]["input_sha256"] = digest(changed["input"])
            # Actual meals are absent from controller inputs; announcement remains 20 g.
            self.assertEqual(changed["rows"], case["rows"])
            check_case(changed, self.pins)

    def test_update_current_before_command_is_detected(self):
        self.reject(lambda c: c["rows"][1].update(command_u_h=1.8), "controller-order")

    def test_repeat_and_out_of_order_sampled_calls_refuse(self):
        self.reject(lambda c: c["rows"].insert(1, copy.deepcopy(c["rows"][0])), "rows")
        self.reject(lambda c: c["rows"][1].update(time_min=0), "update-clock")
        self.reject(lambda c: c["rows"][1].update(time_min=-3), "update-clock")

    def test_minutes_hours_and_rate_amount_errors(self):
        self.reject(lambda c: c["rows"][1].update(time_min=180), "update-clock")
        self.reject(lambda c: c["rows"][0]["native_action"].update(unit="U"), "action-unit")
        self.reject(lambda c: c["rows"][0]["native_action"].update(rate=1.2 / 3), "rate-conversion")
        self.reject(
            lambda c: c["rows"][0]["native_action"].update(kind="bolus_amount"), "action-unit"
        )
        self.reject(lambda c: c["rows"][0]["native_action"].update(bolus=1), "unsupported-action")

    def test_initial_basal_seed_runtime_and_input_identity(self):
        self.reject(lambda c: c["input"].update(seed=102), "identity")
        self.reject(lambda c: c["input"].update(basal_u_h=2), "identity")
        self.reject(lambda c: c["identity"].update(runtime_lock_sha256="0" * 64), "identity")
        self.reject(lambda c: c["identity"].update(upstream_revision="0" * 40), "identity")
        self.reject(lambda c: c["input"].update(seed=True), "seed")
        for case in self.cases.values():
            changed = copy.deepcopy(case)
            changed["input"]["samples"][0]["available_min"] = 1
            changed["identity"]["input_sha256"] = digest(changed["input"])
            with self.assertRaisesRegex(ValueError, "^initial$"):
                check_case(changed, self.pins)

    def test_partial_failed_deadline_and_unfinished_accounting(self):
        for case in self.cases.values():
            for status, error in (
                ("failed", "native error"),
                ("interrupted", "deadline"),
                ("started", None),
            ):
                partial = copy.deepcopy(case)
                partial.update(status=status, error=error, rows=partial["rows"][:1])
                # First interval's delivered amount is independently specified.
                partial["delivered_u"] = 0.054 if case["input"]["engine"] == "simglucose" else 0.075
                result = check_case(partial, self.pins)
                self.assertEqual(result["completed_intervals"], 1)
                with self.assertRaisesRegex(ValueError, "^completion$"):
                    check_case({**partial, "status": "completed", "error": None}, self.pins)
                empty = {**partial, "rows": [], "delivered_u": None}
                self.assertEqual(check_case(empty, self.pins)["observed_minutes"], 0)
                with self.assertRaisesRegex(ValueError, "^undefined-amount$"):
                    check_case({**empty, "delivered_u": 0}, self.pins)
        self.reject(lambda c: c.update(status="failed", error=None), "failure-reason")
        self.reject(lambda c: c["rows"].pop(), "completion")

    def test_nonfinite_negative_and_command_delivery_confusion(self):
        self.reject(lambda c: c["rows"][0].update(delivered_rate=-1), "delivery")
        self.reject(lambda c: c["rows"][0].update(command_u_h=float("nan")), "command")
        self.reject(lambda c: c["rows"][0].update(delivered_rate=True), "delivery")
        self.reject(lambda c: c.update(delivered_u=4.8), "delivery-amount")

    def test_simulator_free_cli_receipt(self):
        result = subprocess.run(
            [sys.executable, "-S", "-m", "experiments.adapter_audit.check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        receipt = json.loads(result.stdout)
        self.assertEqual(
            receipt["fixture_bytes_sha256"],
            hashlib.sha256((HERE / "cases.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(set(receipt["cases"]), set(self.cases))


if __name__ == "__main__":
    unittest.main()
