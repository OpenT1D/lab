"""Private v2 channel resources; only the fixed gated route consumes this helper."""

import hashlib
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time

from experiments.lt1_diagnostic import native_supervisor as owner
from experiments.lt1_diagnostic.control_identity import ROOT, identity

FRAME_LIMIT = 64 * 1024
ACK_LIMIT = 1024
CHUNK_LIMIT = 1024
SHIM = ROOT / "experiments/lt1_diagnostic/native_route_exec.py"
AUTHORITY = {
    "native_host_qualified": False,
    "native_acceptance": False,
    "setup_admitted": False,
    "native_execution_authorized": False,
    "phase_verified": False,
    "endpoint_identity_verified": False,
    "effective_erasure_verified": False,
    "new_authority_granted": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 entry transport refused: " + reason)


def source_identity():
    value = identity(__file__)
    value["implementation"][SHIM.relative_to(ROOT).as_posix()] = hashlib.sha256(
        SHIM.read_bytes()
    ).hexdigest()
    return value


def _supervise(
    argv,
    log_path,
    *,
    expected_identity,
    carrier,
    invented=False,
    verify_frame,
    timeout,
    handoff_timeout,
    cancel=None,
    grace=0.2,
    before_spawn=None,
):
    """Trusted-code resource helper, never metadata dispatch or native admission.

    The sole production caller admits exact raw grants before creating resources.
    The actual startup environment has four keys; post-clear observation has three.
    Callback execution is not preemptible; unfinished daemon work is explicit.
    """
    need(os.name == "posix", "POSIX channels required")
    need(
        isinstance(carrier, str) and 0 < len(carrier.encode()) <= 65536, "bounded internal carrier"
    )
    source = source_identity()
    need(expected_identity == source, "expected transport source")
    need(
        isinstance(argv, (list, tuple))
        and 0 < len(argv) <= 16
        and all(isinstance(v, str) and 0 < len(v) <= 4096 and "\0" not in v for v in argv)
        and os.path.isabs(argv[0]),
        "trusted fixed argv",
    )
    need(callable(verify_frame), "trusted byte verifier")
    need(before_spawn is None or callable(before_spawn), "trusted last guard")
    for value, limit in ((timeout, 3600), (handoff_timeout, 30), (grace, 60)):
        need(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= limit, "budget")
    need(timeout > 0 and handoff_timeout > 0, "positive budgets")
    stopped = cancel if cancel is not None else threading.Event()
    need(callable(getattr(stopped, "is_set", None)), "cancellation observer")
    fixed = tuple(argv)
    shared = {
        "status": "not-started",
        "reason": None,
        "frame_raw": b"",
        "ack_raw": b"",
        "ack_sent_raw": b"",
        "ack_eof_sent": False,
        "frame_eof": False,
        "ack_sent": False,
        "verifier_started": False,
        "verifier_returned": False,
    }
    lock, finish, stop = threading.Lock(), threading.Event(), threading.Event()
    spawned = threading.Event()
    spawned_pid = None
    thread, started, cancelled_before = None, False, False
    close_errors = []

    def close_channel(channel):
        try:
            channel.close()
        except OSError as error:
            close_errors.append(type(error).__name__)

    frame_parent, frame_child = socket.socketpair()
    try:
        ack_parent, ack_child = socket.socketpair()
    except BaseException:
        close_channel(frame_parent)
        close_channel(frame_child)
        raise
    sockets = (frame_parent, frame_child, ack_parent, ack_child)
    shim_argv = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(ROOT / "tests/lt1_native_route_exec.py") if invented else str(SHIM),
        str(ack_child.fileno()),
        str(frame_child.fileno()),
        *fixed,
    ]

    def update(**values):
        with lock:
            shared.update(values)

    def exchange():
        until = time.monotonic() + handoff_timeout
        raw, chunks = b"", 0

        def live():
            if stop.is_set() or stopped.is_set():
                raise InterruptedError("channel stopped")
            if time.monotonic() >= until:
                raise TimeoutError("channel deadline")

        try:
            update(status="receiving")
            frame_parent.settimeout(0.05)
            while True:
                live()
                try:
                    part = frame_parent.recv(min(8192, FRAME_LIMIT + 1 - len(raw)))
                except TimeoutError:
                    continue
                live()
                if not part:
                    update(frame_eof=True)
                    break
                chunks += 1
                room = FRAME_LIMIT - len(raw)
                raw += part[:room]
                update(frame_raw=raw)
                need(len(part) <= room and chunks <= CHUNK_LIMIT, "frame bound")
            need(bool(raw), "empty frame")
            while not spawned.wait(0.01):
                live()
            need(
                json.loads(raw.split(b"\n")[1])["facts"]["pid"] == spawned_pid, "exact spawned PID"
            )
            update(verifier_started=True)
            ack = verify_frame(raw)
            update(verifier_returned=True)
            live()
            need(isinstance(ack, bytes) and 0 < len(ack) <= ACK_LIMIT, "bounded verifier ACK")
            update(ack_raw=ack)
            ack_parent.settimeout(max(0.001, until - time.monotonic()))
            offset = 0
            while offset < len(ack):
                live()
                written = ack_parent.send(ack[offset:])
                need(written > 0, "ACK short write")
                offset += written
                update(ack_sent_raw=ack[:offset])
            ack_parent.shutdown(socket.SHUT_WR)
            update(ack_eof_sent=True)
            live()
            update(status="ack-sent", ack_sent=True)
        except Exception as error:
            update(
                status="cancelled"
                if isinstance(error, InterruptedError)
                else "timeout"
                if isinstance(error, TimeoutError)
                else "failed",
                reason=type(error).__name__,
            )
        finally:
            close_channel(frame_parent)
            close_channel(ack_parent)
            finish.set()

    def controlled_spawn(actual_argv, **kwargs):
        nonlocal thread, started, cancelled_before, spawned_pid
        need(set(kwargs) == {"cwd", "env", "stdout", "stderr"}, "canonical spawn fields")
        need(
            list(actual_argv) == shim_argv
            and kwargs["cwd"] == ROOT
            and kwargs["env"] == owner.ENVIRONMENT
            and kwargs["stderr"] == subprocess.STDOUT,
            "actual spawn bindings",
        )
        log = kwargs["stdout"]
        token = owner._log_token(log, log_path, private=False)
        os.fchmod(log.fileno(), 0o600)
        if before_spawn is not None:
            before_spawn(log)
        need(owner._log_token(log, log_path, private=True) == token, "late log binding")
        need(source_identity() == source, "late transport source")
        if stopped.is_set():
            cancelled_before = True
            raise owner._NotStartedCancel(owner.CANCEL_MESSAGE)
        kwargs.update(
            env={**kwargs["env"], "OPENT1D_LT1_ROUTE_CONTROL": carrier},
            stdin=subprocess.DEVNULL,
            close_fds=True,
            pass_fds=(ack_child.fileno(), frame_child.fileno()),
        )
        thread = threading.Thread(target=exchange, daemon=True)
        thread.start()
        process = owner.canonical.spawn(actual_argv, **kwargs)
        spawned_pid = process.pid
        spawned.set()
        started = True
        # A post-Popen resource error must still hand this Popen to its owner.
        for channel in (ack_child, frame_child):
            close_channel(channel)
        # Return promptly: the shared owner starts its deadline after this call.
        return process

    try:
        if stopped.is_set():
            outer = owner._not_started(shim_argv)
        else:
            view = owner._supervisor_view(controlled_spawn)
            outer = view(
                shim_argv,
                log_path,
                timeout=timeout,
                cancel=stopped,
                grace=grace,
                environment=dict(owner.ENVIRONMENT),
            )
    finally:
        stop.set()
        for channel in sockets:
            close_channel(channel)
        if thread is not None and thread.ident is not None:
            thread.join(timeout=0.25)
    if cancelled_before:
        need(
            not started
            and outer["exit_code"] is None
            and outer["owned_processes"] == []
            and outer["remaining_owned_processes"] == []
            and outer["error"] == f"{owner._NotStartedCancel.__name__}: {owner.CANCEL_MESSAGE}"
            and not outer.get("cleanup_error")
            and not outer.get("signal_error"),
            "before-spawn cancellation receipt",
        )
        outer = {**outer, "status": "interrupted", "error": "Cancelled"}
    with lock:
        exchange_result = dict(shared)
    exchange_result["thread_finished"] = finish.is_set()
    if started and not finish.is_set():
        exchange_result["status"] = "unfinished"
    stable = source_identity() == source
    clean = (
        outer["status"] == "completed"
        and type(outer["exit_code"]) is int
        and outer["exit_code"] == 0
        and outer["error"] is None
        and outer["remaining_owned_processes"] == []
        and outer["received_signals"] == []
        and not outer.get("cleanup_error")
        and not outer.get("signal_error")
    )
    return {
        "schema": "opent1d.lt1-native-route-transport/2",
        "outer": outer,
        "exchange": exchange_result,
        "source_stable": stable,
        "resource_close_errors": list(close_errors),
        "local_exchange_and_process_complete": stable
        and clean
        and not close_errors
        and finish.is_set()
        and exchange_result["status"] == "ack-sent",
        "endpoint_close_verified": False,
        "source_identity": source,
        **AUTHORITY,
    }
