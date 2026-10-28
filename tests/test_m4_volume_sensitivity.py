"""BC-012 artifact arithmetic with hand-derived residuals and orthogonal SVDs."""

import copy
import itertools
import math
import tempfile
import unittest
from pathlib import Path

from experiments.m4.joint_identifiability import common as parent_common
from experiments.m4.volume_sensitivity import common, report


def observation_fixture():
    """Affine synthetic fixture makes mismatched times and channels visible."""
    reference = [[100 + t / 4, 50 + 2 * t, 200 + 3 * t] for t in range(241)]
    datasets, noise = {}, {}
    for name, signs in (
        ("noiseless", (0, 0, 0)),
        ("noise_117", (5, -10, 30)),
        ("noise_221", (-5, 10, -30)),
    ):
        error = [[0 if t == 0 and j < 2 else signs[j] for j in range(3)] for t in range(241)]
        datasets[name] = [
            [v + delta for v, delta in zip(row, perturbation)]
            for row, perturbation in zip(reference, error)
        ]
        noise[name] = error
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


def case_fixture(
    p, data, *, regime="estimated_rates", arm="estimated", step=30, dataset="noiseless"
):
    modality = "GI" if arm == "control" else "GIC"
    spec = {
        "id": f"{regime}-{arm}-{step}-{dataset}",
        "regime": regime,
        "arm": arm,
        "step": step,
        "data": dataset,
        "modality": modality,
    }
    active = [0] if regime == "known_rates" else ([0, 1] if arm == "control" else [0, 1, 2])
    if arm == "estimated":
        active.append(3)
    fixed = {"m4_scale": 1, "k3_scale": 1} if regime == "known_rates" else {}
    if arm in ("correct", "low", "high"):
        fixed["volume_scale"] = {"correct": 1.0, "low": 0.8, "high": 1.2}[arm]
    absent = (
        (["volume_scale"] if regime == "known_rates" else ["k3_scale", "volume_scale"])
        if arm == "control"
        else []
    )
    columns = [0, 1] if arm == "control" else [0, 1, 2]
    times = list(range(0, 241, step))
    selected = [[data["datasets"][dataset][t][c] for c in columns] for t in times]
    evaluated = [1, 1, 1, fixed.get("volume_scale", 1)]
    fits = [
        {
            "start": list(start),
            "active_parameters": active[:],
            "status": "completed",
            "optimizer_status": 1,
            "message": "Arithmetic fixture, not a model execution",
            "estimates": [1.0 if j in active else None for j in range(4)],
            "evaluated_parameters": evaluated[:],
            "prediction": copy.deepcopy(selected),
            "residuals": [0.0] * (len(times) * len(columns)),
            "objective": 0.0,
            "channel_objectives": [0.0] * len(columns),
            "nfev": 1,
            "forward_evaluations": 1,
            "optimality": 0.0,
            "bound_hits": [],
        }
        for start in p["inference"]["starts"]
    ]
    return spec, {
        **spec,
        "times": times,
        "columns": columns,
        "observed": selected,
        "active_parameters": active,
        "unobservable": absent,
        "fixed_parameters": fixed,
        "fits": fits,
    }


def sensitivity_fixture(*, volume_amplitude=1.0):
    """Independent orthogonal columns; V scales Cp rows only in this fixture."""
    support = [30 * 3, 60 * 3 + 1, 90 * 3 + 2, 120 * 3 + 2]
    full, checks = {}, {}
    for anchor in (0.8, 1.0, 1.2):
        array = [[0.0] * 4 for _ in range(723)]
        for j, amplitude in enumerate((4.0, 3.0, 2.0 / anchor, volume_amplitude / anchor)):
            array[support[j]][j] = amplitude
        full[str(anchor)] = {
            f"{solver}-{h}": copy.deepcopy(array)
            for solver in ("fit", "reference")
            for h in (0.002, 0.001)
        }
        checks[str(anchor)] = {
            "jacobian_relative_refinement_error": 0.0,
            "jacobian_solver_relative_error": 0.0,
        }
    records = []
    for regime, arm, step in itertools.product(
        ("known_rates", "estimated_rates"),
        ("correct", "low", "high", "estimated", "control"),
        (10, 30),
    ):
        modality = "GI" if arm == "control" else "GIC"
        anchor = {"low": "0.8", "high": "1.2"}.get(arm, "1.0")
        declared = [0] if regime == "known_rates" else [0, 1, 2]
        if arm in ("estimated", "control"):
            declared.append(3)
        active = [j for j in declared if arm != "control" or j < 2]
        absent = [j for j in declared if j not in active]
        columns = [0, 1] if arm == "control" else [0, 1, 2]
        rows = [t * 3 + c for t in range(0, 241, step) for c in columns]
        ref = full[anchor]["reference-0.001"]
        selected = [[0.0 if j in absent else ref[r][j] for j in declared] for r in rows]
        singular = [0.0 if j in absent else ref[support[j]][j] for j in declared]
        u = [[0.0] * len(declared) for _ in rows]
        occupied = {rows.index(support[j]) for j in active}
        null_rows = iter(i for i in range(len(rows)) if i not in occupied)
        for column, j in enumerate(declared):
            u[rows.index(support[j]) if j in active else next(null_rows)][column] = 1
        records.append(
            {
                "regime": regime,
                "arm": arm,
                "step": step,
                "modality": modality,
                "anchor": anchor,
                "declared_parameters": declared,
                "active_parameters": active,
                "unobservable": [common.NAMES[j] for j in absent],
                "jacobian": selected,
                "left_vectors": u,
                "right_vectors": [
                    [float(i == j) for j in range(len(declared))] for i in range(len(declared))
                ],
                "singular_values": singular,
                "rank": len(active),
                "condition_number": singular[0] / singular[-1]
                if len(active) == len(declared)
                else None,
                "numerical_leakage": {common.NAMES[j]: 0.0 for j in absent},
            }
        )
    return {
        "full_weighted_log_jacobians": full,
        "checks": checks,
        "records": records,
        "passed": True,
    }


def forward_fixture(p, parent):
    return {
        "passed": True,
        "parent": {
            "passed": True,
            "checks": {
                key: {"value": 0, "limit": limit, "passed": True}
                for key, limit in parent_common.forward_check_specifications(parent).items()
            },
            "details": {},
        },
        "checks": {
            key: {"value": 0, "limit": p["criteria"][key], "passed": True}
            for key in common.VOLUME_CHECKS
        },
        "details": {},
    }


def archive_fixture(directory, p, parent, data, *, edits=None):
    """Hashed consistency fixture; placeholders are explicitly not model evidence."""
    for name in common.required_files(p):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Handcrafted artifact-consistency fixture\n")
    common.dump(directory / "protocol.json", p)
    common.dump(directory / "parent.json", parent)
    artifacts = {
        "worker.json": {"fixture": True},
        "verification.json": forward_fixture(p, parent),
        "observations.json": data,
        "sensitivity.json": sensitivity_fixture(),
    }
    for regime, arm, step, dataset in itertools.product(
        ("known_rates", "estimated_rates"),
        ("correct", "low", "high", "estimated", "control"),
        (10, 30),
        ("noiseless", "noise_117", "noise_221"),
    ):
        spec, case = case_fixture(p, data, regime=regime, arm=arm, step=step, dataset=dataset)
        artifacts[f"cases/{spec['id']}.json"] = case
    if edits:
        edits(artifacts)
    for name, value in artifacts.items():
        common.dump(directory / name, value)
        common.dump(directory / "repeat" / name, value)
    common.dump(
        directory / "manifest.json",
        {"schema": common.VERSION, "status": "completed", "files": common.file_hashes(directory)},
    )


class VolumeSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.HERE / "protocol.json")
        self.parent = parent_common.read(parent_common.HERE / "protocol.json")
        self.data = observation_fixture()

    def case(self, **kwargs):
        return case_fixture(self.p, self.data, **kwargs)

    def assess(self, spec, case):
        return report.assess_case(self.p, spec, case, self.data)

    def test_frozen_inventory_has_sixty_distinct_cases_and_one_gi_control(self):
        cases = common.specifications(self.p)
        self.assertEqual(len(cases), 60)
        self.assertEqual(len({c["id"] for c in cases}), 60)
        self.assertEqual(sum(c["arm"] == "control" for c in cases), 12)
        self.assertEqual(len(common.numerical_files(self.p)), 64)
        self.assertEqual(sum(c["arm"] == "estimated" for c in cases), 12)

    def test_protocol_freeze_rejects_changed_volume_bounds_and_acceptance(self):
        common.validate(self.p)
        for change in (
            lambda x: x["inference"]["volume_arms"].__setitem__("low", 0.9),
            lambda x: x["model"]["upper"].__setitem__(3, 2),
            lambda x: x["criteria"].__setitem__("noiseless_active_parameter_relative_error", 0.1),
        ):
            altered = copy.deepcopy(self.p)
            change(altered)
            with self.assertRaises(ValueError):
                common.validate(altered)

    def test_parent_observation_schema_keeps_three_parameter_truth(self):
        report.assess_observations(self.p, self.parent, self.data)
        for change in (
            lambda x: x["truth"].append(1),
            lambda x: x["noise"].pop("noise_221"),
            lambda x: x["noise"].__setitem__("noise_999", copy.deepcopy(x["noise"]["noise_117"])),
            lambda x: x["initial"].pop(),
            lambda x: x["baseline"]["state"].pop(),
            lambda x: x["datasets"]["noise_117"][0].__setitem__(2, 200),
            lambda x: x["reference"][1].__setitem__(0, float("nan")),
        ):
            data = copy.deepcopy(self.data)
            change(data)
            with self.assertRaises(ValueError):
                report.assess_observations(self.p, self.parent, data)

    def test_basal_noise_and_noiseless_noise_remain_zero(self):
        for name, row, col in (("noise_117", 0, 1), ("noiseless", 10, 2)):
            data = copy.deepcopy(self.data)
            data["noise"][name][row][col] += 1
            data["datasets"][name][row][col] += 1
            with self.assertRaises(ValueError):
                report.assess_observations(self.p, self.parent, data)

    def test_independent_weighted_channel_sums_and_best_start(self):
        spec, case = self.case()
        for fit, factor, estimates in zip(
            case["fits"], (1, 0.5), ([0.9, 1.1, 1.2, 0.8], [1.02, 0.95, 1.03, 0.99])
        ):
            fit["estimates"] = estimates
            fit["evaluated_parameters"] = estimates[:]
            fit["prediction"] = [
                [g + 5 * factor, i - 20 * factor, cp + 90 * factor] for g, i, cp in case["observed"]
            ]
            fit["residuals"] = [factor, -2 * factor, 3 * factor] * 9
            fit["channel_objectives"] = [9 * factor**2, 36 * factor**2, 81 * factor**2]
            fit["objective"] = 126 * factor**2
        result = self.assess(spec, case)
        self.assertEqual(result["fits"][0]["channel_objectives"], [9, 36, 81])
        self.assertEqual(result["best"]["objective"], 31.5)
        self.assertAlmostEqual(result["best"]["max_active_relative_error"], 0.05)
        self.assertAlmostEqual(result["fits"][0]["relative_bias"][3], -0.2)
        self.assertAlmostEqual(result["start_max_absolute_disagreement"], 0.19)
        self.assertFalse(result["noiseless_recovered"])

    def test_wrong_volume_bias_is_a_finding_not_noiseless_gate(self):
        for arm in ("low", "high"):
            spec, case = self.case(arm=arm)
            for fit in case["fits"]:
                fit["estimates"][2] = 1.25
                fit["evaluated_parameters"][2] = 1.25
            result = self.assess(spec, case)
            self.assertFalse(result["noiseless_recovery_eligible"])
            self.assertIsNone(result["noiseless_recovered"])
            self.assertEqual(result["best"]["relative_errors"][2], 0.25)

    def test_free_volume_null_handling_and_known_rates_are_distinct(self):
        spec, case = self.case(regime="known_rates")
        result = self.assess(spec, case)
        self.assertEqual(result["active_parameters"], [0, 3])
        self.assertEqual(result["best"]["estimates"], [1, None, None, 1])
        self.assertTrue(result["noiseless_recovered"])
        for regime, arm, slot in (
            ("known_rates", "estimated", 1),
            ("estimated_rates", "low", 3),
            ("estimated_rates", "control", 2),
            ("estimated_rates", "control", 3),
        ):
            spec, case = self.case(regime=regime, arm=arm)
            case["fits"][0]["estimates"][slot] = 1
            with self.subTest(regime=regime, arm=arm, slot=slot), self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_fixed_and_unobservable_evaluated_values_cannot_drift(self):
        for regime, arm, slot in (
            ("known_rates", "estimated", 1),
            ("estimated_rates", "low", 3),
            ("estimated_rates", "control", 2),
            ("estimated_rates", "control", 3),
            ("estimated_rates", "estimated", 0),
        ):
            spec, case = self.case(regime=regime, arm=arm)
            case["fits"][0]["evaluated_parameters"][slot] = 1.1
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_one_recovered_start_does_not_hide_second_start_bias(self):
        spec, case = self.case()
        case["fits"][1]["estimates"][3] = 1.02
        case["fits"][1]["evaluated_parameters"][3] = 1.02
        result = self.assess(spec, case)
        self.assertEqual(result["best"]["max_active_relative_error"], 0)
        self.assertFalse(result["noiseless_recovered"])
        spec, case = self.case(dataset="noise_117")
        self.assertIsNone(self.assess(spec, case)["noiseless_recovered"])

    def test_shared_observations_select_exact_schedule_noise_and_modality(self):
        for edit in (
            lambda x: x["times"].__setitem__(1, 29),
            lambda x: x.__setitem__("columns", [0, 2, 1]),
            lambda x: x["observed"][1].__setitem__(2, self.data["datasets"]["noise_221"][30][2]),
            lambda x: x.__setitem__("data", "noise_221"),
            lambda x: x.__setitem__("arm", "correct"),
        ):
            spec, case = self.case(dataset="noise_117")
            edit(case)
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_residual_channel_and_total_objectives_must_agree(self):
        for edit in (
            lambda x: x["channel_objectives"].__setitem__(2, 1),
            lambda x: x["channel_objectives"].pop(),
            lambda x: x.__setitem__("objective", 1),
            lambda x: x["residuals"].__setitem__(0, 1),
            lambda x: x["residuals"].pop(),
            lambda x: x["prediction"].pop(),
            lambda x: x["prediction"][0].__setitem__(2, float("inf")),
        ):
            spec, case = self.case()
            edit(case["fits"][0])
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_invalid_estimates_bounds_starts_and_counts_rejected(self):
        for edit in (
            lambda x: x["fits"].pop(),
            lambda x: x["fits"].reverse(),
            lambda x: x["fits"][0]["estimates"].__setitem__(3, True),
            lambda x: x["fits"][0]["estimates"].__setitem__(3, float("nan")),
            lambda x: x["fits"][0]["estimates"].__setitem__(3, 1.501),
            lambda x: x["fits"][0].__setitem__("nfev", 0),
            lambda x: x["fits"][0].__setitem__("forward_evaluations", 1.5),
            lambda x: x["fits"][0].__setitem__("active_parameters", [0, 1, 2]),
        ):
            spec, case = self.case()
            edit(case)
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_bound_hit_reconstructed_for_estimated_volume(self):
        spec, case = self.case()
        fit = case["fits"][0]
        fit["estimates"][3] = fit["evaluated_parameters"][3] = 0.5
        with self.assertRaises(ValueError):
            self.assess(spec, case)
        fit["bound_hits"] = [3]
        self.assertEqual(self.assess(spec, case)["fits"][0]["bound_hits"], [3])

    def test_model_failure_retained_without_fabricated_residual(self):
        spec, case = self.case()
        case["fits"][1] = {
            "start": self.p["inference"]["starts"][1],
            "active_parameters": [0, 1, 2, 3],
            "status": "model_failed",
            "error": {"type": "ValueError", "message": "Incomplete integration"},
        }
        result = self.assess(spec, case)
        self.assertEqual(len(result["fits"]), 2)
        self.assertNotIn("estimates", result["fits"][1])
        self.assertFalse(result["noiseless_recovered"])
        self.assertIsNone(result["start_max_absolute_disagreement"])
        case["fits"][1]["residuals"] = [1000]
        with self.assertRaises(ValueError):
            self.assess(spec, case)

    def test_optimizer_nonconvergence_cannot_be_promoted(self):
        spec, case = self.case()
        case["fits"][0]["optimizer_status"] = 0
        with self.assertRaises(ValueError):
            self.assess(spec, case)
        case["fits"][0]["status"] = "optimizer_failed"
        self.assertFalse(self.assess(spec, case)["noiseless_recovered"])
        case["fits"][0]["status"] = "unknown"
        with self.assertRaises(ValueError):
            self.assess(spec, case)

    def test_orthogonal_svd_four_columns_volume_anchors_and_gi_nulls(self):
        records, checks, passed = report.assess_sensitivities(
            self.p, self.parent, sensitivity_fixture()
        )
        self.assertTrue(passed)
        self.assertEqual(set(checks), {"0.8", "1.0", "1.2"})
        self.assertEqual(len(records), 20)
        free = next(
            r for r in records if r["regime"] == "estimated_rates" and r["arm"] == "estimated"
        )
        self.assertEqual(free["singular_values"], [4, 3, 2, 1])
        self.assertEqual(free["rank"], 4)
        controls = [r for r in records if r["arm"] == "control"]
        self.assertTrue(all(r["condition_number"] is None for r in controls))
        self.assertEqual({r["rank"] for r in controls}, {1, 2})

    def test_svd_must_bind_to_correct_volume_anchor_and_columns(self):
        for edit in (
            lambda x: x["records"][2].__setitem__("anchor", "1.0"),
            lambda x: x["records"][2]["jacobian"][9].__setitem__(0, 1),
            lambda x: x["records"][-1].__setitem__("unobservable", ["volume_scale"]),
            lambda x: x["records"][-1]["numerical_leakage"].__setitem__("k3_scale", 1),
            lambda x: x["records"][0].__setitem__("declared_parameters", [0, 3]),
            lambda x: x["records"][1].__setitem__("step", 10),
            lambda x: x["records"].pop(),
            lambda x: x["full_weighted_log_jacobians"].pop("0.8"),
            lambda x: x["full_weighted_log_jacobians"]["1.0"].pop("fit-0.002"),
        ):
            evidence = sensitivity_fixture()
            edit(evidence)
            with self.assertRaises(ValueError):
                report.assess_sensitivities(self.p, self.parent, evidence)

    def test_svd_wrong_rank_factors_and_order_rejected(self):
        for edit in (
            lambda x: x["records"][-3].__setitem__("rank", 3),
            lambda x: x["records"][-3]["left_vectors"][0].__setitem__(0, 1),
            lambda x: x["records"][-3]["right_vectors"][0].__setitem__(1, 1),
            lambda x: x["records"][-3]["singular_values"].reverse(),
        ):
            evidence = sensitivity_fixture()
            edit(evidence)
            with self.assertRaises(ValueError):
                report.assess_sensitivities(self.p, self.parent, evidence)

    def test_local_rank_resolution_uses_design_discrepancy_not_global_gate(self):
        evidence = sensitivity_fixture(volume_amplitude=0.01)
        evidence["full_weighted_log_jacobians"]["1.0"]["fit-0.001"][120 * 3 + 2][3] += 0.02
        evidence["checks"]["1.0"]["jacobian_solver_relative_error"] = 0.02 / math.sqrt(
            16 + 9 + 4 + 0.0001
        )
        records, _, passed = report.assess_sensitivities(self.p, self.parent, evidence)
        self.assertTrue(passed)
        record = next(
            r for r in records if r["regime"] == "estimated_rates" and r["arm"] == "estimated"
        )
        self.assertEqual(record["rank"], 4)
        self.assertEqual(record["directions_above_numerical_discrepancy"], 3)
        self.assertFalse(record["rank_resolved_under_checked_refinements"])
        fixed = next(
            r for r in records if r["regime"] == "estimated_rates" and r["arm"] == "correct"
        )
        self.assertTrue(fixed["rank_resolved_under_checked_refinements"])

    def test_forward_and_sensitivity_status_are_recomputed(self):
        for edit in (
            lambda x: x["checks"].pop("volume_state_error"),
            lambda x: x["checks"]["volume_state_error"].__setitem__("value", 1),
            lambda x: x["checks"]["volume_state_error"].__setitem__("limit", 1),
            lambda x: x["checks"]["volume_state_error"].__setitem__("value", -1),
            lambda x: x["parent"]["checks"].pop("independent_cpeptide"),
        ):
            evidence = forward_fixture(self.p, self.parent)
            edit(evidence)
            with self.assertRaises(ValueError):
                report.assess_forward(self.p, self.parent, evidence)
        evidence = sensitivity_fixture()
        evidence["passed"] = False
        with self.assertRaises(ValueError):
            report.assess_sensitivities(self.p, self.parent, evidence)

    def test_genuine_forward_failure_is_not_erased(self):
        evidence = forward_fixture(self.p, self.parent)
        evidence["checks"]["volume_state_error"].update(value=1, passed=False)
        evidence["passed"] = False
        self.assertFalse(report.assess_forward(self.p, self.parent, evidence))

    def test_complete_consistency_archive_reconstructs_all_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.parent, self.data)
            result = report.reconstruct(directory)
            self.assertTrue(result["passed"])
            self.assertEqual((result["analyses"], result["fit_starts"]), (60, 120))
            self.assertEqual(result["repeat_artifact_differences"], 0)
            self.assertEqual(len(result["local_sensitivity"]), 20)
            self.assertEqual(sum(c["noiseless_recovery_eligible"] for c in result["cases"]), 12)

    def test_archive_wrong_volume_bias_passes_but_correct_volume_bias_fails(self):
        for arm, should_pass in (("low", True), ("correct", False)):

            def edit(artifacts):
                case = artifacts[f"cases/estimated_rates-{arm}-30-noiseless.json"]
                for fit in case["fits"]:
                    fit["estimates"][2] = fit["evaluated_parameters"][2] = 1.25

            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive_fixture(directory, self.p, self.parent, self.data, edits=edit)
                result = report.reconstruct(directory)
                self.assertEqual(result["passed"], should_pass)
                self.assertEqual(result["gates"]["noiseless_eligible_recovery"], should_pass)

    def test_changed_hash_or_parent_protocol_rejected(self):
        for name in (
            "source-common.py",
            "observations.json",
            "parent.json",
            "repeat/sensitivity.json",
        ):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive_fixture(directory, self.p, self.parent, self.data)
                path = directory / name
                path.write_text(path.read_text() + "\n")
                with self.assertRaises(ValueError):
                    report.reconstruct(directory)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.parent, self.data)
            altered = copy.deepcopy(self.parent)
            altered["model"]["truth"][0] = 1.1
            common.dump(directory / "parent.json", altered)
            manifest = common.read(directory / "manifest.json")
            manifest["files"] = common.file_hashes(directory)
            common.dump(directory / "manifest.json", manifest)
            with self.assertRaises(ValueError):
                report.reconstruct(directory)

    def test_rehashed_repeat_difference_is_still_a_failed_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.parent, self.data)
            path = directory / "repeat" / "worker.json"
            path.write_text(path.read_text() + "\n")
            manifest = common.read(directory / "manifest.json")
            manifest["files"] = common.file_hashes(directory)
            common.dump(directory / "manifest.json", manifest)
            result = report.reconstruct(directory)
            self.assertFalse(result["passed"])
            self.assertEqual(result["repeat_artifact_differences"], 1)

    def test_incomplete_status_and_missing_required_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.parent, self.data)
            manifest = common.read(directory / "manifest.json")
            for status in ("started", "failed", "calculated"):
                manifest["status"] = status
                common.dump(directory / "manifest.json", manifest)
                with self.subTest(status=status), self.assertRaises(ValueError):
                    report.reconstruct(directory)
            self.assertTrue(report.reconstruct(directory, allow_pending=True)["passed"])
            (directory / "repeat" / "worker.json").unlink()
            with self.assertRaises(ValueError):
                report.reconstruct(directory, allow_pending=True)
