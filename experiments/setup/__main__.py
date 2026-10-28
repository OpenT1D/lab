"""Plan/check task runtimes; installation is a separate explicit operation."""

import argparse
import json
import subprocess
from pathlib import Path

from experiments.catalogue.formats import TASKS

from . import core


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    command = commands.add_parser("plan")
    command.add_argument("task", choices=TASKS)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--reconstruct", action="store_true")
    command.add_argument("--source", type=Path)
    for operation in ("check", "install"):
        command = commands.add_parser(operation)
        command.add_argument("--plan", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if operation == "install":
            command.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "plan":
            result = core.plan(args.task, args.output, args.reconstruct, args.source)
        else:
            result = core.execute(
                args.plan, args.output, args.operation == "install", getattr(args, "offline", False)
            )
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(
            json.dumps(
                {"schema": core.VERSION, "error_type": type(error).__name__, "error": str(error)}
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if args.operation == "plan" or result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
