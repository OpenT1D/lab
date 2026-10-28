"""Passive boundaries, immutable reconstruction and process ownership."""

import copy
import hashlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.initial_load import analysis, common, process, report, run


class InitialLoadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.model = b"raise RuntimeError('passive intake executed supplied source')\n"
        (self.folder / "model.py").write_bytes(self.model)
        value = common.read(common.ROOT / "experiments/m4/causal_secretion/example_model.json")
        value["source_sha256"] = hashlib.sha256(self.model).hexdigest()
        common.dump(self.folder / "model.json", value)
        self.config = {
            "schema": common.CONFIG_SCHEMA,
            "sources": [
                {"id": name, "model": "model.py", "declaration": "model.json"}
                for name in ("first", "second")
            ],
            "scenarios": ["fasting", "gastric_load_15g", "gastric_load_30g"],
            "timeout_seconds": 30,
            "source_timeout_seconds": 60,
        }
        self.config_path = self.folder / "config.json"
        common.dump(self.config_path, self.config)

    def failed_archive(self):
        archive, plan, _ = run.freeze(self.config_path, self.folder / "archive")
        state = {
            "schema": common.VERSION,
            "status": "failed",
            "reference": {
                "status": "failed",
                "stage": "historical",
                "attempts": [],
                "error_type": "FixtureFailure",
            },
            "sources": {
                item["id"]: {
                    "status": "not_attempted",
                    "stage": None,
                    "attempts": [],
                    "error_type": None,
                }
                for item in self.config["sources"]
            },
            "interruption_signal": None,
        }
        common.dump(archive / "state.json", state)
        common.seal(archive)
        return archive, plan, state

    def test_passive_intake_retains_order_and_does_not_execute(self):
        config, bundles = common.intake(self.config_path)
        self.assertEqual(config, self.config)
        self.assertEqual(list(bundles), ["first", "second"])
        prepared = common.prepare(self.config_path)
        self.assertEqual(prepared["source_order"], ["first", "second"])
        self.assertEqual(
            [item["initial_gastric_solid_mg"] for item in prepared["scenarios"]], [0, 15000, 30000]
        )
        self.assertEqual(prepared["config_sha256"], common.sha256(self.config_path))

    def test_unsupported_and_ambiguous_config_rejected(self):
        values = []
        for scenarios in ([], ["gastric_load_20g"], ["fasting", "fasting"], [True]):
            value = copy.deepcopy(self.config)
            value["scenarios"] = scenarios
            values.append(value)
        for key, value in (
            ("timeout_seconds", True),
            ("source_timeout_seconds", 10801),
            ("horizon_min", 240),
        ):
            changed = copy.deepcopy(self.config)
            changed[key] = value
            values.append(changed)
        changed = copy.deepcopy(self.config)
        changed["sources"][1]["id"] = "first"
        values.append(changed)
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                common.validate_config(value)

    def test_subset_order_is_configuration(self):
        value = copy.deepcopy(self.config)
        value["scenarios"] = ["gastric_load_30g", "fasting"]
        self.assertEqual(common.validate_config(value)["scenarios"], value["scenarios"])

    def test_raw_config_and_sources_are_frozen(self):
        archive, plan, _ = self.failed_archive()
        self.assertEqual((archive / "config.json").read_bytes(), self.config_path.read_bytes())
        run.verify_frozen(archive, plan)
        (archive / "frozen/first/model.py").write_bytes(b"changed\n")
        with self.assertRaises(ValueError):
            run.verify_frozen(archive, plan)

    def test_failure_reconstruction_keeps_all_denominators(self):
        archive, _, _ = self.failed_archive()
        with self.assertRaises(ValueError):
            report.reconstruct(archive)
        value = report.reconstruct(archive, allow_failed=True)
        self.assertFalse(value["passed"])
        self.assertEqual(value["denominators"]["source_scenarios"], 6)
        self.assertEqual(list(value["sources"]), ["first", "second"])
        self.assertIsNone(value["pairs"][0]["scenarios"]["gastric_load_15g"]["metrics"])
        report.write_reports(archive, value)
        destination = self.folder / "reconstructed"
        report.reconstruct(archive, write_to=destination, allow_failed=True)
        for name in ("report.json", "report.md", "figure.svg"):
            self.assertEqual((archive / name).read_bytes(), (destination / name).read_bytes())

    def test_existing_reports_validated_before_external_write(self):
        archive, _, _ = self.failed_archive()
        report.write_reports(archive, report.reconstruct(archive, allow_failed=True))
        (archive / "report.md").write_text("tampered\n")
        destination = self.folder / "reconstructed"
        with self.assertRaises(ValueError):
            report.reconstruct(archive, write_to=destination, allow_failed=True)
        self.assertFalse(destination.exists())

    def test_resealed_config_load_and_parameter_mutations_rejected(self):
        for target in ("config", "protocol", "declaration"):
            with self.subTest(target=target):
                archive, _, _ = self.failed_archive()
                if target == "config":
                    value = common.read(archive / "config.json")
                    value["scenarios"] = ["gastric_load_15g"]
                    common.dump(archive / "config.json", value)
                elif target == "protocol":
                    value = common.read(archive / "plan.json")
                    value["protocol"]["scenarios"][1]["initial_gastric_solid_mg"] = 16000
                    common.dump(archive / "plan.json", value)
                else:
                    value = common.read(archive / "frozen/first/model.json")
                    value["parameters"]["alpha"] = 0.9
                    common.dump(archive / "frozen/first/model.json", value)
                common.seal(archive)
                with self.assertRaises(ValueError):
                    report.reconstruct(archive, allow_failed=True)
                import shutil

                shutil.rmtree(archive)

    def test_state_interruption_provenance_rejected_after_reseal(self):
        archive, _, state = self.failed_archive()
        state["status"] = "interrupted"
        common.dump(archive / "state.json", state)
        common.seal(archive)
        with self.assertRaises(ValueError):
            report.reconstruct(archive, allow_failed=True)

    def test_failed_truncated_worker_is_diagnostic_not_acceptance(self):
        archive, _, state = self.failed_archive()
        state["reference"].update(status="completed", stage="verification", error_type=None)
        # Direct diagnostic parsing is deliberately tolerant; completed owners
        # still need all independently verified reference/numerical evidence.
        path = archive / "children/first/primary"
        path.mkdir(parents=True)
        (path / "worker.json").write_text('{"status":')
        self.assertEqual(
            report.diagnostic_worker(archive, Path("children/first/primary/worker.json"))["status"],
            "missing_or_invalid_diagnostic",
        )

    def test_reconstruction_rejects_overlap_and_existing_destination(self):
        archive, _, _ = self.failed_archive()
        for destination in (archive, archive / "inside", self.folder):
            with (
                self.subTest(destination=destination),
                self.assertRaises((ValueError, FileExistsError)),
            ):
                report.reconstruct(archive, write_to=destination, allow_failed=True)

    def test_signed_trapezoids_use_full_grid(self):
        times = [index * 0.25 for index in range(961)]
        left = {
            "times": times,
            **{signal: [1.0] * 961 for signal in ("glucose", "insulin", "cpeptide")},
        }
        right = {
            "times": times,
            **{signal: [3.0] * 961 for signal in ("glucose", "insulin", "cpeptide")},
        }
        value = analysis.contrast(left, right)
        self.assertEqual(
            value["glucose"],
            {
                "signed_auc_difference": -480.0,
                "signed_time_mean_difference": -2.0,
                "maximum_absolute_pointwise_difference": 2.0,
            },
        )
        right["times"] = times[:-1]
        with self.assertRaises(ValueError):
            analysis.contrast(left, right)

    def test_generated_reference_binding_does_not_mutate_frozen_plan(self):
        archive, plan, _ = self.failed_archive()
        historical = archive / "historical"
        historical.mkdir()
        common.dump(historical / "manifest.json", {"synthetic": "reference"})
        common.dump(
            archive / "reference-binding.json",
            {
                "schema": "m4-initial-load-reference-binding/1",
                "manifest_sha256": common.sha256(historical / "manifest.json"),
                "config_sha256": plan["config_sha256"],
            },
        )
        # No original-source execution occurs; exercise the post-generation
        # binding separately from the existing reference reader's own tests.
        native = {"parameters": {}}
        with patch.object(
            analysis, "verify_reference", return_value=({}, native, {"initial": []}, {})
        ):
            self.assertEqual(analysis.context(archive, plan)[3], native)
        self.assertIsNone(plan["historical_manifest_sha256"])
        self.assertEqual(common.read(archive / "plan.json"), plan)

    def test_worker_command_uses_declared_isolated_runtime(self):
        args = run.worker_args(self.folder, "observer", "repeat", "first")
        self.assertEqual(
            args[0], str(common.ROOT / "experiments/m4/beta_cell/runtime/.venv/bin/python")
        )
        self.assertEqual(args[-4:], ["--label", "repeat", "--source", "first"])

    def test_source_runtime_metadata_semantics(self):
        worker = {
            "schema": "m4-initial-load-worker/1",
            "kind": "source",
            "source": "first",
            "label": "primary",
            "status": "completed",
            "attempts": [],
            "runtime": {"python": "3.12.13", "numpy": "1.26.4", "scipy": "1.13.1"},
            "native_identity": {"profile": "adult#001"},
        }
        runtime = {"python": "3.12", "numpy": "1.26.4", "scipy": "1.13.1"}
        analysis.validate_worker(
            worker, "source", "first", "primary", runtime, [], worker["native_identity"]
        )
        worker["runtime"]["numpy"] = "2.2.6"
        with self.assertRaises(ValueError):
            analysis.validate_worker(
                worker, "source", "first", "primary", runtime, [], worker["native_identity"]
            )

    def native_record(self):
        return {
            "identity": {
                "upstream_revision": "pinned-revision",
                "package_version": "0.2.11",
                "profile": "adult#001",
                "patient_file_sha256": "a" * 64,
                "parameter_file_sha256": "b" * 64,
                "patient_file": "/original/site-packages/simglucose/patient/t1dpatient.py",
                "parameter_file": "/original/site-packages/simglucose/params/vpatient_params.csv",
                "body_weight_kg": 102.32,
                "kinetic_parameters": {"BW": 102.32, "Vi": 0.054906},
            },
            "parameters": {"Name": "adult#001", "BW": 102.32, "Vi": 0.054906},
            "runtime": {"python": "3.12.13", "numpy": "1.26.4", "scipy": "1.13.1"},
        }

    def test_relocated_native_reference_preserves_full_current_worker_identity(self):
        historical = self.native_record()
        current = copy.deepcopy(historical)
        for key in ("patient_file", "parameter_file"):
            current["identity"][key] = current["identity"][key].replace("/original/", "/current/")
        common.validate_native_record(current, historical)
        self.assertNotEqual(current["identity"], historical["identity"])
        worker = {
            "schema": "m4-initial-load-worker/1",
            "kind": "source",
            "source": "first",
            "label": "primary",
            "status": "completed",
            "attempts": [],
            "runtime": current["runtime"],
            "native_identity": current["identity"],
        }
        runtime = {**current["runtime"], "python": "3.12"}
        analysis.validate_worker(
            worker, "source", "first", "primary", runtime, [], current["identity"]
        )
        with self.assertRaises(ValueError):
            analysis.validate_worker(
                worker, "source", "first", "primary", runtime, [], historical["identity"]
            )
        self.assertEqual(historical, self.native_record())

    def test_relocated_reference_rejects_every_other_identity_or_parameter_change(self):
        historical = self.native_record()
        for key in historical["identity"]:
            if key in {"patient_file", "parameter_file"}:
                continue
            current = copy.deepcopy(historical)
            value = current["identity"][key]
            current["identity"][key] = (
                {**value, "Vi": 0.1}
                if isinstance(value, dict)
                else value + 1
                if isinstance(value, float)
                else value + "-changed"
            )
            with self.subTest(identity=key), self.assertRaises(ValueError):
                common.validate_native_record(current, historical)
        for key in historical["parameters"]:
            current = copy.deepcopy(historical)
            current["parameters"][key] = "changed"
            with self.subTest(parameter=key), self.assertRaises(ValueError):
                common.validate_native_record(current, historical)
        for key in historical["runtime"]:
            current = copy.deepcopy(historical)
            current["runtime"][key] = "changed"
            with self.subTest(runtime=key), self.assertRaises(ValueError):
                common.validate_native_record(current, historical)
        current = copy.deepcopy(historical)
        current["identity"]["unexpected_scientific_field"] = 1
        with self.assertRaises(ValueError):
            common.validate_native_record(current, historical)
        for key in ("patient_file", "parameter_file"):
            current = copy.deepcopy(historical)
            del current["identity"][key]
            with self.subTest(missing_provenance=key), self.assertRaises(ValueError):
                common.validate_native_record(current, historical)

    def test_completed_owner_cannot_hide_failed_exit(self):
        owner = {
            "status": "completed",
            "stage": "verification",
            "error_type": None,
            "attempts": [
                {"status": "completed", "argv": ["worker"], "exit_code": 1, "error_type": None}
            ],
        }
        with self.assertRaises(ValueError):
            report.owner_state(owner)

    def test_launch_failure_retains_reconstructible_full_roster(self):
        with patch.object(
            run, "supervise", side_effect=FileNotFoundError("missing worker executable")
        ):
            value = run.run_study(self.config_path, self.folder / "launch-failure")
        self.assertFalse(value["passed"])
        attempt = value["reference"]["execution"]["attempts"][0]
        self.assertEqual(attempt["status"], "failed")
        self.assertIsNone(attempt["exit_code"])
        self.assertEqual(value["denominators"]["source_scenarios"], 6)
        self.assertEqual(value["sources"]["second"]["status"], "not_attempted")

    def test_completed_owner_missing_stages_rejected(self):
        archive, plan, _ = self.failed_archive()
        owner = {"status": "completed", "stage": "verification", "error_type": None, "attempts": []}
        with self.assertRaises(ValueError):
            report.ledger(archive, owner, ["reference_primary", "reference_repeat"], plan)

    def test_common_reference_parent_mutation_rejected_after_seal(self):
        archive, _, _ = self.failed_archive()
        (archive / "reference/primary").mkdir(parents=True)
        common.dump(archive / "reference/primary/case.json", {"states": [1.0]})
        common.dump(
            archive / "reference-manifest.json",
            {
                "schema": "m4-initial-load-reference-seal/1",
                "files": common.reference_snapshot(archive),
            },
        )
        common.verify_reference_snapshot(archive)
        common.dump(archive / "reference/primary/case.json", {"states": [2.0]})
        with self.assertRaises(ValueError):
            common.verify_reference_snapshot(archive)

    def test_exited_leader_does_not_leave_resistant_owned_descendant(self):
        pidfile = self.folder / "descendant.pid"
        child = (
            "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);"
            "print('ready',flush=True);time.sleep(60)"
        )
        leader = (
            "import subprocess,sys,pathlib;"
            f"p=subprocess.Popen([sys.executable,'-c',{child!r}],stdout=subprocess.PIPE);"
            "p.stdout.readline();"
            f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))"
        )
        control = process.Control()
        code, error = process.supervise(
            [sys.executable, "-B", "-c", leader],
            self.folder / "process.log",
            3,
            control,
            grace_seconds=0.05,
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "UnreapedWorkerGroup")
        self.assertIsNone(control.active)
        pid = int(pidfile.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            self.fail("Owned resistant descendant remains after supervisor cleanup")


if __name__ == "__main__":
    unittest.main()
