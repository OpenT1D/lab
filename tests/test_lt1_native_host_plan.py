"""Static candidate profile/plan controls; no candidate, private intake or OS probe."""

import copy
import os
import unittest
from unittest.mock import patch

from experiments.lt1_diagnostic import native_host_plan as plan


@unittest.skipUnless(os.name == "posix", "POSIX trusted source reader required")
class NativeHostPlanTests(unittest.TestCase):
    def setUp(self):
        self.roots = {key: "/invented/" + key for key in plan.ROOTS}
        self.identity = plan.source_identity()

    def prepare(self):
        return plan.prepare(self.roots, expected_identity=self.identity)

    def test_exact_candidate_native_profile_and_unchanged_closed_execution_contract(self):
        before = copy.deepcopy(self.roots)
        result = self.prepare()
        expected = plan.launcher.profile(
            *(plan.PurePosixPath(self.roots[key]) for key in ("staging", "packet", "output"))
        )
        self.assertEqual(result["profile"], expected)
        self.assertEqual(result["profile_sha256"], plan.preflight.digest(expected.encode()))
        self.assertEqual(result["runtime"], plan.preflight.RUNTIME)
        self.assertEqual(result["candidate"], plan.preflight.CANDIDATE)
        self.assertEqual(result["argv"][3], "/invented/staging/runtime/bin/node")
        self.assertEqual(result["argv"][4], str(plan.ROOT / plan.preflight.ENTRY))
        self.assertEqual(
            result["argv"][5:], [self.roots[k] for k in ("staging", "packet", "output")]
        )
        self.assertEqual(
            result["passed_environment"], {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
        )
        self.assertEqual(result["stdin"], "DEVNULL")
        self.assertIs(result["close_fds"], True)
        self.assertEqual(result["exec_argv"], [])
        self.assertEqual(self.roots, before)
        self.assertNotIn("(allow network", result["profile"])
        self.assertIn(
            '(allow process-exec (literal "/invented/staging/runtime/bin/node"))', expected
        )

    def test_tooling_evidence_cannot_fill_any_native_case_or_grant_authority(self):
        result = self.prepare()
        self.assertEqual(set(result["cases"]), set(plan.preflight.NATIVE_CASES))
        for case in result["cases"].values():
            self.assertEqual((case["state"], case["origin"]), ("not_run", "none"))
            self.assertTrue(case["required"])
        self.assertIs(result["tooling_host_evidence_transferred"], False)
        self.assertEqual(result["C15-C18"], "not_run")
        self.assertIn("not-wired", result["native_entry_channels"])
        self.assertTrue(all(result[key] is False for key in plan.AUTHORITY))
        self.assertIn("global-file-metadata-and-mach-lookup-rules", result["limitations"])

    def test_plan_never_calls_native_entry_host_capture_private_intake_or_spawn(self):
        with (
            patch.object(plan.launcher, "launch_native", side_effect=AssertionError("launch")),
            patch.object(plan.launcher, "_roots", side_effect=AssertionError("private roots")),
            patch.object(plan.launcher.host_context, "capture", side_effect=AssertionError("host")),
            patch.object(plan.launcher.subprocess, "run", side_effect=AssertionError("run")),
            patch.object(plan.launcher.subprocess, "Popen", side_effect=AssertionError("spawn")),
        ):
            result = self.prepare()
        self.assertIs(result["private_root_intake_performed"], False)
        self.assertIs(result["host_capture_performed"], False)
        self.assertIs(result["stage_materialized"], False)

    def test_bad_expected_source_refuses_before_profile_derivation(self):
        with patch.object(plan.launcher, "profile", side_effect=AssertionError("profile")):
            with self.assertRaisesRegex(ValueError, "expected planner source"):
                plan.prepare(self.roots, expected_identity={})

    def test_lexical_alias_nested_and_checkout_roots_refuse_before_profile(self):
        for key, value in (
            ("packet", self.roots["staging"]),
            ("output", "/invented/staging/child"),
            ("evidence", "/invented/../evidence"),
            ("evidence", "relative"),
            ("staging", str(plan.ROOT)),
            ("packet", str(plan.ROOT.parent)),
        ):
            roots = {**self.roots, key: value}
            with (
                self.subTest(key=key, value=value),
                patch.object(plan.launcher, "profile", side_effect=AssertionError("profile")),
            ):
                with self.assertRaises(ValueError):
                    plan.prepare(roots, expected_identity=self.identity)

    def test_source_change_during_profile_refuses(self):
        changed = copy.deepcopy(self.identity)
        changed["implementation"]["experiments/invented.py"] = "a" * 64
        with patch.object(plan, "source_identity", side_effect=[self.identity, changed]):
            with self.assertRaisesRegex(ValueError, "source changed"):
                self.prepare()

    def test_source_map_binds_explicit_native_sources_readers_and_all_authority_files(self):
        sources = self.identity["implementation"]
        for name in (
            "native_host_plan.py",
            "native_launcher.py",
            "integration_worker.mjs",
            "native_loader.mjs",
            "journal_reader.py",
            "reader.py",
            "native-admissions.json",
            "setup-request-admissions.json",
            "removal-admissions.json",
        ):
            self.assertIn("experiments/lt1_diagnostic/" + name, sources)
        self.assertTrue(
            all(".." not in key.split("/") and not key.startswith("/") for key in sources)
        )

    def test_returned_mutation_does_not_change_future_candidate_or_case_requirements(self):
        result = self.prepare()
        result["runtime"]["node"] = "invented changed"
        result["cases"].clear()
        again = self.prepare()
        self.assertEqual(again["runtime"], plan.preflight.RUNTIME)
        self.assertEqual(set(again["cases"]), set(plan.preflight.NATIVE_CASES))


class NativeHostPlanUnsupportedTests(unittest.TestCase):
    def test_unsupported_source_reader_refuses_before_source_profile_or_root_intake(self):
        with (
            patch.object(plan.os, "name", "unsupported"),
            patch.object(plan, "identity", side_effect=AssertionError("source intake")),
            patch.object(plan.launcher, "profile", side_effect=AssertionError("profile")),
        ):
            with self.assertRaisesRegex(ValueError, "POSIX trusted source reader required"):
                plan.prepare(object(), expected_identity={})
