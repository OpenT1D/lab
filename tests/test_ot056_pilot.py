"""Invented bookkeeping fixtures, never researcher observations."""

import csv
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.ot056_pilot import (
    CATEGORIES,
    FIELDS,
    GATES,
    SLOTS,
    TASKS,
    TOOLS,
    initialize,
    meets_targets,
    schedule,
    summarize,
)


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "packet"
        initialize(self.root)

    def write(self, name, rows):
        with (self.root / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS[name])
            writer.writeheader()
            writer.writerows(rows)

    def prepared_fixture(self):
        """Exercise arithmetic with invented rows; keep technical evidence label."""
        plan = json.loads((self.root / "plan.json").read_text())
        plan.update(status="frozen", evidence_kind="technical_rehearsal")
        plan["primary_comparator"] = dict.fromkeys(TASKS, "notebook")
        plan["gates"] = dict.fromkeys(GATES, "invented-test-reference")
        (self.root / "plan.json").write_text(json.dumps(plan))
        self.write(
            "roster",
            [
                dict(
                    researcher=slot,
                    team=f"test-team-{i % 2}",
                    experience_ref="invented",
                    participation_ref="invented",
                )
                for i, slot in enumerate(SLOTS)
            ],
        )
        sessions, reviews = [], []
        for allocation in schedule():
            identity = {k: allocation[k] for k in ("researcher", "task", "tool")}
            sessions.append(
                dict(
                    **identity,
                    case=allocation["case"],
                    status="complete",
                    active_seconds="70" if allocation["tool"] == "opent1d" else "100",
                    elapsed_seconds="120",
                    compute_seconds="20",
                    assistance_count="0",
                    report_sha256="a" * 64,
                    evidence_ref="invented-test-reference",
                )
            )
            reviews.append(
                dict(
                    **identity,
                    report_sha256="a" * 64,
                    correct_complete="yes",
                    critical_errors="0",
                    review_ref="invented-test-reference",
                )
            )
        self.write("sessions", sessions)
        self.write("reviews", reviews)
        self.write(
            "effort",
            [
                dict(
                    tool=tool,
                    category=category,
                    study=study,
                    person_seconds="0",
                    elapsed_seconds="0",
                    evidence_ref="invented",
                )
                for tool in TOOLS
                for category in CATEGORIES
                for study in ("first", "repeat")
            ],
        )
        return sessions, reviews

    def test_empty_packet_never_implies_success(self):
        result = summarize(self.root)
        self.assertEqual(result["status"], "not_evaluable")
        self.assertEqual(result["observed_cells"], 0)
        self.assertIsNone(result["product_decision"])
        self.assertEqual(len(result["input_sha256"]), 6)
        for comparison in result["comparisons"].values():
            self.assertIsNone(comparison["quantitative_gates_met"])
            self.assertIsNone(comparison["median_active_time_reduction"])
            self.assertIsNone(comparison["failure_penalized_median_reduction"])
            self.assertEqual(len(comparison["pairs"]), 6)

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            initialize(self.root)

    def test_malformed_plan_cannot_supply_readiness(self):
        plan = json.loads((self.root / "plan.json").read_text())
        plan["primary_comparator"] = []
        (self.root / "plan.json").write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "objects"):
            summarize(self.root)
        plan["primary_comparator"] = dict.fromkeys(TASKS, None)
        plan["gates"][GATES[0]] = True
        (self.root / "plan.json").write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "string"):
            summarize(self.root)

    def test_arithmetic_targets_require_both_time_gains_and_complete_pairs(self):
        # Pure numeric boundary checks; these are not human observations.
        self.assertTrue(meets_targets(5, 5, 5, 0.30, 0.30, 0, 0))
        for values in (
            (4, 6, 4, 0.5, 0.5, 0, 0),
            (6, 4, 4, 0.5, 0.5, 0, 0),
            (5, 5, 4, 0.5, 0.5, 0, 0),
            (6, 6, 6, 0.2999, 0.5, 0, 0),
            (6, 6, 6, 0.5, 0.2999, 0, 0),
            (6, 6, 6, None, 0.5, 0, 0),
            (6, 6, 6, 0.5, None, 0, 0),
            (5, 6, 5, 0.5, 0.5, 1, 0),
        ):
            with self.subTest(values=values):
                self.assertFalse(meets_targets(*values))

    def test_allocation_balances_order_cases_and_tools(self):
        rows = schedule()
        self.assertEqual(len(rows), 36)
        self.assertEqual(
            sum(r["block"] == 1 and r["period"] == 1 and r["task"] == "task1" for r in rows), 3
        )
        for task in TASKS:
            orders = [
                tuple(r["tool"] for r in rows if r["researcher"] == s and r["task"] == task)
                for s in SLOTS
            ]
            self.assertEqual(len(set(orders)), 6)
            for tool in TOOLS:
                counts = Counter(r["case"] for r in rows if r["task"] == task and r["tool"] == tool)
                self.assertEqual(sorted(counts.values()), [2, 2, 2])

    def test_hand_calculated_paired_reduction_and_technical_label(self):
        self.prepared_fixture()
        result = summarize(self.root)
        comparison = result["comparisons"]["task1/notebook"]
        self.assertEqual(comparison["paired_successes"], 6)
        self.assertAlmostEqual(comparison["median_active_time_reduction"], 0.3)
        self.assertEqual({p["difference_seconds"] for p in comparison["pairs"]}, {-30})
        self.assertEqual(comparison["paired_difference_seconds"]["median"], -30)
        self.assertEqual(result["status"], "not_evaluable")
        self.assertIsNone(comparison["quantitative_gates_met"])

    def test_incorrect_fast_reports_and_assistance_cannot_count(self):
        sessions, reviews = self.prepared_fixture()
        for row in sessions:
            if row["tool"] == "opent1d":
                row["active_seconds"] = "1"
                row["assistance_count"] = "1"
        self.write("sessions", sessions)
        result = summarize(self.root)["comparisons"]["task1/notebook"]
        self.assertEqual(result["paired_successes"], 0)
        self.assertIsNone(result["median_active_time_reduction"])
        self.assertLess(result["failure_penalized_median_reduction"], 0)
        for row in reviews:
            if row["tool"] == "opent1d":
                row.update(correct_complete="no", critical_errors="1")
        self.write("reviews", reviews)
        self.assertEqual(
            summarize(self.root)["comparisons"]["task1/notebook"]["critical_errors"]["opent1d"], 6
        )

    def test_timeout_retained_and_missing_cells_not_dropped(self):
        sessions, reviews = self.prepared_fixture()
        sessions[0].update(
            status="timeout", active_seconds="3600", elapsed_seconds="3700", report_sha256=""
        )
        reviews[0].update(report_sha256="", correct_complete="no")
        self.write("sessions", sessions[:-1])
        self.write("reviews", reviews[:-1])
        result = summarize(self.root)
        self.assertEqual(result["planned_cells"], 36)
        self.assertEqual(result["observed_cells"], 35)
        pair = result["comparisons"]["task1/notebook"]["pairs"][0]
        self.assertFalse(pair["opent1d_success"])
        self.assertEqual(pair["opent1d_scored_seconds"], 3600)

    def test_duplicate_wrong_case_review_hash_and_nonfinite_rejected(self):
        sessions, reviews = self.prepared_fixture()
        self.write("sessions", sessions + [sessions[0]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(self.root)
        sessions[0]["case"] = "wrong"
        self.write("sessions", sessions)
        with self.assertRaisesRegex(ValueError, "case"):
            summarize(self.root)
        sessions, reviews = self.prepared_fixture()
        reviews[0]["report_sha256"] = "b" * 64
        self.write("reviews", reviews)
        with self.assertRaisesRegex(ValueError, "bytes"):
            summarize(self.root)
        self.write("reviews", reviews[1:])
        sessions[0]["active_seconds"] = "nan"
        self.write("sessions", sessions)
        with self.assertRaisesRegex(ValueError, "finite"):
            summarize(self.root)


if __name__ == "__main__":
    unittest.main()
