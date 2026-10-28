"""Causal and rate-unit checks for the selected C1 replacement-route probe."""

import math
import unittest

from experiments.c1.comparator_route_preflight import _oref0_no_go
from experiments.c1.g2p2c_boundary import CausalState, pump_rate
from experiments.m1.contracts import Action, Observation


def observation(minute, glucose=140, source=None):
    source = minute if source is None else source
    return Observation(minute, glucose, source, source == minute)


class G2P2CBoundaryTests(unittest.TestCase):
    def test_causal_twelve_sample_state_and_reset(self):
        state = CausalState()
        first = state.update(observation(0))
        self.assertEqual(len(first), 12)
        self.assertEqual(first[:-1], ((0.0, 0.0),) * 11)
        self.assertEqual(first[-1], ((140 - 39) * 2 / (600 - 39) - 1, -1.0))
        second = state.update(observation(3, 150), previous_action=Action(0.02, 0))
        self.assertEqual(second[-2], first[-1])
        self.assertEqual(second[-1], ((150 - 39) * 2 / (600 - 39) - 1, (0.02 - 0) * 2 / 5 - 1))
        state.reset()
        self.assertEqual(state.update(observation(0)), first)

    def test_no_private_row_future_action_or_stale_cgm(self):
        state = CausalState()
        with self.assertRaises(ValueError):
            state.update(object())
        with self.assertRaises(ValueError):
            state.update(observation(3))
        state.update(observation(0))
        with self.assertRaises(ValueError):
            state.update(observation(3, source=0), previous_action=Action(0.02, 0))
        with self.assertRaises(ValueError):
            state.update(observation(6), previous_action=Action(0.02, 0))
        with self.assertRaises(ValueError):
            state.update(observation(3), previous_action=Action(0.02, 0.01))
        # Rejected calls did not advance the state.
        state.update(observation(3), previous_action=Action(0.02, 0))

    def test_gap_restart_uses_only_new_cgm_and_previous_command(self):
        state = CausalState()
        state.update(observation(0, 140))
        with self.assertRaises(ValueError):
            state.restart_after_gap(observation(33, source=0), previous_action=Action(0.02, 0))
        history = state.restart_after_gap(observation(33, 150), previous_action=Action(0.02, 0))
        self.assertEqual(history[:-1], ((0.0, 0.0),) * 11)
        self.assertEqual(
            history[-1],
            ((150 - 39) * 2 / (600 - 39) - 1, (0.02 - 0) * 2 / 5 - 1),
        )
        state.update(observation(36, 155), previous_action=Action(0.03, 0))

    def test_source_action_domain_and_rate_units(self):
        for value in (-1, -0.5, 0, 0.5, 1):
            action = pump_rate(value)
            self.assertAlmostEqual(action.basal_u_min, 5 * math.exp((value - 1) * 4))
            self.assertEqual(action.bolus_u_min, 0)
        for value in (-1.01, 1.01, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                pump_rate(value)

    def test_unmodified_oref0_route_is_explicit_no_go(self):
        result = _oref0_no_go()
        self.assertFalse(result["minute_5_on_m1_grid"])
        self.assertTrue(result["off_grid_temp_rejected"])
        self.assertTrue(result["command_as_pump_receipt_rejected"])


if __name__ == "__main__":
    unittest.main()
