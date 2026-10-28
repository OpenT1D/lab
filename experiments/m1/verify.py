"""Fresh-process replay and reconstruction without installed simulation packages."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from experiments.m0.simglucose.recording import write_json

from .artifacts import digest, read_run
from .historical import check as check_historical


def verify(study, output):
    output.mkdir(parents=True, exist_ok=False)
    evidence = {
        "schema": "opent1d.verification/2",
        "status": "started",
        "replay": [],
        "tolerance_applied": False,
    }
    write_json(output / "verification.json", evidence)
    try:
        evidence["historical"] = check_historical(study)
        for controller, seed in (("basal_bolus", 101), ("pid", 101), ("pid", 102)):
            identifier = f"adult#001-{seed}-{controller}-D"
            original = study / identifier
            replay = output / identifier
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "experiments.m1",
                    "run",
                    "--config",
                    str(original / "config.json"),
                    "--output",
                    str(replay),
                ],
                check=False,
            )
            saved = read_run(replay)
            expected_status = read_run(original)["manifest"]["status"]
            if saved["manifest"]["status"] != expected_status:
                raise ValueError("Fresh-process status differs")
            if expected_status not in ("completed", "terminated"):
                raise ValueError(
                    "Cannot verify a failed or unfinished simulation as a native replay"
                )
            expected_exit = 0 if expected_status == "completed" else 1
            if process.returncode != expected_exit:
                raise ValueError("Unexpected replay process exit")
            for name in ("initial.json", "trace.jsonl", "native-diagnostic.csv"):
                if (original / name).read_bytes() != (replay / name).read_bytes():
                    raise ValueError(f"Fresh-process replay differs: {identifier}/{name}")
            evidence["replay"].append(
                {"id": identifier, "trace_sha256": digest(replay / "trace.jsonl"), "exact": True}
            )
        reconstructed = output / "reconstructed"
        # -S removes site-packages: report reconstruction cannot rely on the simulator,
        # numpy, pandas or any other installed third-party package.
        subprocess.run(
            [
                sys.executable,
                "-S",
                "-m",
                "experiments.m1",
                "report",
                "--study",
                str(study),
                "--output",
                str(reconstructed),
            ],
            check=True,
        )
        for name in ("report.json", "report.md"):
            if (study / "report" / name).read_bytes() != (reconstructed / name).read_bytes():
                raise ValueError(f"Reconstruction differs: {name}")
        evidence["report_exact_without_site_packages"] = True
        evidence["report_sha256"] = digest(reconstructed / "report.json")
        evidence["status"] = "completed"
        write_json(output / "verification.json", evidence)
        print(json.dumps(evidence, indent=2))
    except BaseException as error:
        evidence.update(status="failed", error=f"{type(error).__name__}: {error}")
        write_json(output / "verification.json", evidence)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify(args.study, args.output)
