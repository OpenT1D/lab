"""Fixed existing M3 CLI routes with owned cleanup and immutable native reports."""

import argparse
import json
import signal
import sys
from pathlib import Path

from experiments.maintained_campaigns.process import Control, supervise
from experiments.platform_process import handled_signals

from .campaign_worker import log_result, owned_path
from .m3 import (
    ARTIFACTS,
    MAX_CONFIG,
    RESULT,
    comparison,
    forecast,
    identity,
    require,
    validate_freeze,
    validate_report,
    validate_request,
)
from .packaged_phases import command as phased_command
from .service import MAX_REPORT, bounded_bytes, digest, encode, inventory, read_json


def invoke(argv, logfile, timeout, control):
    # Packaged coordinators own a separate 30-second cleanup allowance.
    # The GUI reserves 60 seconds, leaving room for this owner's final receipt.
    grace = 40 if "--admission-prepare-seconds" in argv else 20
    code, error = supervise(argv, logfile, timeout, control, grace_seconds=grace)
    result = None
    try:
        result = log_result(logfile)
    except (OSError, ValueError):
        pass
    return code, error, result


def checked_identity(result, request):
    require(
        isinstance(result, dict)
        and result.get("schema") == "opent1d.workflow-entry/1"
        and result.get("task") == request["task"]
        and result.get("ready") is True
        and result.get("metadata_valid") is True
        and result.get("observation_bytes_verified") is False,
        "M3 native metadata/runtime check failed",
    )
    sources = (
        forecast.provenance if request["task"] == "m3-forecast" else comparison.provenance
    )()["sources"]
    return digest(
        encode(
            {
                "task": request["task"],
                "config_sha256": request["config_sha256"],
                "freeze_sha256": request["freeze_sha256"],
                "sources": sources,
                **{
                    key: result[key]
                    for key in ("metadata", "runtimes", "uv", "observation_path_issues")
                },
            }
        )
    )


def bind_archive(archive, frozen, task):
    plan = read_json(archive / "plan.json", MAX_CONFIG * 2)
    config = read_json(frozen / "config.json", MAX_CONFIG)
    require(plan["config"] == config, "Native M3 plan differs from the frozen GUI configuration")
    if task == "m3-forecast":
        expected = read_json(Path(config["predictor"]), 65536)
        require(plan["predictor"] == expected, "Native M3 forecast declaration differs")
        for name, key in (("source.py", "source"), ("settings.json", "settings")):
            require(
                bounded_bytes(archive / "predictor" / name, 1048576)
                == bounded_bytes(Path(expected[key]["file"]), 1048576),
                "Native M3 forecast source/settings differs",
            )
    else:
        for candidate in config["candidates"]:
            target = archive / "frozen" / candidate["id"]
            original = Path(candidate["declaration"])
            declaration = read_json(original, 65536)
            require(
                bounded_bytes(target / "original-declaration.json", 65536)
                == bounded_bytes(original, 65536),
                "Native M3 comparison declaration differs",
            )
            for name, key in (("source.py", "source"), ("settings.json", "settings")):
                require(
                    bounded_bytes(target / name, 1048576)
                    == bounded_bytes(Path(declaration[key]["file"]), 1048576),
                    "Native M3 comparison source/settings differs",
                )


def execute(request, output, *, runner=invoke):
    request = validate_request(request)
    output = Path(output).absolute()
    identity(output.name, "job")
    require(
        output.parent.name == "gui"
        and output.parent.parent.name == "results"
        and output.is_dir()
        and not output.is_symlink(),
        "M3 worker needs an owned GUI job folder",
    )
    root = output.parents[2]
    owned_path(root, output)
    data = output.parent / "m3"
    operation, task = request["operation"], request["task"]
    frozen = (
        None
        if request["configuration_id"] is None
        else data / "configurations" / request["configuration_id"] / "frozen"
    )
    archive = (
        None if request["entry_id"] is None else data / "archives" / request["entry_id"] / "archive"
    )
    result = {
        "schema": RESULT,
        "operation": operation,
        "task": task,
        "request_sha256": digest(encode(request)),
        "input_id": request["input_id"],
        "configuration_id": request["configuration_id"],
        "entry_id": request["entry_id"],
        "status": "failed",
        "error": None,
        "diagnostic": None,
        "ready": False,
        "checked_identity": None,
        "readiness_changed": False,
        "native_exit_code": None,
        "interruption_signal": None,
        "verification": "not_requested",
        "report_completeness": "unavailable",
        "source_inventory_sha256": None,
        "artifacts_sha256": {},
        "forensic_unsealed": False,
        "summary": None,
    }
    control = Control()

    def stop(signum, _frame=None):
        if control.signal is None:
            control.stop(signum)

    previous = {number: signal.signal(number, stop) for number in handled_signals()}
    cli = [sys.executable, "-B", "-E", "-s", "-S", "-m", "experiments.workflows"]
    before, record = None, None
    packaged_run = False
    try:
        if operation == "m3_fixture":
            fixture = owned_path(root, data / "inputs" / request["input_id"])
            require(not fixture.exists(), "M3 fixture requires a fresh owned folder")
            code, error, _ = runner(
                [
                    sys.executable,
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.m3.comparison",
                    "fixture",
                    "--output",
                    str(fixture),
                ],
                output / "m3-fixture.log",
                90,
                control,
            )
            require(
                code == 0 and error is None and control.signal is None,
                "Explicit synthetic fixture preparation failed/interrupted",
            )
            owned_path(root, fixture)
            result["status"] = "completed"
        else:
            owned_path(root, frozen)
            owned_path(root, output / "snapshot")
            config = None if operation == "m3_reconstruct" else validate_freeze(frozen, request)
            config_path = frozen / "config.json"
            record = read_json(owned_path(root, frozen.parent / "record.json"))
            require(
                record["task"] == task
                and record["id"] == request["configuration_id"]
                and record["config_sha256"] == request["config_sha256"]
                and record["freeze_sha256"] == request["freeze_sha256"],
                "M3 worker configuration pointer differs",
            )
            if operation != "m3_reconstruct":
                prepared = read_json(frozen / "preparation.json")
                require(
                    all(
                        record[key] == prepared[key]
                        for key in ("task", "candidate_ids", "timeout_seconds")
                    )
                    and record["planned_people"] == len(config["people"])
                    and record["planned_origins"]
                    == {p["id"]: len(p["origins_us"]) for p in config["people"]},
                    "M3 administration differs from its immutable preparation",
                )
            if archive is not None:
                owned_path(root, archive)
                pointer = read_json(
                    owned_path(root, data / "entries" / (request["entry_id"] + ".json"))
                )
                origin = read_json(
                    owned_path(
                        root, output.parent / identity(pointer["creator_job"], "job") / "job.json"
                    )
                )
                require(
                    pointer["id"] == request["entry_id"]
                    and pointer["task"] == task
                    and pointer["configuration_id"] == request["configuration_id"]
                    and origin["operation"] == "m3_run"
                    and origin["task"] == task
                    and origin["request"]["entry_id"] == pointer["id"]
                    and origin["request"]["configuration_id"] == pointer["configuration_id"]
                    and origin["request"]["config_sha256"] == request["config_sha256"]
                    and origin["request"]["freeze_sha256"] == request["freeze_sha256"],
                    "M3 archive has no matching own originating job",
                )
                if operation == "m3_run":
                    require(not archive.exists(), "M3 run requires a fresh archive")
                    archive.parent.mkdir(parents=True, exist_ok=True)
                else:
                    plan = read_json(archive / "plan.json", MAX_CONFIG * 2)
                    config = plan["config"]
                    require(
                        digest(encode(config)) == request["config_sha256"],
                        "Saved native M3 plan differs from the own frozen run identity",
                    )
                    before = inventory(archive, files=True)
                    if request["expected_inventory"] is not None:
                        require(
                            digest(encode(before)) == request["expected_inventory"],
                            "M3 archive changed since its previous snapshot",
                        )
            check_args = ["check", task, "--config", str(config_path)]
            if task == "m3-forecast":
                check_args.extend(["--timeout", str(record["timeout_seconds"])])
            if operation in {"m3_check", "m3_run"}:
                command, budget = phased_command(
                    cli + check_args,
                    task,
                    output,
                    120,
                    phase_name="m3-check-phase.json",
                )
                code, error, checked = runner(command, output / "m3-check.log", budget, control)
                require(
                    code == 0 and error is None and control.signal is None,
                    "M3 metadata/runtime check failed/interrupted",
                )
                current = checked_identity(checked, request)
                validate_freeze(frozen, request)
                result["checked_identity"] = current
                result["metadata_check"] = checked
                if operation == "m3_check":
                    result.update(status="completed", ready=True)
                else:
                    require(
                        current == request["checked_identity"],
                        "M3 runtime, source or metadata changed; "
                        "check the frozen preparation again",
                    )
            if operation == "m3_run":
                require(control.signal is None, "M3 cancelled before native dispatch")
                args = ["run", task, "--config", str(config_path), "--output", str(archive)]
                if task == "m3-forecast":
                    args.extend(["--timeout", str(record["timeout_seconds"])])
                deadline = 120 + len(config["people"]) * len(record["candidate_ids"]) * (
                    record["timeout_seconds"] + 10
                )
                command, budget = phased_command(
                    cli + args,
                    task,
                    output,
                    120,
                    deadline,
                    phase_name="m3-run-phase.json",
                )
                packaged_run = "--admission-prepare-seconds" in command
                code, error, _ = runner(command, output / "m3-execution.log", budget, control)
                result["native_exit_code"] = code
                require(archive.is_dir(), "M3 execution produced no native archive")
                owned_path(root, archive)
                before = inventory(archive, files=True)
                result["source_inventory_sha256"] = digest(encode(before))
                if "manifest.json" not in before:
                    result.update(
                        status="failed",
                        verification="verification_failed",
                        forensic_unsealed=True,
                        diagnostic=(
                            "Native parent is unsealed; retained raw bytes "
                            "are forensic evidence only"
                        ),
                    )
                else:
                    bind_archive(archive, frozen, task)
                    require(
                        error in {None, "WorkerExit", "GlobalInterruption"},
                        "M3 execution cleanup or deadline failed",
                    )
            if (
                operation == "m3_reconstruct"
                or operation == "m3_run"
                and not result["forensic_unsealed"]
                and not (packaged_run and control.signal is not None)
            ):
                require(before is not None, "M3 native archive inventory unavailable")
                result["source_inventory_sha256"] = digest(encode(before))
                # A cooperative cancellation can preserve a valid incomplete sealed parent.
                # Its separate reader never executes candidate code or original observations.
                read_control = Control() if control.signal is not None else control
                command, budget = phased_command(
                    cli
                    + [
                        "reconstruct",
                        task,
                        "--archive",
                        str(archive),
                        "--output",
                        str(output / "snapshot"),
                    ],
                    task,
                    output,
                    120,
                    120,
                    reconstruction=True,
                    phase_name="m3-reconstruct-phase.json",
                )
                code, error, _ = runner(
                    command,
                    output / "m3-reconstruct.log",
                    budget,
                    read_control,
                )
                require(code == 0 and error is None, "Authoritative M3 reconstruction failed")
                require(
                    inventory(archive, files=True) == before,
                    "M3 source archive changed during reconstruction",
                )
                saved = validate_report(
                    read_json(output / "snapshot/report.json", MAX_REPORT), record
                )
                artifacts = {
                    name: digest(bounded_bytes(output / "snapshot" / name, MAX_REPORT))
                    for name in ARTIFACTS
                }
                for name in ARTIFACTS:
                    if name in before:
                        require(
                            before[name] == artifacts[name],
                            "Rebuilt M3 report differs from original native bytes",
                        )
                evaluation = saved["evaluation"] if task == "m3-forecast" else saved["common"]
                result.update(
                    verification="native_reader_verified",
                    artifacts_sha256=artifacts,
                    report_completeness="complete"
                    if evaluation["complete_cohort"]
                    else "incomplete",
                    summary={
                        "planned_people": evaluation["planned_people"],
                        "contributing_people": evaluation["contributing_people"],
                        "complete_cohort": evaluation["complete_cohort"],
                    },
                )
                result["status"] = (
                    "completed"
                    if operation == "m3_reconstruct" or result["native_exit_code"] == 0
                    else "failed"
                )
            if packaged_run and control.signal is not None and not result["forensic_unsealed"]:
                result["diagnostic"] = (
                    "Cancelled; preserved native archive requires a separate saved-analysis check"
                )
            if operation != "m3_reconstruct":
                validate_freeze(frozen, request)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        message = type(error).__name__ + ": " + str(error)[:500]
        result["status"] = "failed"
        if control.signal is not None:
            result["diagnostic"] = message
        else:
            result["error"] = message
        result["ready"] = False
        if operation == "m3_run" and result["native_exit_code"] is None:
            result["readiness_changed"] = True
        if archive is not None and archive.is_dir():
            try:
                owned_path(root, archive)
                result["source_inventory_sha256"] = inventory(archive)
                result["forensic_unsealed"] = not (archive / "manifest.json").is_file()
            except (OSError, ValueError):
                pass
            result["verification"] = "verification_failed"
    finally:
        result["interruption_signal"] = control.signal
        if control.signal is not None:
            result["status"] = "cancelled"
        try:
            (output / "m3-result.json").write_bytes(encode(result))
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    require(
        args.request.parent.resolve(strict=True) == output,
        "M3 request must belong to its own job folder",
    )
    result = execute(read_json(args.request), output)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
