"""Candidate-specific static host plan; never intake staging or start a runtime."""

import copy
import os
from pathlib import Path, PurePosixPath

from experiments.lt1_diagnostic import native_launcher as launcher
from experiments.lt1_diagnostic import native_preflight as preflight
from experiments.lt1_diagnostic.control_identity import ROOT, identity

AUTHORITY = {
    **preflight.AUTHORITY,
    "native_acceptance": False,
    "native_execution_authorized": False,
    "effective_erasure_verified": False,
}
ROOTS = ("staging", "packet", "output", "evidence")
REQUIREMENTS = {
    "native_bootstrap": "Actual executable/start identity, initialization and trusted bootstrap.",
    "native_modules": "Actual TypeScript registration, computed imports, cache and source closure.",
    "native_addons": "Actual addon policy with matched allow/deny controls; no assumed flags.",
    "native_process": "Owned children/grandchildren, stops, coordinator loss, unrelated control.",
    "native_file_network": "Native parent/child read/write/network denials and successful twins.",
    "native_host_mechanism": "Current OS/profile/loader/IPC boundaries and broad-rule disposition.",
}
LIMITATIONS = (
    "whole-bootstrap-and-build-to-binary-correspondence-unqualified",
    "broad-system-library-read-and-map-rules",
    "global-file-metadata-and-mach-lookup-rules",
    "staging-and-packet-subtree-reads-unqualified",
    "module-addon-and-relevant-IPC-behavior-unrun",
    "check-to-exec-race-and-hostile-owner-isolation-unqualified",
    "hard-memory-and-resource-limits-unqualified",
    "lexical-roots-only-no-storage-ACL-alias-or-restore-qualification",
)


def need(ok, reason):
    if not ok:
        raise ValueError("LT1 native host plan refused: " + reason)


def source_identity():
    """Bind repository controls and explicit native sources, not dynamic bootstrap."""
    need(os.name == "posix", "POSIX trusted source reader required")
    result = identity(__file__)
    for name in (
        *launcher.WORKER,
        *launcher.INTEGRATION,
        "native-admissions.json",
        "setup-request-admissions.json",
        "removal-admissions.json",
    ):
        path = Path(os.path.normpath(launcher.HERE / name))
        result["implementation"][path.relative_to(ROOT).as_posix()] = preflight.digest(
            launcher._source(path)
        )
    reader = launcher.journal_reader.identity(b"")
    result["implementation"].update(reader["implementation"])
    result["implementation"].update(reader["protocol"]["implementation_sha256"])
    return result


def _roots(roots):
    preflight.fields(roots, " ".join(ROOTS))
    parsed = {key: preflight.absolute(value) for key, value in roots.items()}
    values = list(parsed.values())
    checkout = PurePosixPath(str(ROOT))
    need(
        all(
            not a.is_relative_to(b) and not b.is_relative_to(a)
            for index, a in enumerate(values)
            for b in values[index + 1 :]
        )
        and all(not p.is_relative_to(checkout) and not checkout.is_relative_to(p) for p in values),
        "separate lexical roots outside checkout",
    )
    return parsed


def prepare(roots, *, expected_identity):
    """Return a private review plan, not a grant, host receipt or launch request.

    Repository controls and trusted Python identity are read. Private roots are lexical strings;
    their existence, storage ownership and recovery scope are not inspected.
    Expected source identity must come from independently trusted review.
    """
    source = source_identity()
    need(source == expected_identity, "expected planner source")
    roots = _roots(copy.deepcopy(roots))
    policy = launcher.profile(*(roots[key] for key in ("staging", "packet", "output")))
    need(source_identity() == source, "source changed while deriving profile")
    node = str(roots["staging"] / "runtime/bin/node")
    return {
        "schema": "opent1d.lt1-native-host-plan/1",
        "kind": "native-preparation",
        "status": "unqualified-plan-for-independent-review",
        "candidate": preflight.CANDIDATE,
        "runtime": copy.deepcopy(preflight.RUNTIME),
        "source_identity": source,
        "roots": {key: str(value) for key, value in roots.items()},
        "profile": policy,
        "profile_sha256": preflight.digest(policy.encode()),
        "profile_origin": "unchanged-provisional-native-launcher",
        "argv": [
            str(launcher.SANDBOX),
            "-p",
            policy,
            node,
            str(ROOT / preflight.ENTRY),
            *(str(roots[key]) for key in ("staging", "packet", "output")),
        ],
        "cwd": str(ROOT),
        "passed_environment": dict(preflight.host_context.ENVIRONMENT),
        "stdin": "DEVNULL",
        "close_fds": True,
        "exec_argv": [],
        "log_path": str(roots["evidence"] / "launch.log"),
        "deadline_and_grace": "require-separately-reviewed-exact-grant",
        "native_entry_channels": "not-wired-by-existing-native-launcher-or-worker",
        "tooling_host_evidence_transferred": False,
        "cases": {
            name: {"state": "not_run", "origin": "none", "required": REQUIREMENTS[name]}
            for name in preflight.NATIVE_CASES
        },
        "C15-C18": "not_run",
        "required_separate_decisions": [
            "exact-runtime-security-and-restricted-use-rights",
            "harness-and-reader-review",
            "setup-request-and-verified-actual-setup-receipt",
            "candidate-specific-host-and-bounded-execution-admission",
            "complete-private-copy-restore-and-retention-scope",
        ],
        "limitations": list(LIMITATIONS),
        "private_root_intake_performed": False,
        "host_capture_performed": False,
        "stage_materialized": False,
        "saved_outputs_require_private_accounting": True,
        **AUTHORITY,
    }
