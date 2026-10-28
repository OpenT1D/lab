"""Persist study verification, including historical outputs and reconstruction."""

import json
import subprocess
import sys
from pathlib import Path

from experiments.m0.simglucose.recording import write_json
from experiments.m1.artifacts import digest

from .report import reconstruct, verify_development
from .run import ROOT


def verify(study, output):
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "started"}
    write_json(output / "verification.json", result)
    try:
        report = reconstruct(study)
        if report["phase"] == "development":
            result["historical"] = verify_development(study)
        original = (Path(study) / "report/report.json").read_bytes()
        if json.loads(original) != report:
            raise ValueError("Saved report differs from reconstructed artifacts")
        rebuilt = output / "rebuilt"
        subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m2",
                "report",
                "--study",
                str(Path(study).resolve()),
                "--output",
                str(rebuilt.resolve()),
            ],
            cwd=ROOT,
            check=True,
        )
        for name in ("report.json", "report.md"):
            if (rebuilt / name).read_bytes() != (Path(study) / "report" / name).read_bytes():
                raise ValueError(f"Simulator-free report bytes differ: {name}")
        result.update(
            status="completed",
            simulator_free_exact_reconstruction=True,
            report_sha256=digest(rebuilt / "report.json"),
            scheduled=report["scheduled"],
        )
    except BaseException as error:
        result.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        write_json(output / "verification.json", result)
    print(json.dumps(result, indent=2))
