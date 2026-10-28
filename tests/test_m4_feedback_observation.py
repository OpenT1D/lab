"""Boundary, independent accounting and failed-archive tests without SciPy."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.feedback_observation import adapter, common, report, run


def parent_fixture(q=1):
    times = [i * 0.25 for i in range(961)]
    states = [[0.0] * 20 for _ in times]
    for t, row in zip(times, states):
        row[16] = q * t
    return dict(
        status="completed",
        failure=None,
        times=times,
        source_rates=[[q, q] for _ in times],
        baseline={"Sb_pmol_kg_min": q},
        states=states,
    )


def equilibrium(bundle):
    q = bundle["basal_pmol_kg_min"]
    return [[*bundle["initial"][:2], q * t, q * t] for t in bundle["times"]]


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.HERE / "protocol.json")
        self.source = parent_fixture()

    def fixture(self):
        b = adapter.prepare(self.p, self.source)
        return dict(
            id="fasting--constant_basal--fixed",
            status="completed",
            boundary=b,
            states={n: equilibrium(b) for n in ("tight", "reference")},
            oracle=equilibrium(b),
            diagnostics={
                n: dict(boundary=v, states=equilibrium(v))
                for n, v in adapter.diagnostic_inputs(self.p, self.source, self.source).items()
            },
        )

    def test_no_second_conversion_or_basal_addition(self):
        self.source["body_weight_kg"] = 102.32
        self.source["baseline"]["u_sc_pmol_kg_min"] = 100
        b = adapter.prepare(self.p, self.source)
        self.assertEqual(set(b["forcing"]["left"]), {1})
        self.assertEqual(b["forcing"]["units"], "pmol/(kg min)")
        self.assertAlmostEqual(b["initial"][0], 1 / 0.052)
        self.assertAlmostEqual(b["initial"][1], 0.037 / 0.031 / 0.052)
        self.assertEqual(b["initial"][2:], [0, 0])

    def test_pancreatic_boundary_is_distinct_from_liver_arrival(self):
        self.source["source_rates"] = [[1, 2] for _ in self.source["times"]]
        good = adapter.prepare(self.p, self.source)
        fault = adapter.prepare(self.p, self.source, signal="liver_fault")
        self.assertEqual(good["forcing"]["left"][0], 1)
        self.assertEqual(fault["forcing"]["left"][0], 2)
        self.assertEqual(good["initial"], fault["initial"])

    def test_pharmaceutical_insulin_gives_no_cpeptide(self):
        source = parent_fixture(0)
        source["baseline"]["u_sc_pmol_kg_min"] = 100
        b = adapter.prepare(self.p, source)
        self.assertEqual(b["initial"], [0] * 4)
        self.assertTrue(all(q == 0 for q in b["forcing"]["left"]))

    def test_no_parent_mutation(self):
        before = copy.deepcopy(self.source)
        for scale in (0.5, 1, 2):
            adapter.prepare(self.p, self.source, scale=scale)
        self.assertEqual(self.source, before)

    def test_source_rejection(self):
        for update in ({"status": "failed"}, {"times": [0, 240]}, {"source_rates": [[1, 1]]}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                adapter.prepare(self.p, self.source | update)
        for value in (float("nan"), -1, True):
            changed = copy.deepcopy(self.source)
            changed["source_rates"][0][0] = value
            with self.assertRaises(ValueError):
                adapter.prepare(self.p, changed)
        with self.assertRaises(ValueError):
            adapter.prepare(self.p, self.source, step=0.125)

    def test_frozen_protocol(self):
        common.validate(self.p)
        self.p["boundary"]["appearance_ratio"] = 0.5
        with self.assertRaises(ValueError):
            common.validate(self.p)

    def test_independent_equilibrium_and_ledger_assessment(self):
        r = report.assess_case(self.p, self.fixture(), self.source, self.source)
        for k, v in r["checks"].items():
            self.assertLessEqual(v, self.p["criteria"][k], k)
        self.assertAlmostEqual(r["outcomes"]["baseline_pmol_l"], 1 / (0.052 * 0.0655))

    def test_mass_ledger_and_oracle_faults_detected(self):
        item = self.fixture()
        item["states"]["reference"][5][2] += 0.25
        self.assertAlmostEqual(
            report.assess_case(self.p, item, self.source, self.source)["checks"][
                "mass_error_pmol_kg"
            ],
            0.25,
        )
        item = self.fixture()
        item["oracle"][5][0] += 0.0655
        self.assertAlmostEqual(
            report.assess_case(self.p, item, self.source, self.source)["checks"][
                "oracle_concentration_error_pmol_l"
            ],
            1,
        )

    def test_wrong_boundary_initialization_and_missing_diagnostic_rejected(self):
        for edit in (
            lambda x: x["boundary"]["initial"].__setitem__(0, 0),
            lambda x: x["diagnostics"].pop("liver_fault"),
            lambda x: x["states"]["reference"].pop(),
        ):
            item = self.fixture()
            edit(item)
            with self.assertRaises(ValueError):
                report.assess_case(self.p, item, self.source, self.source)

    def test_preserved_source_amount_checks_sampling_separately(self):
        changed = copy.deepcopy(self.source)
        changed["states"][-1][16] += 1
        r = report.assess_case(self.p, self.fixture(), changed, changed)
        self.assertAlmostEqual(r["checks"]["parent_dose_relative_error"], 1 / 241)

    def test_failed_parent_attempt_preserved_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "failed"
            with (
                patch.object(run.subprocess, "check_output", side_effect=["test", b""]),
                patch.object(run, "new_parent", side_effect=RuntimeError("parent failed")),
            ):
                with self.assertRaisesRegex(RuntimeError, "parent failed"):
                    run.execute(out)
            failure = report.reconstruct(out, allow_failed=True)
            self.assertFalse(failure["passed"])
            self.assertEqual(failure["expected_cases"], 24)
            before = (out / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run.execute(out)
            self.assertEqual(before, (out / "manifest.json").read_bytes())
            with (out / "source-adapter.py").open("a") as f:
                f.write("\n# tamper\n")
            with self.assertRaisesRegex(ValueError, "Changed/missing"):
                report.reconstruct(out, allow_failed=True)
