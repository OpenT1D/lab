"""Subprocess workflow, complete failures and semantic reconstruction regressions."""

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

from experiments.m3.azt1d.common import MINUTE
from experiments.m3.external.fixtures import generate
from experiments.m3.researcher.common import ROOT, SCHEMA, digest, read, save
from experiments.m3.researcher.fixtures import fixture, write_predictor
from experiments.m3.researcher.study import inventory, reconstruct, run_study, seal

PERSISTENCE_SOURCE = """def predict(request, settings):
    assert set(request) == {"origin_us", "times_us", "values_mg_dl"}
    assert request["times_us"] == [request["origin_us"] + offset * 60_000_000
                                   for offset in (-25, -20, -15, -10, -5, 0)]
    return request["values_mg_dl"][-1]
"""


def configuration(root, *, source=PERSISTENCE_SOURCE, settings=None, people=2, days=1):
    root = Path(root).resolve()
    root.mkdir()
    registry = generate(root / "observations", people=people, days=days)
    predictor = write_predictor(
        root / "predictor",
        source,
        {} if settings is None else settings,
        name="invented-integration-test",
        reference="Self-authored synthetic integration test, no training",
    )
    config = {
        "schema": SCHEMA,
        "kind": "synthetic",
        "source": registry["source"],
        "prior_access": registry["prior_access"],
        "predictor": str(predictor),
        "people": registry["people"],
    }
    path = root / "config.json"
    save(path, config)
    return path, config


def trace_rows(study, pid):
    return [
        json.loads(line)
        for line in (Path(study) / "cases" / pid / "trace.jsonl").read_text().splitlines()
    ]


def rewrite_trace(study, pid, rows):
    path = Path(study) / "cases" / pid / "trace.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def worker_arguments(study, pid):
    return [
        sys.executable,
        "-B",
        "-S",
        "-m",
        "experiments.m3.researcher.worker",
        str(study),
        pid,
    ]


def alive(pid):
    """A killed but unreaped orphan has no running work and counts as stopped."""
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=5
    )
    return bool(result.stdout.strip()) and not result.stdout.lstrip().startswith("Z")


class ResearcherStudyTests(unittest.TestCase):
    def test_full_public_fixture_uses_real_workers_and_retains_all_registered_origins(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            config = fixture(root / "fixture")
            report = run_study(root / "fixture/config.json", root / "study", timeout=10)
            evaluation = report["evaluation"]
            self.assertTrue(evaluation["complete_cohort"])
            self.assertEqual(evaluation["planned_people"], 2)
            self.assertEqual(evaluation["contributing_people"], 2)
            for person in config["people"]:
                case = evaluation["people"][person["id"]]
                rows = trace_rows(root / "study", person["id"])
                self.assertEqual(case["execution_status"], "completed")
                self.assertEqual(case["attempted"], len(person["origins_us"]))
                self.assertEqual(case["not_attempted"], 0)
                self.assertEqual([row["origin_us"] for row in rows], person["origins_us"])
                self.assertEqual(case["candidate"]["scored"], case["persistence"]["scored"])
                self.assertGreater(case["history_exclusions"]["history_unavailable"], 0)
                self.assertGreater(case["history_exclusions"]["history_gap"], 0)

    def test_missing_and_invalid_inputs_remain_in_roster_and_report(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation")
            Path(config["people"][0]["input"]["file"]).unlink()
            invalid = Path(config["people"][1]["input"]["file"])
            invalid.write_bytes(b'{"synthetic": "wrong normalized document"}\n')
            config["people"][1]["input"]["sha256"] = digest(invalid.read_bytes())
            save(path, config)
            report = run_study(path, root / "study", timeout=10)
            evaluation = report["evaluation"]
            self.assertEqual(evaluation["planned_people"], 2)
            self.assertEqual(evaluation["execution_status_counts"], {"failed": 2})
            for person in config["people"]:
                case = evaluation["people"][person["id"]]
                folder = root / "study/cases" / person["id"]
                self.assertEqual(case["execution"]["stage"], "input")
                self.assertEqual(case["attempted"], 0)
                self.assertEqual(case["not_attempted"], len(person["origins_us"]))
                self.assertEqual(case["candidate"]["predicted"], 0)
                self.assertTrue((folder / "input-access.json").is_file())
                self.assertFalse((folder / "worker-claim.json").exists())
            self.assertEqual(reconstruct(root / "study"), report)

    def test_shortened_origin_schedule_is_a_retained_input_failure(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation")
            config["people"][0]["origins_us"].pop(20)
            save(path, config)
            report = run_study(path, root / "study", timeout=10)
            cases = report["evaluation"]["people"]
            self.assertEqual(cases[config["people"][0]["id"]]["execution_status"], "failed")
            self.assertEqual(cases[config["people"][1]["id"]]["execution_status"], "completed")
            self.assertFalse(report["evaluation"]["complete_cohort"])

    def test_late_exception_and_nonfinite_result_preserve_exact_trace_prefix(self):
        for failure in ("raise TypeError('synthetic private marker')", "return float('nan')"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                source = (
                    "def predict(request, settings):\n"
                    f"    if request['origin_us'] >= {90 * MINUTE}:\n"
                    f"        {failure}\n"
                    "    return request['values_mg_dl'][-1]\n"
                )
                path, config = configuration(root / "preparation", source=source)
                report = run_study(path, root / "study", timeout=10)
                self.assertEqual(report["evaluation"]["execution_status_counts"], {"failed": 2})
                for person in config["people"]:
                    case = report["evaluation"]["people"][person["id"]]
                    rows = trace_rows(root / "study", person["id"])
                    self.assertEqual(case["attempted"], 18)
                    self.assertEqual(case["forecastable"], 6)
                    self.assertEqual(case["not_attempted"], len(person["origins_us"]) - 18)
                    self.assertEqual(rows[-1]["origin_us"], 85 * MINUTE)
                    self.assertFalse(case["eligible_for_primary"])
                    self.assertEqual(
                        case["execution"]["error_type"],
                        "TypeError" if failure.startswith("raise") else "ValueError",
                    )
                self.assertEqual(reconstruct(root / "study"), report)
                self.assertNotIn("synthetic private marker", (root / "study/report.md").read_text())

    def test_late_timeout_preserves_prefix_and_continues_full_roster(self):
        source = (
            "import time\n"
            "def predict(request, settings):\n"
            f"    if request['origin_us'] >= {90 * MINUTE}: time.sleep(30)\n"
            "    return request['values_mg_dl'][-1]\n"
        )
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", source=source)
            started = time.monotonic()
            report = run_study(path, root / "study", timeout=0.5)
            self.assertLess(time.monotonic() - started, 5)
            self.assertEqual(report["evaluation"]["execution_status_counts"], {"interrupted": 2})
            for person in config["people"]:
                case = report["evaluation"]["people"][person["id"]]
                self.assertEqual(case["attempted"], 18)
                self.assertEqual(case["execution"]["error_type"], "TimeoutExpired")
                self.assertFalse(case["eligible_for_primary"])
            self.assertEqual(reconstruct(root / "study"), report)

    def test_reconstruction_after_removing_originals_never_executes_retained_predictor(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            marker = root / "module-executed"
            source = f"open({str(marker)!r}, 'a').write('executed\\n')\n" + PERSISTENCE_SOURCE
            path, _ = configuration(root / "preparation", source=source)
            run_study(path, root / "study", timeout=10)
            self.assertTrue(marker.exists())
            marker.unlink()
            shutil.rmtree(root / "preparation")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-S",
                    "-m",
                    "experiments.m3.researcher",
                    "report",
                    "--study",
                    str(root / "study"),
                    "--output",
                    str(root / "reconstructed"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            for name in ("report.json", "report.md"):
                self.assertEqual(
                    (root / "study" / name).read_bytes(),
                    (root / "reconstructed" / name).read_bytes(),
                )

    def test_resealed_history_target_persistence_and_completion_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            run_study(path, root / "original", timeout=10)
            pid = config["people"][0]["id"]
            for field in ("features", "target", "persistence", "origin_us", "result", "state"):
                with self.subTest(field=field):
                    study = root / field
                    shutil.copytree(root / "original", study)
                    if field in ("features", "target", "persistence", "origin_us"):
                        rows = trace_rows(study, pid)
                        row = next(row for row in rows if row["features"] is not None)
                        if field == "features":
                            row[field][0] += 1
                        elif field == "target":
                            row[field]["value"] += 1
                        else:
                            row[field] += 1
                        rewrite_trace(study, pid, rows)
                    elif field == "result":
                        result, _ = read(study / "cases" / pid / "result.json")
                        result["rows"] -= 1
                        save(study / "cases" / pid / "result.json", result)
                    else:
                        state, _ = read(study / "cases" / pid / "state.json")
                        state["stage"] = "input"
                        save(study / "cases" / pid / "state.json", state)
                    seal(study)
                    with self.assertRaises(ValueError):
                        reconstruct(study)

    def test_resealed_result_is_validated_even_when_supervision_failed(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            run_study(path, root / "study", timeout=10)
            folder = root / "study/cases" / config["people"][0]["id"]
            state, _ = read(folder / "state.json")
            state.update(status="failed", error_type="RuntimeError")
            save(folder / "state.json", state)
            save(folder / "result.json", {"person": "different", "status": "fabricated"})
            seal(root / "study")
            with self.assertRaises(ValueError):
                reconstruct(root / "study")

    def test_resealed_failed_worker_claim_and_complete_result_require_trace_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            run_study(path, root / "original", timeout=10)
            pid = config["people"][0]["id"]
            for mutation in ("missing_claim", "incomplete_result_trace"):
                with self.subTest(mutation=mutation):
                    study = root / mutation
                    shutil.copytree(root / "original", study)
                    folder = study / "cases" / pid
                    state, _ = read(folder / "state.json")
                    state.update(status="failed", error_type="RuntimeError")
                    save(folder / "state.json", state)
                    if mutation == "missing_claim":
                        (folder / "worker-claim.json").unlink()
                        (folder / "result.json").unlink()
                        (folder / "trace.jsonl").write_bytes(b"")
                        save(folder / "worker-error.json", {"type": "RuntimeError"})
                    else:
                        rewrite_trace(study, pid, trace_rows(study, pid)[:-1])
                    seal(study)
                    with self.assertRaises(ValueError):
                        reconstruct(study)

    def test_incomplete_failed_trace_keeps_raw_tail_but_scores_only_complete_prefix(self):
        source = (
            "def predict(request, settings):\n"
            f"    if request['origin_us'] >= {90 * MINUTE}: raise RuntimeError('synthetic')\n"
            "    return request['values_mg_dl'][-1]\n"
        )
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", source=source, people=1)
            report = run_study(path, root / "study", timeout=10)
            trace = root / "study/cases" / config["people"][0]["id"] / "trace.jsonl"
            tail = b'{"origin_us":'
            trace.write_bytes(trace.read_bytes() + tail)
            seal(root / "study")
            self.assertEqual(reconstruct(root / "study"), report)
            self.assertTrue(trace.read_bytes().endswith(tail))

    def test_worker_failure_receipt_can_coexist_with_supervisor_interruption(self):
        source = (
            "def predict(request, settings):\n"
            f"    if request['origin_us'] >= {90 * MINUTE}: raise TypeError('synthetic')\n"
            "    return request['values_mg_dl'][-1]\n"
        )
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", source=source, people=1)
            original = run_study(path, root / "study", timeout=10)
            pid = config["people"][0]["id"]
            state_path = root / "study/cases" / pid / "state.json"
            state, _ = read(state_path)
            # Deterministically represent a timeout observed just after the worker
            # committed its error receipt, without relying on a scheduling race.
            state.update(
                status="interrupted", error_type="TimeoutExpired", worker_error_type="TypeError"
            )
            save(state_path, state)
            seal(root / "study")
            rebuilt = reconstruct(root / "study")
            case = rebuilt["evaluation"]["people"][pid]
            self.assertEqual(case["execution_status"], "interrupted")
            self.assertEqual(case["execution"]["error_type"], "TimeoutExpired")
            self.assertEqual(case["execution"]["worker_error_type"], "TypeError")
            self.assertEqual(case["attempted"], original["evaluation"]["people"][pid]["attempted"])
            state["worker_error_type"] = "RuntimeError"
            save(state_path, state)
            seal(root / "study")
            with self.assertRaises(ValueError):
                reconstruct(root / "study")

    def test_interrupted_partial_claim_before_execution_is_retained_but_wrong_claim_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            run_study(path, root / "study", timeout=10)
            pid = config["people"][0]["id"]
            folder = root / "study/cases" / pid
            state, _ = read(folder / "state.json")
            state.update(status="interrupted", error_type="TimeoutExpired", worker_error_type=None)
            save(folder / "state.json", state)
            (folder / "trace.jsonl").unlink()
            (folder / "result.json").unlink()
            claim = folder / "worker-claim.json"
            partial = b'{"person":'
            claim.write_bytes(partial)
            seal(root / "study")
            report = reconstruct(root / "study")
            case = report["evaluation"]["people"][pid]
            self.assertEqual(case["execution_status"], "interrupted")
            self.assertEqual(case["attempted"], 0)
            self.assertEqual(case["not_attempted"], len(config["people"][0]["origins_us"]))
            self.assertEqual(claim.read_bytes(), partial)
            save(claim, {"person": "different-person"})
            seal(root / "study")
            with self.assertRaises(ValueError):
                reconstruct(root / "study")

    def test_failed_prefix_retains_uncommitted_metadata_but_completed_case_refuses_it(self):
        source = (
            "def predict(request, settings):\n"
            f"    if request['origin_us'] >= {90 * MINUTE}: raise TypeError('synthetic')\n"
            "    return request['values_mg_dl'][-1]\n"
        )
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", source=source, people=1)
            original = run_study(path, root / "failed", timeout=10)
            folder = root / "failed/cases" / config["people"][0]["id"]
            trace = folder / "trace.jsonl"
            trace.write_bytes(trace.read_bytes() + b'{"origin_us":')
            staged = {"result.json.tmp": b'{"person":', "worker-error.json.tmp": b'{"type":'}
            for name, raw in staged.items():
                (folder / name).write_bytes(raw)
            seal(root / "failed")
            self.assertEqual(reconstruct(root / "failed"), original)
            for name, raw in staged.items():
                self.assertEqual((folder / name).read_bytes(), raw)
            (folder / "worker-claim.json").write_bytes(b'{"person":')
            seal(root / "failed")
            with self.assertRaises(ValueError):
                reconstruct(root / "failed")
            complete_path, complete_config = configuration(root / "complete-preparation", people=1)
            run_study(complete_path, root / "completed", timeout=10)
            completed_folder = root / "completed/cases" / complete_config["people"][0]["id"]
            (completed_folder / "result.json.tmp").write_bytes(b'{"person":')
            seal(root / "completed")
            with self.assertRaises(ValueError):
                reconstruct(root / "completed")

    def test_resealed_result_count_requires_integer_type_even_when_numerically_equal(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            run_study(path, root / "study", timeout=10)
            result_path = root / "study/cases" / config["people"][0]["id"] / "result.json"
            result, _ = read(result_path)
            result["rows"] = float(result["rows"])
            save(result_path, result)
            seal(root / "study")
            with self.assertRaises(ValueError):
                reconstruct(root / "study")

    @unittest.skipUnless(os.name == "posix", "Signal supervision is POSIX")
    def test_user_interruption_keeps_remaining_people_as_unattempted(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            marker = root / "predictor-running"
            source = (
                "import time\n"
                "def predict(request, settings):\n"
                f"    open({str(marker)!r}, 'w').write('synthetic')\n"
                "    time.sleep(30)\n"
                "    return request['values_mg_dl'][-1]\n"
            )
            path, config = configuration(root / "preparation", source=source)
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-S",
                    "-m",
                    "experiments.m3.researcher",
                    "run",
                    "--config",
                    str(path),
                    "--output",
                    str(root / "study"),
                    "--timeout",
                    "10",
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                deadline = time.monotonic() + 5
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), "Synthetic predictor never began")
                os.kill(child.pid, signal.SIGINT)
                child.communicate(timeout=5)
                self.assertEqual(child.returncode, 1)
                report, _ = read(root / "study/report.json")
                cases = report["evaluation"]["people"]
                self.assertEqual(
                    cases[config["people"][0]["id"]]["execution_status"], "interrupted"
                )
                later = cases[config["people"][1]["id"]]
                self.assertEqual(later["execution_status"], "not_attempted")
                self.assertEqual(later["attempted"], 0)
                self.assertEqual(later["execution"]["elapsed_seconds"], 0)
                self.assertEqual(reconstruct(root / "study"), report)
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate()

    def test_existing_outputs_and_artifact_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            study = root / "study"
            run_study(path, study, timeout=10)
            before, _ = inventory(study)
            with self.assertRaises(FileExistsError):
                run_study(path, study, timeout=10)
            with self.assertRaises(FileExistsError):
                reconstruct(study, study)
            self.assertEqual(inventory(study)[0], before)
            alias = root / "study-alias"
            alias.symlink_to(study, target_is_directory=True)
            with self.assertRaises(ValueError):
                reconstruct(alias)
            observation = study / "cases" / config["people"][0]["id"] / "observations.json"
            real = root / "saved-input.json"
            observation.rename(real)
            observation.symlink_to(real)
            with self.assertRaises(ValueError):
                reconstruct(study)

    def test_duplicate_worker_cannot_change_owned_or_sealed_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path, config = configuration(root / "preparation", people=1)
            study = root / "study"
            report = run_study(path, study, timeout=10)
            before, _ = inventory(study)
            result = subprocess.run(
                worker_arguments(study, config["people"][0]["id"]),
                cwd=ROOT,
                capture_output=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(inventory(study)[0], before)
            self.assertEqual(reconstruct(study), report)

    def test_large_finite_prediction_has_stable_finite_report_metrics(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = "def predict(request, settings): return 1e200\n"
            path, config = configuration(root / "preparation", source=source, people=1)
            report = run_study(path, root / "study", timeout=10)
            case = report["evaluation"]["people"][config["people"][0]["id"]]
            self.assertEqual(case["execution_status"], "completed")
            for metric in ("mae", "rmse", "bias"):
                self.assertAlmostEqual(case["candidate"][metric] / 1e200, 1.0)
            self.assertEqual(reconstruct(root / "study"), report)

    @unittest.skipUnless(os.name == "posix", "Process-group supervision is POSIX")
    def test_worker_descendants_are_stopped_after_success_failure_and_timeout(self):
        for ending in ("success", "failure", "timeout"):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                marker = root / "descendant-pid"
                source = (
                    "import subprocess, sys, time\n"
                    "spawned = False\n"
                    "def predict(request, settings):\n"
                    "    global spawned\n"
                    "    if not spawned:\n"
                    "        child = subprocess.Popen([sys.executable, '-S', '-c', "
                    "'import time; time.sleep(30)'])\n"
                    f"        open({str(marker)!r}, 'w').write(str(child.pid))\n"
                    "        spawned = True\n"
                )
                if ending == "failure":
                    source += "    raise RuntimeError('synthetic failure')\n"
                elif ending == "timeout":
                    source += "    time.sleep(30)\n"
                else:
                    source += "    return request['values_mg_dl'][-1]\n"
                path, config = configuration(root / "preparation", source=source, people=1)
                descendant = None
                try:
                    report = run_study(
                        path, root / "study", timeout=0.5 if ending == "timeout" else 10
                    )
                    self.assertTrue(marker.is_file())
                    descendant = int(marker.read_text())
                    deadline = time.monotonic() + 1
                    while alive(descendant) and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertFalse(alive(descendant), "Supplied source descendant still running")
                    expected = {
                        "success": "completed",
                        "failure": "failed",
                        "timeout": "interrupted",
                    }
                    case = report["evaluation"]["people"][config["people"][0]["id"]]
                    self.assertEqual(case["execution_status"], expected[ending])
                finally:
                    if descendant is None and marker.exists():
                        descendant = int(marker.read_text())
                    if descendant is not None and alive(descendant):
                        try:
                            os.kill(descendant, signal.SIGKILL)
                        except ProcessLookupError:
                            pass


if __name__ == "__main__":
    unittest.main()
