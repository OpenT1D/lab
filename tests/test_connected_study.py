"""Connected ledger/bridge controls with independent forward math, real MMTT.

The forward boundary is a labelled controlled stand-in, not M4 qualification.
Downstream full/reduced inverse analysis and its trusted reader run unchanged.
"""

import copy
import csv
import io
import math
import os
import shutil
import tempfile
import unittest
from decimal import ROUND_UP, Decimal, Inexact, Rounded, localcontext
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import seal
from experiments.shared_services import (
    connected,
    connected_bridge,
    execution,
    installed,
    routes,
    sampling,
    store,
)
from tests.connected_fixtures import (
    SLOPES,
    affine_state,
    controlled_forward,
    finish_forward,
    forward_archive,
)


@unittest.skipUnless(os.name == "posix", "Connected project services require POSIX leases")
class ConnectedStudy(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="connected-study-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.enterContext(controlled_forward())
        self.path = store.create(self.root / "project", "Controlled connected source")
        self.inputs = installed.example("m4-study-installed", self.root / "inputs", "fasting")[
            "inputs"
        ]
        config = Path(self.inputs["config.json"])
        value = store.read(config)
        value["scenarios"] = ["fasting", "gastric_load_15g"]
        config.write_bytes(store.encoded(value))
        with store.opened(self.path, write_access=True) as project:
            self.forward = routes.freeze(project, "m4-study-installed", self.inputs)
            self.study = connected.freeze(project, self.request())["study"]
            self.initial_tip = project.head["tip"]

    def request(self, *, observation_case="complete"):
        return {
            "name": "Known affine inputs",
            "question": "Does the frozen inverse recover known source amounts?",
            "forward_plan": self.forward,
            "observation_case": observation_case,
        }

    def finished_forward(self, project):
        attempt = finish_forward(project, self.forward)
        self.assertEqual(connected.view(project, self.study)["next"]["action"], "materialize")
        return attempt

    def report(self, identity=None, *, at=None, name="report", path=None):
        target = self.root / name
        with store.opened(path or self.path) as project:
            result = connected.reconstruct(project, identity or self.study, target, at=at)
        return result, store.read(target / "report.json")

    def test_unattempted_denominator_detached_views_and_expired_leases(self):
        before, report = self.report()
        self.assertEqual(report["coverage"]["planned_rows"], 72)
        self.assertEqual(report["coverage"]["unavailable_point_rows"], 72)
        self.assertEqual(report["point_recovery"], {"all_passed": False, "passed": 0, "planned": 6})
        self.assertTrue(all(row["known_pmol"] is None for row in report["rows"]))
        with store.opened(self.path) as project:
            expected = copy.deepcopy(connected.view(project, self.study))
            exposed = connected.view(project, self.study)
            exposed["protocol"]["kinetics"]["k3"] = 999
            exposed["stages"]["forward"]["status"] = "completed"
            self.assertEqual(connected.view(project, self.study), expected)
            after = connected.reconstruct(project, self.study, self.root / "again")
        self.assertEqual(before["report_sha256"], after["report_sha256"])
        with self.assertRaisesRegex(ValueError, "active project lease"):
            connected.view(project, self.study)

    def test_independent_affine_oracle_exact_window_units_and_weight_scaling(self):
        archive = forward_archive(self.root / "affine")
        definition = {"protocol": connected.protocol(), "observation_case": "complete"}
        files = connected_bridge.generated(definition, archive)
        bridge = store.decode(files["bridge.json"])
        for case, source in definition["protocol"]["case_sources"].items():
            for visit, scene in (("before", "fasting"), ("after", "gastric_load_15g")):
                slope = Decimal(str(SLOPES[source][scene]))
                expected = Decimal(70) * (120 + slope * 120**2 / 2)
                whole = Decimal(70) * (240 + slope * 240**2 / 2)
                truth = bridge["truth"][case][visit]
                self.assertAlmostEqual(truth["known_total_pmol"], float(expected), delta=1e-8)
                self.assertAlmostEqual(truth["parent_240min_total_pmol"], float(whole), delta=1e-8)
                self.assertAlmostEqual(
                    truth["cpeptide_auc_nmol_min_l"] * 1000,
                    truth["cpeptide_auc_pmol_min_l"],
                    delta=1e-8,
                )
                if slope:
                    self.assertNotEqual(
                        truth["known_total_pmol"], truth["parent_240min_total_pmol"] / 2
                    )
            self.assertAlmostEqual(bridge["truth"][case]["paired_change_pmol"], 5040, delta=1e-8)
        rows = list(csv.DictReader(io.StringIO(files["observations.csv"].decode())))
        self.assertEqual(len(rows), 2 * 2 * 481)
        self.assertEqual({float(row["time_min"]) for row in rows}, {i / 4 for i in range(481)})
        self.assertAlmostEqual(float(rows[0]["glucose_mmol_l"]), 5.5)
        self.assertAlmostEqual(
            float(rows[0]["cpeptide_nmol_l"]), affine_state(0, 0)[0] / 0.0655 / 1000
        )
        doubled = forward_archive(self.root / "double-weight", weight=140)
        double_files = connected_bridge.generated(definition, doubled)
        double_bridge = store.decode(double_files["bridge.json"])
        self.assertEqual(files["observations.csv"], double_files["observations.csv"])
        self.assertEqual(double_bridge["whole_body_volume_l"], bridge["whole_body_volume_l"] * 2)
        self.assertEqual(
            double_bridge["truth"]["synthetic-dalla-man"]["after"]["known_total_pmol"],
            bridge["truth"]["synthetic-dalla-man"]["after"]["known_total_pmol"] * 2,
        )

    def test_bridge_refuses_wrong_inlet_grid_kinetics_and_profile(self):
        archive = forward_archive(self.root / "control")
        definition = {"protocol": connected.protocol(), "observation_case": "complete"}
        mutations = {
            "inlet": (
                "children/dalla_man/observations/primary/cases/fasting--candidate.json",
                lambda value: value["boundary"].update(signal="liver_fault"),
            ),
            "units": (
                "children/dalla_man/observations/primary/cases/fasting--candidate.json",
                lambda value: value["boundary"]["forcing"].update(units="pmol/min"),
            ),
            "grid": (
                "children/dalla_man/primary/fasting/candidate-reference.json",
                lambda value: value["times"].pop(),
            ),
            "kinetics": (
                "children/dalla_man/observations/primary/cases/fasting--candidate.json",
                lambda value: value["boundary"]["parameters"].update(k3=0.1),
            ),
            "weight": (
                "children/ultradian/primary/native.json",
                lambda value: value["parameters"].update(BW=140),
            ),
            "initial": (
                "children/dalla_man/observations/primary/cases/fasting--candidate.json",
                lambda value: value["boundary"]["initial"].__setitem__(1, 0),
            ),
        }
        for case, (name, mutate) in mutations.items():
            with self.subTest(case=case):
                target = self.root / case
                shutil.copytree(archive, target)
                file = target / name
                value = store.read(file)
                mutate(value)
                file.write_bytes(store.encoded(value))
                with self.assertRaises(ValueError):
                    connected_bridge.generated(definition, target)

    def test_bridge_bytes_ignore_ambient_decimal_precision_rounding_and_traps(self):
        archive = forward_archive(self.root / "decimal-control")
        definition = {"protocol": connected.protocol(), "observation_case": "complete"}
        expected = connected_bridge.generated(definition, archive)
        with localcontext() as ambient:
            ambient.prec = 6
            ambient.rounding = ROUND_UP
            ambient.traps[Inexact] = True
            ambient.traps[Rounded] = True
            self.assertEqual(connected_bridge.generated(definition, archive), expected)
            self.assertEqual(
                connected_bridge.decimal_area(
                    [0, 0.5, 1], [0.1234567891, 1.1234567891, 2.1234567891]
                ),
                Decimal("1.1234567891"),
            )

    def test_actual_inverse_full_reduced_retries_prefix_replay_and_relocation(self):
        original, _ = self.report(name="unattempted")
        with store.opened(self.path, write_access=True) as project:
            first = self.finished_forward(project)
            materialized = connected.materialize(project, self.study)
            child = materialized["sampling_plan"]
            self.assertEqual(project.plans[child][0]["task"], "mmtt-sampling")
            self.assertEqual(project.events[-1][1]["kind"], "study-bridge")
            second = execution.execute(project, child, timeout=120)
            tip = project.head["tip"]
            native = project.finishes[second][1] / "native/studies"
            stored_points = {}
            for schedule in ("full", "one-minute", "fifteen-minute"):
                saved = store.read(native / schedule / "report.json")
                for case, person in saved["people"].items():
                    for variant, data in person["variants"].items():
                        for visit in ("before", "after"):
                            stored_points[(schedule, case, variant, "visit_total:" + visit)] = data[
                                "point"
                            ]["visits"][visit]["estimate"]["total_pmol"]
                        stored_points[(schedule, case, variant, "paired_change")] = data[
                            "paired_change_pmol"
                        ]
        current, report = self.report(name="complete")
        self.assertEqual(report["coverage"]["planned_rows"], 72)
        self.assertEqual(report["coverage"]["planned_native_variant_pairs"], 24)
        self.assertEqual(report["coverage"]["available_point_rows"], 72)
        self.assertEqual(report["coverage"]["complete_rows"], 72)
        self.assertEqual(report["point_recovery"], {"all_passed": True, "passed": 6, "planned": 6})
        self.assertEqual(
            report["mismatch_controls"], {"all_passed": True, "passed": 18, "planned": 18}
        )
        for row in report["rows"]:
            self.assertEqual(row["unit"], "pmol")
            self.assertEqual(row["status"], "complete")
            self.assertEqual(len(row["interval"]), 2)
            self.assertLess(row["interval"][0], row["interval"][1])
            self.assertEqual(
                row["value"],
                stored_points[(row["schedule"], row["case"], row["variant"], row["endpoint"])],
            )
            if row["schedule"] == "full" and row["variant"] == "nominal":
                self.assertLessEqual(
                    abs(row["difference_from_known_pmol"]), 1e-4 * max(1, abs(row["known_pmol"]))
                )
        nominal = {
            (row["case"], row["endpoint"]): row["value"]
            for row in report["rows"]
            if row["schedule"] == "full" and row["variant"] == "nominal"
        }
        for row in report["rows"]:
            if row["schedule"] != "full" or row["variant"] == "nominal":
                continue
            base = nominal[(row["case"], row["endpoint"])]
            source = {
                "synthetic-dalla-man": "dalla_man",
                "synthetic-ultradian": "ultradian",
            }[row["case"]]

            def offset(visit):
                if row["variant"] == "peripheral-075":
                    return 0.25 * 0.037 / 0.031 * 70 / 0.052 * -math.expm1(-0.031 * 120)
                slope = SLOPES[source]["fasting" if visit == "before" else "gastric_load_15g"]
                cp = [affine_state(i / 4, slope)[0] / 0.0655 for i in range(481)]
                area = math.fsum((a + b) / 8 for a, b in zip(cp[:-1], cp[1:], strict=True))
                return 0.2 * 0.052 * (70 * 0.0655) * area

            expected = (
                base * 0.2
                if row["variant"] == "volume-120"
                else offset("after") - offset("before")
                if row["endpoint"] == "paired_change"
                else offset(row["endpoint"].split(":", 1)[1])
            )
            self.assertAlmostEqual(row["value"] - base, expected, delta=1e-8 * max(1, abs(base)))
        with store.opened(self.path, write_access=True) as project:
            before = {
                name: len(getattr(project, name))
                for name in ("plans", "comparisons", "study_intents")
            }
            reused = connected.materialize(project, self.study)
            self.assertTrue(reused["reused"])
            self.assertEqual(before, {name: len(getattr(project, name)) for name in before})
            execution.execute(project, child, retry_of=second, timeout=120)
            view = connected.view(project, self.study)
            self.assertEqual(view["stages"]["forward"]["attempt"], first)
            self.assertEqual(view["stages"]["inverse_sampling"]["attempt"], second)
            moved = project.relocate(self.root / "moved")
        self.path.rename(self.root / "original-unavailable")
        shutil.rmtree(self.root / "inputs")
        replay, _ = self.report(at=tip, path=moved, name="replay")
        self.assertEqual(current["report_sha256"], replay["report_sha256"])
        with patch.object(
            execution, "reconstruct", side_effect=AssertionError("No future evidence")
        ):
            earliest, early_report = self.report(at=self.initial_tip, path=moved, name="earliest")
        self.assertEqual(original["report_sha256"], earliest["report_sha256"])
        self.assertEqual(early_report["coverage"]["unavailable_point_rows"], 72)

    def test_missing_evaluation_preserves_development_seal_and_native_failures(self):
        with store.opened(self.path, write_access=True) as project:
            missing = connected.freeze(
                project, self.request(observation_case="missing-evaluation")
            )["study"]
            self.finished_forward(project)
            normal = connected.materialize(project, self.study)
            failed = connected.materialize(project, missing)
            regular_input = project.plans[normal["sampling_plan"]][1] / "original"
            missing_input = project.plans[failed["sampling_plan"]][1] / "original"
            self.assertEqual(
                sampling.hashes(regular_input / "development"),
                sampling.hashes(missing_input / "development"),
            )
            rows = list(
                csv.DictReader(io.StringIO((missing_input / "observations.csv").read_text()))
            )
            missing_rows = [row for row in rows if row["cpeptide_status"] == "missing"]
            self.assertEqual(len(rows), 2 * 2 * 481)
            self.assertEqual(len(missing_rows), 1)
            self.assertEqual(
                (
                    missing_rows[0]["participant_id"],
                    missing_rows[0]["visit_id"],
                    float(missing_rows[0]["time_min"]),
                ),
                ("synthetic-ultradian", "after", 60),
            )
            self.assertEqual(missing_rows[0]["cpeptide_nmol_l"], "")
            execution.execute(project, failed["sampling_plan"], timeout=120)
        _, report = self.report(missing, name="missing")
        self.assertEqual(report["completeness"], "incomplete")
        self.assertFalse(report["point_recovery"]["all_passed"])
        self.assertEqual(report["coverage"]["planned_rows"], 72)
        self.assertEqual(report["coverage"]["available_point_rows"], 48)
        self.assertEqual(report["coverage"]["complete_rows"], 36)
        for row in report["rows"]:
            if row["case"] == "synthetic-dalla-man":
                self.assertEqual(row["status"], "complete")
            elif row["endpoint"] == "visit_total:before":
                self.assertIsNotNone(row["value"])
                self.assertIsNone(row["interval"])
                self.assertEqual(row["status"], "incomplete")
            if row["case"] == "synthetic-ultradian" and row["endpoint"] in (
                "visit_total:after",
                "paired_change",
            ):
                self.assertIsNone(row["value"])
                self.assertIsNone(row["difference_from_known_pmol"])
                self.assertNotEqual(row["status"], "complete")

    def test_interrupted_materialization_reuses_owned_plan_and_comparison(self):
        with store.opened(self.path, write_access=True) as project:
            self.finished_forward(project)
            append = project.append

            def stop_before_comparison(kind, data, populate=None):
                if kind == "comparison":
                    raise RuntimeError("Controlled publication interruption")
                return append(kind, data, populate)

            with patch.object(project, "append", side_effect=stop_before_comparison):
                with self.assertRaisesRegex(RuntimeError, "publication interruption"):
                    connected.materialize(project, self.study)
            partial = connected.view(project, self.study)
            child = partial["sampling_plan"]
            self.assertIsNotNone(child)
            self.assertIsNone(partial["comparison"])
            with self.assertRaisesRegex(ValueError, "Complete connected materialization"):
                execution.begin(project, child)
            intent = partial["intent"]
            with self.assertRaises(ValueError):
                connected.validate_bridge(
                    project,
                    {
                        "study": self.study,
                        "intent": intent,
                        "sampling_plan": child,
                        "comparison": None,
                    },
                )
        premature = self.root / "bridge-before-comparison"
        shutil.copytree(self.path, premature)
        with store.opened(premature, write_access=True) as project:
            project.append(
                "study-bridge",
                {
                    "study": self.study,
                    "intent": intent,
                    "sampling_plan": child,
                    "comparison": None,
                },
            )
        with self.assertRaises(ValueError):
            with store.opened(premature):
                pass
        with store.opened(self.path, write_access=True) as project:
            append = project.append

            def stop_before_bridge(kind, data, populate=None):
                if kind == "study-bridge":
                    raise RuntimeError("Controlled final publication interruption")
                return append(kind, data, populate)

            with patch.object(project, "append", side_effect=stop_before_bridge):
                with self.assertRaisesRegex(RuntimeError, "final publication interruption"):
                    connected.materialize(project, self.study)
            comparison = project.study_comparisons[intent]
        with store.opened(self.path, write_access=True) as project:
            complete = connected.materialize(project, self.study)
            self.assertEqual(complete["sampling_plan"], child)
            self.assertEqual(complete["comparison"], comparison)
            self.assertEqual(len(project.plans), 2)
            self.assertEqual(len(project.comparisons), 1)
            self.assertEqual(len(project.study_intents), 1)
            before = (self.path / "HEAD.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "executed first attempt"):
                execution.begin(project, child, mode="import")
            self.assertEqual((self.path / "HEAD.json").read_bytes(), before)

    def test_child_development_evidence_tamper_refuses(self):
        with store.opened(self.path, write_access=True) as project:
            self.finished_forward(project)
            child = connected.materialize(project, self.study)["sampling_plan"]
            frozen = project.plans[child][1]
            descriptor = store.read(frozen / "descriptor.json")
            target = self.root / "tampered-child"
            shutil.copytree(frozen, target)
        evidence = target / "original/development/observations.csv"
        evidence.write_bytes(evidence.read_bytes().replace(b"observed", b"missing", 1))
        with self.assertRaisesRegex(ValueError, "Sampling originals differ"):
            sampling.validate_freeze(target, descriptor, current=True)

    def test_intent_only_prefix_counts_all_rows_and_null_bridge_replay_refuses(self):
        with store.opened(self.path, write_access=True) as project:
            self.finished_forward(project)
            with patch.object(routes, "freeze", side_effect=RuntimeError("Before child")):
                with self.assertRaisesRegex(RuntimeError, "Before child"):
                    connected.materialize(project, self.study)
            partial = connected.view(project, self.study)
            tip = project.head["tip"]
            self.assertIsNotNone(partial["intent"])
            self.assertIsNone(partial["sampling_plan"])
        _, report = self.report(at=tip, name="intent-only")
        self.assertEqual(report["coverage"]["planned_rows"], 72)
        self.assertEqual(report["coverage"]["unavailable_point_rows"], 72)
        self.assertTrue(all(row["known_pmol"] is not None for row in report["rows"]))
        invalid = {
            "study": self.study,
            "intent": partial["intent"],
            "sampling_plan": None,
            "comparison": None,
        }
        with store.opened(self.path, write_access=True) as project:
            with self.assertRaises(ValueError):
                connected.validate_bridge(project, invalid)
            project.append("study-bridge", invalid)
        with self.assertRaises(ValueError):
            with store.opened(self.path):
                pass

    def test_failed_first_forward_and_unfinished_prefix_never_promote_later_retry(self):
        with store.opened(self.path, write_access=True) as project:
            first, _ = execution.begin(project, self.forward)
            unfinished = project.head["tip"]
            execution.recover(project, first, execution_stopped=True)
            finish_forward(project, self.forward, retry_of=first)
            view = connected.view(project, self.study)
            self.assertEqual(view["stages"]["forward"]["attempt"], first)
            self.assertEqual(view["next"]["action"], "blocked")
            with self.assertRaisesRegex(ValueError, "first forward attempt incomplete"):
                connected.materialize(project, self.study)
        with patch.object(
            execution, "reconstruct", side_effect=AssertionError("No later native result")
        ):
            _, report = self.report(at=unfinished, name="unfinished")
        self.assertEqual(report["definition"]["stages"]["forward"]["status"], "unfinished")
        self.assertEqual(report["coverage"]["unavailable_point_rows"], 72)

    def test_forward_import_refuses_before_mutation_and_during_replay(self):
        prior_archive = forward_archive(self.root / "prior-archive")
        with store.opened(self.path, write_access=True) as project:
            before = (self.path / "HEAD.json").read_bytes()
            for action in (
                lambda: execution.begin(project, self.forward, mode="import"),
                lambda: routes.import_attempt(project, self.forward, prior_archive),
            ):
                with self.assertRaisesRegex(ValueError, "executed first attempt"):
                    action()
                self.assertEqual((self.path / "HEAD.json").read_bytes(), before)
                self.assertFalse(any((self.path / "work").iterdir()))
            project.append(
                "start",
                {
                    "plan": self.forward,
                    "ordinal": 1,
                    "retry_of": None,
                    "mode": "import",
                    "host": {"controlled": "old evidence"},
                },
            )
        with self.assertRaisesRegex(ValueError, "executed first attempt"):
            with store.opened(self.path):
                pass

    def test_resealed_generated_observation_does_not_detach_from_forward_truth(self):
        with store.opened(self.path, write_access=True) as project:
            self.finished_forward(project)
            with patch.object(routes, "freeze", side_effect=RuntimeError("Stop before child")):
                with self.assertRaisesRegex(RuntimeError, "Stop before child"):
                    connected.materialize(project, self.study)
            intent, data, folder = project.study_intents[self.study]
            self.assertEqual(project.head["tip"], intent)
        for name in ("observations.csv", "development/observations.csv"):
            with self.subTest(name=name):
                copied = self.root / ("resealed-development" if "/" in name else "resealed-raw")
                shutil.copytree(self.path, copied)
                event_folder = copied / folder.relative_to(self.path)
                bridge = event_folder / "bridge"
                raw = (bridge / name).read_bytes()
                rows = list(csv.DictReader(io.StringIO(raw.decode())))
                rows[0]["cpeptide_nmol_l"] = str(float(rows[0]["cpeptide_nmol_l"]) + 0.01)
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
                (bridge / name).write_text(stream.getvalue())
                if "/" in name:
                    (bridge / "development/manifest.json").unlink()
                    seal(bridge / "development")
                (bridge / "manifest.json").unlink()
                seal(bridge)
                event = store.read(event_folder / "event.json")
                event["data"]["artifacts_sha256"] = sampling.hashes(bridge)
                (event_folder / "event.json").write_bytes(store.encoded(event))
                (event_folder / "manifest.json").unlink()
                seal(event_folder)
                head = store.read(copied / "HEAD.json")
                head["tip"] = store.digest((event_folder / "manifest.json").read_bytes())
                (copied / "HEAD.json").write_bytes(store.encoded(head))
                with self.assertRaisesRegex(ValueError, "conversion bytes differ"):
                    with store.opened(copied):
                        pass
        with store.opened(self.path) as project:
            self.assertEqual(project.head["tip"], intent)

    def test_changed_reader_refuses_without_rewriting_study(self):
        before = (self.path / "HEAD.json").read_bytes()
        reader = connected.reader()
        reader["protocol_sha256"] = "0" * 64
        with patch.object(connected, "reader", return_value=reader):
            with self.assertRaisesRegex(ValueError, "Study/source identity"):
                with store.opened(self.path):
                    pass
        self.assertEqual((self.path / "HEAD.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
