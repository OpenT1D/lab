"""Installed task commands sharing the Python process-proxy API."""

import argparse
import json

from .api import (
    Project,
    attach_runtimes,
    create_project,
    example,
    inspect_inputs,
    installation,
    prepare_development,
    validate,
)


def _inputs(args):
    if args.task not in {"mmtt-sensitivity", "mmtt-sampling"}:
        if not args.config:
            raise ValueError("This task requires --config")
        return {"config.json": args.config}
    if not all((args.package, args.csv, args.settings)):
        raise ValueError("MMTT requires --package, --csv and --settings")
    inputs = {
        "package.json": args.package,
        "observations.csv": args.csv,
        "settings.json": args.settings,
    }
    if args.task == "mmtt-sampling":
        if not all((args.design, args.development_import)):
            raise ValueError("Sampling requires --design and --development-import")
        inputs.update({"design.json": args.design, "development": args.development_import})
    return inputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("installation")
    command = commands.add_parser("prepare-study-packet")
    command.add_argument("--reference-project", required=True)
    for role in ("mmtt", "fasting", "load15", "failed"):
        command.add_argument("--" + role + "-attempt", required=True)
    command.add_argument("--output", required=True)
    command = commands.add_parser("verify-study-packet")
    command.add_argument("--packet", required=True)
    command = commands.add_parser("gui")
    command.add_argument("--workspace", required=True)
    command.add_argument("--port", type=int, default=0)
    command.add_argument("--runtime-attachment")
    command = commands.add_parser("attach-runtimes")
    command.add_argument("--native-site", required=True)
    command.add_argument("--observer-site", required=True)
    command.add_argument("--output", required=True)
    command = commands.add_parser("create")
    command.add_argument("--project", required=True)
    command.add_argument("--name", required=True)
    command = commands.add_parser("example")
    command.add_argument(
        "--task",
        choices=(
            "mmtt-sensitivity",
            "m4-study-secure",
            "m4-study-installed",
            "mmtt-sampling",
            "m3-compare",
        ),
        required=True,
    )
    command.add_argument("--output", required=True)
    command.add_argument(
        "--case",
        default="complete",
        choices=(
            "complete",
            "censored",
            "fasting",
            "gastric_load_15g",
            "information-loss",
            "constant",
            "incomplete",
            "steep-response",
        ),
    )
    for operation in ("validate", "inspect", "freeze"):
        command = commands.add_parser(operation)
        command.add_argument(
            "--task",
            choices=(
                "mmtt-sensitivity",
                "m4-study-secure",
                "m4-study-installed",
                "mmtt-sampling",
                "m3-compare",
            ),
            required=True,
        )
        for name in ("config", "package", "csv", "settings", "design", "development-import"):
            command.add_argument("--" + name)
        if operation == "freeze":
            command.add_argument("--project", required=True)
            command.add_argument("--parent")
    for operation in (
        "info",
        "plan",
        "check",
        "run",
        "reconstruct",
        "import",
        "relocate",
        "recover",
        "export-inputs",
    ):
        command = commands.add_parser(operation)
        command.add_argument("--project", required=True)
        if operation in ("plan", "check", "run", "import", "export-inputs"):
            command.add_argument("--plan", required=True)
        if operation in ("run", "import"):
            command.add_argument("--retry-of")
        if operation in ("check", "run"):
            command.add_argument("--runtime-attachment")
        if operation == "run":
            command.add_argument("--timeout", type=float, default=600)
        if operation in ("reconstruct", "recover"):
            command.add_argument("--attempt", required=True)
        if operation in ("reconstruct", "relocate", "export-inputs"):
            command.add_argument("--output", required=True)
        if operation == "reconstruct":
            command.add_argument("--allow-failed", action="store_true")
        if operation == "import":
            command.add_argument("--archive", required=True)
        if operation == "recover":
            command.add_argument("--execution-stopped", action="store_true")
    command = commands.add_parser("prepare-development")
    for name in ("package", "csv", "design", "output"):
        command.add_argument("--" + name, required=True)
    for operation in (
        "comparison-options",
        "freeze-comparison",
        "comparison",
        "reconstruct-comparison",
    ):
        command = commands.add_parser(operation)
        command.add_argument("--project", required=True)
        if operation == "comparison-options":
            command.add_argument("--plan", required=True)
        elif operation == "freeze-comparison":
            command.add_argument("--definition", required=True)
        else:
            command.add_argument("--comparison", required=True)
            command.add_argument("--at")
        if operation == "reconstruct-comparison":
            command.add_argument("--output", required=True)
    for operation in ("freeze-study", "study", "materialize-study", "reconstruct-study"):
        command = commands.add_parser(operation)
        command.add_argument("--project", required=True)
        if operation == "freeze-study":
            command.add_argument("--name", required=True)
            command.add_argument("--question", required=True)
            command.add_argument("--forward-plan")
            command.add_argument(
                "--observation-case", default="complete", choices=("complete", "missing-evaluation")
            )
        else:
            command.add_argument("--study", required=True)
        if operation in {"study", "reconstruct-study"}:
            command.add_argument("--at")
        if operation == "reconstruct-study":
            command.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action in {"prepare-study-packet", "verify-study-packet"}:
            from . import study_packet

            if args.action == "verify-study-packet":
                result = study_packet.verify(args.packet)
            else:
                result = study_packet.create(
                    args.reference_project,
                    {
                        role: getattr(args, role + "_attempt")
                        for role in ("mmtt", "fasting", "load15", "failed")
                    },
                    args.output,
                )
            print(json.dumps(result, sort_keys=True))
            return 0
        if args.action == "gui":
            from .gui import serve

            serve(args.workspace, port=args.port, runtime_attachment=args.runtime_attachment)
            return 0
        project = Project(args.project) if hasattr(args, "project") else None
        if args.action == "installation":
            result = installation()
        elif args.action == "freeze-study":
            result = project.freeze_study(
                args.name,
                args.question,
                forward_plan=args.forward_plan,
                observation_case=args.observation_case,
            )
        elif args.action == "study":
            result = project.study(args.study, at=args.at)
        elif args.action == "materialize-study":
            result = project.materialize_study(args.study)
        elif args.action == "reconstruct-study":
            result = project.reconstruct_study(args.study, args.output, at=args.at)
        elif args.action == "comparison-options":
            result = project.comparison_options(args.plan)
        elif args.action == "freeze-comparison":
            from ._gui_files import decode, read

            result = project.freeze_comparison(decode(read(args.definition, 65536)))
        elif args.action == "comparison":
            result = project.comparison(args.comparison, at=args.at)
        elif args.action == "reconstruct-comparison":
            result = project.reconstruct_comparison(args.comparison, args.output, at=args.at)
        elif args.action == "prepare-development":
            result = prepare_development(args.package, args.csv, args.design, args.output)
        elif args.action == "attach-runtimes":
            result = attach_runtimes(args.native_site, args.observer_site, args.output)
        elif args.action == "create":
            result = create_project(args.project, args.name).info()
        elif args.action == "example":
            result = example(args.task, args.output, case=args.case)
        elif args.action == "validate":
            result = validate(args.task, _inputs(args))
        elif args.action == "inspect":
            result = inspect_inputs(args.task, _inputs(args))
        elif args.action == "freeze":
            result = project.freeze(args.task, _inputs(args), parent=args.parent)
        elif args.action == "run":
            result = project.run(
                args.plan,
                retry_of=args.retry_of,
                timeout=args.timeout,
                runtime_attachment=args.runtime_attachment,
            )
        elif args.action == "reconstruct":
            result = project.reconstruct(args.attempt, args.output, allow_failed=args.allow_failed)
        elif args.action == "import":
            result = project.import_attempt(args.plan, args.archive, retry_of=args.retry_of)
        elif args.action == "relocate":
            result = project.relocate(args.output)
        elif args.action == "recover":
            result = project.recover(args.attempt, execution_stopped=args.execution_stopped)
        elif args.action == "check":
            result = project.check(args.plan, runtime_attachment=args.runtime_attachment)
        elif args.action == "plan":
            result = project.plan(args.plan)
        elif args.action == "export-inputs":
            result = project.export_inputs(args.plan, args.output)
        else:
            result = project.info()
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 1 if args.action == "run" and result["result"]["completeness"] != "complete" else 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({"status": "refused", "error": str(error)}))
        return 2
