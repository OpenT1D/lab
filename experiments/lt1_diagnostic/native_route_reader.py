"""Engine-free v2 route/session reader; actual outer bytes are never rewritten.

Nested durable sessions have a new explicit parent/output relationship. Their
scientific rows use the unchanged strict fractional trace validator.
"""

import base64
import copy
import json
import re
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


def _control(entry, observation, packet, source, producer_paths):
    route.storage.fields(entry, route.FIELDS)
    route.storage.fields(
        observation,
        "schema packet_sha256 runtime entry_executable owner_pid owner_start "
        "attempt nonce_sha256 profile_sha256 producer_sha256 reader_identity "
        "process_argv runtime_environment",
    )
    route.need(
        type(entry["owner_pid"]) is int
        and entry["owner_pid"] > 1
        and type(entry["owner_start"]) is str
        and 0 < len(entry["owner_start"]) <= 512
        and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", entry["attempt"])
        and route.prior.base.preflight.host_context.sha(entry["nonce_sha256"]),
        "typed control owner/attempt/nonce",
    )
    roots = route.prior.base._roots(entry["roots"])
    historical_root = PurePosixPath(producer_paths["root"])
    role = historical_root / (
        "tests/lt1_native_route_fixture.mjs"
        if entry["kind"] == "invented"
        else "experiments/lt1_diagnostic/native_route_cli.mjs"
    )
    argv = entry["process_argv"]
    route.need(
        type(argv) is list
        and len(argv) == 5
        and argv[1] == str(role)
        and argv[2:] == [str(roots[k]) for k in ("staging", "packet", "output")]
        and type(argv[0]) is str
        and argv[0].startswith("/"),
        "fixed historical Node ABI",
    )
    route.need(
        all(
            observation[k] == entry[k]
            for k in (
                "owner_pid",
                "owner_start",
                "attempt",
                "nonce_sha256",
                "profile_sha256",
                "process_argv",
            )
        )
        and observation["entry_executable"] == argv[0],
        "complete observation/entry crossbindings",
    )
    route.storage.fields(observation["runtime"], "node platform arch executable_sha256")
    if entry["kind"] == "native-unadmitted":
        route.need(
            argv[0] == str(roots["staging"] / "runtime/bin/node")
            and observation["runtime"]
            == {
                k: route.prior.base.preflight.RUNTIME[k]
                for k in ("node", "platform", "arch", "executable_sha256")
            },
            "selected native producer ABI",
        )
    runtime_env = observation["runtime_environment"]
    route.need(
        type(runtime_env) is dict
        and all(runtime_env.get(k) == v for k, v in route.transport.owner.ENVIRONMENT.items())
        and set(runtime_env)
        <= set(route.transport.owner.ENVIRONMENT)
        | ({"__CF_USER_TEXT_ENCODING"} if observation["runtime"]["platform"] == "darwin" else set())
        and all(type(v) is str and 0 < len(v) <= 128 for v in runtime_env.values()),
        "explicit historical runtime environment",
    )
    engine = route.legacy.decoded(packet["grant.json"])
    integration = route.legacy.decoded(packet["integration-grant.json"])
    host = route.decode(packet["integration_host_receipt.json"])
    route.storage.fields(
        engine,
        "schema source_revision node platform arch host staging_root mode "
        "plan_sha256 setup_receipt_sha256 host_receipt_sha256 "
        "rights_receipt_sha256 security_receipt_sha256 files worker_files",
    )
    route.storage.fields(
        integration,
        "schema engine_grant_sha256 host_receipt_sha256 output_root attempt "
        "owner_pid reader_identity implementation",
    )
    route.need(
        engine["schema"] == "opent1d.lt1-native-grant/1"
        and engine["source_revision"] == route.prior.base.preflight.REVISION
        and engine["mode"] in ("direct", "wrapped")
        and engine["staging_root"] == entry["roots"]["staging"]
        and all(
            engine[k] == route.prior.base.preflight.RUNTIME[k] for k in ("node", "platform", "arch")
        ),
        "engine schema/source/runtime/roots",
    )
    route.need(
        all(
            engine[n + "_sha256"] == route.storage.digest(packet[n + ".json"])
            for n in route.legacy.RECEIPTS
        )
        and engine["setup_receipt_sha256"] == entry["setup_sha256"]
        and engine["worker_files"] == route.legacy._worker(route.legacy.WORKER),
        "opaque packet/old worker byte bindings",
    )
    route.need(
        type(engine["files"]) is dict
        and set(route.legacy.ENTRIES) <= set(engine["files"])
        and len(engine["files"]) <= 4096
        and all(
            type(k) is str
            and len(k) <= 512
            and not k.startswith("/")
            and all(p not in ("", ".", "..") for p in k.split("/"))
            and "\\" not in k
            and route.prior.base.preflight.host_context.sha(v)
            for k, v in engine["files"].items()
        ),
        "bounded declared staging map",
    )
    route.need(
        integration["schema"] == "opent1d.lt1-integration-grant/1"
        and integration["engine_grant_sha256"] == entry["engine_sha256"]
        and integration["host_receipt_sha256"]
        == route.storage.digest(packet["integration_host_receipt.json"])
        and integration["output_root"] == entry["roots"]["output"]
        and type(integration["owner_pid"]) is int
        and integration["owner_pid"] == entry["owner_pid"]
        and integration["attempt"] == entry["attempt"]
        and integration["reader_identity"]
        == observation["reader_identity"]
        == journal_reader.identity(packet["plan.json"])
        and integration["implementation"] == route.legacy._worker(route.legacy.INTEGRATION),
        "complete integration/reader bindings",
    )
    route.need(
        host["schema"] == "opent1d.lt1-native-route-host/2"
        and host["kind"] == ("invented" if entry["kind"] == "invented" else "observed")
        and host["purpose"] == "qualification-only"
        and host["entry_sources"] == entry["entry_sources"]
        and host["profile_sha256"] == entry["profile_sha256"]
        and host["runtime_environment"] == runtime_env
        and host["owner_context"]["observer"]["pid"] == entry["owner_pid"]
        and host["owner_context"]["observer"]["start"] == entry["owner_start"],
        "versioned historical host origin/context",
    )
    route.need(
        set(host["roots"]) == set(roots)
        and all(host["roots"][k]["path"] == entry["roots"][k] for k in roots),
        "host root crossbindings",
    )
    route.need(
        type(entry["case_id"]) is str and type(entry["slot"]) is str,
        "typed fixed case/slot",
    )
    # Cases import this reader for the live consumer; defer the reverse import
    # until both modules are initialized and validate only the owned plan bytes.
    from experiments.lt1_diagnostic.native_route_cases import validate_plan

    validate_plan(
        entry["case_id"], entry["slot"], reader.decode(packet["plan.json"]), engine["mode"]
    )
    return engine["mode"]


def _session(raw, name, entry, plan_raw, outer, kind, mode):
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
        and head["mode"] == mode
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


def _producer_errors(receipt):
    """Recorded intake failures remain authoritative even beside positive flags."""
    route.need(
        type(receipt) is dict
        and all(name in receipt for name in ("postcheck_error", "output_snapshot_error")),
        "producer error fields",
    )
    for name in ("postcheck_error", "output_snapshot_error"):
        value = receipt[name]
        route.need(
            value is None or (type(value) is str and 0 < len(value) <= 16384),
            "bounded producer error",
        )
    return all(receipt[name] is None for name in ("postcheck_error", "output_snapshot_error"))


def _worker_report(worker, entry, packet_hashes, sessions, output_files):
    route.storage.fields(
        worker,
        "schema kind case_id slot verification_context_origin completed construction_count "
        "patient_reset_calls nonfinite_initial_state_probe initial_state_consumed_observation "
        "native_basal sessions packet_sha256 native_acceptance native_execution_authorized",
    )
    route.need(
        worker["schema"] == "opent1d.lt1-buffer-worker/2"
        and all(worker[k] == entry[k] for k in ("kind", "case_id", "slot"))
        and worker["verification_context_origin"]
        == ("invented" if entry["kind"] == "invented" else "current-runtime")
        and type(worker["completed"]) is bool
        and worker["native_acceptance"] is False
        and worker["native_execution_authorized"] is False,
        "worker schema/origin/case context",
    )
    route.need(worker["packet_sha256"] == packet_hashes, "worker consumed owned packet")
    route.need(type(worker["sessions"]) is list, "worker session reports")
    expected = []
    for session in sessions:
        name = session["name"]
        raw = output_files[name + "/events.jsonl"]
        # _session already validates these exact bytes. Bind the producer footer,
        # not its effective status/committed count after an outer failure downgrade.
        terminal = reader.decode(raw.split(b"\n")[-2]) if raw.endswith(b"\n") else None
        route.need(
            terminal is not None and terminal.get("type") == "finish",
            "worker report without durable terminal",
        )
        expected.append(
            {
                "name": name,
                "status": terminal["status"],
                "rows": terminal["rows_in_memory"],
                "journal_sha256": route.storage.digest(raw),
            }
        )
    route.need(
        worker["sessions"] == expected
        and all(
            type(item) is dict
            and type(item.get("rows")) is int
            and set(item) == {"name", "status", "rows", "journal_sha256"}
            for item in worker["sessions"]
        ),
        "worker reports exact durable sessions",
    )
    route.need(
        worker["completed"]
        == (bool(expected) and all(s["status"] == "completed" for s in expected)),
        "worker terminal completion",
    )


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
    original_packet, original_outputs, original_expected = packet, output_files, expected_identity
    route.need(
        type(packet) is dict
        and set(packet) == set(route.PACKET)
        and all(type(v) is bytes and 0 < len(v) <= 4 * 1024 * 1024 for v in packet.values())
        and sum(map(len, packet.values())) <= 32 * 1024 * 1024,
        "immutable exact packet buffers",
    )
    route.need(
        type(output_files) is dict
        and len(output_files) <= 16
        and all(type(v) is bytes and len(v) <= 16 * 1024 * 1024 for v in output_files.values())
        and sum(map(len, output_files.values())) <= 32 * 1024 * 1024,
        "immutable bounded output buffers",
    )
    packet, output_files = dict(packet), dict(output_files)
    expected_identity = copy.deepcopy(expected_identity)
    source = route.source_identity()
    route.need(source == expected_identity, "current route reader source")
    route.need(
        type(receipt_raw) is bytes
        and len(receipt_raw) <= 4 * 1024 * 1024
        and route.storage.digest(receipt_raw) == expected_receipt_sha256,
        "expected actual route receipt",
    )
    receipt = json.loads(receipt_raw, object_pairs_hook=route.storage.unique_object)
    producer_clean = _producer_errors(receipt)
    entry = route.decode(entry_raw)
    observation = route.decode(observation_raw)
    producer = receipt["source_identity"]
    route.storage.fields(producer, "implementation python executable_sha256")
    route.need(
        type(producer["implementation"]) is dict
        and set(producer["implementation"]) == set(source["implementation"])
        and all(
            route.prior.base.preflight.host_context.sha(v)
            for v in producer["implementation"].values()
        ),
        "historical complete producer audit",
    )
    producer_code = copy.deepcopy(producer)
    current_code = copy.deepcopy(source)
    for name in route.prior.AUTHORITY_SOURCES:
        producer_code["implementation"].pop(name)
        current_code["implementation"].pop(name)
    route.need(producer_code == current_code, "unchanged producer code and nonauthority context")
    route.need(
        receipt["schema"] == "opent1d.lt1-native-route-receipt/2"
        and receipt["kind"] == entry["kind"]
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
    producer_paths = receipt["producer_paths"]
    route.storage.fields(producer_paths, "root python")
    route.need(
        all(
            type(v) is str
            and 0 < len(v) <= 4096
            and "\0" not in v
            and PurePosixPath(v).is_absolute()
            and str(PurePosixPath(v)) == v
            and ".." not in PurePosixPath(v).parts
            for v in producer_paths.values()
        ),
        "historical producer paths",
    )
    mode = _control(entry, observation, packet, source, producer_paths)
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
    route.storage.fields(entry, route.FIELDS)
    route.need(
        entry["kind"] in ("invented", "native-unadmitted")
        and type(entry["owner_pid"]) is int
        and entry["owner_pid"] > 1
        and isinstance(entry["owner_start"], str)
        and 0 < len(entry["owner_start"]) <= 512,
        "typed owner context",
    )
    outer = receipt["transport"]["outer"]
    argv = outer.get("argv")
    route.need(
        isinstance(argv, list)
        and len(argv) == 12
        and all(type(v) is str and 0 < len(v) <= 4096 and "\0" not in v for v in argv)
        and argv[0] == producer_paths["python"]
        and argv[4]
        == str(
            PurePosixPath(producer_paths["root"])
            / (
                "tests/lt1_native_route_exec.py"
                if entry["kind"] == "invented"
                else "experiments/lt1_diagnostic/native_route_exec.py"
            )
        )
        and all(v.isascii() and v.isdigit() and str(int(v)) == v and int(v) > 2 for v in argv[5:7])
        and argv[5] != argv[6]
        and argv[-5:] == entry["process_argv"]
        and argv[1:4] == ["-I", "-S", "-B"],
        "actual grant-free outer argv",
    )
    route.need(outer.get("remaining_owned_processes") == [], "owned cleanup unresolved")
    exchange = receipt["transport"]["exchange"]
    frame = base64.b64decode(exchange["frame_raw_b64"], validate=True)
    ack = base64.b64decode(exchange["ack_raw_b64"], validate=True)
    sent_text = exchange.get("ack_sent_raw_b64")
    route.need(type(sent_text) is str and len(sent_text) <= 1368, "bounded actual sent ACK")
    sent = base64.b64decode(sent_text, validate=True)
    route.need(
        len(sent) <= 1024 and base64.b64encode(sent).decode() == sent_text,
        "canonical actual sent ACK",
    )
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
            and sent == ack
            and exchange["status"] == "ack-sent"
            and exchange["ack_sent"] is True
            and exchange["frame_eof"] is True
            and exchange["ack_eof_sent"] is True
            and exchange["thread_finished"] is True
            and not receipt["transport"]["resource_close_errors"]
        )
    wanted = 2 if entry["case_id"] == "C15" else 1
    allowed = (
        {"route.json"}
        | (
            {"descendant-root.json", "grandchild.json", "descendant-stop"}
            if entry["case_id"] == "C18"
            else set()
        )
    ) | {f"session-{i:04d}/events.jsonl" for i in range(wanted)}
    route.need(set(output_files) <= allowed, "closed route/session inventory")
    for index in range(wanted):
        name = f"session-{index:04d}"
        key = name + "/events.jsonl"
        if key in output_files:
            route.need(channel, "journal without acknowledged owned entry")
            sessions.append(
                _session(
                    output_files[key], name, entry, packet["plan.json"], outer, entry["kind"], mode
                )
            )
    completed = (
        channel
        and producer_clean
        and receipt["source_and_packet_stable"] is True
        and receipt["transport"].get("source_stable") is True
        and receipt["transport"].get("local_exchange_and_process_complete") is True
        and len(sessions) == wanted
        and all(v["status"] == "completed" for v in sessions)
    )
    if "route.json" in output_files:
        child = json.loads(
            output_files["route.json"], object_pairs_hook=route.storage.unique_object
        )
        route.storage.fields(
            child,
            "schema kind pid ppid startup_environment_keys post_clear_environment_keys bootstrap "
            "startup_confinement_qualified frame_sha256 ack_sha256 exchange_status worker case_id "
            "slot native_acceptance native_execution_authorized",
        )
        route.need(
            child["schema"] == "opent1d.lt1-native-route-child/2"
            and all(child[k] == entry[k] for k in ("kind", "case_id", "slot"))
            and child["startup_confinement_qualified"] is False
            and child["native_acceptance"] is False
            and child["native_execution_authorized"] is False
            and child["frame_sha256"] == route.storage.digest(frame)
            and child["ack_sha256"] == route.storage.digest(ack),
            "child channel/origin binding",
        )
        if child["worker"] is not None:
            route.need(child["exchange_status"] == "acknowledged", "worker without child ACK")
            _worker_report(child["worker"], entry, receipt["packet_sha256"], sessions, output_files)
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
            and child["exchange_status"] == "acknowledged"
            and child["worker"].get("completed") is True
        )
    else:
        completed = False
    route.need(route.source_identity() == source, "reader source changed")
    route.need(
        original_packet == packet
        and original_outputs == output_files
        and original_expected == expected_identity,
        "caller packet/output/context changed during readback",
    )
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
