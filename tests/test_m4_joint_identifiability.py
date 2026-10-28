"""Independent BC-011 artifact arithmetic; no solver or numerical dependencies."""

import copy
import itertools
import tempfile
import unittest
from pathlib import Path

from experiments.m4.joint_identifiability import common, report


def observations(p):
    """Affine invented signals make selecting the wrong time/channel visible."""
    signal = [[100 + t / 4, 50 + 2 * t, 200 + 3 * t] for t in range(241)]
    datasets, noise = {}, {}
    for name in p["observation"]["data_cases"]:
        error = [[0, 0, 0] for _ in range(241)]
        if name != "noiseless":
            # Handcrafted archived observations, not a noise-generator reference.
            for t in range(241):
                error[t] = [0 if t == 0 else 5, 0 if t == 0 else -10, 30]
        datasets[name] = [
            [value + delta for value, delta in zip(row, perturbation)]
            for row, perturbation in zip(signal, error)
        ]
        noise[name] = error
    return {
        "truth": [1.0, 1.0, 1.0],
        "times": list(range(241)),
        "reference": signal,
        "datasets": datasets,
        "noise": noise,
    }


def case_fixture(
    p, data, *, regime="unknown_clearance", modality="GI", step=30, dataset="noiseless"
):
    spec = {
        "id": f"{regime}-{modality}-{step}-{dataset}",
        "regime": regime,
        "modality": modality,
        "step": step,
        "data": dataset,
    }
    active = [0] if regime == "known_kinetics" else ([0, 1, 2] if modality == "GIC" else [0, 1])
    columns = {"G": [0], "GI": [0, 1], "GIC": [0, 1, 2]}[modality]
    times = list(range(0, 241, step))
    selected = [[data["datasets"][dataset][t][c] for c in columns] for t in times]
    fits = []
    for start in p["inference"]["starts"]:
        fits.append(
            {
                "start": list(start),
                "active_parameters": active[:],
                "status": "completed",
                "optimizer_status": 1,
                "message": "Handcrafted arithmetic fixture; no optimizer invoked",
                "estimates": [1.0 if j in active else None for j in range(3)],
                "prediction": copy.deepcopy(selected),
                "residuals": [0.0] * (len(times) * len(columns)),
                "objective": 0.0,
                "nfev": 1,
                "model_calls": 1,
                "optimality": 0.0,
                "bound_hits": [],
            }
        )
    case = {
        **spec,
        "times": times,
        "columns": columns,
        "observed": selected,
        "active_parameters": active,
        "unobservable": ["k3_scale"] if regime == "unknown_clearance" and modality != "GIC" else [],
        "fixed_parameters": {"m4_scale": 1, "k3_scale": 1} if regime == "known_kinetics" else {},
        "fits": fits,
    }
    return spec, case


def sensitivity_fixture(p):
    """Three orthogonal coordinate columns with singular values 3, 2, 1."""
    full = [[0.0] * 3 for _ in range(723)]
    full[30 * 3][0], full[60 * 3][1], full[30 * 3 + 2][2] = 3.0, 2.0, 1.0
    records = []
    for regime, modality, step in itertools.product(
        ("known_kinetics", "unknown_clearance"), ("G", "GI", "GIC"), (10, 30)
    ):
        columns = {"G": [0], "GI": [0, 1], "GIC": [0, 1, 2]}[modality]
        rows = [t * 3 + c for t in range(0, 241, step) for c in columns]
        declared = [0] if regime == "known_kinetics" else [0, 1, 2]
        active = declared if modality == "GIC" or regime == "known_kinetics" else [0, 1]
        j = [[full[row][col] for col in declared] for row in rows]
        singular = [3.0] if len(declared) == 1 else [3.0, 2.0, 1.0 if modality == "GIC" else 0.0]
        u = [[0.0] * len(declared) for _ in rows]
        for col, source_row in enumerate((30 * 3, 60 * 3, 30 * 3 + 2)[: len(declared)]):
            u[rows.index(source_row) if source_row in rows else 0][col] = 1.0
        records.append(
            {
                "regime": regime,
                "modality": modality,
                "step": step,
                "declared_parameters": declared,
                "active_parameters": active,
                "jacobian": j,
                "left_vectors": u,
                "right_vectors": [[float(i == k) for k in declared] for i in declared],
                "singular_values": singular,
                "rank": len(active),
                "condition_number": singular[0] / singular[-1] if singular[-1] else None,
                "unobservable": ["k3_scale"] if len(active) != len(declared) else [],
                "k3_numerical_leakage_max": 0.0,
            }
        )
    return {
        "passed": True,
        "checks": {
            "jacobian_relative_refinement_error": 0.0,
            "jacobian_solver_relative_error": 0.0,
        },
        "full_weighted_log_jacobians": {
            f"{solver}-{step}": copy.deepcopy(full)
            for solver in ("fit", "reference")
            for step in (0.002, 0.001)
        },
        "records": records,
    }


def archive_fixture(directory, p, data, *, edit_sensitivity=None, edit_verification=None):
    """Artifact-consistency fixture only; these values are not model evidence."""
    for name in common.required_files(p):
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Handcrafted artifact-consistency fixture\n")
    common.dump(directory / "protocol.json", p)
    checks = {
        name: {"value": 0.0, "limit": limit, "passed": True}
        for name, limit in common.forward_check_specifications(p).items()
    }
    verification = {"passed": True, "checks": checks, "details": {}}
    sensitivity = sensitivity_fixture(p)
    if edit_sensitivity:
        edit_sensitivity(sensitivity)
    if edit_verification:
        edit_verification(verification)
    artifacts = {
        "worker.json": {"runtime": {"python": "3.12.11", "numpy": "1.26.4", "scipy": "1.13.1"}},
        "verification.json": verification,
        "sensitivity.json": sensitivity,
        "observations.json": data,
    }
    for regime, modality, step, dataset in itertools.product(
        ("known_kinetics", "unknown_clearance"),
        ("G", "GI", "GIC"),
        (10, 30),
        ("noiseless", "noise_117", "noise_221"),
    ):
        spec, case = case_fixture(
            p, data, regime=regime, modality=modality, step=step, dataset=dataset
        )
        artifacts[f"cases/{spec['id']}.json"] = case
    for name, value in artifacts.items():
        common.dump(directory / name, value)
        common.dump(directory / "repeat" / name, value)
    common.dump(
        directory / "manifest.json",
        {
            "schema": common.VERSION,
            "status": "completed",
            "files": common.file_hashes(directory),
        },
    )


class JointIdentifiabilityTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.HERE / "protocol.json")
        self.data = observations(self.p)

    def case(self, **kwargs):
        return case_fixture(self.p, self.data, **kwargs)

    def assess(self, spec, case):
        return report.assess_case(self.p, spec, case, self.data)

    def test_frozen_matrix_contains_every_distinct_analysis(self):
        expected = {
            f"{r}-{m}-{s}-{d}"
            for r, m, s, d in itertools.product(
                ("known_kinetics", "unknown_clearance"),
                ("G", "GI", "GIC"),
                (10, 30),
                ("noiseless", "noise_117", "noise_221"),
            )
        }
        actual = common.specifications(self.p)
        self.assertEqual(len(actual), 36)
        self.assertEqual({case["id"] for case in actual}, expected)
        numeric = common.numerical_files(self.p)
        self.assertEqual(len(numeric), 40)
        self.assertTrue({"repeat/" + name for name in numeric} <= common.required_files(self.p))

    def test_frozen_protocol_rejects_scientific_and_acceptance_changes(self):
        common.validate(self.p)
        for key, change in (
            ("model", lambda x: x["truth"].__setitem__(0, 1.1)),
            ("observation", lambda x: x["noise_seeds"].append(999)),
            ("inference", lambda x: x.__setitem__("svd_relative_cutoff", 0.1)),
            ("criteria", lambda x: x.__setitem__("noiseless_active_parameter_relative_error", 0.5)),
        ):
            altered = copy.deepcopy(self.p)
            change(altered[key])
            with self.subTest(key=key), self.assertRaises(ValueError):
                common.validate(altered)

    def test_hand_computed_weighted_objective_errors_and_best_start(self):
        spec, case = self.case()
        first, second = case["fits"]
        first["estimates"], second["estimates"] = [0.9, 1.1, None], [1.02, 0.95, None]
        for fit, factor in ((first, 1), (second, 0.5)):
            fit["prediction"] = [
                [g + 5 * factor, insulin - 20 * factor] for g, insulin in case["observed"]
            ]
            fit["residuals"] = [factor, -2 * factor] * 9
            fit["objective"] = 45 * factor**2
        result = self.assess(spec, case)
        self.assertEqual(result["fits"][0]["objective"], 45)
        self.assertEqual(result["best"]["objective"], 11.25)
        self.assertAlmostEqual(result["best"]["max_active_relative_error"], 0.05)
        self.assertAlmostEqual(result["start_max_absolute_disagreement"], 0.15)
        self.assertIsNone(result["fits"][0]["relative_errors"][2])
        self.assertFalse(result["noiseless_recovered"])

    def test_one_recovered_start_does_not_hide_second_start_failure(self):
        spec, case = self.case()
        case["fits"][1]["estimates"][0] = 1.02
        result = self.assess(spec, case)
        self.assertEqual(result["best"]["max_active_relative_error"], 0)
        self.assertFalse(result["noiseless_recovered"])

    def test_noisy_recovery_not_mislabeled_as_noiseless_acceptance(self):
        spec, case = self.case(dataset="noise_117")
        result = self.assess(spec, case)
        self.assertIsNone(result["noiseless_recovered"])

    def test_unobservable_and_fixed_parameters_must_remain_null(self):
        for regime, modality, slot in (
            ("unknown_clearance", "G", 2),
            ("unknown_clearance", "GI", 2),
            ("known_kinetics", "GIC", 1),
            ("known_kinetics", "GI", 2),
        ):
            spec, case = self.case(regime=regime, modality=modality)
            case["fits"][0]["estimates"][slot] = 1.0
            with (
                self.subTest(regime=regime, modality=modality, slot=slot),
                self.assertRaises(ValueError),
            ):
                self.assess(spec, case)
        spec, case = self.case()
        case["unobservable"] = []
        with self.assertRaises(ValueError):
            self.assess(spec, case)

    def test_selected_time_channel_and_dataset_cannot_change(self):
        for change in (
            lambda x: x["times"].__setitem__(1, 29),
            lambda x: x.__setitem__("columns", [1, 0]),
            lambda x: x["observed"][1].__setitem__(0, 107.25),
            lambda x: x.__setitem__("data", "noise_221"),
        ):
            spec, case = self.case()
            change(case)
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_missing_changed_or_reordered_starts_rejected(self):
        for change in (
            lambda x: x["fits"].pop(),
            lambda x: x["fits"].reverse(),
            lambda x: x["fits"][0]["start"].__setitem__(0, 1),
            lambda x: x["fits"][0].__setitem__("active_parameters", [0, 1, 2]),
        ):
            spec, case = self.case()
            change(case)
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_invalid_estimates_and_incomplete_predictions_rejected(self):
        for value in (True, float("nan"), float("inf"), 0.499, 1.501):
            spec, case = self.case()
            case["fits"][0]["estimates"][0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.assess(spec, case)
        for change in (
            lambda x: x["prediction"].pop(),
            lambda x: x["residuals"].pop(),
            lambda x: x["prediction"][0].__setitem__(0, float("nan")),
            lambda x: x.__setitem__("objective", 1),
            lambda x: x["residuals"].__setitem__(0, 1),
        ):
            spec, case = self.case()
            change(case["fits"][0])
            with self.assertRaises(ValueError):
                self.assess(spec, case)

    def test_failed_model_retained_in_denominator_without_fake_estimate(self):
        spec, case = self.case()
        case["fits"][1] = {
            "start": self.p["inference"]["starts"][1],
            "active_parameters": [0, 1],
            "status": "model_failed",
            "error": {"type": "ValueError", "message": "Incomplete integration"},
        }
        result = self.assess(spec, case)
        self.assertEqual(len(result["fits"]), 2)
        self.assertEqual(result["fits"][1]["status"], "model_failed")
        self.assertNotIn("estimates", result["fits"][1])
        self.assertFalse(result["noiseless_recovered"])
        self.assertIsNone(result["start_max_absolute_disagreement"])

    def test_optimizer_termination_cannot_be_promoted_to_completion(self):
        spec, case = self.case()
        case["fits"][0]["optimizer_status"] = 0
        with self.assertRaises(ValueError):
            self.assess(spec, case)
        case["fits"][0]["status"] = "optimizer_failed"
        result = self.assess(spec, case)
        self.assertEqual(len(result["fits"]), 2)
        self.assertFalse(result["noiseless_recovered"])

    def test_bound_hits_are_reconstructed_from_estimates(self):
        spec, case = self.case()
        case["fits"][0]["estimates"][0] = 0.5
        with self.assertRaises(ValueError):
            self.assess(spec, case)
        case["fits"][0]["bound_hits"] = [0]
        self.assertEqual(self.assess(spec, case)["fits"][0]["bound_hits"], [0])
        case["fits"][0]["bound_hits"] = [0, 2]
        with self.assertRaises(ValueError):
            self.assess(spec, case)

    def test_svd_reconstructs_orthogonal_columns_and_exact_null(self):
        records = sensitivity_fixture(self.p)["records"]
        for record in records:
            result = report.svd_check(record, self.p)
            expected = (
                1
                if record["regime"] == "known_kinetics"
                else (3 if record["modality"] == "GIC" else 2)
            )
            self.assertEqual(result["rank"], expected)
            self.assertNotIn("jacobian", result)
            self.assertNotIn("left_vectors", result)

    def test_svd_rejects_wrong_factorization_orthogonality_and_rank(self):
        original = sensitivity_fixture(self.p)["records"][-1]
        for change in (
            lambda x: x["jacobian"][0].__setitem__(0, 0.1),
            lambda x: x["left_vectors"][0].__setitem__(0, 1),
            lambda x: x["right_vectors"][0].__setitem__(1, 1),
            lambda x: x.__setitem__("rank", 2),
            lambda x: x["singular_values"].__setitem__(0, -3),
            lambda x: x["jacobian"].pop(),
        ):
            record = copy.deepcopy(original)
            change(record)
            with self.assertRaises(ValueError):
                report.svd_check(record, self.p)

    def test_valid_but_ascending_singular_factorization_rejected(self):
        record = sensitivity_fixture(self.p)["records"][-1]
        # Reverse all three SVD factors together: reconstruction and orthogonality
        # remain valid, but singular[0] no longer defines the relative cutoff.
        record["singular_values"].reverse()
        record["right_vectors"].reverse()
        for row in record["left_vectors"]:
            row.reverse()
        with self.assertRaises(ValueError):
            report.svd_check(record, self.p)

    def test_complete_handcrafted_archive_reconstructs_all_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.data)
            result = report.reconstruct(directory)
            self.assertTrue(result["passed"])
            self.assertEqual(result["analyses"], 36)
            self.assertEqual(result["fit_starts"], 72)
            self.assertEqual(len(result["local_sensitivity"]), 12)
            self.assertEqual(result["repeat_artifact_differences"], 0)

    def test_duplicate_missing_and_unbound_sensitivity_evidence_rejected(self):
        for edit in (
            lambda x: x["records"].__setitem__(1, copy.deepcopy(x["records"][0])),
            lambda x: x["records"].pop(),
            lambda x: x.__setitem__("checks", {}),
            lambda x: x["full_weighted_log_jacobians"].pop("fit-0.002"),
            lambda x: x["full_weighted_log_jacobians"]["reference-0.001"][0].__setitem__(0, 1),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive_fixture(directory, self.p, self.data, edit_sensitivity=edit)
                with self.assertRaises(ValueError):
                    report.reconstruct(directory)

    def test_incomplete_or_falsely_passing_forward_checks_rejected(self):
        for edit in (
            lambda x: x["checks"].pop("independent_cpeptide"),
            lambda x: x["checks"]["independent_cpeptide"].__setitem__("limit", 100),
            lambda x: x["checks"]["independent_cpeptide"].__setitem__("value", 100),
            lambda x: x["checks"]["independent_cpeptide"].__setitem__("value", -1),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive_fixture(directory, self.p, self.data, edit_verification=edit)
                with self.assertRaises(ValueError):
                    report.reconstruct(directory)

    def test_rehashing_different_repeat_preserves_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            archive_fixture(directory, self.p, self.data)
            path = directory / "repeat" / "worker.json"
            path.write_text(path.read_text() + "\n")
            manifest = common.read(directory / "manifest.json")
            manifest["files"] = common.file_hashes(directory)
            common.dump(directory / "manifest.json", manifest)
            result = report.reconstruct(directory)
            self.assertFalse(result["passed"])
            self.assertEqual(result["repeat_artifact_differences"], 1)
            self.assertFalse(result["gates"]["fresh_process_repeat"])

    def test_changed_source_or_numeric_artifact_rejected_by_hash(self):
        for name in ("source-common.py", "observations.json", "repeat/sensitivity.json"):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                archive_fixture(directory, self.p, self.data)
                path = directory / name
                path.write_text(path.read_text() + "\n")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    report.reconstruct(directory)

    def test_incomplete_or_failed_archives_never_reconstruct_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            common.dump(directory / "protocol.json", self.p)
            for status in ("started", "failed", "calculated", "completed"):
                common.dump(
                    directory / "manifest.json",
                    {
                        "schema": common.VERSION,
                        "status": status,
                        "files": {},
                    },
                )
                with self.subTest(status=status), self.assertRaises(ValueError):
                    report.reconstruct(directory)
