# ADR 0098: Separate private retention planning from removal and admission

- Status: accepted for bounded implementation; native host and erasure unqualified
- Date: 2026-11-02

## Context

Approved use conditions do not establish rights clearance, runtime risk acceptance
or effective removal from a host. Path deletion does not account for copies,
logs, caches, backups or snapshots. Birth/mtime observations are not automatically
original acquisition evidence. Human identities, host/storage details and the
actual policy duration remain private.

## Decision

Add a read-only planner with external byte identities for its register, separate
private policy, latest predecessor and current reviewed context. It has no file
access, deletion command, scheduler or admission updater. Expected identities
must come from trusted current review; hashing supplied records does not prove
their truth or complete history.

Stable subjects describe private objects across copies and revisions, sharing
their original audit creation/acquisition clocks. Independently generated outputs
are separate subjects. Unknown origins remain unknown. A supplied predecessor's
subjects/copies cannot disappear and an established origin cannot move forward.
Registers bind the policy identity. This version refuses policy changes within
a predecessor chain; an explicit successor is needed for a different policy.
Omitted history or a falsely relabelled copy still needs external review.

The private policy fixes a maximum age in seconds with no extension or export.
Expiry uses UTC and includes the deadline. Holds, missing copy/recovery/process
coverage and recoverable copies beyond expiry block the plan. Holds do not extend
deadlines. Known overdue copies remain visible as review items in blocked plans.
Expired subjects remain expired even when all named copies are reportedly absent.

Every result keeps effective erasure, deletion authority, setup admission and
native execution authority false. Actual removal needs a separately reviewed
exact inventory and host procedure. Source/host/storage/scope changes require a
new context. Existing setup-request, setup-receipt and execution lists stay empty.

## Consequences

Invented fixtures check the planning semantics. They do not delete evidence or
qualify storage sanitization. The [private controls guide](../research/ot062-lt1-private-controls.md)
owns the manual stop/inventory/remove/verify procedure and host prerequisites.
Actual rights/runtime/host and effective-erasure decisions remain open.
