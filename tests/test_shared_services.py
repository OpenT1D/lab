"""Real offline workers, all-attempt storage, reader refusals and host ownership."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.catalogue.storage import digest, encoded, seal
from experiments.gui.ownership import ProcessTable
from experiments.shared_contracts.selected import FIXTURES
from experiments.shared_services import execution, routes, store


@unittest.skipUnless(os.name == "posix", "First project-service host boundary is POSIX")
class ProjectServices(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = store.create(self.root / "project", "invented study")

    def inputs(self, *, censored=False):
        return {
            "package.json": FIXTURES / "mmtt-package.json",
            "observations.csv": FIXTURES
            / ("mmtt-censored.csv" if censored else "mmtt-observations.csv"),
            "settings.json": FIXTURES / "mmtt-settings.json",
        }

    def freeze(self, project, *, censored=False):
        return routes.freeze(project, "mmtt-sensitivity", self.inputs(censored=censored))

    def controlled_command(self, mode, config, output):
        return [
            sys.executable,
            "-B",
            "-S",
            "-m",
            "tests.shared_service_worker",
            mode,
            str(config),
            str(output),
        ]

    def altered_copy(self, label):
        target = self.root / label
        shutil.copytree(self.project, target)
        return target

    def reseal(self, project, mutate):
        """Rehash a disposable whole ledger, to challenge semantic checks too."""
        previous = None
        for folder in sorted((project / "events").iterdir()):
            event = store.read(folder / "event.json")
            event["previous"] = previous
            mutate(event, folder)
            (folder / "event.json").write_bytes(encoded(event))
            (folder / "manifest.json").unlink()
            seal(folder)
            previous = digest((folder / "manifest.json").read_bytes())
        head = store.read(project / "HEAD.json")
        head["tip"] = previous
        (project / "HEAD.json").write_bytes(encoded(head))

    def test_real_mmtt_retry_complete_ledger_and_relocated_reader_bytes(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            original = copy.deepcopy(project.plans[plan][0])
            first = execution.execute(project, plan)
            with self.assertRaisesRegex(ValueError, "Explicit retry"):
                execution.execute(project, plan)
            second = execution.execute(project, plan, retry_of=first)
            self.assertEqual(project.attempts[second]["ordinal"], 2)
            self.assertEqual(project.plans[plan][0], original)
            self.assertEqual(len(project.finishes), 2)
            moved = project.relocate(self.root / "moved")
        shutil.rmtree(self.project)
        with store.opened(moved, write_access=True) as project:
            for number, attempt in enumerate((first, second)):
                result = execution.reconstruct(project, attempt, self.root / f"rebuilt-{number}")
                self.assertEqual(result["reconstruction"], "verified")
                self.assertEqual(result["completeness"], "complete")
                native = project.finishes[attempt][1] / "native"
                for name in ("report.json", "report.md"):
                    self.assertEqual(
                        (native / name).read_bytes(),
                        (self.root / f"rebuilt-{number}" / name).read_bytes(),
                    )
            descriptor, frozen = project.plans[plan]
            for name, path in self.inputs().items():
                self.assertEqual((frozen / "original" / name).read_bytes(), path.read_bytes())
            self.assertIn(
                "experiments/observation_analysis/__main__.py",
                descriptor["reader"]["reader_static_dependencies_sha256"],
            )

    def test_completed_but_incomplete_native_mmtt_retains_all_draws(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project, censored=True)
            attempt = execution.execute(project, plan)
            result = project.finishes[attempt][0]["result"]
            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(result["completeness"], "incomplete")
            self.assertEqual(set(result["slot_statuses"].values()), {"failed"})
            report = store.read(project.finishes[attempt][1] / "native/report.json")
            for variant in report["people"]["invented-01"]["variants"].values():
                self.assertEqual(variant["planned_draws"], 128)
                self.assertEqual(variant["attempted_draws"] + variant["not_attempted_draws"], 128)
            moved = project.relocate(self.root / "moved-incomplete")
        with store.opened(moved) as project:
            with self.assertRaisesRegex(ValueError, "allow_failed"):
                execution.reconstruct(project, attempt, self.root / "refused")
            execution.reconstruct(
                project, attempt, self.root / "incomplete-rebuilt", allow_failed=True
            )

    def test_real_signal_interrupt_native_mmtt_and_explicit_retry(self):
        cancel = threading.Event()
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)

            def command(_task, args):
                return self.controlled_command("mmtt-stop", args.config, args.output)

            def request_cancel():
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    logs = list((self.project / "work").glob("*/worker.log"))
                    if logs and b"analysis-ready" in logs[0].read_bytes():
                        cancel.set()
                        return
                    time.sleep(0.02)
                cancel.set()

            thread = threading.Thread(target=request_cancel)
            thread.start()
            try:
                with patch.object(execution, "command_for", side_effect=command):
                    attempt = execution.execute(project, plan, cancel=cancel)
            finally:
                thread.join(12)
            data, evidence = project.finishes[attempt]
            self.assertEqual(data["receipt"]["status"], "interrupted")
            self.assertEqual(data["result"]["execution_status"], "interrupted")
            self.assertEqual(set(data["result"]["slot_statuses"].values()), {"unavailable"})
            self.assertEqual(
                store.read(evidence / "native/report.json")["coverage"]["planned_variant_pairs"], 3
            )
            execution.reconstruct(
                project, attempt, self.root / "interrupted-rebuilt", allow_failed=True
            )
            retry = execution.execute(project, plan, retry_of=attempt)
            self.assertEqual(project.finishes[retry][0]["result"]["completeness"], "complete")

    def test_failed_launch_and_offline_recovery_preserve_forensics(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            with patch.object(
                execution, "spawn", side_effect=FileNotFoundError("controlled missing worker")
            ):
                failed = execution.execute(project, plan)
            self.assertEqual(project.finishes[failed][0]["result"]["payload"], "forensic")
            active, work = execution.begin(project, plan, retry_of=failed)
            (work / "partial.bin").write_bytes(b"forensic\x00\r\n")
        with store.opened(self.project, write_access=True) as project:
            self.assertNotIn(active, project.finishes)
            with self.assertRaisesRegex(ValueError, "unfinished execution"):
                execution.begin(project, plan, retry_of=failed)
            with self.assertRaisesRegex(ValueError, "confirmation"):
                execution.recover(project, active)
            with patch.object(
                execution.os, "killpg", side_effect=AssertionError("saved PID is not authority")
            ):
                execution.recover(project, active, execution_stopped=True)
            self.assertEqual(
                (project.finishes[active][1] / "partial.bin").read_bytes(), b"forensic\x00\r\n"
            )
            self.assertEqual(len(project.attempts), 2)
            with self.assertRaisesRegex(ValueError, "unavailable"):
                execution.reconstruct(project, active, self.root / "not-native", allow_failed=True)
            project.relocate(self.root / "forensic-moved")

    def test_refused_input_does_not_publish_or_poison_project(self):
        invalid = self.root / "invalid.json"
        package = json.loads(self.inputs()["package.json"].read_bytes())
        package["units"]["cpeptide"] = "unsupported"
        invalid.write_bytes(encoded(package))
        with store.opened(self.project, write_access=True) as project:
            before = dict(project.head)
            with self.assertRaises(ValueError):
                routes.freeze(
                    project, "mmtt-sensitivity", {**self.inputs(), "package.json": invalid}
                )
            project.inspect()
            self.assertEqual(project.head, before)
            self.freeze(project)

    def test_lost_swapped_duplicated_events_and_assets_fail_closed(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            one = execution.execute(project, plan)
            execution.execute(project, plan, retry_of=one)
        for label, mutate in (
            ("lost-last", lambda p: shutil.rmtree(sorted((p / "events").iterdir())[-1])),
            ("duplicate", lambda p: shutil.copytree(p / "events/00000002", p / "events/00000009")),
            (
                "asset",
                lambda p: (p / "events/00000002/plan/original/observations.csv").write_bytes(
                    b"changed"
                ),
            ),
            (
                "source",
                lambda p: (
                    p / "events/00000002/plan/trusted/experiments/observation_analysis/__main__.py"
                ).unlink(),
            ),
            ("attempt", lambda p: (p / "events/00000004/evidence/native/attempts.json").unlink()),
            ("unlisted", lambda p: (p / "events/00000002/plan/unlisted").write_bytes(b"extra")),
        ):
            changed = self.altered_copy(label)
            mutate(changed)
            with self.subTest(case=label), self.assertRaises((ValueError, OSError)):
                with store.opened(changed):
                    pass
        changed = self.altered_copy("swapped")
        first, second = changed / "events/00000003", changed / "events/00000005"
        first.rename(changed / "swap")
        second.rename(first)
        (changed / "swap").rename(second)
        with self.assertRaisesRegex(ValueError, "chain"):
            with store.opened(changed):
                pass

    def test_rehashed_runtime_reader_parent_and_slot_contradictions_refused(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project, censored=True)
            execution.execute(project, plan)
        for label, mutate in (
            ("ordinal", lambda e, f: e["data"].update(ordinal=2) if e["kind"] == "start" else None),
            (
                "parent",
                lambda e, f: e["data"].update(parent="0" * 64) if e["kind"] == "freeze" else None,
            ),
            (
                "slots",
                lambda e, f: (
                    e["data"]["result"].update(
                        slot_statuses=dict.fromkeys(
                            e["data"]["result"]["slot_statuses"], "complete"
                        )
                    )
                    if e["kind"] == "finish"
                    else None
                ),
            ),
        ):
            changed = self.altered_copy(label)
            self.reseal(changed, mutate)
            with self.subTest(case=label), self.assertRaises(ValueError):
                with store.opened(changed):
                    pass
        with store.opened(self.project) as project:
            descriptor, folder = project.plans[plan]
            changed = copy.deepcopy(descriptor)
            changed["reader"]["report_schema"] = "unknown/999"
            with self.assertRaisesRegex(ValueError, "freeze identity"):
                routes.validate_freeze(folder, changed, current=False)
            with patch.object(routes.mmtt, "runtime_identity", return_value={"changed": "runtime"}):
                with self.assertRaisesRegex(ValueError, "Execution runtime differs"):
                    routes.validate_freeze(folder, descriptor, current=True)

    def test_exclusive_lease_and_uncommitted_transaction_are_refused(self):
        with store.opened(self.project, write_access=True):
            with self.assertRaisesRegex(ValueError, "in use"):
                with store.opened(self.project, write_access=True):
                    pass
        (self.project / "pending/unfinished").mkdir()
        (self.project / "pending/unfinished/raw.txt").write_bytes(b"retain transaction evidence")
        with self.assertRaisesRegex(ValueError, "Uncommitted transaction"):
            with store.opened(self.project):
                pass
        self.assertTrue((self.project / "pending/unfinished/raw.txt").exists())

    def test_reader_and_export_refuse_dotdot_and_symlink_output_aliases(self):
        outside = self.root / "outside"
        outside.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(self.project, target_is_directory=True)
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            attempt = execution.execute(project, plan)
            for output in (outside / "../project/injected", alias / "injected"):
                for operation in (
                    lambda: execution.reconstruct(project, attempt, output),
                    lambda: project.relocate(output),
                ):
                    with self.subTest(output=output), self.assertRaises(ValueError):
                        operation()
                self.assertFalse((self.project / "injected").exists())
            project.inspect()

    def test_process_metadata_failure_never_invents_empty_cleanup(self):
        launched = []
        real_spawn = execution.spawn

        def recorded_spawn(*args, **kwargs):
            process = real_spawn(*args, **kwargs)
            launched.append(process)
            return process

        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
        )
        try:
            with store.opened(self.project, write_access=True) as project:
                plan = self.freeze(project)
                with (
                    patch.object(
                        execution,
                        "command_for",
                        return_value=[
                            sys.executable,
                            "-B",
                            "-S",
                            "-c",
                            "import time; time.sleep(60)",
                        ],
                    ),
                    patch.object(execution, "spawn", side_effect=recorded_spawn),
                    patch.object(
                        execution.Ownership,
                        "observe",
                        side_effect=ValueError("controlled metadata failure"),
                    ),
                    self.assertRaisesRegex(ValueError, "Owned processes remain"),
                ):
                    execution.execute(project, plan)
                self.assertIsNotNone(launched[0].poll())
                self.assertIsNone(unrelated.poll())
                self.assertEqual(len(project.attempts), 1)
                self.assertEqual(project.finishes, {})
                attempt = next(iter(project.attempts))
                receipt = store.read(self.project / "work" / attempt / "supervision.json")
                self.assertIsNone(receipt["remaining_owned_processes"])
                execution.recover(project, attempt, execution_stopped=True)
        finally:
            for process in launched:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
            unrelated.terminate()
            unrelated.wait(timeout=5)

    def test_reader_upgrade_refusal_and_archived_python_stays_opaque(self):
        with store.opened(self.project, write_access=True) as project:
            plan = self.freeze(project)
            attempt = execution.execute(project, plan)
            expected = routes.reader_identity("mmtt-sensitivity")
            with (
                patch.object(
                    routes,
                    "reader_identity",
                    return_value={**expected, "compatibility": "unknown-upgrade/2"},
                ),
                patch.object(
                    execution, "spawn", side_effect=AssertionError("no incompatible reader launch")
                ),
                self.assertRaisesRegex(ValueError, "reader version"),
            ):
                execution.reconstruct(project, attempt, self.root / "upgrade-refused")
            archive = project.finishes[attempt][1] / "native"
            copied = self.root / "imported-native"
            shutil.copytree(archive, copied)
            sentinel = self.root / "executed-marker"
            # Extra opaque provenance is data. No module, cwd or site path may
            # be selected from this imported archive, even when sealed.
            (copied / "sitecustomize.py").write_text(
                f"from pathlib import Path\nPath({str(sentinel)!r}).touch()\n"
            )
            (copied / "manifest.json").unlink()
            seal(copied)
            with patch.object(
                execution, "spawn", side_effect=AssertionError("import must be passive")
            ):
                imported = routes.import_attempt(project, plan, copied, retry_of=attempt)
            execution.reconstruct(project, imported, self.root / "opaque-rebuilt")
            self.assertFalse(sentinel.exists())

    def test_m4_derived_original_sources_and_controlled_failed_reader_relocation(self):
        with store.opened(self.project, write_access=True) as project:
            first = routes.freeze(
                project, "m4-study-secure", {"config.json": FIXTURES / "m4-fasting.json"}
            )
            derived = routes.freeze(
                project,
                "m4-study-secure",
                {"config.json": FIXTURES / "m4-gastric-15g.json"},
                parent=first,
            )
            descriptor, plan = project.plans[first]
            original = (plan / "original/config.json").read_bytes()
            self.assertEqual(original, (FIXTURES / "m4-fasting.json").read_bytes())
            self.assertNotEqual(original, (plan / "input/config.json").read_bytes())
            self.assertEqual(
                project.plans[derived][0]["boundary"]["planned_slots"],
                ["dalla_man/gastric_load_15g", "ultradian/gastric_load_15g"],
            )
            native = self.root / "m4-controlled-failed"
            completed = subprocess.run(
                self.controlled_command("m4-fail", plan / "input/config.json", native),
                cwd=routes.ROOT,
                capture_output=True,
                timeout=40,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            for label, missing in (
                ("missing-manifest", "manifest.json"),
                ("missing-model", "frozen/dalla_man/model.py"),
            ):
                invalid = self.root / label
                shutil.copytree(native, invalid)
                (invalid / missing).unlink()
                with self.subTest(case=label), self.assertRaises((ValueError, OSError, KeyError)):
                    routes.import_attempt(project, first, invalid)
            self.assertEqual(project.attempts, {})
            with patch.object(
                execution, "spawn", side_effect=AssertionError("import must be passive")
            ):
                attempt = routes.import_attempt(project, first, native)
            self.assertEqual(project.finishes[attempt][0]["result"]["execution_status"], "failed")
            self.assertEqual(
                set(project.finishes[attempt][0]["result"]["slot_statuses"].values()),
                {"unavailable"},
            )
            moved = project.relocate(self.root / "m4-moved")
        shutil.rmtree(self.project)
        with store.opened(moved) as project:
            with self.assertRaisesRegex(ValueError, "allow_failed"):
                execution.reconstruct(project, attempt, self.root / "m4-refused")
            execution.reconstruct(project, attempt, self.root / "m4-rebuilt", allow_failed=True)
            evidence = project.finishes[attempt][1] / "native"
            for name in ("report.json", "report.md", "figure.svg"):
                self.assertEqual(
                    (evidence / name).read_bytes(), (self.root / "m4-rebuilt" / name).read_bytes()
                )

    def test_real_nested_owned_process_deadline_crash_and_unrelated_preservation(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
        )
        self.addCleanup(lambda: unrelated.poll() is None and unrelated.kill())
        try:
            for mode in ("tree", "crash"):
                output = self.root / mode
                receipt = execution.supervise(
                    self.controlled_command(mode, self.root, output),
                    self.root / f"{mode}.log",
                    timeout=1.0,
                    grace=0.15,
                )
                self.assertEqual(receipt["status"], "failed")
                self.assertEqual(receipt["remaining_owned_processes"], [])
                child = int((output / "child.pid").read_text())
                self.assertIn(child, [p["pid"] for p in receipt["owned_processes"]])
                actual = ProcessTable().one(child)
                self.assertTrue(actual is None or not actual["alive"])
                self.assertIsNone(unrelated.poll())
                self.assertEqual(
                    (output / "partial.txt").read_bytes(), b"unfinished evidence\x00\r\n"
                )
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
