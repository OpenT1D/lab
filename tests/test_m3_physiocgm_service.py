"""Preparation uses invented CSVs only and cannot silently lose planned people."""

import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.azt1d.analysis import _Snapshot
from experiments.m3.common import ROOT, digest, read, save
from experiments.m3.external.study import registry_check
from experiments.m3.physiocgm.fixtures import generate
from experiments.m3.physiocgm.service import _seal, prepare, validate_request, verify


class PhysioCGMPreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = generate(self.root / "input")
        self.request_path = self.root / "input/request.json"
        self.output = self.root / "converted"

    def test_complete_conversion_and_offline_verification_without_original_paths(self):
        report = prepare(self.request_path, self.output)
        self.assertEqual(report["planned_people"], 2)
        self.assertEqual(report["registered_origins"], 1152)
        self.assertFalse(report["release_files_verified"])
        self.assertFalse(report["model_fit_or_evaluation"])
        for index, person in enumerate(self.request["people"]):
            folder = self.output / person["id"]
            self.assertEqual(
                (folder / "native.csv").read_bytes(), Path(person["input"]["file"]).read_bytes()
            )
            audit, _ = read(folder / "audit.json")
            self.assertEqual(audit["contract"], "physiocgm-cgm-candidate/0.2")
            variants = audit["format_variants"]
            self.assertEqual(variants["empty_unnamed_column"], index == 1)
            self.assertEqual(variants["single_digit_hour_egv_records"] > 0, index == 1)
        registry, _ = read(self.output / "registry.json")
        identity = registry_check(registry)
        self.assertEqual(len(identity["people"]), 2)
        self.assertEqual(registry["prior_access"]["status"], "present")
        for person in registry["people"]:
            document, sha = read(person["input"]["file"])
            self.assertEqual(sha, person["input"]["sha256"])
            self.assertEqual(person["origins_us"], [row["time_us"] for row in document["rows"]])
            statuses = {row["status"] for row in document["rows"]}
            self.assertTrue(
                {"missing", "ambiguous", "censored_low", "censored_high", "invalid"} <= statuses
            )
        shutil.rmtree(self.root / "input")
        moved = self.root / "moved"
        self.output.rename(moved)
        self.assertEqual(verify(moved), report)
        code = (
            "import sys; from experiments.m3.physiocgm.service import verify; "
            "verify(sys.argv[1]); assert 'numpy' not in sys.modules; "
            "assert 'sklearn' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(moved)], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_human_kind_refused_before_any_native_snapshot(self):
        self.request["kind"] = "human"
        save(self.request_path, self.request)
        with patch("experiments.m3.physiocgm.service._Snapshot") as access:
            with self.assertRaisesRegex(ValueError, "Human PhysioCGM"):
                prepare(self.request_path, self.output)
            access.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_human_bundle_verification_rejects_before_native_hashing(self):
        prepare(self.request_path, self.output)
        request, _ = read(self.output / "request.json")
        request["kind"] = "human"
        save(self.output / "request.json", request)
        original = _Snapshot.read

        def metadata_only(snapshot, name):
            self.assertNotEqual(Path(name).name, "native.csv")
            self.assertNotEqual(Path(name).name, "observations.json")
            return original(snapshot, name)

        with patch.object(_Snapshot, "read", metadata_only):
            with self.assertRaisesRegex(ValueError, "Human PhysioCGM"):
                verify(self.output)

    def test_missing_person_preserved_and_prevents_partial_registry(self):
        Path(self.request["people"][0]["input"]["file"]).unlink()
        with self.assertRaisesRegex(ValueError, "Preparation incomplete"):
            prepare(self.request_path, self.output)
        state, _ = read(self.output / "state.json")
        self.assertEqual([case["status"] for case in state["cases"]], ["failed", "completed"])
        self.assertEqual(state["status"], "failed")
        self.assertTrue((self.output / "manifest.json").exists())
        self.assertFalse((self.output / "registry.json").exists())
        with self.assertRaisesRegex(ValueError, "Only complete"):
            verify(self.output)

    def test_changed_native_hash_fails_with_safe_error_and_preserved_attempt(self):
        first = self.request["people"][0]
        Path(first["input"]["file"]).write_text("private-unexpected-content")
        with self.assertRaises(ValueError):
            prepare(self.request_path, self.output)
        state, _ = read(self.output / "state.json")
        self.assertEqual(state["cases"][0]["error"]["type"], "ValueError")
        self.assertNotIn("private-unexpected-content", json.dumps(state))
        self.assertTrue((self.output / first["id"] / "read-attempt.json").exists())
        self.assertFalse((self.output / first["id"] / "native.csv").exists())

    def test_unnamed_field_data_retains_failure_and_prevents_partial_registry(self):
        person = self.request["people"][1]
        path = Path(person["input"]["file"])
        records = list(csv.reader(io.StringIO(path.read_text(), newline="")))
        records.append(["", "ignored", "Calibration", "", "Invented", "private-unexpected"])
        stream = io.StringIO(newline="")
        csv.writer(stream).writerows(records)
        raw = stream.getvalue().encode()
        path.write_bytes(raw)
        person["input"]["sha256"] = digest(raw)
        save(self.request_path, self.request)
        with self.assertRaisesRegex(ValueError, "Preparation incomplete"):
            prepare(self.request_path, self.output)
        state, _ = read(self.output / "state.json")
        self.assertEqual([case["status"] for case in state["cases"]], ["completed", "failed"])
        self.assertNotIn("private-unexpected", json.dumps(state))
        self.assertEqual((self.output / person["id"] / "native.csv").read_bytes(), raw)
        self.assertFalse((self.output / "registry.json").exists())
        self.assertFalse((self.output / person["id"] / "observations.json").exists())

    def test_semantic_tampering_rejected_after_inventory_rehash(self):
        prepare(self.request_path, self.output)
        pid = self.request["people"][0]["id"]
        path = self.output / pid / "observations.json"
        document, _ = read(path)
        document["rows"][0]["value"] += 1
        save(path, document)
        registry, _ = read(self.output / "registry.json")
        registry["people"][0]["input"]["sha256"] = digest(path.read_bytes())
        save(self.output / "registry.json", registry)
        _seal(self.output)
        with self.assertRaisesRegex(ValueError, "differ from native conversion"):
            verify(self.output)

    def test_symlink_native_input_and_modified_header_are_failed_cases(self):
        first, second = self.request["people"]
        path = Path(first["input"]["file"])
        target = self.root / "original.csv"
        path.rename(target)
        path.symlink_to(target)
        second["header"].append("undeclared")
        save(self.request_path, self.request)
        with self.assertRaisesRegex(ValueError, "Preparation incomplete"):
            prepare(self.request_path, self.output)
        state, _ = read(self.output / "state.json")
        self.assertEqual([c["status"] for c in state["cases"]], ["failed", "failed"])
        self.assertFalse((self.output / "registry.json").exists())

    def test_duplicate_sources_and_overwriting_old_attempt_are_refused(self):
        prepare(self.request_path, self.output)
        with self.assertRaises(FileExistsError):
            prepare(self.request_path, self.output)
        self.request["people"][1]["input"] = self.request["people"][0]["input"]
        with self.assertRaises(ValueError):
            validate_request(self.request)

    def test_original_request_bytes_and_conversion_provenance_are_bound(self):
        prepare(self.request_path, self.output)
        request, _ = read(self.output / "request.json")
        request["people"][0]["input"]["file"] = "/unavailable/changed.csv"
        save(self.output / "request.json", request)
        _seal(self.output)
        with self.assertRaisesRegex(ValueError, "request bytes changed"):
            verify(self.output)
