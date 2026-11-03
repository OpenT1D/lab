"""Read-only logical-removal evidence, timing and authority remain separate."""

from experiments.lt1_diagnostic.retention import (
    decoded,
    fields,
    plan,
    register,
    require,
    sha,
    stamp,
)

CHANNELS = ("live", "quarantine", "snapshot", "backup")
EXCLUDED = ("physical-forensics", "privileged-memory")
METHODS = {
    "live": "namespace-readback",
    "quarantine": "namespace-readback",
    "snapshot": "recovery-inventory",
    "backup": "recovery-inventory",
}
AUTHORITY = {
    "effective_erasure_verified": False,
    "physical_sanitization_verified": False,
    "deletion_authorized": False,
    "setup_admitted": False,
    "native_execution_authorized": False,
}


def assess(
    register_raw,
    expected_register_sha256,
    policy_raw,
    expected_policy_sha256,
    scope_raw,
    expected_scope_sha256,
    observations_raw,
    expected_observations_sha256,
    as_of,
    expected_context_sha256,
    *,
    previous_raw=None,
    expected_previous_sha256=None,
):
    """Assess externally reviewed bytes; hashes do not prove observations true.

    The supported scope is ordinary application access and restore, explicitly
    excluding physical forensics and privileged memory. No path is opened and no
    approval is inferred. Kind 'invented' never becomes real-host evidence.
    """
    retention = plan(
        register_raw,
        expected_register_sha256,
        policy_raw,
        expected_policy_sha256,
        as_of,
        expected_context_sha256,
        previous_raw=previous_raw,
        expected_previous_sha256=expected_previous_sha256,
    )
    records = register(register_raw, expected_register_sha256)
    scope = decoded(scope_raw, expected_scope_sha256)
    fields(
        scope,
        "schema kind decision context_sha256 policy_sha256 channels excluded "
        "copy_channels coverage_receipts max_evidence_age_seconds",
    )
    require(
        scope["schema"] == "opent1d.lt1-logical-recovery-scope/1"
        and scope["kind"] in {"invented", "observed"}
        and scope["decision"] in {"approved", "proposed"},
        "logical scope schema",
    )
    require(
        scope["context_sha256"] == expected_context_sha256
        and scope["policy_sha256"] == expected_policy_sha256,
        "scope context or policy",
    )
    require(
        isinstance(scope["channels"], list)
        and sorted(scope["channels"]) == sorted(CHANNELS)
        and isinstance(scope["excluded"], list)
        and sorted(scope["excluded"]) == sorted(EXCLUDED),
        "supported explicit recovery scope",
    )
    require(
        type(scope["max_evidence_age_seconds"]) is int
        and 0 < scope["max_evidence_age_seconds"] <= 86400,
        "evidence age",
    )
    by_copy = {
        copy_id: (subject_id, item)
        for subject_id, subject in records["subjects"].items()
        for copy_id, item in subject["copies"].items()
    }
    require(
        isinstance(scope["copy_channels"], dict)
        and scope["copy_channels"].keys() == by_copy.keys()
        and all(channel in CHANNELS for channel in scope["copy_channels"].values()),
        "complete registered-copy scope",
    )
    fields(scope["coverage_receipts"], " ".join(CHANNELS))
    require(
        all(value is None or sha(value) for value in scope["coverage_receipts"].values()),
        "reviewed coverage identities",
    )
    observations = decoded(observations_raw, expected_observations_sha256)
    fields(observations, "schema kind register_sha256 scope_sha256 context_sha256 copies coverage")
    require(
        observations["schema"] == "opent1d.lt1-recovery-observations/1"
        and observations["kind"] == scope["kind"],
        "observation kind",
    )
    require(
        observations["register_sha256"] == expected_register_sha256
        and observations["scope_sha256"] == expected_scope_sha256
        and observations["context_sha256"] == expected_context_sha256,
        "observation input binding",
    )
    require(
        isinstance(observations["copies"], dict)
        and observations["copies"].keys() <= by_copy.keys(),
        "unexpected observed copy",
    )
    require(
        isinstance(observations["coverage"], dict)
        and observations["coverage"].keys() <= set(CHANNELS),
        "unexpected coverage channel",
    )
    now = stamp(as_of)

    def fresh(value):
        at = stamp(value)
        require(at <= now, "future observation")
        return (now - at).total_seconds() <= scope["max_evidence_age_seconds"]

    blockers, conflicts, outcomes, timing = [], [], {}, []
    if scope["decision"] != "approved":
        blockers.append("recovery-scope-not-approved")
    for key in ("all_copies_registered", "recovery_scope_reviewed", "processes_stopped"):
        if records["coverage"][key] is not True:
            blockers.append(key)
    for channel in CHANNELS:
        coverage = observations["coverage"].get(channel)
        if coverage is None:
            blockers.append("coverage-unobserved:" + channel)
            continue
        fields(coverage, "complete observed_at evidence_sha256")
        require(
            type(coverage["complete"]) is bool
            and (coverage["evidence_sha256"] is None or sha(coverage["evidence_sha256"])),
            "channel coverage schema",
        )
        if coverage["observed_at"] is None:
            require(coverage["complete"] is False, "missing coverage observation")
            current = False
        else:
            current = fresh(coverage["observed_at"])
        if (
            not current
            or coverage["complete"] is not True
            or scope["coverage_receipts"][channel] is None
            or coverage["evidence_sha256"] != scope["coverage_receipts"][channel]
        ):
            blockers.append("coverage-incomplete-or-stale:" + channel)
    for subject_id, subject in records["subjects"].items():
        if subject["hold"]:
            conflicts.append(subject_id + ":hold-conflict-no-extension")
    for copy_id, (subject_id, registered) in by_copy.items():
        observation = observations["copies"].get(copy_id)
        deadline = retention["deadlines"][subject_id]
        if observation is None:
            blockers.append("copy-unobserved:" + copy_id)
            outcomes[copy_id] = "unobserved"
            timing.append("unknown")
            continue
        fields(observation, "subject channel state method observed_at absent_since evidence_sha256")
        require(
            observation["subject"] == subject_id
            and observation["channel"] == scope["copy_channels"][copy_id]
            and observation["method"] == METHODS[observation["channel"]]
            and observation["state"] in {"absent", "present", "unknown"}
            and sha(observation["evidence_sha256"]),
            "copy observation schema",
        )
        current = fresh(observation["observed_at"])
        if observation["absent_since"] is not None:
            require(
                observation["state"] == "absent"
                and stamp(observation["absent_since"]) <= stamp(observation["observed_at"]),
                "absence timing",
            )
        consistent = (registered["state"] == "absence-observed") == (
            observation["state"] == "absent"
        )
        qualified = (
            current
            and consistent
            and registered["evidence_sha256"] == observation["evidence_sha256"]
        )
        if not qualified:
            blockers.append("copy-evidence-stale-or-inconsistent:" + copy_id)
        outcomes[copy_id] = observation["state"]
        if observation["state"] != "absent":
            blockers.append("copy-not-absent:" + copy_id)
        if deadline is None or not qualified or observation["state"] == "unknown":
            timing.append("unknown")
        elif observation["state"] == "present":
            timing.append(
                "missed"
                if stamp(observation["observed_at"]) >= stamp(deadline)
                else "pending"
                if now < stamp(deadline)
                else "unknown"
            )
        elif observation["absent_since"] is None:
            timing.append("unknown")
        else:
            timing.append(
                "met" if stamp(observation["absent_since"]) <= stamp(deadline) else "missed"
            )
    if (
        records["coverage"]["recoverable_until"] is not None
        and stamp(records["coverage"]["recoverable_until"]) > now
    ):
        blockers.append("recorded-recovery-still-available")
    timing_status = next(
        (state for state in ("missed", "unknown", "pending") if state in timing), "met"
    )
    # No completeness claim follows from potentially contradictory evidence.
    if any(reason.startswith("copy-evidence-") for reason in blockers):
        timing_status = "unknown" if timing_status != "missed" else timing_status
    registered_timing = timing_status
    recovery_conflicts = [
        reason for reason in retention["blockers"] if reason.endswith(":recovery-outlives-deadline")
    ]
    conflicts.extend(recovery_conflicts)
    if recovery_conflicts and timing_status != "missed":
        timing_status = "unknown"
    if timing_status == "met" and blockers:
        timing_status = "unknown"
    return {
        "schema": "opent1d.lt1-logical-removal-assessment/1",
        "kind": scope["kind"],
        "as_of": as_of,
        "register_sha256": expected_register_sha256,
        "scope_sha256": expected_scope_sha256,
        "observations_sha256": expected_observations_sha256,
        "context_sha256": expected_context_sha256,
        "within_reviewed_scope": "evidence-complete" if not blockers else "incomplete",
        "scoped_removal_evidence_complete": not blockers,
        "retention_timing": timing_status,
        "registered_copy_timing": registered_timing,
        "retention_deadline_met": timing_status == "met",
        "policy_conflicts": conflicts,
        "blockers": blockers,
        "copies": outcomes,
        "truth_of_external_observations_independently_proved": False,
        **AUTHORITY,
    }
