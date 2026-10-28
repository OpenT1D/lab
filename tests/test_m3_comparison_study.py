"""Separate child execution, metadata freeze, interruption and saved semantic checks."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.m3.common import ROOT, digest, encoded, read, save
from experiments.m3.comparison.common import SCHEMA, check, metadata
from experiments.m3.comparison.fixtures import fixture
from experiments.m3.comparison.study import markdown, reconstruct, run_study, seal
from experiments.m3.external.fixtures import generate
from experiments.m3.researcher.fixtures import write_predictor

PERSISTENCE = """def predict(request, settings):
    return request["values_mg_dl"][-1] + settings.get("offset", 0)
"""


def configuration(root, *, second_source=PERSISTENCE, people=2, days=2):
    root = Path(root).absolute()
    root.mkdir()
    registry = generate(root / "observations", people=people, days=days)
    candidates = []
    for identity, source, settings in (
        ("first", PERSISTENCE, {"offset": 1}),
        ("second", second_source, {"offset": 2}),
    ):
        declaration = write_predictor(
            root / identity,
            source,
            settings,
            name=identity,
            reference="Invented comparison verification; no training or human evidence",
        )
        candidates.append({"id": identity, "declaration": str(declaration)})
    config = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "source": registry["source"],
        "prior_access": registry["prior_access"],
        "people": registry["people"],
        "candidates": candidates,
        "timeout_seconds": 10,
    }
    save(root / "comparison.json", config)
    return root / "comparison.json", config


class FailedProcess:
    pid = -1

    def poll(self):
        return 1

    def wait(self, timeout=None):
        return 1


class ComparisonStudyTests(unittest.TestCase):
    def test_metadata_check_neither_imports_source_nor_opens_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            marker = folder / "imported"
            source = f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + PERSISTENCE
            path, config = configuration(folder / "prepare", second_source=source)
            for person in config["people"]:
                Path(person["input"]["file"]).unlink()
            result = check(path)
            self.assertEqual(result["candidate_order"], ["first", "second"])
            self.assertFalse(result["observation_bytes_verified"])
            self.assertFalse(result["candidate_executed"])
            self.assertFalse(marker.exists())
            config["candidates"][1]["id"] = "persistence"
            save(path, config)
            with self.assertRaises(ValueError):
                metadata(path)

    def test_plan_all_snapshots_precede_first_child_and_missing_archives_remain_null(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path, config = configuration(folder / "prepare")
            output = folder / "study"
            seen = []
            native_popen = subprocess.Popen

            def launch(*args, **kwargs):
                if args[0][0] == "git":
                    return native_popen(*args, **kwargs)
                plan, _ = read(output / "plan.json")
                self.assertEqual(list(plan["config"]["candidates"]), config["candidates"])
                for candidate in config["candidates"]:
                    self.assertTrue((output / "frozen" / candidate["id"] / "source.py").exists())
                seen.append(args[0])
                return FailedProcess()

            with patch("experiments.m3.comparison.study.subprocess.Popen", side_effect=launch):
                report = run_study(path, output)
            self.assertEqual(len(seen), 2)
            self.assertEqual(report["common"]["planned_people"], 2)
            self.assertEqual(report["common"]["contributing_people"], 0)
            self.assertIsNone(report["common"]["contrasts"][0]["mean_person_mae_difference"])
            for candidate in report["candidates"].values():
                self.assertIsNone(candidate["single_candidate"])
                self.assertEqual(candidate["coordinator"]["status"], "failed")
                self.assertIsNotNone(candidate["missing_archive_reason"])
            self.assertEqual(reconstruct(output), report)
            original_state, _ = read(output / "state.json")
            changed_state = json.loads(json.dumps(original_state))
            changed_state["candidates"]["first"].update(
                status="interrupted", error_type="GlobalInterruption"
            )
            # Otherwise valid failed parent, one failed attempt, no global signal:
            # an interrupted coordinator attempt is impossible in that state.
            save(output / "state.json", changed_state)
            seal(output)
            with self.assertRaisesRegex(ValueError, "Interrupted candidate lacks global"):
                reconstruct(output)
            save(output / "state.json", original_state)
            seal(output)
            self.assertEqual(reconstruct(output), report)

    def test_real_workers_repeat_reconstruct_after_original_locations_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path, config = configuration(folder / "prepare")
            self.assertEqual(
                (folder / "prepare/first/source.py").read_bytes(), PERSISTENCE.encode("utf-8")
            )
            first = run_study(path, folder / "first")
            second = run_study(path, folder / "repeat")
            self.assertEqual(
                (folder / "first/report.md").read_bytes(), markdown(first).encode("utf-8")
            )
            self.assertTrue(first["common"]["complete_cohort"])
            self.assertEqual(first["common"], second["common"])
            for candidate in config["candidates"]:
                for person in config["people"]:
                    relative = (
                        Path("children") / candidate["id"] / "cases" / person["id"] / "trace.jsonl"
                    )
                    self.assertEqual(
                        (folder / "first" / relative).read_bytes(),
                        (folder / "repeat" / relative).read_bytes(),
                    )
            shutil.rmtree(folder / "prepare")
            self.assertEqual(reconstruct(folder / "first", folder / "rebuilt"), first)
            for name in ("report.json", "report.md"):
                self.assertEqual(
                    (folder / "first" / name).read_bytes(), (folder / "rebuilt" / name).read_bytes()
                )

    def test_existing_trend_and_ridge_structures_execute_on_identical_support(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            fixture(folder / "fixture")
            report = run_study(folder / "fixture/comparison.json", folder / "study")
            self.assertTrue(report["common"]["complete_cohort"])
            self.assertEqual(report["common"]["planned_people"], 2)
            self.assertEqual(len(report["common"]["contrasts"]), 3)
            for person in report["common"]["people"].values():
                self.assertEqual(len(set(person["candidate_scored"].values())), 1)

    def test_worker_exception_preserves_other_candidate_and_full_denominators(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = """def predict(request, settings):
    if request["origin_us"] >= 90 * 60_000_000:
        raise KeyboardInterrupt()
    return request["values_mg_dl"][-1]
"""
            path, config = configuration(folder / "prepare", second_source=source)
            report = run_study(path, folder / "study")
            self.assertEqual(report["candidates"]["first"]["coordinator"]["status"], "finished")
            self.assertEqual(report["candidates"]["second"]["coordinator"]["status"], "finished")
            self.assertEqual(
                report["candidates"]["second"]["coordinator"]["comparison_status"], "finished"
            )
            self.assertEqual(report["common"]["contributing_people"], 0)
            self.assertEqual(report["common"]["planned_people"], len(config["people"]))
            for case in report["common"]["people"].values():
                self.assertEqual(case["candidate_statuses"]["second"], "failed")
                self.assertGreater(
                    case["candidate_scored"]["first"], case["candidate_scored"]["second"]
                )
            self.assertEqual(reconstruct(folder / "study"), report)

    def test_final_boundary_signal_preserves_completed_children_and_parent_interruption(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path, _ = configuration(folder / "prepare", people=1)
            original_signal = signal.signal
            installed = {}
            injected = False

            def handler_transition(signum, handler):
                nonlocal injected
                if signum not in installed:
                    installed[signum] = handler
                elif signum == signal.SIGINT and not injected:
                    # Deliver cancellation after the final child completes, exactly when
                    # the parent hands control back to the user's original handlers.
                    installed[signum](int(signum), None)
                    injected = True
                return original_signal(signum, handler)

            with patch(
                "experiments.m3.comparison.study.signal.signal", side_effect=handler_transition
            ):
                report = run_study(path, folder / "study")
            self.assertTrue(injected)
            self.assertTrue(report["common"]["complete_cohort"])
            for candidate in report["candidates"].values():
                self.assertEqual(candidate["coordinator"]["status"], "finished")
                self.assertEqual(candidate["coordinator"]["comparison_status"], "interrupted")
                self.assertEqual(
                    candidate["coordinator"]["interruption_signal"], int(signal.SIGINT)
                )
            self.assertEqual(reconstruct(folder / "study"), report)

    def test_resealed_parent_state_contradictions_fail_semantically(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path, _ = configuration(folder / "prepare", people=1)
            run_study(path, folder / "study")
            original, _ = read(folder / "study/state.json")
            mutations = [
                lambda state: state["candidates"]["first"].update(
                    status="not_attempted", exit_code=None
                ),
                lambda state: state["candidates"]["first"].update(status="failed"),
                lambda state: state.update(status="failed"),
                lambda state: state.update(status="interrupted"),
            ]
            for mutate in mutations:
                state = json.loads(json.dumps(original))
                mutate(state)
                save(folder / "study/state.json", state)
                seal(folder / "study")
                with self.subTest(state=state), self.assertRaises(ValueError):
                    reconstruct(folder / "study")
            save(folder / "study/state.json", original)
            seal(folder / "study")
            reconstruct(folder / "study")

    def test_resealed_child_phase_budget_or_source_mismatch_is_rejected(self):
        from experiments.m3.researcher.study import reconstruct as child_reconstruct
        from experiments.m3.researcher.study import seal as child_seal

        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            path, _ = configuration(folder / "prepare", people=1)
            run_study(path, folder / "study")
            child = folder / "study/children/second"
            original, _ = read(child / "plan.json")
            original_source = (child / "predictor/source.py").read_bytes()
            for change in ("budget", "prior_access", "source"):
                plan = json.loads(json.dumps(original))
                source = original_source
                if change == "budget":
                    plan["timeout_seconds"] += 1
                elif change == "prior_access":
                    plan["config"]["prior_access"]["reference"] += " changed"
                    plan["config_sha256"] = digest(encoded(plan["config"]))
                else:
                    source += b"\n# Independently resealed different candidate bytes\n"
                    plan["predictor"]["source"]["sha256"] = digest(source)
                (child / "predictor/source.py").write_bytes(source)
                save(child / "predictor/declaration.json", plan["predictor"])
                save(child / "plan.json", plan)
                child_seal(child)
                # The unchanged child reader accepts each internally consistent archive.
                # Parent freezing must still reject its different phase, budget or model.
                child_reconstruct(child, write_to=child)
                seal(folder / "study")
                with self.subTest(change=change), self.assertRaises(ValueError):
                    reconstruct(folder / "study")
            (child / "predictor/source.py").write_bytes(original_source)
            save(child / "predictor/declaration.json", original["predictor"])
            save(child / "plan.json", original)
            child_seal(child)
            child_reconstruct(child, write_to=child)
            seal(folder / "study")
            reconstruct(folder / "study")

    def test_local_deadline_does_not_stop_later_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = """import time
def predict(request, settings):
    time.sleep(3)
    return request["values_mg_dl"][-1]
"""
            path, config = configuration(folder / "prepare", second_source=source, people=1)
            config["candidates"].reverse()
            config["timeout_seconds"] = 1
            save(path, config)
            report = run_study(path, folder / "study")
            self.assertEqual(report["candidates"]["second"]["coordinator"]["status"], "finished")
            self.assertEqual(report["candidates"]["first"]["coordinator"]["status"], "finished")
            self.assertEqual(
                report["candidates"]["first"]["coordinator"]["comparison_status"], "finished"
            )
            self.assertIsNone(report["candidates"]["first"]["coordinator"]["interruption_signal"])
            case = next(iter(report["common"]["people"].values()))
            self.assertEqual(case["candidate_statuses"]["second"], "interrupted")
            self.assertEqual(case["candidate_statuses"]["first"], "completed")
            self.assertGreater(case["candidate_scored"]["first"], 0)
            self.assertEqual(report["common"]["contributing_people"], 0)
            self.assertEqual(reconstruct(folder / "study"), report)

    @unittest.skipUnless(os.name == "posix", "Real signal forwarding needs POSIX")
    def test_sighup_cancels_active_supervisor_and_retains_unattempted_candidate_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            marker = folder / "active-predictor.pid"
            source = f"""import os
import time
from pathlib import Path
def predict(request, settings):
    Path({str(marker)!r}).write_text(str(os.getpid()))
    time.sleep(60)
    return request["values_mg_dl"][-1]
"""
            path, config = configuration(folder / "prepare", second_source=source, people=1)
            # Make the waiting source first so the second frozen candidate remains untouched.
            config["candidates"].reverse()
            save(path, config)
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-S",
                    "-m",
                    "experiments.m3.comparison",
                    "run",
                    "--config",
                    str(path),
                    "--output",
                    str(folder / "study"),
                ],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 10
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), "Predictor did not start")
                predictor_pid = int(marker.read_text())
                child.send_signal(signal.SIGHUP)
                self.assertEqual(child.wait(timeout=15), 1)
                report = reconstruct(folder / "study")
                self.assertEqual(
                    report["candidates"]["first"]["coordinator"]["status"], "not_attempted"
                )
                self.assertEqual(
                    report["candidates"]["second"]["coordinator"]["comparison_status"],
                    "interrupted",
                )
                self.assertEqual(
                    report["candidates"]["second"]["coordinator"]["interruption_signal"],
                    int(signal.SIGHUP),
                )
                self.assertFalse((folder / "study/children/first").exists())
                self.assertEqual(report["common"]["contributing_people"], 0)
                active = subprocess.run(
                    ["ps", "-p", str(predictor_pid), "-o", "stat="],
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                self.assertTrue(not active or active.startswith("Z"))
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    unittest.main()
