"""Hand-calculated trajectory accounting and paired recorder failure contracts."""

import copy
import hashlib
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.paired_kinetics.common import (
    HERE,
    cases,
    digest,
    dump,
    read,
    validate,
    verify_files,
)
from experiments.m4.paired_kinetics.report import assess_case, reconstruct
from experiments.m4.paired_kinetics.run import execute
from experiments.m4.paired_observation.run import HERE as BOUNDARY_HERE
from experiments.m4.paired_observation.run import execute as make_boundary


def repeat_hash(rows):
    return hashlib.sha256(b"".join(struct.pack("<d", v) for row in rows for v in row)).hexdigest()


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.p = read(HERE / "protocol.json")
        force = {"edges": [0, 1], "left": [0], "right": [0], "units": "pmol/(kg min)"}
        self.case = {"id": "washout", "insulin": {"forcing": force, "initial": [2, 3, 0, 0, 0]}}
        # Each hand-authored row totals 5 pmol/kg including removal; no input.
        rows = [[2, 3, 0, 0, 0], [1.5, 2, 1, 0.5, 0], [1, 1, 2, 1, 0]]
        self.data = {
            "schema": "bc005-case/1",
            "id": "washout",
            "branch": "insulin",
            "times_min": [0, 0.5, 1],
            "input": force,
            "initial": [2, 3, 0, 0, 0],
            "volume_l_kg": 1,
            "states": {k: copy.deepcopy(rows) for k in ("coarse", "tight", "reference")},
            "oracle": copy.deepcopy(rows),
            "legacy": None,
            "analytical_pmol_l": None,
            "repeat_error": 0,
            "repeat_sha256": repeat_hash(rows),
        }

    def assess(self):
        return assess_case(self.data, self.case, self.p, "insulin", 1)

    def test_initial_mass_and_removed_amount_accounted(self):
        result = self.assess()
        self.assertTrue(result["passed"])
        self.assertEqual(result["metrics"]["mass_error_pmol_kg"], 0)
        self.assertEqual(result["initial_concentration_pmol_l"], 2)
        self.assertEqual(result["final_concentration_pmol_l"], 1)

    def test_lost_initial_inventory_cannot_be_hidden(self):
        self.data["states"]["tight"][-1][2] = 0
        result = self.assess()
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["mass_error_pmol_kg"], 2)

    def test_oracle_ledger_error_detected_even_with_matching_concentration(self):
        self.data["oracle"][-1][2] += 1
        result = self.assess()
        self.assertFalse(result["passed"])
        self.assertEqual(result["metrics"]["oracle_state_error_pmol_kg"], 1)

    def test_initialization_change_rejected(self):
        self.data["states"]["reference"][0] = [0] * 5
        with self.assertRaisesRegex(ValueError, "Initial inventory"):
            self.assess()

    def test_missing_rows_or_solver_rejected(self):
        self.data["states"]["tight"].pop()
        with self.assertRaises(ValueError):
            self.assess()
        self.data["states"].pop("tight")
        with self.assertRaises(ValueError):
            self.assess()

    def test_nonfinite_or_boolean_measurements_rejected(self):
        for value in (float("nan"), float("inf"), True):
            self.data["oracle"][-1][0] = value
            with self.assertRaises(ValueError):
                self.assess()

    def test_repeat_bytes_are_verified(self):
        self.data["repeat_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Repeated state"):
            self.assess()

    def test_wrong_units_and_volume_rejected(self):
        self.data["input"] = {**self.data["input"], "units": "U/h"}
        with self.assertRaises(ValueError):
            self.assess()
        self.data["input"] = self.case["insulin"]["forcing"]
        self.data["volume_l_kg"] = 1000
        with self.assertRaises(ValueError):
            self.assess()


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.boundary = self.root / "boundary"
        make_boundary(BOUNDARY_HERE / "protocol.json", self.boundary)

    def test_fixed_boundary_and_two_additional_cases(self):
        p = read(HERE / "protocol.json")
        bundle = cases(self.boundary, p)
        self.assertEqual(len(bundle), 6)
        self.assertEqual(bundle[-1]["insulin"]["initial"], [2, 3, 0, 0, 0])
        self.assertEqual(bundle[-2]["cpeptide"]["forcing"]["left"], [1.5])
        p["boundary_protocol_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            cases(self.boundary, p)

    def test_worker_failure_preserves_started_attempt(self):
        target = self.root / "attempt"
        with patch(
            "experiments.m4.paired_kinetics.run.command",
            side_effect=subprocess.CalledProcessError(1, ["worker"]),
        ):
            with self.assertRaises(subprocess.CalledProcessError):
                execute(self.boundary, HERE / "protocol.json", target)
        self.assertEqual(read(target / "manifest.json")["status"], "failed")
        self.assertTrue((target / "boundary/preflight.json").is_file())
        with self.assertRaises(ValueError):
            reconstruct(target)

    def test_interruption_is_failed_and_preserved(self):
        target = self.root / "attempt"
        with patch("experiments.m4.paired_kinetics.run.command", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                execute(self.boundary, HERE / "protocol.json", target)
        self.assertEqual(read(target / "manifest.json")["error"]["type"], "KeyboardInterrupt")

    def test_existing_directory_is_untouched(self):
        with self.assertRaises(FileExistsError):
            execute(self.boundary, HERE / "protocol.json", self.boundary)
        self.assertEqual(read(self.boundary / "manifest.json")["status"], "completed")

    def test_incomplete_protocol_rejected(self):
        p = read(HERE / "protocol.json")
        p["criteria"].pop("repeat_error")
        with self.assertRaises(ValueError):
            validate(p)

    def test_missing_altered_and_unsafe_artifacts_rejected(self):
        (self.root / "data").write_text("original")
        manifest = {"files": {"data": digest(self.root / "data")}}
        verify_files(self.root, manifest, {"data"})
        with self.assertRaises(ValueError):
            verify_files(self.root, manifest, {"absent"})
        (self.root / "data").write_text("changed")
        with self.assertRaises(ValueError):
            verify_files(self.root, manifest, {"data"})
        manifest["files"] = {"../outside": "bad"}
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            verify_files(self.root, manifest, set())

    def test_nested_directory_symlink_rejected(self):
        (self.root / "alias").symlink_to(self.boundary, target_is_directory=True)
        manifest = {"files": {"alias/protocol.json": digest(self.boundary / "protocol.json")}}
        with self.assertRaisesRegex(ValueError, "Symlink"):
            verify_files(self.root, manifest, set())

    def test_calculated_state_cannot_be_presented_as_complete(self):
        dump(
            self.root / "manifest.json",
            {
                "schema": "bc005-run/1",
                "status": "calculated",
                "implementation": "bc005-paired-kinetics/1",
            },
        )
        with self.assertRaisesRegex(ValueError, "not complete"):
            reconstruct(self.root)
