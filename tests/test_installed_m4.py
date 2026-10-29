"""Successor contracts and adverse metadata/readers, without numerical dependencies."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.installed_study import common, context, profile, report, runtime
from experiments.m4.installed_study.adapter import activate, freeze
from experiments.m4.installed_study.process import Control, supervise, validate_receipt
from experiments.shared_services.installed_m4 import FIXTURES
from scripts.prepare_m4_runtimes import validate_policy

ROOT = Path(__file__).resolve().parents[1]


class InstalledM4(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m4-installed-contract-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def attachment(self):
        """Synthetic inert metadata, deliberately pointing at absent old sites."""
        roles = {}
        p = common.protocol()
        for role, project in (
            ("native", common.NATIVE_PROJECT),
            ("observer", common.OBSERVER_PROJECT),
        ):
            expected = common.package_records(project)
            roles[role] = {
                "project": project,
                "site_packages": str(self.root / ("absent-" + role)),
                "selectors": {
                    name: p["conditions"]["runtime_files_sha256"][project + "/" + name]
                    for name in ("pyproject.toml", "uv.lock")
                },
                "distributions": {name: item["version"] for name, item in expected.items()},
                "upstream_revisions": {
                    name: item["source"]["git"].rsplit("#", 1)[1]
                    for name, item in expected.items()
                    if "git" in item["source"]
                },
                "files": {"synthetic-inert-metadata.bin": {"sha256": "1" * 64, "bytes": 1}},
            }
        return {
            "schema": profile.SCHEMA,
            "interpreter": profile.interpreter(),
            "source_files": profile.source_records(),
            "roles": roles,
            "application": {
                "schema": "opent1d.sdk-application/1",
                "descriptor_sha256": "2" * 64,
                "source": {"revision": "3" * 40, "dirty": True},
                "build_label": "synthetic-inert-metadata",
                "tasks": ["mmtt-sensitivity", "m4-study-secure", "m4-study-installed"],
                "native_execution": "explicit-reviewed-attachment/1",
            },
        }

    def frozen(self):
        attachment = self.attachment()
        selected = {
            "path": str(self.root / "absent-attachment.json"),
            "sha256": common.digest(profile.canonical(attachment)),
            "record": attachment,
        }
        output = self.root / "frozen"
        with patch.object(context, "CURRENT", selected), activate():
            freeze(FIXTURES / "m4-fasting.json", output)
        common.dump(output / "state.json", {"reference": {"attempts": []}, "sources": {}})
        return output, attachment

    def test_science_and_complete_historical_condition_closure_are_preserved(self):
        old = json.loads((ROOT / "experiments/m4/secure_study/protocol.json").read_bytes())
        new = common.protocol()
        for key in ("acceptance", "comparison", "source_contract", "scenarios"):
            self.assertEqual(old[key], new[key])
        for key in ("numerical", "observer"):
            before, after = copy.deepcopy(old[key]), copy.deepcopy(new[key])
            before["runtime"].pop("project")
            after["runtime"].pop("project")
            self.assertEqual(before, after)
        names = set(common.source_paths())
        for group in ("protocol_files_sha256", "runtime_files_sha256"):
            self.assertLessEqual(set(new["conditions"][group]), names)
            for name, identity in old["conditions"][group].items():
                self.assertEqual(new["conditions"][group][name], identity)

    def test_candidate_policy_rejects_selector_change_with_positive_control(self):
        review = validate_policy()
        self.assertEqual(len(review["selectors"]), 6)
        fixture = self.root / "source"
        fixture.mkdir()
        for name in (
            "publication-security.json",
            "publication-snapshot.json",
            "experiments/m4/installed_study/runtime-review.json",
            *review["selectors"],
        ):
            target = fixture / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        self.assertEqual(validate_policy(fixture), review)
        target = fixture / "experiments/m4/installed_study/native/uv.lock"
        target.write_bytes(target.read_bytes() + b"\n# changed selector\n")
        with self.assertRaisesRegex(ValueError, "Reviewed runtime selector changed"):
            validate_policy(fixture)

    def test_inert_profile_binds_exact_python_and_application_shape(self):
        attachment = self.attachment()
        self.assertEqual(profile.evidence(attachment), attachment)
        selected = {
            "path": str(self.root / "absent.json"),
            "record": attachment,
            "sha256": common.digest(profile.canonical(attachment)),
        }
        with patch.object(context, "CURRENT", selected):
            record = runtime.attest(common.NATIVE_PROJECT)
        runtime.validate(record, common.NATIVE_PROJECT, common.protocol(), attachment)
        record["python"] = "3.12.999"
        with self.assertRaisesRegex(ValueError, "dependency overlay differs"):
            runtime.validate(record, common.NATIVE_PROJECT, common.protocol(), attachment)
        for field, value in (("base_executable_sha256", "not-a-hash"), ("version", "2.7.18")):
            changed = copy.deepcopy(attachment)
            changed["interpreter"][field] = value
            with self.assertRaises(ValueError):
                profile.evidence(changed)
        changed = copy.deepcopy(attachment)
        changed["application"]["source"]["dirty"] = "yes"
        with self.assertRaises(ValueError):
            profile.evidence(changed)

    def test_noncanonical_attachment_refuses_before_dependency_access(self):
        attachment = self.attachment()
        filename = self.root / "attachment.json"
        filename.write_text(json.dumps(attachment))
        with self.assertRaisesRegex(ValueError, "Canonical runtime attachment"):
            profile.load(filename, hashlib.sha256(filename.read_bytes()).hexdigest())
        filename.write_bytes(profile.canonical(attachment))
        # Matching canonical metadata reaches dependency admission and refuses
        # the deliberately absent directories; it cannot become runtime-ready.
        with self.assertRaisesRegex(ValueError, "dependency directory missing"):
            profile.load(filename)

    def test_frozen_plan_ties_application_and_source_bytes_to_attachment(self):
        output, _ = self.frozen()

        def files():
            return {
                p.relative_to(output).as_posix(): p.read_bytes()
                for p in output.rglob("*")
                if p.is_file()
            }

        original = common.read(output / "plan.json")
        self.assertEqual(report.validate_frozen(output, files()), original)
        changed = copy.deepcopy(original)
        changed["provenance"]["application"]["build_label"] = "different-app"
        common.dump(output / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "application/source provenance"):
            report.validate_frozen(output, files())
        common.dump(output / "plan.json", original)
        source = "experiments/m4/installed_study/worker.py"
        target = output / "sources" / source
        target.write_bytes(target.read_bytes() + b"\n# resealed altered source\n")
        changed = copy.deepcopy(original)
        changed["provenance"]["sources"][source] = common.digest(target.read_bytes())
        common.dump(output / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "application/source provenance"):
            report.validate_frozen(output, files())

    @unittest.skipUnless(os.name == "posix", "POSIX live stage ownership")
    def test_real_stage_receipt_requires_observed_cleanup_and_matching_exit(self):
        log = self.root / "stage.log"
        argv = [sys.executable, "-I", "-B", "-S", "-c", "print('controlled-stage')"]
        code, error = supervise(argv, log, 5, Control(), grace_seconds=0.1)
        self.assertEqual((code, error), (0, None))
        receipt = validate_receipt(log, argv, 5, 0, "completed", 0.1)
        self.assertEqual(receipt["remaining_owned_processes"], [])
        sidecar = log.with_suffix(".log.ownership.json")
        sidecar.unlink()
        with self.assertRaises(FileNotFoundError):
            validate_receipt(log, argv, 5, 0, "completed", 0.1)
        for change in (
            {"remaining_owned_processes": [{"pid": 123}]},
            {"exit_code": 7},
            {"status": "failed"},
            {"timeout_seconds": 6},
        ):
            common.dump(sidecar, {**receipt, **change})
            with self.assertRaises(ValueError):
                validate_receipt(log, argv, 5, 0, "completed", 0.1)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO admission control")
    def test_reader_refuses_fifo_manifest_without_blocking(self):
        archive = self.root / "archive"
        archive.mkdir()
        os.mkfifo(archive / "manifest.json")
        script = (
            "import sys;sys.path.insert(0,sys.argv[1]);"
            "from experiments.m4.installed_study.report import reconstruct;"
            "reconstruct(sys.argv[2])"
        )
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-S", "-c", script, str(ROOT), str(archive)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bounded regular copies", result.stderr)


if __name__ == "__main__":
    unittest.main()
