"""Real synthetic ledgers, omission controls and fail-closed diagnostic publication."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import digest, encoded, seal
from experiments.m3.comparison import fixtures as m3_fixtures
from experiments.m3.researcher.fixtures import write_predictor
from experiments.observation_analysis.run import run as run_mmtt
from experiments.shared_contracts.selected import FIXTURES
from experiments.shared_services import execution, routes, store
from scripts import export_project_diagnostics as diagnostics


@unittest.skipUnless(os.name == "posix", "Existing project store requires POSIX")
class ProjectDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="diagnostic-path-OMIT-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = store.create(self.root / "project", "project-name-OMIT")
        self.output = self.root / "diagnostics.json"

    def snapshot(self):
        return {
            path.relative_to(self.project).as_posix(): path.read_bytes()
            for path in self.project.rglob("*")
            if path.is_file()
        }

    def freeze(self, project, *, censored=False):
        return routes.freeze(
            project,
            "mmtt-sensitivity",
            {
                "package.json": FIXTURES / "mmtt-package.json",
                "observations.csv": FIXTURES
                / ("mmtt-censored.csv" if censored else "mmtt-observations.csv"),
                "settings.json": FIXTURES / "mmtt-settings.json",
            },
        )

    def export(self):
        before = self.snapshot()
        diagnostics.export(self.project, self.output)
        self.assertEqual(self.snapshot(), before)
        return json.loads(self.output.read_bytes())

    def refused(self, category="project_refused", *, output=None):
        output = self.output if output is None else output
        before = self.snapshot()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            code = diagnostics.main(["--project", str(self.project), "--output", str(output)])
        self.assertEqual(code, 1)
        self.assertEqual(stderr.getvalue(), category + "\n")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".project-diagnostics-*")))

    def test_empty_project_and_direct_checkout_command(self):
        before = self.snapshot()
        result = subprocess.run(
            [
                sys.executable,
                str(diagnostics.ROOT / "scripts/export_project_diagnostics.py"),
                "--project",
                str(self.project),
                "--output",
                str(self.output),
            ],
            cwd=self.root,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(
            json.loads(self.output.read_bytes()),
            {
                "schema": "opent1d.project-diagnostics/1",
                "exporter": "opent1d.export-project-diagnostics/1",
                "project_schema": "opent1d.project-store/1",
                "plans": 0,
                "attempts": 0,
                "tasks": [],
            },
        )

    def test_complete_failed_interrupted_unfinished_and_unattempted_counts(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            complete = execution.execute(project, plan)
            failed, work = execution.begin(project, plan, retry_of=complete)
            (work / "worker.log").write_text("log-text-OMIT")
            execution.finish(
                project,
                failed,
                work,
                {
                    "status": "failed",
                    "error": "error-text-OMIT",
                    "remaining_owned_processes": [],
                },
                forensic=True,
            )
            interrupted, _ = execution.begin(project, plan, retry_of=failed)
            execution.recover(project, interrupted, execution_stopped=True)
            unfinished, work = execution.begin(project, plan, retry_of=interrupted)
            (work / "partial.txt").write_text("partial-text-OMIT")
            # Even without its live workspace the durable start must be counted.
            shutil.rmtree(work)
            self.freeze(project)
        report = self.export()
        self.assertEqual((report["plans"], report["attempts"]), (2, 4))
        self.assertEqual(
            report["tasks"],
            [
                {
                    "task": "mmtt-sensitivity",
                    "plans": 2,
                    "plans_without_attempts": 1,
                    "attempts": 4,
                    "outcomes": [
                        {
                            "process_status": process,
                            "execution_status": status,
                            "completeness": completeness,
                            "count": 1,
                        }
                        for process, status, completeness in (
                            ("completed", "completed", "complete"),
                            ("failed", "failed", "incomplete"),
                            ("interrupted", "interrupted", "incomplete"),
                            ("unfinished", "unknown", "unknown"),
                        )
                    ],
                }
            ],
        )
        raw = self.output.read_text()
        for excluded in (
            str(self.root),
            "OMIT",
            complete,
            failed,
            interrupted,
            unfinished,
            "invented-01",
            "BC-003",
            "0.037",
            "report.json",
            "host",
            "argv",
        ):
            self.assertNotIn(excluded, raw)

    def test_completed_incomplete_native_result_and_different_process_status(self):
        with store.opened(self.project, write_access=True) as project:
            # Controlled coordinator receipts around real native evidence exercise
            # both supported combinations independently of the task CLI's exit policy.
            for censored, process_status in ((True, "completed"), (False, "failed")):
                plan = self.freeze(project, censored=censored)
                attempt, work = execution.begin(project, plan)
                run_mmtt(project.plans[plan][1] / "input", work / "native")
                execution.finish(
                    project,
                    attempt,
                    work,
                    {"status": process_status, "remaining_owned_processes": []},
                )
        outcomes = self.export()["tasks"][0]["outcomes"]
        self.assertEqual(
            outcomes,
            [
                {
                    "process_status": "completed",
                    "execution_status": "completed",
                    "completeness": "incomplete",
                    "count": 1,
                },
                {
                    "process_status": "failed",
                    "execution_status": "completed",
                    "completeness": "complete",
                    "count": 1,
                },
            ],
        )

    def test_repeated_failures_and_unfinished_workspace_are_all_counted(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            prior = None
            with patch.object(
                execution, "runtime_identity", return_value={"host": "host-text-OMIT"}
            ):
                for _ in range(2):
                    prior, work = execution.begin(project, plan, retry_of=prior)
                    execution.finish(
                        project,
                        prior,
                        work,
                        {"status": "failed", "remaining_owned_processes": []},
                        forensic=True,
                    )
                execution.begin(project, plan, retry_of=prior)
        task = self.export()["tasks"][0]
        self.assertEqual(task["attempts"], 3)
        self.assertEqual(task["plans_without_attempts"], 0)
        self.assertEqual([row["count"] for row in task["outcomes"]], [2, 1])
        self.assertEqual(
            [row["process_status"] for row in task["outcomes"]], ["failed", "unfinished"]
        )
        self.assertNotIn("OMIT", self.output.read_text())

    def test_supplied_model_and_sensitive_inputs_remain_inert_and_omitted(self):
        fixture = self.root / "fixture"
        config = m3_fixtures.fixture(fixture)
        sentinel = self.root / "model-was-executed"
        declaration = write_predictor(
            self.root / "model-path-OMIT",
            f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
            "def predict(request, settings): return 1.0\n",
            {"secret": "settings-value-OMIT"},
            name="candidate-OMIT",
            reference="reference-OMIT",
        )
        config["candidates"][0] = {"id": "candidate-OMIT", "declaration": str(declaration)}
        (fixture / "comparison.json").write_bytes(encoded(config))
        with store.opened(self.project, write_access=True) as project:
            routes.freeze(project, "m3-compare", {"config.json": fixture / "comparison.json"})
            self.freeze(project)
        popen = subprocess.Popen

        def passive_only(argv, *args, **kwargs):
            # Existing native validators inspect checkout provenance passively.
            self.assertIn(argv, (["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain"]))
            self.assertEqual(kwargs.get("cwd"), diagnostics.ROOT)
            return popen(argv, *args, **kwargs)

        with (
            patch.object(subprocess, "Popen", side_effect=passive_only),
            patch.object(execution, "recover", side_effect=AssertionError("No recovery")),
            patch.object(execution, "execute", side_effect=AssertionError("No task execution")),
            patch.object(execution, "reconstruct", side_effect=AssertionError("No reader command")),
        ):
            report = self.export()
        self.assertFalse(sentinel.exists())
        self.assertEqual(
            [row["task"] for row in report["tasks"]], ["m3-compare", "mmtt-sensitivity"]
        )
        self.assertTrue(all(row["plans_without_attempts"] == 1 for row in report["tasks"]))
        for excluded in ("OMIT", str(self.root), "predict", "values_mg_dl", "people", "origins_us"):
            self.assertNotIn(excluded, self.output.read_text())

    def reseal(self, mutate):
        previous = None
        for folder in sorted((self.project / "events").iterdir()):
            event = store.read(folder / "event.json")
            event["previous"] = previous
            mutate(event, folder)
            (folder / "event.json").write_bytes(encoded(event))
            (folder / "manifest.json").unlink()
            seal(folder)
            previous = digest((folder / "manifest.json").read_bytes())
        head = store.read(self.project / "HEAD.json")
        (self.project / "HEAD.json").write_bytes(encoded(head | {"tip": previous}))

    def test_corrupt_unknown_and_incompatible_projects_have_no_fallback(self):
        with store.opened(self.project, write_access=True) as project:
            self.freeze(project)
        control = self.root / "control"
        shutil.copytree(self.project, control)
        for case in ("bytes", "head", "event", "task", "reader", "pending"):
            with self.subTest(case=case):
                shutil.rmtree(self.project)
                shutil.copytree(control, self.project)
                if case == "bytes":
                    (self.project / "events/00000002/plan/original/observations.csv").write_bytes(
                        b"bad"
                    )
                elif case == "head":
                    head = store.read(self.project / "HEAD.json")
                    (self.project / "HEAD.json").write_bytes(encoded(head | {"schema": "unknown"}))
                elif case == "pending":
                    (self.project / "pending/uncommitted").write_text("pending-OMIT")
                else:

                    def mutate(event, folder):
                        if event["kind"] != "freeze":
                            return
                        if case == "event":
                            event["kind"] = "unknown"
                        elif case == "task":
                            event["data"]["descriptor"]["task"] = "unknown-OMIT"
                        else:
                            event["data"]["descriptor"]["reader"]["report_schema"] = "unknown-OMIT"
                        (folder / "plan/descriptor.json").write_bytes(
                            encoded(event["data"]["descriptor"])
                        )

                    self.reseal(mutate)
                self.refused()

    def test_writer_lock_refused_and_shared_reader_lease_retained(self):
        with store.opened(self.project, write_access=True):
            self.refused()
        original = diagnostics.summarize

        def summarize(project):
            self.assertFalse(project.writable)
            with store.opened(self.project):
                pass
            with self.assertRaises(ValueError), store.opened(self.project, write_access=True):
                pass
            return original(project)

        with patch.object(diagnostics, "summarize", side_effect=summarize):
            self.export()

    def test_unsafe_or_existing_outputs_refused_without_source_changes(self):
        existing = self.root / "existing.json"
        existing.write_bytes(b"existing-OMIT")
        directory = self.root / "directory"
        directory.mkdir()
        link = self.root / "linked.json"
        link.symlink_to(existing)
        dangling = self.root / "dangling.json"
        dangling.symlink_to(self.root / "absent")
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(directory, target_is_directory=True)
        fifo = self.root / "fifo"
        os.mkfifo(fifo)
        for output in (
            self.project / "diagnostics.json",
            self.project / "work/diagnostics.json",
            existing,
            directory,
            link,
            dangling,
            linked_parent / "out.json",
            fifo,
            self.root / "absent/out.json",
            existing / "out.json",
            self.root / "../out.json",
            self.root / "EXISTING.JSON",
        ):
            with self.subTest(output=output):
                self.refused("output_refused", output=output)
        self.assertEqual(existing.read_bytes(), b"existing-OMIT")
        self.assertEqual(list(directory.iterdir()), [])

    def test_failed_write_and_late_output_collision_publish_no_success(self):
        with patch.object(diagnostics.os, "fsync", side_effect=OSError("write-error-OMIT")):
            self.refused("output_refused")
        original = diagnostics.os.link

        def collide(source, target, **kwargs):
            self.output.write_bytes(b"late-existing-OMIT")
            original(source, target, **kwargs)

        before = self.snapshot()
        with patch.object(diagnostics.os, "link", side_effect=collide):
            with self.assertRaisesRegex(diagnostics.Refused, "^output_refused$"):
                diagnostics.export(self.project, self.output)
        self.assertEqual(self.output.read_bytes(), b"late-existing-OMIT")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.glob(".project-diagnostics-*")))

    def test_swapped_output_parent_never_writes_into_source(self):
        parent = self.root / "exports"
        parent.mkdir()
        backup = self.root / "old-exports"
        output = parent / "diagnostics.json"
        before = self.snapshot()
        original = os.open

        def swap(path, flags, *args, **kwargs):
            if flags & os.O_CREAT and str(path).startswith(".project-diagnostics-"):
                parent.rename(backup)
                self.project.rename(parent)
            return original(path, flags, *args, **kwargs)

        try:
            with patch.object(diagnostics.os, "open", side_effect=swap):
                with self.assertRaisesRegex(diagnostics.Refused, "^output_refused$"):
                    diagnostics.export(self.project, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(backup.iterdir()), [])
        finally:
            parent.rename(self.project)
            backup.rename(parent)
        self.assertEqual(self.snapshot(), before)
        with store.opened(self.project):
            pass

    def test_replaced_stage_cannot_publish_private_symlink(self):
        secret = self.root / "private.txt"
        secret.write_bytes(b"private-content-OMIT")
        original = diagnostics.os.fsync

        def replace_stage(descriptor):
            original(descriptor)
            [stage] = self.root.glob(".project-diagnostics-*")
            stage.unlink()
            stage.symlink_to(secret)

        before = self.snapshot()
        with patch.object(diagnostics.os, "fsync", side_effect=replace_stage):
            with self.assertRaisesRegex(diagnostics.Refused, "^output_refused$"):
                diagnostics.export(self.project, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(secret.read_bytes(), b"private-content-OMIT")
        # The substituted entry is not ours to delete.
        [stage] = self.root.glob(".project-diagnostics-*")
        self.assertTrue(stage.is_symlink())

    def test_replaced_final_entry_is_preserved_on_refusal(self):
        original = diagnostics.os.link

        def substitute(source, target, **kwargs):
            original(source, target, **kwargs)
            self.output.unlink()
            self.output.write_bytes(b"unrelated-existing-output")

        before = self.snapshot()
        with patch.object(diagnostics.os, "link", side_effect=substitute):
            with self.assertRaisesRegex(diagnostics.Refused, "^output_refused$"):
                diagnostics.export(self.project, self.output)
        self.assertEqual(self.output.read_bytes(), b"unrelated-existing-output")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(list(self.root.glob(".project-diagnostics-*")))

    def test_case_aliased_project_output_is_refused(self):
        alias = self.project.with_name(self.project.name.upper())
        if not alias.exists():
            self.skipTest("Filesystem has case-sensitive project names")
        self.assertTrue(alias.samefile(self.project))
        self.refused("output_refused", output=alias / "diagnostics.json")
        with store.opened(self.project):
            pass

    def test_missing_project_and_validator_errors_do_not_echo_details(self):
        for error in (FileNotFoundError("secret-path-OMIT"), AttributeError("input-text-OMIT")):
            with self.subTest(error=type(error).__name__):
                with patch.object(store, "opened", side_effect=error):
                    self.refused()
        missing = self.root / "not-a-project"
        with self.assertRaisesRegex(diagnostics.Refused, "^project_refused$"):
            diagnostics.export(missing, self.output)
        self.assertFalse(self.output.exists())

    def test_non_posix_host_is_explicitly_refused(self):
        with patch.object(diagnostics.os, "name", "nt"):
            with self.assertRaisesRegex(diagnostics.Refused, "^unsupported_host$"):
                diagnostics.export(self.project, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
