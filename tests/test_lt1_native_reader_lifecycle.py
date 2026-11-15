"""C15 worker/footer lifecycle checks without importing a route or native engine.

The caller has already validated scientific journal rows in ``_session``. These
unit fixtures model only its footer/worker handoff, not complete scientific
journals, observed process histories or native results.
"""

import ast
import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace


def need(value, reason):
    if not value:
        raise ValueError(reason)


def fields(value, names):
    need(type(value) is dict and set(value) == set(names.split()), "exact fields")


class C15WorkerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (
            Path(__file__).absolute().parents[1]
            / "experiments/lt1_diagnostic/native_route_reader.py"
        )
        node = next(
            value
            for value in ast.parse(source.read_text()).body
            if isinstance(value, ast.FunctionDef) and value.name == "_worker_report"
        )
        context = {
            "route": SimpleNamespace(
                need=need,
                storage=SimpleNamespace(
                    fields=fields,
                    digest=lambda raw: hashlib.sha256(raw).hexdigest(),
                ),
            ),
            "reader": SimpleNamespace(decode=json.loads),
        }
        # Execute only this trusted function definition, never module imports.
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), context)
        cls.inspect_worker = staticmethod(context["_worker_report"])

    def fixture(self, *, completed=True, case="C15", slot="direct-reset", kind="invented"):
        entry = {"kind": kind, "case_id": case, "slot": slot}
        packet_hashes = {"already-validated-packet": "f" * 64}
        sessions, output_files, reports = [], {}, []
        for index in range(2 if case == "C15" else 1):
            name = f"session-{index:04d}"
            status, count = ("completed", 31) if completed else ("failed", 0)
            raw = (
                json.dumps(
                    {"type": "finish", "status": status, "rows_in_memory": count},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                + b"\n"
            )
            sessions.append({"name": name})
            output_files[name + "/events.jsonl"] = raw
            reports.append(
                {
                    "name": name,
                    "status": status,
                    "rows": count,
                    "journal_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        worker = {
            "schema": "opent1d.lt1-buffer-worker/2",
            **entry,
            "verification_context_origin": "invented" if kind == "invented" else "current-runtime",
            "completed": completed,
            "construction_count": 1 if completed else 0,
            "patient_reset_calls": (2 if case == "C15" else 1) if completed else 0,
            "nonfinite_initial_state_probe": False,
            "initial_state_consumed_observation": None,
            # Basal values/units are not changed or evaluated by these counter fixtures.
            "native_basal": {"calls": 1} if completed else None,
            "sessions": reports,
            "packet_sha256": packet_hashes,
            "native_acceptance": False,
            "native_execution_authorized": False,
        }
        return worker, entry, packet_hashes, sessions, output_files

    def test_completed_c15_keeps_one_engine_two_resets_and_one_basal_call(self):
        for kind in ("invented", "native-unadmitted"):
            for slot in ("direct-reset", "wrapped-reset", "direct-fresh", "wrapped-fresh"):
                with self.subTest(kind=kind, slot=slot):
                    self.assertIsNone(self.inspect_worker(*self.fixture(kind=kind, slot=slot)))

    def test_completed_c15_refuses_wrong_or_boolean_construction_counts(self):
        for count in (0, 2, True, False):
            with self.subTest(count=count, value_type=type(count).__name__):
                args = self.fixture()
                args[0]["construction_count"] = count
                with self.assertRaisesRegex(ValueError, "C15.*lifecycle"):
                    self.inspect_worker(*args)

    def test_completed_c15_refuses_wrong_or_boolean_reset_counts(self):
        for count in (1, 3, True, False):
            with self.subTest(count=count, value_type=type(count).__name__):
                args = self.fixture()
                args[0]["patient_reset_calls"] = count
                with self.assertRaisesRegex(ValueError, "C15.*lifecycle"):
                    self.inspect_worker(*args)

    def test_completed_c15_refuses_wrong_or_boolean_basal_call_counts(self):
        for count in (0, 2, True, False):
            with self.subTest(count=count, value_type=type(count).__name__):
                args = self.fixture()
                args[0]["native_basal"]["calls"] = count
                with self.assertRaisesRegex(ValueError, "C15.*lifecycle"):
                    self.inspect_worker(*args)

    def test_completed_c15_requires_a_basal_call_count_object(self):
        for basal in (None, [], "1", {}, {"calls": None}):
            with self.subTest(basal=basal):
                args = self.fixture()
                args[0]["native_basal"] = basal
                with self.assertRaisesRegex(ValueError, "C15.*lifecycle"):
                    self.inspect_worker(*args)

    def test_incomplete_c15_keeps_existing_failed_diagnostic_behavior(self):
        self.assertIsNone(self.inspect_worker(*self.fixture(completed=False)))

    def test_other_case_keeps_its_single_session_reset_count(self):
        self.assertIsNone(self.inspect_worker(*self.fixture(case="C16", slot="direct-filtered")))


if __name__ == "__main__":
    unittest.main()
