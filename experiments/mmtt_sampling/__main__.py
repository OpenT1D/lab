"""Frozen synthetic sampling comparisons through the shared OT-054 core."""

import argparse
import hashlib
import json
from pathlib import Path

from .design import validate_design, validate_development_times
from .fixtures import CASES, export_example
from .intake import development_inventory
from .plan import freeze as freeze_study
from .plan import load_plan
from .run import reconstruct, run


def unique_fields(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("Duplicate JSON fields are not allowed in a frozen design")
        document[key] = value
    return document


def freeze(design_path, inventory_path, output):
    design_bytes = design_path.read_bytes()
    inventory_bytes = inventory_path.read_bytes()
    design = validate_design(json.loads(design_bytes, object_pairs_hook=unique_fields))
    inventory = validate_development_times(
        design, json.loads(inventory_bytes, object_pairs_hook=unique_fields)
    )
    receipt = {
        "schema": "opent1d.mmtt-sampling-selection/1",
        "status": "synthetic-schedule-preparation-only",
        "design_sha256": hashlib.sha256(design_bytes).hexdigest(),
        "development_times_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "design": design,
        "development_times": inventory,
        "empirical_acceptance": "not assessed; rights, data, protocol and margins remain open",
    }
    with output.open("x") as stream:
        stream.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


def freeze_import(design_path, archive, output):
    raw = design_path.read_bytes()
    design = validate_design(json.loads(raw, object_pairs_hook=unique_fields))
    inventory = development_inventory(archive, design)
    receipt = {
        "schema": "opent1d.mmtt-sampling-import-selection/1",
        "status": "synthetic-schedule-preparation-only",
        "design_sha256": hashlib.sha256(raw).hexdigest(),
        "development_import_seal_sha256": hashlib.sha256(
            (archive / "manifest.json").read_bytes()
        ).hexdigest(),
        "design": design,
        "development_times": inventory,
        "empirical_acceptance": "not assessed; rights, data, protocol and margins remain open",
    }
    with output.open("x") as stream:
        stream.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser(
        "freeze", help="Freeze synthetic schedules using development times only"
    )
    prepare.add_argument("--design", type=Path, required=True)
    prepare.add_argument("--development-times", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    imported = sub.add_parser("freeze-import", help="Reuse a sealed development-only OT-054 import")
    imported.add_argument("--design", type=Path, required=True)
    imported.add_argument("--development-import", type=Path, required=True)
    imported.add_argument("--output", type=Path, required=True)
    example = sub.add_parser("example", help="Export invented shared-format observation cases")
    example.add_argument("--output", type=Path, required=True)
    example.add_argument("--development-only", action="store_true")
    example.add_argument("--case", choices=CASES, default="information-loss")
    study = sub.add_parser("freeze-study", help="Freeze sampling inputs and development evidence")
    for name in ("package", "csv", "settings", "design", "development-import", "output"):
        study.add_argument("--" + name, type=Path, required=True)
    check = sub.add_parser("check", help="Check frozen source/data identities without estimation")
    check.add_argument("--config", type=Path, required=True)
    execute = sub.add_parser("run", help="Run all native full/reduced analyses")
    execute.add_argument("--config", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    reader = sub.add_parser(
        "reconstruct", help="Verify native child analyses and rebuild comparisons"
    )
    reader.add_argument("--archive", type=Path, required=True)
    reader.add_argument("--output", type=Path, required=True)
    reader.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            freeze(args.design, args.development_times, args.output)
        elif args.command == "freeze-import":
            freeze_import(args.design, args.development_import, args.output)
        elif args.command == "example":
            export_example(args.output, args.development_only, args.case)
        elif args.command == "freeze-study":
            freeze_study(
                args.package,
                args.csv,
                args.settings,
                args.design,
                args.development_import,
                args.output,
            )
        elif args.command == "check":
            plan, package, _ = load_plan(args.config, check_runtime=True)
            print(
                json.dumps(
                    {
                        "status": "ready",
                        "estimation_performed": False,
                        "planned_people": len(package["participants"]),
                        "planned_schedules": 1 + len(plan["design"]["subsets"]),
                    }
                )
            )
            return 0
        else:
            report = (
                run(args.config, args.output)
                if args.command == "run"
                else reconstruct(args.archive, args.output, allow_failed=args.allow_failed)
            )
            print(
                json.dumps(
                    {
                        "status": report["execution_status"],
                        "complete_cohort": report["coverage"]["complete_cohort"],
                        "empirical_assessment": "not performed",
                    },
                    sort_keys=True,
                )
            )
            return (
                0 if args.command == "reconstruct" or report["coverage"]["complete_cohort"] else 1
            )
    except (ValueError, OSError, TypeError, KeyError, OverflowError) as error:
        parser.exit(2, f"Sampling command refused: {error}\n")
    print("Synthetic preparation saved; empirical acceptance remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
