"""Causal and unit checks for the simulator-free oref0 bridge boundary."""

import unittest

from experiments.c1.oref0_adapter import (
    CommandHistory,
    PriorCommand,
    PumpBolusReceipt,
    PumpTempReceipt,
    TempBasalProjection,
    pump_history,
    source_decision_on_m1_grid,
)
from experiments.m1.contracts import Action


class CommandBoundaryTests(unittest.TestCase):
    def test_completed_commands_only_and_reset(self):
        history = CommandHistory()
        command = PriorCommand(0, Action(1 / 60, 0.1))
        with self.assertRaises(ValueError):
            history.append(command, decision_min=0)
        history.append(command, decision_min=3)
        self.assertEqual(history.prior(3), (command,))
        with self.assertRaises(ValueError):
            history.append(PriorCommand(6, Action(0, 0)), decision_min=9)
        with self.assertRaises(ValueError):
            history.append(object(), decision_min=6)
        history.reset()
        self.assertEqual(history.prior(0), ())
        history.append(command, decision_min=3)

    def test_command_is_not_pump_delivery(self):
        command = PriorCommand(0, Action(1 / 60, 0.1))
        with self.assertRaisesRegex(ValueError, "pump receipt"):
            pump_history((command,), decision_min=3)


class PumpReceiptTests(unittest.TestCase):
    def test_source_event_shape_and_reverse_order(self):
        records = pump_history(
            (PumpTempReceipt(0, 2, 30), PumpBolusReceipt(30, 1)), decision_min=60
        )
        self.assertEqual(
            [record["_type"] for record in records],
            ["Bolus", "TempBasalDuration", "TempBasal"],
        )
        self.assertEqual(records[0]["amount"], 1)
        self.assertEqual(records[1]["duration (min)"], 30)
        self.assertEqual(records[2]["rate"], 2)
        self.assertEqual(records[2]["timestamp"], "2024-07-20T00:00:00+00:00")

    def test_no_future_or_unfinished_delivery(self):
        with self.assertRaisesRegex(ValueError, "Future pump bolus"):
            pump_history((PumpBolusReceipt(6, 1),), decision_min=3)
        with self.assertRaisesRegex(ValueError, "Uncompleted pump temp"):
            pump_history((PumpTempReceipt(0, 1, 30),), decision_min=15)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pump_history((PumpBolusReceipt(3, 1), PumpBolusReceipt(3, 1)), decision_min=6)
        with self.assertRaises(ValueError):
            PumpBolusReceipt(0, -1)
        with self.assertRaises(ValueError):
            PumpTempReceipt(0, 1, 0)


class TempProjectionTests(unittest.TestCase):
    def test_thirty_minute_temp_noop_expiration_and_reset(self):
        projection = TempBasalProjection(1)
        projection.accept(0, {"duration": 30, "rate": 2})
        self.assertEqual(projection.currenttemp(0), {"duration": 30, "rate": 2.0})
        for minute in range(0, 30, 3):
            self.assertAlmostEqual(projection.action_for_m1(minute).basal_u_min, 2 / 60)
        projection.accept(30, {})  # Source emitted no new temp command.
        self.assertAlmostEqual(projection.action_for_m1(30).basal_u_min, 1 / 60)
        self.assertEqual(projection.currenttemp(30), {"duration": 0, "rate": 0})
        projection.reset()
        self.assertAlmostEqual(projection.action_for_m1(0).basal_u_min, 1 / 60)

    def test_cancel_and_noop(self):
        projection = TempBasalProjection(1)
        projection.accept(0, {"duration": 30, "rate": 2})
        projection.accept(15, {})
        self.assertEqual(projection.currenttemp(15), {"duration": 15, "rate": 2.0})
        projection.accept(18, {"duration": 0, "rate": 0})
        self.assertAlmostEqual(projection.action_for_m1(18).basal_u_min, 1 / 60)
        self.assertEqual(projection.action_for_m1(18).bolus_u_min, 0)

    def test_off_grid_source_change_splits_m1_interval(self):
        projection = TempBasalProjection(1)
        projection.accept(0, {"duration": 30, "rate": 2})
        with self.assertRaisesRegex(ValueError, "inside an M1 interval"):
            projection.accept(5, {"duration": 30, "rate": 3})
        with self.assertRaisesRegex(ValueError, "three-minute grid"):
            projection.action_for_m1(5)
        self.assertAlmostEqual(projection.action_for_m1(6).basal_u_min, 2 / 60)
        self.assertFalse(source_decision_on_m1_grid(5))
        self.assertTrue(source_decision_on_m1_grid(15))

    def test_off_grid_expiration_splits_m1_interval(self):
        projection = TempBasalProjection(1)
        projection.accept(0, {"duration": 5, "rate": 2})
        with self.assertRaisesRegex(ValueError, "expiration inside an M1 interval"):
            projection.action_for_m1(3)

    def test_invalid_source_suggestion(self):
        projection = TempBasalProjection(1)
        for suggestion in (
            {"rate": 1},
            {"duration": 30},
            {"duration": 0, "rate": 1},
            {"duration": -1, "rate": 0},
        ):
            with self.assertRaises(ValueError):
                projection.accept(0, suggestion)


if __name__ == "__main__":
    unittest.main()
