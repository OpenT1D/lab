"""Human conversion controls exercised exclusively with self-authored records.

The ten-source roster and evidence below are invented; no release files or local
health-data directory are opened by this test module.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from experiments.m3.azt1d.analysis import _Snapshot
from experiments.m3.common import ROOT, digest, read, save
from experiments.m3.physiocgm import human
from experiments.m3.physiocgm.fixtures import generate
from experiments.m3.physiocgm.intake import RELEASE


class PhysioCGMHumanConversion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.release = self.root / "release"
        self.release.mkdir(mode=0o700)
        generated = generate(self.root / "input", people=10)
        self.request = {
            "schema": human.REQUEST_SCHEMA,
            "kind": "human",
            "release": RELEASE,
            "authorization": {
                "confirmed": True,
                "scope": "local-conversion-only",
                "reference": "Invented test authorization; not a real consent record",
                "retention": "private-local-reproducibility",
            },
            "prior_access": {
                "reviewed": True,
                "status": "present",
                "reference": "Self-authored test inputs were generated before conversion",
            },
            "evidence": {},
            "people": [],
        }
        archive_hashes, members, acquisitions = {}, {}, []
        for index, person in enumerate(generated["people"], 1):
            archive = f"archive-{index:02d}"
            member = f"audit/format-check-01/cgm/{archive}.csv"
            source = self.release / member
            source.parent.mkdir(parents=True, exist_ok=True)
            Path(person["input"]["file"]).rename(source)
            person["input"]["file"] = str(source)
            self.request["people"].append(person | {"archive": archive, "audit_member": member})
            archive_hashes[archive] = digest(f"invented archive identity {index}".encode())
            members[member] = person["input"]["sha256"]
            acquisitions.append({"archive": f"{archive}.zip", "sha256": archive_hashes[archive]})
        evidence = {
            "acquisition": {
                "release_doi": RELEASE,
                "all_verified": True,
                "model_evaluation": False,
                "files": acquisitions,
            },
            "rights_metadata": {"doi": RELEASE, "license": {"name": "CC0"}},
            "prior_access": {"description": "Invented source generation; no model access"},
            "audit_report": "Self-authored evidence fixture, not a human audit report.\n",
        }
        paths = {
            "acquisition": "acquisition.json",
            "audit_inventory": "audit/format-check-03/evidence-manifest.json",
            "prior_access": "audit/format-check-03/access-snapshot.jsonl",
            "rights_metadata": "metadata/release-v1.json",
            "audit_report": "audit/format-check-03/Bevindingen.md",
        }
        for name, value in evidence.items():
            path = self.release / paths[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, str):
                path.write_text(value)
            else:
                save(path, value)
            path.chmod(0o600)
            self.request["evidence"][name] = {
                "file": str(path),
                "sha256": digest(path.read_bytes()),
            }
            members[paths[name]] = digest(path.read_bytes())
        inventory_path = self.release / paths["audit_inventory"]
        save(
            inventory_path,
            {
                "release": RELEASE,
                "archive_sha256": archive_hashes,
                "private_evidence_files_sha256": members,
                "access_snapshot_sha256": self.request["evidence"]["prior_access"]["sha256"],
            },
        )
        inventory_path.chmod(0o600)
        self.request["evidence"]["audit_inventory"] = {
            "file": str(inventory_path),
            "sha256": digest(inventory_path.read_bytes()),
        }
        for path in self.release.rglob("*"):
            if path.is_dir():
                path.chmod(0o700)
        self.request_path = self.root / "request.json"
        self.frozen = self.root / "frozen"
        self.converted = self.root / "converted"
        self._save_request()

    def _save_request(self):
        save(self.request_path, self.request)
        self.request_path.chmod(0o600)

    def _freeze(self):
        return human.freeze(self.request_path, self.frozen)

    def _prepare(self):
        self._freeze()
        return human.prepare(self.frozen / "plan.json", self.converted)

    def _rewrite_evidence(self, name, change):
        pointer = self.request["evidence"][name]
        path = Path(pointer["file"])
        value, _ = read(path)
        change(value)
        save(path, value)
        path.chmod(0o600)
        pointer["sha256"] = digest(path.read_bytes())
        self._save_request()

    @staticmethod
    def _reseal(folder):
        # Test semantic validation after an attacker recomputes ordinary hashes.
        (folder / "manifest.json").unlink()
        human._seal(folder)

    def test_complete_roster_converts_and_verifies_without_original_paths_or_model_imports(self):
        result = self._prepare()
        self.assertEqual(result["converted_sources"], 10)
        self.assertFalse(result["model_fit_or_evaluation"])
        self.assertFalse((self.converted / "registry.json").exists())
        self.assertTrue((self.converted / "cohort.json").exists())
        for path in (self.converted, *self.converted.rglob("*")):
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        for person in self.request["people"]:
            folder = self.converted / person["id"]
            self.assertEqual(
                (folder / "native.csv").read_bytes(), Path(person["input"]["file"]).read_bytes()
            )
            document, _ = read(folder / "observations.json")
            audit, _ = read(folder / "audit.json")
            self.assertEqual(audit["kind"], "human")
            self.assertEqual(document["person"], person["id"])
        for folder in (self.root / "input", self.release, self.frozen):
            shutil.rmtree(folder)
        self.request_path.unlink()
        moved = self.root / "moved"
        self.converted.rename(moved)
        self.assertEqual(human.verify(moved, self.root / "verification"), result)
        script = (
            "import sys; from experiments.m3.physiocgm.human import verify; "
            "verify(sys.argv[1], sys.argv[2]); "
            "assert 'numpy' not in sys.modules; assert 'sklearn' not in sys.modules"
        )
        checked = subprocess.run(
            [sys.executable, "-S", "-c", script, str(moved), str(self.root / "isolated-check")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_freeze_reads_only_metadata_not_native_csv(self):
        for person in self.request["people"]:
            Path(person["input"]["file"]).unlink()
        self._freeze()
        self.assertTrue((self.frozen / "plan.json").exists())
        self.assertFalse(any(self.frozen.rglob("native.csv")))

    def test_missing_native_file_preserves_entire_roster_and_blocks_partial_cohort(self):
        self._freeze()
        Path(self.request["people"][0]["input"]["file"]).unlink()
        with self.assertRaises(ValueError):
            human.prepare(self.frozen / "plan.json", self.converted)
        state, _ = read(self.converted / "state.json")
        self.assertEqual(state["status"], "failed")
        self.assertEqual(len(state["cases"]), 10)
        self.assertEqual(state["cases"][0]["status"], "failed")
        self.assertTrue(all(case["status"] == "completed" for case in state["cases"][1:]))
        self.assertFalse((self.converted / "cohort.json").exists())
        self.assertTrue((self.converted / "manifest.json").exists())
        with self.assertRaises(ValueError):
            human.verify(self.converted, self.root / "failed-verification")

    def test_changed_source_is_rejected_with_safe_failure_record(self):
        self._freeze()
        source = Path(self.request["people"][0]["input"]["file"])
        source.write_text("private-unexpected-fixture-content")
        with self.assertRaises(ValueError):
            human.prepare(self.frozen / "plan.json", self.converted)
        state, _ = read(self.converted / "state.json")
        self.assertNotIn("private-unexpected-fixture-content", json.dumps(state))
        self.assertEqual(len(state["cases"]), 10)
        self.assertEqual(state["cases"][0]["status"], "failed")
        folder = self.converted / self.request["people"][0]["id"]
        self.assertEqual((folder / "native.csv").read_bytes(), source.read_bytes())
        self.assertFalse((folder / "observations.json").exists())

    def test_ledger_failure_prevents_any_native_read(self):
        self._freeze()
        native_names = {Path(person["input"]["file"]).name for person in self.request["people"]}
        native_reads = []
        original = _Snapshot.read

        def checked_read(snapshot, name):
            if Path(name).name in native_names or Path(name).name == "native.csv":
                native_reads.append(name)
                self.fail("Native read preceded successful durable access recording")
            return original(snapshot, name)

        ledger_os = types.SimpleNamespace(**vars(os))
        ledger_os.fsync = Mock(side_effect=OSError("invented fsync failure"))
        with patch("experiments.m3.physiocgm.access.os", ledger_os):
            with patch.object(_Snapshot, "read", checked_read):
                with self.assertRaises((ValueError, OSError)):
                    human.prepare(self.frozen / "plan.json", self.converted)
        self.assertGreater(ledger_os.fsync.call_count, 0)
        self.assertEqual(native_reads, [])
        self.assertFalse((self.converted / "cohort.json").exists())

    def test_native_csv_cannot_be_disguised_as_review_evidence_before_read(self):
        native = self.request["people"][0]["input"]
        self.request["evidence"]["audit_report"] = dict(native)
        self._save_request()
        native_reads = []
        original = human._read_private

        def checked_read(path):
            if str(path) == native["file"]:
                native_reads.append(str(path))
                self.fail("Native input was read as pre-freeze review evidence")
            return original(path)

        with patch.object(human, "_read_private", checked_read):
            with self.assertRaises(ValueError):
                self._freeze()
        self.assertEqual(native_reads, [])

    def test_all_ten_sources_and_exact_release_are_required(self):
        original = copy.deepcopy(self.request)
        for mutate in (
            lambda value: value["people"].pop(),
            lambda value: value.update(release="10.6084/m9.figshare.28136294.v2"),
            lambda value: value["people"][1].update(archive=value["people"][0]["archive"]),
            lambda value: value["people"][1].update(input=value["people"][0]["input"]),
        ):
            with self.subTest(mutation=mutate):
                self.request = copy.deepcopy(original)
                mutate(self.request)
                self._save_request()
                with self.assertRaises(ValueError):
                    human.freeze(self.request_path, self.root / "invalid-freeze")

    def test_authorization_and_prior_access_cannot_be_omitted_or_expanded(self):
        original = copy.deepcopy(self.request)
        for mutate in (
            lambda value: value["authorization"].update(confirmed=False),
            lambda value: value["authorization"].update(scope="model-evaluation"),
            lambda value: value["authorization"].update(reference=""),
            lambda value: value["prior_access"].update(reviewed=False),
            lambda value: value["prior_access"].update(status="none"),
        ):
            with self.subTest(mutation=mutate):
                self.request = copy.deepcopy(original)
                mutate(self.request)
                self._save_request()
                with self.assertRaises(ValueError):
                    human.freeze(self.request_path, self.root / "invalid-freeze")

    def test_evidence_hash_and_source_lineage_must_agree(self):
        self._rewrite_evidence(
            "audit_inventory",
            lambda value: value["private_evidence_files_sha256"].update(
                {self.request["people"][0]["audit_member"]: "a" * 64}
            ),
        )
        with self.assertRaises(ValueError):
            self._freeze()

    def test_changed_evidence_bytes_are_refused(self):
        Path(self.request["evidence"]["audit_report"]["file"]).write_text("altered evidence")
        with self.assertRaises(ValueError):
            self._freeze()

    def test_native_symlinks_and_hardlinks_are_failed_sources(self):
        self._freeze()
        first, second = (Path(p["input"]["file"]) for p in self.request["people"][:2])
        original = self.root / "retained-original.csv"
        first.rename(original)
        first.symlink_to(original)
        os.link(second, self.root / "second-hardlink.csv")
        with self.assertRaises(ValueError):
            human.prepare(self.frozen / "plan.json", self.converted)
        state, _ = read(self.converted / "state.json")
        self.assertEqual([case["status"] for case in state["cases"][:2]], ["failed", "failed"])
        self.assertFalse((self.converted / "cohort.json").exists())

    def test_freeze_inside_git_repository_is_refused(self):
        repository = self.root / "invented-repository"
        (repository / ".git").mkdir(parents=True)
        with self.assertRaises(ValueError):
            human.freeze(self.request_path, repository / "freeze")

    def test_existing_output_is_never_overwritten(self):
        self._prepare()
        before = (self.converted / "manifest.json").read_bytes()
        with self.assertRaises((FileExistsError, ValueError)):
            human.freeze(self.request_path, self.frozen)
        with self.assertRaises((FileExistsError, ValueError)):
            human.prepare(self.frozen / "plan.json", self.converted)
        self.assertEqual((self.converted / "manifest.json").read_bytes(), before)

    def test_changed_plan_is_rejected_before_source_read(self):
        self._freeze()
        plan, _ = read(self.frozen / "plan.json")
        plan["rules"]["timing"] = "round all timestamps"
        save(self.frozen / "plan.json", plan)
        (self.frozen / "plan.json").chmod(0o600)
        self._reseal(self.frozen)
        with self.assertRaises(ValueError):
            human.prepare(self.frozen / "plan.json", self.converted)

    def test_changed_converter_provenance_is_rejected_after_inventory_rehash(self):
        self._freeze()
        plan, _ = read(self.frozen / "plan.json")
        sources = plan["provenance"]["sources"]
        sources[next(iter(sources))] = "a" * 64
        save(self.frozen / "plan.json", plan)
        (self.frozen / "plan.json").chmod(0o600)
        self._reseal(self.frozen)
        with self.assertRaises(ValueError):
            human.prepare(self.frozen / "plan.json", self.converted)

    def test_changed_converted_values_cannot_pass_offline_verification(self):
        self._prepare()
        path = self.converted / self.request["people"][0]["id"] / "observations.json"
        document, _ = read(path)
        document["rows"][0]["value"] += 1
        save(path, document)
        path.chmod(0o600)
        self._reseal(self.converted)
        with self.assertRaisesRegex(ValueError, "differs from native"):
            human.verify(self.converted, self.root / "tampered-verification")

    def test_verification_ledger_failure_prevents_native_and_observation_reads(self):
        self._prepare()
        private_reads = []
        original = _Snapshot.read

        def checked_read(snapshot, name):
            if Path(name).name in ("native.csv", "observations.json"):
                private_reads.append(name)
                self.fail("Verification read preceded successful durable access recording")
            return original(snapshot, name)

        with patch.object(human, "record_access", side_effect=OSError("invented fsync failure")):
            with patch.object(_Snapshot, "read", checked_read):
                with self.assertRaises((ValueError, OSError)):
                    human.verify(self.converted, self.root / "unlogged-verification")
        self.assertEqual(private_reads, [])

    def test_unexpected_bundle_file_is_rejected_without_reading_its_contents(self):
        self._prepare()
        unexpected = self.converted / "unexpected.csv"
        unexpected.write_text("invented,unexpected,private,contents\n")
        unexpected.chmod(0o600)
        self._reseal(self.converted)
        unexpected_reads = []
        original = _Snapshot.read

        def checked_read(snapshot, name):
            if Path(name).name == unexpected.name:
                unexpected_reads.append(name)
                self.fail("Unexpected file was read before exact bundle membership validation")
            return original(snapshot, name)

        with patch.object(_Snapshot, "read", checked_read):
            with self.assertRaises(ValueError):
                human.verify(self.converted, self.root / "unexpected-verification")
        self.assertEqual(unexpected_reads, [])
