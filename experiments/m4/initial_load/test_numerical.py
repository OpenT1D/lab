"""New 15g initial-condition/refinement checks in the unchanged native lock."""

import unittest
from dataclasses import asdict

from experiments.m4.causal_secretion import common as causal
from experiments.m4.causal_secretion import coupled, example_model
from experiments.m4.causal_secretion.report import inspect
from experiments.m4.feedback import coupled as reference_coupled
from experiments.m4.feedback import secretion
from experiments.m4.feedback.contract import baseline
from experiments.m4.kinetic_inlet.native import load

from .common import ROOT, protocol, read


class InitialLoadNumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = protocol()
        cls.bc = read(ROOT / "experiments/m4/feedback/protocol.json")
        cls.task = read(ROOT / "experiments/m4/causal_secretion/protocol.json")
        native, cls.identity = load()
        cls.params = {
            key: (str(value) if key == "Name" else float(value))
            for key, value in native.to_dict().items()
        }
        cls.gamma = cls.bc["source"]["parameters"]["gamma_per_min"]
        cls.basal = baseline(
            cls.params, [float(value) for value in native.iloc[2:15]], 0.25, cls.gamma
        )
        cls.declared = causal.declaration(
            read(ROOT / "experiments/m4/causal_secretion/example_model.json")
        )
        cls.records = {}
        for solver in cls.p["numerical"]["solvers"]:
            item, _ = coupled.integrate(
                cls.task,
                cls.bc,
                cls.params,
                cls.basal,
                cls.gamma,
                15000,
                solver,
                example_model.evaluate,
                cls.declared["parameters"],
                "candidate",
            )
            item.update(model_source_sha256=cls.declared["source_sha256"], gamma_per_min=cls.gamma)
            cls.records[solver["name"]] = item

    def test_midpoint_initial_state_grid_and_independent_inventory(self):
        for solver in self.p["numerical"]["solvers"]:
            item = self.records[solver["name"]]
            self.assertEqual(item["load_mg"], 15000)
            self.assertEqual(item["initial"][0], 15000)
            self.assertEqual(item["times"], [index * 0.25 for index in range(961)])
            result = inspect(
                item,
                self.bc,
                self.task,
                self.params,
                self.basal,
                self.gamma,
                {"id": "gastric_load_15g", "stomach_solid_mg": 15000},
                "candidate",
                solver,
                self.declared["source_sha256"],
            )
            for key, value in result["metrics"].items():
                self.assertLessEqual(value, self.p["numerical"]["criteria"][key])

    def test_both_refinement_levels_meet_frozen_limits(self):
        reference = self.records["reference"]
        for name in ("coarse", "tight"):
            candidate = self.records[name]
            for key, column, volume in (
                ("glucose_solver_error_mg_dl", 3, self.params["Vg"]),
                ("insulin_solver_error_pmol_l", 5, self.params["Vi"]),
            ):
                error = max(
                    abs(a[column] - b[column]) / volume
                    for a, b in zip(candidate["states"], reference["states"], strict=True)
                )
                self.assertLessEqual(error, self.p["numerical"]["criteria"][key])
            error = max(
                abs(a - b)
                for left, right in zip(
                    candidate["source_rates"], reference["source_rates"], strict=True
                )
                for a, b in zip(left, right, strict=True)
            )
            self.assertLessEqual(
                error, self.p["numerical"]["criteria"]["source_solver_error_pmol_kg_min"]
            )

    def test_midpoint_constant_control_matches_independent_feedback_equations(self):
        solver = self.p["numerical"]["solvers"][-1]
        item, _ = coupled.integrate(
            self.task,
            self.bc,
            self.params,
            self.basal,
            self.gamma,
            15000,
            solver,
            example_model.evaluate,
            self.declared["parameters"],
            "host_constant_basal",
        )
        source = secretion.parameters(self.bc, self.basal, 0)
        reference, _ = reference_coupled.integrate(
            self.bc, self.params, self.basal, source, 15000, solver
        )
        reference["source_parameters"] = asdict(source)
        for key in (
            "times",
            "states",
            "source_rates",
            "glucose_flux_integrals",
            "initial",
            "baseline",
        ):
            self.assertEqual(item[key], reference[key])


if __name__ == "__main__":
    unittest.main()
