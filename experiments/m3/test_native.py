"""Execute with the isolated M3 runtime: native estimator and preprocessing checks."""

import copy
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from experiments.m3.common import save
from experiments.m3.data import load_observations, training_windows
from experiments.m3.estimator import SETTINGS, fit, predict
from experiments.m3.fixtures import generate
from experiments.m3.workflow import fit_worker


class NativeEstimatorTests(unittest.TestCase):
    def test_native_ridge_and_saved_coefficients(self):
        samples = {
            "one": [(i, [100 + i + j for j in range(6)], 120 + i) for i in range(10)],
            "two": [(i, [150 + i * 2 + j for j in range(6)], 160 + i) for i in range(20)],
        }
        saved = fit(samples)
        x = [w[1] for v in samples.values() for w in v]
        y = [w[2] for v in samples.values() for w in v]
        weights = [1 / len(v) for v in samples.values() for _ in v]
        native_scaler = StandardScaler().fit(x, sample_weight=weights)
        native = Ridge(**SETTINGS).fit(native_scaler.transform(x), y, sample_weight=weights)
        self.assertEqual(saved["coef"], native.coef_.tolist())
        self.assertEqual(saved["mean"], native_scaler.mean_.tolist())
        discrepancies = [
            abs(predict(saved, features) - float(expected))
            for features, expected in zip(
                x, native.predict(native_scaler.transform(x)), strict=True
            )
        ]
        # Six-term scalar accumulation vs BLAS dot: measured at <=1 ULP locally.
        # A 16-operation floating rounding budget, not a scientific error tolerance.
        for error, expected in zip(
            discrepancies, native.predict(native_scaler.transform(x)), strict=True
        ):
            self.assertLessEqual(error, 16 * math.ulp(float(expected)))
        self.assertEqual(fit(samples), saved)
        self.assertTrue(np.isfinite(saved["singular_values"]).all())

    def test_validation_changes_cannot_change_fit_and_eval_is_never_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            value = generate(data)
            plan = {"registry": value, "input_root": str(data)}
            samples = {}
            for person in value["people"]:
                rows, _ = load_observations(data, person, "train", value["clock"])
                samples[person["id"]] = training_windows(rows, person)
            expected = fit(samples)
            for person in value["people"]:
                # Reading XML/JSON evaluation values here is forbidden by an actual open guard.
                (data / person["evaluation"]["file"]).unlink()
                path = data / person["train"]["file"]
                import json

                obj = json.loads(path.read_bytes())
                for row in obj["rows"]:
                    if row["time"] >= 2304 and row["value"] is not None:
                        row["value"] += 50
                save(path, obj)
                from experiments.m3.common import digest

                person["train"]["sha256"] = digest(path.read_bytes())
            output = root / "fit"
            output.mkdir()
            with patch("experiments.m3.workflow.plan_read", return_value=(plan, "test-plan")):
                fit_worker(root / "unused-plan", output)
            import json

            actual = json.loads((output / "model.json").read_text())
            self.assertEqual(actual, expected)

    def test_patient_weighting_and_no_hidden_estimator_state(self):
        samples = {
            "a": [(i, [i + j for j in range(6)], i + 10) for i in range(10)],
            "b": [(i, [i + j + 30 for j in range(6)], i + 40) for i in range(20)],
        }
        original = fit(samples)
        other = copy.deepcopy(samples)
        for windows in other.values():
            for _, x, _ in windows:
                x[0] += 1000
        fit(other)
        self.assertEqual(fit(samples), original)
        # Native weighted mean has one-ULP rounding from 0.1/0.05 sample weights.
        self.assertLessEqual(abs(original["mean"][0] - 22.0), math.ulp(22.0))


class NativeWorkflowTest(unittest.TestCase):
    def test_small_synthetic_workflow_and_frozen_artifact_reconstruction(self):
        from experiments.m3.analysis import reconstruct
        from experiments.m3.common import provenance
        from experiments.m3.workflow import fit_plan, freeze, run_study

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generate(root / "data")
            # Format/lifecycle unit test. The verify command requires a real clean commit.
            synthetic_prov = provenance()
            synthetic_prov["dirty"] = False
            with patch("experiments.m3.workflow.provenance", return_value=synthetic_prov):
                freeze(root / "data/registry.json", root / "plan")
            fit_plan(root / "plan/plan.json", root / "fit")
            result = run_study(root / "plan/plan.json", root / "fit", root / "study")
            self.assertEqual(result, reconstruct(root / "study"))
            self.assertEqual(result["status_counts"], {"completed": 6})
            self.assertEqual(sum(p["planned"] for p in result["people"]), 1728)
