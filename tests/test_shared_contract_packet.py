"""OT-059 metadata controls plus actual existing readers, without native setup."""

import copy
import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m4.secure_study import common as m4
from experiments.m4.secure_study import report as m4_report
from experiments.m4.secure_study import run as m4_run
from experiments.observation_analysis import plan as mmtt_plan
from experiments.observation_analysis import run as mmtt_run
from experiments.shared_contracts import inventory as inventory_module
from experiments.shared_contracts.core import asset, identity, record, validate
from experiments.shared_contracts.inventory import inventory
from experiments.shared_contracts.selected import FIXTURES, ROOT, boundary, reader
from experiments.workflows.registry import TASKS


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class ContractPacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(FIXTURES, self.root)
        self.packet = load(self.root / "packet.json")
        self.outcomes = load(self.root / "outcomes.json")["cases"]

    def test_frozen_inventory_covers_ten_exact_route_boundaries(self):
        frozen = load(ROOT / "experiments/shared_contracts/route-inventory.json")
        self.assertEqual(frozen, inventory())
        self.assertEqual(set(frozen["routes"]), set(TASKS))
        self.assertEqual(len(TASKS), 10)
        for name in ("mmtt-sensitivity", "mmtt-sampling"):
            self.assertFalse(frozen["routes"][name]["historical_helper_supported"])
        self.assertEqual(set(frozen["routes"]["m3-forecast"]["execution_projects"]), {"."})
        self.assertEqual(len(frozen["routes"]["m4-study-secure"]["execution_projects"]), 3)
        for task, helper in (
            ("p1-controller", "experiments/m1/report.py"),
            ("m3-forecast", "experiments/m3/workflow.py"),
            ("m3-compare", "experiments/m3/azt1d/study.py"),
            ("m4-secretion", "experiments/m4/hepatic/model.py"),
        ):
            self.assertIn(helper, frozen["routes"][task]["reader_static_dependencies_sha256"])

    def test_reader_inventory_tracks_lazy_helpers_and_implicit_parent_initializers(self):
        source_root = self.root / "source-copy"
        for name, code in {
            "experiments/__init__.py": "from . import bootstrap\n",
            "experiments/bootstrap.py": "VALUE = 1\n",
            "experiments/review_fixture/__init__.py": "",
            "experiments/review_fixture/__main__.py": (
                "def reconstruct():\n    from .. import helper\n"
            ),
            "experiments/helper.py": "VALUE = 2\n",
        }.items():
            path = source_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code)
        with (
            patch.object(inventory_module, "ROOT", source_root),
            patch.object(inventory_module.m4_study, "ROOT", source_root),
        ):
            before = inventory_module.reader_source_inventory("experiments.review_fixture")
            paths = before["reader_static_dependencies_sha256"]
            self.assertIn("experiments/review_fixture/__main__.py", before["reader_source_roots"])
            self.assertIn("experiments/helper.py", paths)
            self.assertIn("experiments/__init__.py", paths)
            self.assertIn("experiments/bootstrap.py", paths)
            for name in ("experiments/helper.py", "experiments/bootstrap.py"):
                with self.subTest(name=name):
                    path = source_root / name
                    original = path.read_bytes()
                    path.write_bytes(original + b"# changed reader dependency\n")
                    after = inventory_module.reader_source_inventory("experiments.review_fixture")
                    self.assertNotEqual(
                        paths[name], after["reader_static_dependencies_sha256"][name]
                    )
                    path.write_bytes(original)

    def test_positive_payloads_derived_lineage_and_native_metadata(self):
        validate(self.packet, self.root)
        base, derived, mmtt = self.packet["plans"]
        self.assertEqual(derived["parent_id"], base["id"])
        self.assertEqual(len(base["planned_slots"]), 2)
        self.assertEqual(len(derived["planned_slots"]), 2)
        self.assertEqual(len(mmtt["planned_slots"]), 3)
        for path, scenario, amount in (
            ("m4-fasting.json", "fasting", 0),
            ("m4-gastric-15g.json", "gastric_load_15g", 15000),
        ):
            # Authoritative intake resolves the unchanged example source bytes.
            prepared = m4.prepare(FIXTURES / path)
            self.assertEqual(prepared["source_order"], ["dalla_man", "ultradian"])
            self.assertEqual(
                prepared["scenarios"], [{"id": scenario, "initial_gastric_solid_mg": amount}]
            )
            p = prepared["protocol"]
            self.assertEqual(p["conditions"]["horizon_min"], 240)
            self.assertEqual(p["conditions"]["sample_step_min"], 0.25)
            self.assertEqual(p["conditions"]["sample_count"], 961)
        settings = load(self.root / "mmtt-settings.json")
        self.assertEqual(
            [v["id"] for v in settings["variants"]], ["nominal", "volume-120", "peripheral-075"]
        )
        self.assertEqual(settings["uncertainty"]["draws"], 128)

    def test_refused_bytes_version_family_roster_and_parent_even_after_reidentification(self):
        original = copy.deepcopy(self.packet)
        for field, value, message in (
            ("schema", "opent1d.shared-plan/2", "Unsupported plan schema"),
            ("family", "sampled-stateful-control/1-provisional", "family differs"),
            ("planned_slots", ["dalla_man/fasting"], "planned_slots differs"),
            ("parent_id", "0" * 64, "Parent must"),
        ):
            changed = copy.deepcopy(original)
            plan = changed["plans"][0]
            plan[field] = value
            plan["id"] = identity(plan)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                validate(changed, self.root)
        (self.root / "mmtt-observations.csv").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Asset bytes changed"):
            validate(original, self.root)

    def test_refused_science_and_unsafe_asset_paths(self):
        cases = {case["id"]: case for case in load(FIXTURES / "cases.json")["cases"]}
        config = load(FIXTURES / "m4-fasting.json")
        config.update(cases["m4-refused-load"]["mutation"])
        with self.assertRaises(ValueError):
            boundary("m4-study-secure", {"config.json": json.dumps(config).encode()})
        package = load(FIXTURES / "mmtt-package.json")
        package["units"]["cpeptide"] = cases["mmtt-refused-units"]["mutation"]["units.cpeptide"]
        with self.assertRaisesRegex(ValueError, "convert before import"):
            boundary(
                "mmtt-sensitivity",
                {
                    "package.json": json.dumps(package).encode(),
                    "settings.json": (FIXTURES / "mmtt-settings.json").read_bytes(),
                    "observations.csv": (FIXTURES / "mmtt-observations.csv").read_bytes(),
                },
            )
        for path in (
            "../private",
            "/private",
            "a/../mmtt-package.json",
            "a\\b",
            "./mmtt-package.json",
            "C:/outside.json",
            "report.json:private-stream",
        ):
            changed = copy.deepcopy(self.packet)
            changed["assets"][0]["path"] = path
            changed["assets"][0]["id"] = identity(changed["assets"][0])
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "relative asset"):
                validate(changed, self.root)

    def attach_result(self, plan, archive, *, reconstruction="verified"):
        report_ref = asset(
            self.root, archive.relative_to(self.root).as_posix() + "/report.json", "native-report"
        )
        execution_name = "state.json" if plan["task"] == "m4-study-secure" else "execution.json"
        execution_ref = asset(
            self.root, archive.relative_to(self.root).as_posix() + "/" + execution_name, "execution"
        )
        report, execution = load(archive / "report.json"), load(archive / execution_name)
        complete = (
            report["passed"]
            if plan["task"] == "m4-study-secure"
            else report["coverage"]["complete_cohort"]
        )
        attempt = record(
            "attempt",
            plan_id=plan["id"],
            ordinal=1,
            execution_status=execution["status"],
            slot_statuses={
                slot: "complete"
                if complete
                else "failed"
                if execution["status"] == "completed"
                else "unavailable"
                for slot in plan["planned_slots"]
            },
        )
        result = record(
            "result",
            attempt_id=attempt["id"],
            report_asset=report_ref["id"],
            execution_asset=execution_ref["id"],
            reader=reader(plan["task"]),
            states={
                "completeness": "complete" if complete else "incomplete",
                "reconstruction": reconstruction,
                "scientific_evidence": "synthetic-only",
            },
        )
        self.packet["assets"].extend((report_ref, execution_ref))
        self.packet["attempts"].append(attempt)
        self.packet["results"].append(result)
        validate(self.packet, self.root)
        return attempt, result

    def m4_failed(self):
        archive = self.root / "m4-failed"
        with patch(
            "experiments.m4.secure_study.adapter.supervise",
            side_effect=FileNotFoundError("controlled absent worker"),
        ) as spawn:
            report = m4_run.run_study(FIXTURES / "m4-fasting.json", archive)
        self.assertEqual(spawn.call_count, 1)
        self.assertFalse(report["passed"])
        self.assertEqual(report["denominators"]["source_scenarios"], 2)
        self.assertEqual(set(report["sources"]), {"dalla_man", "ultradian"})
        with self.assertRaisesRegex(ValueError, "allow_failed"):
            m4_report.reconstruct(archive)
        moved = self.root / "moved-m4"
        archive.rename(moved)
        rebuilt = self.root / "m4-rebuilt"
        m4_report.reconstruct(moved, rebuilt, allow_failed=True)
        for name in ("report.json", "report.md", "figure.svg"):
            self.assertEqual((moved / name).read_bytes(), (rebuilt / name).read_bytes())
        self.assertEqual(
            {
                "report_schema": report["schema"],
                "execution_status": load(moved / "state.json")["status"],
                "passed": report["passed"],
                "denominators": report["denominators"],
                "source_statuses": {
                    name: value["status"] for name, value in report["sources"].items()
                },
                "relocated_report_bytes_equal": True,
            },
            self.outcomes["m4-failed-launch-relocated"],
        )
        self.attach_result(self.packet["plans"][0], moved)
        return moved

    def test_m4_controlled_launch_failure_relocates_with_full_roster(self):
        self.m4_failed()

    def updated_native_assets(self):
        changed = copy.deepcopy(self.packet)
        for result in changed["results"]:
            for field in ("report_asset", "execution_asset"):
                saved = next(a for a in changed["assets"] if a["id"] == result[field])
                saved.update(asset(self.root, saved["path"], saved["role"]))
                result[field] = saved["id"]
            result["id"] = identity(result)
        return changed

    def mmtt(self, *, censored=False, interrupted=False):
        if censored:
            (self.root / "mmtt-observations.csv").write_bytes(
                (self.root / "mmtt-censored.csv").read_bytes()
            )
            a = next(a for a in self.packet["assets"] if a["path"] == "mmtt-observations.csv")
            old = a["id"]
            a.update(asset(self.root, a["path"], a["role"]))
            p = self.packet["plans"][2]
            self.assertEqual(p["payload"]["observations.csv"], old)
            p["payload"]["observations.csv"] = a["id"]
            p["id"] = identity(p)
        sealed = self.root / "sealed-mmtt"
        mmtt_plan.freeze(
            self.root / "mmtt-package.json",
            self.root / "mmtt-observations.csv",
            self.root / "mmtt-settings.json",
            sealed,
        )
        archive = self.root / "mmtt-result"
        if interrupted:
            with patch(
                "experiments.observation_analysis.run.evaluate", side_effect=KeyboardInterrupt
            ):
                report = mmtt_run.run(sealed, archive)
        else:
            report = mmtt_run.run(sealed, archive)
        self.assertEqual(report["coverage"]["planned_variant_pairs"], 3)
        self.assertEqual(report["coverage"]["planned_visits"], 2)
        complete = not censored and not interrupted
        self.assertEqual(report["coverage"]["complete_cohort"], complete)
        if not complete:
            with self.assertRaisesRegex(ValueError, "allow-failed"):
                mmtt_run.reconstruct(archive, self.root / "refused-mmtt")
        moved = self.root / "moved-mmtt"
        archive.rename(moved)
        rebuilt = self.root / "mmtt-rebuilt"
        mmtt_run.reconstruct(moved, rebuilt, allow_failed=not complete)
        for name in ("report.json", "report.md"):
            self.assertEqual((moved / name).read_bytes(), (rebuilt / name).read_bytes())
        case = (
            "mmtt-interrupted-relocated"
            if interrupted
            else "mmtt-censored"
            if censored
            else "mmtt-positive-relocated"
        )
        self.assertEqual(
            {
                "report_schema": report["schema"],
                "execution_status": report["execution_status"],
                "coverage": report["coverage"],
                "relocated_report_bytes_equal": True,
            },
            self.outcomes[case],
        )
        self.attach_result(self.packet["plans"][2], moved)
        return moved

    def test_actual_mmtt_complete_and_relocated_packet(self):
        self.mmtt()
        moved_project = self.root.with_name("relocated-project")
        self.root.rename(moved_project)
        validate(self.packet, moved_project)
        forged = copy.deepcopy(self.packet)
        result = forged["results"][0]
        result["states"]["completeness"] = "incomplete"
        result["id"] = identity(result)
        with self.assertRaisesRegex(ValueError, "Evidence states"):
            validate(forged, moved_project)

    def test_mmtt_completed_but_incomplete_keeps_required_variants(self):
        self.mmtt(censored=True)
        self.assertEqual(self.packet["attempts"][0]["execution_status"], "completed")
        self.assertEqual(self.packet["results"][0]["states"]["completeness"], "incomplete")
        self.assertEqual(set(self.packet["attempts"][0]["slot_statuses"].values()), {"failed"})
        self.refuse_promoted_slots()

    def refuse_promoted_slots(self):
        changed = copy.deepcopy(self.packet)
        attempt = changed["attempts"][0]
        attempt["slot_statuses"] = {slot: "complete" for slot in attempt["slot_statuses"]}
        attempt["id"] = identity(attempt)
        result = changed["results"][0]
        result["attempt_id"] = attempt["id"]
        result["id"] = identity(result)
        with self.assertRaisesRegex(ValueError, "Native slot states differ"):
            validate(changed, self.root)

    def test_mmtt_interrupted_has_unavailable_slots_and_reader_refusal(self):
        self.mmtt(interrupted=True)
        attempt = self.packet["attempts"][0]
        self.assertEqual(attempt["execution_status"], "interrupted")
        self.assertEqual(set(attempt["slot_statuses"].values()), {"unavailable"})
        self.refuse_promoted_slots()
        changed = copy.deepcopy(self.packet)
        changed["attempts"][0]["slot_statuses"].popitem()
        changed["attempts"][0]["id"] = identity(changed["attempts"][0])
        with self.assertRaisesRegex(ValueError, "Lost slots"):
            validate(changed, self.root)

    def test_native_plan_version_method_settings_and_denominators_are_bound(self):
        archive = self.mmtt()
        original = load(archive / "report.json")
        for section, field, value in (
            ("plan", "schema", "opent1d.observation-analysis-plan/999"),
            ("plan", "method", "other-method/999"),
            ("plan", "task", "mmtt-sampling"),
            ("plan", "kind", "human"),
            ("plan", "settings", {"variants": []}),
            ("coverage", "planned_variant_pairs", 1),
        ):
            report = copy.deepcopy(original)
            report[section][field] = value
            save(archive / "report.json", report)
            changed = copy.deepcopy(self.packet)
            result = changed["results"][0]
            a = next(a for a in changed["assets"] if a["id"] == result["report_asset"])
            a.update(asset(self.root, a["path"], "native-report"))
            result["report_asset"] = a["id"]
            result["id"] = identity(result)
            with (
                self.subTest(section=section, field=field),
                self.assertRaisesRegex(ValueError, "Native result"),
            ):
                validate(changed, self.root)
        save(archive / "report.json", original)

    def test_lost_attempt_and_unsupported_reader_are_refused(self):
        self.mmtt(interrupted=True)
        changed = copy.deepcopy(self.packet)
        attempt = changed["attempts"][0]
        attempt["ordinal"] = 2
        attempt["id"] = identity(attempt)
        changed["results"][0]["attempt_id"] = attempt["id"]
        changed["results"][0]["id"] = identity(changed["results"][0])
        with self.assertRaisesRegex(ValueError, "Lost or duplicate attempt"):
            validate(changed, self.root)
        changed = copy.deepcopy(self.packet)
        result = changed["results"][0]
        result["reader"]["report_schema"] = "opent1d.observation-analysis/999"
        result["id"] = identity(result)
        with self.assertRaisesRegex(ValueError, "Unsupported reader identity"):
            validate(changed, self.root)

    def test_mmtt_native_status_and_runtime_cannot_be_lost_after_rehashing(self):
        archive = self.mmtt()
        original_report = load(archive / "report.json")
        original_execution = load(archive / "execution.json")
        changed_report = copy.deepcopy(original_report)
        changed_report["execution_status"] = "interrupted"
        save(archive / "report.json", changed_report)
        with self.assertRaisesRegex(ValueError, "report/execution status differs"):
            validate(self.updated_native_assets(), self.root)
        for runtime in (None, "unsupported-runtime/999", {}, {"python": "3.12"}):
            report, execution = copy.deepcopy(original_report), copy.deepcopy(original_execution)
            if runtime is None:
                report["plan"].pop("runtime")
                execution.pop("runtime")
            else:
                report["plan"]["runtime"] = execution["runtime"] = runtime
            save(archive / "report.json", report)
            save(archive / "execution.json", execution)
            with (
                self.subTest(runtime=runtime),
                self.assertRaisesRegex(ValueError, "runtime record"),
            ):
                validate(self.updated_native_assets(), self.root)
        # A saved runtime need not equal the reconstruction host.
        foreign_report, foreign_execution = (
            copy.deepcopy(original_report),
            copy.deepcopy(original_execution),
        )
        foreign_report["plan"]["runtime"]["platform"] = "recorded-other-host"
        foreign_execution["runtime"]["platform"] = "recorded-other-host"
        save(archive / "report.json", foreign_report)
        save(archive / "execution.json", foreign_execution)
        validate(self.updated_native_assets(), self.root)

    def test_m4_native_status_provenance_and_execution_contract_are_bound(self):
        archive = self.m4_failed()
        original = load(archive / "report.json")
        changes = []
        for field, value, reason in (
            ("status", "completed", "report/execution status differs"),
            ("execution", {"unknown": "runtime/999"}, "execution contract differs"),
            ("passed", True, "acceptance/status differs"),
        ):
            report = copy.deepcopy(original)
            report[field] = value
            changes.append((report, reason))
        for sources in (
            {},
            {
                **original["provenance"]["sources"],
                "experiments/m4/secure_study/worker.py": "0" * 64,
            },
        ):
            report = copy.deepcopy(original)
            report["provenance"]["sources"] = sources
            changes.append((report, "implementation differs"))
        promoted = copy.deepcopy(original)
        promoted["passed"] = True
        promoted["denominators"]["accepted_sources"] = 2
        promoted["denominators"]["accepted_source_scenarios"] = 2
        for source in promoted["sources"].values():
            source["accepted"] = True
            for scenario in source["scenarios"].values():
                scenario["accepted"] = True
        changes.append((promoted, "source acceptance/status differs"))
        for report, reason in changes:
            save(archive / "report.json", report)
            changed = self.updated_native_assets()
            if report is promoted:
                attempt = changed["attempts"][0]
                attempt["slot_statuses"] = dict.fromkeys(attempt["slot_statuses"], "complete")
                attempt["id"] = identity(attempt)
                result = changed["results"][0]
                result["attempt_id"] = attempt["id"]
                result["states"]["completeness"] = "complete"
                result["id"] = identity(result)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                validate(changed, self.root)

    def test_control_family_is_stateful_sampled_and_not_rhs(self):
        from experiments.m1.contracts import Observation
        from experiments.p1_external.intake import SuppliedController, declaration

        p1 = importlib.import_module("experiments.p1_external.__main__")
        metadata = declaration(ROOT / "experiments/p1_external/example")
        self.assertEqual(metadata["step_minutes"], 3)
        marker, roster = p1.plan("adult#001", 101, metadata)
        self.assertEqual(roster["cases"], list("ABCD"))
        self.assertEqual(marker["controller"]["action"], "simglucose-pump-rate-u-min/1")
        control = SuppliedController(ROOT / "experiments/p1_external/example", metadata, seed=101)
        control.reset()
        control.command(Observation(0, 200, 0, True), 0)
        control.command(Observation(3, 200, 0, False), 0)
        with self.assertRaisesRegex(ValueError, "Unexpected observation clock"):
            control.command(Observation(9, 200, 9, True), 0)


if __name__ == "__main__":
    unittest.main()
