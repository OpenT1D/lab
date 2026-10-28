"""Run a self-authored study and compare independent stdlib reconstruction."""

import argparse
import subprocess
import sys
from pathlib import Path

from .common import require, save
from .fixtures import generate_study
from .study import fit_plan, freeze, init_ledger, private_directory, run_study


def verify(output):
    output = Path(output).resolve()
    with private_directory(output):
        generate_study(output / "input")
        freeze(output / "input/registry.json", output / "plan")
        plan = output / "plan/plan.json"
        init_ledger(plan)
        fit_plan(plan, output / "fit")
        report = run_study(plan, output / "fit", output / "study")
        process = subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m3.azt1d",
                "report",
                "--study",
                str(output / "study"),
                "--output",
                str(output / "reconstructed.json"),
            ],
            capture_output=True,
        )
        require(process.returncode == 0, "Independent reconstruction failed")
        require(
            (output / "study/report.json").read_bytes()
            == (output / "reconstructed.json").read_bytes(),
            "Reconstruction differs",
        )
        require(report["evaluation"]["complete_cohort"], "Synthetic study incomplete")
        save(
            output / "verification.json",
            {
                "kind": "synthetic",
                "complete_workflow": True,
                "independent_reconstruction": True,
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
        print(f"AZT1D verification failed ({type(error).__name__})", file=sys.stderr)
        sys.exit(1)
    print("Synthetic AZT1D study and reconstruction verified.")
