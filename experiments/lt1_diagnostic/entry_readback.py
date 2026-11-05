"""One bounded process-observation frame, never native bootstrap qualification."""

import json
import re

from experiments.lt1_diagnostic import host_context, native_preflight, native_readback, reader
from experiments.lt1_diagnostic import native_launcher as launch
from experiments.lt1_diagnostic.control_identity import ROOT, identity
from experiments.lt1_diagnostic.retention import fields, identifier

MAGIC = b"OPENT1D-LT1-ENTRY-1\n"
LIMIT = 64 * 1024
PRODUCER = ROOT / "experiments/lt1_diagnostic/entry_observation.mjs"
AUTHORITY = dict(native_readback.AUTHORITY)


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 entry readback refused: " + reason)


def encode_grant(value):
    """Compact UTF-8 observation-grant bytes; existing packet bytes are opaque."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def inspect_frame(
    raw,
    expected_sha256,
    grant_raw,
    expected_grant_sha256,
    packet_bytes,
    parent_raw,
    expected_parent_sha256,
    receipt_raw,
    expected_receipt_sha256,
    *,
    as_of,
):
    """Correlate externally pinned evidence; never opens a private path or queries OS.

    Parent bytes are an independent external input. Parsing does not prove their
    truth, a live entry, an actual bootstrap phase, stdio or confinement.
    """
    need(
        isinstance(raw, bytes)
        and 0 < len(raw) <= LIMIT
        and host_context.sha(expected_sha256)
        and reader.digest(raw) == expected_sha256,
        "bounded expected frame",
    )
    need(raw.startswith(MAGIC) and raw.endswith(b"\n"), "complete frame boundary")
    chunks = raw.split(b"\n")
    need(len(chunks) == 3 and chunks[0] == MAGIC[:-1] and chunks[-1] == b"", "single frame EOF")
    frame = reader.decode(chunks[1])
    fields(
        frame,
        "schema kind phase observed_at grant_sha256 attempt nonce_sha256 facts "
        "native_host_qualified native_acceptance setup_admitted native_execution_authorized",
    )
    need(
        frame["schema"] == "opent1d.lt1-entry-observation/1"
        and frame["kind"] in ("invented", "observed")
        and frame["phase"] == "unqualified-current-process-observation"
        and all(
            frame[k] is False
            for k in (
                "native_host_qualified",
                "native_acceptance",
                "setup_admitted",
                "native_execution_authorized",
            )
        ),
        "frame schema/origin/authority",
    )
    grant = native_preflight.decoded(grant_raw, expected_grant_sha256)
    need(encode_grant(grant) == grant_raw, "canonical observation grant bytes")
    fields(
        grant,
        "schema packet_sha256 runtime entry_executable owner_pid owner_start "
        "attempt nonce_sha256 profile_sha256 producer_sha256 reader_identity process_argv",
    )
    fields(grant["runtime"], "node platform arch executable_sha256")
    fields(grant["packet_sha256"], " ".join(launch.PACKET))
    need(
        grant["schema"] == "opent1d.lt1-entry-observation-grant/1"
        and grant["runtime"]
        == {
            k: native_preflight.RUNTIME[k]
            for k in ("node", "platform", "arch", "executable_sha256")
        }
        and grant["reader_identity"] == identity(__file__)
        and grant["producer_sha256"] == reader.digest(PRODUCER.read_bytes())
        and host_context.sha(grant["nonce_sha256"])
        and host_context.sha(grant["profile_sha256"])
        and frame["grant_sha256"] == expected_grant_sha256
        and frame["nonce_sha256"] == grant["nonce_sha256"]
        and frame["attempt"] == grant["attempt"],
        "same source/grant/runtime/nonce",
    )
    identifier(grant["attempt"])
    need(
        isinstance(grant["process_argv"], list)
        and 2 <= len(grant["process_argv"]) <= 16
        and grant["process_argv"][0] == grant["entry_executable"]
        and all(
            isinstance(v, str) and 0 < len(v) <= 1024 and "\0" not in v
            for v in grant["process_argv"]
        ),
        "fixed observed argv",
    )
    need(
        isinstance(packet_bytes, dict)
        and packet_bytes.keys() == launch.PACKET
        and all(
            isinstance(v, bytes) and 0 < len(v) <= 4 * 1024 * 1024 for v in packet_bytes.values()
        )
        and sum(map(len, packet_bytes.values())) <= 32 * 1024 * 1024
        and all(
            host_context.sha(grant["packet_sha256"][k])
            and reader.digest(v) == grant["packet_sha256"][k]
            for k, v in packet_bytes.items()
        ),
        "packet byte binding",
    )
    engine = launch.decoded(packet_bytes["grant.json"])
    integration = launch.decoded(packet_bytes["integration-grant.json"])
    host = launch.decoded(packet_bytes["integration_host_receipt.json"])
    need(
        engine.get("schema") == "opent1d.lt1-native-grant/1"
        and integration.get("schema") == "opent1d.lt1-integration-grant/1"
        and integration.get("engine_grant_sha256") == grant["packet_sha256"]["grant.json"]
        and engine.get("setup_receipt_sha256") == grant["packet_sha256"]["setup_receipt.json"]
        and integration.get("host_receipt_sha256")
        == grant["packet_sha256"]["integration_host_receipt.json"]
        and integration.get("owner_pid") == grant["owner_pid"]
        and integration.get("attempt") == grant["attempt"]
        and host.get("profile_sha256") == grant["profile_sha256"],
        "packet metadata binding",
    )
    context = host_context.validate(host["owner_context"])
    need(
        context["status"] == "observed"
        and not context["unknown"]
        and type(grant["owner_pid"]) is int
        and 1 < grant["owner_pid"] <= 2**53 - 1
        and context["observer"]["pid"] == grant["owner_pid"]
        and context["observer"]["start"] == grant["owner_start"],
        "parent context",
    )
    expected_path = native_preflight.absolute(engine["staging_root"]) / "runtime/bin/node"
    need(
        grant["entry_executable"] == str(expected_path)
        and engine["files"]["runtime/bin/node"] == grant["runtime"]["executable_sha256"]
        and all(engine[k] == grant["runtime"][k] for k in ("node", "platform", "arch")),
        "selected entry executable",
    )
    facts = frame["facts"]
    fields(
        facts,
        "pid ppid exec_path node platform arch exec_argv environment_keys environment "
        "executable_sha256 producer_sha256 stdio process_argv",
    )
    fields(facts["environment"], "LANG LC_ALL PATH")
    need(
        type(facts["pid"]) is int
        and 1 < facts["pid"] <= 2**53 - 1
        and facts["pid"] != grant["owner_pid"]
        and type(facts["ppid"]) is int
        and facts["ppid"] == grant["owner_pid"]
        and facts["exec_path"] == grant["entry_executable"]
        and all(
            facts[k] == grant["runtime"][k]
            for k in ("node", "platform", "arch", "executable_sha256")
        )
        and facts["producer_sha256"] == grant["producer_sha256"]
        and facts["process_argv"] == grant["process_argv"]
        and facts["exec_argv"] == []
        and facts["environment_keys"] == sorted(host_context.ENVIRONMENT)
        and facts["environment"] == host_context.ENVIRONMENT
        and facts["stdio"] == "unobserved",
        "entry facts",
    )
    parent = native_preflight.decoded(parent_raw, expected_parent_sha256)
    fields(
        parent,
        "schema kind grant_sha256 frame_sha256 attempt nonce_sha256 profile_sha256 "
        "owner entry observed_from observed_to",
    )
    fields(parent["owner"], "pid start")
    fields(parent["entry"], "pid ppid start executable_path executable_sha256")
    need(
        parent["schema"] == "opent1d.lt1-entry-parent-observation/1"
        and type(parent["owner"]["pid"]) is int
        and type(parent["entry"]["pid"]) is int
        and type(parent["entry"]["ppid"]) is int
        and parent["kind"] == frame["kind"]
        and parent["grant_sha256"] == expected_grant_sha256
        and parent["frame_sha256"] == expected_sha256
        and all(parent[k] == grant[k] for k in ("attempt", "nonce_sha256", "profile_sha256"))
        and parent["owner"] == {"pid": grant["owner_pid"], "start": grant["owner_start"]}
        and parent["entry"]["pid"] == facts["pid"]
        and parent["entry"]["ppid"] == facts["ppid"]
        and parent["entry"]["executable_path"] == facts["exec_path"]
        and parent["entry"]["executable_sha256"] == facts["executable_sha256"]
        and isinstance(parent["entry"]["start"], str)
        and 0 < len(parent["entry"]["start"]) <= 512,
        "independent parent/entry binding",
    )
    at = frame["observed_at"]
    need(
        isinstance(at, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", at),
        "canonical UTC frame time",
    )
    need(
        host_context.stamp(at).isoformat(timespec="milliseconds").replace("+00:00", "Z") == at,
        "canonical UTC frame time",
    )
    now = host_context.stamp(as_of)
    need(
        host_context.stamp(parent["observed_from"])
        <= host_context.stamp(parent["observed_to"])
        <= now
        and host_context.stamp(frame["observed_at"]) <= now,
        "observation clock",
    )
    receipt = native_preflight.decoded(receipt_raw, expected_receipt_sha256)
    argv = receipt.get("argv")
    need(
        isinstance(argv, list)
        and len(argv) == len(grant["process_argv"]) + 3
        and argv[:2] == [str(launch.SANDBOX), "-p"]
        and isinstance(argv[2], str)
        and reader.digest(argv[2].encode()) == grant["profile_sha256"]
        and argv[3:] == grant["process_argv"],
        "same parent launcher argv/profile",
    )
    owned = receipt.get("owned_processes")
    need(
        isinstance(owned, list)
        and 0 < len(owned) <= native_readback.MAX_OWNED
        and all(
            isinstance(p, dict)
            and all(type(p.get(k)) is int and p[k] > 0 for k in ("pid", "ppid"))
            and isinstance(p.get("start"), str)
            and 0 < len(p["start"]) <= 512
            for p in owned
        )
        and len({p["pid"] for p in owned}) == len(owned),
        "owned process records",
    )
    entry_pid = native_readback._owned_tree(owned, grant["owner_pid"])
    entry = next(p for p in owned if p["pid"] == entry_pid)
    need(
        entry_pid == facts["pid"]
        and entry["start"] == parent["entry"]["start"]
        and receipt.get("kind") == "qualification-only"
        and all(receipt.get(k) is False for k in launch.AUTHORITY),
        "same owned entry",
    )
    return {
        "schema": "opent1d.lt1-entry-readback-result/1",
        "kind": frame["kind"],
        "entry_binding_consistent": True,
        "frame_sha256": expected_sha256,
        "parent_sha256": expected_parent_sha256,
        "entry_pid": entry_pid,
        "entry_start": entry["start"],
        "phase_verified": False,
        "attempt_completion_checked": False,
        "stdio_verified": False,
        "live_owner_revalidated": False,
        "external_observations_independently_proved": False,
        "native_cases": {name: {"state": "not_run"} for name in native_preflight.NATIVE_CASES},
        **AUTHORITY,
    }
