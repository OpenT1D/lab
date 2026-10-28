"""Independent numerical checks for the six-case observation composition."""

import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path

import numpy as np

from experiments.m4.c_peptide.model import Parameters, simulate
from experiments.m4.feedback_observation.adapter import prepare
from experiments.m4.feedback_observation.common import read
from experiments.m4.kinetic_inlet.forcing import Forcing
from experiments.m4.paired_kinetics.oracle import cpeptide

from .observation import assess, case_ids
from .worker import case_record, run

HERE = Path(__file__).resolve().parent


class ResearcherObservationNumerics(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE.parent / "feedback_observation" / "protocol.json")
        self.params = Parameters(**self.p["cpeptide"]["parameters"])
        self.solver = self.p["solvers"][-1]

    def constant_parent(self, solver="reference"):
        q = 0.7741402585
        times = [i * 0.25 for i in range(961)]
        states = [[0.0] * 20 for _ in times]
        for t, state in zip(times, states, strict=True):
            state[16] = t * q
        return {
            "schema": "m4-causal-trajectory/1",
            "status": "completed",
            "failure": None,
            "mode": "host_constant_basal",
            "load_mg": 30000,
            "solver": next(s for s in self.p["solvers"] if s["name"] == solver),
            "times": times,
            "states": states,
            "baseline": {"Sb_pmol_kg_min": q},
            "source_rates": [[q, q * 0.8] for _ in times],
        }

    def test_host_basal_is_equilibrium_and_pancreatic_input_is_counted_once(self):
        parent = self.constant_parent()
        q = parent["baseline"]["Sb_pmol_kg_min"]
        bundle = prepare(self.p, parent)
        forcing = Forcing(**bundle["forcing"])
        self.assertTrue(all(v == q for v in forcing.left + forcing.right))
        self.assertEqual(bundle["initial"][2:], [0, 0])
        self.assertAlmostEqual(forcing.integral(), q * 240, places=9)
        actual = simulate(bundle["times"], self.params, forcing, bundle["initial"], self.solver)
        np.testing.assert_allclose(
            actual[:, :2], np.tile(bundle["initial"][:2], (961, 1)), atol=1e-10, rtol=0
        )
        self.assertAlmostEqual(actual[-1, 3], q * 240, places=9)
        # The distinct archived liver arrival must not become the valid inlet.
        liver = prepare(self.p, parent, signal="liver_fault")
        self.assertAlmostEqual(Forcing(**liver["forcing"]).integral(), q * 240 * 0.8, places=9)
        self.assertNotEqual(bundle["forcing"], liver["forcing"])

    def test_meal_host_control_equilibrium_is_assessed_without_relabeling_archive(self):
        reference, tight = self.constant_parent(), self.constant_parent("tight")
        case_id = "gastric_load_30g--host_constant_basal"
        record = case_record(self.p, case_id, reference, tight)
        result = assess(self.p, record, reference, tight)
        self.assertLess(result["checks"]["equilibrium_drift_pmol_l"], 1e-7)
        corrupted = copy.deepcopy(record)
        corrupted["states"]["reference"][100][0] += 0.02
        result = assess(self.p, corrupted, reference, tight)
        self.assertGreater(result["checks"]["equilibrium_drift_pmol_l"], 0.3)
        self.assertEqual(record["id"], case_id)
        self.assertEqual(corrupted["id"], case_id)

    def test_linear_pancreatic_ramp_matches_independent_matrix_oracle(self):
        times = np.arange(0, 60.25, 0.25)
        forcing = Forcing([0, 20, 60], [0, 4], [4, 0])
        initial = [0.0] * 4
        actual = simulate(times, self.params, forcing, initial, self.solver)
        np.testing.assert_allclose(
            actual, cpeptide(times, self.params, forcing, initial), atol=1e-8, rtol=0
        )
        self.assertAlmostEqual(actual[-1, 3], 120, places=8)
        self.assertAlmostEqual(sum(actual[-1, :3]), 120, places=8)

    def test_failed_preflight_retains_every_observation_case(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            # An absent frozen protocol prevents numerical execution, but must
            # still leave the entire roster and the original error observable.
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                run(root, "primary")
            status = read(root / "observations/primary/worker.json")
            self.assertEqual(status["status"], "failed")
            self.assertEqual(status["failures"], list(case_ids()))
            for case_id in case_ids():
                item = read(root / "observations/primary/cases" / f"{case_id}.json")
                self.assertEqual(item["id"], case_id)
                self.assertEqual(item["status"], "failed")
                self.assertEqual(item["error"]["type"], "FileNotFoundError")

    def test_existing_partial_label_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            output = root / "observations/repeat"
            output.mkdir(parents=True)
            sentinel = output / "worker.json"
            sentinel.write_text("existing incomplete evidence\n")
            with self.assertRaises(FileExistsError):
                run(root, "repeat")
            self.assertEqual(sentinel.read_text(), "existing incomplete evidence\n")
            self.assertFalse((output / "cases").exists())


if __name__ == "__main__":
    unittest.main()
