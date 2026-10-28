"""Bounded synthetic transfer and offline reconstruction of an unchanged model."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from experiments.m3.azt1d.fixtures import generate_study
from experiments.m3.azt1d.study import fit_plan, private_directory
from experiments.m3.azt1d.study import freeze as donor_freeze
from experiments.m3.azt1d.study import init_ledger as donor_init_ledger
from experiments.m3.common import ROOT, digest, require, save

from .fixtures import generate
from .model import export_model, load_model
from .study import freeze, init_ledger, run_study


def verify(output):
    """Fit an invented donor once, then evaluate a distinct cohort without fitting.

    The old AZT1D route prepares the synthetic donor only. The external route
    receives that completed export. Its saved study must reconstruct after all
    original donor, fit, external inputs, plans and live ledgers are removed.
    """
    output = Path(output).resolve()
    with private_directory(output):
        work = output / "work"
        work.mkdir(mode=0o700)
        generate_study(work / "donor")
        donor_freeze(work / "donor/registry.json", work / "donor-plan")
        donor_plan = work / "donor-plan/plan.json"
        donor_init_ledger(donor_plan)
        fit_plan(donor_plan, work / "fit")
        original_model = (work / "fit/model.json").read_bytes()
        export_model(donor_plan, work / "fit", work / "export")
        bundle_sha = load_model(work / "export")[2]
        require(
            (work / "export/model.json").read_bytes() == original_model,
            "Export changed donor model or scaler",
        )

        generate(work / "external-input")
        freeze(work / "external-input/registry.json", work / "export", work / "plan")
        plan = work / "plan/plan.json"
        init_ledger(plan)
        report = run_study(plan, work / "study")
        require(report["kind"] == "synthetic", "Verification unexpectedly used human material")
        require(report["evaluation"]["complete_cohort"], "Synthetic external study incomplete")
        require(
            load_model(work / "study/model")[2] == bundle_sha, "Export changed during evaluation"
        )
        require(
            (work / "study/model/model.json").read_bytes() == original_model,
            "Evaluation changed frozen donor model or scaler",
        )

        archive = output / "archive"
        shutil.copytree(work / "study", archive)
        # Only files generated in this function's newly created work directory.
        shutil.rmtree(work)
        require(not work.exists(), "Original synthetic inputs remain available")
        process = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m3.external",
                "report",
                "--study",
                str(archive),
                "--output",
                str(output / "reconstructed.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=120,
        )
        require(process.returncode == 0, "Independent offline reconstruction failed")
        require(
            (archive / "report.json").read_bytes() == (output / "reconstructed.json").read_bytes(),
            "Offline reconstruction differs",
        )
        require(load_model(archive / "model")[2] == bundle_sha, "Archive model identity changed")
        save(
            output / "verification.json",
            {
                "kind": "synthetic",
                "complete_workflow": True,
                "independent_reconstruction": True,
                "original_inputs_removed_before_reconstruction": True,
                "external_refit": False,
                "model_and_scaler_unchanged": True,
                "model_bundle_sha256": bundle_sha,
                "model_sha256": digest(original_model),
                "human_evaluation": False,
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        verify(args.output)
    except BaseException as error:
        print(f"External M3 verification failed ({type(error).__name__})", file=sys.stderr)
        sys.exit(1)
    print("Synthetic external transfer and offline reconstruction verified; no external refitting.")
