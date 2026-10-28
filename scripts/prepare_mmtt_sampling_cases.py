"""Prepare the four invented OT-055 software controls through their public CLI."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(module, *args, expected=0):
    result = subprocess.run(
        [sys.executable, "-B", "-E", "-s", "-S", "-m", module, *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != expected:
        raise ValueError(f"{module} {args[0]} failed: {result.stdout} {result.stderr}")


def prepare(output):
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for case in ("constant", "information-loss", "incomplete", "steep-response"):
        folder = output / case
        folder.mkdir()
        dev, source = folder / "development", folder / "source"
        command(
            "experiments.mmtt_sampling",
            "example",
            "--case",
            case,
            "--development-only",
            "--output",
            dev,
        )
        command(
            "experiments.observation_analysis",
            "import",
            "--package",
            dev / "package.json",
            "--csv",
            dev / "observations.csv",
            "--output",
            folder / "development-import",
        )
        command("experiments.mmtt_sampling", "example", "--case", case, "--output", source)
        command(
            "experiments.mmtt_sampling",
            "freeze-study",
            "--package",
            source / "package.json",
            "--csv",
            source / "observations.csv",
            "--settings",
            source / "settings.json",
            "--design",
            source / "sampling-design.json",
            "--development-import",
            folder / "development-import",
            "--output",
            folder / "plan",
        )
        command("experiments.workflows", "check", "mmtt-sampling", "--config", folder / "plan")
        code = 0 if case in ("constant", "information-loss") else 1
        command(
            "experiments.workflows",
            "run",
            "mmtt-sampling",
            "--config",
            folder / "plan",
            "--output",
            folder / "archive",
            expected=code,
        )
        command(
            "experiments.workflows",
            "reconstruct",
            "mmtt-sampling",
            "--archive",
            folder / "archive",
            "--output",
            folder / "reconstructed",
            "--allow-failed",
        )
        for name in ("report.json", "report.md"):
            if (folder / "archive" / name).read_bytes() != (
                folder / "reconstructed" / name
            ).read_bytes():
                raise ValueError("Reconstructed report differs")
        raw = (folder / "archive/report.json").read_bytes()
        report = json.loads(raw)
        cases.append(
            {
                "case": case,
                "archive": case + "/archive",
                "expected_run_exit": code,
                "report_sha256": hashlib.sha256(raw).hexdigest(),
                "manifest_sha256": hashlib.sha256(
                    (folder / "archive/manifest.json").read_bytes()
                ).hexdigest(),
                "coverage": report["coverage"],
            }
        )
    result = {
        "schema": "opent1d.mmtt-sampling-casepack/1",
        "kind": "synthetic",
        "scope": "Known engineered software controls; no empirical or independent user result",
        "cases": cases,
    }
    (output / "casepack.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "prepared_and_reconstructed", "cases": len(cases)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    prepare(parser.parse_args().output)
