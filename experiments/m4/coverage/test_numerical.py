"""Native regression and noise-boundary checks for the BC-014 driver."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from experiments.m4.volume_sensitivity.model import Model

from .common import HERE, dump, read, validate
from .report import assess_case, assess_observation
from .worker import fit_one, generate


class CoverageNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = read(HERE / "protocol.json")
        validate(cls.protocol)
        cls.profile = read(HERE.parent / "profile_likelihood" / "protocol.json")
        cls.volume = read(HERE.parent / "volume_sensitivity" / "protocol.json")

    def test_generation_matches_independent_seeded_noise_and_boundary_truth(self):
        model = Model(self.volume)
        sd = np.asarray(self.volume["observation"]["synthetic_sd"])
        for group in ("interior", "gain_boundary"):
            spec = {"group": group, "seed": 117, "id": f"{group}-117"}
            result = generate(model, self.protocol, spec)
            truth = self.protocol["design"][group]["truth"]
            expected_reference = model.simulate(truth, solver="reference")["observations"]
            draw = np.random.default_rng(117).normal(size=(241, 3)) * sd
            draw[0, :2] = 0
            np.testing.assert_array_equal(result["reference"], expected_reference)
            np.testing.assert_array_equal(result["error"], draw)
            np.testing.assert_allclose(
                result["observed"], expected_reference + draw, rtol=0, atol=0
            )
            self.assertEqual(result["error"][0][:2], [0, 0])
        self.assertNotEqual(
            generate(
                model, self.protocol, {"group": "interior", "seed": 118, "id": "interior-118"}
            )["error"],
            result["error"],
        )

    def test_targeted_fit_matches_preassessment_development_benchmark(self):
        # Seed 117 was used in BC-013 development, not in the BC-014 assessment.
        with tempfile.TemporaryDirectory() as name:
            source = Path(name)
            (source / "observations").mkdir()
            (source / "cases").mkdir()
            dump(source / "parent-profile.json", self.profile)
            dump(source / "parent-volume.json", self.volume)
            spec = {
                "group": "interior",
                "seed": 117,
                "design": "free_volume",
                "id": "interior-117-free_volume",
            }
            observation = generate(
                Model(self.volume),
                self.protocol,
                {"group": "interior", "seed": 117, "id": "interior-117"},
            )
            dump(source / "observations" / "interior-117.json", observation)
            self.assertEqual(fit_one((name, name, self.protocol, self.profile, spec)), spec["id"])
            record = read(source / "cases" / (spec["id"] + ".json"))
            self.assertEqual(record["status"], "completed", record.get("error"))
            self.assertEqual(len(record["baseline"]), 3)
            self.assertEqual(len(record["constrained"]), 2)
            self.assertTrue(all(record["gates"].values()))
            self.assertAlmostEqual(
                min(f["objective"] for f in record["baseline"]), 23.028091205359722, delta=0.001
            )
            self.assertAlmostEqual(
                min(f["objective"] for f in record["constrained"]),
                23.991701550918993,
                delta=0.001,
            )
            checked_observation = assess_observation(
                self.protocol,
                {"group": "interior", "seed": 117, "id": "interior-117"},
                observation,
            )
            checked_case = assess_case(
                self.protocol, self.profile, spec, record, checked_observation
            )
            self.assertEqual(checked_case["status"], "completed")

    def test_failed_observation_is_retained_without_coverage(self):
        with tempfile.TemporaryDirectory() as name:
            source = Path(name)
            (source / "observations").mkdir()
            (source / "cases").mkdir()
            dump(source / "parent-profile.json", self.profile)
            dump(source / "parent-volume.json", self.volume)
            spec = {
                "group": "interior",
                "seed": 117,
                "design": "GI",
                "id": "interior-117-GI",
            }
            # Wrong time-grid shape fails before optimizer calls; it cannot
            # produce a completed coverage result.
            dump(
                source / "observations" / "interior-117.json",
                {"times": [0], "observed": [[100, 100, 100]]},
            )
            fit_one((name, name, self.protocol, self.profile, spec))
            record = json.loads((source / "cases" / (spec["id"] + ".json")).read_text())
            self.assertEqual(record["status"], "failed")
            self.assertFalse(record["covered"])
            self.assertEqual(record["baseline"], [])
            self.assertEqual(record["error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
