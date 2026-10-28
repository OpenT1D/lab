"""Discover, passively check and explicitly execute the supported local tasks."""

import argparse
import json
from pathlib import Path

from .checks import check
from .dispatch import execute
from .registry import TASKS, VERSION


def task_options(parser, task):
    parser.add_argument("--" + task.input_option, type=Path, required=True)
    if task.id == "p1-controller":
        parser.add_argument("--profile", choices=("adult#001", "adult#002"), default="adult#001")
        parser.add_argument("--seed", type=int, choices=(101, 102), default=101)
    elif task.id == "m3-forecast":
        parser.add_argument("--timeout", type=float, default=120)
    elif task.id in ("m4-secretion", "m4-compare", "m4-study", "m4-study-secure"):
        parser.add_argument("--reference", type=Path)
    elif task.id == "m5-prognosis":
        parser.add_argument("--timeout-seconds", type=float, default=5)


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    operations = root.add_subparsers(dest="operation", required=True)
    operations.add_parser("list", help="List the explicitly supported tasks")
    describe = operations.add_parser("describe", help="Show task inputs and canonical guide")
    describe.add_argument("task", choices=TASKS)
    for operation in ("check", "run", "reconstruct"):
        command = operations.add_parser(operation)
        tasks = command.add_subparsers(dest="task", required=True)
        for task in TASKS.values():
            command = tasks.add_parser(task.id, help=task.title)
            command.add_argument("--admission-prepare-seconds", type=float)
            command.add_argument("--operation-seconds", type=float)
            command.add_argument("--phase-state", type=Path)
            if operation == "reconstruct":
                command.add_argument("--archive", type=Path, required=True)
                if task.reconstruction_output:
                    command.add_argument("--output", type=Path, required=True)
                if task.id in (
                    "m4-secretion",
                    "m4-compare",
                    "m4-study",
                    "m4-study-secure",
                    "mmtt-sensitivity",
                    "mmtt-sampling",
                ):
                    command.add_argument("--allow-failed", action="store_true")
            else:
                task_options(command, task)
                if operation == "run":
                    command.add_argument("--output", type=Path, required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.operation == "list":
            result = {
                "schema": VERSION,
                "operation": "list",
                "tasks": [task.describe() for task in TASKS.values()],
            }
        elif args.operation == "describe":
            result = {"schema": VERSION, "operation": "describe", **TASKS[args.task].describe()}
        elif args.operation == "check":
            result = check(TASKS[args.task], args)
        else:
            result = execute(TASKS[args.task], args, operation=args.operation)
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        result = {
            "schema": VERSION,
            "operation": args.operation,
            "task": getattr(args, "task", None),
            "entry_error": str(error),
            "error_type": getattr(error, "error_type", type(error).__name__),
            "child_exit_code": None,
            "report_completeness": "unavailable",
        }
        forwarded = getattr(error, "forwarded_signal", None)
        if forwarded is not None:
            result.update(forwarded_signal=forwarded, child_exit_code=-forwarded)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    if "entry_error" in result:
        return 128 + result["forwarded_signal"] if result.get("forwarded_signal") else 2
    if args.operation == "check":
        return 0 if result["ready"] else 2
    code = result.get("child_exit_code")
    return 128 - code if code is not None and code < 0 else (code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
