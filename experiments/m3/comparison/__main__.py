"""Frozen synthetic M3 candidate comparison; no model fitting or human evaluation."""

import argparse
import json
import sys
from pathlib import Path

from .common import check
from .fixtures import fixture
from .study import reconstruct, run_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser(
        "check", help="Metadata only; no observation contents or model import"
    )
    check_parser.add_argument("--config", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("reconstruct")
    report.add_argument("--study", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True)
    example = commands.add_parser(
        "fixture", help="Generate explicit invented inputs and frozen examples"
    )
    example.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "check":
            print(json.dumps(check(args.config), sort_keys=True))
            return 0
        if args.command == "fixture":
            fixture(args.output)
            print("Invented comparison preparation saved; no assessment executed.")
            return 0
        if args.command == "run":
            result = run_study(args.config, args.output)
        else:
            result = reconstruct(args.study, args.output)
        print(
            "Comparison reports saved. Common cohort complete: "
            f"{result['common']['complete_cohort']}. "
            f"Contributing people: {result['common']['contributing_people']}. No human evaluation."
        )
        if args.command == "run" and (
            result["candidates"][result["candidate_order"][0]]["coordinator"]["comparison_status"]
            != "finished"
            or any(
                candidate["single_candidate"] is None
                or any(
                    person["execution_status"] != "completed"
                    for person in candidate["single_candidate"]["evaluation"]["people"].values()
                )
                for candidate in result["candidates"].values()
            )
        ):
            return 1
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(f"M3 comparison failed ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
