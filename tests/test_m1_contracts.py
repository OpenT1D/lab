import math
import unittest
from dataclasses import replace

from experiments.m1.contracts import Action, Config, Observation, Row, validate_rows
from experiments.m1.metrics import exposure, summarize


class Contracts(unittest.TestCase):
    def test_reject_bad_configuration(self):
        for kwargs in (
            {"profile": "adult#003"},
            {"seed": True},
            {"seed": 1},
            {"schema": "future"},
            {"condition": "AB"},
            {"controller": "mpc"},
        ):
            with self.assertRaises(ValueError):
                Config(**kwargs)
        self.assertEqual(Config().to_dict()["seed"], 101)

    def test_numbers_and_clock(self):
        for bad in (None, "1", True, [], {}, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                Action(bad, 0)
        Action(-1, 0)  # native pump owns negative-command limiting
        Observation(6, 100, 3, False)
        for args in ((6, 100, 9, True), (4, 100, 3, False), (6, 100, 3, True)):
            with self.assertRaises(ValueError):
                Observation(*args)

    def test_intervals_and_terminal(self):
        first = Row(0, 3, 100, 101, True, 102, 0, 0, 0, -1, 0, 0, False)
        self.assertEqual(validate_rows([first]), 3)
        for rows in (
            [replace(first, start_min=3, end_min=6)],
            [replace(first, terminal=True), replace(first, start_min=3, end_min=6)],
        ):
            with self.assertRaises(ValueError):
                validate_rows(rows)
        with self.assertRaises(ValueError):
            replace(first, delivered_u_min=-1)
        self.assertEqual(summarize([first])["glucose"]["observed_minutes"], 0)

    def test_independent_threshold_and_weight_fixture(self):
        result = exposure(
            [(53, 1), (54, 1), (69, 1), (70, 1), (180, 1), (181, 1), (250, 1), (251, 1), (None, 2)],
            10,
        )
        self.assertEqual(result["in_70_180_percent"], 25)
        self.assertEqual(result["below_70_percent"], 37.5)
        self.assertEqual(result["below_54_percent"], 12.5)
        self.assertEqual(result["above_180_percent"], 37.5)
        self.assertEqual(result["above_250_percent"], 12.5)
        self.assertEqual(result["coverage_percent"], 80)
        weighted = exposure([(100, 1), (200, 3)], 4)
        self.assertEqual(weighted["mean_mg_dl"], 175)
        self.assertEqual(weighted["sd_mg_dl"], math.sqrt(1875))
        self.assertIsNone(exposure([], 10)["mean_mg_dl"])
        self.assertIsNone(exposure([(0, 1)], 1)["cv_percent"])
        for bad in ("100", float("nan"), True):
            with self.assertRaises(ValueError):
                exposure([(bad, 3)], 3)

    def test_scored_insulin_and_missing_sensor(self):
        rows = [
            Row(t, t + 3, 100, 200, t + 3 != 1443, 999, t, 0, 0, 1, 2, 0.5, False)
            for t in range(0, 1446, 3)
        ]
        metrics = summarize(rows)
        self.assertEqual(metrics["delivered_insulin_u"], 3)
        self.assertEqual(metrics["glucose"]["observed_minutes"], 6)
        self.assertEqual(metrics["sensor"]["observed_minutes"], 3)
        self.assertEqual(metrics["sensor"]["mean_mg_dl"], 200)
        self.assertEqual(metrics["sensor"]["missing_minutes"], 1437)
