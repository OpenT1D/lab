"""Run one bounded M1 research task and rebuild its report without a simulator."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, write_json
from experiments.m1.artifacts import execute, strict_json
from experiments.m1.contracts import Config
from experiments.m1.report import write_report

WORKFLOW = "opent1d.p1-m1-workflow/1"
SOURCE = Path(__file__).resolve()
PURPOSE = (
    "P1/0.1 researcher workflow: describe effects of meal-announcement and sensor "
    "conditions for native basal-bolus and PID in one synthetic M1 development profile/seed."
)
PROFILES = ("adult#001", "adult#002")
SEEDS = (101, 102)
REPORT_FILES = ("report.json", "report.md", "overview.md")


def plan(profile, seed):
    if profile not in PROFILES or type(seed) is not int or seed not in SEEDS:
        raise ValueError("P1 supports adult#001/adult#002 and development seeds 101/102 only")
    cases = []
    for controller in ("basal_bolus", "pid"):
        for condition in "ABCD":
            config = Config(profile, seed, controller, condition)
            cases.append(
                {
                    "id": f"{profile}-{seed}-{controller}-{condition}",
                    "config": config.to_dict(),
                }
            )
    marker = {
        "schema": WORKFLOW,
        "profile": profile,
        "seed": seed,
        "p1_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    }
    study = {
        "schema": "opent1d.study/1",
        "status": "started",
        "purpose": PURPOSE,
        "cases": cases,
    }
    return marker, study


def require_runtime():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("P1 native execution requires the locked Python 3.12 environment")
    try:
        version = importlib.metadata.version("simglucose")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(
            "simglucose is absent; run uv sync --locked --project experiments/m0/simglucose "
            "and execute P1 in that environment"
        ) from error
    if version != "0.2.11":
        raise RuntimeError(f"Unsupported simglucose version: {version}; expected 0.2.11")


def validate_study(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("P1 study must be a regular directory")
    for name in ("workflow.json", "study.json"):
        if (directory / name).is_symlink():
            raise ValueError("P1 control files must not be symlinks")
    marker = strict_json((directory / "workflow.json").read_bytes())
    if not isinstance(marker, dict) or set(marker) != {
        "schema",
        "profile",
        "seed",
        "p1_source_sha256",
    }:
        raise ValueError("Wrong P1 workflow marker")
    if marker["schema"] != WORKFLOW:
        raise ValueError("Unsupported P1 workflow version")
    expected_marker, expected_study = plan(marker["profile"], marker["seed"])
    if marker != expected_marker:
        raise ValueError("Wrong P1 workflow marker")
    saved = strict_json((directory / "study.json").read_bytes())
    if not isinstance(saved, dict) or saved.get("status") not in (
        "started",
        "completed",
        "finished_with_failures",
    ):
        raise ValueError("Invalid P1 study status")
    expected_study["status"] = saved["status"]
    if saved != expected_study:
        raise ValueError("P1 schedule differs from its supported eight-case task")
    return marker


def fmt(value):
    return "undefined" if value is None else f"{value:.3f}"


def overview(result, marker):
    by_key = {
        (case["config"]["controller"], case["config"]["condition"]): case
        for case in result["cases"]
    }
    lines = [
        "# P1: meal and sensor information in one synthetic profile",
        "",
        f"Development profile `{marker['profile']}`, seed `{marker['seed']}`. "
        "Two unchanged native reference controllers, four information conditions, "
        "48 simulated hours with the second day scored.",
        "",
        "This is a research-software demonstration, not patient-specific dosing, "
        "a clinical comparison or evidence that one controller is superior.",
        "",
        "## Read the eight runs",
        "",
        "| Controller | Condition | Status | 70–180 (%) | Below 70 (%) | "
        "Scored minutes | Delivered insulin (U) |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for controller in ("basal_bolus", "pid"):
        for condition in "ABCD":
            case = by_key[(controller, condition)]
            metrics = case["metrics"]
            glucose = metrics["glucose"] if metrics else {}
            scored = metrics["delivered_interval_minutes"] if metrics else None
            delivered = metrics["delivered_insulin_u"] if scored else None
            lines.append(
                f"| {controller} | {condition} | {case['status']} | "
                f"{fmt(glucose.get('in_70_180_percent'))} | "
                f"{fmt(glucose.get('below_70_percent'))} | {fmt(scored)} | "
                f"{fmt(delivered)} |"
            )
    lines.extend(
        [
            "",
            "A: full meal announcements; B: no meal announcements; C: half announcements; "
            "D: a 30-minute noon sensor mask. True meals are identical. Glucose is the "
            "native three-minute mean subcutaneous quantity. An undefined dose means "
            "the scored interval was not observed; it is never a zero-dose claim.",
            "",
            "## Paired descriptive changes",
            "",
            "Right minus left in percentage points; a comparison is shown only when "
            "both corresponding runs completed. One profile and one seed provide no "
            "population uncertainty or held-out evaluation.",
            "",
            "| Comparison | Complete pairs | Δ 70–180 (pp) | Δ below 70 (pp) |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for comparison in result["comparisons"]:
        record = comparison["profiles"][0]
        changes = record["changes_right_minus_left_pp"]
        left = "/".join(comparison["left"])
        right = "/".join(comparison["right"])
        lines.append(
            f"| {right} − {left} | {record['complete_pairs']}/{comparison['scheduled_pairs']} | "
            f"{fmt(changes['in_70_180_percent']['mean'])} | "
            f"{fmt(changes['below_70_percent']['mean'])} |"
        )
    errors = [case for case in result["cases"] if case.get("error")]
    if errors:
        lines.extend(["", "## Failures and incomplete runs", ""])
        for case in errors:
            lines.append(f"- `{case['id']}`: {case['status']} — {case['error']}")
    lines.extend(
        [
            "",
            "## Inspect and reconstruct",
            "",
            f"Study status: `{result['study_status']}`; eight scheduled cases; "
            f"status counts: `{json.dumps(result['status_counts'], sort_keys=True)}`.",
            "Read [the full M1 report](report.md) for additional metrics, excluded "
            "pairs and caveats, or [its JSON](report.json) for the complete artifact "
            "inventory and provenance. Keep this entire study directory. Use the "
            "P1 `reconstruct` command from the recorded source revision to rebuild "
            "all three report files without importing simglucose.",
            "",
        ]
    )
    return "\n".join(lines)


def write_product_report(study, output):
    marker = validate_study(study)
    result = write_report(study, output)
    (Path(output) / "overview.md").write_text(overview(result, marker))
    return result


def run_study(output, profile="adult#001", seed=101):
    marker, study = plan(profile, seed)
    require_runtime()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "workflow.json", marker)
    write_json(output / "study.json", study)  # Every case is planned before execution.
    inputs = output / "inputs"
    inputs.mkdir()
    for case in study["cases"]:
        write_json(inputs / f"{case['id']}.json", case["config"])
    failed, execution_errors = False, False
    try:
        for case in study["cases"]:
            try:
                result = execute(inputs / f"{case['id']}.json", output / case["id"])
                failed |= result["status"] != "completed"
            except (RunInterrupted, KeyboardInterrupt):
                raise
            except Exception:
                failed, execution_errors = True, True
    finally:
        # An interruption leaves the schedule started and unattempted cases visible.
        write_json(output / "study.json", study)
    study["status"] = "finished_with_failures" if failed else "completed"
    write_json(output / "study.json", study)
    report = write_product_report(output, output / "report")
    if execution_errors:
        raise RuntimeError("Some P1 runs failed; inspect report/overview.md and run artifacts")
    return report


def reconstruct(study, output):
    validate_study(study)
    output = Path(output)
    result = write_product_report(study, output)
    original = Path(study) / "report"
    present = [((original / name).exists()) for name in REPORT_FILES]
    if any(present) and not all(present):
        raise ValueError("Incomplete original P1 report")
    if all(present):
        for name in REPORT_FILES:
            if (original / name).is_symlink() or (original / name).read_bytes() != (
                output / name
            ).read_bytes():
                raise ValueError(f"P1 reconstruction differs: {name}")
    write_json(
        output / "reconstruction.json",
        {
            "schema": "opent1d.p1-reconstruction/1",
            "study_status": result["study_status"],
            "original_report_present": all(present),
            "byte_identical_to_original": all(present),
            "files_sha256": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in REPORT_FILES
            },
        },
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Execute the eight fixed M1 development cases")
    run.add_argument("--profile", choices=PROFILES, default="adult#001")
    run.add_argument("--seed", type=int, choices=SEEDS, default=101)
    run.add_argument("--output", type=Path, required=True)
    rebuild = commands.add_parser("reconstruct", help="Rebuild without the simulator")
    rebuild.add_argument("--study", type=Path, required=True)
    rebuild.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (
        run_study(args.output, args.profile, args.seed)
        if args.command == "run"
        else reconstruct(args.study, args.output)
    )
    print(
        json.dumps(
            {
                "study_status": result["study_status"],
                "scheduled": result["scheduled"],
                "status_counts": result["status_counts"],
                "report": str(args.output / "report" / "overview.md")
                if args.command == "run"
                else str(args.output / "overview.md"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
