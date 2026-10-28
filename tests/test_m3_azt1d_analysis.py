"""Offline integrity counterexamples using declared coefficients and invented inputs."""

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from experiments.m3.azt1d.analysis import reconstruct, verify_inventory, verify_learned
from experiments.m3.azt1d.common import ROOT, SCHEMA, digest, provenance, read, save
from experiments.m3.azt1d.data import eligibility, forecast_rows, origins, training_windows
from experiments.m3.azt1d.fixtures import generate_study
from experiments.m3.azt1d.service import load_conversion
from experiments.m3.azt1d.study import freeze, init_ledger, run_study, seal


def inventory(folder):
    save(
        folder / "inventory.json",
        {
            str(path.relative_to(folder)): digest(path.read_bytes())
            for path in sorted(folder.rglob("*"))
            if path.is_file() and path.name not in ("inventory.json", "report.json")
        },
    )


def fixture(root):
    """Build saved coefficients directly; this tests artifacts, not estimator fitting."""
    generate_study(root / "input", people=1, days=6)
    plan = freeze(root / "input/registry.json", root / "plan")
    anchor = init_ledger(root / "plan/plan.json")
    _, plan_sha = read(root / "plan/plan.json")
    fit = root / "fit"
    fit.mkdir()
    person = plan["registry"]["people"][0]
    pid = person["id"]
    inputs, rows = {}, {}
    for phase in ("development", "validation"):
        folder = Path(person[phase]["folder"])
        intake, rows[phase], _ = load_conversion(folder, expected_phase=phase)
        inputs[phase] = {
            name: read(folder / f"{name}.json")[0]
            for name in ("intake", "conversion", "observations", "status")
        }
    request = inputs["development"]["intake"]
    windows = training_windows(rows["development"], request["start_us"], request["end_us"])
    times = [window[0] for window in windows]
    counts = {
        pid: {
            "eligible": eligibility(times),
            "origins_us": times,
            "registered_origins_us": origins(rows["development"]),
        }
    }
    lock = tomllib.loads((ROOT / "experiments/m3/runtime/uv.lock").read_text())
    model = {
        "method": "sklearn-ridge",
        "settings": {"alpha": 1.0, "fit_intercept": True, "solver": "svd"},
        "mean": [0.0] * 6,
        "scale": [1.0] * 6,
        "coef": [0.0] * 6,
        "intercept": 130.0,
        "feature_rank": 0,
        "singular_values": [0.0] * 6,
        "training_counts": {pid: len(times)},
        "packages": {p["name"]: p["version"] for p in lock["package"] if "registry" in p["source"]},
    }
    request = inputs["validation"]["intake"]
    trace = list(
        forecast_rows(
            rows["validation"], pid, "validation", [request["start_us"], request["end_us"]], model
        )
    )
    schedules = {pid: origins(rows["validation"])}
    save(fit / "model.json", model)
    save(fit / "inputs.json", {pid: inputs})
    save(fit / "development.json", counts)
    save(fit / "validation-schedule.json", schedules)
    (fit / "trace.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace)
    )
    (fit / "worker.log").write_text("")
    save(
        fit / "result.json",
        {
            "schema": SCHEMA,
            "status": "completed",
            "plan_sha256": plan_sha,
            "development": counts,
            "training_people": [pid],
            "validation_origins": schedules,
        },
    )
    save(
        fit / "freeze.json",
        {
            "schema": SCHEMA,
            "stage": "learned",
            "plan_sha256": plan_sha,
            "model_sha256": digest((fit / "model.json").read_bytes()),
            "validation_sha256": digest((fit / "trace.jsonl").read_bytes()),
            "result_sha256": digest((fit / "result.json").read_bytes()),
            "inputs_sha256": digest((fit / "inputs.json").read_bytes()),
            "ledger_anchor": anchor,
            "provenance": provenance(),
        },
    )
    seal(
        fit,
        {
            "schema": SCHEMA,
            "status": "completed",
            "elapsed_seconds": 0.0,
            "provenance": provenance(),
        },
    )
    verify_learned(root / "plan/plan.json", fit)
    run_study(root / "plan/plan.json", fit, root / "study")
    shutil.rmtree(root / "input")
    shutil.rmtree(root / "plan")
    shutil.rmtree(fit)
    return root / "study"


class AZT1DArtifactReconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_temp = tempfile.TemporaryDirectory()
        cls.base = fixture(Path(cls.base_temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.base_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.study = Path(self.temp.name) / "study"
        shutil.copytree(self.base, self.study)
        self.run = self.study / "invented-1/run"

    def reseal_run(self, *, state=None):
        if state is None:
            state, _ = read(self.run / "state.json")
        seal(self.run, state)
        inventory(self.study)

    def test_reconstructs_with_only_saved_files_and_no_estimator(self):
        expected, _ = read(self.study / "report.json")
        self.assertEqual(reconstruct(self.study), expected)
        self.assertEqual(expected["kind"], "synthetic")
        self.assertTrue(expected["evaluation"]["complete_cohort"])
        script = (
            "import json,sys; from experiments.m3.azt1d.analysis import reconstruct; "
            "result=reconstruct(sys.argv[1]); "
            "assert 'experiments.m3.estimator' not in sys.modules; "
            "assert 'sklearn' not in sys.modules; assert 'numpy' not in sys.modules; "
            "open(sys.argv[2],'w').write(json.dumps(result,allow_nan=False))"
        )
        output = Path(self.temp.name) / "report.json"
        subprocess.run(
            [sys.executable, "-S", "-c", script, str(self.study), str(output)], check=True
        )
        self.assertEqual(json.loads(output.read_text()), expected)

    def test_recursive_inventory_rejects_links_and_traversal(self):
        self.assertEqual(verify_inventory(self.run)["status"], "completed")
        (self.study / "untrusted-link").symlink_to(self.run / "trace.jsonl")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            reconstruct(self.study)
        (self.study / "untrusted-link").unlink()
        state, _ = read(self.run / "state.json")
        state["files"]["../outside"] = "0" * 64
        save(self.run / "state.json", state)
        with self.assertRaisesRegex(ValueError, "Unsafe artifact path"):
            verify_inventory(self.run)

    def test_resealed_missing_completed_origin_is_not_completion(self):
        path = self.run / "trace.jsonl"
        path.write_bytes(b"".join(path.read_bytes().splitlines(keepends=True)[:-1]))
        self.reseal_run()
        with self.assertRaisesRegex(ValueError, "Incomplete completed forecast"):
            reconstruct(self.study)

    def test_resealed_future_history_and_forecasts_are_rejected(self):
        path = self.run / "trace.jsonl"
        rows = [json.loads(line) for line in path.read_bytes().splitlines()]
        row = next(row for row in rows if row["forecasts"] is not None)
        row["history_rows"][0]["available_us"] = row["origin_us"] + 1
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.reseal_run()
        with self.assertRaisesRegex(ValueError, "frozen causal inputs or model"):
            reconstruct(self.study)

    def test_partial_failure_retains_complete_prefix_and_fragment_count(self):
        path = self.run / "trace.jsonl"
        fragment = b'{"unfinished":'
        path.write_bytes(b"".join(path.read_bytes().splitlines(keepends=True)[:15]) + fragment)
        (self.run / "result.json").unlink()
        state, _ = read(self.run / "state.json")
        state.update(status="interrupted", error={"type": "SyntheticInterrupted"})
        seal(self.run, state)
        study, _ = read(self.study / "study.json")
        study["status"] = "interrupted"
        study["cases"][0].update(status="interrupted", error={"type": "SyntheticInterrupted"})
        save(self.study / "study.json", study)
        inventory(self.study)
        report = reconstruct(self.study)
        case = report["evaluation"]["people"]["invented-1"]
        self.assertEqual(case["attempted"], 15)
        self.assertTrue(case["partial_fragment"])
        self.assertEqual(case["partial_fragment_bytes"], len(fragment))
        self.assertEqual(case["not_attempted"], case["planned"] - 15)
        self.assertFalse(case["eligible_for_primary"])
        self.assertFalse(report["evaluation"]["complete_cohort"])

    def test_missing_access_receipt_and_truncated_ledger_fail_closed(self):
        access = self.study / "invented-1/execution-access.json"
        raw = access.read_bytes()
        access.unlink()
        inventory(self.study)
        with self.assertRaisesRegex(ValueError, "Missing evaluation access"):
            reconstruct(self.study)
        access.write_bytes(raw)
        ledger = self.study / "ledger.jsonl"
        ledger.write_bytes(b"".join(ledger.read_bytes().splitlines(keepends=True)[:-1]))
        inventory(self.study)
        with self.assertRaises(ValueError):
            reconstruct(self.study)

    def test_original_registry_bytes_and_full_roster_are_required(self):
        plan_path = self.study / "plan.json"
        original = plan_path.read_bytes()
        plan = json.loads(original)
        plan["registry_source_utf8"] += " "
        save(plan_path, plan)
        inventory(self.study)
        with self.assertRaisesRegex(ValueError, "Registry byte identity differs"):
            reconstruct(self.study)
        plan_path.write_bytes(original)
        study, _ = read(self.study / "study.json")
        study["cases"] = []
        save(self.study / "study.json", study)
        inventory(self.study)
        with self.assertRaisesRegex(ValueError, "roster or order"):
            reconstruct(self.study)


if __name__ == "__main__":
    unittest.main()
