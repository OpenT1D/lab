"""Hand-derived objective geometry and archive-integrity checks for BC-013."""

import copy
import math
import tempfile
import unittest
from pathlib import Path

from experiments.m4.joint_identifiability import common as joint_common
from experiments.m4.profile_likelihood import common, report
from experiments.m4.volume_sensitivity import common as volume_common


def observations_fixture():
    reference = [[100 + t / 4, 50 + t / 2, 200 + t] for t in range(241)]
    datasets, noise = {}, {}
    for name, sign in (("noiseless", 0), ("noise_117", 1), ("noise_221", -1)):
        perturbation = [
            [0 if t == 0 and j < 2 else sign * (j + 1) for j in range(3)] for t in range(241)
        ]
        noise[name] = perturbation
        datasets[name] = [
            [a + b for a, b in zip(row, error)] for row, error in zip(reference, perturbation)
        ]
    return {
        "truth": [1, 1, 1],
        "times": list(range(241)),
        "reference": reference,
        "datasets": datasets,
        "noise": noise,
        "initial": [0] * 24,
        "baseline": {
            "state": [0] * 13,
            "u_sc_pmol_kg_min": 1,
            "action_insulin_u_min": 1,
            "Sb_pmol_kg_min": 1,
            "Z_pmol_kg_min": 1,
            "P_pmol_kg": 1,
            "h_mg_dl": 100,
        },
        "generator": "reference solver; invented observations, known exact basal G/I",
    }


def evaluation(p, spec, observed, sd, theta, residual=0, nuisance_residual=0):
    rows = common.selection(p, spec)
    errors = [0.0] * len(rows)
    errors[next(i for i, row in enumerate(rows) if row % 3 == 0)] = residual
    errors[next(i for i, row in enumerate(rows) if row % 3 == 1)] = nuisance_residual
    return {
        "evaluated_parameters": list(theta),
        "prediction": [obs + scale * error for obs, scale, error in zip(observed, sd, errors)],
        "residuals": errors,
        "objective": residual**2 + nuisance_residual**2,
        "bound_hits": [
            j for j in p["designs"][spec["design"]]["estimated"] if theta[j] in (0.5, 1.5)
        ],
    }


def fit_record(p, spec, evaluated, start, interest=None):
    estimated = [
        j
        for j in p["designs"][spec["design"]]["estimated"]
        if interest is None or j != interest["parameter"]
    ]
    projected = 3 in estimated
    return {
        **copy.deepcopy(evaluated),
        "start": list(start),
        "interest": interest,
        "estimated_parameters": estimated,
        "optimized_parameters": [j for j in estimated if j != 3],
        "estimates": [
            evaluated["evaluated_parameters"][j] if j in estimated else None for j in range(4)
        ],
        "projected_volume": projected,
        "status": "completed",
        "optimizer_status": 1,
        "message": "Hand-derived quadratic fixture, not a biological model run",
        "nfev": 1,
        "forward_evaluations": 0,
        "optimality": 0,
    }


def parent_fixture(volume, dataset, data):
    spec = {
        "id": f"estimated_rates-estimated-30-{dataset}",
        "regime": "estimated_rates",
        "arm": "estimated",
        "step": 30,
        "data": dataset,
        "modality": "GIC",
    }
    observed = [data["datasets"][dataset][t] for t in range(0, 241, 30)]
    return {
        **spec,
        "times": list(range(0, 241, 30)),
        "columns": [0, 1, 2],
        "observed": observed,
        "active_parameters": [0, 1, 2, 3],
        "unobservable": [],
        "fixed_parameters": {},
        "fits": [
            {
                "start": start,
                "active_parameters": [0, 1, 2, 3],
                "status": "completed",
                "optimizer_status": 1,
                "message": "Arithmetic fixture",
                "estimates": [1] * 4,
                "evaluated_parameters": [1] * 4,
                "prediction": copy.deepcopy(observed),
                "residuals": [0] * 27,
                "objective": 0,
                "channel_objectives": [0] * 3,
                "nfev": 1,
                "forward_evaluations": 1,
                "optimality": 0,
                "bound_hits": [],
            }
            for start in volume["inference"]["starts"]
        ],
    }


def case_fixture(p, volume, data, *, design="GI", dataset="noiseless"):
    """Q=64*(target-1)^2+16*(nuisance-1+(target-1)/2)^2.

    Its analytic nuisance optimum is 1-(target-1)/2. Thus profiles have
    Q=64*(target-1)^2 and slices Q=68*(target-1)^2. Cp is independent of this
    manufactured objective and exactly predicted, so its conditional V is one.
    """
    spec = {"id": f"{design}-{dataset}", "design": design, "data": dataset}
    rows = common.selection(p, spec)
    observed = [data["datasets"][dataset][r // 3][r % 3] for r in rows]
    sd = [p["observation"]["synthetic_sd"][r % 3] for r in rows]
    zero = evaluation(p, spec, observed, sd, [1] * 4)
    baseline = [fit_record(p, spec, zero, start) for start in p["inference"]["unrestricted_starts"]]
    case = {
        **spec,
        "selection": rows,
        "observed": observed,
        "sd": sd,
        "baseline": {
            "fit": baseline,
            "reference": copy.deepcopy(baseline),
            "parent_unprojected": parent_fixture(volume, dataset, data)
            if design == "free_volume"
            else None,
        },
        "profiles": [],
    }
    initial = [0.5, 0.625, 0.75, 0.875, 1, 1.125, 1.25, 1.375, 1.5]
    cutoff = p["profiles"]["cutoff"]
    for j in p["designs"][design]["profiled"]:
        nuisance = 1 if j == 0 else 0
        starts = common.profile_starts(p, spec, baseline[0], j)
        records = {}

        def add(value, stage):
            u = value - 1
            theta = [1] * 4
            theta[j], theta[nuisance] = value, 1 - u / 2
            interest = {"parameter": j, "value": value}
            fitted = evaluation(p, spec, observed, sd, theta, 8 * u)
            theta[nuisance] = 1
            records[value] = {
                "value": value,
                "stage": stage,
                "fits": [fit_record(p, spec, fitted, start, interest) for start in starts],
                "slice": evaluation(p, spec, observed, sd, theta, 8 * u, 2 * u),
            }

        for value in initial:
            add(value, "coarse" if value in (0.5, 0.75, 1, 1.25, 1.5) else "grid_refinement")
        crossings = []
        for a, b in zip(initial, initial[1:]):
            if (64 * (a - 1) ** 2 <= cutoff) == (64 * (b - 1) ** 2 <= cutoff):
                continue
            crossing = {"initial_bracket": [a, b], "history": []}
            while b - a > 0.005:
                middle = (a + b) / 2
                crossing["history"].append({"bracket": [a, b], "midpoint": middle})
                add(middle, "crossing_refinement")
                if (64 * (a - 1) ** 2 <= cutoff) == (64 * (middle - 1) ** 2 <= cutoff):
                    a = middle
                else:
                    b = middle
            crossing["bracket"] = [a, b]
            crossings.append(crossing)
        refvalues = sorted({0.5, 1.5, *(v for cross in crossings for v in cross["bracket"])})
        checks = [
            {
                "value": value,
                "fits": copy.deepcopy(records[value]["fits"]),
                "at_fit_best": {
                    k: copy.deepcopy(v) for k, v in records[value]["fits"][0].items() if k in zero
                },
            }
            for value in refvalues
        ]
        case["profiles"].append(
            {
                "parameter": j,
                "coarse_values": [0.5, 0.75, 1, 1.25, 1.5],
                "initial_values": initial[:],
                "points": [records[value] for value in sorted(records)],
                "crossings": crossings,
                "reference_checks": checks,
            }
        )
    return spec, case


def forward_fixture(p, volume, joint):
    return {
        "parent": {
            "passed": True,
            "parent": {
                "passed": True,
                "checks": {
                    key: {"value": 0, "limit": limit, "passed": True}
                    for key, limit in joint_common.forward_check_specifications(joint).items()
                },
                "details": {},
            },
            "checks": {
                key: {"value": 0, "limit": volume["criteria"][key], "passed": True}
                for key in volume_common.VOLUME_CHECKS
            },
            "details": {},
        },
        "profile_oracles": {
            "passed": True,
            "checks": {
                key: {"value": 0, "limit": p["criteria"][key], "passed": True}
                for key in (
                    "analytic_volume_objective_error",
                    "quadratic_profile_objective_error",
                    "quadratic_profile_parameter_error",
                )
            },
        },
    }


def archive_fixture(directory, p, volume, joint, data):
    for name in common.required_files(p):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Artifact consistency fixture only\n")
    for name, value in (
        ("protocol.json", p),
        ("parent-volume.json", volume),
        ("parent-joint.json", joint),
    ):
        common.dump(directory / name, value)
    artifacts = {
        "worker.json": {"fixture": True},
        "observations.json": data,
        "verification.json": forward_fixture(p, volume, joint),
    }
    for spec in common.specifications(p):
        _, case = case_fixture(p, volume, data, design=spec["design"], dataset=spec["data"])
        artifacts[f"cases/{spec['id']}.json"] = case
    for name, value in artifacts.items():
        common.dump(directory / name, value)
        common.dump(directory / "repeat" / name, value)
    common.dump(
        directory / "manifest.json",
        {"schema": common.VERSION, "status": "completed", "files": common.file_hashes(directory)},
    )


class ProfileLikelihoodTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.HERE / "protocol.json")
        self.volume = common.read(volume_common.HERE / "protocol.json")
        self.joint = common.read(joint_common.HERE / "protocol.json")
        self.data = observations_fixture()

    def fixture(self, **kwargs):
        return case_fixture(self.p, self.volume, self.data, **kwargs)

    def assess(self, spec, case):
        return report.assess_case(self.p, self.volume, spec, case, self.data)

    def test_frozen_nine_cases_twentyseven_profiles_and_twelve_numerical_files(self):
        common.validate(self.p)
        cases = common.specifications(self.p)
        self.assertEqual(len(cases), 9)
        self.assertEqual(sum(len(self.p["designs"][s["design"]]["profiled"]) for s in cases), 27)
        self.assertEqual(len(common.numerical_files(self.p)), 12)
        changed = copy.deepcopy(self.p)
        changed["profiles"]["cutoff"] = 4
        with self.assertRaises(ValueError):
            common.validate(changed)

    def test_exact_basal_conditioning_excluded_but_cpeptide_zero_retained(self):
        for design, length in (("GI", 16), ("free_volume", 25), ("fixed_volume", 25)):
            spec, case = self.fixture(design=design)
            self.assertEqual(len(case["selection"]), length)
            self.assertNotIn(0, case["selection"])
            self.assertNotIn(1, case["selection"])
            self.assertEqual(2 in case["selection"], design != "GI")
            self.assertEqual(case["selection"], report.selected_rows(self.p, spec))

    def test_quadratic_profile_and_slice_have_independent_analytic_values(self):
        spec, case = self.fixture()
        result = self.assess(spec, case)
        self.assertTrue(result["passed"])
        profile = result["profiles"][0]
        for point in profile["points"]:
            self.assertAlmostEqual(point["delta_q"], 64 * (point["value"] - 1) ** 2)
            self.assertAlmostEqual(point["slice_delta_q"], 68 * (point["value"] - 1) ** 2)
            self.assertAlmostEqual(
                point["best"]["evaluated_parameters"][1], 1 - (point["value"] - 1) / 2
            )
        self.assertEqual(len(profile["crossings"]), 2)
        radius = math.sqrt(self.p["profiles"]["cutoff"]) / 8
        for crossing, exact in zip(profile["crossings"], (1 - radius, 1 + radius)):
            a, b = crossing["bracket"]
            self.assertLessEqual(a, exact)
            self.assertLessEqual(exact, b)
            self.assertLessEqual(b - a, 0.005)
        self.assertTrue(profile["sampled_regions"][0]["closed_within_bounds"])

    def test_farthest_nuisance_start_includes_projected_volume(self):
        spec, case = self.fixture(design="free_volume")
        best = case["baseline"]["fit"][0]
        best["evaluated_parameters"] = [1.1, 1.1, 0.8, 0.55]
        for j in range(4):
            self.assertEqual(
                common.profile_starts(self.p, spec, best, j),
                report.profile_starts(self.p, spec, best["evaluated_parameters"], j),
            )

    def test_null_interest_fixed_and_absent_coordinates_are_not_estimates(self):
        for design in ("GI", "fixed_volume", "free_volume"):
            spec, case = self.fixture(design=design)
            self.assertTrue(self.assess(spec, case)["passed"])
            record = case["profiles"][0]["points"][0]["fits"][0]
            self.assertIsNone(record["estimates"][0])
            record["estimates"][0] = 0.5
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_projected_volume_estimate_and_conditional_minimum_are_checked(self):
        spec, case = self.fixture(design="free_volume")
        record = case["baseline"]["fit"][0]
        record["evaluated_parameters"][3] = record["estimates"][3] = 1.1
        for i, row in enumerate(case["selection"]):
            if row % 3 == 2:
                record["prediction"][i] /= 1.1
        record["residuals"] = [
            (a - b) / s for a, b, s in zip(record["prediction"], case["observed"], case["sd"])
        ]
        record["objective"] = sum(v * v for v in record["residuals"])
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            self.assess(spec, case)

    def test_lost_failed_start_cannot_be_hidden(self):
        spec, case = self.fixture()
        point = case["profiles"][0]["points"][0]
        record = point["fits"][0]
        record["status"], record["optimizer_status"] = "optimizer_failed", 0
        result = self.assess(spec, case)
        self.assertFalse(result["gates"]["all_fits_completed"])
        self.assertFalse(result["passed"])
        point["fits"].pop(0)
        with self.assertRaisesRegex(ValueError, "start"):
            self.assess(spec, case)

    def test_model_failure_retains_error_without_invented_predictions(self):
        spec, case = self.fixture()
        record = case["profiles"][0]["points"][0]["fits"][0]
        keys = {
            "start",
            "interest",
            "estimated_parameters",
            "optimized_parameters",
            "projected_volume",
        }
        failed = {k: v for k, v in record.items() if k in keys}
        failed.update(
            status="model_failed", error={"type": "RuntimeError", "message": "incomplete solve"}
        )
        case["profiles"][0]["points"][0]["fits"][0] = failed
        self.assertFalse(self.assess(spec, case)["passed"])
        failed["objective"] = 0
        with self.assertRaisesRegex(ValueError, "fabricate"):
            self.assess(spec, case)

    def test_hand_residual_corruption_and_wrong_error_scale_are_rejected(self):
        for change in (
            lambda c: c["profiles"][0]["points"][0]["fits"][0]["residuals"].__setitem__(0, 5),
            lambda c: c["sd"].__setitem__(0, 4),
            lambda c: c["observed"].__setitem__(0, c["observed"][0] + 1),
        ):
            spec, case = self.fixture()
            change(case)
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_partial_failed_or_started_checkpoint_cannot_be_accepted(self):
        for status in ("partial", "failed", "started"):
            spec, case = self.fixture()
            case["status"] = status
            with self.assertRaisesRegex(ValueError, "Incomplete/failed case"):
                self.assess(spec, case)

    def test_negative_stored_square_sum_is_invalid_even_within_roundoff_tolerance(self):
        spec, case = self.fixture()
        case["baseline"]["fit"][0]["objective"] = -1e-15
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.assess(spec, case)

    def test_bisection_history_and_complete_endpoint_solver_checks_required(self):
        for change in (
            lambda p: p["crossings"].pop(),
            lambda p: p["crossings"][0]["history"][0].__setitem__("midpoint", 0.8),
            lambda p: p["reference_checks"].pop(),
            lambda p: p["points"].pop(2),
        ):
            spec, case = self.fixture()
            change(case["profiles"][0])
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_disconnected_sampled_regions_and_bound_limited_endpoints(self):
        points = {
            0.5: {"delta_q": 0},
            0.7: {"delta_q": 5},
            0.9: {"delta_q": 0},
            1.1: {"delta_q": 5},
            1.3: {"delta_q": 0},
            1.5: {"delta_q": 0},
        }
        crossings = [
            {"bracket": [a, b]} for a, b in ((0.6, 0.61), (0.8, 0.81), (1, 1.01), (1.2, 1.21))
        ]
        regions = report.sampled_regions(points, crossings, 3.84)
        self.assertEqual(len(regions), 3)
        self.assertEqual([r["closed_within_bounds"] for r in regions], [False, True, False])
        self.assertEqual(regions[0]["lower"]["kind"], "bound_limited")
        self.assertEqual(regions[-1]["upper"]["kind"], "bound_limited")
        self.assertEqual(
            report.components(sorted(points), {v: r["delta_q"] for v, r in points.items()}, 3.84), 3
        )

    def test_negative_profile_delta_is_preserved_and_fails_minimum_gate(self):
        spec, case = self.fixture(dataset="noise_117")
        for solver in ("fit", "reference"):
            for record in case["baseline"][solver]:
                record.update(evaluation(self.p, spec, case["observed"], case["sd"], [1] * 4, 0.02))
        result = self.assess(spec, case)
        at_truth = next(r for r in result["profiles"][0]["points"] if r["value"] == 1)
        self.assertAlmostEqual(at_truth["delta_q"], -0.0004)
        self.assertFalse(result["profiles"][0]["gates"]["not_below_unrestricted_minimum"])

    def test_reference_solver_subtracts_its_own_baseline(self):
        spec, case = self.fixture(dataset="noise_117")
        for record in case["baseline"]["reference"]:
            record.update(evaluation(self.p, spec, case["observed"], case["sd"], [1] * 4, 0.04))
        result = self.assess(spec, case)
        self.assertFalse(result["gates"]["baseline_reference_agreement"])
        self.assertFalse(result["profiles"][0]["gates"]["reference_objective_agreement"])
        self.assertAlmostEqual(
            result["profiles"][0]["reference_checks"][0]["delta_q_error"], 0.0016
        )

    def test_valid_reduction_roundoff_retains_raw_start_selection(self):
        spec, case = self.fixture()
        fits = case["baseline"]["fit"]
        for i, fit in enumerate(fits):
            theta = [1 + i / 10, 1, 1, 1]
            fit.update(evaluation(self.p, spec, case["observed"], case["sd"], theta, 1))
            fit["estimates"][:2] = theta[:2]
        # A dot-product reduction and Python sum can differ by one ulp. Both
        # arithmetic checks pass; raw objective still selects the second start.
        fits[0]["objective"] = math.nextafter(1, math.inf)
        fits[2]["objective"] = math.nextafter(1, math.inf)
        checked, best = report.assess_fits(
            self.p,
            spec,
            fits,
            case["observed"],
            case["sd"],
            self.p["inference"]["unrestricted_starts"],
        )
        self.assertEqual([r["residual_objective"] for r in checked], [1, 1, 1])
        self.assertEqual(best["evaluated_parameters"][0], 1.1)

    def test_reference_minimum_gate_is_stricter_than_solver_agreement(self):
        spec, case = self.fixture(dataset="noise_117")
        for fit in case["baseline"]["reference"]:
            fit.update(evaluation(self.p, spec, case["observed"], case["sd"], [1] * 4, 0.03))
        for profile in case["profiles"]:
            profile["points"] = [
                r for r in profile["points"] if r["value"] in profile["initial_values"]
            ]
            profile["crossings"] = []
            profile["reference_checks"] = [
                r for r in profile["reference_checks"] if r["value"] in (0.5, 1.5)
            ]
            for point in profile["points"]:
                for fit in point["fits"]:
                    fit.update(
                        evaluation(
                            self.p, spec, case["observed"], case["sd"], fit["evaluated_parameters"]
                        )
                    )
                point["slice"].update(
                    evaluation(
                        self.p,
                        spec,
                        case["observed"],
                        case["sd"],
                        point["slice"]["evaluated_parameters"],
                    )
                )
            for check in profile["reference_checks"]:
                for fit in check["fits"]:
                    fit.update(
                        evaluation(
                            self.p, spec, case["observed"], case["sd"], fit["evaluated_parameters"]
                        )
                    )
                check["at_fit_best"].update(
                    evaluation(
                        self.p,
                        spec,
                        case["observed"],
                        case["sd"],
                        check["at_fit_best"]["evaluated_parameters"],
                    )
                )
        result = self.assess(spec, case)
        self.assertTrue(result["gates"]["baseline_reference_agreement"])
        profile = result["profiles"][0]
        self.assertTrue(profile["gates"]["reference_objective_agreement"])
        self.assertFalse(profile["gates"]["not_below_unrestricted_minimum"])
        self.assertAlmostEqual(profile["reference_checks"][0]["delta_q"], -0.0009)

    def test_reference_minimum_cannot_exceed_its_known_feasible_candidate(self):
        spec, case = self.fixture()
        check = case["profiles"][0]["reference_checks"][0]
        for fit in check["fits"]:
            fit.update(
                evaluation(
                    self.p,
                    spec,
                    case["observed"],
                    case["sd"],
                    fit["evaluated_parameters"],
                    math.sqrt(16.0005),
                )
            )
        result = self.assess(spec, case)["profiles"][0]
        self.assertTrue(result["gates"]["reference_objective_agreement"])
        self.assertFalse(result["gates"]["reference_not_above_feasible_candidate"])

    def test_slice_inequality_is_independently_enforced(self):
        spec, case = self.fixture()
        point = case["profiles"][0]["points"][0]
        point["slice"].update(
            evaluation(
                self.p,
                spec,
                case["observed"],
                case["sd"],
                point["slice"]["evaluated_parameters"],
                1,
            )
        )
        self.assertFalse(
            self.assess(spec, case)["profiles"][0]["gates"]["not_above_feasible_slice"]
        )

    def test_unprojected_parent_comparator_is_required_and_verified(self):
        spec, case = self.fixture(design="free_volume")
        case["baseline"]["parent_unprojected"] = None
        with self.assertRaisesRegex(ValueError, "comparator"):
            self.assess(spec, case)

    def test_independent_forward_oracle_failure_and_false_status_are_distinct(self):
        evidence = forward_fixture(self.p, self.volume, self.joint)
        self.assertTrue(report.assess_forward(self.p, self.volume, self.joint, evidence))
        oracle = evidence["profile_oracles"]
        oracle["checks"]["quadratic_profile_objective_error"]["value"] = 1
        with self.assertRaisesRegex(ValueError, "status"):
            report.assess_forward(self.p, self.volume, self.joint, evidence)
        oracle["checks"]["quadratic_profile_objective_error"]["passed"] = False
        oracle["passed"] = False
        self.assertFalse(report.assess_forward(self.p, self.volume, self.joint, evidence))

    def test_complete_archive_reconstructs_and_hash_status_repeat_failures_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.volume, self.joint, self.data)
            result = report.reconstruct(directory)
            self.assertTrue(result["passed"])
            self.assertEqual(result["profiles"], 27)
            manifest = common.read(directory / "manifest.json")
            manifest["status"] = "calculated"
            common.dump(directory / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                report.reconstruct(directory)
            self.assertTrue(report.reconstruct(directory, allow_pending=True)["passed"])
            manifest["status"] = "completed"
            common.dump(directory / "manifest.json", manifest)
            (directory / "repeat" / "worker.json").write_text('{"fixture":false}\n')
            with self.assertRaises(ValueError):
                report.reconstruct(directory)
            manifest["files"] = common.file_hashes(directory)
            common.dump(directory / "manifest.json", manifest)
            result = report.reconstruct(directory)
            self.assertFalse(result["gates"]["fresh_process_repeat"])
            self.assertEqual(result["repeat_artifact_differences"], 1)

    def test_atomic_checkpoint_preserves_previous_finite_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            common.dump(path, {"completed_starts": 1})
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                common.dump(path, {"objective": math.nan})
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
