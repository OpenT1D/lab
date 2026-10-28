"""Import and verify bounded local retrospective observations."""

import argparse
import json
from pathlib import Path

from .fixtures import CASES, export_example
from .intake import import_observations, verify_import
from .plan import freeze, load_plan
from .run import reconstruct, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    command = commands.add_parser("example")
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--case", choices=CASES, default="increase")
    command = commands.add_parser("import")
    command.add_argument("--package", type=Path, required=True)
    command.add_argument("--csv", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("verify-import")
    command.add_argument("--archive", type=Path, required=True)
    command = commands.add_parser("freeze")
    command.add_argument("--package", type=Path, required=True)
    command.add_argument("--csv", type=Path, required=True)
    command.add_argument("--settings", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("check")
    command.add_argument("--config", type=Path, required=True)
    command = commands.add_parser("run")
    command.add_argument("--config", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("reconstruct")
    command.add_argument("--archive", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--allow-failed", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "example":
            export_example(args.output, args.case)
            result = {"status": "example_created", "estimation_performed": False}
        elif args.operation == "import":
            record = import_observations(args.package, args.csv, args.output)
            result = {"status": record["status"], "estimation_performed": False}
        elif args.operation == "verify-import":
            _, validation = verify_import(args.archive)
            result = {
                "status": "verified",
                "valid_observations": validation is not None and validation["valid"],
                "estimation_performed": False,
            }
        elif args.operation == "freeze":
            plan = freeze(args.package, args.csv, args.settings, args.output)
            result = {
                "status": "plan_frozen",
                "method": plan["method"],
                "estimation_performed": False,
            }
        elif args.operation == "check":
            plan, package, _ = load_plan(args.config, check_runtime=True)
            result = {
                "status": "ready",
                "planned_people": len(package["participants"]),
                "planned_variants": len(plan["settings"]["variants"]),
                "estimation_performed": False,
            }
        else:
            report = (
                run(args.config, args.output)
                if args.operation == "run"
                else reconstruct(args.archive, args.output, allow_failed=args.allow_failed)
            )
            result = {
                "status": "verified"
                if args.operation == "reconstruct"
                else report["execution_status"],
                "coverage": report["coverage"],
                "human_evaluation": False,
                "report": str(args.output / "report.md"),
            }
            print(json.dumps(result, sort_keys=True))
            return (
                0 if args.operation == "reconstruct" or report["coverage"]["complete_cohort"] else 1
            )
        print(json.dumps(result, sort_keys=True))
        return 2 if result["status"] == "invalid" else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        result = {
            "status": "refused",
            "estimation_performed": False,
            "reason": str(error)
            if isinstance(error, ValueError)
            else "Input unavailable or unsupported structure; inspect local inputs",
        }
        print(json.dumps(result))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
