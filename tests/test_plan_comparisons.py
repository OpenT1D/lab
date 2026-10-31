"""Preexecution rosters, native readers, analytical endpoints and immutable prefixes."""

import copy
import csv
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.shared_contracts.selected import FIXTURES
from experiments.shared_services import comparison_tasks as tasks
from experiments.shared_services import comparisons, execution, routes, store


@unittest.skipUnless(os.name == "posix", "Shared project leases require POSIX")
class PlanComparisons(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="plan-comparisons-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.project = store.create(self.root / "project", "Invented constant controls")
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        settings = store.read(FIXTURES / "mmtt-settings.json")
        settings["uncertainty"]["draws"] = 32
        (self.inputs / "settings.json").write_bytes(store.encoded(settings))
        shutil.copyfile(FIXTURES / "mmtt-package.json", self.inputs / "package.json")
        reader = csv.DictReader(io.StringIO((FIXTURES / "mmtt-observations.csv").read_text()))
        target = io.StringIO(newline="")
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            row["cpeptide_nmol_l"] = "0.2" if row["visit_id"] == "before" else "0.3"
            writer.writerow(row)
        (self.inputs / "observations.csv").write_text(target.getvalue())

    def freeze_plan(self, project, *, settings=None):
        paths = {
            name: self.inputs / name
            for name in ("package.json", "observations.csv", "settings.json")
        }
        if settings is not None:
            name = self.root / ("settings-" + str(len(project.plans)) + ".json")
            name.write_bytes(store.encoded(settings))
            paths["settings.json"] = name
        return routes.freeze(project, "mmtt-sensitivity", paths)

    def definition(self, plans):
        return {
            "schema": comparisons.SCHEMA,
            "name": "Constant-input contrasts",
            "question": "How do the declared volumes change the same synthetic endpoint?",
            "baseline": "baseline",
            "variants": [
                {
                    "id": "baseline" if i == 0 else "member-" + str(i),
                    "label": "Nominal" if i == 0 else "Control " + str(i),
                    "plan": plan,
                    "selector": {"variant": "nominal" if i == 0 else "volume-120"},
                }
                for i, plan in enumerate(plans)
            ],
        }

    def test_native_constant_oracle_fixed_attempts_old_prefix_and_relocation(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            frozen = comparisons.freeze(project, self.definition([plan, plan]))
            identity = frozen["comparison"]
            self.assertTrue(frozen["changes"][1]["fields"])
            changed = {row["path"]: row for row in frozen["changes"][1]["fields"]}
            self.assertEqual(changed["/selected_assumptions/volume_l"]["before"], 4.585)
            self.assertEqual(changed["/selected_assumptions/volume_l"]["after"], 5.502)
            self.assertIn(
                "experiments/mmtt_sampling/comparison.py",
                frozen["reader"]["reader_static_dependencies_sha256"],
            )
            first = execution.execute(project, plan)
            tip = project.head["tip"]
        with store.opened(self.project) as project:
            report = comparisons.reconstruct(project, identity, self.root / "first")
            value = store.read(self.root / "first/report.json")
            self.assertEqual(value["completeness"], "complete")
            self.assertEqual(value["coverage"]["planned_members"], 2)
            self.assertEqual(value["coverage"]["planned_cases"], 6)
            exposed = comparisons.view(project, identity)
            exposed["attempts"][plan]["report_sha256"]["report.json"] = "0" * 64
            self.assertEqual(
                comparisons.view(project, identity)["attempts"][plan]["report_sha256"],
                value["definition"]["attempts"][plan]["report_sha256"],
            )
            rows = value["members"][1]["rows"]
            for row in rows:
                c = (
                    100
                    if row["endpoint"] == "paired_change"
                    else 200
                    if "before" in row["endpoint"]
                    else 300
                )
                expected = 4.585 * 0.052 * c * 120
                self.assertAlmostEqual(row["reference_value"], expected, delta=1e-8)
                self.assertAlmostEqual(row["difference"], expected * 0.2, delta=1e-8)
                self.assertEqual(row["unit"], "pmol")
        with store.opened(self.project, write_access=True) as project:
            second = execution.execute(project, plan, retry_of=first)
            self.assertNotEqual(first, second)
            moved = project.relocate(self.root / "moved")
        shutil.rmtree(self.project)
        shutil.rmtree(self.inputs)
        with (
            store.opened(moved) as project,
            patch.object(execution, "execute", side_effect=AssertionError("No model run")),
        ):
            restored = comparisons.reconstruct(project, identity, self.root / "restored", at=tip)
            self.assertEqual(restored["report_sha256"], report["report_sha256"])
            self.assertEqual(
                comparisons.view(project, identity)["attempts"][plan]["attempt"], first
            )

    def test_failed_and_unattempted_members_never_disappear_or_select_later_retry(self):
        with store.opened(self.project, write_access=True) as project:
            plans = [self.freeze_plan(project) for _ in range(3)]
            frozen = comparisons.freeze(project, self.definition(plans))
            first = execution.execute(project, plans[0])
            with patch.object(
                execution, "check", side_effect=ValueError("Controlled admission refusal")
            ):
                failed = execution.execute(project, plans[1])
            tip = project.head["tip"]
        with store.opened(self.project) as project:
            before = comparisons.reconstruct(project, frozen["comparison"], self.root / "before")
            value = store.read(self.root / "before/report.json")
            self.assertEqual(
                [m["attempt"]["status"] for m in value["members"]],
                ["completed", "failed", "unattempted"],
            )
            self.assertEqual(value["coverage"]["planned_cases"], 9)
            self.assertEqual(value["coverage"]["unavailable_contrasts"], 6)
        with store.opened(self.project, write_access=True) as project:
            execution.execute(project, plans[1], retry_of=failed)
            execution.execute(project, plans[2])
        with store.opened(self.project) as project:
            after = comparisons.reconstruct(
                project, frozen["comparison"], self.root / "after", at=tip
            )
            self.assertEqual(before["report_sha256"], after["report_sha256"])
            current = comparisons.view(project, frozen["comparison"])
            self.assertEqual(current["attempts"][plans[1]]["attempt"], failed)
            self.assertEqual(current["attempts"][plans[0]]["attempt"], first)

    def test_view_mutation_cannot_change_frozen_snapshot(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            identity = comparisons.freeze(project, self.definition([plan, plan]))["comparison"]
            tip = project.head["tip"]
        with store.opened(self.project) as project:
            before = comparisons.reconstruct(project, identity, self.root / "before", at=tip)
            original = copy.deepcopy(comparisons.view(project, identity, at=tip))
            exposed = comparisons.view(project, identity, at=tip)
            exposed["variants"][1]["selector"]["variant"] = "nominal"
            exposed["changes"][1]["fields"].clear()
            exposed["support"]["participants"][0]["allocation"] = "changed"
            exposed["reader"]["schema"] = "changed"
            self.assertEqual(comparisons.view(project, identity, at=tip), original)
            after = comparisons.reconstruct(project, identity, self.root / "after", at=tip)
            self.assertEqual(before["report_sha256"], after["report_sha256"])

    def test_first_import_cannot_satisfy_prospective_comparison(self):
        with store.opened(self.project, write_access=True) as project:
            historical = self.freeze_plan(project)
            old_attempt = execution.execute(project, historical)
            archive = project.finishes[old_attempt][1] / "native"
            plan = self.freeze_plan(project)
            identity = comparisons.freeze(project, self.definition([plan, plan]))["comparison"]
            original = {
                path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in self.project.rglob("*")
                if path.is_file()
            }
            for attempt in (
                lambda: execution.begin(project, plan, mode="import"),
                lambda: routes.import_attempt(project, plan, archive),
            ):
                with self.assertRaisesRegex(ValueError, "executed first attempt"):
                    attempt()
                self.assertEqual(
                    {
                        path.relative_to(self.project).as_posix(): path.read_bytes()
                        for path in self.project.rglob("*")
                        if path.is_file()
                    },
                    original,
                )
                self.assertFalse(any((self.project / "pending").iterdir()))
                self.assertFalse(any((self.project / "work").iterdir()))
            unrelated = self.freeze_plan(project)
            imported = routes.import_attempt(project, unrelated, archive)
            self.assertEqual(project.attempts[imported]["mode"], "import")
            first = execution.execute(project, plan)
            later = routes.import_attempt(project, plan, archive, retry_of=first)
            self.assertEqual(project.attempts[later]["mode"], "import")
            self.assertEqual(
                comparisons.view(project, identity)["attempts"][plan]["attempt"], first
            )

    def test_replay_refuses_imported_first_attempt_after_comparison(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            comparisons.freeze(project, self.definition([plan, plan]))
            project.append(
                "start",
                {
                    "plan": plan,
                    "ordinal": 1,
                    "retry_of": None,
                    "mode": "import",
                    "host": {"controlled": "precomputed archive intake"},
                },
            )
        with self.assertRaisesRegex(ValueError, "executed first attempt"):
            with store.opened(self.project):
                pass

    def test_roster_prior_execution_duplicates_support_and_prefix_refusals(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            request = self.definition([plan, plan])
            for field, value in (("baseline", "unknown"), ("schema", "unknown")):
                with self.assertRaises(ValueError):
                    comparisons.freeze(project, {**request, field: value})
            duplicate = copy.deepcopy(request)
            duplicate["variants"][1]["selector"] = {"variant": "nominal"}
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                comparisons.freeze(project, duplicate)
            settings = store.read(self.inputs / "settings.json")
            settings["visit_order"].reverse()
            reversed_plan = self.freeze_plan(project, settings=settings)
            with self.assertRaisesRegex(ValueError, "support"):
                comparisons.freeze(project, self.definition([plan, reversed_plan]))
            earlier = project.head["tip"]
            frozen = comparisons.freeze(project, request)
            with self.assertRaisesRegex(ValueError, "predates"):
                comparisons.view(project, frozen["comparison"], at=earlier)
            execution.execute(project, plan)
            with self.assertRaisesRegex(ValueError, "precede execution"):
                comparisons.freeze(project, request)

    def test_expired_service_objects_refuse_comparison_reads(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            request = self.definition([plan, plan])
            frozen = comparisons.freeze(project, request)
        for read in (
            lambda: tasks.plan_data(project, plan),
            lambda: comparisons.definition(project, request),
            lambda: comparisons.view(project, frozen["comparison"]),
            lambda: comparisons.prefix(project, None),
        ):
            with self.assertRaisesRegex(ValueError, "active project lease"):
                read()

    def test_prefix_before_finish_does_not_consume_later_evidence(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            frozen = comparisons.freeze(project, self.definition([plan, plan]))
            attempt, _ = execution.begin(project, plan)
            tip = project.head["tip"]
            execution.recover(project, attempt, execution_stopped=True)
        with (
            store.opened(self.project) as project,
            patch.object(
                execution,
                "reconstruct",
                side_effect=AssertionError("Future evidence must not be read"),
            ),
        ):
            value = comparisons.view(project, frozen["comparison"], at=tip)
            self.assertEqual(value["attempts"][plan]["status"], "unfinished")
            comparisons.reconstruct(project, frozen["comparison"], self.root / "unfinished", at=tip)
            report = store.read(self.root / "unfinished/report.json")
            self.assertEqual(report["coverage"]["planned_cases"], 6)
            self.assertEqual(report["coverage"]["compared_cases"], 0)

    def test_changed_comparison_helper_identity_refuses_without_modifying_project(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze_plan(project)
            comparisons.freeze(project, self.definition([plan, plan]))
        head = (self.project / "HEAD.json").read_bytes()
        reader = comparisons.reader()
        reader["reader_static_dependencies_sha256"]["experiments/mmtt_sampling/comparison.py"] = (
            "0" * 64
        )
        with patch.object(comparisons, "reader", return_value=reader):
            with self.assertRaisesRegex(ValueError, "comparison/source"):
                with store.opened(self.project):
                    pass
        self.assertEqual((self.project / "HEAD.json").read_bytes(), head)

    def test_incomplete_uncertainty_retains_points_without_interval_or_direction(self):
        folder = self.root / "native-table"
        folder.mkdir()
        value = {
            "status": "incomplete",
            "point": {
                "status": "completed",
                "visits": {
                    "before": {"status": "completed", "estimate": {"total_pmol": 10}},
                    "after": {"status": "completed", "estimate": {"total_pmol": 12}},
                },
            },
            "paired_change_pmol": 2,
            "direction": "increase",
        }
        (folder / "report.json").write_bytes(
            store.encoded(
                {"people": {"invented": {"variants": {"nominal": value}}}, "import_errors": []}
            )
        )
        info = {
            "task": "mmtt-sensitivity",
            "support": {
                "participants": [{"id": "invented", "allocation": "evaluation"}],
                "visit_order": ["before", "after"],
            },
        }
        rows = tasks.mmtt_rows(info, {"selector": {"variant": "nominal"}}, folder, None)
        self.assertEqual([row["value"] for row in rows], [10, 12, 2])
        self.assertTrue(
            all(
                row["interval"] is None
                and row["direction"] is None
                and row["status"] == "incomplete"
                for row in rows
            )
        )

    def test_m4_native_contrast_oracle_complete_grid_and_failed_source(self):
        curve = {
            "times": [i / 4 for i in range(961)],
            "glucose": [2.0] * 961,
            "insulin": [3.0] * 961,
            "cpeptide": [4.0] * 961,
        }
        base = {**curve, "glucose": [1.0] * 961, "insulin": [1.0] * 961, "cpeptide": [1.0] * 961}
        rows = tasks.m4_rows(curve, base, None)
        for row, difference in zip(rows, (1, 2, 3), strict=True):
            self.assertEqual(row["metrics"]["signed_auc_difference"], difference * 240)
            self.assertEqual(row["metrics"]["signed_time_mean_difference"], difference)
            self.assertEqual(row["metrics"]["maximum_absolute_pointwise_difference"], difference)
        with self.assertRaisesRegex(ValueError, "grid mismatch"):
            tasks.m4_rows({**curve, "times": curve["times"][:-1]}, base, None)
        self.assertTrue(all(row["metrics"] is None for row in tasks.m4_rows(None, base, "failed")))


if __name__ == "__main__":
    unittest.main()
