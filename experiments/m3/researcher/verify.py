"""Native donor verification, two forecast structures and source-free reconstruction."""

import shutil
import subprocess
import sys

from experiments.m1.artifacts import strict_json
from experiments.m3.azt1d.fixtures import generate_study
from experiments.m3.azt1d.study import fit_plan, freeze, init_ledger
from experiments.m3.estimator import predict
from experiments.m3.external.model import export_model

from .common import ROOT, digest, fresh_directory, read, require, save
from .fixtures import fixture
from .study import run_study


def verify(output):
    output = fresh_directory(output)
    work = output / "work"
    work.mkdir()
    generate_study(work / "donor")
    freeze(work / "donor/registry.json", work / "donor-plan")
    plan = work / "donor-plan/plan.json"
    init_ledger(plan)
    fit_plan(plan, work / "fit")
    export_model(plan, work / "fit", work / "export")
    model, model_sha = read(work / "export/model.json")
    require(
        (work / "export/model.json").read_bytes() == (work / "fit/model.json").read_bytes(),
        "Donor export changed fitted model bytes",
    )
    fixture(work / "fixture", ridge_model=model)
    reports = {}
    for method, name in (("trend", "config.json"), ("ridge", "ridge-config.json")):
        report = run_study(work / "fixture" / name, output / method)
        require(report["evaluation"]["complete_cohort"], "Synthetic comparison incomplete")
        reports[method] = {
            "planned_people": report["evaluation"]["planned_people"],
            "paired_targets": sum(
                c["paired"]["scored"] for c in report["evaluation"]["people"].values()
            ),
        }
        checked = 0
        for person in report["evaluation"]["people"]:
            trace_path = output / method / "cases" / person / "trace.jsonl"
            for line in trace_path.read_bytes().splitlines():
                row = strict_json(line)
                if row["features"] is not None:
                    expected = (
                        predict(model, row["features"])
                        if method == "ridge"
                        else (
                            row["features"][-1]
                            + max(-30.0, min(30.0, 6 * (row["features"][-1] - row["features"][-2])))
                        )
                    )
                    require(row["candidate"] == expected, "Adapter output differs from reference")
                    checked += 1
        reports[method]["reference_predictions_checked"] = checked
        run_study(work / "fixture" / name, output / f"{method}-repeat")
        for person in report["evaluation"]["people"]:
            require(
                (output / method / "cases" / person / "trace.jsonl").read_bytes()
                == (output / f"{method}-repeat" / "cases" / person / "trace.jsonl").read_bytes(),
                "Fresh-process forecast repetition differs",
            )
    saved_settings, _ = read(output / "ridge/predictor/settings.json")
    require(saved_settings["model"] == model, "Ridge model or scaler values changed")
    # Only this invocation's own invented preparation directory is removed.
    shutil.rmtree(work)
    for method in reports:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-S",
                "-m",
                "experiments.m3.researcher",
                "report",
                "--study",
                str(output / method),
                "--output",
                str(output / f"{method}-reconstructed"),
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=120,
        )
        require(result.returncode == 0, "Independent reconstruction failed")
        for name in ("report.json", "report.md"):
            require(
                (output / method / name).read_bytes()
                == (output / f"{method}-reconstructed" / name).read_bytes(),
                "Independent reconstruction differs",
            )
    save(
        output / "verification.json",
        {
            "kind": "synthetic",
            "human_evaluation": False,
            "methods": reports,
            "native_donor_model_sha256": model_sha,
            "original_inputs_removed": True,
            "model_scaler_values_unchanged": True,
            "evaluation_refit": False,
            "independent_reconstruction": True,
            "candidate_outputs_independently_recomputed": False,
            "worked_examples_reference_checked": True,
            "fresh_process_traces_identical": True,
            "ridge_adapter_source_sha256": digest(
                (output / "ridge/predictor/source.py").read_bytes()
            ),
        },
    )
