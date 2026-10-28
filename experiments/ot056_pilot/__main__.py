"""Prepare bounded synthetic cases; never record simulated researchers as people."""

import argparse
import json
from pathlib import Path

from .cases import export_cases, verify_cases
from .preflight import preflight, verify_preflight
from .references import export_references, verify_references
from .rehearsal import rehearse, verify
from .technical import task1_phase, verify_task1_phase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("cases")
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("verify-cases")
    command.add_argument("--archive", required=True, type=Path)
    command = sub.add_parser("preflight")
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("verify-preflight")
    command.add_argument("--archive", required=True, type=Path)
    command = sub.add_parser("references")
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("verify-references")
    command.add_argument("--archive", required=True, type=Path)
    command = sub.add_parser("rehearse-task1")
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("verify-task1")
    command.add_argument("--archive", required=True, type=Path)
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("rehearse")
    command.add_argument("--output", required=True, type=Path)
    command = sub.add_parser("verify")
    command.add_argument("--archive", required=True, type=Path)
    command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "cases":
            result = export_cases(args.output)
        elif args.command == "verify-cases":
            result = verify_cases(args.archive)
        elif args.command == "preflight":
            result = preflight(args.output)
        elif args.command == "verify-preflight":
            result = verify_preflight(args.archive)
        elif args.command == "references":
            result = export_references(args.output)
        elif args.command == "verify-references":
            result = verify_references(args.archive)
        elif args.command == "rehearse-task1":
            result = task1_phase(args.output)
        elif args.command == "verify-task1":
            result = verify_task1_phase(args.archive, args.output)
        elif args.command == "rehearse":
            result = rehearse(args.output)
        else:
            result = verify(args.archive, args.output)
        print(json.dumps({"schema": result["schema"], "human_sessions": 0}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Technical pilot preparation failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
