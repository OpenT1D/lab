"""Pages publishes only reviewed main output; PR HTML remains a read-only artifact."""

import itertools
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.stage_documentation import stage

ROOT = Path(__file__).resolve().parents[1]
MAIN = (
    "github.repository == 'OpenT1D/lab' && github.event_name == 'push'"
    " && github.ref == 'refs/heads/main'"
)
ARTIFACT = "github-pages-${{ github.run_id }}-${{ github.run_attempt }}"


def pages_condition(condition, values, *, inherited_success, workflow_cancelled=False):
    """Check the workflow's bounded conjunction, not GitHub's hosted scheduler."""
    clauses = condition.split(" && ")
    if (
        not any(clause in {"always()", "!cancelled()"} for clause in clauses)
        and not inherited_success
    ):
        return False  # GitHub applies success() when no status function is supplied.
    result = True
    for clause in clauses:
        if clause == "always()":
            continue
        if clause == "!cancelled()":
            result = result and not workflow_cancelled
            continue
        match = re.fullmatch(r"([a-z._-]+) == '([^']*)'", clause)
        if match is None or match[1] not in values:
            raise ValueError("Unsupported publication policy expression")
        actual = values[match[1]]
        result = result and isinstance(actual, str) and actual.casefold() == match[2].casefold()
    return result


class DocumentationStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "html"
        self.destination = self.root / "site"
        for name in ("index.html", "docs/index.html", "searchindex.js"):
            self.write(name, name.encode())

    def write(self, name, data):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_visible_downloads_assets_and_search_are_byte_exact_but_hidden_paths_absent(self):
        for name in ("_downloads/abc/protocol.ipynb", "_static/theme.css", "objects.inv"):
            self.write(name, b"\x00synthetic\xff")
        for name in (".buildinfo", ".doctrees/private.pickle", "docs/.hidden/secret"):
            self.write(name, b"not public")
        receipt = stage(self.source, self.destination)
        published = {
            p.relative_to(self.destination) for p in self.destination.rglob("*") if p.is_file()
        }
        self.assertEqual(len(published), 6)
        self.assertEqual(receipt["files"], 6)
        self.assertEqual(receipt["bytes"], sum((self.source / p).stat().st_size for p in published))
        for path in published:
            self.assertFalse(any(part.startswith(".") for part in path.parts))
            self.assertEqual(
                (self.source / path).read_bytes(), (self.destination / path).read_bytes()
            )

    def test_symlinks_hardlinks_and_special_files_fail_before_output_even_when_hidden(self):
        for kind in ("file_symlink", "directory_symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                bad = self.source / ".unsafe"
                if kind == "file_symlink":
                    bad.symlink_to(self.source / "index.html")
                elif kind == "directory_symlink":
                    bad.symlink_to(self.root, target_is_directory=True)
                elif kind == "hardlink":
                    os.link(self.source / "index.html", bad)
                elif hasattr(os, "mkfifo"):
                    os.mkfifo(bad)
                else:
                    continue
                try:
                    with self.assertRaises(ValueError):
                        stage(self.source, self.destination)
                    self.assertFalse(self.destination.exists())
                finally:
                    bad.unlink()

    def test_stale_destination_and_incomplete_output_are_not_published(self):
        self.destination.mkdir()
        sentinel = self.destination / "old.html"
        sentinel.write_bytes(b"preserve")
        with self.assertRaises(ValueError):
            stage(self.source, self.destination)
        self.assertEqual(sentinel.read_bytes(), b"preserve")
        sentinel.unlink()
        self.destination.rmdir()
        (self.source / "index.html").unlink()
        with self.assertRaises(ValueError):
            stage(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_source_alias_and_nested_destination_are_refused(self):
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        for source, destination in ((alias, self.destination), (self.source, self.source / "site")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                stage(source, destination)


class DocumentationWorkflowTests(unittest.TestCase):
    def test_pr_artifact_and_main_upload_share_one_filtered_successful_build(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        steps = workflow["jobs"]["repository-checks"]["steps"]
        names = [step.get("name") for step in steps]
        stage_step = next(
            step for step in steps if step.get("name") == "Stage public documentation"
        )
        self.assertEqual(
            stage_step["run"],
            "uv run --locked python scripts/stage_documentation.py _build/html _build/site",
        )
        self.assertLess(
            names.index("Check repository and build documentation"),
            names.index("Stage public documentation"),
        )
        preview = next(step for step in steps if step.get("name") == "Preserve pull request HTML")
        pages = next(
            step for step in steps if step.get("name") == "Upload trusted main Pages artifact"
        )
        self.assertEqual(preview["if"], "github.event_name == 'pull_request'")
        self.assertEqual(pages["if"], MAIN)
        for step in (preview, pages):
            self.assertEqual(step["with"]["path"], "_build/site")
            self.assertEqual(step["with"]["retention-days"], 1)
            self.assertFalse(step["with"]["include-hidden-files"])
            self.assertNotIn("continue-on-error", step)
        self.assertEqual(preview["with"]["if-no-files-found"], "error")
        self.assertEqual(pages["with"]["name"], ARTIFACT)

    def test_only_guarded_main_deployment_has_pages_or_identity_permissions(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(
            workflow["concurrency"]["cancel-in-progress"],
            "${{ github.event_name == 'pull_request' }}",
        )
        deploy = workflow["jobs"]["pages-deploy"]
        self.assertEqual(
            deploy["if"],
            "always() && !cancelled() && " + MAIN + " && needs.public-checks.result == 'success'",
        )
        self.assertEqual(deploy["needs"], ["public-checks"])
        self.assertNotIn("pages-deploy", workflow["jobs"]["public-checks"]["needs"])
        self.assertEqual(
            deploy["permissions"], {"contents": "read", "pages": "write", "id-token": "write"}
        )
        self.assertEqual(
            deploy["environment"],
            {"name": "github-pages", "url": "${{ steps.deployment.outputs.page_url }}"},
        )
        self.assertEqual(
            deploy["concurrency"], {"group": "github-pages", "cancel-in-progress": False}
        )
        self.assertEqual(len(deploy["steps"]), 1)
        action = deploy["steps"][0]
        self.assertEqual(
            action["uses"], "actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346"
        )
        self.assertEqual(action["with"], {"artifact_name": ARTIFACT})
        for name, job in workflow["jobs"].items():
            if name != "pages-deploy":
                self.assertEqual(
                    job.get("permissions", workflow["permissions"]), {"contents": "read"}
                )
                self.assertNotIn("environment", job)
        transitive = json.loads((ROOT / ".github/action-dependencies.json").read_text())
        self.assertEqual(
            transitive,
            {
                "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9": [
                    "actions/upload-artifact@bbbca2ddaa5d8feaa63e36b76fdaad77386f024f"
                ]
            },
        )

    def test_deploy_condition_rejects_untrusted_events_and_every_unsuccessful_aggregate(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/checks.yml").read_text())
        condition = workflow["jobs"]["pages-deploy"]["if"]
        for repository, event, ref, result, inherited, cancelled in itertools.product(
            ("OpenT1D/lab", "another/repository"),
            (
                "push",
                "pull_request",
                "pull_request_target",
                "workflow_dispatch",
                "workflow_run",
                None,
            ),
            ("refs/heads/main", "refs/heads/other", "refs/pull/21/merge", "refs/tags/main", None),
            ("success", "failure", "cancelled", "skipped", "neutral", "unknown", "", None),
            (True, False),
            (False, True),
        ):
            # The false inherited status models the observed legitimate PR-only
            # ancestor skip. Only the validated aggregate authorizes deployment.
            values = {
                "github.repository": repository,
                "github.event_name": event,
                "github.ref": ref,
                "needs.public-checks.result": result,
            }
            expected = (
                repository == "OpenT1D/lab"
                and event == "push"
                and ref == "refs/heads/main"
                and result == "success"
                and not cancelled
            )
            with self.subTest(**values, inherited_success=inherited, workflow_cancelled=cancelled):
                self.assertEqual(
                    pages_condition(
                        condition, values, inherited_success=inherited, workflow_cancelled=cancelled
                    ),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
