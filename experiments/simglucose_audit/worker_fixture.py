"""Fixed invented worker IPC; no native bootstrap, sandbox or host admission.

Only this module's fixed child is launched. Denials are invented events: no
network, font discovery, selected dependency or asset operation is attempted.
"""

import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from experiments import platform_process

from .contract import (
    AUTHORITY,
    decode,
    default_config,
    digest,
    encode,
    fields,
    require,
    source_identity,
    validate_config,
)
from .reference import expected_fixture

REQUEST_SCHEMA = "opent1d.simglucose-audit1-worker-fixture/1"
REPORT_SCHEMA = "opent1d.simglucose-audit1-worker-fixture-result/1"
MAX_BYTES = 1024 * 1024
BUDGET_SECONDS = 5.0
CLEANUP_SECONDS = 1.0
MODES = (
    "complete",
    "cancel",
    "deadline",
    "stall-before-read",
    "finish-block",
    "deny-network",
    "deny-subprocess",
    "deny-system-font",
)
HOST_REQUIREMENTS = (
    "interpreter-runtime-build-identity",
    "complete-import-effects-closure",
    "three-resource-hashes-and-use-rights",
    "bundled-data-and-private-cache",
    "network-and-subprocess-denies",
    "system-font-and-config-denies",
    "owned-worker-lifecycle",
    "native-direct-wrapped-parity",
)
ROOT = Path(__file__).resolve().parents[2]


def default_request():
    return {
        "schema": REQUEST_SCHEMA,
        "kind": "invented",
        "mode": "complete",
        "config": default_config(),
    }


def _request(raw):
    value = decode(raw)
    fields(value, "schema kind mode config", "worker-request-fields")
    require(
        value["schema"] == REQUEST_SCHEMA and value["kind"] == "invented",
        "invented-worker-only",
    )
    require(type(value["mode"]) is str and value["mode"] in MODES, "fixed-worker-mode")
    value["config"] = validate_config(value["config"])
    if value["mode"] in ("cancel", "deadline"):
        require(value["config"]["fault"] == "none", "worker-prefix-fault-is-fixed")
    return value


def _identity():
    # Also binds this file before integration into the shared package inventory.
    return source_identity() | {"worker_fixture.py": digest(Path(__file__).read_bytes())}


def _owner_identity():
    return {name: digest((ROOT / name).read_bytes()) for name in platform_process.SOURCE_FILES}


def default_host_preconditions():
    return {
        "schema": "opent1d.simglucose-audit1-invented-host-preconditions/1",
        "kind": "invented",
        "requirements": dict.fromkeys(HOST_REQUIREMENTS, "unqualified"),
    }


def inspect_host_preconditions(raw):
    """Validate fictional future requirements; never probe or qualify a host."""
    value = decode(raw)
    fields(value, "schema kind requirements", "invented-host-fields")
    require(
        value["schema"] == default_host_preconditions()["schema"] and value["kind"] == "invented",
        "invented-host-only",
    )
    requirements = value["requirements"]
    require(
        type(requirements) is dict and set(requirements) == set(HOST_REQUIREMENTS),
        "host-roster",
    )
    require(
        all(
            type(v) is str and v in ("unqualified", "invented-pass", "invented-fail")
            for v in requirements.values()
        ),
        "invented-host-states",
    )
    return {
        "kind": "invented",
        "status": "blocked",
        "requirements": requirements,
        "host_or_process_qualified": False,
        "actual_host_probe_performed": False,
        "authority": dict(AUTHORITY),
    }


def _fixture_config(request):
    config = dict(request["config"])
    if request["mode"] in ("cancel", "deadline"):
        config["fault"] = "cancel-after-two" if request["mode"] == "cancel" else "after-two"
    return config


def _expected_result(request, identity):
    mode = request["mode"]
    if mode.startswith("deny-"):
        return {
            "phase": "result",
            "fixture": None,
            "error": "invented-permission-denied:" + mode[5:],
        }
    config = _fixture_config(request)
    fixture = expected_fixture(config, identity, digest(encode(config)))
    return {"phase": "result", "fixture": fixture, "error": None}


def _observe(sink, event, data):
    if sink is not None:
        from .worker_journal import _JournalSink

        require(type(sink) is _JournalSink, "fixed-journal-sink-only")
        try:
            _JournalSink._record(sink, event, data)
        except (OSError, ValueError):
            # Recording failure must never skip the owned child's finally stop.
            sink.error = sink.error or "journal-write-failed"


def _frame_reader(stream, events, sink=None):
    """Bounded output from the fixed trusted child; not a hostile-worker parser."""
    try:
        for _ in range(4):
            line = stream.readline(MAX_BYTES + 1)
            if not line:
                _observe(sink, "stdout-eof", {})
                events.put_nowait(("eof", None))
                return
            _observe(sink, "raw-frame", {"raw": line})
            if len(line) > MAX_BYTES or not line.endswith(b"\n"):
                events.put_nowait(("error", "bounded-worker-frame"))
                return
            events.put_nowait(("frame", decode(line[:-1])))
        events.put_nowait(("error", "too-many-worker-frames"))
    except (ValueError, OSError):
        events.put_nowait(("error", "invalid-worker-frame"))


def _input_writer(stream, raw, events, result, sink=None):
    """Keep pipe backpressure inside the supervisor's single whole deadline."""
    error = None
    try:
        if stream.write(raw) != len(raw):
            error = "worker-input-failed"
    except (OSError, ValueError):
        error = "worker-input-failed"
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            error = "worker-input-failed"
        result.append(error)
        _observe(sink, "input-closed", {"attempted_bytes": len(raw), "error": error})
        events.put_nowait(("input", error))


def _stop(process, _sink=None):
    """Signal only a live Popen; never signal a reaped leader's old group ID."""
    try:
        before = process.poll()
        _observe(_sink, "stop-poll", {"returncode": before})
        if before is None:
            _observe(_sink, "force-request", {})
            platform_process.force_tree(process)
            process.wait(timeout=CLEANUP_SECONDS)
            _observe(_sink, "wait-return", {"returncode": process.returncode})
        # A fixed child has no descendants. An unexpected remaining group is
        # incomplete cleanup, never fresh authority to signal an exited PID.
        remains = platform_process.tree_exists(process)
        _observe(_sink, "group-observation", {"remaining": remains})
        if remains:
            return "owned-tree-remains"
        platform_process.close_tree(process)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return "owned-stop-failed"
    return None


def _report(raw, identity, owner, status, primary, cleanup, frames, fixture, stopped):
    return {
        "schema": REPORT_SCHEMA,
        "kind": "invented",
        "request_sha256": digest(raw),
        "source_identity": identity,
        "process_owner_source_identity": owner,
        "status": status,
        "primary_error": primary,
        "cleanup_error": cleanup,
        "frames_received": frames,
        "fixture_report": fixture,
        "owned_stop_observed": stopped,
        "host_or_process_qualified": False,
        "native_acceptance": False,
        "authority": dict(AUTHORITY),
    }


def run_worker_fixture(raw=None):
    """Run one fresh fixed stdlib child; all native entries remain closed."""
    return _run_worker_fixture(raw)


def _run_worker_fixture(raw=None, _sink=None):
    """Private concrete journal integration; no public callback or factory."""
    raw = encode(default_request()) if raw is None else raw
    request = _request(raw)  # Strict data intake precedes source reads and spawn.
    if _sink is not None:
        from .worker_journal import _JournalSink

        require(type(_sink) is _JournalSink, "fixed-journal-sink-only")
    identity, owner = _identity(), _owner_identity()
    expected = _expected_result(request, identity)
    ready = {
        "phase": "ready",
        "request_sha256": digest(raw),
        "source_identity": identity,
    }
    deadline = time.monotonic() + BUDGET_SECONDS
    events = queue.Queue(maxsize=8)
    try:
        process = platform_process.spawn(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-c",
                "import sys; sys.path.insert(0, " + repr(str(ROOT)) + "); "
                "from experiments.simglucose_audit.worker_fixture import _child; "
                + (
                    "_child(stall_before_read=True)"
                    if request["mode"] == "stall-before-read"
                    else "_child()"
                ),
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        _observe(_sink, "launch-refused", {})
        return _report(
            raw,
            identity,
            owner,
            "failed",
            "worker-launch-refused",
            None,
            [],
            None,
            False,
        )
    reader = threading.Thread(
        target=_frame_reader,
        args=(process.stdout, events, _sink),
        name="simglucose-fixture-output",
        daemon=True,
    )
    input_result = []
    writer = threading.Thread(
        target=_input_writer,
        args=(process.stdin, raw, events, input_result, _sink),
        name="simglucose-fixture-input",
        daemon=True,
    )
    started = []
    frames, fixture, primary, cleanup = [], None, None, None
    status, stopped = "failed", False
    try:
        if _sink is not None:
            import os

            _observe(_sink, "launch", {"parent_pid": os.getpid(), "child_pid": process.pid})
        for thread in (reader, writer):
            thread.start()
            started.append(thread)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                primary = (
                    "fixture-finish-deadline"
                    if request["mode"] == "finish-block"
                    and frames == ["ready", "result", "finished"]
                    else "fixture-deadline"
                    if request["mode"] == "deadline" and fixture
                    else "worker-deadline"
                )
                status = "incomplete"
                break
            try:
                event, value = events.get(timeout=remaining)
            except queue.Empty:
                primary = (
                    "fixture-finish-deadline"
                    if request["mode"] == "finish-block"
                    and frames == ["ready", "result", "finished"]
                    else "fixture-deadline"
                    if request["mode"] == "deadline" and fixture
                    else "worker-deadline"
                )
                status = "incomplete"
                break
            if event == "input":
                if value:
                    primary = value
                    break
                continue
            if event == "error":
                primary = value
                break
            if event == "eof":
                if frames != ["ready", "result", "finished"]:
                    primary = "incomplete-worker-protocol"
                else:
                    process.wait(timeout=max(0.001, deadline - time.monotonic()))
                    _observe(_sink, "wait-return", {"returncode": process.returncode})
                    if process.returncode != 0:
                        primary = "worker-nonzero-exit"
                    else:
                        primary = expected["error"]
                        status = fixture["status"] if fixture else "failed"
                break
            phase = ("ready", "result", "finished")[len(frames)] if len(frames) < 3 else None
            wanted = (
                ready
                if phase == "ready"
                else expected
                if phase == "result"
                else {"phase": "finished"}
            )
            if phase is None or encode(value) != encode(wanted):
                primary = "worker-protocol-mismatch"
                break
            frames.append(phase)
            if phase == "result":
                fixture = value["fixture"]
                if request["mode"] == "cancel":
                    primary, status = "fixture-cancelled", "interrupted"
                    break
                if request["mode"] == "deadline":
                    deadline = min(deadline, time.monotonic() + 0.05)
            if phase == "finished" and request["mode"] == "finish-block":
                deadline = min(deadline, time.monotonic() + 0.05)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        primary = "worker-transport-failed"
    finally:
        cleanup = _stop(process) if _sink is None else _stop(process, _sink)
        # Both joins share one separately bounded cleanup window, after stop.
        join_deadline = time.monotonic() + CLEANUP_SECONDS
        for thread in started:
            thread.join(timeout=max(0, join_deadline - time.monotonic()))
        if reader in started and reader.is_alive():
            cleanup = cleanup or "worker-reader-not-joined"
        else:
            process.stdout.close()
        if writer in started and writer.is_alive():
            cleanup = cleanup or "worker-writer-not-joined"
        elif not process.stdin.closed:
            process.stdin.close()
        if input_result and input_result != [None] and primary is None:
            primary, status = "worker-input-failed", "failed"
        stopped = cleanup is None
        if _sink is not None:
            _observe(
                _sink,
                "io-joined",
                {
                    "reader_joined": not reader.is_alive(),
                    "writer_joined": not writer.is_alive(),
                    "returncode": process.poll(),
                    "cleanup_error": cleanup,
                },
            )
    if _identity() != identity or _owner_identity() != owner:
        primary = primary or "worker-source-changed"
        status = "failed"
    if cleanup:
        status = "failed"
    return _report(raw, identity, owner, status, primary, cleanup, frames, fixture, stopped)


def inspect_worker_fixture(
    report_raw, expected_report_sha256, request_raw, expected_request_sha256
):
    """Cold source-bound readback; no consumer, engine or child invocation."""
    require(
        digest(report_raw) == expected_report_sha256
        and digest(request_raw) == expected_request_sha256,
        "external-worker-byte-pins",
    )
    request = _request(request_raw)
    report = decode(report_raw)
    identity, owner = _identity(), _owner_identity()
    fields(
        report,
        "schema kind request_sha256 source_identity process_owner_source_identity status "
        "primary_error cleanup_error frames_received fixture_report owned_stop_observed "
        "host_or_process_qualified native_acceptance authority",
        "worker-report-fields",
    )
    require(
        report["schema"] == REPORT_SCHEMA and report["kind"] == "invented",
        "invented-worker-only",
    )
    require(
        report["request_sha256"] == digest(request_raw)
        and report["source_identity"] == identity
        and report["process_owner_source_identity"] == owner,
        "worker-source-input-binding",
    )
    require(
        encode(report["authority"]) == encode(AUTHORITY)
        and report["host_or_process_qualified"] is False
        and report["native_acceptance"] is False,
        "no-worker-authority",
    )
    frames = report["frames_received"]
    require(
        type(frames) is list
        and frames in ([], ["ready"], ["ready", "result"], ["ready", "result", "finished"]),
        "worker-frame-prefix",
    )
    expected = _expected_result(request, identity)
    require(
        encode(report["fixture_report"])
        == encode(expected["fixture"] if len(frames) >= 2 else None),
        "worker-fixture-oracle",
    )
    mode, primary, status = request["mode"], report["primary_error"], report["status"]
    cleanup = report["cleanup_error"]
    require(
        cleanup
        in (
            None,
            "owned-tree-remains",
            "owned-stop-failed",
            "worker-reader-not-joined",
            "worker-writer-not-joined",
        ),
        "worker-cleanup-error",
    )
    require(type(report["owned_stop_observed"]) is bool, "worker-stop-accounting")
    if primary == "worker-launch-refused":
        require(
            frames == []
            and cleanup is None
            and report["owned_stop_observed"] is False
            and status == "failed",
            "worker-launch-accounting",
        )
    else:
        require((cleanup is None) == report["owned_stop_observed"], "worker-stop-accounting")
    if primary == "worker-launch-refused":
        pass
    elif primary == "fixture-cancelled":
        require(
            mode == "cancel"
            and frames == ["ready", "result"]
            and status == ("failed" if cleanup else "interrupted"),
            "worker-cancel-prefix",
        )
    elif primary == "fixture-deadline":
        require(
            mode == "deadline"
            and frames == ["ready", "result"]
            and status == ("failed" if cleanup else "incomplete"),
            "worker-deadline-prefix",
        )
    elif primary == "fixture-finish-deadline":
        require(
            mode == "finish-block"
            and frames == ["ready", "result", "finished"]
            and status == ("failed" if cleanup else "incomplete"),
            "worker-finish-deadline",
        )
    elif primary in (
        "worker-input-failed",
        "worker-deadline",
        "worker-transport-failed",
        "incomplete-worker-protocol",
        "worker-protocol-mismatch",
        "bounded-worker-frame",
        "too-many-worker-frames",
        "invalid-worker-frame",
        "worker-nonzero-exit",
        "worker-source-changed",
    ):
        require(
            status in (("failed", "incomplete") if not cleanup else ("failed",)),
            "worker-failed-status",
        )
    else:
        require(
            mode not in ("cancel", "deadline", "stall-before-read", "finish-block")
            and frames == ["ready", "result", "finished"]
            and primary == expected["error"]
            and status
            == (
                "failed"
                if cleanup
                else expected["fixture"]["status"]
                if expected["fixture"]
                else "failed"
            ),
            "worker-terminal-status",
        )
    require(
        _identity() == identity and _owner_identity() == owner,
        "worker-readback-source-changed",
    )
    return {
        "kind": "invented",
        "status": status,
        "host_or_process_qualified": False,
        "native_acceptance": False,
        "authority": dict(AUTHORITY),
    }


def _child(stall_before_read=False):
    if stall_before_read:
        # Deliberate fixed backpressure fixture, not a supplied script/target.
        time.sleep(BUDGET_SECONDS)
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    request = _request(raw)
    identity = _identity()

    def emit(value):
        encoded = encode(value)
        require(len(encoded) < MAX_BYTES, "bounded-worker-frame")
        sys.stdout.buffer.write(encoded + b"\n")
        sys.stdout.buffer.flush()

    emit({"phase": "ready", "request_sha256": digest(raw), "source_identity": identity})
    if request["mode"].startswith("deny-"):
        result = _expected_result(request, identity)
    else:
        from .bootstrap import run_fixture

        result = {
            "phase": "result",
            "fixture": run_fixture(encode(_fixture_config(request))),
            "error": None,
        }
        # Shared source inventory will include this module after integration.
        result["fixture"]["source_identity"] = identity
    emit(result)
    if request["mode"] in ("cancel", "deadline"):
        # Independent finite backstop for this invented trusted child only.
        time.sleep(BUDGET_SECONDS)
        return
    emit({"phase": "finished"})
    if request["mode"] == "finish-block":
        time.sleep(BUDGET_SECONDS)


if __name__ == "__main__":
    require(sys.argv[1:] == ["--fixed-child"], "fixed-worker-entry-only")
    _child()
