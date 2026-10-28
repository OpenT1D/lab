"""Fresh, immutable local campaign sessions with explicit identity-checked resume."""

import copy
import signal
from datetime import UTC, datetime
from pathlib import Path

from experiments.desktop.runtime import interpreter
from experiments.m4.secure_study.locations import join_recorded
from experiments.platform_process import handled_signals

from . import common, native
from .process import Control, supervise


def separate(output, path):
    common.require(
        output != path and output not in path.parents and path not in output.parents,
        "Campaign output overlaps supplied input",
    )


def freeze(config_path, output):
    config, raw, bundles = common.intake(config_path)
    runtimes = common.runtime_identity()
    common.validate_runtime_identity(runtimes)
    p = common.protocol()
    output = Path(output).absolute()
    common.require(not output.is_symlink(), "Campaign output cannot be a symlink")
    output = output.resolve()
    separate(output, Path(config_path).resolve())
    expected = {}
    for name in common.SELF_SOURCES:
        expected[name] = common.digest((common.ROOT / name).read_bytes())
    for bundle in bundles.values():
        metadata = bundle["metadata"]
        separate(output, bundle["config_path"])
        for source in bundle["sources"].values():
            for path in source["paths"]:
                separate(output, path)
        for group in ("implementation_sources_sha256", "runtime_files_sha256"):
            for name, identity in metadata[group].items():
                common.require(
                    name not in expected or expected[name] == identity,
                    "Native implementation/runtime identities disagree between cells",
                )
                expected[name] = identity
    snapshots = {}
    for name, identity in expected.items():
        path = Path(name)
        common.require(
            not path.is_absolute() and ".." not in path.parts and path.as_posix() == name,
            "Unsafe implementation snapshot path",
        )
        _, snapshots[name] = common.regular(common.ROOT / path)
        common.require(
            common.digest(snapshots[name]) == identity,
            "Implementation/runtime changed during freeze",
        )
    output.mkdir(parents=True, exist_ok=False)
    (output / "sessions").mkdir()
    (output / "config.json").write_bytes(raw)
    cells = {}
    for cell in config["cells"]:
        identity, bundle = cell["id"], bundles[cell["id"]]
        folder = output / "frozen" / identity
        folder.mkdir(parents=True)
        (folder / "original-config.json").write_bytes(bundle["config_raw"])
        effective = copy.deepcopy(bundle["metadata"]["configuration"])
        for source in effective["sources"]:
            model_id = source["id"]
            source_folder = folder / "sources" / model_id
            source_folder.mkdir(parents=True)
            (source_folder / "model.py").write_bytes(bundle["sources"][model_id]["model"])
            (source_folder / "model.json").write_bytes(bundle["sources"][model_id]["declaration"])
            source.update(
                model=f"sources/{model_id}/model.py", declaration=f"sources/{model_id}/model.json"
            )
        common.dump(folder / "config.json", effective)
        cells[identity] = {
            "native_metadata": bundle["metadata"],
            "effective_config": effective,
            "effective_config_sha256": common.digest((folder / "config.json").read_bytes()),
            "planned_source_scenarios": len(effective["sources"]) * len(effective["scenarios"]),
        }
    for name, snapshot in snapshots.items():
        path = output / "implementation" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(snapshot)
    plan = {
        "schema": common.VERSION,
        "protocol": p,
        "configuration": config,
        "config_sha256": common.digest(raw),
        "cells": cells,
        "slots": common.slots(config),
        "source_sha256": expected,
        "runtime_identity": runtimes,
    }
    common.dump(output / "plan.json", plan)
    common.dump(
        output / "manifest.json",
        {
            "schema": common.VERSION,
            "files": {
                name: common.digest(data) for name, data in common.root_inventory(output).items()
            },
        },
    )
    return output


def command(campaign, session_number, slot, implementation_root=None, coordinator=None):
    root = common.ROOT if implementation_root is None else Path(implementation_root)
    session = join_recorded(str(campaign), "sessions", f"session-{session_number:04d}")
    return [
        str(interpreter(source_root=root)) if coordinator is None else coordinator,
        "-B",
        "-E",
        "-s",
        "-S",
        "-m",
        "experiments.m4.secure_study",
        "run",
        "--config",
        join_recorded(str(campaign), "frozen", slot["cell"], "config.json"),
        "--output",
        join_recorded(session, "attempts", slot["id"], "archive"),
    ]


def empty_attempt():
    return {
        "status": "not_attempted",
        "error_type": None,
        "exit_code": None,
        "native_manifest_sha256": None,
    }


def session(campaign):
    from .report import inspect, reconstruct

    campaign = Path(campaign).absolute().resolve()
    plan, report = inspect(campaign)
    common.require(
        common.encoded(common.runtime_identity()) == common.encoded(plan["runtime_identity"]),
        "Installed runtime identity changed; completed attempts cannot be reused",
    )
    number = len(report["sessions"]) + 1
    previous = report["sessions"][-1]["manifest_sha256"] if report["sessions"] else None
    schedule = []
    for slot in report["slots"]:
        if not slot["accepted"]:
            attempts = slot["attempts"]
            schedule.append(
                {
                    "id": slot["id"],
                    "cell": slot["cell"],
                    "repeat": slot["repeat"],
                    "attempt": len(attempts) + 1,
                    "previous_attempt_manifest_sha256": attempts[-1]["manifest_sha256"]
                    if attempts
                    else None,
                    "argv": command(
                        campaign,
                        number,
                        slot,
                        coordinator=plan["runtime_identity"]["."]["executable"],
                    ),
                }
            )
    directory = campaign / "sessions" / f"session-{number:04d}"
    directory.mkdir(exist_ok=False)
    session_plan = {
        "schema": common.VERSION,
        "number": number,
        "campaign_sha256": common.digest((campaign / "manifest.json").read_bytes()),
        "previous_session_manifest_sha256": previous,
        "implementation_root": str(common.ROOT),
        "campaign_path": str(campaign),
        "schedule": schedule,
    }
    common.dump(directory / "plan.json", session_plan)
    state = {
        "status": "started",
        "interruption_signal": None,
        "attempts": {item["id"]: empty_attempt() for item in schedule},
    }
    common.dump(directory / "state.json", state)
    control = Control()
    previous_handlers = {
        signum: signal.signal(signum, control.stop) for signum in handled_signals()
    }
    try:
        try:
            for item in schedule:
                if control.signal is not None:
                    break
                # Recheck immutable inputs immediately before every dispatch; earlier callbacks
                # must not alter a later cell's effective configuration or supplied source.
                inspect(campaign, active_session=number)
                if control.signal is not None:
                    break
                attempt = state["attempts"][item["id"]]
                folder = directory / "attempts" / item["id"]
                folder.mkdir(parents=True, exist_ok=False)
                attempt["status"] = "started"
                common.dump(directory / "state.json", state)
                receipt = {
                    "schema": common.VERSION,
                    "slot": item["id"],
                    "attempt": item["attempt"],
                    "previous_attempt_manifest_sha256": item["previous_attempt_manifest_sha256"],
                    "argv": item["argv"],
                    "timeout_seconds": plan["configuration"]["timeout_seconds"],
                    "started_utc": datetime.now(UTC).isoformat(),
                    "outcome": attempt,
                }
                common.dump(folder / "receipt.json", receipt)
                try:
                    code, error = supervise(
                        item["argv"],
                        folder / "command.log",
                        plan["configuration"]["timeout_seconds"],
                        control,
                    )
                    attempt["exit_code"] = code
                    manifest = folder / "archive/manifest.json"
                    if manifest.is_file():
                        attempt["native_manifest_sha256"] = common.digest(manifest.read_bytes())
                    if control.signal is not None:
                        attempt.update(status="interrupted", error_type="GlobalInterruption")
                    elif error is not None:
                        attempt.update(status="failed", error_type=error)
                    else:
                        result = native.reconstruct(folder / "archive")
                        common.require(
                            result.get("passed") is True, "Native study did not completely pass"
                        )
                        common.require(
                            (folder / "archive/config.json").read_bytes()
                            == (campaign / "frozen" / item["cell"] / "config.json").read_bytes(),
                            "Native archive configuration differs from frozen cell",
                        )
                        attempt.update(status="completed", error_type=None)
                except BaseException as error:
                    if isinstance(error, KeyboardInterrupt):
                        control.stop(signal.SIGINT)
                    attempt.update(
                        status="interrupted" if control.signal is not None else "failed",
                        error_type="GlobalInterruption"
                        if control.signal is not None
                        else type(error).__name__,
                    )
                finally:
                    receipt.update(
                        finished_utc=datetime.now(UTC).isoformat(), outcome=copy.deepcopy(attempt)
                    )
                    common.dump(folder / "receipt.json", receipt)
                    common.seal(folder)
                    common.dump(directory / "state.json", state)
            state["status"] = (
                "interrupted"
                if control.signal is not None
                else "failed"
                if any(attempt["status"] == "failed" for attempt in state["attempts"].values())
                else "completed"
            )
        finally:
            if control.signal is not None:
                state.update(status="interrupted", interruption_signal=control.signal)
            if state["status"] == "started":
                state["status"] = "failed"
            common.dump(directory / "state.json", state)
            common.seal(directory, common.REPORTS)
        result = reconstruct(campaign, allow_failed=True)
        common.dump(directory / "report.json", result)
        from .report import markdown

        (directory / "report.md").write_bytes(markdown(result).encode("utf-8"))
        return result
    finally:
        # Cooperative signals remain installed through immutable session sealing
        # and both report-cache writes. A late request stops no new dispatch and
        # must not rewrite an already sealed scientific outcome.
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def run_study(config_path, output):
    return session(freeze(config_path, output))


def resume(campaign):
    return session(campaign)
