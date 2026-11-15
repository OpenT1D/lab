"""Invented PBS authentication controls, never a real cryptographic verifier.

The fixed semantic checks and hypothetical controls below qualify orchestration
only. Bundle-supplied booleans/certificates and a rehashed fixture receipt cannot
establish actual trust. No verifier, path, command, callback or network adapter is
selected here. Actual verification remains unconditionally closed.
"""

import re
from pathlib import Path

from .contract import AUTHORITY, decode, digest, encode, fields, require, source_identity

SCHEMA = "opent1d.pbs-auth-fixture/1"
CONTEXT_SCHEMA = "opent1d.pbs-auth-context/1"
POLICY_SCHEMA = "opent1d.pbs-auth-policy-fixture/1"
BUNDLE_SCHEMA = "opent1d.pbs-auth-bundle-fixture/1"
HEX = re.compile(r"[0-9a-f]{64}")
LIMITS = {
    "bundle_bytes": 65536,
    "policy_bytes": 32768,
    "context_bytes": 32768,
    "report_bytes": 65536,
    "invented_artifact_bytes": 262144,
}
RETENTION = {
    "not_after_utc": "2026-11-28T18:32:01Z",
    "max_days_new_facts": 30,
    "earlier_limits_win": True,
    "old_origins_reset": False,
    "unknown_old_origins_timely": False,
    "automatic_cleanup_or_extension": False,
}
TARGET = {
    "repository": "astral-sh/python-build-standalone",
    "repository_id": 162334160,
    "release_id": 424411241,
    "tag": "20261026",
    "source_commit": "fa506e0858ac9f2cc5b289c137b888a2aa24d1ee",
    "builder": "https://github.com/astral-sh/python-build-standalone/.github/workflows/release.yml@refs/heads/main",
}
ISSUER = "https://token.actions.githubusercontent.com"
RELEASE_NAME = "cpython-3.12.16+20261026-aarch64-apple-darwin-install_only.tar.gz"
BUILD_NAME = "cpython-3.12.16-aarch64-apple-darwin-install_only-20261026T1353.tar.gz"
PREDICATES = ("https://slsa.dev/provenance/v1", "https://in-toto.io/attestation/release/v0.2")
CONTROLS = (
    "signature",
    "certificate_chain",
    "identity",
    "trusted_signing_time",
    "transparency_log",
    "trust_root_freshness",
    "revocation_rotation",
    "build_source",
    "self_hosted_builder",
)
MISSING_ACTUAL = (
    "verifier_source_sha256",
    "verifier_dependency_lock_sha256",
    "crypto_backend_artifact_sha256",
    "trust_root_snapshot_sha256",
    "bootstrap_policy_sha256",
    "identity_policy_sha256",
    "time_log_policy_sha256",
    "rotation_revocation_disposition_sha256",
    "self_hosted_builder_disposition_sha256",
    "actual_authentication_receipt_sha256",
)


def verify_archive(*_args, **_kwargs):
    """Refuse before input/source/path/tool use; no qualified real verifier exists."""
    raise PermissionError("actual PBS authentication closed: verifier/trust qualification absent")


def _identity():
    return source_identity() | {"pbs_auth.py": digest(Path(__file__).read_bytes())}


def _document(raw, held, label, maximum):
    require(type(raw) is bytes and 0 < len(raw) <= maximum, label + "-byte-cap")
    require(type(held) is str and HEX.fullmatch(held) and digest(raw) == held, label + "-held-pin")
    return decode(raw)


def _context(raw, held):
    value = _document(raw, held, "context", LIMITS["context_bytes"])
    fields(
        value,
        "schema kind artifact_sha256 artifact_bytes request_sha256 reader_source_sha256",
        "context-fields",
    )
    require(value["schema"] == CONTEXT_SCHEMA and value["kind"] == "invented", "invented-context")
    for key in ("artifact_sha256", "request_sha256", "reader_source_sha256"):
        require(type(value[key]) is str and HEX.fullmatch(value[key]), "context-pin")
    require(
        type(value["artifact_bytes"]) is int
        and 0 < value["artifact_bytes"] <= LIMITS["invented_artifact_bytes"],
        "invented-artifact-size",
    )
    return value


def _policy(raw, held):
    value = _document(raw, held, "policy", LIMITS["policy_bytes"])
    fields(
        value,
        "schema kind expected_target expected_issuer expected_certificate_identity "
        "controls missing_actual_bindings retention",
        "policy-fields",
    )
    require(
        value["schema"] == POLICY_SCHEMA
        and value["kind"] == "invented"
        and encode(value["expected_target"]) == encode(TARGET)
        and value["expected_issuer"] == ISSUER
        and value["expected_certificate_identity"] == TARGET["builder"]
        and value["controls"] == list(CONTROLS)
        and encode(value["retention"]) == encode(RETENTION),
        "fixed-invented-policy",
    )
    fields(value["missing_actual_bindings"], " ".join(MISSING_ACTUAL), "actual-binding-fields")
    require(
        all(v is None for v in value["missing_actual_bindings"].values()),
        "fixture-cannot-supply-real-verifier-or-trust",
    )
    return value


def _bundle(raw, held, context):
    value = _document(raw, held, "bundle", LIMITS["bundle_bytes"])
    fields(
        value,
        "schema kind target issuer certificate_identity statements controls actual_crypto_verified",
        "bundle-fields",
    )
    require(
        value["schema"] == BUNDLE_SCHEMA
        and value["kind"] == "invented"
        and value["actual_crypto_verified"] is False,
        "invented-bundle-only",
    )
    require(
        encode(value["target"]) == encode(TARGET)
        and value["issuer"] == ISSUER
        and value["certificate_identity"] == TARGET["builder"],
        "fixed-identity-semantics",
    )
    require(
        type(value["statements"]) is list and len(value["statements"]) == 2,
        "two-distinct-statements",
    )
    for statement, predicate, name in zip(
        value["statements"], PREDICATES, (BUILD_NAME, RELEASE_NAME), strict=True
    ):
        fields(statement, "predicate subject_name subject_sha256", "statement-fields")
        require(
            statement["predicate"] == predicate
            and statement["subject_name"] == name
            and statement["subject_sha256"] == context["artifact_sha256"],
            "subject-release-provenance-semantics",
        )
    fields(value["controls"], " ".join(CONTROLS), "control-fields")
    require(all(type(v) is bool for v in value["controls"].values()), "invented-control-booleans")
    return value


def _report(
    bundle_raw, policy_raw, context_raw, held_bundle_sha256, held_policy_sha256, held_context_sha256
):
    context = _context(context_raw, held_context_sha256)
    policy = _policy(policy_raw, held_policy_sha256)
    bundle = _bundle(bundle_raw, held_bundle_sha256, context)
    failed = [name for name in CONTROLS if not bundle["controls"][name]]
    return {
        "schema": SCHEMA,
        "kind": "invented",
        "status": "fixture-controls-refused" if failed else "fixture-controls-passed",
        "semantic_correspondence": True,
        "fixture_controls_passed": not failed,
        "failed_invented_controls": failed,
        "artifact_sha256": context["artifact_sha256"],
        "artifact_bytes": context["artifact_bytes"],
        "request_sha256": context["request_sha256"],
        "reader_source_sha256": context["reader_source_sha256"],
        "context_sha256": held_context_sha256,
        "bundle_sha256": held_bundle_sha256,
        "policy_sha256": held_policy_sha256,
        "source_identity": _identity(),
        "limits": dict(LIMITS),
        "retention": dict(RETENTION),
        "actual_crypto_verified": False,
        "actual_authentication_admitted": False,
        "actual_archive_inspection_authorized": False,
        "runtime_use_authorized": False,
        "execution_ready": False,
        "missing_actual_bindings": policy["missing_actual_bindings"],
        "authority": dict(AUTHORITY),
    }


def qualify_invented_auth(
    bundle_raw,
    policy_raw,
    context_raw,
    *,
    held_bundle_sha256,
    held_policy_sha256,
    held_context_sha256,
):
    """Validate fixed invented semantics/controls, never signatures or real trust."""
    result = _report(
        bundle_raw,
        policy_raw,
        context_raw,
        held_bundle_sha256,
        held_policy_sha256,
        held_context_sha256,
    )
    require(_identity() == result["source_identity"], "auth-source-changed")
    require(len(encode(result)) <= LIMITS["report_bytes"], "auth-report-cap")
    return result


def inspect_auth_fixture_report(
    report_raw,
    held_report_sha256,
    bundle_raw,
    policy_raw,
    context_raw,
    *,
    held_bundle_sha256,
    held_policy_sha256,
    held_context_sha256,
):
    """Cold reconstruction bypasses the public producer and interprets no body."""
    report = _document(report_raw, held_report_sha256, "report", LIMITS["report_bytes"])
    expected = _report(
        bundle_raw,
        policy_raw,
        context_raw,
        held_bundle_sha256,
        held_policy_sha256,
        held_context_sha256,
    )
    require(encode(report) == encode(expected), "cold-auth-fixture-reconstruction")
    require(_identity() == expected["source_identity"], "cold-auth-source-changed")
    return {
        "kind": "invented",
        "status": "fixture-auth-metadata-reconstructed",
        "fixture_controls_passed": expected["fixture_controls_passed"],
        "artifact_sha256": expected["artifact_sha256"],
        "actual_crypto_verified": False,
        "actual_authentication_admitted": False,
        "execution_ready": False,
        "authority": dict(AUTHORITY),
    }


def invented_auth_inputs(artifact_sha256, artifact_bytes, request_sha256, reader_source_sha256):
    """Produce owned invented metadata only; no actual verifier is selected."""
    context = {
        "schema": CONTEXT_SCHEMA,
        "kind": "invented",
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": artifact_bytes,
        "request_sha256": request_sha256,
        "reader_source_sha256": reader_source_sha256,
    }
    policy = {
        "schema": POLICY_SCHEMA,
        "kind": "invented",
        "expected_target": dict(TARGET),
        "expected_issuer": ISSUER,
        "expected_certificate_identity": TARGET["builder"],
        "controls": list(CONTROLS),
        "missing_actual_bindings": dict.fromkeys(MISSING_ACTUAL),
        "retention": dict(RETENTION),
    }
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "kind": "invented",
        "target": dict(TARGET),
        "issuer": ISSUER,
        "certificate_identity": TARGET["builder"],
        "statements": [
            {"predicate": pred, "subject_name": name, "subject_sha256": artifact_sha256}
            for pred, name in zip(PREDICATES, (BUILD_NAME, RELEASE_NAME), strict=True)
        ],
        "controls": dict.fromkeys(CONTROLS, True),
        "actual_crypto_verified": False,
    }
    values = tuple(encode(v) for v in (bundle, policy, context))
    held = {
        "held_" + key + "_sha256": digest(raw)
        for key, raw in zip(("bundle", "policy", "context"), values, strict=True)
    }
    return *values, held
