"""Engine-free v2 route/session reader; actual outer bytes are never rewritten.

Nested durable sessions have a new explicit parent/output relationship. Their
scientific rows use the unchanged strict fractional trace validator.
"""

import base64
import json
from pathlib import PurePosixPath

from experiments.gui.ownership import ProcessTable
from experiments.lt1_diagnostic import journal_reader, reader
from experiments.lt1_diagnostic import native_route as route

MAGIC = b"OPENT1D-LT1-ROUTE-2\n"
ACK_MAGIC = b"OPENT1D-LT1-ROUTE-ACK-2\n"


def frame_value(raw, entry_raw, observation_raw, packet, *, invented):
    route.need(
        isinstance(raw, bytes)
        and 0 < len(raw) <= 65536
        and raw.startswith(MAGIC)
        and raw.endswith(b"\n"),
        "bounded single frame",
    )
    parts = raw.split(b"\n")
    route.need(len(parts) == 3 and not parts[-1], "frame EOF")
    value = json.loads(parts[1], object_pairs_hook=route.storage.unique_object)
    route.need(MAGIC + route.encoded(value) + b"\n" == raw, "canonical frame")
    route.storage.fields(
        value,
        "schema kind phase observed_at grant_sha256 attempt nonce_sha256 facts "
        "native_host_qualified native_acceptance setup_admitted "
        "native_execution_authorized",
    )
    entry, observation = route.decode(entry_raw), route.decode(observation_raw)
    route.need(
        value["schema"] == "opent1d.lt1-route-observation/2"
        and value["kind"] == ("invented" if invented else "observed")
        and value["phase"] == "unqualified-current-process-observation"
        and value["grant_sha256"] == route.storage.digest(observation_raw)
        and all(
            value[k] is False
            for k in (
                "native_host_qualified",
                "native_acceptance",
                "setup_admitted",
                "native_execution_authorized",
            )
        ),
        "frame schema/origin",
    )
    route.need(
        value["attempt"] == entry["attempt"] and value["nonce_sha256"] == entry["nonce_sha256"],
        "frame attempt/nonce",
    )
    facts = value["facts"]
    route.storage.fields(
        facts,
        "pid ppid exec_path node platform arch executable_sha256 producer_sha256 "
        "process_argv exec_argv environment_keys environment stdio "
        "startup_environment_keys",
    )
    route.need(
        type(facts["pid"]) is int
        and facts["pid"] > 1
        and facts["pid"] != entry["owner_pid"]
        and facts["ppid"] == entry["owner_pid"]
        and facts["exec_path"] == observation["entry_executable"]
        and facts["process_argv"] == entry["process_argv"]
        and facts["exec_argv"] == []
        and facts["environment"] == observation["runtime_environment"]
        and facts["environment_keys"] == sorted(observation["runtime_environment"])
        and facts["startup_environment_keys"]
        == sorted([*observation["runtime_environment"], route.CARRIER])
        and facts["stdio"] == "unobserved",
        "frame actual process/ambient bindings",
    )
    route.need(
        all(
            facts[k] == observation["runtime"][k]
            for k in ("node", "platform", "arch", "executable_sha256")
        )
        and facts["producer_sha256"] == observation["producer_sha256"],
        "frame runtime/source",
    )
    route.packet_binding(entry, observation, packet)
    return value


def ack_for(raw, value):
    return (
        ACK_MAGIC
        + route.encoded(
            {
                "schema": "opent1d.lt1-route-ack/2",
                "kind": value["kind"],
                "frame_sha256": route.storage.digest(raw),
                "grant_sha256": value["grant_sha256"],
                "attempt": value["attempt"],
                "nonce_sha256": value["nonce_sha256"],
            }
        )
        + b"\n"
    )


def acknowledge(raw, entry_raw, observation_raw, packet, *, invented):
    value = frame_value(raw, entry_raw, observation_raw, packet, invented=invented)
    child = ProcessTable().one(value["facts"]["pid"])
    owner = ProcessTable().one(route.os.getpid())
    entry = route.decode(entry_raw)
    route.need(
        child
        and child["alive"]
        and child["ppid"] == route.os.getpid()
        and owner
        and owner["start"] == entry["owner_start"],
        "live actual frame owner/entry",
    )
    return ack_for(raw, value), child


def _session(raw, name, entry, plan_raw, outer, kind):
    route.need(isinstance(raw, bytes) and 0 < len(raw) <= 16 * 1024 * 1024, "bounded journal")
    *chunks, tail = raw.split(b"\n")
    route.need(chunks and len(chunks) <= 130, "committed header/count")
    records = [reader.decode(v) for v in chunks]
    head = records.pop(0)
    reader.fields(
        head,
        "type schema kind mode identity attempt output_root owner_pid "
        "engine_grant_sha256 integration_sha256",
    )
    route.need(
        head["type"] == "start"
        and head["schema"] == journal_reader.SCHEMA
        and head["kind"] == kind
        and head["mode"] in ("direct", "wrapped")
        and head["identity"] == journal_reader.identity(plan_raw),
        "journal source/origin",
    )
    route.need(
        head["output_root"] == entry["roots"]["output"] + "/" + name
        and head["owner_pid"] == entry["owner_pid"]
        and head["attempt"] == entry["attempt"]
        and head["engine_grant_sha256"] == entry["engine_sha256"]
        and head["integration_sha256"] == entry["integration_sha256"],
        "actual parent/session binding",
    )
    rows = []
    finish = None
    for record in records:
        route.need(isinstance(record, dict) and finish is None, "record after terminal")
        if record.get("type") == "row":
            reader.fields(record, "type ordinal row")
            route.need(
                type(record["ordinal"]) is int and record["ordinal"] == len(rows), "row ordinal"
            )
            rows.append(record["row"])
        else:
            reader.fields(
                record, "type rows_in_memory status primary_error diagnostic_error diagnostic_tail"
            )
            route.need(
                record["type"] == "finish"
                and type(record["rows_in_memory"]) is int
                and len(rows) <= record["rows_in_memory"] <= 128,
                "terminal record",
            )
            if record["status"] == "completed":
                route.need(record["rows_in_memory"] == len(rows), "completed row count")
            finish = record
    route.need(finish is None or not tail, "tail after finish")
    plan = reader.validate_plan(reader.decode(plan_raw))
    native = (
        {k: finish[k] for k in ("status", "primary_error", "diagnostic_error", "diagnostic_tail")}
        if finish
        else {
            "status": "started",
            "primary_error": None,
            "diagnostic_error": None,
            "diagnostic_tail": [],
        }
    )
    common = {
        "schema": reader.SCHEMA,
        "kind": kind,
        "identity": head["identity"]["protocol"],
        "mode": head["mode"],
        "rows": rows,
    }
    if finish:
        reader.validate({**common, **native}, plan)
    clean = (
        outer.get("status") == "completed"
        and type(outer.get("exit_code")) is int
        and outer["exit_code"] == 0
        and outer.get("error") is None
        and outer.get("cleanup_error") is None
        and outer.get("signal_error") is None
        and outer.get("received_signals") == []
        and outer.get("remaining_owned_processes") == []
    )
    if not clean or not finish:
        native = {
            **native,
            "status": "interrupted"
            if outer.get("status") == "interrupted" or outer.get("received_signals")
            else "failed",
            "primary_error": native["primary_error"]
            or outer.get("error")
            or "Worker finish/clean outer missing",
        }
    result = reader.validate({**common, **native}, plan)
    return {
        **result,
        "name": name,
        "rows": rows,
        "worker_finish_present": finish is not None,
        "uncommitted_tail_bytes": len(tail),
    }


def inspect(
    receipt_raw,
    expected_receipt_sha256,
    entry_raw,
    observation_raw,
    packet,
    output_files,
    *,
    expected_identity,
):
    """Bounded externally pinned data only; never reopens a packet or native code."""
    source = route.source_identity()
    route.need(source == expected_identity, "current route reader source")
    route.need(
        isinstance(receipt_raw, bytes)
        and len(receipt_raw) <= 4 * 1024 * 1024
        and route.storage.digest(receipt_raw) == expected_receipt_sha256,
        "expected actual route receipt",
    )
    receipt = json.loads(receipt_raw, object_pairs_hook=route.storage.unique_object)
    entry = route.decode(entry_raw)
    observation = route.decode(observation_raw)
    route.need(
        receipt["schema"] == "opent1d.lt1-native-route-receipt/2"
        and receipt["kind"] == entry["kind"]
        and receipt["source_identity"] == source
        and receipt["entry_sha256"] == route.storage.digest(entry_raw)
        and receipt["observation_sha256"] == route.storage.digest(observation_raw),
        "route source/control identity",
    )
    route.need(
        entry["schema"] == "opent1d.lt1-native-route-grant/2"
        and entry["entry_sources"] == route.prior.grant_sources(source)
        and observation["schema"] == "opent1d.lt1-route-observation-grant/2"
        and observation["producer_sha256"]
        == source["implementation"]["experiments/lt1_diagnostic/native_route_observation.mjs"],
        "current version2 complete control source",
    )
    route.need(
        receipt["packet_sha256"] == route.packet_binding(entry, observation, packet)
        and receipt["roots"] == entry["roots"]
        and receipt["case_id"] == entry["case_id"]
        and receipt["slot"] == entry["slot"],
        "route packet/roots",
    )
    route.need(
        all(receipt[k] is False for k in route.AUTHORITY)
        and receipt["startup_confinement_qualified"] is False
        and receipt["startup_environment_keys"]
        == sorted([*route.transport.owner.ENVIRONMENT, route.CARRIER])
        and receipt["post_clear_environment_keys"] == sorted(observation["runtime_environment"]),
        "unqualified startup facts",
    )
    route.need(
        isinstance(output_files, dict)
        and len(output_files) <= 16
        and all(
            isinstance(k, str)
            and not PurePosixPath(k).is_absolute()
            and ".." not in PurePosixPath(k).parts
            and isinstance(v, bytes)
            and len(v) <= 16 * 1024 * 1024
            for k, v in output_files.items()
        )
        and sum(map(len, output_files.values())) <= 32 * 1024 * 1024,
        "bounded output bytes",
    )
    route.need(
        {k: route.storage.digest(v) for k, v in output_files.items()} == receipt["output_sha256"],
        "externally pinned exact output inventory",
    )
    outer = receipt["transport"]["outer"]
    argv = outer.get("argv")
    route.need(
        isinstance(argv, list)
        and argv[-5:] == entry["process_argv"]
        and argv[1:4] == ["-I", "-S", "-B"],
        "actual grant-free outer argv",
    )
    route.need(outer.get("remaining_owned_processes") == [], "owned cleanup unresolved")
    exchange = receipt["transport"]["exchange"]
    frame = base64.b64decode(exchange["frame_raw_b64"], validate=True)
    ack = base64.b64decode(exchange["ack_raw_b64"], validate=True)
    sessions = []
    channel = False
    if frame:
        value = frame_value(
            frame, entry_raw, observation_raw, packet, invented=entry["kind"] == "invented"
        )
        child = receipt["entry_identity"]
        route.need(
            child.get("pid") == value["facts"]["pid"]
            and child.get("ppid") == entry["owner_pid"]
            and any(
                all(p.get(k) == child.get(k) for k in ("pid", "ppid", "pgid", "start"))
                for p in outer.get("owned_processes", [])
            ),
            "actual one entry identity",
        )
        channel = (
            ack == ack_for(frame, value)
            and exchange["status"] == "ack-sent"
            and exchange["ack_sent"] is True
            and exchange["frame_eof"] is True
            and exchange["ack_eof_sent"] is True
            and exchange["thread_finished"] is True
            and not receipt["transport"]["resource_close_errors"]
        )
    wanted = 2 if entry["case_id"] == "C15" else 1
    allowed = {"route.json", "descendant-root.json", "grandchild.json", "descendant-stop"} | {
        f"session-{i:04d}/events.jsonl" for i in range(wanted)
    }
    route.need(set(output_files) <= allowed, "closed route/session inventory")
    for index in range(wanted):
        name = f"session-{index:04d}"
        key = name + "/events.jsonl"
        if key in output_files:
            route.need(channel, "journal without acknowledged owned entry")
            sessions.append(
                _session(output_files[key], name, entry, packet["plan.json"], outer, entry["kind"])
            )
    completed = (
        channel
        and receipt["source_and_packet_stable"] is True
        and len(sessions) == wanted
        and all(v["status"] == "completed" for v in sessions)
    )
    if "route.json" in output_files:
        child = json.loads(
            output_files["route.json"], object_pairs_hook=route.storage.unique_object
        )
        route.need(
            child["kind"] == entry["kind"]
            and child["frame_sha256"] == route.storage.digest(frame)
            and child["ack_sha256"] == route.storage.digest(ack),
            "child channel/origin binding",
        )
        route.need(
            child["worker"] is None or child["worker"]["packet_sha256"] == receipt["packet_sha256"],
            "worker consumed owned packet",
        )
        route.need(
            child["pid"] == receipt["entry_identity"]["pid"]
            and child["ppid"] == entry["owner_pid"]
            and child["startup_environment_keys"]
            == sorted([*observation["runtime_environment"], route.CARRIER])
            and child["post_clear_environment_keys"] == sorted(observation["runtime_environment"]),
            "actual child identity/runtime environment",
        )
        completed = (
            completed
            and child.get("worker") is not None
            and child["worker"].get("completed") is True
        )
    else:
        completed = False
    route.need(route.source_identity() == source, "reader source changed")
    return {
        "schema": "opent1d.lt1-native-route-readback/2",
        "kind": entry["kind"],
        "status": "completed" if completed else "incomplete",
        "sessions": sessions,
        "channel_bound": channel,
        "actual_outer_unchanged": True,
        "output_copy_accounting_required": True,
        **route.AUTHORITY,
    }
