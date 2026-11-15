"""Engine-free contracts and independent counterexamples; no native dependencies."""

import builtins
import copy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.simglucose_audit import bootstrap, consumer
from experiments.simglucose_audit.contract import (
    AUTHORITY,
    HORIZON,
    STEP,
    decode,
    default_config,
    digest,
    encode,
    source_contract,
    source_identity,
)
from experiments.simglucose_audit.reader import inspect_fixture

ROOT = Path(__file__).resolve().parents[1]


def proposal_bundle():
    """Public source-only proposal data. Labels are deliberately not opened paths."""
    contract = source_contract()
    common = {
        "kind": "proposal-only",
        "eligible_for_admission_registry": False,
        "implementation_exists": False,
        "runtime_observation": False,
        "approval_requested": False,
        "activation_command": None,
        "authority": AUTHORITY,
        "retention": {
            "private_outside_git": True,
            "max_days_new_technical_facts": 30,
            "not_after_UTC": "2099-01-01T00:00:00Z",
            "earlier_limits_win": True,
            "old_origins_reset": False,
            "unknown_old_origins_timely_retention_not_proven": True,
            "automatic_cleanup_or_extension": False,
        },
    }
    assets = copy.deepcopy(common) | {
        "schema": "opent1d.private-simglucose-audit1-assets-proposal/1",
        **copy.deepcopy(contract["asset_semantics"]),
    }
    for key in ("selected_code", "notices"):
        for row in assets[key]:
            row["source_file"] = "/invented-never-opened/source.py"
    boot = copy.deepcopy(common) | {
        "schema": "opent1d.private-simglucose-audit1-bootstrap-proposal/1",
        **copy.deepcopy(contract["bootstrap_semantics"]),
    }
    consume = copy.deepcopy(common) | {
        "schema": "opent1d.private-simglucose-audit1-consumer-proposal/1",
        **copy.deepcopy(contract["consumer_semantics"]),
    }
    return assets, boot, consume


def proposal_bytes(documents):
    assets, boot, consume = copy.deepcopy(documents)
    a = encode(assets)
    boot["asset_manifest_sha256"] = digest(a)
    b = encode(boot)
    consume.update(asset_manifest_sha256=digest(a), bootstrap_manifest_sha256=digest(b))
    c = encode(consume)
    index = {
        "schema": "opent1d.private-simglucose-audit1-manifest-bundle/1",
        "kind": "proposal-only",
        "files": {
            name: {"bytes": len(raw), "sha256": digest(raw)}
            for name, raw in zip(
                (
                    "asset-manifest.private.json",
                    "bootstrap-manifest.private.json",
                    "consumer-manifest.private.json",
                ),
                (a, b, c),
                strict=True,
            )
        },
        "operational_approvals_requested": False,
        "new_authority_granted": False,
        "native_execution_deferred": True,
    }
    raw = encode(index)
    return a, b, c, raw, digest(raw)


class SimglucoseAuditTests(unittest.TestCase):
    def run_config(self, config=None):
        raw = encode(default_config() if config is None else config)
        report = bootstrap.run_fixture(raw)
        encoded = encode(report)
        summary = inspect_fixture(encoded, digest(encoded), raw, digest(raw))
        return report, summary

    def test_complete_reference_units_amount_and_observation_channels(self):
        report, summary = self.run_config()
        self.assertEqual(
            (summary["status"], len(report["rows"]), len(report["observations"])),
            ("completed", 10, 11),
        )
        self.assertEqual(
            report["calls"],
            {"constructed": 1, "reset": 1, "step": 10, "close": 1, "sampled_observations": 11},
        )
        self.assertEqual(report["scripted_observation_cursor"], 10)
        self.assertEqual(report["initial_history_cgm"], 119)
        self.assertEqual(report["observations"][0]["glucose_mg_dl"], 120)
        self.assertEqual(report["rows"][2]["command_u_h"].hex(), "0x1.cccccccccccccp+0")
        self.assertEqual(summary["delivered_u_exact"], {"numerator": "309", "denominator": "500"})
        for row, received in zip(report["rows"], report["scripted_actions_received"], strict=True):
            self.assertEqual(received, {"basal_u_min": row["command_u_h"] / 60, "bolus_u_min": 0.0})
        self.assertFalse(summary["native_acceptance"])

    def test_all_variants_repeat_and_reset_without_fixture_state_leak(self):
        for variant in ("filtered", "unfiltered", "future80", "fasting"):
            config = default_config() | {"variant": variant}
            a, _ = self.run_config(config)
            b, _ = self.run_config(config)
            self.assertEqual(encode(a), encode(b))
            self.assertEqual(a["rows"][0]["previous_mg_dl"], 120.0)
        first, _ = self.run_config()
        future, _ = self.run_config(default_config() | {"variant": "future80"})
        self.assertEqual(first["rows"], future["rows"])
        self.assertNotEqual(first["config_sha256"], future["config_sha256"])

    def test_delayed_measurement_memory_order_and_single_announcement(self):
        report, _ = self.run_config()
        rows = report["rows"]
        self.assertEqual(
            [r["observation"]["measured_ms"] for r in rows[:6]],
            [0, STEP, 2 * STEP, 2 * STEP, 2 * STEP, 3 * STEP],
        )
        self.assertEqual([r["fresh"] for r in rows[:6]], [True, True, True, False, False, True])
        self.assertEqual(rows[5]["previous_mg_dl"], 60)
        self.assertEqual(rows[5]["observation"]["available_ms"], 900000)
        self.assertEqual([r["time_ms"] for r in rows if r["new_announcements"]], [900000])

    def test_masked_values_never_enter_controller(self):
        original, _ = self.run_config()
        config = default_config()
        config["samples"][4:6] = [999, 888]
        changed, _ = self.run_config(config)
        self.assertNotEqual(changed["observations"], original["observations"])
        self.assertEqual(changed["rows"], original["rows"])

    def test_delayed_future_value_does_not_change_controller_prefix(self):
        original, _ = self.run_config()
        config = default_config()
        config["samples"][3] = 999
        changed, _ = self.run_config(config)
        self.assertEqual(original["rows"][:5], changed["rows"][:5])
        self.assertNotEqual(original["rows"][5:], changed["rows"][5:])

    def test_terminal_point_never_adds_a_command_or_amount(self):
        report, _ = self.run_config()
        config = default_config()
        config["samples"][-1] = 999
        changed, _ = self.run_config(config)
        self.assertEqual(report["rows"], changed["rows"])
        self.assertEqual(len(changed["scripted_actions_received"]), 10)
        self.assertEqual(changed["observations"][-1]["measured_ms"], HORIZON)

    def test_clipping_and_prior_initial_memory(self):
        for basal, initial, expected in ((1.2, 1000, 3.0), (0.6, 0, 0.0)):
            config = default_config() | {"basal_u_h": basal}
            config["samples"][0] = initial
            result, _ = self.run_config(config)
            self.assertEqual(result["rows"][0]["command_u_h"], basal)
            self.assertEqual(result["rows"][1]["command_u_h"], expected)

    def test_fault_prefixes_and_no_false_completion(self):
        expected = {
            "cancel-before-reset": 0,
            "reset-error": 0,
            "after-two": 2,
            "cancel-after-two": 2,
            "early-done": 2,
            "terminal-tail": 10,
        }
        for fault, intervals in expected.items():
            with self.subTest(fault=fault):
                report, summary = self.run_config(default_config() | {"fault": fault})
                self.assertNotEqual(summary["status"], "completed")
                self.assertEqual(summary["completed_intervals"], intervals)
                if fault in ("after-two", "cancel-after-two"):
                    self.assertEqual(report["pending_command"]["time_ms"], 2 * STEP)
                    self.assertEqual(len(report["scripted_actions_received"]), 3)
                    self.assertEqual(report["calls"]["sampled_observations"], 3)
                if intervals == 0:
                    self.assertIsNone(summary["delivered_u_exact"])

    def test_primary_error_survives_cleanup_failure_and_full_journal_not_success(self):
        report, _ = self.run_config(default_config() | {"fault": "after-two", "close_error": True})
        self.assertEqual(report["primary_error"], "scripted-after-two")
        self.assertEqual(report["diagnostic_error"], "scripted-close-error")
        full, summary = self.run_config(default_config() | {"close_error": True})
        self.assertEqual(len(full["rows"]), 10)
        self.assertEqual(summary["status"], "failed")

    def test_invalid_inputs_refuse_before_constructing_fixed_engine(self):
        variants = []
        for value in (True, False, float("inf"), -1, 10**500):
            config = default_config() | {"basal_u_h": value}
            variants.append(config)
        variants.extend(
            [
                default_config() | {"kind": "native"},
                default_config() | {"factory": "simglucose"},
                default_config() | {"close_error": 1},
            ]
        )
        with patch.object(
            consumer, "ScriptedEngine", side_effect=AssertionError("constructor reached")
        ):
            for config in variants:
                with self.subTest(config_keys=sorted(config)), self.assertRaises(ValueError):
                    bootstrap.run_fixture(encode(config))
            with self.assertRaisesRegex(ValueError, "duplicate-json-field"):
                bootstrap.run_fixture(b'{"kind":"invented","kind":"native"}')
            with self.assertRaisesRegex(ValueError, "nonfinite-json"):
                bootstrap.run_fixture(b'{"samples":[NaN]}')

    def test_native_refuses_before_decode_paths_imports_or_constructor(self):
        class Poison:
            def __getattribute__(self, _):
                raise AssertionError("input inspected")

        with (
            patch("builtins.open", side_effect=AssertionError("file reached")),
            patch("json.loads", side_effect=AssertionError("decode reached")),
            patch("pathlib.Path.read_bytes", side_effect=AssertionError("path reached")),
            patch("builtins.__import__", side_effect=AssertionError("import reached")),
        ):
            with self.assertRaisesRegex(PermissionError, "native execution deferred"):
                bootstrap.run_native(Poison(), path=Poison())

    def test_fixture_route_imports_no_selected_dependency(self):
        original = builtins.__import__
        blocked = {
            "simglucose",
            "numpy",
            "scipy",
            "pandas",
            "gym",
            "matplotlib",
            "glucosim",
            "_distutils_hack",
        }

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in blocked:
                raise AssertionError("selected dependency imported")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded):
            self.run_config()

    def test_reader_refuses_forged_science_actions_origin_completion_and_counts(self):
        config_raw = encode(default_config())
        report = bootstrap.run_fixture(config_raw)
        mutations = [
            lambda r: r.update(kind="native"),
            lambda r: r.update(native_execution=True),
            lambda r: r["rows"][1].update(command_u_h=1.8),
            lambda r: r["scripted_actions_received"][0].update(basal_u_min=1.2),
            lambda r: r["calls"].update(sampled_observations=12),
            lambda r: r.update(scripted_observation_cursor=11),
            lambda r: r["rows"].pop(),
            lambda r: r.update(source_identity={}),
            lambda r: r.update(extra="unknown"),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(report)
            mutate(changed)
            raw = encode(changed)
            with self.assertRaises(ValueError):
                inspect_fixture(raw, digest(raw), config_raw, digest(config_raw))
        with self.assertRaisesRegex(ValueError, "external-byte-pins"):
            inspect_fixture(encode(report), "0" * 64, config_raw, digest(config_raw))

    def test_reader_cannot_promote_interrupted_prefix(self):
        config_raw = encode(default_config() | {"fault": "after-two"})
        report = bootstrap.run_fixture(config_raw)
        report.update(status="completed", primary_error=None, pending_command=None)
        raw = encode(report)
        with self.assertRaisesRegex(ValueError, "fixture-oracle-mismatch"):
            inspect_fixture(raw, digest(raw), config_raw, digest(config_raw))

    def test_queue_and_controller_refuse_bad_clocks_types_and_extra_fields(self):
        queue = consumer.ReleaseQueue("filtered")
        with self.assertRaisesRegex(ValueError, "no-released-observation"):
            queue.release(0)
        self.assertEqual(queue.next_tick, 0)
        for index in range(11):
            queue.offer({"measured_ms": index * STEP, "glucose_mg_dl": 120})
        with self.assertRaisesRegex(ValueError, "measurement-grid"):
            queue.offer({"measured_ms": 11 * STEP, "glucose_mg_dl": 120})
        for bad in (True, -1, STEP, HORIZON):
            control = consumer.SampledAudit1(1.2)
            with self.assertRaises(ValueError):
                control.update(bad, {"measured_ms": 0, "available_ms": 0, "glucose_mg_dl": 120})
        control = consumer.SampledAudit1(1.2)
        observation = {"measured_ms": 0, "available_ms": 0, "glucose_mg_dl": 120}
        with self.assertRaisesRegex(ValueError, "observation-fields"):
            control.update(0, observation | {"patient_state": []})
        control.update(0, observation)
        with self.assertRaisesRegex(ValueError, "changed-held-observation"):
            control.update(STEP, observation | {"glucose_mg_dl": 999})

    def test_source_identity_includes_parent_engine_oracle_and_contract(self):
        identity = source_identity()
        self.assertTrue(
            {"experiments/__init__.py", "reference.py", "_fixture.py", "source-contract.json"}
            <= set(identity)
        )
        original = dict(identity)
        altered = original | {"consumer.py": "0" * 64}
        with patch(
            "experiments.simglucose_audit.contract.source_identity", side_effect=[original, altered]
        ):
            with self.assertRaisesRegex(ValueError, "source-changed-during-fixture"):
                bootstrap.run_fixture()

    def test_proposal_inspection_is_pinned_data_only_and_stays_blocked(self):
        supplied = proposal_bytes(proposal_bundle())
        original = Path.read_bytes

        def own_contract_only(path):
            self.assertEqual(path, ROOT / "experiments/simglucose_audit/source-contract.json")
            return original(path)

        with patch.object(Path, "read_bytes", own_contract_only):
            result = bootstrap.inspect_proposals(*supplied)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["source_paths_opened"])

    def test_proposal_rehashed_asset_scope_and_science_drift_refused(self):
        mutations = [
            lambda a, b, c: a["consumer_excluded_asset_metadata"][0].update(consumer_allowed=True),
            lambda a, b, c: a["future_path_read_policy"].update(
                no_Quest_or_BB_source_fallback=False
            ),
            lambda a, b, c: a["notices"][0].update(keep_full_notice=False),
            lambda a, b, c: a["selected_code"][0].update(sha256="0" * 64),
            lambda a, b, c: c["configuration"].update(sensor_seed=102),
            lambda a, b, c: b["compatibility_contract"]["EntryPoint"].update(
                parse_or_load_allowed=True
            ),
        ]
        for mutate in mutations:
            docs = proposal_bundle()
            mutate(*docs)
            with self.assertRaises(ValueError):
                bootstrap.inspect_proposals(*proposal_bytes(docs))

    def test_proposal_literal_authority_retention_and_external_pin_refused(self):
        for bad in (True, 0, 1):
            docs = proposal_bundle()
            docs[0]["authority"]["setup_authorized"] = bad
            with self.assertRaisesRegex(ValueError, "no-proposal-authority"):
                bootstrap.inspect_proposals(*proposal_bytes(docs))
        docs = proposal_bundle()
        docs[0]["retention"]["old_origins_reset"] = True
        with self.assertRaisesRegex(ValueError, "inherited-retention-limits"):
            bootstrap.inspect_proposals(*proposal_bytes(docs))
        raw = proposal_bytes(proposal_bundle())
        with self.assertRaisesRegex(ValueError, "external-proposal-index-pin"):
            bootstrap.inspect_proposals(*raw[:4], "0" * 64)

    def test_fixed_fixture_cli_and_closed_native_cli(self):
        for mode, expected in (("fixture", 0), ("native", 1)):
            result = subprocess.run(
                [sys.executable, "-B", "-m", "experiments.simglucose_audit", mode],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, expected, result.stderr)
            if mode == "fixture":
                self.assertEqual(decode(result.stdout.encode())["kind"], "invented")
            else:
                self.assertIn("native execution deferred", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
