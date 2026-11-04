"""Versioned entry preparation; no native launcher, private intake or authority.

Raw grants are trusted-code API arguments, never process arguments. Existing
engine/reader evidence cannot qualify this new entry/profile. Fixture validation
is explicitly invented and cannot select a native continuation.
"""

import copy
import json
import re

from experiments.lt1_diagnostic import native_host_plan as base
from experiments.lt1_diagnostic.control_identity import ROOT, identity

HERE = ROOT / "experiments/lt1_diagnostic"
ENTRY = "experiments/lt1_diagnostic/native_entry.mjs"
SOURCE_KEYS = "experiments/lt1_diagnostic/native_entry_sources.json"
FIXTURE = "tests/lt1_native_entry_fixture.mjs"
JS = (
    "native_entry.mjs",
    "entry_channels.mjs",
    "entry_handoff.mjs",
    "entry_observation.mjs",
    "integration_worker.mjs",
)
PACKET = (
    "grant.json",
    "integration-grant.json",
    "integration_host_receipt.json",
    "plan.json",
    "setup_receipt.json",
    "host_receipt.json",
    "rights_receipt.json",
    "security_receipt.json",
)
ENTRY_FIELDS = (
    "schema kind observation_sha256 engine_sha256 integration_sha256 setup_sha256 "
    "entry_sources roots profile_sha256 owner_pid owner_start attempt nonce_sha256 "
    "process_argv new_host_qualification_required"
)
AUTHORITY = {
    **base.AUTHORITY,
    "phase_verified": False,
    "endpoint_identity_verified": False,
}
LIMIT = 1024 * 1024
AUTHORITY_SOURCES = {
    "experiments/lt1_diagnostic/" + name
    for name in (
        "native-admissions.json",
        "setup-request-admissions.json",
        "removal-admissions.json",
    )
}


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native entry refused: " + reason)


def encoded(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def source_identity():
    need(base.os.name == "posix", "POSIX trusted source reader required")
    result = identity(__file__)
    result["implementation"].update(base.source_identity()["implementation"])
    for name in JS:
        result["implementation"]["experiments/lt1_diagnostic/" + name] = base.preflight.digest(
            base.launcher._source(HERE / name)
        )
    raw = base.launcher._source(ROOT / SOURCE_KEYS)
    result["implementation"][SOURCE_KEYS] = base.preflight.digest(raw)
    manifest = json.loads(raw, object_pairs_hook=base.preflight.unique_object)
    base.preflight.fields(manifest, "schema sources")
    need(
        manifest["schema"] == "opent1d.lt1-native-entry-source-keys/1"
        and manifest["sources"] == sorted(result["implementation"]),
        "versioned complete source-key manifest",
    )
    return result


def grant_sources(source):
    """Pin all code; mutable authority bytes are a separate post-publication audit.

    A grant cannot hash the registry which must itself contain that grant's hash.
    Full audit identity still binds all three authority files independently.
    """
    return {
        name: digest
        for name, digest in source["implementation"].items()
        if name not in AUTHORITY_SOURCES
    }


def profile(roots, source):
    """New unqualified profile version; old profile and receipts are untouched."""
    parsed = base._roots(copy.deepcopy(roots))
    original = base.launcher.profile(*(parsed[k] for k in ("staging", "packet", "output")))
    paths = [str(ROOT / name) for name in sorted(source["implementation"])]
    return (
        original
        + "(allow file-read* "
        + " ".join("(literal " + json.dumps(name) + ")" for name in paths)
        + ")\n"
    )


def _bytes(raw):
    need(isinstance(raw, bytes) and 0 < len(raw) <= LIMIT, "bounded raw grant")
    return raw


def _decoded(raw):
    value = json.loads(_bytes(raw), object_pairs_hook=base.preflight.unique_object)
    need(encoded(value) == raw, "canonical grant bytes")
    return value


def _registry(value):
    base.preflight.fields(value, "schema setup execution")
    need(value["schema"] == "opent1d.lt1-native-admissions/1", "canonical authority schema")
    for key in ("setup", "execution"):
        rows = value[key]
        need(
            isinstance(rows, list)
            and len(rows) <= 4096
            and all(base.preflight.host_context.sha(v) for v in rows)
            and len(set(rows)) == len(rows),
            "bounded exact authority",
        )
    return value


def _admit(entry_raw, observation_raw, registry, *, invented):
    """Exact opaque/declaration membership before caller packet/context intake."""
    for raw in (entry_raw, observation_raw):
        _bytes(raw)
        need(
            base.preflight.digest(raw) in registry["execution"],
            "exact entry/observation membership",
        )
    declared = _decoded(entry_raw)
    base.preflight.fields(declared, ENTRY_FIELDS)
    need(
        declared["schema"] == "opent1d.lt1-native-entry-continuation-grant/1"
        and declared["kind"] == ("invented" if invented else "native-preparation")
        and declared["new_host_qualification_required"] is True,
        "versioned entry purpose",
    )
    need(
        all(
            base.preflight.host_context.sha(declared[key])
            for key in ("observation_sha256", "engine_sha256", "integration_sha256", "setup_sha256")
        )
        and declared["observation_sha256"] == base.preflight.digest(observation_raw)
        and declared["engine_sha256"] in registry["execution"]
        and declared["integration_sha256"] in registry["execution"]
        and declared["setup_sha256"] in registry["setup"],
        "exact declared engine/integration/setup membership",
    )
    return declared


def _validate(
    entry_raw, observation_raw, packet, expected_identity, registry, *, invented, authority_sha=None
):
    entry = _admit(entry_raw, observation_raw, registry, invented=invented)
    observation = _decoded(observation_raw)
    base.preflight.fields(packet, " ".join(PACKET))
    need(
        all(isinstance(raw, bytes) and 0 < len(raw) <= 4 * LIMIT for raw in packet.values())
        and sum(map(len, packet.values())) <= 32 * LIMIT,
        "bounded packet buffers",
    )
    digests = {name: base.preflight.digest(raw) for name, raw in packet.items()}
    need(
        digests["grant.json"] in registry["execution"]
        and digests["integration-grant.json"] in registry["execution"]
        and digests["setup_receipt.json"] in registry["setup"],
        "exact engine/integration/setup memberships",
    )
    need(
        observation.get("packet_sha256") == digests
        and entry["engine_sha256"] == digests["grant.json"]
        and entry["integration_sha256"] == digests["integration-grant.json"]
        and entry["setup_sha256"] == digests["setup_receipt.json"],
        "complete actual packet binding before context intake",
    )
    source = source_identity()
    need(source == expected_identity, "expected entry source")
    if authority_sha is not None:
        need(
            source["implementation"]["experiments/lt1_diagnostic/native-admissions.json"]
            == authority_sha,
            "canonical authority snapshot changed",
        )
    base.preflight.fields(entry, ENTRY_FIELDS)
    need(
        entry["schema"] == "opent1d.lt1-native-entry-continuation-grant/1"
        and entry["kind"] == ("invented" if invented else "native-preparation")
        and entry["new_host_qualification_required"] is True,
        "versioned entry purpose",
    )
    roots = base._roots(entry["roots"])
    need(entry["entry_sources"] == grant_sources(source), "complete current entry/base code")
    policy = profile(entry["roots"], source)
    need(
        entry["profile_sha256"] == base.preflight.digest(policy.encode())
        and entry["observation_sha256"] == base.preflight.digest(observation_raw)
        and entry["engine_sha256"] == digests["grant.json"]
        and entry["integration_sha256"] == digests["integration-grant.json"]
        and entry["setup_sha256"] == digests["setup_receipt.json"],
        "entry grant bindings",
    )
    need(
        observation.get("schema") == "opent1d.lt1-entry-observation-grant/1"
        and observation.get("packet_sha256") == digests
        and observation.get("profile_sha256") == entry["profile_sha256"]
        and observation.get("producer_sha256")
        == source["implementation"]["experiments/lt1_diagnostic/entry_observation.mjs"]
        and all(
            observation.get(key) == entry[key]
            for key in ("owner_pid", "owner_start", "attempt", "nonce_sha256", "process_argv")
        ),
        "observation entry/owner/nonce binding",
    )
    need(
        type(entry["owner_pid"]) is int
        and 1 < entry["owner_pid"] <= 2**53 - 1
        and isinstance(entry["owner_start"], str)
        and 0 < len(entry["owner_start"]) <= 512
        and base.preflight.host_context.sha(entry["nonce_sha256"]),
        "owner/nonce types",
    )
    need(
        isinstance(entry["attempt"], str)
        and re.fullmatch("[a-z0-9][a-z0-9-]{0,63}", entry["attempt"]),
        "fixed attempt",
    )
    argv = entry["process_argv"]
    need(
        isinstance(argv, list)
        and 2 <= len(argv) <= 16
        and all(isinstance(v, str) and 0 < len(v) <= 1024 and "\0" not in v for v in argv),
        "fixed process argument bound",
    )
    if invented:
        need(argv[1] == str(ROOT / FIXTURE), "fixed invented entry")
    else:
        need(
            argv
            == [str(roots["staging"] / "runtime/bin/node"), str(ROOT / ENTRY)]
            + [str(roots[k]) for k in ("staging", "packet", "output")]
            and observation.get("runtime")
            == {
                key: base.preflight.RUNTIME[key]
                for key in ("node", "platform", "arch", "executable_sha256")
            },
            "fixed selected candidate and future entry convention",
        )
    host = _decoded(packet["integration_host_receipt.json"])
    need(
        host.get("schema") == "opent1d.lt1-native-entry-host/1"
        and host.get("kind") == ("invented" if invented else "observed")
        and host.get("purpose") == "qualification-only"
        and host.get("profile_sha256") == entry["profile_sha256"]
        and host.get("entry_sources") == entry["entry_sources"]
        and host.get("owner_context", {}).get("observer")
        == {"pid": entry["owner_pid"], "start": entry["owner_start"]},
        "new entry host namespace; old receipt cannot qualify it",
    )
    integration = _decoded(packet["integration-grant.json"])
    engine = _decoded(packet["grant.json"])
    need(
        integration.get("engine_grant_sha256") == digests["grant.json"]
        and integration.get("host_receipt_sha256") == digests["integration_host_receipt.json"]
        and integration.get("owner_pid") == entry["owner_pid"]
        and integration.get("attempt") == entry["attempt"]
        and integration.get("reader_identity") == observation.get("reader_identity")
        and engine.get("setup_receipt_sha256") == digests["setup_receipt.json"],
        "underlying packet bindings; semantic native verification remains separate",
    )
    need(source_identity() == source, "entry preparation source changed")
    return {
        "schema": "opent1d.lt1-native-entry-preparation/1",
        "kind": entry["kind"],
        "status": "unqualified-entry-continuation-preparation",
        "entry_sha256": base.preflight.digest(entry_raw),
        "observation_sha256": base.preflight.digest(observation_raw),
        "source_identity": source,
        "profile": policy,
        "profile_sha256": entry["profile_sha256"],
        "process_argv": list(argv),
        "fixed_args": [str(roots[k]) for k in ("staging", "packet", "output")],
        "expected_context": {
            "source_identity": copy.deepcopy(source),
            "profile_sha256": entry["profile_sha256"],
            "process_argv": list(argv),
        },
        "native_cli_wired": False,
        "new_native_launcher": False,
        "old_host_receipt_qualifies_new_entry": False,
        "new_host_qualification_required": True,
        "private_path_intake_performed": False,
        "saved_outputs_require_private_accounting": True,
        "native_cases": {key: "not_run" for key in base.preflight.NATIVE_CASES},
        "C15-C18": "not_run",
        **AUTHORITY,
    }


def prepare(entry_raw, observation_raw, packet_buffers, *, expected_identity):
    """Refuse closed canonical authority before examining caller packet or paths."""
    authority_raw = (HERE / "native-admissions.json").read_bytes()
    registry = _registry(json.loads(authority_raw))
    need(registry["setup"] and registry["execution"], "no reviewed entry continuation grant")
    return _validate(
        entry_raw,
        observation_raw,
        packet_buffers,
        expected_identity,
        registry,
        invented=False,
        authority_sha=base.preflight.digest(authority_raw),
    )


def _prepare_invented(entry_raw, observation_raw, packet_buffers, *, expected_identity):
    """Trusted fresh fixture only; no alternate native authority or runtime route."""
    _bytes(entry_raw)
    _bytes(observation_raw)
    base.preflight.fields(packet_buffers, " ".join(PACKET))
    for raw in packet_buffers.values():
        _bytes(raw)
    registry = {
        "schema": "opent1d.lt1-native-admissions/1",
        "setup": [base.preflight.digest(packet_buffers["setup_receipt.json"])],
        "execution": list(
            dict.fromkeys(
                base.preflight.digest(raw)
                for raw in (
                    entry_raw,
                    observation_raw,
                    packet_buffers["grant.json"],
                    packet_buffers["integration-grant.json"],
                )
            )
        ),
    }
    return _validate(
        entry_raw, observation_raw, packet_buffers, expected_identity, registry, invented=True
    )
