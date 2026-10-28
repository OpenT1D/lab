"""Native-shaped OT-027 join rehearsal keeps source clocks and gaps distinct."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from experiments.m5.native_rehearsal.fixture import generate
from experiments.m5.native_rehearsal.run import HERE, execute


def change_row(path, edit):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    edit(rows)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class M5NativeRehearsalTests(unittest.TestCase):
    def test_mean_start_is_not_treated_as_visit_day_and_repeat_is_retained(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            generate(source)
            report = execute(HERE / "intent-synthetic.json", source, Path(root) / "report.json")
            self.assertEqual(report["roster_count"], 3)
            self.assertEqual(report["candidate_structure_count"], 2)
            self.assertEqual(report["people"][0]["candidate_mean_interval"], [359, 365])
            self.assertEqual(
                report["people"][1]["intervening_infusions_before_interval_end"], [150]
            )
            self.assertEqual(report["people"][2]["issues"], ["daily_insulin_interval_unverified"])
            self.assertFalse(report["one_year_visit_linkage_verified"])
            self.assertFalse(report["human_execution_authorized"])

    def test_missing_daily_value_and_ambiguous_mean_are_accounted(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            generate(source)
            change_row(source / "insulin.csv", lambda rows: rows[0].update(Insulin=""))
            report = execute(HERE / "intent-synthetic.json", source, Path(root) / "missing.json")
            self.assertIn("daily_insulin_value_missing", report["people"][0]["issues"])
            change_row(source / "mean_insulin.csv", lambda rows: rows.append(dict(rows[0])))
            report = execute(HERE / "intent-synthetic.json", source, Path(root) / "ambiguous.json")
            self.assertIn("missing_or_ambiguous_one_year_interval", report["people"][0]["issues"])

    def test_inconsistent_transplant_order_is_visible(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            generate(source)
            change_row(
                source / "ieq_infused.csv",
                lambda rows: rows.pop(next(i for i, row in enumerate(rows) if row["TX"] == "2")),
            )
            report = execute(HERE / "intent-synthetic.json", source, Path(root) / "report.json")
            self.assertIn("ieq_transplant_orders_inconsistent", report["people"][1]["issues"])

    def test_human_intent_is_rejected_before_opening_csvs(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "intent.json"
            intent = json.loads((HERE / "intent-synthetic.json").read_text())
            intent["kind"] = "human"
            path.write_text(json.dumps(intent))
            with self.assertRaisesRegex(ValueError, "Only invented synthetic"):
                execute(path, Path(root) / "absent", Path(root) / "report.json")
            self.assertFalse((Path(root) / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
