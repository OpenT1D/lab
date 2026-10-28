"""Fixed campaign CLI operations and authoritative, separate cached report snapshots."""

import argparse
import json
import signal
import sys
from pathlib import Path

from experiments.maintained_campaigns import common
from experiments.maintained_campaigns.process import Control, supervise
from experiments.platform_files import is_link
from experiments.platform_process import handled_signals

from .campaigns import ARTIFACTS, RESULT, atomic, identity, validate_freeze, validate_request
from .service import MAX_REPORT, bounded_bytes, decode_json, digest, encode, inventory, read_json


def checked_identity(result):
    common.require(
        isinstance(result, dict)
        and result.get("ready") is True
        and result.get("schema") == common.PREPARATION_SCHEMA,
        "Campaign readiness check failed",
    )
    return digest(
        encode(
            {
                key: result[key]
                for key in (
                    "config_sha256",
                    "protocol_sha256",
                    "source_sha256",
                    "runtime_identity",
                )
            }
        )
    )


def owned_path(root, path):
    """Recheck every owned component before dispatch, including replaced ancestors."""
    path = Path(path).absolute()
    common.require(root == path or root in path.parents, "Campaign path escapes own workspace")
    for component in (path, *path.parents):
        common.require(not is_link(component), "Campaign workspace path is a symlink")
        if component == root:
            break
    return path


def log_result(path):
    # CLI output is captured as evidence; only a bounded last JSON line is parsed.
    raw = bounded_bytes(path, MAX_REPORT + 65536)
    for line in reversed(raw.splitlines()):
        try:
            value = decode_json(line)
            if isinstance(value, dict):
                return value
        except (ValueError, UnicodeDecodeError):
            continue
    raise ValueError("CLI returned no bounded JSON result")


def invoke(argv, logfile, timeout, control):
    code, error = supervise(argv, logfile, timeout, control, grace_seconds=90)
    result = None
    try:
        result = log_result(logfile)
    except (OSError, ValueError):
        pass
    return code, error, result


def bind_archive(archive, frozen, matrix):
    """Bind an authoritative campaign to these GUI-owned immutable cell bytes."""
    common.require(
        bounded_bytes(archive / "config.json", 65536)
        == bounded_bytes(frozen / "matrix.json", 65536),
        "Native campaign matrix differs from own GUI configuration",
    )
    for cell in matrix["cells"]:
        original = frozen / cell["config"]
        archived = archive / "frozen" / cell["id"]
        common.require(
            bounded_bytes(archived / "original-config.json", 65536)
            == bounded_bytes(original, 65536),
            "Native campaign cell differs from own GUI configuration",
        )
        config = decode_json(bounded_bytes(original, 65536))
        for source in config["sources"]:
            for key, name, maximum in (
                ("model", "model.py", 1048576),
                ("declaration", "model.json", 65536),
            ):
                common.require(
                    bounded_bytes(archived / "sources" / source["id"] / name, maximum)
                    == bounded_bytes(original.parent / source[key], maximum),
                    "Native campaign source differs from own GUI configuration",
                )


def execute(request, output, *, runner=invoke):
    request = validate_request(request)
    output = Path(output).absolute()
    identity(output.name, "job")
    common.require(
        output.parent.name == "gui"
        and output.parent.parent.name == "results"
        and output.is_dir()
        and not output.is_symlink(),
        "Campaign worker requires an owned GUI job folder",
    )
    root = output.parents[2]
    owned_path(root, output)
    data = output.parent / "campaigns"
    configuration = data / "configurations" / request["configuration_id"]
    frozen = configuration / "frozen"
    operation = request["operation"]
    archive = (
        None
        if request["campaign_id"] is None
        else data / "archives" / request["campaign_id"] / "campaign"
    )
    result = {
        "schema": RESULT,
        "operation": operation,
        "request_sha256": digest(encode(request)),
        "configuration_id": request["configuration_id"],
        "campaign_id": request["campaign_id"],
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
        "summary": None,
        "forensic_unsealed": False,
    }
    control = Control()

    def stop(signum, _frame=None):
        if control.signal is None:
            control.stop(signum)

    previous = {signum: signal.signal(signum, stop) for signum in handled_signals()}
    cli = [
        sys.executable,
        "-B",
        "-E",
        "-s",
        "-S",
        "-m",
        "experiments.maintained_campaigns",
    ]
    before = None
    try:
        for path in (frozen, output / "snapshot"):
            owned_path(root, path)
        matrix = validate_freeze(frozen, request)
        config_path = frozen / "matrix.json"
        if archive is not None:
            owned_path(root, archive)
            pointer_path = owned_path(root, data / "entries" / (request["campaign_id"] + ".json"))
            pointer = read_json(pointer_path)
            common.require(
                isinstance(pointer, dict)
                and pointer["id"] == request["campaign_id"]
                and pointer["configuration_id"] == request["configuration_id"],
                "Worker campaign pointer differs",
            )
            origin = read_json(
                owned_path(
                    root, output.parent / identity(pointer["creator_job"], "job") / "job.json"
                )
            )
            common.require(
                isinstance(origin, dict)
                and origin["operation"] == "campaign_run"
                and origin["request"]["campaign_id"] == pointer["id"]
                and origin["request"]["configuration_id"] == pointer["configuration_id"],
                "Worker campaign has no own originating job",
            )
            if operation == "campaign_run":
                common.require(not archive.exists(), "Campaign run requires a fresh archive")
                archive.parent.mkdir(parents=True, exist_ok=True)
            else:
                bind_archive(archive, frozen, matrix)
                before = inventory(archive, files=True)
                if request["expected_inventory"] is not None:
                    common.require(
                        digest(encode(before)) == request["expected_inventory"],
                        "Campaign archive changed since the previous worker snapshot",
                    )
        if operation == "campaign_install":
            setup = [sys.executable, "-B", "-E", "-s", "-S", "-m", "experiments.setup"]
            code, error, _ = runner(
                setup + ["plan", "m4-study-secure", "--output", str(output / "setup-plan")],
                output / "setup-plan.log",
                60,
                control,
            )
            common.require(
                code == 0 and error is None and control.signal is None,
                "Explicit setup planning failed/interrupted",
            )
            code, error, receipt = runner(
                setup
                + [
                    "install",
                    "--plan",
                    str(output / "setup-plan"),
                    "--output",
                    str(output / "setup-receipt"),
                ],
                output / "setup-install.log",
                1800,
                control,
            )
            common.require(
                code == 0
                and error is None
                and control.signal is None
                and isinstance(receipt, dict)
                and receipt.get("ready") is True,
                "Explicit installation failed/interrupted",
            )
            result["status"] = "completed"
        else:
            if operation in {"campaign_check", "campaign_run", "campaign_resume"}:
                code, error, prepared = runner(
                    cli + ["check", "--config", str(config_path)],
                    output / "campaign-check.log",
                    180,
                    control,
                )
                common.require(
                    code == 0 and error is None and control.signal is None,
                    "Campaign readiness check failed/interrupted",
                )
                selected = checked_identity(prepared)
                common.require(
                    prepared["config_sha256"] == request["matrix_sha256"],
                    "Readiness checked a different frozen matrix",
                )
                result["checked_identity"] = selected
                if operation == "campaign_check":
                    result.update(status="completed", ready=True)
                elif selected != request["checked_identity"]:
                    result["readiness_changed"] = True
                    raise ValueError(
                        "Campaign runtime/source identity changed; check this configuration again"
                    )
            if operation in {"campaign_run", "campaign_resume"}:
                owned_path(root, archive)
                owned_path(root, frozen)
                validate_freeze(frozen, request)
                common.require(
                    control.signal is None, "Campaign operation cancelled before dispatch"
                )
                args = (
                    ["run", "--config", str(config_path), "--output", str(archive)]
                    if operation == "campaign_run"
                    else ["resume", "--campaign", str(archive)]
                )
                budget = len(common.slots(matrix)) * (matrix["timeout_seconds"] + 30) + 600
                code, error, _ = runner(
                    cli + args, output / "campaign-execution.log", budget, control
                )
                result["native_exit_code"] = code
                # Cooperative failure/interruption can still leave authoritative sealed
                # evidence. Reconstruction executes no candidate and uses a fresh child.
                if archive.is_dir():
                    owned_path(root, archive)
                    bind_archive(archive, frozen, matrix)
                    before = inventory(archive, files=True)
                else:
                    raise ValueError("Campaign produced no native archive")
                if error not in {None, "WorkerExit", "GlobalInterruption"}:
                    result["error"] = error
            if operation in {"campaign_run", "campaign_resume", "campaign_reconstruct"}:
                owned_path(root, archive)
                owned_path(root, output / "snapshot")
                common.require(before is not None, "Campaign archive inventory is unavailable")
                result["source_inventory_sha256"] = digest(encode(before))
                derived_control = Control() if control.signal is not None else control
                code, error, reconstructed = runner(
                    cli
                    + [
                        "reconstruct",
                        "--campaign",
                        str(archive),
                        "--output",
                        str(output / "snapshot"),
                        "--allow-failed",
                    ],
                    output / "campaign-reconstruct.log",
                    600,
                    derived_control,
                )
                common.require(
                    inventory(archive, files=True) == before,
                    "Campaign source archive changed during reconstruction",
                )
                common.require(
                    code == 0
                    and error is None
                    and isinstance(reconstructed, dict)
                    and reconstructed.get("schema") == common.REPORT_SCHEMA,
                    "Authoritative campaign reconstruction failed",
                )
                saved = read_json(owned_path(root, output / "snapshot/report.json"), MAX_REPORT)
                common.require(saved == reconstructed, "CLI and saved campaign reports differ")
                expected_cases = matrix["repeats"] * sum(
                    len(child["sources"]) * len(child["scenarios"])
                    for child in (
                        read_json(frozen / cell["config"], 65536) for cell in matrix["cells"]
                    )
                )
                common.require(
                    saved["planned_slots"] == len(common.slots(matrix))
                    and saved["planned_source_scenarios"] == expected_cases,
                    "Campaign report frozen denominators differ",
                )
                result.update(
                    verification="native_reader_verified",
                    report_completeness="complete" if saved["passed"] else "failed",
                    artifacts_sha256={
                        name: digest(bounded_bytes(output / "snapshot" / name, MAX_REPORT))
                        for name in ARTIFACTS
                    },
                    summary={
                        key: saved[key]
                        for key in (
                            "status",
                            "passed",
                            "planned_slots",
                            "accepted_slots",
                            "planned_source_scenarios",
                            "accepted_source_scenarios",
                        )
                    },
                )
                result["status"] = (
                    "completed"
                    if operation == "campaign_reconstruct"
                    or result["native_exit_code"] == 0
                    and result["error"] is None
                    else "failed"
                )
        owned_path(root, frozen)
        validate_freeze(frozen, request)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        result.update(status="failed", ready=False)
        message = type(error).__name__ + ": " + str(error)[:300]
        if control.signal is not None and str(error) in {
            "Campaign readiness check failed/interrupted",
            "Campaign operation cancelled before dispatch",
            "Explicit setup planning failed/interrupted",
            "Explicit installation failed/interrupted",
            "Campaign produced no native archive",
        }:
            result["diagnostic"] = message
        else:
            result["error"] = message
        if operation in {"campaign_run", "campaign_resume"} and result["native_exit_code"] is None:
            result["readiness_changed"] = True
        if archive is not None and archive.is_dir():
            try:
                owned_path(root, archive)
                result["source_inventory_sha256"] = inventory(archive)
                sessions = sorted((archive / "sessions").iterdir())
                result["forensic_unsealed"] = bool(
                    sessions and not (sessions[-1] / "manifest.json").is_file()
                )
            except (OSError, ValueError):
                pass
            result["verification"] = "verification_failed"
    finally:
        result["interruption_signal"] = control.signal
        if control.signal is not None:
            result["status"] = "cancelled"
        try:
            atomic(owned_path(root, output / "campaign-result.json"), result)
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    common.require(
        args.request.parent.resolve(strict=True) == output,
        "Worker request must belong to its own job folder",
    )
    result = execute(read_json(args.request), output)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
