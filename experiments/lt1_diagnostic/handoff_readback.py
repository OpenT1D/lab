"""Strict historical frame/ACK consistency; no endpoint or native qualification."""

import json

from experiments.lt1_diagnostic import entry_readback as entry
from experiments.lt1_diagnostic import reader
from experiments.lt1_diagnostic.control_identity import ROOT, identity

ACK_MAGIC = b"OPENT1D-LT1-ACK-1\n"
ACK_LIMIT = 1024
JS_SOURCES = ("entry_handoff.mjs", "entry_observation.mjs")


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 handoff readback refused: " + reason)


def source_identity():
    value = identity(__file__)
    for name in JS_SOURCES:
        relative = "experiments/lt1_diagnostic/" + name
        value["implementation"][relative] = reader.digest((ROOT / relative).read_bytes())
    return value


def inspect_exchange(ack_raw, expected_ack_sha256, *, expected_reader_identity, **frame_inputs):
    """Require external expected source/frame/parent/receipt identities and bytes.

    Repeated historical reading is permitted. A matching ACK does not prove who
    received the frame, that streams were confined, or that any model was run.
    """
    current = source_identity()
    need(expected_reader_identity == current, "current handoff reader identity")
    need(
        isinstance(ack_raw, bytes)
        and 0 < len(ack_raw) <= ACK_LIMIT
        and reader.digest(ack_raw) == expected_ack_sha256,
        "bounded expected acknowledgment",
    )
    result = entry.inspect_frame(**frame_inputs)
    raw = frame_inputs["raw"]
    frame = reader.decode(raw.split(b"\n")[1])
    encoded = json.dumps(frame, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    need(raw == entry.MAGIC + encoded + b"\n", "canonical transport frame")
    expected = {
        "schema": "opent1d.lt1-entry-ack/1",
        "kind": frame["kind"],
        "frame_sha256": reader.digest(raw),
        "grant_sha256": frame["grant_sha256"],
        "attempt": frame["attempt"],
        "nonce_sha256": frame["nonce_sha256"],
    }
    need(
        ack_raw
        == ACK_MAGIC
        + json.dumps(expected, separators=(",", ":"), allow_nan=False).encode()
        + b"\n",
        "exact canonical acknowledgment",
    )
    need(source_identity() == current, "handoff reader source changed")
    return {
        **result,
        "schema": "opent1d.lt1-entry-handoff-readback/1",
        "ack_sha256": expected_ack_sha256,
        "reader_identity": current,
        "ack_binding_consistent": True,
        "transport_execution_independently_proved": False,
        "endpoint_identity_verified": False,
        "endpoint_close_verified": False,
        "handoff_timing_verified": False,
        "new_authority_granted": False,
        "effective_erasure_verified": False,
    }
