"""Frozen study orchestration with bounded numerical groups and complete failures."""

import shutil
import signal
import sys
import time
from pathlib import Path

from experiments.m4.comparison.run import separate
from experiments.platform_process import handled_signals

from .common import (
    ROOT,
    VERSION,
    digest,
    dump,
    intake,
    protocol,
    provenance,
    read,
    reference_snapshot,
    require,
    seal,
    sha256,
    source_snapshots,
    verify_reference,
    verify_reference_snapshot,
)
from .process import Control, supervise


def freeze(config_path, output, reference_path=None):
    config, bundles = intake(config_path)
    p = protocol()
    output = Path(output).absolute()
    require(not output.is_symlink(), "Output cannot be a symlink")
    output = output.resolve()
    separate(output, Path(config_path).resolve())
    for bundle in bundles.values():
        for key in ("model_path", "declaration_path"):
            separate(output, bundle[key])
    reference_hash = None
    if reference_path is not None:
        reference_path = Path(reference_path).absolute()
        require(not reference_path.is_symlink(), "Historical reference cannot be a symlink")
        reference_path = reference_path.resolve()
        separate(output, reference_path)
        verify_reference(reference_path)
        reference_hash = sha256(reference_path / "manifest.json")
    snapshots = source_snapshots()
    identity = provenance(snapshots)
    output.mkdir(parents=True, exist_ok=False)
    for name in ("sources", "frozen", "children", "logs"):
        (output / name).mkdir()
    raw = next(iter(bundles.values()))["config_raw"]
    (output / "config.json").write_bytes(raw)
    frozen = {}
    for item in config["sources"]:
        name, bundle = item["id"], bundles[item["id"]]
        folder = output / "frozen" / name
        folder.mkdir()
        (folder / "model.py").write_bytes(bundle["model_raw"])
        (folder / "model.json").write_bytes(bundle["declaration_raw"])
        frozen[name] = {
            "declaration": bundle["declared"],
            "source_sha256": digest(bundle["model_raw"]),
            "declaration_sha256": digest(bundle["declaration_raw"]),
        }
    for name, raw in snapshots.items():
        path = output / "sources" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    plan = {
        "schema": VERSION,
        "protocol": p,
        "configuration": config,
        "config_sha256": sha256(output / "config.json"),
        "sources": frozen,
        "provenance": identity,
        "historical_manifest_sha256": reference_hash,
        "archive_original_path": str(output),
        "coordinator_executable": sys.executable,
    }
    dump(output / "plan.json", plan)
    return output, plan, reference_path


def verify_frozen(output, plan):
    require(
        read(output / "plan.json") == plan
        and sha256(output / "config.json") == plan["config_sha256"],
        "Frozen plan/config changed",
    )
    for name, expected in plan["provenance"]["sources"].items():
        require(
            sha256(output / "sources" / name) == expected and sha256(ROOT / name) == expected,
            f"Frozen implementation/condition changed: {name}",
        )
    for name, item in plan["sources"].items():
        require(
            sha256(output / "frozen" / name / "model.py") == item["source_sha256"]
            and sha256(output / "frozen" / name / "model.json") == item["declaration_sha256"],
            "Frozen source/declaration changed",
        )


def worker_args(output, kind, label, source=None):
    project = (
        "experiments/m4/beta_cell/runtime" if kind == "observer" else "experiments/m0/simglucose"
    )
    args = [
        str(ROOT / project / ".venv/bin/python"),
        "-B",
        "-E",
        "-s",
        "-m",
        "experiments.m4.initial_load.worker",
        str(output),
        "--kind",
        kind,
        "--label",
        label,
    ]
    if source is not None:
        args += ["--source", source]
    return args


def run_study(config_path, output, reference_path=None):
    output, plan, reference_path = freeze(config_path, output, reference_path)
    state = {
        "schema": VERSION,
        "status": "started",
        "reference": {"status": "not_attempted", "stage": None, "attempts": [], "error_type": None},
        "sources": {
            item["id"]: {
                "status": "not_attempted",
                "stage": None,
                "attempts": [],
                "error_type": None,
            }
            for item in plan["configuration"]["sources"]
        },
        "interruption_signal": None,
    }
    dump(output / "state.json", state)
    control = Control()
    previous = {signum: signal.getsignal(signum) for signum in handled_signals()}
    for signum in previous:
        signal.signal(signum, control.stop)

    def invoke(owner, args, logfile, stage, budget, source_deadline=None):
        verify_frozen(output, plan)
        if control.signal is not None:
            return False
        if source_deadline is not None:
            verify_reference_snapshot(output)
            budget = min(budget, source_deadline - time.monotonic())
            if budget <= 0:
                owner.update(status="failed", stage=stage, error_type="SourceDeadline")
                dump(output / "state.json", state)
                return False
        owner.update(status="started", stage=stage)
        attempt = {
            "stage": stage,
            "status": "started",
            "argv": args,
            "timeout_seconds": budget,
            "exit_code": None,
            "error_type": None,
        }
        owner["attempts"].append(attempt)
        dump(output / "state.json", state)
        try:
            code, error = supervise(args, output / "logs" / logfile, budget, control)
        except Exception as exc:
            code, error = None, type(exc).__name__
            attempt["error_message"] = str(exc).replace(str(output), "<archive>")[:500]
        attempt.update(
            status="completed"
            if error is None
            else "interrupted"
            if control.signal is not None
            else "failed",
            exit_code=code,
            error_type=error,
        )
        if error is not None:
            owner.update(status=attempt["status"], error_type=error)
        dump(output / "state.json", state)
        verify_frozen(output, plan)
        return error is None

    try:
        reference = state["reference"]
        reference.update(status="started", stage="historical")
        dump(output / "state.json", state)
        if reference_path is None:
            okay = invoke(
                reference,
                [
                    sys.executable,
                    "-B",
                    "-S",
                    "-m",
                    "experiments.m4.feedback.run",
                    "--output",
                    str(output / "historical"),
                ],
                "historical.log",
                "historical",
                plan["configuration"]["timeout_seconds"],
            )
        else:
            verify_frozen(output, plan)
            verify_reference(reference_path)
            if control.signal is None:
                shutil.copytree(reference_path, output / "historical")
                require(
                    sha256(output / "historical/manifest.json")
                    == plan["historical_manifest_sha256"],
                    "Historical reference changed during copy",
                )
                (output / "logs/historical.log").write_text(
                    "Reused verified unchanged complete BC-008 archive; "
                    "new scenario references generated separately.\n"
                )
                okay = True
            else:
                okay = False
        if okay:
            verify_reference(output / "historical")
            dump(
                output / "reference-binding.json",
                {
                    "schema": "m4-initial-load-reference-binding/1",
                    "manifest_sha256": sha256(output / "historical/manifest.json"),
                    "config_sha256": plan["config_sha256"],
                },
            )
            for label in ("primary", "repeat"):
                if not invoke(
                    reference,
                    worker_args(output, "reference", label),
                    f"reference-{label}.log",
                    f"reference_{label}",
                    plan["configuration"]["timeout_seconds"],
                ):
                    okay = False
                    break
        if okay:
            from .analysis import assess_numeric

            reference["stage"] = "verification"
            assessment, _ = assess_numeric(output, plan)
            reference["status"] = "completed" if assessment["passed"] else "failed"
            reference["error_type"] = None if assessment["passed"] else "NumericalGateFailure"
            if assessment["passed"]:
                dump(
                    output / "reference-manifest.json",
                    {
                        "schema": "m4-initial-load-reference-seal/1",
                        "files": reference_snapshot(output),
                    },
                )
            dump(output / "state.json", state)
        elif reference["status"] == "started":
            reference.update(
                status="interrupted" if control.signal is not None else "failed",
                error_type="GlobalInterruption"
                if control.signal is not None
                else "ReferenceFailure",
            )
        if reference["status"] == "completed":
            for name, owner in state["sources"].items():
                if control.signal is not None:
                    break
                started = time.monotonic()
                deadline = started + plan["configuration"]["source_timeout_seconds"]
                owner.update(status="started", stage="source_primary")
                try:
                    verify_reference(output / "historical")
                    for kind, label in (
                        ("source", "primary"),
                        ("source", "repeat"),
                        ("observer", "primary"),
                        ("observer", "repeat"),
                    ):
                        remaining = plan["configuration"]["source_timeout_seconds"] - (
                            time.monotonic() - started
                        )
                        if remaining <= 0:
                            owner.update(status="failed", error_type="SourceDeadline")
                            break
                        if kind == "observer" and label == "primary":
                            numeric, _ = assess_numeric(output, plan, name)
                            if not numeric["passed"]:
                                owner.update(
                                    status="failed",
                                    stage="numerical_verification",
                                    error_type="NumericalGateFailure",
                                )
                                break
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            owner.update(status="failed", error_type="SourceDeadline")
                            break
                        budget = min(plan["configuration"]["timeout_seconds"], remaining)
                        if not invoke(
                            owner,
                            worker_args(output, kind, label, name),
                            f"{name}-{kind}-{label}.log",
                            f"{kind}_{label}",
                            budget,
                            deadline,
                        ):
                            break
                    else:
                        from .analysis import assess_observer

                        owner["stage"] = "verification"
                        numeric, records = assess_numeric(output, plan, name)
                        observation, _ = assess_observer(output, plan, name, records)
                        if (
                            time.monotonic() - started
                            > plan["configuration"]["source_timeout_seconds"]
                        ):
                            owner.update(status="failed", error_type="SourceDeadline")
                        elif numeric["passed"] and observation["passed"]:
                            owner.update(status="completed", error_type=None)
                        else:
                            owner.update(status="failed", error_type="NumericalGateFailure")
                except Exception as exc:
                    owner.update(
                        status="failed",
                        error_type=type(exc).__name__,
                        error_message=str(exc).replace(str(output), "<archive>")[:500],
                    )
                owner["duration_seconds"] = time.monotonic() - started
                dump(output / "state.json", state)
        state["status"] = (
            "interrupted"
            if control.signal is not None
            else "completed"
            if state["reference"]["status"] == "completed"
            and all(item["status"] == "completed" for item in state["sources"].values())
            else "failed"
        )
    except BaseException as exc:
        state.update(
            status="interrupted" if control.signal is not None else "failed",
            error_type=type(exc).__name__,
            error_message=str(exc).replace(str(output), "<archive>")[:500],
        )
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if control.signal is not None:
            state.update(status="interrupted", interruption_signal=control.signal)
        if state["status"] == "started":
            state["status"] = "failed"
        for owner in (state["reference"], *state["sources"].values()):
            if owner["status"] == "started":
                owner.update(
                    status="interrupted" if control.signal is not None else "failed",
                    error_type="GlobalInterruption"
                    if control.signal is not None
                    else "UncommittedStage",
                )
        dump(output / "state.json", state)
        seal(output)
    from .report import reconstruct, write_reports

    report = reconstruct(output, allow_failed=True)
    write_reports(output, report)
    reconstruct(output, allow_failed=True)
    return report


execute = run_study
