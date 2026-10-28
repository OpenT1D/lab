"""Run explicitly in the existing locked BC-003 numerical runtime."""

import unittest

import numpy as np

from experiments.m4.c_peptide.model import Parameters, initial_state, simulate
from experiments.m4.c_peptide.reference import constant_schedule
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.observation_analysis.estimator import estimate
from experiments.observation_analysis.fixtures import analysis_settings


class SourceModelParityTests(unittest.TestCase):
    def test_known_nonconstant_forward_input_and_refinement(self):
        variant = analysis_settings()["variants"][0]
        p = Parameters(0.037, 0.031, 0.052, 0.0655)
        force = Forcing([0, 10, 30, 120], [1.5, 10.5, 1.5], [1.5, 10.5, 1.5])
        initial = initial_state({"kind": "equilibrium", "basal_q_pmol_kg_min": 1.5}, p)
        expected_total = 70 * (120 * 1.5 + 20 * 9)
        errors = []
        outcomes = []
        for step in (15, 5, 1, 0.25):
            times = np.unique(np.r_[np.arange(0, 120 + step, step), 10, 30])
            analytical = constant_schedule(times, p, force, initial)
            ode = simulate(
                times,
                p,
                force,
                initial,
                {"method": "DOP853", "rtol": 1e-11, "atol": 1e-13, "max_step": 0.125},
            )
            np.testing.assert_allclose(ode[:, 0] / p.volume_l_kg, analytical, atol=1e-5, rtol=0)
            fitted = estimate(times.tolist(), analytical.tolist(), variant)
            errors.append(abs(fitted["total_pmol"] - expected_total))
            outcomes.append(
                {
                    "step_min": step,
                    "status": fitted["status"],
                    "minimum_rate_pmol_min": fitted["minimum_rate_pmol_min"],
                }
            )
        self.assertTrue(all(b < a for a, b in zip(errors, errors[1:])), errors)
        self.assertLess(errors[-1] / expected_total, 1e-4)
        self.assertEqual(outcomes[-1]["status"], "completed")
        # A coarse interpolant can imply negative secretion even with positive
        # generating input. Keep that finding rather than clipping it away.
        self.assertEqual(outcomes[0]["status"], "boundary_failed")
        print(
            {
                "source": "BC-003 original analytical and ODE forward paths",
                "known_total_pmol": expected_total,
                "refinement_absolute_errors_pmol": errors,
                "outcomes": outcomes,
            }
        )


if __name__ == "__main__":
    unittest.main()
