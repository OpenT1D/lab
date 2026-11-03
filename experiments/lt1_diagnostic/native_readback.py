"""Private exact attempt readback; never starts or admits native execution."""

import math
import os
import stat
from contextlib import ExitStack
from pathlib import Path

from experiments.gui.ownership import MAX_OWNED
from experiments.lt1_diagnostic import host_context, journal_reader, native_preflight, reader
from experiments.lt1_diagnostic import native_launcher as launch
from experiments.lt1_diagnostic.control_identity import ROOT, identity

LIMIT = 4 * 1024 * 1024
JOURNAL_LIMIT = 16 * 1024 * 1024
AUTHORITY = {
    "native_host_qualified": False,
    "native_acceptance": False,
    "setup_admitted": False,
    "native_execution_authorized": False,
    "effective_erasure_verified": False,
    "deletion_authorized": False,
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native readback refused: " + reason)


def _read(path, expected, limit):
    path = Path(path)
    need(
        path.is_absolute() and path.resolve() == path and not launch._overlap(path.parent, ROOT),
        "canonical private evidence outside checkout",
    )
    with ExitStack() as stack:
        fd = launch.storage._private_directory(path.parent)
        stack.callback(os.close, fd)
        need(stat.S_IMODE(os.fstat(fd).st_mode) == 0o700, "private evidence parent")
        info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        need(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_nlink == 1
            and stat.S_IMODE(info.st_mode) in (0o400, 0o600),
            "private ordinary evidence file",
        )
        raw = launch.storage._read_at(fd, path.name, limit)
    need(host_context.sha(expected) and reader.digest(raw) == expected, "evidence byte identity")
    return raw


def _owned_tree(owned, owner):
    """The retained first-observation graph must descend from one spawned entry."""
    by_pid = {row["pid"]: row for row in owned}
    need(owner not in by_pid, "supervisor cannot be an owned descendant")
    entries = [row["pid"] for row in owned if row["ppid"] == owner]
    need(len(entries) == 1, "exactly one owned entry required")
    connected = {owner}
    for pid in by_pid:
        chain, current = set(), pid
        while current not in connected:
            need(current in by_pid and current not in chain, "owned parent chain missing or cyclic")
            chain.add(current)
            current = by_pid[current]["ppid"]
        connected.update(chain)
    return entries[0]


def inspect_attempt(
    journal_path,
    plan_path,
    receipt_path,
    expected_journal_sha256,
    expected_plan_sha256,
    expected_receipt_sha256,
    capsule_raw,
    expected_capsule_sha256,
    packet_bytes,
):
    """Reuse the committed-prefix reader and correlate one externally pinned attempt.

    Only these three exact evidence files are read. Packet/capsule bytes and their
    expected identity come from external review. Only these private files, supplied
    packet bytes and canonical public source
    bytes are consumed. No supplied reader report or live context refresh is
    accepted; no execution registry or staged payload is opened and no worker
    is started. Repeated
    expected-byte reads bracket the existing reader; a hostile writer is outside
    the reviewed quiet-owner assumption. Files may have been relocated together.
    """
    capsule = native_preflight.decoded(capsule_raw, expected_capsule_sha256)
    launch.storage.fields(
        capsule,
        "schema kind reader_identity packet_sha256 packet_root "
        "journal_sha256 plan_sha256 receipt_sha256",
    )
    need(
        capsule["schema"] == "opent1d.lt1-native-attempt-readback/1"
        and capsule["kind"] in ("invented", "observed")
        and capsule["reader_identity"] == identity(__file__)
        and capsule["journal_sha256"] == expected_journal_sha256
        and capsule["plan_sha256"] == expected_plan_sha256
        and capsule["receipt_sha256"] == expected_receipt_sha256,
        "capsule source/attempt identity",
    )
    need(
        isinstance(packet_bytes, dict)
        and packet_bytes.keys() == launch.PACKET
        and isinstance(capsule["packet_sha256"], dict)
        and capsule["packet_sha256"].keys() == launch.PACKET,
        "closed packet",
    )
    need(
        all(isinstance(raw, bytes) and 0 < len(raw) <= LIMIT for raw in packet_bytes.values())
        and sum(map(len, packet_bytes.values())) <= 8 * LIMIT,
        "packet byte bounds",
    )
    need(
        all(
            host_context.sha(capsule["packet_sha256"][name])
            and reader.digest(raw) == capsule["packet_sha256"][name]
            for name, raw in packet_bytes.items()
        ),
        "packet byte identity",
    )
    plan_raw = _read(plan_path, expected_plan_sha256, 65536)
    receipt_raw = _read(receipt_path, expected_receipt_sha256, LIMIT)
    journal_raw = _read(journal_path, expected_journal_sha256, JOURNAL_LIMIT)
    need(packet_bytes["plan.json"] == plan_raw, "packet/reader plan bytes")
    receipt = reader.decode(receipt_raw)
    base_fields = {
        "argv",
        "status",
        "exit_code",
        "error",
        "cleanup_forced",
        "owned_processes",
        "remaining_owned_processes",
        "received_signals",
        "kind",
        *launch.AUTHORITY,
    }
    need(
        isinstance(receipt, dict)
        and base_fields <= receipt.keys() <= base_fields | {"cleanup_error", "signal_error"},
        "launcher receipt fields",
    )
    need(
        receipt["kind"] == "qualification-only"
        and all(receipt[k] is False for k in launch.AUTHORITY)
        and type(receipt["cleanup_forced"]) is bool
        and receipt["remaining_owned_processes"] == []
        and receipt.get("cleanup_error") is None
        and receipt.get("signal_error") is None,
        "launcher kind/cleanup/authority",
    )
    need(
        receipt["status"] in ("completed", "failed", "interrupted")
        and type(receipt["exit_code"]) is int,
        "started process status",
    )
    if receipt["status"] == "completed":
        need(
            receipt["exit_code"] == 0
            and receipt["error"] is None
            and receipt["received_signals"] == [],
            "inconsistent outer completion",
        )
    owned = receipt["owned_processes"]
    need(isinstance(owned, list) and 0 < len(owned) <= MAX_OWNED, "owned start identities")
    tokens = []
    for process in owned:
        need(
            isinstance(process, dict)
            and all(type(process.get(k)) is int and process[k] > 0 for k in ("pid", "ppid"))
            and isinstance(process.get("start"), str)
            and 0 < len(process["start"]) <= 512,
            "owned process start identity",
        )
        tokens.append((process["pid"], process["start"]))
    need(len({pid for pid, _ in tokens}) == len(tokens), "duplicate owned process identity")
    engine = launch.decoded(packet_bytes["grant.json"])
    integration = launch.decoded(packet_bytes["integration-grant.json"])
    host = launch.decoded(packet_bytes["integration_host_receipt.json"])
    launch.storage.fields(
        engine,
        "schema source_revision node platform arch host staging_root mode "
        "plan_sha256 setup_receipt_sha256 host_receipt_sha256 rights_receipt_sha256 "
        "security_receipt_sha256 files worker_files",
    )
    launch.storage.fields(
        integration,
        "schema engine_grant_sha256 host_receipt_sha256 output_root attempt "
        "owner_pid reader_identity implementation",
    )
    launch.storage.fields(
        host,
        "schema purpose owner_context launcher_identity roots profile_sha256 "
        "sandbox_sha256 dyld_sha256 timeout_seconds grace_seconds max_context_age_seconds "
        "materialization_request_sha256 materialization_manifest_sha256",
    )
    need(
        engine["schema"] == "opent1d.lt1-native-grant/1"
        and engine["source_revision"] == native_preflight.REVISION
        and all(engine[k] == native_preflight.RUNTIME[k] for k in ("node", "platform", "arch"))
        and engine["mode"] in ("direct", "wrapped")
        and engine["worker_files"] == launch._worker(launch.WORKER),
        "current engine identity",
    )
    files = engine["files"]
    need(
        isinstance(files, dict)
        and set(launch.ENTRIES) <= files.keys()
        and all(isinstance(k, str) and host_context.sha(v) for k, v in files.items())
        and files["runtime/bin/node"] == native_preflight.RUNTIME["executable_sha256"],
        "selected executable/inventory identity",
    )
    launch.storage._path_inventory(files)
    for name in launch.RECEIPTS:
        need(
            engine[name + "_sha256"] == reader.digest(packet_bytes[name + ".json"]),
            "same packet receipt: " + name,
        )
    need(
        integration["schema"] == "opent1d.lt1-integration-grant/1"
        and integration["engine_grant_sha256"] == reader.digest(packet_bytes["grant.json"])
        and integration["host_receipt_sha256"]
        == reader.digest(packet_bytes["integration_host_receipt.json"])
        and integration["reader_identity"] == journal_reader.identity(plan_raw)
        and integration["implementation"] == launch._worker(launch.INTEGRATION),
        "same integration/source identity",
    )
    need(
        host["schema"] == "opent1d.lt1-prestart-host/1"
        and host["purpose"] == "qualification-only"
        and host["launcher_identity"] == identity(launch.__file__),
        "launcher identity",
    )
    context = host_context.validate(host["owner_context"])
    need(
        context["status"] == "observed"
        and not context["unknown"]
        and type(integration["owner_pid"]) is int
        and integration["owner_pid"] > 1
        and integration["owner_pid"] == context["observer"]["pid"]
        and engine["host"] == context["host"]["hostname"],
        "same observed owner/context",
    )
    _owned_tree(owned, integration["owner_pid"])
    stage = native_preflight.absolute(engine["staging_root"])
    packet = native_preflight.absolute(capsule["packet_root"])
    output = native_preflight.absolute(integration["output_root"])
    launch.storage.fields(host["roots"], "stage packet output evidence")
    roots, root_tokens = [], []
    for role in ("stage", "packet", "output", "evidence"):
        binding = host["roots"][role]
        launch.storage.fields(binding, "path identity")
        path = native_preflight.absolute(binding["path"])
        roots.append(path)
        token = binding["identity"]
        need(
            isinstance(token, list)
            and len(token) == 4
            and all(type(v) is int and v >= 0 for v in token)
            and token[1] > 0
            and token[2] == context["host"]["uid"]
            and token[3] == (0o500 if role in ("stage", "packet") else 0o700),
            "reviewed root identities",
        )
        root_tokens.append(tuple(token[:2]))
    need(len(set(root_tokens)) == len(root_tokens), "aliased root identities")
    need(
        roots[:3] == [stage, packet, output]
        and all(
            not a.is_relative_to(b) and not b.is_relative_to(a)
            for i, a in enumerate(roots)
            for b in roots[i + 1 :]
        ),
        "separate command roots",
    )
    need(
        all(not r.is_relative_to(ROOT) and not ROOT.is_relative_to(r) for r in roots),
        "command roots outside checkout",
    )
    profile = launch.profile(stage, packet, output)
    need(
        host["profile_sha256"] == reader.digest(profile.encode())
        and all(
            host_context.sha(host[k])
            for k in (
                "sandbox_sha256",
                "dyld_sha256",
                "materialization_request_sha256",
                "materialization_manifest_sha256",
            )
        ),
        "host mechanism identities",
    )
    for key, maximum in (
        ("timeout_seconds", 3600),
        ("grace_seconds", 60),
        ("max_context_age_seconds", 3600),
    ):
        value = host[key]
        need(
            type(value) in (int, float)
            and math.isfinite(value)
            and 0 <= value <= maximum
            and (key == "grace_seconds" or value > 0),
            "host clock",
        )
    expected_argv = [
        str(launch.SANDBOX),
        "-p",
        profile,
        str(stage / "runtime/bin/node"),
        str(launch.HERE / "integration_worker.mjs"),
        str(stage),
        str(packet),
        str(output),
    ]
    need(receipt["argv"] == expected_argv, "exact fixed launcher command")
    header = reader.decode(journal_raw.split(b"\n", 1)[0])
    need(
        isinstance(header, dict)
        and header.get("kind")
        == ("invented" if capsule["kind"] == "invented" else "native-unadmitted")
        and header.get("mode") == engine["mode"]
        and header.get("owner_pid") == integration["owner_pid"]
        and header.get("attempt") == integration["attempt"]
        and header.get("output_root") == str(output)
        and header.get("engine_grant_sha256") == integration["engine_grant_sha256"]
        and header.get("integration_sha256")
        == reader.digest(packet_bytes["integration-grant.json"]),
        "journal/grant/owner attempt binding",
    )
    result = journal_reader.inspect(
        journal_path, plan_path, receipt_path, expected_journal_sha256, expected_receipt_sha256
    )
    for path, expected, limit in (
        (plan_path, expected_plan_sha256, 65536),
        (receipt_path, expected_receipt_sha256, LIMIT),
        (journal_path, expected_journal_sha256, JOURNAL_LIMIT),
    ):
        _read(path, expected, limit)
    return {
        "schema": "opent1d.lt1-native-attempt-readback-result/1",
        "kind": capsule["kind"],
        "structurally_correlated": True,
        "capsule_sha256": expected_capsule_sha256,
        "journal_result": result,
        "native_cases": {
            name: {"state": "not_run", "reason": "case-specific-native-instrumentation-absent"}
            for name in native_preflight.NATIVE_CASES
        },
        "external_observations_independently_proved": False,
        "live_owner_revalidated": False,
        **AUTHORITY,
    }
