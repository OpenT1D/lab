# ADR 0100: Separate native preparation and scoped recovery evidence

- Status: accepted for read-only preparation; operational gates remain closed
- Date: 2026-11-03

## Context

[ADR 0099](0099-lt1-quarantine-and-host-fixtures.md) qualifies invented Python
host/removal cases. It neither runs the selected Node engine nor accounts for
recoverable copies. Worker checks run after Node startup, so they cannot undo a
preload already executed by that startup. Namespace absence also cannot answer
whether an object remains available through an ordinary restore path.

## Decision

Add a data-only launch preparation assessor. Bind the selected runtime, fixed
worker/argv, clean environment, actual supervisor working-directory convention,
source/reader/plan identities and separately reviewed input bytes. Reject extra
flags/preload environment and unsupported enforcement claims. Opaque receipt
hashes bind bytes; they do not establish their semantic approval. Keep native
bootstrap, modules, addons, process, file/network and host-mechanism cases explicit
and distinct from invented tests. All authority/qualification flags remain false,
even if a supplied packet becomes ready for independent review.

Provide a separate explicit, canonical-source, read-only OS/process collector.
Record fixed boot/kernel queries and the observer's process start and POSIX
session; unavailable observations stay unknown. Never infer login/audit-session
continuity or identify the short-lived observer as a future launcher. Keep actual
identifiers and context bytes private. The assessor itself performs no capture,
filesystem inspection, staging, spawn or admission.

Add a pure logical-recovery evidence assessor for an explicitly reviewed ordinary
application-access/restore scope: live copies, quarantine, snapshots and backups.
Require the entire registered denominator, current externally pinned coverage
receipts and consistent copy observations. Preserve retention history and original
origins. Report scoped absence, deadline timing, policy conflicts and authority
separately. A predeadline presence observation cannot prove a later violation;
contradictory recovery timing cannot prove compliance. Unknown origin/coverage
remains unknown. An existing hold neither extends the clock nor silently reverses
an otherwise truthful observation of absence.

The supported scope explicitly excludes physical forensics and privileged memory.
This is a declared scope, not a claim that those recovery paths are impossible.
Do not add a universal crypto-erasure requirement or call logical evidence
physical sanitization. The actual storage/recovery scope and an appropriate
removal mechanism still need review; metadata cannot prove external claims true.

## Consequences and alternatives

There is no new authority registry, launcher, deletion CLI, scheduler or automatic
scope acceptance. Existing setup-request, setup-receipt, execution and removal
lists remain empty. Reusing the Python fixture as native clearance, treating
unlink as global erasure, or demanding an unselected forensic threat model would
each answer a different question from the evidence collected here.

Revisit this decision when reviewed actual native startup/confinement cases and
an approved recovery scope supply concrete observations. A later launcher must
enforce its reviewed contract before Node starts and reobserve current source,
runtime, host and ownership. See the [implementation and limits](../research/ot062-lt1-native-recovery.md).
