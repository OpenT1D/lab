"""Fixed Python owner and bounded private carrier, never a worker selector."""

import math
import os
import subprocess
import sys
from pathlib import Path

from experiments.lt1_diagnostic import native_supervisor as owner
from experiments.lt1_diagnostic import native_tree_removal as tree

WORKER = tree.ROOT / "experiments/lt1_diagnostic/native_tree_removal_worker.py"
FIXTURE = tree.ROOT / "tests/lt1_native_tree_worker.py"
CARRIER_LIMIT = 3 * tree.LIMIT


def argv(request, *, invented=False):
    path = Path(request["cleanup_parent"]["path"]) / (request["attempt"] + ".control.json")
    return [
        str(Path(sys.executable).resolve()),
        "-I",
        "-S",
        "-B",
        str(FIXTURE if invented else WORKER),
        str(path),
    ]


def complete_outer(value, raw, request, context_raw, producer_audit):
    """Exact owner envelope; unobserved outer evidence is not manufactured."""
    if type(value) is not dict:
        return False
    expected = {
        "schema",
        "kind",
        "request_sha256",
        "audit_sha256",
        "control_sha256",
        "control_path",
        "log_path",
        "log_sha256",
        "source_identity",
        "receipt",
        "producer_root",
        "producer_executable",
        "journal",
    }
    if set(value) != expected or value["schema"] != "opent1d.lt1-native-tree-owned-outer/1":
        return False
    invented = request["kind"] == "invented"
    if (
        value["kind"] != request["kind"]
        or value["request_sha256"] != tree.digest(raw)
        or value["source_identity"] != producer_audit
        or value["audit_sha256"] != tree.digest(tree.encoded(value["source_identity"]))
        or not tree.retention.sha(value["control_sha256"])
    ):
        return False
    for key in ("producer_root", "producer_executable"):
        path = value[key]
        if (
            type(path) is not str
            or not 0 < len(path) <= 4096
            or not Path(path).is_absolute()
            or str(Path(path)) != path
            or ".." in Path(path).parts
            or "\0" in path
        ):
            return False
    # Archived launch paths are data. Do not reopen the historical checkout or
    # executable, and do not construct a command that can be executed from them.
    control_path = str(
        Path(request["cleanup_parent"]["path"]) / (request["attempt"] + ".control.json")
    )
    relative = (
        "tests/lt1_native_tree_worker.py"
        if invented
        else "experiments/lt1_diagnostic/native_tree_removal_worker.py"
    )
    command = [
        value["producer_executable"],
        "-I",
        "-S",
        "-B",
        str(Path(value["producer_root"]) / relative),
        control_path,
    ]
    if value["control_path"] != control_path:
        return False
    log = str(Path(request["cleanup_parent"]["path"]) / (request["attempt"] + ".launch.log"))
    if value["log_path"] != log:
        return False
    carrier = tree.encoded(
        {
            "schema": "opent1d.lt1-native-tree-carrier/1",
            "request": raw.decode(),
            "context": context_raw.hex(),
            "audit": producer_audit,
        }
    )
    if value["control_sha256"] != tree.digest(carrier) or not tree.retention.sha(
        value["log_sha256"]
    ):
        return False
    journal = value["journal"]
    if (
        type(journal) is not dict
        or set(journal) != {"sha256", "identity"}
        or not tree.retention.sha(journal["sha256"])
    ):
        return False
    token = journal["identity"]
    if (
        type(token) is not dict
        or set(token) != set("device inode uid bytes mode mtime_ns ctime_ns".split())
        or not all(type(v) is int and v >= 0 for v in token.values())
        or token["uid"] != os.getuid()
        or token["mode"] != 0o600
        or token["bytes"] > tree.JOURNAL_LIMIT
    ):
        return False
    folder = tree._private_directory(request["cleanup_parent"]["path"])
    try:
        try:
            if (
                tree._read_at(folder, Path(command[-1]).name, CARRIER_LIMIT) != carrier
                or tree.digest(tree._read_at(folder, Path(log).name, tree.removal.FILE_LIMIT))
                != value["log_sha256"]
            ):
                return False
        except (OSError, ValueError):
            return False
    finally:
        os.close(folder)
    receipt = value["receipt"]
    if type(receipt) is not dict:
        return False
    required = {
        "argv",
        "status",
        "exit_code",
        "error",
        "cleanup_forced",
        "owned_processes",
        "remaining_owned_processes",
        "received_signals",
    }
    owned = receipt.get("owned_processes")
    if type(owned) is not list or not 0 < len(owned) <= 128:
        return False
    seen_pid, seen_start = set(), set()
    for process in owned:
        if (
            type(process) is not dict
            or set(process) != {"pid", "ppid", "pgid", "start", "alive"}
            or not all(type(process[k]) is int and process[k] > 0 for k in ("pid", "ppid", "pgid"))
            or process["pid"] == process["ppid"]
            or type(process["start"]) is not str
            or not 0 < len(process["start"]) <= 256
            or type(process["alive"]) is not bool
            or process["pid"] in seen_pid
            or (process["pid"], process["start"]) in seen_start
        ):
            return False
        seen_pid.add(process["pid"])
        seen_start.add((process["pid"], process["start"]))
    if owned[0]["pgid"] != owned[0]["pid"]:
        return False
    return bool(
        set(receipt) == required
        and receipt["argv"] == command + [tree.digest(raw), value["control_sha256"]]
        and receipt["status"] == "completed"
        and type(receipt["exit_code"]) is int
        and receipt["exit_code"] == 0
        and receipt["error"] is None
        and receipt["cleanup_forced"] is False
        and receipt["remaining_owned_processes"] == []
        and receipt["received_signals"] == []
    )


def _run_reviewed(
    raw, grants, context_raw, audit, *, invented=False, timeout=30, cancel=None, grace=0.5
):
    tree.admitted(raw, grants)
    r = tree.request(raw, context_raw, audit, invented=invented)
    tree.need(
        type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 300,
        "bounded owner deadline",
    )
    tree.need(
        type(grace) in (int, float) and math.isfinite(grace) and 0 <= grace <= 5,
        "bounded owner grace",
    )
    carrier = tree.encoded(
        {
            "schema": "opent1d.lt1-native-tree-carrier/1",
            "request": raw.decode(),
            "context": context_raw.hex(),
            "audit": audit,
        }
    )
    tree.need(len(carrier) <= CARRIER_LIMIT, "whole carrier before resources")
    command = argv(r, invented=invented) + [tree.digest(raw), tree.digest(carrier)]
    tree.need(sum(len(s.encode()) + 1 for s in command) <= 64 * 1024, "fixed exec budget")
    cleanup_path = Path(r["cleanup_parent"]["path"])
    control_path = Path(command[-3])
    log_path = cleanup_path / (r["attempt"] + ".launch.log")
    cleanup = tree._private_directory(cleanup_path)
    try:
        tree.bind(cleanup_path, cleanup, r["cleanup_parent"])
        if cancel is not None and cancel.is_set():
            # Native owner has its own exact pre-spawn interrupted receipt.
            receipt = owner.supervise(
                command,
                log_path,
                timeout=timeout,
                cancel=cancel,
                environment=dict(owner.ENVIRONMENT),
                stdin=subprocess.DEVNULL,
                before_spawn=lambda _: None,
            )
        else:
            fd = os.open(
                control_path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=cleanup,
            )
            try:
                view = memoryview(carrier)
                while view:
                    count = os.write(fd, view)
                    tree.need(count > 0, "control write")
                    view = view[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(cleanup)

            def last_guard(log):
                os.fchmod(log.fileno(), 0o600)
                tree.admitted(raw, grants if invented else tree.registry())
                tree.need(tree.source_identity() == audit, "owner late source")
                tree.bind(cleanup_path, cleanup, r["cleanup_parent"])
                tree.need(
                    tree._read_at(cleanup, control_path.name, CARRIER_LIMIT) == carrier,
                    "owner late carrier",
                )

            receipt = owner.supervise(
                command,
                log_path,
                timeout=timeout,
                cancel=cancel,
                grace=grace,
                environment=dict(owner.ENVIRONMENT),
                stdin=subprocess.DEVNULL,
                before_spawn=last_guard,
            )
        try:
            log_sha = tree.digest(tree._read_at(cleanup, log_path.name, tree.removal.FILE_LIMIT))
        except (OSError, ValueError):
            log_sha = None
        journal_pin = None
        attempt = None
        try:
            attempt = tree._private_directory(cleanup_path / r["attempt"])
            journal_raw = tree._read_at(attempt, "events.jsonl", tree.JOURNAL_LIMIT)
            journal_pin = {
                "sha256": tree.digest(journal_raw),
                "identity": tree.removal.signature(
                    os.stat("events.jsonl", dir_fd=attempt, follow_symlinks=False)
                ),
            }
        except (OSError, ValueError):
            pass
        finally:
            if attempt is not None:
                os.close(attempt)
        return {
            "schema": "opent1d.lt1-native-tree-owned-outer/1",
            "kind": r["kind"],
            "request_sha256": tree.digest(raw),
            "audit_sha256": tree.digest(tree.encoded(audit)),
            "control_sha256": tree.digest(carrier),
            "control_path": str(control_path),
            "log_path": str(log_path),
            "source_identity": audit,
            "receipt": receipt,
            "log_sha256": log_sha,
            "producer_root": str(tree.ROOT),
            "producer_executable": str(Path(sys.executable).resolve()),
            "journal": journal_pin,
        }
    finally:
        os.close(cleanup)


def remove(raw, context_raw, *, audit, timeout=30, cancel=None, grace=0.5):
    grants = tree.registry()
    tree.admitted(raw, grants)
    return _run_reviewed(
        raw, grants, context_raw, audit, timeout=timeout, cancel=cancel, grace=grace
    )
