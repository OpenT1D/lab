"""Numerical profile checks using independent equations and intentional faults."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from .optimizer import Problem, project_volume, solve
from .profiles import run_case
from .verify import QuadraticModel, quadratic_observations, run


class ProfileNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(Path(__file__).with_name("protocol.json").read_text())

    def problem(self, design="free_volume", protocol=None, model=None, observations=None):
        protocol = self.protocol if protocol is None else protocol
        return Problem(
            QuadraticModel() if model is None else model,
            quadratic_observations() if observations is None else observations,
            protocol["designs"][design],
            protocol,
        )

    def test_independent_quadratic_profiles_and_scalar_volume_oracles(self):
        evidence = run(self.protocol)
        self.assertTrue(evidence["passed"], evidence["checks"])
        self.assertEqual(len(evidence["details"]["quadratic_profiles"]), 5)
        self.assertEqual(len(evidence["details"]["volume_cases"]), 4)

    def test_volume_interior_bounds_and_zero_denominator(self):
        self.assertEqual(project_volume([2, 4], [2, 4]), 1)
        self.assertEqual(project_volume([2, 4], [8, 16]), 0.5)
        self.assertEqual(project_volume([2, 4], [0, 0]), 1.5)
        self.assertEqual(project_volume([2, 4], [-2, -4]), 1.5)
        for args in (
            ([0, 0], [1, 2]),
            ([], []),
            ([1], [1, 2]),
            ([[1]], [[1]]),
            ([1], [np.nan]),
            ([np.inf], [1]),
            ([1 + 0j], [1]),
            ([True], [1]),
            ([1], ["1"]),
            ([1], [1], 1.5, 0.5),
            ([1], [1], 0, 1.5),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                project_volume(*args)

    def test_exact_conditioning_samples_excluded_and_basal_cp_retained(self):
        gic, gi = self.problem(), self.problem("GI")
        self.assertEqual(len(gic.selected_indices), 25)
        self.assertEqual(len(gi.selected_indices), 16)
        self.assertEqual(gic.selected_indices[0], 2)
        self.assertNotIn(0, gic.selected_indices)
        self.assertNotIn(1, gic.selected_indices)
        self.assertEqual(gic.selected_indices[1:4], [90, 91, 92])
        np.testing.assert_allclose(gi.evaluate([1.3, 0.8, 1, 1])["residuals"], 0, atol=1e-15)
        original = gic.evaluate([1.3, 0.8, 1, 1])["objective"]
        observations = quadratic_observations()
        observations["datasets"]["noiseless"][0][2] += 60
        perturbed = self.problem(observations=observations)
        self.assertAlmostEqual(perturbed.evaluate([1.3, 0.8, 1, 1])["objective"] - original, 4)

    def test_analytic_projection_is_fitted_nuisance_and_target_volume_stays_fixed(self):
        observations = quadratic_observations()
        for row in observations["datasets"]["noiseless"]:
            row[2] /= 1.25
        problem = self.problem(observations=observations)
        fit = solve(problem, [0.7, 1.25, 0.8, 0.8])
        self.assertEqual(fit["status"], "completed")
        self.assertTrue(fit["projected_volume"])
        self.assertIn(3, fit["estimated_parameters"])
        self.assertNotIn(3, fit["optimized_parameters"])
        self.assertAlmostEqual(fit["estimates"][3], 1.25, places=12)
        evaluated = problem.evaluate(fit["evaluated_parameters"])
        for field in ("prediction", "residuals", "objective"):
            self.assertEqual(fit[field], evaluated[field])
        target = solve(problem, [1.3, 0.8, 1, 1], interest=(3, 0.75))
        self.assertEqual(target["status"], "completed")
        self.assertFalse(target["projected_volume"])
        self.assertNotIn(3, target["estimated_parameters"])
        self.assertIsNone(target["estimates"][3])
        self.assertEqual(target["evaluated_parameters"][3], 0.75)
        self.assertGreater(target["objective"], fit["objective"])
        # An ordinary evaluate call remains a fixed-candidate/slice calculation.
        self.assertEqual(problem.evaluate([1.3, 0.8, 1, 0.6])["evaluated_parameters"][3], 0.6)

    def test_projected_bound_and_interest_bound_are_visible(self):
        observations = quadratic_observations()
        for row in observations["datasets"]["noiseless"]:
            row[2] *= 3
        fit = solve(self.problem(observations=observations), [1.3, 0.8, 1, 1], interest=(0, 0.5))
        self.assertEqual(fit["status"], "completed")
        self.assertEqual(fit["evaluated_parameters"][3], 0.5)
        self.assertIn(3, fit["bound_hits"])
        self.assertIn(0, fit["bound_hits"])

    def test_fixed_and_unobservable_coordinates_are_canonical_and_null(self):
        for design, indices in (("GI", [2, 3]), ("fixed_volume", [3])):
            with self.subTest(design=design):
                fit = solve(self.problem(design), [1.3, 0.8, 0.6, 1.4])
                self.assertEqual(fit["status"], "completed")
                self.assertFalse(fit["projected_volume"])
                for index in indices:
                    self.assertEqual(fit["evaluated_parameters"][index], 1)
                    self.assertIsNone(fit["estimates"][index])
                    self.assertNotIn(index, fit["estimated_parameters"])

    def test_model_failures_and_optimizer_noncompletion_are_preserved(self):
        problem = self.problem("GI")
        with patch.object(problem.model, "simulate", side_effect=RuntimeError("intentional")):
            failed = solve(problem, [1, 1, 1, 1])
        self.assertEqual(failed["status"], "model_failed")
        self.assertEqual(failed["error"]["message"], "intentional")
        self.assertNotIn("objective", failed)
        self.assertNotIn("prediction", failed)
        protocol = copy.deepcopy(self.protocol)
        protocol["inference"]["optimizer"]["max_nfev"] = 1
        failed = solve(self.problem("GI", protocol=protocol), [0.7, 1.25, 1, 1])
        self.assertEqual(failed["status"], "optimizer_failed")
        self.assertEqual(failed["optimizer_status"], 0)
        self.assertGreater(failed["objective"], 0)
        self.assertEqual(len(failed["residuals"]), 16)

    def test_invalid_or_incomplete_inputs_do_not_create_completed_predictions(self):
        problem = self.problem()
        for theta in (
            [1, 1, 1],
            [1, 1, 1, True],
            [1, 1, 1, "1"],
            [1, 1, 1, 1 + 0j],
            [1, 1, 1, np.nan],
            [1, 1, 1, 1.5001],
            [1, 1, 1, 0.4999],
        ):
            with self.subTest(theta=theta), self.assertRaises(ValueError):
                problem.evaluate(theta)
        for target in ((0, 2), (False, 1), (0, np.nan), (2, 1)):
            with self.subTest(target=target), self.assertRaises(ValueError):
                solve(self.problem("GI"), [1, 1, 1, 1], interest=target)
        with patch.object(
            problem.model,
            "simulate",
            return_value={"times": list(range(240)), "observations": np.zeros((240, 3))},
        ):
            failed = solve(problem, [1, 1, 1, 1])
        self.assertEqual(failed["status"], "model_failed")
        self.assertNotIn("objective", failed)
        self.assertEqual(len(problem._cache), 0)
        observations = quadratic_observations()
        observations["times"][-1] = 239
        with self.assertRaises(ValueError):
            self.problem(observations=observations)

    def test_exact_cache_is_detached_and_solver_is_forwarded(self):
        problem = self.problem("GI")
        with patch.object(problem.model, "simulate", wraps=problem.model.simulate) as model:
            first = problem.evaluate([1, 1, 1, 1])
            untouched = copy.deepcopy(first)
            first["prediction"][0] = -1e6
            first["residuals"][0] = -1e6
            self.assertEqual(problem.evaluate([1, 1, 1, 1]), untouched)
            self.assertEqual(model.call_count, 1)
            problem.evaluate([np.nextafter(1.0, 1.5), 1, 1, 1])
            self.assertEqual(model.call_count, 2)
            self.assertEqual(model.call_args.kwargs["solver"], "fit")
        reference = Problem(
            QuadraticModel(),
            quadratic_observations(),
            self.protocol["designs"]["GI"],
            self.protocol,
            solver="reference",
        )
        with patch.object(reference.model, "simulate", wraps=reference.model.simulate) as model:
            reference.evaluate([1, 1, 1, 1])
            self.assertEqual(model.call_args.kwargs["solver"], "reference")

    def test_actual_profile_driver_refines_quadratic_crossings_and_reference_endpoints(self):
        class ScaledQuadratic(QuadraticModel):
            def simulate(self, theta, solver="fit"):
                result = super().simulate(theta, solver)
                result["observations"][:, :2] *= 10
                return result

        observations = quadratic_observations()
        for dataset in observations["datasets"].values():
            for row in dataset:
                row[:2] = [v * 10 for v in row[:2]]
        spec = {"id": "GI-noiseless", "design": "GI", "data": "noiseless"}
        snapshots = []
        result = run_case(
            ScaledQuadratic(),
            self.protocol,
            spec,
            observations,
            checkpoint=lambda record: snapshots.append(copy.deepcopy(record)),
        )
        cutoff = self.protocol["profiles"]["cutoff"]
        # x-profile: 50*(x-1.3)^2. Only its lower root lies inside the bounds.
        # y-profile: 100*(y-.8)^2 near both in-bound roots (x=2.1-y).
        roots = {
            0: [1.3 - np.sqrt(cutoff / 50)],
            1: [0.8 - np.sqrt(cutoff / 100), 0.8 + np.sqrt(cutoff / 100)],
        }
        for profile in result["profiles"]:
            self.assertEqual(len(profile["crossings"]), len(roots[profile["parameter"]]))
            endpoints = {0.5, 1.5}
            for crossing, root in zip(profile["crossings"], roots[profile["parameter"]]):
                left, right = crossing["bracket"]
                self.assertLessEqual(left, root)
                self.assertGreaterEqual(right, root)
                self.assertLessEqual(right - left, 0.005)
                self.assertGreater(len(crossing["history"]), 0)
                endpoints.update((left, right))
            self.assertEqual({c["value"] for c in profile["reference_checks"]}, endpoints)
            for point in profile["points"]:
                self.assertEqual(len(point["fits"]), 2)
                for fit in point["fits"]:
                    self.assertEqual(fit["status"], "completed")
                self.assertLessEqual(
                    min(f["objective"] for f in point["fits"]), point["slice"]["objective"] + 1e-8
                )
            for check in profile["reference_checks"]:
                self.assertEqual(len(check["fits"]), 2)
                self.assertAlmostEqual(
                    min(f["objective"] for f in check["fits"]),
                    check["at_fit_best"]["objective"],
                    places=6,
                )
        self.assertEqual(snapshots[-1], result)

    def test_actual_profile_driver_retains_all_fine_grid_crossings(self):
        class MultipleComponents:
            def simulate(self, theta, solver="fit"):
                values = np.zeros((241, 3))
                values[30, :2] = [45 * np.sin(4 * np.pi * (theta[0] - 0.5)), 10 * (theta[1] - 1)]
                return {"times": np.arange(241), "observations": values, "status": "completed"}

        observations = quadratic_observations(a=0, b=0)
        result = run_case(
            MultipleComponents(),
            self.protocol,
            {"id": "GI-noiseless", "design": "GI", "data": "noiseless"},
            observations,
        )
        profile = result["profiles"][0]
        # Q=81*sin(4*pi*(x-.5))^2 has four peaks and eight crossings inside
        # the bounds. The .25-spaced coarse grid alone sees only zeroes.
        self.assertEqual(len(profile["crossings"]), 8)
        for point in profile["points"]:
            if point["stage"] == "coarse":
                self.assertLess(min(f["objective"] for f in point["fits"]), 1e-8)
        angle = np.arcsin(np.sqrt(self.protocol["profiles"]["cutoff"]) / 9)
        expected = sorted(
            0.5 + (k * np.pi + delta) / (4 * np.pi)
            for k in range(4)
            for delta in (angle, np.pi - angle)
        )
        for crossing, root in zip(profile["crossings"], expected):
            left, right = crossing["bracket"]
            self.assertLessEqual(left, root)
            self.assertGreaterEqual(right, root)
            self.assertLessEqual(right - left, 0.005)

    def test_profile_driver_preserves_each_failed_start_before_aborting(self):
        snapshots = []
        with (
            patch(
                "experiments.m4.profile_likelihood.profiles.solve",
                return_value={"status": "model_failed", "error": {"message": "intentional"}},
            ),
            self.assertRaisesRegex(ValueError, "No completed"),
        ):
            run_case(
                QuadraticModel(),
                self.protocol,
                {"id": "GI-noiseless", "design": "GI", "data": "noiseless"},
                quadratic_observations(),
                checkpoint=lambda record: snapshots.append(copy.deepcopy(record)),
            )
        self.assertEqual(len(snapshots), 3)
        self.assertEqual(len(snapshots[-1]["baseline"]["fit"]), 3)
        self.assertTrue(
            all(f["status"] == "model_failed" for f in snapshots[-1]["baseline"]["fit"])
        )


if __name__ == "__main__":
    unittest.main()
