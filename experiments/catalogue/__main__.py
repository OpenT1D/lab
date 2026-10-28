"""Index, verify and filter local pointers to registered researcher archives."""

import argparse
import json
from pathlib import Path

from . import core


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    command = commands.add_parser("index")
    command.add_argument("--config", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("verify")
    command.add_argument("--catalogue", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--allow-failed", action="store_true")
    command = commands.add_parser("list")
    command.add_argument("--catalogue", type=Path, required=True)
    for name in ("task", "protocol", "model", "status", "tag"):
        command.add_argument("--" + name)
    command = commands.add_parser("compare")
    command.add_argument("--catalogue", type=Path, required=True)
    command.add_argument("--left", required=True)
    command.add_argument("--right", required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "index":
            result = core.index(args.config, args.output)
        elif args.operation == "verify":
            result = core.verify(args.catalogue, args.output, args.allow_failed)
        elif args.operation == "list":
            result = core.listing(
                args.catalogue,
                **{
                    name: getattr(args, name)
                    for name in ("task", "protocol", "model", "status", "tag")
                },
            )
        else:
            result = core.compare(args.catalogue, args.left, args.right)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            json.dumps(
                {"schema": core.VERSION, "error_type": type(error).__name__, "error": str(error)}
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    if args.operation == "verify":
        return (
            0
            if all(
                item["verification"]["status"] == "verified_reconstruction"
                for item in result["entries"]
            )
            else 1
        )
    if args.operation == "compare":
        return 0 if result["eligible"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
