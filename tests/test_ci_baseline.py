"""Public CI retains failure authority, explicit tools and narrowly scoped evidence."""

import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts import ci_environment
from scripts.check import run

ROOT = Path(__file__).resolve().parents[1]


class CIBaselinePolicyTests(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        self.job = self.workflow["jobs"]["repository-checks"]
        self.steps = {step["name"]: step for step in self.job["steps"]}

    def test_public_job_keeps_its_name_scope_and_explicit_uncached_toolchain(self):
        self.assertEqual(len(self.workflow["jobs"]), 16)
        self.assertEqual(self.job["name"], "Repository checks")
        self.assertNotIn("if", self.job)
        self.assertEqual(self.job["runs-on"], "ubuntu-24.04")
        self.assertEqual(self.job["timeout-minutes"], 15)
        self.assertEqual(self.job["defaults"]["run"]["shell"], "bash")
        self.assertEqual((ROOT / ".python-version").read_text().strip(), "3.12")
        self.assertEqual(self.steps["Install selected Python"]["run"], "uv python install")
        self.assertEqual(
            self.steps["Set up uv"]["with"], {"version": "0.11.16", "enable-cache": False}
        )
        node = self.steps["Set up required frontend Node"]
        self.assertEqual(
            node["uses"], "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1"
        )
        self.assertEqual(node["with"], {"node-version": "24.22.1", "package-manager-cache": False})
        self.assertNotIn("continue-on-error", self.job)
        self.assertTrue(all("continue-on-error" not in step for step in self.job["steps"]))
        evidence = self.steps["Preserve public check diagnostics including failures"]
        self.assertEqual(evidence["if"], "always()")
        self.assertEqual(evidence["with"]["retention-days"], 5)
        self.assertEqual(
            evidence["with"]["path"].splitlines(), ["results/ci/*.log", "results/ci/*.json"]
        )
        self.assertIn(
            "uv run --locked python scripts/check.py",
            self.steps["Check repository and build documentation"]["run"],
        )
        for name, job in self.workflow["jobs"].items():
            if name != "repository-checks":
                for step in job["steps"]:
                    if step.get("uses", "").startswith("actions/setup-node@"):
                        self.assertEqual(step["with"]["node-version"], "22.22.2")

    def test_selected_action_payload_allows_exactly_the_checked_in_revisions(self):
        uses = set()
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            workflow = yaml.safe_load(path.read_text())
            self.assertEqual(workflow["permissions"], {"contents": "read"})
            self.assertNotIn("pull_request_target", workflow["on"])
            self.assertNotIn("workflow_run", workflow["on"])
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[^@*]+@[0-9a-f]{40}$")
                        uses.add(step["uses"])
                    if step.get("uses", "").startswith("actions/checkout@"):
                        self.assertFalse(step["with"]["persist-credentials"])
        selected = json.loads((ROOT / ".github/public-source-selected-actions.json").read_text())
        self.assertFalse(selected["github_owned_allowed"])
        self.assertFalse(selected["verified_allowed"])
        self.assertEqual(set(selected["patterns_allowed"]), uses)
        self.assertEqual(len(selected["patterns_allowed"]), 5)
        self.assertEqual(
            json.loads((ROOT / ".github/public-source-actions-permissions.json").read_text()),
            {"enabled": True, "allowed_actions": "selected", "sha_pinning_required": True},
        )

    @unittest.skipUnless(shutil.which("bash"), "Hosted Ubuntu log pipelines require Bash")
    def test_logged_failure_stays_failed_and_preserves_diagnostics(self):
        command = self.steps["Check repository and build documentation"]["run"]
        failing = shlex.join(
            [sys.executable, "-c", "print('synthetic failure');raise SystemExit(7)"]
        )
        command = command.replace("uv run --locked python scripts/check.py", failing)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "results/ci").mkdir(parents=True)
            completed = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", command],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 7)
            self.assertIn(
                "synthetic failure", (root / "results/ci/repository-checks.log").read_text()
            )

    @unittest.skipUnless(shutil.which("bash"), "Hosted Ubuntu log pipelines require Bash")
    def test_first_paired_failure_cannot_be_hidden_by_a_successful_final_compare(self):
        command = self.steps["Verify paired boundary preflight and reconstruction"]["run"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "bin"
            tools.mkdir()
            (root / "results/ci").mkdir(parents=True)
            uv = tools / "uv"
            uv.write_text(
                "#!/bin/sh\n"
                'if [ "$FAIL_FIRST" = 1 ]; then\n'
                ' case "$*" in *"--output results/m4-paired/ci-reference"*)\n'
                "  echo 'synthetic first paired failure'; exit 7;; esac\n"
                "fi\nexit 0\n"
            )
            compare = tools / "cmp"
            compare.write_text('#!/bin/sh\necho success > "$COMPARE_MARKER"\nexit 0\n')
            for executable in (uv, compare):
                executable.chmod(0o700)
            marker = root / "compared"
            for fail_first in (False, True):
                marker.unlink(missing_ok=True)
                with self.subTest(fail_first=fail_first):
                    completed = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", command],
                        cwd=root,
                        env={
                            **os.environ,
                            "PATH": str(tools) + os.pathsep + os.environ.get("PATH", ""),
                            "FAIL_FIRST": str(int(fail_first)),
                            "COMPARE_MARKER": str(marker),
                        },
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(completed.returncode, 7 if fail_first else 0)
                    self.assertEqual(marker.exists(), not fail_first)
                    if fail_first:
                        self.assertIn(
                            "synthetic first paired failure",
                            (root / "results/ci/paired-boundary.log").read_text(),
                        )


class CIDiagnosticTests(unittest.TestCase):
    def test_environment_separates_source_event_and_pr_identity_without_dumping_secrets(self):
        versions = {"git": "a" * 40, "uv": "uv 0.11.16", "node": "v24.22.1"}

        def selected(tool, *args, **kwargs):
            return "" if tool == "git" and args[0] == "status" else versions[tool]

        with (
            patch.dict(
                os.environ,
                {"GITHUB_SHA": "b" * 40, "PR_HEAD_SHA": "c" * 40, "SECRET": "PRIVATE_SENTINEL"},
                clear=True,
            ),
            patch.object(ci_environment, "command", side_effect=selected),
        ):
            data = ci_environment.collect()
        self.assertEqual(data["source_sha"], "a" * 40)
        self.assertEqual(data["event_sha"], "b" * 40)
        self.assertEqual(data["pull_request_head_sha"], "c" * 40)
        self.assertFalse(data["source_dirty"])
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(data))

    def test_missing_node_is_an_error_in_required_environment_recording(self):
        def available(tool, *args, **kwargs):
            if tool == "node":
                raise FileNotFoundError("node")
            return "synthetic tool"

        with (
            patch.object(ci_environment, "command", side_effect=available),
            self.assertRaises(FileNotFoundError),
        ):
            ci_environment.collect()

    def test_timed_commands_preserve_success_and_failure_exit_outcomes(self):
        for code in (0, 7):
            output = io.StringIO()
            with self.subTest(exit_code=code), redirect_stdout(output):
                if code:
                    with self.assertRaises(subprocess.CalledProcessError) as failure:
                        run(sys.executable, "-c", "raise SystemExit(7)")
                    self.assertEqual(failure.exception.returncode, 7)
                else:
                    run(sys.executable, "-c", "pass")
            self.assertRegex(output.getvalue(), r"Elapsed: [0-9.]+ seconds")


if __name__ == "__main__":
    unittest.main()
