"""The two-route installed command line, sharing the Python process-proxy API."""

import argparse
import json

from .api import Project, create_project, example, installation, validate


def _inputs(args):
    if args.task == "m4-study-secure":
        if not args.config:
            raise ValueError("M4 requires --config")
        return {"config.json": args.config}
    if not all((args.package, args.csv, args.settings)):
        raise ValueError("MMTT requires --package, --csv and --settings")
    return {
        "package.json": args.package,
        "observations.csv": args.csv,
        "settings.json": args.settings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("installation")
    command = commands.add_parser("create")
    command.add_argument("--project", required=True)
    command.add_argument("--name", required=True)
    command = commands.add_parser("example")
    command.add_argument("--task", choices=("mmtt-sensitivity", "m4-study-secure"), required=True)
    command.add_argument("--output", required=True)
    command.add_argument(
        "--case",
        default="complete",
        choices=("complete", "censored", "fasting", "gastric_load_15g"),
    )
    for operation in ("validate", "freeze"):
        command = commands.add_parser(operation)
        command.add_argument(
            "--task", choices=("mmtt-sensitivity", "m4-study-secure"), required=True
        )
        for name in ("config", "package", "csv", "settings"):
            command.add_argument("--" + name)
        if operation == "freeze":
            command.add_argument("--project", required=True)
            command.add_argument("--parent")
    for operation in ("info", "check", "run", "reconstruct", "import", "relocate", "recover"):
        command = commands.add_parser(operation)
        command.add_argument("--project", required=True)
        if operation in ("check", "run", "import"):
            command.add_argument("--plan", required=True)
        if operation in ("run", "import"):
            command.add_argument("--retry-of")
        if operation == "run":
            command.add_argument("--timeout", type=float, default=600)
        if operation in ("reconstruct", "recover"):
            command.add_argument("--attempt", required=True)
        if operation in ("reconstruct", "relocate"):
            command.add_argument("--output", required=True)
        if operation == "reconstruct":
            command.add_argument("--allow-failed", action="store_true")
        if operation == "import":
            command.add_argument("--archive", required=True)
        if operation == "recover":
            command.add_argument("--execution-stopped", action="store_true")
    args = parser.parse_args(argv)
    try:
        project = Project(args.project) if hasattr(args, "project") else None
        if args.action == "installation":
            result = installation()
        elif args.action == "create":
            result = create_project(args.project, args.name).info()
        elif args.action == "example":
            result = example(args.task, args.output, case=args.case)
        elif args.action == "validate":
            result = validate(args.task, _inputs(args))
        elif args.action == "freeze":
            result = project.freeze(args.task, _inputs(args), parent=args.parent)
        elif args.action == "run":
            result = project.run(args.plan, retry_of=args.retry_of, timeout=args.timeout)
        elif args.action == "reconstruct":
            result = project.reconstruct(args.attempt, args.output, allow_failed=args.allow_failed)
        elif args.action == "import":
            result = project.import_attempt(args.plan, args.archive, retry_of=args.retry_of)
        elif args.action == "relocate":
            result = project.relocate(args.output)
        elif args.action == "recover":
            result = project.recover(args.attempt, execution_stopped=args.execution_stopped)
        elif args.action == "check":
            result = project.check(args.plan)
        else:
            result = project.info()
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 1 if args.action == "run" and result["result"]["completeness"] != "complete" else 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({"status": "refused", "error": str(error)}))
        return 2
