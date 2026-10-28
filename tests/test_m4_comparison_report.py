"""Scientific support, frozen identities and simulator-free M4 archive reporting."""

import copy
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from experiments.m4.comparison import analysis, common, report, run


def native_report(offset=0.0):
    trajectories = {}
    for scenario in analysis.SCENARIOS:
        for mode in analysis.MODES:
            candidate = mode == "candidate"
            trajectories[f"{scenario}--{mode}"] = {
                "times_min": list(analysis.TIMES),
                "glucose_mg_dl": [
                    100 + (offset * t / 240 if candidate else 0) for t in analysis.TIMES
                ],
                "insulin_pmol_l": [20 + (offset if candidate else 0)] * 961,
                "cpeptide_pmol_l": [30 + (2 * offset if candidate else 0)] * 961,
            }
    return {
        "schema": "m4-researcher-workflow/1",
        "protocol": "M4-RESEARCHER/1",
        "status": "completed",
        "passed": True,
        "model_id": "set in archive fixture",
        "accepted_observation_cases": 6,
        "case_accounting": {
            label: {case_id: "completed" for case_id in trajectories}
            for label in ("primary", "repeat")
        },
        "trajectories": trajectories,
        "causal_checks": {"glucose_error": 0.0},
        "observation_checks": {"mass_error": {"value": 0.0, "limit": 1e-7, "passed": True}},
    }


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.archive = self.folder / "archive"
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.children = {}
        self.stack.enter_context(
            patch.object(
                report,
                "reconstruct_child",
                side_effect=lambda path, **_: copy.deepcopy(self.children[path.name]),
            )
        )
        self.stack.enter_context(
            patch.object(common, "verify_reference", return_value=({}, {}, {}, {"checks": {}}))
        )

    def prepare(self, count=2):
        fixture = common.ROOT / "experiments/m4/causal_secretion"
        identities = ("left", "right", "third")[:count]
        config = {
            "schema": common.CONFIG_SCHEMA,
            "sources": [
                {
                    "id": identity,
                    "model": str(fixture / "example_model.py"),
                    "declaration": str(fixture / "example_model.json"),
                }
                for identity in identities
            ],
            "timeout_seconds": 600,
            "source_timeout_seconds": 3600,
        }
        config_path = self.folder / "config.json"
        common.dump(config_path, config)
        _, self.plan, _ = run.freeze(config_path, self.archive)
        reference = self.archive / "reference"
        reference.mkdir()
        common.dump(
            reference / "manifest.json", {"schema": "bc008/2", "status": "completed", "files": {}}
        )
        self.state = {
            "status": "completed",
            "interruption_signal": None,
            "reference": {
                "status": "completed",
                "error_type": None,
                "exit_code": 0,
                "manifest_sha256": common.sha256(reference / "manifest.json"),
            },
            "sources": {},
        }
        for index, identity in enumerate(identities):
            child = self.archive / "children" / identity
            child.mkdir()
            for name in ("model.py", "model.json", "config.json"):
                shutil.copyfile(self.archive / "frozen" / identity / name, child / name)
            (child / "reference").mkdir()
            shutil.copyfile(reference / "manifest.json", child / "reference/manifest.json")
            self.seal_child(identity)
            self.state["sources"][identity] = {
                "status": "completed",
                "error_type": None,
                "exit_code": 0,
                "manifest_sha256": common.sha256(child / "manifest.json"),
            }
            self.children[identity] = native_report(4.0 if index == 0 else 0.0)
            self.children[identity]["model_id"] = self.plan["sources"][identity]["declaration"][
                "model_id"
            ]
        self.seal()
        return self.archive

    def seal_child(self, identity, status="completed"):
        child = self.archive / "children" / identity
        files = {
            str(path.relative_to(child)): common.sha256(path)
            for path in sorted(child.rglob("*"))
            if path.is_file() and path != child / "manifest.json"
        }
        common.dump(
            child / "manifest.json",
            {"schema": "m4-researcher-workflow/1", "status": status, "files": files},
        )
        if hasattr(self, "state") and identity in self.state["sources"]:
            self.state["sources"][identity]["manifest_sha256"] = common.sha256(
                child / "manifest.json"
            )

    def seal(self):
        common.dump(self.archive / "state.json", self.state)
        common.seal(self.archive)

    def render(self, allow_failed=False):
        return report.reconstruct(self.archive, write_to=self.archive, allow_failed=allow_failed)

    def test_independent_linear_and_constant_signed_contrasts(self):
        self.prepare()
        result = self.render()
        pair = result["pairs"][0]
        self.assertTrue(result["passed"])
        self.assertEqual((pair["left"], pair["right"]), ("left", "right"))
        metrics = pair["scenarios"]["fasting"]["signals"]
        self.assertEqual(
            metrics["glucose_mg_dl"]["metrics"],
            {
                "signed_auc_difference": 480.0,
                "signed_time_mean_difference": 2.0,
                "maximum_absolute_pointwise_difference": 4.0,
            },
        )
        self.assertEqual(metrics["insulin_pmol_l"]["metrics"]["signed_auc_difference"], 960.0)
        self.assertEqual(metrics["cpeptide_pmol_l"]["metrics"]["signed_time_mean_difference"], 8.0)
        reverse = analysis.contrast([0.0] * 961, [3.0] * 961)
        self.assertEqual(
            reverse,
            {
                "signed_auc_difference": -720.0,
                "signed_time_mean_difference": -3.0,
                "maximum_absolute_pointwise_difference": 3.0,
            },
        )

    def test_fresh_reconstruction_is_byte_identical_and_does_not_import_model(self):
        self.prepare()
        self.render()
        output = self.folder / "reconstructed"
        with patch(
            "experiments.m4.causal_secretion.common.load_model",
            side_effect=AssertionError("must not execute"),
        ):
            result = report.reconstruct(self.archive, output)
        self.assertTrue(result["passed"])
        for name in report.REPORTS:
            self.assertEqual((self.archive / name).read_bytes(), (output / name).read_bytes())
        ElementTree.fromstring((output / "figure.svg").read_text())

    def test_short_grid_boolean_time_signal_units_and_partial_repeat_rejected(self):
        self.prepare()
        for mutate in (
            lambda value: value["trajectories"]["fasting--candidate"]["times_min"].pop(),
            lambda value: value["trajectories"]["fasting--candidate"]["times_min"].__setitem__(
                0, False
            ),
            lambda value: value["trajectories"]["fasting--candidate"].__setitem__(
                "insulin_u_l", value["trajectories"]["fasting--candidate"].pop("insulin_pmol_l")
            ),
            lambda value: value["trajectories"].pop("gastric_load_30g--candidate"),
            lambda value: value["case_accounting"]["repeat"].__setitem__(
                "fasting--candidate", "failed"
            ),
            lambda value: value["trajectories"]["fasting--candidate"]["glucose_mg_dl"].__setitem__(
                0, float("nan")
            ),
        ):
            original = copy.deepcopy(self.children["right"])
            mutate(self.children["right"])
            with self.assertRaises(ValueError):
                self.render()
            self.children["right"] = original

    def test_shared_control_mismatch_nulls_every_direct_pair(self):
        self.prepare(3)
        self.children["right"]["trajectories"]["gastric_load_30g--host_constant_basal"][
            "cpeptide_pmol_l"
        ][45] += 0.001
        result = self.render(allow_failed=True)
        self.assertFalse(result["passed"])
        self.assertEqual(result["common_controls"]["status"], "mismatch")
        self.assertTrue(
            all(
                pair["null_reason"] == "shared control trajectories disagree"
                for pair in result["pairs"]
            )
        )
        self.assertTrue(
            all(
                item["metrics"] is None
                for pair in result["pairs"]
                for scenario in pair["scenarios"].values()
                for item in scenario["signals"].values()
            )
        )
        self.assertNotIn("host_constant_basal</text>", report.figure(result))

    def test_failed_third_source_keeps_valid_pair_and_full_roster(self):
        self.prepare(3)
        shutil.rmtree(self.archive / "children/third")
        self.state["status"] = "failed"
        self.state["sources"]["third"] = {
            "status": "failed",
            "error_type": "WorkerExit",
            "exit_code": 1,
            "manifest_sha256": None,
        }
        self.seal()
        result = self.render(allow_failed=True)
        self.assertFalse(result["passed"])
        self.assertEqual(result["planned_source_scenario_count"], 6)
        self.assertEqual(result["accepted_source_scenario_count"], 4)
        self.assertEqual(len(result["pairs"]), 3)
        self.assertTrue(result["pairs"][0]["accepted"])
        self.assertFalse(result["pairs"][1]["accepted"])
        with self.assertRaisesRegex(ValueError, "allow-failed"):
            report.reconstruct(self.archive)

    def test_interrupted_completed_child_never_becomes_accepted(self):
        self.prepare()
        self.state["status"], self.state["interruption_signal"] = "interrupted", 15
        self.state["sources"]["right"].update(
            status="interrupted", error_type="GlobalInterruption", exit_code=-15
        )
        self.seal()
        result = self.render(allow_failed=True)
        self.assertFalse(result["sources"]["right"]["accepted"])
        self.assertFalse(result["pairs"][0]["accepted"])
        self.state["status"], self.state["interruption_signal"] = "failed", None
        self.seal()
        with self.assertRaisesRegex(ValueError, "without global"):
            self.render(allow_failed=True)

    def test_early_failed_prepare_without_declaration_preserves_roster(self):
        self.prepare()
        child = self.archive / "children/right"
        shutil.rmtree(child)
        child.mkdir()
        self.seal_child("right", status="failed")
        self.children["right"] = {
            "status": "failed",
            "passed": False,
            "model_id": "unavailable",
            "stage": "prepare",
            "error": {"type": "OSError"},
            "case_accounting": {
                label: {
                    f"{s}--{m}": "not_attempted" for s in analysis.SCENARIOS for m in analysis.MODES
                }
                for label in ("primary", "repeat")
            },
        }
        self.state["status"] = "failed"
        self.state["sources"]["right"].update(status="failed", error_type="WorkerExit", exit_code=1)
        self.seal()
        result = self.render(allow_failed=True)
        self.assertEqual(result["accepted_source_count"], 1)
        self.assertIn("right", result["sources"])
        self.assertIn("failed stage: prepare", report.markdown(result))

    def test_unsealed_and_truncated_interrupted_child_is_only_diagnostic(self):
        self.prepare()
        path = self.archive / "children/right/manifest.json"
        path.write_bytes(b'{"truncated":')
        self.state["status"], self.state["interruption_signal"] = "interrupted", 2
        self.state["sources"]["right"].update(
            status="interrupted",
            error_type="GlobalInterruption",
            exit_code=-2,
            manifest_sha256=common.sha256(path),
        )
        self.seal()
        result = self.render(allow_failed=True)
        self.assertIsNone(result["sources"]["right"]["single_source"])
        self.assertIn("interrupted", result["sources"]["right"]["null_reason"])

    def test_rewritten_inventories_do_not_hide_child_source_or_extra_file(self):
        self.prepare()
        child = self.archive / "children/right"
        original = (child / "model.py").read_bytes()
        (child / "model.py").write_bytes(b"raise RuntimeError('altered')\n")
        self.seal_child("right")
        self.seal()
        with self.assertRaisesRegex(ValueError, "frozen roster"):
            self.render()
        (child / "model.py").write_bytes(original)
        self.seal_child("right")
        (child / "extra.txt").write_text("not in native manifest")
        self.seal()
        with self.assertRaisesRegex(ValueError, "Native manifest inventory"):
            self.render()

    def test_rewritten_parent_inventory_rejects_worker_budget_and_common_reference(self):
        self.prepare()
        self.plan["sources"]["right"]["effective_config"]["timeout_seconds"] = 601
        common.dump(self.archive / "plan.json", self.plan)
        common.seal(self.archive)
        with self.assertRaisesRegex(ValueError, "worker budget"):
            self.render()
        self.plan["sources"]["right"]["effective_config"]["timeout_seconds"] = 600
        common.dump(self.archive / "plan.json", self.plan)
        path = self.archive / "children/right/reference/manifest.json"
        path.write_text('{"changed":true}')
        self.seal_child("right")
        self.seal()
        with self.assertRaisesRegex(ValueError, "common-reference identity"):
            self.render()

    def test_saved_reports_are_checked_before_external_reconstruction(self):
        self.prepare()
        self.render()
        path = self.archive / "figure.svg"
        path.write_text(path.read_text().replace("M4 synthetic", "Misleading synthetic"))
        destination = self.folder / "new-output"
        with self.assertRaisesRegex(ValueError, "report or figure"):
            report.reconstruct(self.archive, destination)
        self.assertFalse(destination.exists())

    def test_existing_overlap_and_symlink_destinations_refused(self):
        self.prepare()
        self.render()
        (self.folder / "existing").mkdir()
        (self.folder / "alias").symlink_to(self.archive, target_is_directory=True)
        for destination in (
            self.folder / "existing",
            self.archive / "nested",
            self.folder,
            self.folder / "alias",
        ):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                report.reconstruct(self.archive, destination)
        self.assertFalse((self.archive / "nested").exists())

    def test_unattempted_child_and_snapshot_tampering_rejected(self):
        self.prepare()
        self.state["status"] = "failed"
        self.state["sources"]["right"] = run.attempt()
        self.seal()
        with self.assertRaisesRegex(ValueError, "Unattempted source"):
            self.render(allow_failed=True)
        self.state["sources"]["right"] = {
            "status": "completed",
            "error_type": None,
            "exit_code": 0,
            "manifest_sha256": common.sha256(self.archive / "children/right/manifest.json"),
        }
        self.state["status"] = "completed"
        common.dump(self.archive / "state.json", self.state)
        source = "experiments/m4/comparison/analysis.py"
        (self.archive / "sources" / source).write_text("# changed checker snapshot\n")
        self.plan["provenance"]["sources"][source] = common.sha256(
            self.archive / "sources" / source
        )
        common.dump(self.archive / "plan.json", self.plan)
        common.seal(self.archive)
        with self.assertRaisesRegex(ValueError, "snapshot differs"):
            self.render()


if __name__ == "__main__":
    unittest.main()
