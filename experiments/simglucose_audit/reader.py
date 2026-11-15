"""Engine-free invented readback: fixed trusted oracle, never supplied code."""

from .contract import decode, digest, encode, require, source_identity, validate_config
from .reference import expected_fixture


def inspect_fixture(report_raw, expected_report_sha256, config_raw, expected_config_sha256):
    require(
        digest(report_raw) == expected_report_sha256
        and digest(config_raw) == expected_config_sha256,
        "external-byte-pins",
    )
    config = validate_config(decode(config_raw))
    report = decode(report_raw)
    require(type(report) is dict and report.get("kind") == "invented", "fixture-only")
    identity = source_identity()
    require(report.get("source_identity") == identity, "current-trusted-reader-source")
    expected = expected_fixture(config, identity, digest(config_raw))
    require(encode(report) == encode(expected), "fixture-oracle-mismatch")
    require(source_identity() == identity, "source-changed-during-readback")
    return {
        "kind": "invented",
        "status": report["status"],
        "completed_intervals": len(report["rows"]),
        "observation_points": len(report["observations"]),
        "delivered_u_exact": report["delivered_u_exact"],
        "native_execution_authorized": False,
        "native_acceptance": False,
        "new_authority_granted": False,
        "native_execution_deferred": True,
    }
