"""Independent BC-014 planned-denominator, artifact and interval checks."""

import copy
import math
import unittest
from pathlib import Path

from experiments.m4.coverage.common import observation_specs, read, specifications, validate
from experiments.m4.coverage.plot import render
from experiments.m4.coverage.report import assess_observation, summarize, wilson

PROTOCOL = read(Path(__file__).parents[1] / "experiments/m4/coverage/protocol.json")


class CoverageArtifactTests(unittest.TestCase):
    def test_frozen_roster_has_independent_assessment_seeds_and_paired_designs(self):
        validate(PROTOCOL)
        observations = observation_specs(PROTOCOL)
        cases = specifications(PROTOCOL)
        self.assertEqual(len(observations), 96)
        self.assertEqual(len(cases), 224)
        self.assertEqual(len({s["id"] for s in observations}), 96)
        self.assertEqual(len({s["id"] for s in cases}), 224)
        self.assertNotIn(117, {s["seed"] for s in observations})
        self.assertNotIn(221, {s["seed"] for s in observations})
        self.assertEqual(sum(s["group"] == "gain_boundary" for s in cases), 32)

    def test_wilson_extremes_and_invalid_denominators(self):
        z2 = 1.959963984540054**2
        self.assertEqual(wilson(0, 64)[0], 0)
        self.assertAlmostEqual(wilson(0, 64)[1], z2 / (64 + z2))
        self.assertAlmostEqual(wilson(64, 64)[0], 64 / (64 + z2))
        self.assertEqual(wilson(64, 64)[1], 1)
        for included, planned in ((-1, 64), (65, 64), (0, 0), (True, 64), (1, 2.0)):
            with self.subTest(included=included, planned=planned), self.assertRaises(ValueError):
                wilson(included, planned)

    def test_observation_arithmetic_and_exact_basal_conditioning(self):
        spec = observation_specs(PROTOCOL)[0]
        reference = [[100.0, 50.0, 200.0] for _ in range(241)]
        error = [[0.0, 0.0, 0.0] for _ in range(241)]
        error[3][2] = 3.0
        record = {
            **spec,
            "status": "completed",
            "truth": [1.0] * 4,
            "times": list(range(241)),
            "reference": reference,
            "error": error,
            "observed": [[a + b for a, b in zip(row, e)] for row, e in zip(reference, error)],
            "sd": [5, 10, 30],
            "generator": "unchanged BC-012 reference solver; independent seeded Gaussian errors",
        }
        self.assertEqual(assess_observation(PROTOCOL, spec, record)["observed"][3][2], 203)
        changed = copy.deepcopy(record)
        changed["observed"][3][2] = 202
        with self.assertRaises(ValueError):
            assess_observation(PROTOCOL, spec, changed)
        changed = copy.deepcopy(record)
        changed["error"][0][0] = 5
        changed["observed"][0][0] += 5
        with self.assertRaises(ValueError):
            assess_observation(PROTOCOL, spec, changed)

    def test_failed_case_stays_in_denominator_and_boundary_has_no_nominal_target(self):
        records = []
        for spec in specifications(PROTOCOL):
            records.append(
                {
                    **spec,
                    "status": "completed",
                    "covered": True,
                    "unrestricted_bound_hits": [],
                    "nuisance_bound_hits": [],
                    "reference_refit": False,
                }
            )
        records[0] = {**records[0], "status": "failed", "covered": False}
        result = summarize(PROTOCOL, records)
        primary = result["interior/free_volume"]
        self.assertEqual(
            (primary["planned"], primary["completed"], primary["included"]), (64, 63, 63)
        )
        self.assertAlmostEqual(primary["conservative_rate"], 63 / 64)
        self.assertEqual(primary["completed_rate"], 1)
        self.assertEqual(primary["failed"], 1)
        self.assertFalse(result["gain_boundary/free_volume"]["nominal_reference"])
        self.assertTrue(math.isfinite(primary["wilson_95"][0]))
        with self.assertRaises(ValueError):
            summarize(PROTOCOL, records[:-1])

    def test_figure_is_deterministic_and_labels_boundary_separately(self):
        cases = [
            {
                **spec,
                "status": "completed",
                "covered": True,
                "unrestricted_bound_hits": [],
                "nuisance_bound_hits": [],
                "reference_refit": False,
            }
            for spec in specifications(PROTOCOL)
        ]
        report = {"schema": "bc014-synthetic-coverage/1", "summary": summarize(PROTOCOL, cases)}
        svg = render(report)
        self.assertEqual(svg, render(report))
        self.assertIn("Exact parameter boundary: no nominal 95% target", svg)
        self.assertIn("64/64", svg)
        self.assertIn("32/32", svg)


if __name__ == "__main__":
    unittest.main()
