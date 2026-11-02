# ADR 0099: Qualify exact-file quarantine/removal and separate host fixtures

- Status: accepted for invented fixtures; production removal and native gates closed
- Date: 2026-11-02

## Context

The [retention planner](0098-private-retention-planning.md) produces review items,
never deletion permission. Host and effective-erasure evidence are incomplete.
A filesystem mutation needs exact authority and retained partial evidence. A
pathname check followed by POSIX unlink is not an atomic expected-inode operation.
The earlier Python host fixture also does not cover all selected write/exec/alias
boundaries or constitute a native sandbox.

## Decision

Keep all existing setup-request, verified setup-receipt and execution lists
unchanged. Add a separate fixed `removal-admissions.json`, initially empty, for
exact reviewed removal-request hashes. The production API rejects unknown bytes
before parsing caller paths or creating evidence. It accepts no caller registry,
approval flag or retention-plan promotion. Trusted registry/callback injection
exists only for controlled invented tests, not as a hostile-Python boundary.

Bind a request to current helper/import/initializer source and Python identity,
host/account observations, reviewed context bytes, a private existing flat directory, exact
ordinary single-link file identities/bytes, and a separate fresh evidence attempt
on the same filesystem. Validate every input before mutation. Keep original file
descriptors open to prevent inode reuse during the operation. The static source
inventory does not qualify an entire bootstrap, import cache, standard library,
dynamic library, OS or arbitrary same-user process.
The host tuple is not a boot/login/session-continuity proof.

Move each named entry exclusively to a new private quarantine using the existing
atomic no-replace primitive. Revalidate its inode/content there before unlink.
Mismatches remain in quarantine; never restore blindly, recursively clean or
resume/adopt a previous attempt. Retain fsynced prepared/move/removal events and
observed final namespaces outside the target. Failed journal writes preserve the
prefix instead of appending a misleading terminal record. A crash between unlink
and logging can leave an unrecorded absence; the prefix is a lower bound.

This protocol requires exclusive, quiet ownership. The final check-to-unlink
window still exists for a hostile process under the same UID, including inside
quarantine. Do not claim atomic inode-conditioned deletion or a hostile-owner
sandbox. The reader requires externally retained request/journal identities,
current source/root/journal/mode/namespace observations and a consistent zero-exit,
error-free, cleaned owned process before reporting fixture completion. A marker,
boolean zero, or reported path absence alone is insufficient.

Add a separately versioned Python host-boundary fixture, preserving legacy source
identities. Qualify complete and cancel cases with successful unconfined controls,
nine parent/child denials, observed live child start identity, stopped heartbeat,
unrelated-process preservation and cleanup. Use inherited descriptors for the
no-op executable probe so a preliminary DEVNULL open cannot masquerade as exec
denial. Narrow broad `/System` read/map access; retain the explicit dyld and broad
mach-lookup limitations rather than claiming complete IPC confinement.

## Consequences

Only fresh invented data is moved/unlinked for qualification. No generic deletion
CLI, scheduler, native dispatch or automatic admission is added. Quarantine is
another retained location of the same private object, never a new retention clock.
All results keep new authority, setup/native admission and effective-erasure claims
false. Backups, snapshots, recoverable storage and actual native TCB/confinement
remain separate prerequisites in the [host/removal record](../research/ot062-lt1-host-removal.md).
