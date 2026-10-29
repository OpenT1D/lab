"""Owned isolated workers and fixed trusted readers around a complete ledger."""

import math
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from experiments.gui.ownership import Ownership
from experiments.observation_analysis.plan import runtime_identity
from experiments.platform_process import handled_signals, spawn
from experiments.workflows.checks import check
from experiments.workflows.dispatch import child_environment, command_for
from experiments.workflows.registry import TASKS

from .routes import ROOT, forensic_result, native_result, reader_identity, validate_freeze
from .store import require, safe_path, snapshot, write


def begin(store, plan_id, *, retry_of=None, mode="execute", application=None):
    store.require_lease(write_access=True)
    require(mode in {"execute", "import"}, "Unsupported attempt mode")
    require(plan_id in store.plans, "Unknown frozen plan")
    require(
        not (set(store.attempts) - set(store.finishes)),
        "Recover unfinished execution before starting another attempt",
    )
    prior = [(key, row) for key, row in store.attempts.items() if row["plan"] == plan_id]
    require(
        retry_of == (prior[-1][0] if prior else None)
        and (not prior or prior[-1][0] in store.finishes),
        "Explicit retry must name the previous terminal attempt",
    )
    host = runtime_identity()
    if application is not None:
        host["application"] = application
    attempt = store.append(
        "start",
        {
            "plan": plan_id,
            "ordinal": len(prior) + 1,
            "retry_of": retry_of,
            "mode": mode,
            "host": host,
        },
    )
    work = store.path / "work" / attempt
    work.mkdir()
    store.inspect()
    return attempt, work


def finish(store, attempt, work, receipt, *, forensic=False):
    store.require_lease(write_access=True)
    require(
        attempt in store.attempts and attempt not in store.finishes,
        "No unfinished attempt to seal",
    )
    work = safe_path(work)
    require(work == store.path / "work" / attempt, "Attempt workspace differs from owned work")
    descriptor, plan = store.plans[store.attempts[attempt]["plan"]]
    require(
        receipt["remaining_owned_processes"] == [],
        "Owned processes remain; retain unfinished workspace",
    )
    result = forensic_result(descriptor, receipt["status"])
    if not forensic and (work / "native/report.json").exists():
        try:
            result = native_result(work / "native", descriptor, plan)
        except (OSError, ValueError, KeyError, TypeError) as error:
            receipt["native_admission_error"] = type(error).__name__ + ": " + str(error)[:500]
            receipt["status"] = "failed"
            result = forensic_result(descriptor, "failed")
    if result["payload"] == "forensic" and receipt["status"] == "completed":
        receipt["status"] = "failed"
        receipt["error"] = "Worker did not produce an admissible native report"
        result = forensic_result(descriptor, "failed")
    write(work / "receipt.json", receipt)

    def populate(folder):
        snapshot(work, folder / "evidence")

    store.append("finish", {"attempt": attempt, "receipt": receipt, "result": result}, populate)
    # Only the duplicate live workspace is disposable, after committed snapshot.
    shutil.rmtree(work)
    store.inspect()
    return attempt


def supervise(argv, log_path, *, timeout, cancel=None, grace=30):
    """Forward cancellation to the coordinator; retain observed nested ownership."""
    require(
        type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
        "Finite positive deadline required",
    )
    require(
        type(grace) in (int, float) and math.isfinite(grace) and grace >= 0,
        "Finite cleanup grace required",
    )
    cancel = cancel or threading.Event()
    previous, received = {}, []

    def stop(signum, _frame):
        received.append(signum)
        cancel.set()

    process = ownership = stopped = None
    receipt = {
        "argv": argv,
        "status": "failed",
        "exit_code": None,
        "error": None,
        "cleanup_forced": False,
        "owned_processes": [],
        "remaining_owned_processes": None,
    }
    try:
        if threading.current_thread() is threading.main_thread():
            for signum in handled_signals():
                previous[signum] = signal.signal(signum, stop)
        with Path(log_path).open("xb") as log:
            process = spawn(
                argv, cwd=ROOT, env=child_environment(), stdout=log, stderr=subprocess.STDOUT
            )
            ownership = Ownership(process)
            deadline, stopped = time.monotonic() + timeout, None
            while process.poll() is None:
                ownership.observe()
                now = time.monotonic()
                if stopped is None and (cancel.is_set() or now >= deadline):
                    receipt["error"] = "Cancelled" if cancel.is_set() else "WorkerDeadline"
                    receipt["status"] = "interrupted" if cancel.is_set() else "failed"
                    process.terminate()
                    stopped = now
                if stopped is not None and now - stopped >= grace:
                    ownership.signal(signal.SIGKILL)
                    receipt["cleanup_forced"] = True
                time.sleep(0.02)
            receipt["exit_code"] = process.wait()
            if stopped is None:
                receipt["status"] = "completed" if process.returncode == 0 else "failed"
                if ownership.observe():
                    receipt.update(status="failed", error="Entry exited with live descendants")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt.update(status="failed", error=type(error).__name__ + ": " + str(error)[:500])
    finally:
        if process is not None:
            try:
                if ownership is not None:
                    remaining_grace = (
                        grace if stopped is None else max(0, stopped + grace - time.monotonic())
                    )
                    try:
                        forced, remaining = ownership.cleanup(remaining_grace)
                        receipt["cleanup_forced"] |= forced
                        receipt["remaining_owned_processes"] = remaining
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        receipt.update(status="failed", cleanup_error=str(error)[:500])
                        # cleanup itself begins with observe(), which may fail.
                        # Previously observed start identities still authorize
                        # a bounded force attempt, independently of a new scan.
                        try:
                            ownership.signal(signal.SIGKILL)
                        except (OSError, ValueError) as signal_error:
                            receipt["signal_error"] = str(signal_error)[:500]
                        receipt["cleanup_forced"] = True
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=2)
                        try:
                            _, remaining = ownership.cleanup(0)
                            receipt["remaining_owned_processes"] = remaining
                        except (OSError, ValueError, subprocess.SubprocessError):
                            # Unknown is never rewritten as an observed empty
                            # tree; finish refuses this and keeps the start/work.
                            receipt["remaining_owned_processes"] = None
                    finally:
                        receipt["owned_processes"] = ownership.receipt()
                elif process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                receipt["exit_code"] = process.wait(timeout=2)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                receipt.update(status="failed", cleanup_error=str(error)[:500])
                receipt["remaining_owned_processes"] = None
            finally:
                for signum, handler in previous.items():
                    signal.signal(signum, handler)
        else:
            receipt["remaining_owned_processes"] = []
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    receipt["received_signals"] = received
    if receipt["remaining_owned_processes"] != []:
        receipt.update(status="failed", error="Owned process cleanup remains unresolved")
    return receipt


def execute(store, plan_id, *, retry_of=None, timeout=3600, cancel=None, backend=None):
    store.require_lease(write_access=True)
    require(
        type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
        "Finite positive deadline required",
    )
    descriptor, plan = store.plans[plan_id]
    validate_freeze(plan, descriptor, current=True)
    attempt, work = begin(
        store,
        plan_id,
        retry_of=retry_of,
        application=None if backend is None else backend.application,
    )
    args = SimpleNamespace(
        config=plan / "input"
        if descriptor["task"] == "mmtt-sensitivity"
        else plan / "input/config.json",
        output=work / "native",
        reference=None,
    )
    argv = receipt = None
    try:
        admission = (
            check(TASKS[descriptor["task"]], args)
            if backend is None
            else backend.check(TASKS[descriptor["task"]], args)
        )
        write(work / "admission.json", admission)
        if not admission["runtimes_ready"]:
            receipt = {
                "status": "failed",
                "error": "Required admitted runtimes unavailable; no setup performed",
                "owned_processes": [],
                "remaining_owned_processes": [],
            }
        else:
            argv = (
                command_for(TASKS[descriptor["task"]], args)
                if backend is None
                else backend.command_for(TASKS[descriptor["task"]], args)
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        receipt = {
            "status": "failed",
            "error": type(error).__name__ + ": " + str(error)[:500],
            "owned_processes": [],
            "remaining_owned_processes": [],
        }
    if receipt is None:
        receipt = supervise(argv, work / "worker.log", timeout=timeout, cancel=cancel)
    write(work / "supervision.json", receipt)
    return finish(store, attempt, work, receipt)


def recover(store, attempt, *, execution_stopped=False):
    """Explicit offline recovery; never adopt or signal a journal's PID."""
    store.require_lease(write_access=True)
    require(execution_stopped is True, "Explicit confirmation that execution stopped is required")
    require(attempt in store.attempts and attempt not in store.finishes, "No unfinished attempt")
    work = store.path / "work" / attempt
    work.mkdir(exist_ok=True)
    receipt = {
        "status": "interrupted",
        "error": "Previous execution stopped; process outcome unobserved",
        "owned_processes": [],
        "remaining_owned_processes": [],
        "recovered": True,
    }
    return finish(store, attempt, work, receipt, forensic=True)


def reconstruct(store, attempt, output, *, allow_failed=False, backend=None):
    store.require_lease()
    require(attempt in store.finishes, "Unfinished attempt; native reconstruction unavailable")
    finish_record, evidence = store.finishes[attempt]
    result = finish_record["result"]
    require(
        allow_failed or result["completeness"] == "complete",
        "Explicit allow_failed required for incomplete evidence",
    )
    require(
        result["payload"] == "native",
        "Native reconstruction unavailable; forensic files are retained",
    )
    descriptor, plan = store.plans[store.attempts[attempt]["plan"]]
    validate_freeze(plan, descriptor, current=False)
    require(
        descriptor["reader"] == reader_identity(descriptor["task"]),
        "Unsupported trusted reader version",
    )
    output = safe_path(output, fresh=True)
    require(
        not output.exists() and not output.is_relative_to(store.path),
        "Fresh output outside the project required",
    )
    args = SimpleNamespace(archive=evidence / "native", output=output, allow_failed=allow_failed)
    argv = (
        command_for(TASKS[descriptor["task"]], args, operation="reconstruct")
        if backend is None
        else backend.command_for(TASKS[descriptor["task"]], args, operation="reconstruct")
    )
    # Reader cwd/env/module are trusted and fixed by registry, never an archive.
    with tempfile_log() as logfile:
        receipt = supervise(argv, logfile, timeout=600)
    require(
        receipt["status"] == "completed"
        and receipt.get("exit_code") == 0
        and receipt.get("remaining_owned_processes") == [],
        "Trusted native reader refused reconstruction: " + str(receipt["error"]),
    )
    from experiments.catalogue.storage import digest

    require(
        {name: digest((output / name).read_bytes()) for name in result["report_sha256"]}
        == result["report_sha256"],
        "Authoritative reconstructed report bytes differ",
    )
    if store.writable:
        store.append(
            "reconstruct",
            {
                "attempt": attempt,
                "status": "verified",
                "reader": descriptor["reader"],
                "report_sha256": result["report_sha256"],
            },
        )
        store.inspect()
    return {
        "reconstruction": "verified",
        "completeness": result["completeness"],
        "report_sha256": result["report_sha256"],
    }


def tempfile_log():
    import contextlib
    import tempfile

    @contextlib.contextmanager
    def owned():
        with tempfile.TemporaryDirectory(prefix="opent1d-reader-") as directory:
            yield Path(directory) / "reader.log"

    return owned()
