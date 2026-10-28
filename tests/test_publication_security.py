"""Check public installer refusal, CI scope, rights notices and reviewed locks."""

import hashlib
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

import yaml
from packaging.specifiers import SpecifierSet

from experiments.setup.publication import check_install
from scripts.publication_ci_scope import native_enabled

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DISPATCH = (
    "github.event.repository.private && github.event_name == 'workflow_dispatch' "
    "&& inputs.historical_native"
)


class PublicSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "publication-snapshot.json").write_text("{}")
        self.policy = json.loads((ROOT / "publication-security.json").read_text())
        self.policy_path = self.root / "publication-security.json"
        self.policy_path.write_text(json.dumps(self.policy))

    def test_all_affected_environments_and_unknown_projects_are_refused(self):
        projects = [*self.policy["blocked_historical_projects"], "unreviewed/runtime"]
        self.assertEqual(len(self.policy["blocked_historical_projects"]), 6)
        for project in projects:
            with self.subTest(project=project):
                with self.assertRaisesRegex(ValueError, "excludes historical"):
                    check_install(self.root, [".", project])
        check_install(self.root, ["."])

    def test_missing_or_malformed_policy_fails_closed(self):
        for content in ("not-json", "{}", '{"schema":"unknown"}'):
            self.policy_path.write_text(content)
            with self.assertRaisesRegex(ValueError, "requires a valid"):
                check_install(self.root, ["."])
        self.policy_path.unlink()
        with self.assertRaisesRegex(ValueError, "requires a valid"):
            check_install(self.root, ["."])

    def test_historical_ci_requires_explicit_request_and_private_non_snapshot_archive(self):
        for private in (True, False):
            for requested in (True, False):
                self.assertFalse(
                    native_enabled(
                        self.root, private_repository=private, historical_requested=requested
                    )
                )
        (self.root / "publication-snapshot.json").unlink()
        for private, requested in ((False, False), (True, False), (False, True)):
            self.assertFalse(
                native_enabled(
                    self.root, private_repository=private, historical_requested=requested
                )
            )
        self.assertTrue(
            native_enabled(self.root, private_repository=True, historical_requested=True)
        )

    def test_workflow_and_public_branch_policy_enforce_supported_scope(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        jobs = workflow["jobs"]
        for key, job in jobs.items():
            if key != "repository-checks":
                self.assertEqual(job["needs"], "repository-checks")
                self.assertEqual(
                    job["if"],
                    PRIVATE_DISPATCH
                    + " && needs.repository-checks.outputs.native_enabled == 'true'",
                )
        for step in jobs["repository-checks"]["steps"]:
            if "--project experiments/" in step.get("run", ""):
                self.assertEqual(
                    step["if"],
                    PRIVATE_DISPATCH + " && steps.scope.outputs.native_enabled == 'true'",
                )
        for step in jobs["repository-checks"]["steps"]:
            if "native_enabled" in step.get("if", ""):
                expected = PRIVATE_DISPATCH + " && steps.scope.outputs.native_enabled == 'true'"
                if step.get("uses", "").startswith("actions/upload-artifact@"):
                    expected = "always() && " + expected
                self.assertEqual(step["if"], expected)
        dispatch = workflow["on"]["workflow_dispatch"]["inputs"]["historical_native"]
        self.assertFalse(dispatch["default"])
        public = json.loads((ROOT / ".github/public-source-branch-protection.json").read_text())
        self.assertEqual(
            public["required_status_checks"]["checks"],
            [{"context": "Repository checks", "app_id": 15368}],
        )
        installer = yaml.safe_load((ROOT / ".github/workflows/windows-installer.yml").read_text())
        self.assertEqual(set(installer["on"]), {"workflow_dispatch"})
        self.assertEqual(
            installer["jobs"]["build-and-verify-payload"]["if"], "github.event.repository.private"
        )
        self.assertTrue(public["enforce_admins"])
        self.assertFalse(public["allow_force_pushes"])
        self.assertFalse(public["allow_deletions"])

    def test_reviewed_advisories_do_not_affect_root_tooling_and_native_coverage_is_complete(self):
        packages = {
            item["name"].lower(): item["version"]
            for item in tomllib.loads((ROOT / "uv.lock").read_text())["package"]
            if "version" in item
        }
        affected_projects = set()
        for advisory in self.policy["advisories"]:
            package = advisory["package"]
            if package in packages:
                self.assertNotIn(packages[package], SpecifierSet(advisory["affected_range"]))
            affected_projects.update(
                str(Path(name).parent) for name in advisory["base_manifests"] if "/" in name
            )
        self.assertEqual(affected_projects, set(self.policy["blocked_historical_projects"]))
        self.assertEqual(len({a["id"] for a in self.policy["advisories"]}), 50)

    def test_distributed_notices_and_redacted_records_match_the_reviewed_inventory(self):
        rights = json.loads((ROOT / "publication-rights.json").read_text())
        for notice in rights["notices"]:
            with self.subTest(asset=notice["asset"]):
                self.assertEqual(
                    hashlib.sha256((ROOT / notice["notice"]).read_bytes()).hexdigest(),
                    notice["sha256"],
                )
        mapping = json.loads((ROOT / "publication-source-map.json").read_text())
        for record in mapping["files"]:
            self.assertEqual(
                hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest(),
                record["published_sha256"],
            )
        for project in ("profile_likelihood", "volume_sensitivity"):
            data = json.loads((ROOT / f"experiments/m4/{project}/execution.json").read_text())
            fragment = data["runtime_and_native_identity"]["parameters"]
            self.assertTrue(fragment["publication_omitted"])
            self.assertNotIn("BW", fragment)
            self.assertNotIn("Vg", fragment)


if __name__ == "__main__":
    unittest.main()
