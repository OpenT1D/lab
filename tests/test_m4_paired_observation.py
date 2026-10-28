"""Dimensional anchors, initial-state ownership and durable boundary artifacts."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.paired_observation.contract import evaluate, prepare_case, validate
from experiments.m4.paired_observation.run import (
    HERE,
    ROOT,
    dump,
    execute,
    hashes,
    read,
    reconstruct,
)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")

    def test_frozen_pulse_and_triangle_integrals(self):
        result = evaluate(self.p)
        self.assertTrue(result["passed"])
        amounts = [b["integrated_each_branch_pmol_kg"] for b in result["bundles"]]
        for actual, expected in zip(
            amounts, [0, 9 * 20, 1.5 * 240 + 9 * 20, 1000 * 60 / 2 / 102.32], strict=True
        ):
            self.assertAlmostEqual(actual, expected, places=11)

    def test_whole_body_mass_conversion_and_normalization_once(self):
        c = self.p["cases"][-1]
        result = prepare_case(self.p, c)
        # 5.808 ug = 1000 pmol under the declared 5808 g/mol convention.
        self.assertAlmostEqual(result["insulin"]["forcing"]["right"][0], 1000 / 102.32)
        self.assertEqual(result["insulin"]["forcing"], result["cpeptide"]["forcing"])

    def test_basal_and_extra_secretion_are_not_duplicated(self):
        result = prepare_case(self.p, self.p["cases"][2])
        self.assertAlmostEqual(result["integrated_basal_pmol_kg"], 360)
        self.assertAlmostEqual(result["integrated_evoked_pmol_kg"], 180)
        for value, expected in zip(
            result["insulin"]["forcing"]["left"], [1.5, 10.5, 1.5], strict=True
        ):
            self.assertAlmostEqual(value, expected)

    def test_hand_solved_stationary_amounts_and_distinct_concentrations(self):
        for name in ("m1", "m2", "m30", "m4"):
            self.p["insulin"][name] = 1
        for name in ("k1", "k2", "k3"):
            self.p["cpeptide"][name] = 1
        self.p["insulin"]["volume_l_kg"] = self.p["cpeptide"]["volume_l_kg"] = 1
        result = prepare_case(self.p, self.p["cases"][2])
        for a, b in zip(result["insulin"]["initial"], [0.5, 1, 0, 0, 0], strict=True):
            self.assertAlmostEqual(a, b)
        for a, b in zip(result["cpeptide"]["initial"], [1.5, 1.5, 0, 0], strict=True):
            self.assertAlmostEqual(a, b)
        self.assertNotEqual(
            result["insulin"]["initial_concentration_pmol_l"],
            result["cpeptide"]["initial_concentration_pmol_l"],
        )
        self.assertFalse(result["insulin"]["current_bc002_initial_state_supported"])

    def test_zero_and_incremental_start_without_invented_background(self):
        for c in (self.p["cases"][0], self.p["cases"][1], self.p["cases"][3]):
            result = prepare_case(self.p, c)
            self.assertEqual(result["insulin"]["initial"], [0] * 5)
            self.assertEqual(result["cpeptide"]["initial"], [0] * 4)
            self.assertTrue(result["insulin"]["current_bc002_initial_state_supported"])

    def test_source_immutable_and_branches_do_not_alias(self):
        saved = copy.deepcopy(self.p)
        result = prepare_case(self.p, self.p["cases"][1])
        result["cpeptide"]["forcing"]["left"][1] = 999
        self.assertNotEqual(result["insulin"]["forcing"]["left"][1], 999)
        self.assertEqual(self.p, saved)

    def test_unsupported_units_rejected(self):
        for unit in ("pmol/(kg min)", "U/h", "pmol/L", "unknown"):
            self.p["cases"][0]["evoked_unit"] = unit
            with self.assertRaisesRegex(ValueError, "whole-body"):
                validate(self.p)

    def test_ambiguous_source_and_route_rejected(self):
        for key, value in (
            ("route", "peripheral"),
            ("scale_interpretation", "unknown"),
            ("evidence_kind", "human"),
            ("time_unit", "second"),
            ("appearance_assumption", "implicit"),
        ):
            p = copy.deepcopy(self.p)
            p[key] = value
            with self.assertRaises(ValueError):
                validate(p)

    def test_missing_baseline_and_hidden_extraction_rejected(self):
        p = copy.deepcopy(self.p)
        p["cases"][0].pop("basal_pmol_min")
        with self.assertRaises(ValueError):
            validate(p)
        self.p["insulin"]["hepatic_fraction"] = 0.5
        with self.assertRaises(ValueError):
            validate(self.p)

    def test_profile_body_mass_mismatch_rejected(self):
        self.p["body_weight_kg"] = 80
        with self.assertRaisesRegex(ValueError, "Body mass differs"):
            validate(self.p)

    def test_nonfinite_negative_boolean_and_non_equimolar_rejected(self):
        for value in (0, -1, True, "1", float("nan"), float("inf"), 2):
            self.p["cpeptide_per_insulin_molar_ratio"] = value
            with self.assertRaises(ValueError):
                validate(self.p)

    def test_baseline_mode_and_stationarity_rejected(self):
        self.p["cases"][0]["basal_pmol_min"] = 1
        with self.assertRaisesRegex(ValueError, "Incremental baseline"):
            validate(self.p)
        self.p["cases"][0]["basal_pmol_min"] = 0
        self.p["cases"][2]["left"][0] = 1
        with self.assertRaisesRegex(ValueError, "zero initial evoked"):
            validate(self.p)

    def test_invalid_forcing_and_missing_case_rejected(self):
        self.p["cases"][0]["edges_min"] = [0, 0]
        with self.assertRaises(ValueError):
            validate(self.p)
        self.p["cases"].pop()
        with self.assertRaises(ValueError):
            validate(self.p)

    def test_independent_amount_anchor_detects_wrong_scale(self):
        self.p["cases"][1]["left"][1] *= 2
        self.p["cases"][1]["right"][1] *= 2
        self.assertFalse(evaluate(self.p)["passed"])


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / "run"

    def test_success_repeat_and_standard_library_reconstruction(self):
        a = execute(HERE / "protocol.json", self.output)
        b = execute(HERE / "protocol.json", self.root / "repeat")
        self.assertEqual(a, b)
        self.assertEqual(
            read(self.output / "manifest.json")["files"],
            read(self.root / "repeat/manifest.json")["files"],
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m4.paired_observation.run",
                "--reconstruct",
                str(self.output),
                "--output",
                str(self.root / "report.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            (self.root / "report.json").read_bytes(), (self.output / "preflight.json").read_bytes()
        )

    def test_failed_criteria_saved_and_not_reconstructible(self):
        p = read(HERE / "protocol.json")
        p["acceptance"]["expected_integrals_pmol_kg"]["pulse_increment"] = 1
        dump(self.root / "bad.json", p)
        with self.assertRaisesRegex(ValueError, "acceptance failed"):
            execute(self.root / "bad.json", self.output)
        self.assertEqual(read(self.output / "manifest.json")["status"], "failed")
        self.assertFalse(read(self.output / "preflight.json")["passed"])
        with self.assertRaises(ValueError):
            reconstruct(self.output)

    def test_malformed_protocol_is_preserved(self):
        (self.root / "bad.json").write_text("{bad")
        with self.assertRaises(json.JSONDecodeError):
            execute(self.root / "bad.json", self.output)
        self.assertEqual(read(self.output / "manifest.json")["status"], "failed")
        self.assertEqual((self.output / "protocol.json").read_text(), "{bad")

    def test_interrupt_is_preserved(self):
        with patch("experiments.m4.paired_observation.run.evaluate", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                execute(HERE / "protocol.json", self.output)
        self.assertEqual(read(self.output / "manifest.json")["error"]["type"], "KeyboardInterrupt")

    def test_existing_output_not_overwritten(self):
        self.output.mkdir()
        (self.output / "keep").write_text("unchanged")
        with self.assertRaises(FileExistsError):
            execute(HERE / "protocol.json", self.output)
        self.assertEqual(list(self.output.iterdir()), [self.output / "keep"])

    def test_tampering_rejected_even_after_rehash(self):
        execute(HERE / "protocol.json", self.output)
        report = read(self.output / "preflight.json")
        report["bundles"][1]["cpeptide"]["forcing"]["left"][1] = 999
        dump(self.output / "preflight.json", report)
        with self.assertRaisesRegex(ValueError, "Changed"):
            reconstruct(self.output)
        manifest = read(self.output / "manifest.json")
        manifest["files"] = hashes(self.output)
        dump(self.output / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            reconstruct(self.output)

    def test_unsafe_path_and_incomplete_status(self):
        execute(HERE / "protocol.json", self.output)
        manifest = read(self.output / "manifest.json")
        manifest["files"]["../escape"] = "invalid"
        dump(self.output / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            reconstruct(self.output)
        manifest["status"] = "started"
        dump(self.output / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "completed"):
            reconstruct(self.output)
