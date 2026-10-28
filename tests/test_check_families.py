"""Stage selection and the required public gate retain explicit failure outcomes."""

import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import check, ci_gate, public_smoke
from tests import public_smoke_cases


class CheckStageTests(unittest.TestCase):
    def test_default_order_and_each_requested_family(self):
        for requested, expected in (
            ([], ["style", "tests", "docs"]),
            (["--stage", "style"], ["style"]),
            (["--stage", "tests"], ["tests"]),
            (["--stage", "docs"], ["docs"]),
        ):
            calls = []
            with (
                self.subTest(arguments=requested),
                patch.object(check, "check_style", side_effect=lambda: calls.append("style")),
                patch.object(check, "check_tests", side_effect=lambda: calls.append("tests")),
                patch.object(
                    check, "build_documentation", side_effect=lambda: calls.append("docs")
                ),
            ):
                check.main(requested)
            self.assertEqual(calls, expected)

    def test_unknown_stage_does_not_start_any_check(self):
        with (
            patch.object(check, "check_style") as style,
            patch.object(check, "check_tests") as tests,
            patch.object(check, "build_documentation") as docs,
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as failure,
        ):
            check.main(["--stage", "not-a-stage"])
        self.assertEqual(failure.exception.code, 2)
        for action in (style, tests, docs):
            action.assert_not_called()

    def test_default_failure_is_not_swallowed_or_followed_by_later_checks(self):
        with (
            patch.object(check, "check_style"),
            patch.object(
                check, "check_tests", side_effect=subprocess.CalledProcessError(7, "tests")
            ),
            patch.object(check, "build_documentation") as docs,
            self.assertRaises(subprocess.CalledProcessError) as failure,
        ):
            check.main([])
        self.assertEqual(failure.exception.returncode, 7)
        docs.assert_not_called()


class PublicGateTests(unittest.TestCase):
    def test_every_failure_cancellation_skip_or_missing_result_is_rejected(self):
        names = sorted(ci_gate.REQUIRED)
        for states in itertools.product(
            ("success", "failure", "cancelled", "skipped", None), repeat=len(names)
        ):
            results = {name: {"result": state} for name, state in zip(names, states, strict=True)}
            with self.subTest(states=states):
                if all(state == "success" for state in states):
                    ci_gate.validate(results)
                else:
                    with self.assertRaises(ValueError):
                        ci_gate.validate(results)

    def test_missing_extra_and_malformed_families_are_not_vacuous_success(self):
        valid = {name: {"result": "success", "outputs": {}} for name in ci_gate.REQUIRED}
        ci_gate.validate(valid)
        for value in (
            {},
            [],
            None,
            valid | {"native": {"result": "success"}},
            {**valid, "browser": None},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ci_gate.validate(value)
        for name in valid:
            with self.subTest(missing=name), self.assertRaises(ValueError):
                ci_gate.validate({key: value for key, value in valid.items() if key != name})

    def test_pr_cannot_pass_with_only_the_previous_three_public_families(self):
        previous = {
            name: {"result": "success"} for name in ("repository-checks", "public-smoke", "browser")
        }
        with self.assertRaisesRegex(ValueError, "Missing"):
            ci_gate.validate(previous)

    def test_gate_cli_returns_failure_for_bad_or_absent_input(self):
        path = Path(ci_gate.__file__)
        valid = json.dumps({name: {"result": "success"} for name in ci_gate.REQUIRED})
        for payload, expected in ((None, 1), ("not-json", 1), ("{}", 1), (valid, 0)):
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in {"PUBLIC_CHECK_RESULTS", "PUBLIC_CHECK_EVENT"}
            }
            env["PUBLIC_CHECK_EVENT"] = "pull_request"
            if payload is not None:
                env["PUBLIC_CHECK_RESULTS"] = payload
            completed = subprocess.run(
                [sys.executable, "-B", "-S", str(path)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, expected, completed.stderr)

    def test_only_named_non_pr_events_allow_the_dependency_only_skip(self):
        valid = {name: {"result": "success"} for name in ci_gate.REQUIRED}
        skipped = valid | {"dependency-review": {"result": "skipped"}}
        for event in ("push", "workflow_dispatch"):
            ci_gate.validate(skipped, event)
            for name in ci_gate.REQUIRED - {"dependency-review"}:
                with self.subTest(event=event, name=name), self.assertRaises(ValueError):
                    ci_gate.validate(skipped | {name: {"result": "skipped"}}, event)
        for event in ("pull_request", "pull_request_target", "schedule", "", None):
            with self.subTest(event=event), self.assertRaises(ValueError):
                ci_gate.validate(skipped, event)


class SmokeSelectionTests(unittest.TestCase):
    def test_http_fixture_closes_transport_when_service_cleanup_fails(self):
        case = public_smoke_cases.HTTPTaskSmoke()
        service, server, thread = Mock(), Mock(), Mock()
        service.close.side_effect = OSError("Synthetic service cleanup failure")
        thread.is_alive.return_value = False
        case.service, case.server, case.thread = service, server, thread
        with self.assertRaisesRegex(OSError, "Synthetic service cleanup"):
            case.stop()
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()
        thread.join.assert_called_once_with(2)
        self.assertIsNone(case.service)

    def test_real_host_selection_keeps_windows_native_and_posix_cases_separate(self):
        for system in ("Linux", "Darwin", "Windows"):
            selected = public_smoke.cases(system)
            self.assertEqual(len(selected), len(set(selected)))
            self.assertTrue(set(public_smoke.COMMON) <= set(selected))
            expected = public_smoke.WINDOWS if system == "Windows" else public_smoke.POSIX
            excluded = public_smoke.POSIX if system == "Windows" else public_smoke.WINDOWS
            self.assertTrue(set(expected) <= set(selected))
            self.assertFalse(set(excluded) & set(selected))
            self.assertFalse(any("numpy" in name.lower() for name in selected))
        with self.assertRaises(ValueError):
            public_smoke.cases("unsupported")

    def test_skips_missing_cases_empty_suites_and_real_assertions_do_not_pass(self):
        module = types.ModuleType("public_smoke_fixture")

        class Cases(unittest.TestCase):
            def test_pass(self):
                pass

            def test_failure(self):
                self.fail("Synthetic behavior regressed")

            @unittest.skip("Missing required host capability")
            def test_skipped(self):
                pass

            @unittest.expectedFailure
            def test_expected_failure(self):
                self.fail("A required host behavior is still broken")

            @unittest.expectedFailure
            def test_unexpected_success(self):
                pass

        class Empty(unittest.TestCase):
            pass

        module.Cases, module.Empty = Cases, Empty
        with patch.dict(sys.modules, {module.__name__: module}):
            for name, passed in (
                ("Cases.test_pass", True),
                ("Cases.test_failure", False),
                ("Cases.test_skipped", False),
                ("Cases.test_expected_failure", False),
                ("Cases.test_unexpected_success", False),
                ("Cases.test_missing", False),
                ("Empty", False),
            ):
                result = public_smoke.run_cases([module.__name__ + "." + name], io.StringIO())
                self.assertEqual(result["passed"], passed, result)
                if name == "Cases.test_expected_failure":
                    self.assertEqual(len(result["expected_failures"]), 1)
                if name == "Cases.test_unexpected_success":
                    self.assertEqual(len(result["unexpected_successes"]), 1)
            with self.assertRaises(ValueError):
                public_smoke.run_cases([])

    def test_wrong_matrix_platform_is_rejected_before_cases_or_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "not-created.json"
            with (
                patch.object(public_smoke.platform, "system", return_value="Windows"),
                patch.object(public_smoke.platform, "machine", return_value="AMD64"),
                patch.object(public_smoke, "run_cases") as execute,
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as failure,
            ):
                public_smoke.main(["--expected-platform", "darwin-arm64", "--output", str(output)])
            self.assertEqual(failure.exception.code, 2)
            execute.assert_not_called()
            self.assertFalse(output.exists())

    def test_existing_receipt_is_preserved_and_refused_before_running_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            output.write_bytes(b"preserve previous evidence")
            with (
                patch.object(public_smoke, "run_cases") as execute,
                redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as failure,
            ):
                public_smoke.main(["--output", str(output)])
            self.assertEqual(failure.exception.code, 2)
            execute.assert_not_called()
            self.assertEqual(output.read_bytes(), b"preserve previous evidence")


if __name__ == "__main__":
    unittest.main()
