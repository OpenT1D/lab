"""Preserve maintained M4 and synthetic M3 evidence; package data never selects executable code."""

import argparse
from pathlib import Path

from . import core, reader, storage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--task", choices=reader.TASKS, required=True)
    export.add_argument("--archive", type=Path, required=True)
    export.add_argument("--checkout", type=Path, required=True)
    export.add_argument("--revision", required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--timeout-seconds", type=int, default=120)
    verify = commands.add_parser("verify")
    verify.add_argument("--package", type=Path, required=True)
    restore = commands.add_parser("restore")
    restore.add_argument("--package", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)
    reconstruct = commands.add_parser("reconstruct")
    reconstruct.add_argument("--package", type=Path, required=True)
    reconstruct.add_argument("--checkout", type=Path, required=True)
    reconstruct.add_argument("--revision", required=True)
    reconstruct.add_argument("--output", type=Path, required=True)
    reconstruct.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    try:
        if args.command == "export":
            result = core.export_archive(
                args.task,
                args.archive,
                args.checkout,
                args.revision,
                args.output,
                timeout_seconds=args.timeout_seconds,
            )
        elif args.command == "verify":
            result = core.verify_package(args.package)
        elif args.command == "restore":
            result = core.restore_package(args.package, args.output)
        else:
            result = core.reconstruct_package(
                args.package,
                args.checkout,
                args.revision,
                args.output,
                timeout_seconds=args.timeout_seconds,
            )
    except (OSError, ValueError, KeyError, TypeError, RecursionError, KeyboardInterrupt) as error:
        result = {
            "schema": core.RESULT_SCHEMA,
            "operation": args.command,
            "status": "failed",
            "task": getattr(args, "task", None),
            "package_identity": None,
            "integrity_verified": False,
            "reconstruction_verified": False,
            "complete": None,
            "reader_revision": getattr(args, "revision", None),
            "error": type(error).__name__ + ": " + str(error)[:500],
        }
    print(storage.encoded(result).decode(), end="")
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
