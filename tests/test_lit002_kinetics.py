"""Scientific boundary checks for the standalone synthetic SC comparison."""

import json
import math
import unittest
from pathlib import Path

from experiments.literature.lit002.kinetics import (
    CAMBRIDGE,
    FAGGIONATO,
    SCParameters,
    appearance,
    impulse,
    matched_cambridge,
    propagate,
    simulate,
    steady_state,
)


def rk4_reference(state, rate, duration, p):
    """Independent numerical ODE including an explicit appearance integral."""
    values = (*state, 0.0)
    steps = max(1, math.ceil(duration / 0.025))
    dt = duration / steps

    def rhs(x):
        first, second, _absorbed = x
        return (
            rate - (p.ka1 + p.kd) * first,
            p.kd * first - p.ka2 * second,
            p.ka1 * first + p.ka2 * second,
        )

    for _ in range(steps):
        k1 = rhs(values)
        k2 = rhs(tuple(x + dt * k / 2 for x, k in zip(values, k1)))
        k3 = rhs(tuple(x + dt * k / 2 for x, k in zip(values, k2)))
        k4 = rhs(tuple(x + dt * k for x, k in zip(values, k3)))
        values = tuple(
            x + dt * (a + 2 * b + 2 * c + d) / 6 for x, a, b, c, d in zip(values, k1, k2, k3, k4)
        )
    return values


class SCKineticsTests(unittest.TestCase):
    def test_constants_match_transcribed_source(self):
        source = (
            Path(__file__).resolve().parents[1] / "experiments/literature/lit001/parameters.json"
        )
        values = json.loads(source.read_text())["deterministic_parameters"]
        self.assertEqual(FAGGIONATO.ka1, values["k_a1"]["value"])
        self.assertEqual(FAGGIONATO.ka2, values["k_a2"]["value"])
        self.assertEqual(FAGGIONATO.kd, values["k_a2"]["value"] + values["alpha"]["value"])
        self.assertEqual(FAGGIONATO.delay_min, values["tau"]["value"])

    def test_serial_impulse_has_exact_gamma_response(self):
        for time in (0, 0.0001, 5, 55, 120.2, 600):
            with self.subTest(time=time):
                sample = impulse(time, 200, CAMBRIDGE)
                first = 200 * math.exp(-time / 55)
                second = first * time / 55
                self.assertAlmostEqual(sample.sc1, first, places=12)
                self.assertAlmostEqual(sample.sc2, second, places=12)
                self.assertAlmostEqual(sample.appearance, second / 55, places=12)
                self.assertAlmostEqual(sample.cumulative_absorbed, 200 - first - second, places=12)
                self.assertAlmostEqual(sample.balance_residual, 0, places=12)

    def test_exact_propagation_matches_independent_ode_integral(self):
        for p in (CAMBRIDGE, FAGGIONATO, SCParameters(0.002, 0.018, 0.02)):
            with self.subTest(parameters=p):
                state, absorbed = propagate((7, 11), 0.8, 173.2, p)
                reference = rk4_reference((7, 11), 0.8, 173.2, p)
                for actual, expected in zip((*state, absorbed), reference):
                    self.assertAlmostEqual(actual, expected, delta=1e-9)

    def test_exact_propagation_composes_and_handles_small_intervals(self):
        for p in (CAMBRIDGE, FAGGIONATO):
            initial = (7.0, 11.0)
            combined, absorbed = propagate(initial, 0.8, 123.456, p)
            state = initial
            parts = []
            for duration in (1e-10, 0.001, 7.35, 116.1049999999):
                state, part = propagate(state, 0.8, duration, p)
                parts.append(part)
            self.assertAlmostEqual(state[0], combined[0], delta=1e-12)
            self.assertAlmostEqual(state[1], combined[1], delta=1e-12)
            self.assertAlmostEqual(math.fsum(parts), absorbed, delta=1e-12)
            self.assertEqual(propagate(initial, 1, 0, p), (initial, 0.0))
            state, _ = propagate((0.0, 0.0), 1, 1e-10, p)
            self.assertGreaterEqual(min(state), 0)
            self.assertAlmostEqual(state[1] / (p.kd * 1e-20 / 2), 1, places=10)

    def test_near_coincident_rates_are_continuous(self):
        expected, _ = propagate((7, 11), 0.8, 100, CAMBRIDGE)
        for epsilon in (-1e-10, 1e-10):
            p = SCParameters(0, CAMBRIDGE.kd, CAMBRIDGE.ka2 + epsilon)
            actual, _ = propagate((7, 11), 0.8, 100, p)
            self.assertAlmostEqual(actual[0], expected[0], places=10)
            self.assertAlmostEqual(actual[1], expected[1], delta=3e-7)

    def test_basal_history_preserves_equilibrium_and_delay_inventory(self):
        for p in (CAMBRIDGE, FAGGIONATO, matched_cambridge()):
            steady = steady_state(0.3, p)
            self.assertAlmostEqual(appearance(steady, p), 0.3, places=14)
            for sample in simulate([0, 1.7, 5.62, 720], [(0, 0.3)], 0.3, p):
                self.assertAlmostEqual(sample.sc1, steady[0], places=12)
                self.assertAlmostEqual(sample.sc2, steady[1], places=12)
                self.assertAlmostEqual(sample.appearance, 0.3, places=13)
                self.assertAlmostEqual(sample.delay_inventory, 0.3 * p.delay_min, places=12)
                self.assertAlmostEqual(sample.cumulative_absorbed, 0.3 * sample.time_min, places=11)
                self.assertAlmostEqual(sample.balance_residual, 0, places=11)

    def test_delay_is_exact_and_finite_pulse_dose_is_conserved(self):
        schedule = [(0, 0), (1.3, 1), (3.7, 0)]
        samples = simulate([0, 3.7, 6.91, 6.92, 7, 9.32, 2000], schedule, 0, FAGGIONATO)
        for sample in samples:
            self.assertGreaterEqual(min(sample.sc1, sample.sc2, sample.delay_inventory), -1e-12)
            self.assertAlmostEqual(sample.balance_residual, 0, places=12)
        for sample in samples[:4]:
            self.assertEqual(sample.sc1, 0)
            self.assertEqual(sample.sc2, 0)
            self.assertEqual(sample.cumulative_absorbed, 0)
        self.assertAlmostEqual(samples[4].delay_inventory, 2.32, places=12)
        self.assertAlmostEqual(samples[-1].cumulative_delivered, 2.4, places=12)
        self.assertAlmostEqual(samples[-1].cumulative_absorbed, 2.4, delta=1e-9)
        self.assertEqual(samples[-1].delay_inventory, 0)

    def test_shift_boundaries_and_results_do_not_depend_on_output_grid(self):
        schedule = [(0, 0.3), (120, 0.8), (125, 0.3)]
        sparse = simulate([0, 121, 130, 720], schedule, 0.3, FAGGIONATO)
        dense = simulate(list(range(721)), schedule, 0.3, FAGGIONATO)
        for left in sparse:
            right = dense[int(left.time_min)]
            for field in ("sc1", "sc2", "appearance", "cumulative_absorbed"):
                self.assertAlmostEqual(getattr(left, field), getattr(right, field), delta=1e-10)
        baseline = steady_state(0.3, FAGGIONATO)
        self.assertAlmostEqual(sparse[1].sc1, baseline[0], places=12)
        self.assertAlmostEqual(sparse[1].sc2, baseline[1], places=12)

    def test_impulse_is_distinct_from_rate_and_scales_linearly(self):
        for time in (0, 5.61, 5.62, 5.63, 55, 720):
            zero = impulse(time, 0, FAGGIONATO)
            self.assertEqual(zero.sc1 + zero.sc2 + zero.appearance + zero.delay_inventory, 0)
            unit, doubled = (impulse(time, dose, FAGGIONATO) for dose in (100, 200))
            for field in ("sc1", "sc2", "appearance", "cumulative_absorbed", "delay_inventory"):
                self.assertAlmostEqual(getattr(doubled, field), 2 * getattr(unit, field), places=12)
            self.assertAlmostEqual(unit.balance_residual, 0, places=12)
        self.assertEqual(impulse(5.61, 200, FAGGIONATO).delay_inventory, 200)
        self.assertEqual(impulse(5.62, 200, FAGGIONATO).sc1, 200)

    def test_moment_match_includes_delay_and_has_numerical_first_moment(self):
        matched = matched_cambridge()
        self.assertAlmostEqual(1 / matched.kd, 59.2729932475205, places=10)
        self.assertAlmostEqual(
            matched.mean_appearance_min, FAGGIONATO.mean_appearance_min, places=12
        )
        # Integrate the impulse appearance first moment with Simpson's rule.
        # Integrate age since delayed entry so its direct-path jump is an endpoint.
        for p in (FAGGIONATO, matched):
            step, n = 0.25, 8000
            weighted = []
            for i in range(n + 1):
                time = p.delay_min + i * step
                value = time * impulse(time, 1, p).appearance
                weight = 1 if i in (0, n) else 4 if i % 2 else 2
                weighted.append(weight * value)
            self.assertAlmostEqual(
                step / 3 * math.fsum(weighted), p.mean_appearance_min, delta=1e-6
            )

    def test_custom_initial_state_and_invalid_boundaries(self):
        initial = (1.2, 3.4)
        samples = simulate([0, 5, 700], [(0, 0.2)], 0.5, FAGGIONATO, initial_state=initial)
        self.assertEqual((samples[0].sc1, samples[0].sc2), initial)
        self.assertAlmostEqual(samples[0].delay_inventory, 0.5 * FAGGIONATO.delay_min)
        for sample in samples:
            self.assertAlmostEqual(sample.balance_residual, 0, places=11)
        invalid = (
            lambda: SCParameters(-1, 1, 1),
            lambda: SCParameters(0, 0, 1),
            lambda: SCParameters(0, 1, math.nan),
            lambda: impulse(0, -1, FAGGIONATO),
            lambda: propagate((-1, 0), 1, 1, FAGGIONATO),
            lambda: simulate([0, 0], [(0, 1)], 0, FAGGIONATO),
            lambda: simulate([0, 1], [(1, 1)], 0, FAGGIONATO),
            lambda: simulate([0, 1], [(0, 1), (0, 0)], 0, FAGGIONATO),
            lambda: simulate([0, 1], [(0, 1)], -1, FAGGIONATO),
        )
        for call in invalid:
            with self.assertRaises(ValueError):
                call()


if __name__ == "__main__":
    unittest.main()
