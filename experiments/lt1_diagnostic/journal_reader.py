"""Engine-free committed-prefix reconstruction. Never admits native execution."""

import re
from pathlib import Path

from experiments.lt1_diagnostic import reader
from experiments.m3.researcher.intake import read_regular
from experiments.m4.initial_load.common import source_closure

ROOT = reader.ROOT
JS_FILES = (
    "native_loader.mjs",
    "direct.mjs",
    "wrapped.mjs",
    "protocol.mjs",
    "../adapter_audit/lt1_sampled.mjs",
    "../m0/lt1/record.mjs",
    "attempt_journal.mjs",
    "integration_gate.mjs",
    "integration_worker.mjs",
)
SCHEMA = "opent1d.lt1-attempt-journal/1"


def relative_source_name(path):
    return path.relative_to(ROOT).as_posix()


def identity(plan_raw):
    paths = set(reader.implementation()) | {"experiments/lt1_diagnostic/journal_reader.py"}
    paths.update((Path("experiments/lt1_diagnostic") / name).as_posix() for name in JS_FILES)
    # Normalize the fixed ../ references before static closure; never archive paths.
    paths = {relative_source_name((ROOT / name).resolve()) for name in paths}
    while True:
        paths = set(source_closure(paths))
        initializers = {
            (p / "__init__.py").as_posix()
            for name in paths
            for p in Path(name).parents
            if p.parts and (ROOT / p / "__init__.py").is_file()
        }
        if initializers <= paths:
            break
        paths.update(initializers)
    return {
        "protocol": reader.identity(plan_raw),
        "implementation": {
            name: reader.digest((ROOT / name).read_bytes()) for name in sorted(paths)
        },
    }


def checked(path, expected, limit, label):
    raw = read_regular(path, limit, label)
    reader.require(
        isinstance(expected, str)
        and re.fullmatch("[a-f0-9]{64}", expected)
        and reader.digest(raw) == expected,
        label + "-identity",
    )
    return raw


def inspect(journal_path, plan_path, receipt_path, journal_sha256, receipt_sha256):
    raw = checked(journal_path, journal_sha256, 16 * 1024 * 1024, "journal")
    receipt_raw = checked(receipt_path, receipt_sha256, 4 * 1024 * 1024, "process receipt")
    plan_raw = read_regular(plan_path, 65536, "LT1 plan")
    plan = reader.validate_plan(reader.decode(plan_raw))
    receipt = reader.decode(receipt_raw)
    reader.require(isinstance(receipt, dict), "process receipt")
    reader.require(receipt.get("remaining_owned_processes") == [], "cleanup unresolved")
    process_status = receipt.get("status")
    reader.require(process_status in {"completed", "failed", "interrupted"}, "process status")
    reader.require(type(receipt.get("exit_code")) is int, "process exit")
    if process_status == "completed":
        reader.require(receipt["exit_code"] == 0, "completion exit")
    chunks = raw.splitlines(keepends=True)
    tail = b""
    if chunks and not chunks[-1].endswith(b"\n"):
        tail = chunks.pop()
    reader.require(bool(chunks), "committed journal header")
    reader.require(len(chunks) <= 130, "journal record count")
    records = [reader.decode(chunk) for chunk in chunks]
    head = records.pop(0)
    reader.fields(
        head,
        "type schema kind mode identity attempt output_root owner_pid "
        "engine_grant_sha256 integration_sha256",
    )
    reader.require(head["type"] == "start" and head["schema"] == SCHEMA, "journal schema")
    reader.require(head["identity"] == identity(plan_raw), "journal source identity")
    reader.require(head["kind"] in {"invented", "native-unadmitted"}, "journal kind")
    reader.require(head["mode"] in {"direct", "wrapped"}, "journal mode")
    reader.require(type(head["owner_pid"]) is int and head["owner_pid"] > 1, "journal owner")
    reader.require(
        isinstance(head["output_root"], str) and head["output_root"].startswith("/"),
        "journal output",
    )
    argv = receipt.get("argv")
    reader.require(
        isinstance(argv, list) and len(argv) > 0 and argv[-1] == head["output_root"],
        "process output binding",
    )
    owned = receipt.get("owned_processes")
    reader.require(
        isinstance(owned, list)
        and any(isinstance(p, dict) and p.get("ppid") == head["owner_pid"] for p in owned),
        "process owner binding",
    )
    reader.require(
        isinstance(head["attempt"], str)
        and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", head["attempt"]),
        "journal attempt",
    )
    for name in ("engine_grant_sha256", "integration_sha256"):
        reader.require(
            isinstance(head[name], str) and re.fullmatch("[a-f0-9]{64}", head[name]),
            "journal grant identity",
        )
    rows = []
    finish = None
    for record in records:
        reader.require(isinstance(record, dict) and finish is None, "record after finish")
        if record.get("type") == "row":
            reader.fields(record, "type ordinal row")
            reader.require(
                type(record["ordinal"]) is int and record["ordinal"] == len(rows), "row ordinal"
            )
            rows.append(record["row"])
            reader.require(len(rows) <= 128, "row bound")
        elif record.get("type") == "finish":
            reader.fields(
                record, "type rows_in_memory status primary_error diagnostic_error diagnostic_tail"
            )
            reader.require(
                type(record["rows_in_memory"]) is int
                and len(rows) <= record["rows_in_memory"] <= 128,
                "memory row count",
            )
            if record["status"] == "completed":
                reader.require(record["rows_in_memory"] == len(rows), "completed row count")
            finish = record
        else:
            raise ValueError("journal record type")
    reader.require(finish is None or not tail, "tail after finish")
    common = {
        "schema": reader.SCHEMA,
        "kind": head["kind"],
        "identity": head["identity"]["protocol"],
        "mode": head["mode"],
        "rows": rows,
    }
    if finish is not None:
        native = {
            key: finish[key]
            for key in ("status", "primary_error", "diagnostic_error", "diagnostic_tail")
        }
        reader.validate({**common, **native}, plan)
    else:
        native = {
            "status": "started",
            "primary_error": None,
            "diagnostic_error": None,
            "diagnostic_tail": [],
        }
    reported_process_status = process_status
    signals = receipt.get("received_signals")
    reader.require(
        isinstance(signals, list) and all(type(s) is int and s > 0 for s in signals),
        "process signals",
    )
    process_error = receipt.get("error")
    if signals:
        process_status = "interrupted"
        process_error = process_error or "External signal " + ",".join(map(str, signals))
    reader.require(
        process_error is None or (isinstance(process_error, str) and len(process_error) <= 4096),
        "process error",
    )
    effective = dict(native)
    if process_status != "completed" or finish is None:
        effective["status"] = "interrupted" if process_status == "interrupted" else "failed"
        effective["primary_error"] = (
            native["primary_error"]
            or process_error
            or (
                "Worker finish missing"
                if finish is None
                else "Worker exit " + str(receipt["exit_code"])
            )
        )
    result = reader.validate({**common, **effective}, plan)
    return {
        **result,
        "attempt": head["attempt"],
        "journal_bytes_sha256": reader.digest(raw),
        "process_receipt_bytes_sha256": reader.digest(receipt_raw),
        "plan_bytes_sha256": reader.digest(plan_raw),
        "uncommitted_tail_bytes": len(tail),
        "worker_finish_present": finish is not None,
        "process_status": process_status,
        "reported_process_status": reported_process_status,
        "process_error": process_error,
        "native_execution_authorized": False,
        "native_acceptance": False,
    }
