"""Composition boundaries, archive reconstruction and retained failures without SciPy."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.causal_secretion.common import SOLVERS
from experiments.m4.feedback_observation.adapter import diagnostic_inputs, prepare
from experiments.m4.paired_kinetics.common import dump, file_hashes
from experiments.m4.researcher_workflow import common, observation, report, run


def source_fixture(case_id, solver):
    scenario, mode = observation.split_case(case_id)
    times = [i * 0.25 for i in range(961)]
    states = [[0.0] * 20 for _ in times]
    for t, row in zip(times, states, strict=True):
        row[3], row[5], row[16] = 140.0, 20.0, t
    return {
        "schema": "bc008-trajectory/1" if mode == "bc008_reference" else "m4-causal-trajectory/1",
        "status": "completed",
        "failure": None,
        "times": times,
        "states": states,
        "source_rates": [[1.0, 1.0] for _ in times],
        "baseline": {"Sb_pmol_kg_min": 1.0},
        "source_active": True,
        "mode": mode,
        "load_mg": 0 if scenario == "fasting" else 30000,
        "solver": {"name": solver},
    }


def equilibrium(bundle):
    return [[*bundle["initial"][:2], t, t] for t in bundle["times"]]


def case_fixture(p, case_id):
    src = source_fixture(case_id, "reference")
    boundary = prepare(p, src)

    def states(b):
        return [
            [*b["initial"][:2], t * b["appearance_scale"], t * b["appearance_scale"]]
            for t in b["times"]
        ]

    return {
        "schema": observation.CASE_SCHEMA,
        "id": case_id,
        "status": "completed",
        "boundary": boundary,
        "states": {name: states(boundary) for name in SOLVERS},
        "oracle": states(boundary),
        "diagnostics": {
            name: {"boundary": b, "states": states(b)}
            for name, b in diagnostic_inputs(p, src, src).items()
        },
    }


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.p = common.read(common.ROOT / "experiments/m4/feedback_observation/protocol.json")
        self.config = common.read(common.HERE / "dalla_man.json")

    def test_config_is_bounded_and_paths_are_relative_to_config(self):
        value, paths, declared = common.intake(common.HERE / "dalla_man.json")
        self.assertEqual(value, self.config)
        self.assertTrue(paths["model"].is_file())
        self.assertEqual(common.sha256(paths["model"]), declared["source_sha256"])
        for edit in (
            {"timeout_seconds": True},
            {"timeout_seconds": 0},
            {"extra": 1},
            {"model": ""},
        ):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                common.validate_config(self.config | edit)

    def test_bad_hash_and_symlink_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "model.py").write_text("raise RuntimeError('must never be imported')\n")
            declared = common.read(common.HERE.parent / "causal_secretion/example_model.json")
            dump(folder / "model.json", declared)
            config = self.config | {"model": "model.py", "declaration": "model.json"}
            dump(folder / "config.json", config)
            with self.assertRaisesRegex(ValueError, "source hash"):
                run.execute(folder / "output", folder / "config.json")
            self.assertFalse((folder / "output").exists())
            (folder / "link.json").symlink_to(folder / "config.json")
            with self.assertRaisesRegex(ValueError, "regular JSON"):
                common.intake(folder / "link.json")

    def test_frozen_composition(self):
        p = common.validate_protocol(common.read(common.HERE / "protocol.json"))
        changed = copy.deepcopy(p)
        changed["boundary"]["appearance_ratio"] = 0.5
        with self.assertRaisesRegex(ValueError, "frozen"):
            common.validate_protocol(changed)

    def test_six_case_scope_and_parent_identity(self):
        self.assertEqual(len(observation.case_ids()), 6)
        src = source_fixture("gastric_load_30g--bc008_reference", "reference")
        for edit in (
            {"load_mg": 0},
            {"source_active": False},
            {"solver": {"name": "tight"}},
            {"status": "failed"},
        ):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                observation.validate_parent(
                    "gastric_load_30g--bc008_reference", src | edit, "reference"
                )

    def test_bad_boundary_initial_inventory_and_missing_diagnostics(self):
        case_id = "gastric_load_30g--host_constant_basal"
        src, tight = (source_fixture(case_id, s) for s in ("reference", "tight"))
        item = case_fixture(self.p, case_id)
        self.assertLess(
            observation.assess(self.p, item, src, tight)["checks"]["equilibrium_drift_pmol_l"], 1e-7
        )
        for mutate in (
            lambda x: x["boundary"]["forcing"]["left"].__setitem__(0, 2.0),
            lambda x: x["boundary"]["initial"].__setitem__(0, 0),
            lambda x: x["diagnostics"].pop("liver_fault"),
            lambda x: x["states"]["reference"].pop(),
        ):
            altered = copy.deepcopy(item)
            mutate(altered)
            with self.assertRaises(ValueError):
                observation.assess(self.p, altered, src, tight)

    def test_runtime_and_failed_worker_are_not_accepted(self):
        worker = {
            "schema": observation.WORKER_SCHEMA,
            "label": "primary",
            "status": "completed",
            "failures": [],
            "runtime": {"python": "3.12.13", "numpy": "2.2.6", "scipy": "1.15.3"},
        }
        observation.validate_worker(self.p, worker, "primary")
        for edit in (
            {"label": "repeat"},
            {"status": "failed"},
            {"failures": ["fasting--candidate"]},
            {"runtime": worker["runtime"] | {"numpy": "1.26.4"}},
            {"runtime": worker["runtime"] | {"python": "3.13.0"}},
        ):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                observation.validate_worker(self.p, worker | edit, "primary")

    def test_failed_stage_preserves_plan_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "failed"
            with patch.object(run, "command", side_effect=TimeoutError("controlled deadline")):
                with self.assertRaisesRegex(TimeoutError, "controlled deadline"):
                    run.execute(output, common.HERE / "dalla_man.json")
            failure = report.reconstruct(output, allow_failed=True)
            self.assertFalse(failure["passed"])
            self.assertEqual(failure["accepted_observation_cases"], 0)
            self.assertEqual(set(failure["case_accounting"]["primary"].values()), {"not_attempted"})
            self.assertEqual(len(failure["case_accounting"]["repeat"]), 6)
            before = (output / "manifest.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run.execute(output, common.HERE / "dalla_man.json")
            self.assertEqual(before, (output / "manifest.json").read_bytes())
            (output / "model.py").write_text("# changed\n")
            with self.assertRaisesRegex(ValueError, "Changed/missing"):
                report.reconstruct(output, allow_failed=True)

    def test_truncated_failed_evidence_remains_reconstructible(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "failed"
            with patch.object(run, "command", side_effect=TimeoutError("controlled")):
                with self.assertRaises(TimeoutError):
                    run.execute(output, common.HERE / "dalla_man.json")
            (output / "model.json").write_text('{"truncated":')
            path = output / "observations/primary/cases/fasting--candidate.json"
            path.parent.mkdir(parents=True)
            path.write_text('{"truncated":')
            manifest = common.read(output / "manifest.json")
            manifest["files"] = file_hashes(output)
            manifest["verification_checks"] = {
                "mass_error_pmol_kg": {"value": 1.0, "limit": 1e-7, "passed": False}
            }
            dump(output / "manifest.json", manifest)
            failure = report.reconstruct(output, allow_failed=True)
            self.assertEqual(failure["case_accounting"]["primary"]["fasting--candidate"], "invalid")
            self.assertEqual(failure["accepted_observation_cases"], 0)
            self.assertFalse(
                failure["recorded_verification_checks"]["mass_error_pmol_kg"]["passed"]
            )
            self.assertIn("Recorded failed numerical verification", report.markdown(failure))

    def test_reference_source_snapshots_are_checked_before_reuse(self):
        from experiments.m4.feedback import common as bc

        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            pairs = [("source-" + name, bc.HERE / name) for name in bc.SOURCES]
            pairs += [
                ("source-" + name.replace("/", "__"), common.ROOT / name) for name in bc.REUSED
            ]
            pairs += [
                (name, common.ROOT / "experiments/m0/simglucose" / name)
                for name in ("uv.lock", "pyproject.toml")
            ]
            for name, path in pairs:
                (directory / name).write_bytes(path.read_bytes())
            common.verify_reference_sources(directory)
            (directory / "source-coupled.py").write_text("# altered snapshot\n")
            with self.assertRaisesRegex(ValueError, "snapshot differs"):
                common.verify_reference_sources(directory)

    def test_dotdot_reference_cannot_hide_nested_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "reference").mkdir()
            (folder / "neighbor").mkdir()
            aliased = folder / "neighbor/../reference"
            output = folder / "reference/nested-output"
            with patch("experiments.m4.causal_secretion.common.reference") as validate:
                with self.assertRaisesRegex(ValueError, "separate directories"):
                    run.execute(output, common.HERE / "dalla_man.json", aliased)
                validate.assert_not_called()
            self.assertFalse(output.exists())

    def complete_fixture(self, output):
        output.mkdir()
        for name in report.required():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
        for name in ("protocol.json", "dalla_man.json"):
            dest = "config.json" if name == "dalla_man.json" else name
            dump(output / dest, common.read(common.HERE / name))
        dump(output / "observation-protocol.json", self.p)
        source = common.HERE.parent / "causal_secretion/example_model.py"
        declared = common.read(source.with_suffix(".json"))
        for prefix in ("", "causal/"):
            (output / prefix / "model.py").write_bytes(source.read_bytes())
            dump(output / prefix / "model.json", declared)
        (output / "causal/reference").mkdir(exist_ok=True)
        (output / "causal/reference/manifest.json").write_bytes(
            (output / "reference/manifest.json").read_bytes()
        )
        for label in ("primary", "repeat"):
            dump(
                output / "observations" / label / "worker.json",
                {
                    "schema": observation.WORKER_SCHEMA,
                    "label": label,
                    "status": "completed",
                    "failures": [],
                    "runtime": {"python": "3.12.13", "numpy": "2.2.6", "scipy": "1.15.3"},
                },
            )
            for case_id in observation.case_ids():
                dump(
                    output / "observations" / label / "cases" / (case_id + ".json"),
                    case_fixture(self.p, case_id),
                )
        manifest = {
            "schema": common.VERSION,
            "protocol": "M4-RESEARCHER/1",
            "status": "calculated",
            "reference_manifest_sha256": common.sha256(output / "reference/manifest.json"),
            "causal_manifest_sha256": common.sha256(output / "causal/manifest.json"),
            "files": file_hashes(output),
        }
        dump(output / "manifest.json", manifest)

    def parent_patches(self):
        return (
            patch.object(
                report,
                "causal_report",
                return_value={
                    "passed": True,
                    "metrics": {},
                    "scenarios": {"fasting": {}, "gastric_load_30g": {}},
                },
            ),
            patch(
                "experiments.m4.causal_secretion.common.reference",
                return_value=({}, {"parameters": {"Vg": 1, "Vi": 1}}, {}, {}),
            ),
            patch.object(
                report,
                "parent_records",
                side_effect=lambda directory, case_id: tuple(
                    source_fixture(case_id, s) for s in ("reference", "tight")
                ),
            ),
        )

    def test_full_reconstruction_and_resealed_ledger_fault(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "archive"
            self.complete_fixture(output)
            a, b, c = self.parent_patches()
            with a, b, c:
                result = report.reconstruct(output, allow_pending=True)
                self.assertTrue(result["passed"])
                self.assertEqual(result["accepted_observation_cases"], 6)
                common.dump_reports(output, result)
                manifest = common.read(output / "manifest.json") | {
                    "status": "completed",
                    "files": file_hashes(output),
                }
                dump(output / "manifest.json", manifest)
                self.assertEqual(report.reconstruct(output), result)
                for label in ("primary", "repeat"):
                    path = output / "observations" / label / "cases/fasting--candidate.json"
                    item = common.read(path)
                    item["states"]["reference"][5][2] += 0.25
                    dump(path, item)
                manifest.update(status="calculated", files=file_hashes(output))
                dump(output / "manifest.json", manifest)
                altered = report.reconstruct(output, allow_pending=True)
                self.assertFalse(altered["passed"])
                self.assertEqual(altered["accepted_observation_cases"], 0)
                self.assertGreater(
                    altered["observation_checks"]["mass_error_pmol_kg"]["value"], 0.2
                )

    def test_missing_observation_and_unexpected_matrix_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "archive"
            self.complete_fixture(output)
            a, b, c = self.parent_patches()
            with a, b, c:
                dump(output / "observations/primary/extra.json", {})
                manifest = common.read(output / "manifest.json") | {"files": file_hashes(output)}
                dump(output / "manifest.json", manifest)
                with self.assertRaisesRegex(ValueError, "unexpected"):
                    report.reconstruct(output, allow_pending=True)
                (output / "observations/primary/extra.json").unlink()
                (output / "observations/repeat/cases/fasting--candidate.json").unlink()
                manifest["files"] = file_hashes(output)
                dump(output / "manifest.json", manifest)
                with self.assertRaisesRegex(ValueError, "Missing required"):
                    report.reconstruct(output, allow_pending=True)


if __name__ == "__main__":
    unittest.main()
