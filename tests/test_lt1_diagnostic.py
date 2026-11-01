"""Fractional LT1 interface/reader controls using invented records only."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import ROUND_DOWN, localcontext
from pathlib import Path

from experiments.lt1_diagnostic import reader

ROOT, HERE = reader.ROOT, reader.HERE


@unittest.skipUnless(shutil.which("node"), "Node required for invented LT1 interface controls")
class LT1DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan_raw = (HERE / "plan.json").read_bytes()
        run = subprocess.run(
            [shutil.which("node"), "tests/lt1_diagnostic.test.mjs", "--emit"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        cls.sessions = json.loads(run.stdout)
        cls.identity = reader.identity(cls.plan_raw)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.plan = self.folder / "plan.json"
        self.plan.write_bytes(self.plan_raw)
        self.path = self.folder / "packet.json"
        self.packet = self.make_packet("wrapped")

    def make_packet(self, mode):
        return {
            "schema": reader.SCHEMA,
            "kind": "invented",
            "identity": self.identity,
            "mode": mode,
            **copy.deepcopy(self.sessions[mode]),
        }

    def inspect(self, packet=None):
        self.path.write_text(json.dumps(self.packet if packet is None else packet, allow_nan=False))
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        return reader.inspect(self.path, self.plan, expected)

    def reject(self, mutate, reason):
        self.inspect()
        changed = copy.deepcopy(self.packet)
        mutate(changed)
        with self.assertRaisesRegex(ValueError, reason):
            self.inspect(changed)

    def test_scripted_direct_and_wrapped_match_and_independent_fractional_amount(self):
        direct = self.inspect(self.make_packet("direct"))
        wrapped = self.inspect()
        self.assertEqual(self.sessions["direct"], self.sessions["wrapped"])
        self.assertEqual(wrapped["native_callbacks"], 32)
        self.assertEqual(wrapped["sampled_updates"], 6)
        self.assertEqual(wrapped["completed_intervals"], 31)
        # Scripted delivery: 1/16 + 1/5 + 1/8 + 1/20 + 1/12 = 25/48 U.
        self.assertEqual(wrapped["modeled_delivered_u"], {"numerator": 25, "denominator": 48})
        self.assertEqual(direct["modeled_delivered_u"], wrapped["modeled_delivered_u"])
        self.assertFalse(wrapped["native_acceptance"])

    def test_node_lifecycle_counterexamples_and_closed_native_loader(self):
        run = subprocess.run(
            [shutil.which("node"), "--test", "tests/lt1_diagnostic.test.mjs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_bound_pair_comparison_rejects_state_difference_without_tolerance(self):
        other = self.folder / "direct.json"
        direct = self.make_packet("direct")
        other.write_text(json.dumps(direct))
        wrapped = self.inspect()
        direct_hash = reader.digest(other.read_bytes())
        result = reader.compare(
            other, self.path, self.plan, direct_hash, wrapped["packet_bytes_sha256"]
        )
        self.assertTrue(result["exact_scientific_rows"])
        self.assertFalse(result["tolerance_applied"])
        self.assertFalse(result["native_acceptance"])
        direct["rows"][0]["state"]["Q1"] = 1
        other.write_text(json.dumps(direct))
        with self.assertRaisesRegex(ValueError, "scientific-difference"):
            reader.compare(
                other,
                self.path,
                self.plan,
                reader.digest(other.read_bytes()),
                wrapped["packet_bytes_sha256"],
            )

    def test_prefix_integrates_only_present_endpoints_and_retains_errors(self):
        p = copy.deepcopy(self.packet)
        p.update(status="failed", primary_error="primary", diagnostic_error="export")
        p["rows"] = p["rows"][:3]
        result = self.inspect(p)
        self.assertEqual(result["completed_intervals"], 2)
        self.assertEqual(result["modeled_delivered_u"], {"numerator": 3, "denominator": 100})
        self.assertEqual(
            (result["primary_error"], result["diagnostic_error"]), ("primary", "export")
        )
        p["rows"] = p["rows"][:1]
        self.assertIsNone(self.inspect(p)["modeled_delivered_u"])
        p["rows"] = []
        self.assertEqual(self.inspect(p)["native_callbacks"], 0)
        self.assertIsNone(self.inspect(p)["modeled_delivered_u"])

    def test_complete_rows_never_override_failed_or_unfinished_status(self):
        p = copy.deepcopy(self.packet)
        p.update(status="failed", primary_error="failure after terminal endpoint")
        self.assertEqual(self.inspect(p)["status"], "failed")
        p.update(status="started", primary_error=None)
        self.assertEqual(self.inspect(p)["status"], "started")
        p.update(status="completed", diagnostic_tail=[{"nonfinite": "NaN"}])
        with self.assertRaisesRegex(ValueError, "completion"):
            self.inspect(p)

    def test_identically_wrong_direct_and_wrapped_are_not_an_oracle(self):
        for mode in ("direct", "wrapped"):
            p = self.make_packet(mode)
            tick = next(r for r in p["rows"] if r["time_ms"] == reader.STEP)
            tick["command_u_h"] = 1.8  # Uses current180 instead of previous120.
            with self.assertRaisesRegex(ValueError, "controller-command"):
                self.inspect(p)

    def test_causal_timestamp_freshness_and_announcement_counterexamples(self):
        def delayed(p):
            return next(r for r in p["rows"] if r["time_ms"] == 3 * reader.STEP)

        self.reject(
            lambda p: delayed(p)["transition"]["observation"].update(measured_ms=3 * reader.STEP),
            "causal-observation",
        )
        self.reject(lambda p: delayed(p)["transition"].update(fresh=False), "causal-observation")
        self.reject(
            lambda p: p["rows"][0]["transition"].update(
                new_announcements=["invented-announcement"]
            ),
            "announcement-delivery",
        )
        self.reject(
            lambda p: p["rows"][0]["transition"]["observation"].update(measured_ms=False), "clock"
        )
        self.reject(lambda p: p["rows"][0]["memory"].update(source_ms=False), "clock")

    def test_grid_terminal_tail_and_hidden_state_counterexamples(self):
        self.reject(lambda p: p["rows"][3].update(time_ms=180000), "native-grid")
        self.reject(
            lambda p: p["rows"][-1].update(transition=p["rows"][0]["transition"]),
            "non-tick-transition",
        )
        self.reject(lambda p: p["rows"].pop(), "completion")
        self.reject(lambda p: p["rows"][1].update(raw_cgm_mg_dl=123), "raw-cadence")
        self.reject(lambda p: p["rows"][0].update(patient_private=123), "fields")
        self.reject(lambda p: p["rows"][0].update(intake_g_min=1), "actual-meal")

    def test_packet_plan_and_source_identity_and_unsupported_kind(self):
        self.inspect()
        with self.assertRaisesRegex(ValueError, "packet-identity"):
            reader.inspect(self.path, self.plan, "0" * 64)
        self.reject(lambda p: p["identity"].update(source_revision="0" * 40), "source-identity")
        self.reject(lambda p: p.update(kind="native-approved"), "unadmitted-data-only")
        changed = json.loads(self.plan_raw)
        changed["basal_u_h"] = 2
        self.plan.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "source-identity"):
            self.inspect()

    def test_declared_native_data_does_not_grant_acceptance_or_execution(self):
        p = copy.deepcopy(self.packet)
        p["kind"] = "native-unadmitted"
        result = self.inspect(p)
        self.assertFalse(result["native_acceptance"])
        self.assertFalse(result["native_execution_authorized"])

    def test_fractional_integral_ignores_ambient_decimal_context_and_terminal_rate(self):
        control = self.inspect()
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            self.assertEqual(self.inspect()["modeled_delivered_u"], control["modeled_delivered_u"])
        p = copy.deepcopy(self.packet)
        p["rows"][-1]["delivered_u_h"] = 0
        self.assertEqual(self.inspect(p)["modeled_delivered_u"], control["modeled_delivered_u"])

    def test_no_site_relocation_reads_exact_bytes_without_engine_or_archived_code(self):
        result = self.inspect()
        moved = self.folder / "moved"
        moved.mkdir()
        shutil.copyfile(self.path, moved / "packet.json")
        shutil.copyfile(self.plan, moved / "plan.json")
        run = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.lt1_diagnostic.reader",
                str(moved / "packet.json"),
                "--plan",
                str(moved / "plan.json"),
                "--expected-sha256",
                result["packet_bytes_sha256"],
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        self.assertEqual(json.loads(run.stdout), result)
        self.path.write_text('{"schema":1,"schema":2}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            reader.inspect(self.path, self.plan, reader.digest(self.path.read_bytes()))
        self.path.write_text('{"schema":')
        with self.assertRaises(ValueError):
            reader.inspect(self.path, self.plan, reader.digest(self.path.read_bytes()))

    def test_plan_refuses_native_clamping_seed_boolean_and_release_leak(self):
        plan = reader.decode(self.plan_raw)
        reader.validate_plan(plan)
        for mutate, reason in (
            (lambda p: p["meals"][0].update(duration_ms=30000), "native-duration"),
            (lambda p: p.update(seed=True), "identity"),
            (lambda p: p["release_rules"][0].update(available_ms=0), "release-clock"),
        ):
            changed = copy.deepcopy(plan)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, reason):
                reader.validate_plan(changed)
