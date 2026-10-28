"""Maintained execution boundaries without installing a numerical root runtime."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.causal_secretion import common as causal
from experiments.m4.initial_load import common as historical
from experiments.m4.initial_load import report as historical_report
from experiments.m4.initial_load import run as historical_run
from experiments.m4.secure_study import common, report, run
from experiments.m4.secure_study.adapter import activate, supervise_stage, worker_args
from experiments.m4.secure_study.compat import EntryPoint, native_imports, resource_filename
from experiments.m4.secure_study.runtime import validate, validate_numerical_runtime


class MaintainedStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.config = {
            "schema": common.CONFIG_SCHEMA,
            "sources": [
                {
                    "id": name,
                    "model": str(common.ROOT / model),
                    "declaration": str(common.ROOT / declaration),
                }
                for name, model, declaration in (
                    (
                        "dalla_man",
                        "experiments/m4/causal_secretion/example_model.py",
                        "experiments/m4/causal_secretion/example_model.json",
                    ),
                    (
                        "ultradian",
                        "experiments/m4/ultradian_secretion/model.py",
                        "experiments/m4/ultradian_secretion/model.json",
                    ),
                )
            ],
            "scenarios": ["fasting", "gastric_load_15g", "gastric_load_30g"],
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }
        self.path = self.folder / "config.json"
        common.dump(self.path, self.config)

    def test_lock_changes_only_two_packages_and_science_stays_fixed(self):
        p = common.protocol()
        old = historical.protocol()
        self.assertEqual(set(p["execution"]["changed_packages"]), {"urllib3", "setuptools"})
        self.assertEqual(len(p["execution"]["unchanged_packages"]), 32)
        for name, identity in p["execution"]["unchanged_packages"].items():
            self.assertEqual(identity, common.package_records("experiments/m0/simglucose")[name])
        for key in ("scenarios", "source_contract", "observer", "acceptance", "comparison"):
            self.assertEqual(p[key], old[key])
        numerical = copy.deepcopy(p["numerical"])
        numerical["runtime"]["project"] = old["numerical"]["runtime"]["project"]
        self.assertEqual(numerical, old["numerical"])

    def test_explicit_passive_config_and_prepare(self):
        result = common.prepare(self.path)
        self.assertEqual(result["schema"], "m4-secure-study-preparation/1")
        self.assertEqual(result["source_order"], ["dalla_man", "ultradian"])
        self.assertEqual(result["execution"]["native_project"], common.NATIVE_PROJECT)
        self.assertIn(
            "experiments/m4/secure_study/compat.py", result["implementation_sources_sha256"]
        )
        self.assertEqual(result["configuration"], self.config)
        old = copy.deepcopy(self.config)
        old["schema"] = historical.CONFIG_SCHEMA
        with self.assertRaisesRegex(ValueError, "Explicit maintained"):
            common.validate_config(old)

    def test_context_restores_every_boundary_after_exception(self):
        names = [
            (historical, "VERSION"),
            (historical_run, "supervise"),
            (historical_run, "intake"),
            (historical_report, "validate_frozen"),
            (causal, "reference"),
        ]
        previous = [getattr(module, key) for module, key in names]
        with self.assertRaisesRegex(RuntimeError, "deliberate"):
            with activate():
                self.assertEqual(historical.VERSION, common.VERSION)
                self.assertEqual(historical_report.VERSION, common.VERSION)
                raise RuntimeError("deliberate")
        for (module, key), value in zip(names, previous, strict=True):
            self.assertIs(getattr(module, key), value)
        self.assertEqual(historical.protocol()["id"], "M4-STUDY/2")

    def test_legacy_compatibility_is_narrow_and_restored(self):
        self.assertNotIn("pkg_resources", sys.modules)
        with native_imports():
            self.assertFalse(hasattr(sys.modules["pkg_resources"], "get_distribution"))
            self.assertIs(EntryPoint.parse("x=json:loads").load(False), json.loads)
            with self.assertRaisesRegex(ValueError, "observed"):
                EntryPoint.parse("x=json:loads").load()
            with self.assertRaisesRegex(ValueError, "Only pinned"):
                resource_filename("other", "anything")
            for name in ("../private", "/private", "params/../private"):
                with self.assertRaises(ValueError):
                    resource_filename("simglucose", name)
        self.assertNotIn("pkg_resources", sys.modules)

    def test_commands_bind_explicit_runtime_and_nested_cleanup_allowance(self):
        args = worker_args(self.folder, "source", "repeat", "ultradian")
        self.assertEqual(args[0], str(common.ROOT / common.NATIVE_PROJECT / ".venv/bin/python"))
        self.assertIn("experiments.m4.secure_study.worker", args)
        args = [sys.executable, "-B", "-S", "-m", "experiments.m4.feedback.run", "--output", "x"]
        with patch("experiments.m4.secure_study.adapter.supervise", return_value=(0, None)) as call:
            supervise_stage(args, self.folder / "log", 600, None)
        self.assertIn("experiments.m4.secure_study.reference", args)
        self.assertEqual(args[-2:], ["--timeout-seconds", "600"])
        self.assertEqual(call.call_args.kwargs["grace_seconds"], 20)

    def test_effective_baseline_command_is_recorded_before_spawn(self):
        logs = self.folder / "logs"
        logs.mkdir()
        args = [sys.executable, "-B", "-S", "-m", "experiments.m4.feedback.run", "--output", "x"]
        common.dump(
            self.folder / "state.json",
            {
                "reference": {
                    "attempts": [{"stage": "historical", "status": "started", "argv": args}]
                }
            },
        )

        def spawn(effective, *_args, **_kwargs):
            self.assertEqual(
                common.read(self.folder / "state.json")["reference"]["attempts"][0]["argv"],
                effective,
            )
            self.assertIn("experiments.m4.secure_study.reference", effective)
            return 0, None

        with patch("experiments.m4.secure_study.adapter.supervise", side_effect=spawn):
            supervise_stage(args, logs / "historical.log", 600, None)

    def test_reference_rejects_resealed_scientific_whitespace_changes(self):
        from experiments.m4.secure_study.reference import descriptor, verify

        reference = self.folder / "reference"
        reference.mkdir()
        common.dump(reference / "manifest.json", {"schema": common.REFERENCE_SCHEMA})
        common.dump(reference / "execution.json", descriptor())
        original = (common.ROOT / "experiments/m4/feedback/protocol.json").read_bytes()
        (reference / "protocol.json").write_bytes(original + b"\n")
        with self.assertRaisesRegex(ValueError, "scientific bytes"):
            verify(reference)

    def test_actual_receipt_must_match_numeric_python_and_core_versions(self):
        receipt = {"python": "3.12.13", "distributions": {"numpy": "1.26.4", "scipy": "1.13.1"}}
        numeric = {"python": "3.12.13", "numpy": "1.26.4", "scipy": "1.13.1"}
        validate_numerical_runtime(receipt, numeric)
        for key in numeric:
            wrong = {**numeric, key: "changed"}
            with self.assertRaisesRegex(ValueError, "installed runtime disagree"):
                validate_numerical_runtime(receipt, wrong)

    def test_actual_metadata_is_required_and_cannot_claim_historical_http_version(self):
        p = common.protocol()
        records = p["execution"]["package_records"]
        value = {
            "schema": "m4-secure-runtime-attestation/1",
            "project": common.NATIVE_PROJECT,
            "python": "3.12.13",
            "executable": "/installed/python",
            "distributions": {name: item["version"] for name, item in records.items()},
            "upstream_revisions": {
                name: item["source"]["git"].rsplit("#", 1)[1]
                for name, item in records.items()
                if "git" in item["source"]
            },
            "runtime_files_sha256": {
                name: p["conditions"]["runtime_files_sha256"][common.NATIVE_PROJECT + "/" + name]
                for name in ("pyproject.toml", "uv.lock")
            },
        }
        validate(value, common.NATIVE_PROJECT, p)
        value["distributions"]["urllib3"] = "2.7.0"
        with self.assertRaisesRegex(ValueError, "actual runtime"):
            validate(value, common.NATIVE_PROJECT, p)

    def test_failed_launch_seals_full_roster_and_reconstructs_without_native_imports(self):
        output = self.folder / "archive"
        with patch(
            "experiments.m4.secure_study.adapter.supervise",
            side_effect=FileNotFoundError("missing"),
        ):
            result = run.run_study(self.path, output)
        self.assertFalse(result["passed"])
        self.assertEqual(result["schema"], common.REPORT_SCHEMA)
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["denominators"]["source_scenarios"], 6)
        self.assertTrue(
            all(value["status"] == "not_attempted" for value in result["sources"].values())
        )
        with self.assertRaisesRegex(ValueError, "allow_failed"):
            report.reconstruct(output)
        fresh = self.folder / "reconstructed"
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-S",
                "-m",
                "experiments.m4.secure_study",
                "reconstruct",
                "--archive",
                str(output),
                "--output",
                str(fresh),
                "--allow-failed",
            ],
            cwd=common.ROOT,
            check=True,
            capture_output=True,
        )
        for name in ("report.json", "report.md", "figure.svg"):
            self.assertEqual((output / name).read_bytes(), (fresh / name).read_bytes())
        data = common.read(output / "plan.json")
        self.assertEqual(data["schema"], common.VERSION)
        self.assertEqual(data["protocol"]["id"], "M4-STUDY-SECURE/1")
        self.assertEqual(
            common.read(output / "state.json")["reference"]["attempts"][0]["argv"][4],
            "experiments.m4.secure_study.reference",
        )


if __name__ == "__main__":
    unittest.main()
