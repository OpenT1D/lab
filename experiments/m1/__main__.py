"""Run with python -m experiments.m1; reconstruction needs no simulation packages."""

import argparse
import json
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, write_json

from .artifacts import execute
from .contracts import Config
from .report import write_report


def demo(output):
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for profile in ("adult#001", "adult#002"):
        for seed in (101, 102):
            for controller in ("basal_bolus", "pid"):
                for condition in "ABCD":
                    config = Config(profile, seed, controller, condition)
                    identifier = f"{profile}-{seed}-{controller}-{condition}"
                    cases.append({"id": identifier, "config": config.to_dict()})
    study = {
        "schema": "opent1d.study/1",
        "status": "started",
        "purpose": "Bounded OT-001 development demonstration: two development "
        "profiles, seeds 101–102, fixed gains, 48 hours with the second day scored.",
        "cases": cases,
    }
    write_json(output / "study.json", study)  # All attempts scheduled before any run.
    inputs = output / "inputs"
    inputs.mkdir()
    for case in cases:
        write_json(inputs / f"{case['id']}.json", case["config"])
    failed = False
    execution_errors = False
    try:
        for case in cases:
            try:
                result = execute(inputs / f"{case['id']}.json", output / case["id"])
                failed |= result["status"] != "completed"
            except (RunInterrupted, KeyboardInterrupt):
                raise
            except Exception:
                failed = True  # Other scheduled cases still receive an attempt.
                execution_errors = True
    finally:
        # A cancelled study stays started: unattempted cases remain visible as scheduled.
        write_json(output / "study.json", study)
    study["status"] = "finished_with_failures" if failed else "completed"
    write_json(output / "study.json", study)
    write_report(output, output / "report")
    if execution_errors:
        raise RuntimeError("Some scheduled runs had execution errors; inspect the report")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--timeout-seconds", type=float, default=300)
    demonstration = sub.add_parser("demo")
    demonstration.add_argument("--output", type=Path, required=True)
    report = sub.add_parser("report")
    report.add_argument("--study", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        result = execute(args.config, args.output, args.timeout_seconds)
        print(json.dumps({"status": result["status"], "completed_rows": result["completed_rows"]}))
        if result["status"] != "completed":
            raise SystemExit(1)
    elif args.command == "demo":
        demo(args.output)
    else:
        write_report(args.study, args.output)


if __name__ == "__main__":
    main()
