"""Freeze, fit and supervise a bounded M3 study; all outputs are local."""

import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

from experiments.m0.simglucose.recording import RunInterrupted, interruption

from .common import (
    ROOT,
    SCHEMA,
    Snapshot,
    digest,
    finite,
    provenance,
    read,
    require,
    save,
    validate_provenance,
)
from .data import (
    blocks,
    load_observations,
    origins,
    registry,
    training_windows,
    validate_registry,
    verify_bytes,
)
from .estimator import validate_model


def failure(error):
    # Record original type/location, never stringify arbitrary data-bearing exceptions.
    return {
        "type": type(error).__name__,
        "frames": [
            {"function": f.name, "line": f.lineno}
            for f in traceback.extract_tb(error.__traceback__)
        ],
    }


def seal(folder, state):
    state["files"] = {
        p.name: digest(p.read_bytes())
        for p in sorted(folder.iterdir())
        if p.is_file() and p.name not in ("state.json",) and not p.name.endswith(".tmp")
    }
    save(folder / "state.json", state)


def freeze(registry_path, output):
    output = Path(output)
    value, sha = registry(registry_path)
    if value["kind"] == "human":
        require(
            not output.resolve().is_relative_to(ROOT),
            "Human artifacts must remain outside repository",
        )
    prov = provenance()
    require(not prov["dirty"], "Commit reviewed sources before freezing")
    verify_bytes(Path(registry_path).parent, value)
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema": SCHEMA,
        "kind": value["kind"],
        "registry": value,
        "registry_sha256": sha,
        "provenance": prov,
        "input_root": str(Path(registry_path).resolve().parent),
        "splits": {p["id"]: {k: list(v) for k, v in blocks(p).items()} for p in value["people"]},
        "status": "synthetic_freeze"
        if value["kind"] == "synthetic"
        else "authorized_release_freeze",
    }
    save(output / "plan.json", plan)
    return plan


def plan_read(path):
    plan, sha = read(path)
    require(
        plan.get("schema") == SCHEMA and plan.get("kind") in ("synthetic", "human"),
        "Invalid freeze",
    )
    validate_provenance(plan.get("provenance"))
    validate_registry(plan.get("registry"), Path(plan["input_root"]) / "registry.json")
    require(plan["provenance"]["dirty"] is False, "Dirty freeze")
    require(plan["kind"] == plan["registry"]["kind"], "Data kind differs")
    require(
        plan.get("status")
        == ("synthetic_freeze" if plan["kind"] == "synthetic" else "authorized_release_freeze"),
        "Invalid freeze status",
    )
    expected = {
        p["id"]: {k: list(v) for k, v in blocks(p).items()} for p in plan["registry"]["people"]
    }
    require(plan.get("splits") == expected, "Split mismatch")
    return plan, sha


def supervise(command, folder, timeout, *, diagnostic=seal):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    state = {
        "schema": SCHEMA,
        "status": "started",
        "files": {},
        "command": command,
        "stage": "initializing",
    }
    save(folder / "state.json", state)
    (folder / "trace.jsonl").touch()
    (folder / "worker.log").touch()
    child, primary = None, None
    started = time.monotonic()
    try:
        state["provenance"] = provenance()
        state["stage"] = "running"
        save(folder / "state.json", state)
        finite(timeout, "deadline", 0)
        with interruption(timeout, arm_timer=False), (folder / "worker.log").open("wb") as log:
            child = subprocess.Popen(
                command + [str(folder)],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1"),
            )
            code = child.wait(timeout=max(0.0, timeout - (time.monotonic() - started)))
        result, _ = read(folder / "result.json")
        require(code == 0 and result.get("status") == "completed", "Worker exit/status conflict")
        state["status"] = "completed"
    except BaseException as error:
        primary = error
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            except ProcessLookupError:
                child.wait()  # The process can finish between poll and kill.
            except BaseException as cleanup_error:
                state["cleanup_error"] = failure(cleanup_error)
        state.update(
            status="interrupted"
            if isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))
            else "failed",
            error=failure(error),
        )
    finally:
        state["elapsed_seconds"] = time.monotonic() - started
        try:
            diagnostic(folder, state)
        except BaseException as error:
            if primary is None:
                raise
            # Best effort diagnostic fallback must not replace the original exception.
            state["diagnostic_error"] = failure(error)
            try:
                seal(folder, state)
            except BaseException:
                pass
    if primary is not None:
        raise primary
    return state


def fit_plan(plan_path, output, timeout=120):
    plan, sha = plan_read(plan_path)
    output = Path(output)
    if plan["kind"] == "human":
        require(
            not output.resolve().is_relative_to(ROOT),
            "Human artifacts must remain outside repository",
        )
    command = [
        str(ROOT / "experiments/m3/runtime/.venv/bin/python"),
        "-m",
        "experiments.m3.worker",
        "fit",
        str(Path(plan_path).resolve()),
    ]
    supervise(command, output, timeout)
    state, _ = read(output / "state.json")
    try:
        model, model_sha = read(output / "model.json")
        validate_model(model)
        # Seal the learned model before evaluation access is possible.
        save(
            output / "freeze.json",
            {
                "schema": SCHEMA,
                "plan_sha256": sha,
                "model_sha256": model_sha,
                "provenance": provenance(),
                "validation_sha256": digest((output / "trace.jsonl").read_bytes()),
                "fit_result_sha256": digest((output / "result.json").read_bytes()),
            },
        )
        seal(output, state)
    except BaseException as error:
        state.update(status="failed", error=failure(error))
        try:
            seal(output, state)
        except BaseException:
            pass
        raise
    return model


def run_study(plan_path, fit_path, output, timeout=120, reuse=False):
    plan, sha = plan_read(plan_path)
    fit_path, output = Path(fit_path).resolve(), Path(output).resolve()
    require(type(reuse) is bool, "Evaluation reuse flag must be boolean")
    if plan["kind"] == "human":
        require(not output.is_relative_to(ROOT), "Human artifacts must remain outside repository")
    frozen, _ = read(fit_path / "freeze.json")
    model, model_sha = read(fit_path / "model.json")
    validate_model(model)
    validate_provenance(frozen.get("provenance"))
    require(
        frozen.get("schema") == SCHEMA
        and frozen.get("plan_sha256") == sha
        and frozen.get("model_sha256") == model_sha,
        "Model freeze differs",
    )
    require(
        frozen.get("validation_sha256") == digest((fit_path / "trace.jsonl").read_bytes()),
        "Validation bytes changed",
    )
    fit_state, _ = read(fit_path / "state.json")
    require(fit_state.get("status") == "completed", "Fit did not complete")
    validate_provenance(fit_state.get("provenance"))
    require(
        isinstance(fit_state.get("files"), dict)
        and {"model.json", "trace.jsonl", "result.json", "freeze.json", "worker.log"}
        <= fit_state["files"].keys(),
        "Missing fit artifact inventory",
    )
    fit_snapshot = Snapshot(fit_path)
    for name, expected in fit_state["files"].items():
        require(digest(fit_snapshot.read(name)) == expected, "Fit artifact bytes changed")
    fit_snapshot.verify_unchanged()
    require(
        frozen.get("fit_result_sha256") == digest((fit_path / "result.json").read_bytes()),
        "Fit result changed",
    )
    # Every case and origin is persisted before reading evaluation values.
    output.mkdir(parents=True, exist_ok=False)
    save(output / "plan.json", plan)
    save(output / "model.json", model)
    save(output / "freeze.json", frozen)
    (output / "fit-result.json").write_bytes((fit_path / "result.json").read_bytes())
    (output / "validation.jsonl").write_bytes((fit_path / "trace.jsonl").read_bytes())
    cases = [
        {"id": p["id"], "origins": origins(p, "evaluation"), "status": "not_attempted"}
        for p in plan["registry"]["people"]
    ]
    study = {
        "schema": SCHEMA,
        "plan_sha256": sha,
        "kind": plan["kind"],
        "status": "started",
        "reuse": reuse,
        "cases": cases,
        "provenance": provenance(),
    }
    save(output / "study.json", study)
    marker = Path(plan_path).parent / "evaluation-access.json"
    try:
        from .analysis import reconstruct

        # Validate the complete fit, validation trace and schedule before opening evaluation.
        reconstruct(output)
        if marker.exists():
            require(reuse, "Evaluation already known; explicitly record reuse")
        else:
            with marker.open("x") as handle:
                handle.write('{"status":"evaluation_known"}\n')
        save(output / "evaluation-access.json", {"status": "evaluation_known", "reuse": reuse})
        for case in cases:
            command = [
                sys.executable,
                "-m",
                "experiments.m3.worker",
                "evaluate",
                str(output),
                case["id"],
            ]
            try:
                supervise(command, output / case["id"], timeout)
                case["status"] = "completed"
            except (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired) as error:
                # Cancellation may arrive after the supervisor has sealed completion.
                state_path = output / case["id"] / "state.json"
                case["status"] = (
                    read(state_path)[0]["status"] if state_path.exists() else "not_attempted"
                )
                study["error"] = failure(error)
                raise
            except Exception as error:
                case["status"] = "failed"
                case["error"] = failure(error)
            save(output / "study.json", study)
        study["status"] = (
            "completed"
            if all(c["status"] == "completed" for c in cases)
            else "finished_with_failures"
        )
    except BaseException as error:
        study.update(
            status="interrupted"
            if isinstance(error, (RunInterrupted, KeyboardInterrupt, subprocess.TimeoutExpired))
            else "failed",
            error=failure(error),
        )
        raise
    finally:
        save(output / "study.json", study)
    try:
        report = reconstruct(output)
        save(output / "report.json", report)
    except BaseException as error:
        study.update(status="failed", error=failure(error))
        save(output / "study.json", study)
        raise
    return report


def fit_worker(plan_path, output):
    from .estimator import fit
    from .worker import forecast_rows

    plan, plan_sha = plan_read(plan_path)
    samples, input_hashes, data = {}, {}, {}
    for person in plan["registry"]["people"]:
        rows, sha = load_observations(
            plan["input_root"], person, "train", plan["registry"]["clock"]
        )
        input_hashes[person["id"]] = sha
        data[person["id"]] = rows
        samples[person["id"]] = training_windows(rows, person)
    model = fit(samples)
    save(output / "model.json", model)
    with (output / "trace.jsonl").open("w") as trace:
        for person in plan["registry"]["people"]:
            forecast_rows(data[person["id"]], person, "validation", model, trace)
    save(
        output / "result.json",
        {
            "status": "completed",
            "plan_sha256": plan_sha,
            "consumed_train_sha256": input_hashes,
            "training_origins": {p: [w[0] for w in windows] for p, windows in samples.items()},
        },
    )
