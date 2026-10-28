"""Catalogue integrity, native acceptance and conservative scientific compatibility."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue import core
from experiments.catalogue.formats import normalized, study_controls
from experiments.catalogue.storage import digest, dump, inventory
from experiments.m3.researcher.fixtures import fixture
from experiments.m3.researcher.study import run_study
from experiments.m5.researcher_workflow.run import execute, export_example


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.base = Path(cls.fixture.name)
        source = cls.base / "source"
        export_example(source)
        cls.archive = cls.base / "native"
        execute(source, cls.archive)
        other = json.loads((source / "model.json").read_bytes())
        other["model_id"] = "different-frozen-method"
        dump(source / "model.json", other)
        cls.other = cls.base / "other-native"
        execute(source, cls.other)
        invalid = b"def predict(request, state):\n    return None\n"
        (source / "model.py").write_bytes(invalid)
        other["model_id"] = "deliberately-invalid"
        other["source_sha256"] = digest(invalid)
        dump(source / "model.json", other)
        cls.incomplete = cls.base / "incomplete-native"
        execute(source, cls.incomplete)
        forecast = cls.base / "forecast-input"
        fixture(forecast)
        cls.forecast = cls.base / "forecast"
        cls.forecast_other = cls.base / "forecast-other"
        run_study(forecast / "config.json", cls.forecast)
        run_study(forecast / "ridge-config.json", cls.forecast_other)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def index(self, paths=None, task="m5-prognosis"):
        paths = paths or [self.archive]
        config = self.base / "request.json"
        dump(
            config,
            {
                "schema": core.REQUEST,
                "entries": [
                    {
                        "id": f"run-{number}",
                        "task": task,
                        "archive": str(path),
                        "tags": ["local"],
                    }
                    for number, path in enumerate(paths)
                ],
            },
        )
        output = self.base / "catalogue"
        return output, core.index(config, output)

    def test_index_is_metadata_only_even_for_executable_looking_source(self):
        archive = self.base / "p1"
        archive.mkdir()
        sentinel = self.base / "imported"
        source = (
            f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
            "raise RuntimeError('must remain opaque')\n"
        )
        (archive / "controller.py").write_text(source)
        dump(
            archive / "workflow.json",
            {
                "schema": "opent1d.p1-external-workflow/1",
                "profile": "adult#001",
                "seed": 101,
                "controller": {"name": "opaque", "source_sha256": digest(source.encode())},
                "implementation_sha256": {"native": "0" * 64},
            },
        )
        dump(
            archive / "study.json",
            {
                "schema": "opent1d.p1-external-workflow/1",
                "cases": list("ABCD"),
                "status": "completed",
            },
        )
        with patch(
            "experiments.catalogue.core.subprocess.Popen",
            side_effect=AssertionError("passive index launched a worker"),
        ):
            item = core.entry(
                {"id": "opaque", "task": "p1-controller", "archive": str(archive), "tags": []}
            )
        self.assertEqual(item["metadata_status"], "metadata_read")
        self.assertEqual(item["verification"]["status"], "not_requested")
        self.assertFalse(sentinel.exists())

    def test_real_native_reader_accepts_without_changing_source(self):
        before = inventory(self.archive)
        catalogue, _ = self.index()
        verified = core.verify(catalogue, self.base / "verified")
        self.assertEqual(
            verified["entries"][0]["verification"]["status"], "verified_reconstruction"
        )
        self.assertTrue(verified["entries"][0]["verification"]["complete"])
        self.assertEqual(inventory(self.archive), before)
        self.assertEqual(
            len(core.listing(self.base / "verified", tag="local", task="m5-prognosis")["entries"]),
            1,
        )

    def test_emitted_native_forecast_and_prognosis_digests_match(self):
        for task, archive in (("m3-forecast", self.forecast), ("m5-prognosis", self.archive)):
            with self.subTest(task=task):
                before = inventory(archive)
                indexed = core.entry(
                    {"id": "native", "task": task, "archive": str(archive), "tags": []}
                )
                self.assertEqual(indexed["hash_checks"]["status"], "matched")
                self.assertGreater(indexed["hash_checks"]["checked_files"], 0)
                self.assertEqual(indexed["metadata_status"], "metadata_read")
                self.assertEqual(indexed["verification"]["status"], "not_requested")
                self.assertEqual(inventory(archive), before)

    def test_source_changed_after_index_never_verifies(self):
        archive = self.base / "copy"
        shutil.copytree(self.archive, archive)
        catalogue, _ = self.index([archive])
        (archive / "report.md").write_text("tampered report")
        result = core.verify(catalogue, self.base / "verified")
        self.assertEqual(result["entries"][0]["verification"]["status"], "failed")
        self.assertIn("changed since indexing", result["entries"][0]["verification"]["error"])

    def test_rewritten_hash_manifest_is_not_numerical_validation(self):
        archive = self.base / "tampered"
        shutil.copytree(self.archive, archive)
        report = json.loads((archive / "report.json").read_bytes())
        report["candidate_mae_paired_u_day"] += 10
        dump(archive / "report.json", report)
        manifest = json.loads((archive / "manifest.json").read_bytes())
        manifest["files"]["report.json"] = digest((archive / "report.json").read_bytes())
        dump(archive / "manifest.json", manifest)
        catalogue, indexed = self.index([archive])
        self.assertEqual(indexed["entries"][0]["hash_checks"]["status"], "matched")
        result = core.verify(catalogue, self.base / "verified")
        self.assertEqual(result["entries"][0]["verification"]["status"], "failed")

    def test_complete_same_experiment_and_different_method_eligibility(self):
        catalogue, _ = self.index(
            [self.forecast, self.forecast, self.forecast_other], task="m3-forecast"
        )
        core.verify(catalogue, self.base / "verified")
        equal = core.compare(self.base / "verified", "run-0", "run-1")
        self.assertTrue(equal["eligible"])
        self.assertIsNone(equal["metrics"])
        different = core.compare(self.base / "verified", "run-0", "run-2")
        self.assertFalse(different["eligible"])
        self.assertIn("different models", different["reasons"])

    def test_missing_legacy_platform_preserves_verification_but_prevents_repeat(self):
        catalogue, indexed = self.index([self.archive, self.archive])
        self.assertEqual(indexed["entries"][0]["metadata_status"], "metadata_read")
        coverage = indexed["entries"][0]["metadata"]["repeat_condition_coverage"]
        self.assertFalse(coverage["complete"])
        self.assertIn("platform", coverage["reasons"][0])
        verified = core.verify(catalogue, self.base / "verified")
        self.assertTrue(all(item["verification"]["complete"] for item in verified["entries"]))
        result = core.compare(self.base / "verified", "run-0", "run-1")
        self.assertFalse(result["eligible"])
        self.assertIn("run-0: saved repeat conditions incomplete", result["reasons"])

    def study_metadata_fixture(self):
        import copy

        root = self.base / "study"
        root.mkdir()
        config = {"sources": [{"id": "left"}, {"id": "right"}], "scenarios": ["fasting"]}
        dump(
            root / "plan.json",
            {
                "configuration": config,
                "protocol": {"id": "M4-STUDY/2"},
                "provenance": {"python": "3.12.13", "platform": "test-A"},
            },
        )
        native = {
            "runtime": {"python": "3.12.13", "numpy": "1.26.4", "scipy": "1.13.1"},
            "identity": {
                "body_weight_kg": 100,
                "kinetic_parameters": {"m1": 0.15},
                "package_version": "0.2.11",
                "parameter_file": "/old/params.csv",
                "parameter_file_sha256": "0" * 64,
                "patient_file": "/old/patient.py",
                "patient_file_sha256": "1" * 64,
                "profile": "adult#001",
                "upstream_revision": "frozen-upstream",
            },
            "parameters": {"Name": "adult#001", "m1": 0.15},
        }
        curve = {
            "times": [i / 4 for i in range(961)],
            "glucose": [100] * 961,
            "insulin": [10] * 961,
            "cpeptide": [20] * 961,
        }
        source = {
            "accepted": True,
            "curves": {"fasting": {"host_constant_basal": curve, "bc008_reference": curve}},
        }
        shared = {
            "times_min": curve["times"],
            "glucose_mg_dl": curve["glucose"],
            "insulin_pmol_l": curve["insulin"],
            "cpeptide_pmol_l": curve["cpeptide"],
        }
        dump(
            root / "report.json",
            {
                "schema": "m4-initial-load-report/1",
                "protocol": "M4-STUDY/2",
                "passed": True,
                "sources": {name: copy.deepcopy(source) for name in ("left", "right")},
                "common_controls": {
                    "passed": True,
                    "trajectories": {
                        "fasting--" + mode: shared
                        for mode in ("host_constant_basal", "bc008_reference")
                    },
                },
            },
        )
        (root / "historical").mkdir()
        dump(root / "historical/native.json", native)
        for name, folder in [
            (None, root / "reference"),
            ("left", root / "children/left"),
            ("right", root / "children/right"),
        ]:
            if name is not None:
                frozen = root / "frozen" / name
                frozen.mkdir(parents=True)
                dump(frozen / "model.json", {"model_id": name, "source_sha256": "2" * 64})
            for label in ("primary", "repeat"):
                (folder / label).mkdir(parents=True)
                dump(folder / label / "native.json", native)
                dump(
                    folder / label / "worker.json",
                    {
                        "schema": "m4-initial-load-worker/1",
                        "status": "completed",
                        "runtime": native["runtime"],
                        "native_identity": native["identity"],
                    },
                )
                if name is not None:
                    observer = folder / "observations" / label
                    observer.mkdir(parents=True)
                    dump(
                        observer / "worker.json",
                        {
                            "schema": "m4-initial-load-observer/1",
                            "status": "completed",
                            "runtime": {"python": "3.12.13", "numpy": "2.2.6", "scipy": "1.15.3"},
                        },
                    )
        return root

    def test_repeat_signature_binds_exact_runtime_platform_and_native_parameters(self):
        from experiments.catalogue.formats import metadata

        root = self.study_metadata_fixture()
        original = metadata(root, "m4-study", {})
        self.assertTrue(original["repeat_condition_coverage"]["complete"])
        files = {
            "logs/source-source-primary.log": {"sha256": "1" * 64},
            "children/logs/logs/source-run.json": {"sha256": "2" * 64},
            "children/logs/causal/source-common.py": {"sha256": "3" * 64},
            "sources/experiments/numerical.py": {"sha256": "4" * 64},
        }
        signature = metadata(root, "m4-study", files)["conditions_sha256"]
        files["logs/source-source-primary.log"]["sha256"] = "5" * 64
        files["children/logs/logs/source-run.json"]["sha256"] = "6" * 64
        self.assertEqual(metadata(root, "m4-study", files)["conditions_sha256"], signature)
        files["children/logs/causal/source-common.py"]["sha256"] = "7" * 64
        self.assertNotEqual(metadata(root, "m4-study", files)["conditions_sha256"], signature)
        changes = [
            ("plan.json", ("provenance", "python"), "3.12.14"),
            ("plan.json", ("provenance", "platform"), "test-B"),
            ("historical/native.json", ("runtime", "python"), "3.12.14"),
            ("historical/native.json", ("identity", "patient_file_sha256"), "3" * 64),
            ("children/left/primary/native.json", ("parameters", "m1"), 0.16),
            ("children/left/observations/primary/worker.json", ("runtime", "scipy"), "1.15.4"),
        ]
        for relative, keys, value in changes:
            with self.subTest(relative=relative, keys=keys):
                path = root / relative
                raw = path.read_bytes()
                changed = json.loads(raw)
                target = changed
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                dump(path, changed)
                self.assertNotEqual(
                    metadata(root, "m4-study", {})["conditions_sha256"],
                    original["conditions_sha256"],
                )
                path.write_bytes(raw)
        for path in root.rglob("*.json"):
            value = json.loads(path.read_bytes())
            identity = value.get("identity", value.get("native_identity"))
            if identity is not None:
                identity["patient_file"] = "/relocated/patient.py"
                identity["parameter_file"] = "/relocated/params.csv"
                dump(path, value)
        self.assertEqual(
            metadata(root, "m4-study", {})["conditions_sha256"], original["conditions_sha256"]
        )
        path = root / "children/left/observations/primary/worker.json"
        path.unlink()
        with self.assertRaises(FileNotFoundError):
            metadata(root, "m4-study", {})
        report = json.loads((root / "report.json").read_bytes())
        report["passed"] = False
        dump(root / "report.json", report)
        self.assertFalse(metadata(root, "m4-study", {})["repeat_condition_coverage"]["complete"])

    def test_unverified_entries_are_not_eligible(self):
        catalogue, _ = self.index([self.archive, self.archive])
        self.assertFalse(core.compare(catalogue, "run-0", "run-1")["eligible"])

    def test_valid_incomplete_native_archive_stays_incomplete(self):
        catalogue, _ = self.index([self.archive, self.incomplete])
        result = core.verify(catalogue, self.base / "verified")
        incomplete = result["entries"][1]["verification"]
        self.assertEqual(incomplete["status"], "verified_reconstruction")
        self.assertFalse(incomplete["complete"])
        comparison = core.compare(self.base / "verified", "run-0", "run-1")
        self.assertFalse(comparison["eligible"])
        self.assertIn("run-1: experiment incomplete or failed", comparison["reasons"])

    def test_symlink_archive_retains_failed_entry(self):
        archive = self.base / "symlinked"
        shutil.copytree(self.archive, archive)
        (archive / "report.md").unlink()
        (archive / "report.md").symlink_to(self.archive / "report.md")
        _, result = self.index([archive])
        self.assertEqual(result["entries"][0]["metadata_status"], "unavailable")

    def test_catalogue_saved_report_tamper_rejected(self):
        catalogue, _ = self.index()
        (catalogue / "report.md").write_text("changed")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            core.listing(catalogue)

    def test_configuration_parameters_named_model_are_preserved(self):
        self.assertNotEqual(
            normalized({"model": "/path/a.py", "parameters": {"model": 1}}),
            normalized({"model": "/path/b.py", "parameters": {"model": 2}}),
        )
        self.assertEqual(
            normalized({"people": [{"input": {"file": "/old", "sha256": "a"}}]}),
            normalized({"people": [{"input": {"file": "/new", "sha256": "a"}}]}),
        )

    def test_new_study_controls_require_complete_grid_and_exact_agreement(self):
        import copy

        curve = {
            "times": [i / 4 for i in range(961)],
            "glucose": [100] * 961,
            "insulin": [10] * 961,
            "cpeptide": [20] * 961,
        }
        source = {
            "accepted": True,
            "curves": {"fasting": {"host_constant_basal": curve, "bc008_reference": curve}},
        }
        config = {"sources": [{"id": "left"}, {"id": "right"}], "scenarios": ["fasting"]}
        report = {
            "passed": True,
            "common_controls": {
                "passed": True,
                "trajectories": {
                    "fasting--" + mode: {
                        "times_min": curve["times"],
                        "glucose_mg_dl": curve["glucose"],
                        "insulin_pmol_l": curve["insulin"],
                        "cpeptide_pmol_l": curve["cpeptide"],
                    }
                    for mode in ("host_constant_basal", "bc008_reference")
                },
            },
            "sources": {"left": copy.deepcopy(source), "right": copy.deepcopy(source)},
        }
        self.assertTrue(study_controls(report, config)["available"])
        report["sources"]["right"]["curves"]["fasting"]["host_constant_basal"]["glucose"][1] += 1
        with self.assertRaisesRegex(ValueError, "disagree"):
            study_controls(report, config)
        report["sources"]["right"] = copy.deepcopy(source)
        report["sources"]["right"]["curves"]["fasting"]["bc008_reference"]["times"].pop()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            study_controls(report, config)
        self.assertFalse(study_controls({"passed": False}, config)["available"])

    def test_bad_request_and_overlap_refused(self):
        config = self.base / "request.json"
        dump(
            config,
            {
                "schema": core.REQUEST,
                "entries": [
                    {"id": "bad", "task": "unknown", "archive": str(self.archive), "tags": []}
                ],
            },
        )
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            core.index(config, self.base / "new")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            from experiments.catalogue.storage import fresh

            fresh(self.archive / "new-output", [self.archive])


if __name__ == "__main__":
    unittest.main()
