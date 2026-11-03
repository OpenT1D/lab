"""Invented byte-only preparation controls; never captures OS or starts Node."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from test_lt1_host_context import invented_context

from experiments.lt1_diagnostic import host_context
from experiments.lt1_diagnostic import native_preflight as preflight


def wire(value):
    return json.dumps(value, sort_keys=True).encode()


class NativePreflightTests(unittest.TestCase):
    def setUp(self):
        root = patch.object(preflight, "ROOT", Path("/invented/repo"))
        root.start()
        self.addCleanup(root.stop)
        required = (
            preflight.ENTRY,
            "experiments/lt1_diagnostic/native_loader.mjs",
            "experiments/lt1_diagnostic/host_context.py",
            "experiments/lt1_diagnostic/native_preflight.py",
            "experiments/lt1_diagnostic/journal_reader.py",
            "experiments/lt1_diagnostic/reader.py",
        )
        sources = dict.fromkeys(required, "a" * 64)
        self.inputs = {name: ("invented " + name).encode() for name in preflight.INPUTS}
        self.inputs["source_inventory"] = wire(
            {"schema": "opent1d.lt1-launch-source-inventory/1", "files": sources}
        )
        self.inputs["plan"] = b'{"kind":"invented"}'
        self.inputs["reader_identity"] = wire(
            {
                "protocol": {
                    "source_revision": preflight.REVISION,
                    "runtime_candidate": preflight.CANDIDATE,
                    "selected_runtime_artifact_sha256": preflight.RUNTIME["artifact_sha256"],
                    "plan_bytes_sha256": preflight.digest(self.inputs["plan"]),
                    "implementation_sha256": {"experiments/lt1_diagnostic/reader.py": "a" * 64},
                },
                "implementation": {"experiments/lt1_diagnostic/journal_reader.py": "a" * 64},
            }
        )
        self.inputs["host_context"] = wire(invented_context())
        self.spec = {
            "schema": "opent1d.lt1-native-launch-preparation/1",
            "kind": "invented",
            "runtime": copy.deepcopy(preflight.RUNTIME),
            "launch": {
                "argv": [
                    "/invented/staging/runtime/bin/node",
                    "/invented/repo/" + preflight.ENTRY,
                    "/invented/staging",
                    "/invented/packet",
                    "/invented/output",
                ],
                "cwd": "/invented/repo",
                "staging_root": "/invented/staging",
                "packet_root": "/invented/packet",
                "output_root": "/invented/output",
                "exec_argv": [],
                "environment": dict(host_context.ENVIRONMENT),
                "timeout_seconds": 4,
                "grace_seconds": 0.2,
                "stdio_policy": "shared-supervisor-defaults-unqualified",
                "resource_policy": "deadline-grace-only-no-rlimit-or-rss-claim",
            },
            "input_sha256": {},
            "gate_states": dict.fromkeys(preflight.GATES, "pending"),
            "native_cases": {
                name: {"state": "not_run", "origin": "none"} for name in preflight.NATIVE_CASES
            },
        }
        self.bind()
        self.policy = {
            "schema": "opent1d.lt1-launch-review-policy/1",
            "runtime": copy.deepcopy(preflight.RUNTIME),
            "worker_entry": preflight.ENTRY,
            "max_context_age_seconds": 60,
        }

    def bind(self):
        self.spec["input_sha256"] = {
            name: preflight.digest(raw) for name, raw in self.inputs.items()
        }

    def assess(self, *, as_of="2026-01-01T00:00:10Z"):
        raw, policy = wire(self.spec), wire(self.policy)
        return preflight.assess(
            raw, preflight.digest(raw), policy, preflight.digest(policy), self.inputs, as_of=as_of
        )

    def test_consistent_invented_packet_is_blocked_and_has_no_authority(self):
        report = self.assess()
        self.assertTrue(report["structural_spec_valid"])
        self.assertEqual(report["status"], "blocked")
        self.assertIn("packet-is-invented", report["blockers"])
        self.assertEqual(report["native_cases"], self.spec["native_cases"])
        for key in preflight.AUTHORITY:
            self.assertIs(report[key], False)
        self.assertTrue(
            all("case:" + case in report["blockers"] for case in preflight.NATIVE_CASES)
        )

    def test_pure_assessment_reads_no_path_captures_no_host_and_spawns_nothing(self):
        with (
            patch.object(host_context, "capture", side_effect=AssertionError("must not capture")),
            patch.object(
                host_context.subprocess, "run", side_effect=AssertionError("must not spawn")
            ),
            patch.object(Path, "read_bytes", side_effect=AssertionError("must not read paths")),
        ):
            self.assertTrue(self.assess()["structural_spec_valid"])

    def test_native_candidate_and_worker_are_pinned_not_relabelled(self):
        for target, key, value in (
            (self.policy["runtime"], "node", "v99.0.0"),
            (self.spec["runtime"], "executable_sha256", "0" * 64),
            (self.policy, "worker_entry", "other.mjs"),
        ):
            old = target[key]
            target[key] = value
            with self.assertRaises(ValueError):
                self.assess()
            target[key] = old

    def test_extra_node_flags_preloads_cwd_or_enforcement_claims_refuse(self):
        mutations = (
            lambda v: v["exec_argv"].append("--no-addons"),
            lambda v: v["argv"].insert(1, "--import=other.mjs"),
            lambda v: v["environment"].update(NODE_OPTIONS="--require=other.js"),
            lambda v: v["environment"].update(DYLD_INSERT_LIBRARIES="/invented/lib"),
            lambda v: v.update(cwd="/invented/staging"),
            lambda v: v.update(stdio_policy="all-fds-closed"),
            lambda v: v.update(resource_policy="hard-rss-enforced"),
            lambda v: v.update(grace_seconds=-0.5),
            lambda v: v.update(timeout_seconds=True),
        )
        original = copy.deepcopy(self.spec["launch"])
        for mutate in mutations:
            self.spec["launch"] = copy.deepcopy(original)
            mutate(self.spec["launch"])
            with self.assertRaises(ValueError):
                self.assess()

    def test_roots_and_exact_argv_cannot_be_adopted_from_arbitrary_paths(self):
        for key, value in (
            ("output_root", "/invented/staging/output"),
            ("staging_root", "/invented/../changed"),
            ("packet_root", "/invented/repo/packet"),
            ("packet_root", "/invented"),
            ("output_root", "/invented/output/"),
        ):
            original = copy.deepcopy(self.spec["launch"])
            self.spec["launch"][key] = value
            with self.assertRaises(ValueError):
                self.assess()
            self.spec["launch"] = original

    def test_external_hashes_and_duplicate_fields_are_checked(self):
        raw, policy = wire(self.spec), wire(self.policy)
        with self.assertRaisesRegex(ValueError, "external byte identity"):
            preflight.assess(
                raw,
                "0" * 64,
                policy,
                preflight.digest(policy),
                self.inputs,
                as_of="2026-01-01T00:00:10Z",
            )
        duplicate = b'{"schema":1,"schema":2}'
        with self.assertRaises(ValueError):
            preflight.assess(
                duplicate,
                preflight.digest(duplicate),
                policy,
                preflight.digest(policy),
                self.inputs,
                as_of="2026-01-01T00:00:10Z",
            )
        self.inputs["rights_review"] += b"changed"
        with self.assertRaisesRegex(ValueError, "bound input bytes"):
            self.assess()

    def test_source_reader_plan_and_collector_bindings_are_consistent(self):
        original = copy.deepcopy(self.inputs)
        for mutate in (
            lambda data: data["files"].pop(preflight.ENTRY),
            lambda data: data["files"].update({"experiments/../other.py": "a" * 64}),
            lambda data: data["files"].update(
                {"experiments/lt1_diagnostic/host_context.py": "d" * 64}
            ),
        ):
            self.inputs = copy.deepcopy(original)
            value = json.loads(self.inputs["source_inventory"])
            mutate(value)
            self.inputs["source_inventory"] = wire(value)
            self.bind()
            with self.assertRaises(ValueError):
                self.assess()
        self.inputs = copy.deepcopy(original)
        self.inputs["plan"] = b"different invented plan"
        self.bind()
        with self.assertRaisesRegex(ValueError, "reader/plan/runtime"):
            self.assess()

    def test_query_unknown_or_context_expiry_cannot_be_native_clearance(self):
        value = invented_context()
        value["queries"][host_context.KEYS[0]].update(returncode=1, value=None, error="unavailable")
        value["unknown"] = host_context.unknown_fields(value)
        value["status"] = "unavailable"
        self.inputs["host_context"] = wire(value)
        self.bind()
        report = self.assess()
        self.assertIn("query:" + host_context.KEYS[0], report["blockers"])
        for observed in ("2025-12-31T23:59:59Z", "2026-01-01T01:00:00Z"):
            self.assertIn("host-context-future-or-stale", self.assess(as_of=observed)["blockers"])

    def test_python_fixture_passes_cannot_become_actual_native_cases(self):
        for key in self.spec["native_cases"]:
            self.spec["native_cases"][key] = {"state": "passed", "origin": "invented"}
        self.spec["gate_states"] = dict.fromkeys(preflight.GATES, "accepted")
        report = self.assess()
        self.assertTrue(
            all("case:" + case in report["blockers"] for case in preflight.NATIVE_CASES)
        )
        self.assertEqual(report["status"], "blocked")
        self.spec["native_cases"][preflight.NATIVE_CASES[0]]["origin"] = "actual-native"
        with self.assertRaisesRegex(ValueError, "evidence origin"):
            self.assess()

    def test_oldest_context_observation_and_canonical_collector_are_required(self):
        value = invented_context()
        value["observed_from"] = "2025-12-31T00:00:00Z"
        self.inputs["host_context"] = wire(value)
        self.bind()
        self.assertIn("host-context-future-or-stale", self.assess()["blockers"])
        value = invented_context()
        value["collector_identity"]["implementation"] = {
            "experiments/lt1_diagnostic/native_loader.mjs": "a" * 64
        }
        self.inputs["host_context"] = wire(value)
        self.bind()
        with self.assertRaisesRegex(ValueError, "collector identity"):
            self.assess()

    def test_claimed_approval_and_missing_cases_are_not_schema_extensions(self):
        self.spec["claimed_approved"] = True
        with self.assertRaisesRegex(ValueError, "fields"):
            self.assess()
        self.spec.pop("claimed_approved")
        self.spec["native_cases"].pop(preflight.NATIVE_CASES[0])
        with self.assertRaisesRegex(ValueError, "fields"):
            self.assess()

    def test_input_and_aggregate_bounds_refuse_before_component_parsing(self):
        self.inputs["rights_review"] = b"x" * (preflight.LIMIT + 1)
        self.bind()
        with self.assertRaisesRegex(ValueError, "input bounds"):
            self.assess()
        self.inputs = dict.fromkeys(preflight.INPUTS, b"x" * preflight.LIMIT)
        self.bind()
        with self.assertRaisesRegex(ValueError, "input bounds"):
            self.assess()


if __name__ == "__main__":
    unittest.main()
