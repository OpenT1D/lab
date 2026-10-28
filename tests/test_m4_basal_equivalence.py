"""Pure contract and search-policy checks for the synthetic M4 comparison."""

import copy
import tempfile
import unittest
from pathlib import Path

from experiments.m4.basal_equivalence.common import (
    next_step,
    no_solution_confirmation_factors,
    protocol,
    sc_context,
    verify_reference_adapter,
)
from experiments.m4.paired_kinetics.common import read


class BasalEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.task = read("experiments/m4/basal_equivalence/protocol.json")
        self.bc = read("experiments/m4/feedback/protocol.json")

    def history(self, values):
        return [
            {"factor": factor, "auc": auc}
            for factor, auc in zip(
                self.task["sc_rate_multipliers_of_native_u2ss"], values, strict=True
            )
        ]

    def test_protocol_is_frozen_before_numerical_execution(self):
        self.assertEqual(protocol(self.task, self.bc), self.task)
        changed = copy.deepcopy(self.task)
        changed["auc_match_tolerance_mg_min_dl"] = 2.0
        with self.assertRaisesRegex(ValueError, "frozen"):
            protocol(changed, self.bc)

    def test_reference_adapter_is_pinned_for_bc008_parity(self):
        source = Path("experiments/m4/causal_secretion/example_model.json")
        verify_reference_adapter(source)
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "model.json"
            changed.write_bytes(source.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "pinned"):
                verify_reference_adapter(changed)

    def test_search_matches_grid_and_bisects_without_extrapolation(self):
        history = self.history([100, 90, 80, 70, 60])
        self.assertEqual(next_step(history[:2], 85, self.task), ("grid", 0.75))
        self.assertEqual(next_step(history, 80, self.task), ("matched", 0.75))
        self.assertEqual(next_step(history, 85, self.task), ("bisect", 0.6875))
        self.assertEqual(next_step(history, 110, self.task), ("unbracketed", None))

    def test_nonmonotonic_and_resolution_limit_are_visible(self):
        self.assertEqual(
            next_step(self.history([100, 90, 95, 70, 60]), 85, self.task),
            ("nonmonotonic", None),
        )
        short = copy.deepcopy(self.task)
        short["max_bisections"] = 0
        self.assertEqual(
            next_step(self.history([100, 90, 80, 70, 60]), 85, short),
            ("resolution_limit", None),
        )
        self.assertEqual(
            no_solution_confirmation_factors(self.history([100, 90, 80, 70, 60]), 110, self.task),
            self.task["sc_rate_multipliers_of_native_u2ss"],
        )

    def test_only_post_zero_sc_infusion_changes(self):
        basal = {
            "state": [1.0, 2.0],
            "Sb_pmol_kg_min": 3.0,
            "Z_pmol_kg_min": 3.0,
            "P_pmol_kg": 6.0,
            "h_mg_dl": 100.0,
            "u_sc_pmol_kg_min": 7.5,
            "action_insulin_u_min": 0.075,
        }
        updated = sc_context(basal, {"u2ss": 10.0, "BW": 60.0}, 0.8)
        self.assertEqual(updated["state"], basal["state"])
        for name in ("Sb_pmol_kg_min", "Z_pmol_kg_min", "P_pmol_kg", "h_mg_dl"):
            self.assertEqual(updated[name], basal[name])
        self.assertEqual(updated["u_sc_pmol_kg_min"], 8.0)
        self.assertEqual(updated["action_insulin_u_min"], 0.08)


if __name__ == "__main__":
    unittest.main()
