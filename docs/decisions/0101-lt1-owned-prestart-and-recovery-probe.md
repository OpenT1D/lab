# ADR 0101: Enforce the owned pre-start boundary and observe recovery channels

- Status: accepted for bounded qualification; production authorities remain empty
- Date: 2026-11-03

## Context

[ADR 0100](0100-lt1-prelaunch-and-recovery-evidence.md) validates supplied launch
and recovery metadata. It does not enforce the command before Node starts or
observe actual storage. The existing supervisor owns processes; duplicating that
owner would introduce different cancellation and cleanup behavior. Namespace
readback and successful system queries also cannot prove complete restoration
coverage.

## Decision

Add a fixed internal native qualification launcher on the existing supervisor.
Require both exact engine/integration grant hashes in the existing execution
authority before supplied paths, capture or spawn, and separately require the
actual setup-receipt hash in the existing setup authority. Do not add another
registry or promote preflight status into admission. Exact reviewed grants may
permit the first bounded qualification; requiring all six native case families
passed before that first qualification would be circular.

Port the existing staging/worker/reader/plan/grant byte bindings to the pre-start
side. Bind a versioned integration host receipt to the same live main-thread
owner, boot/account/process-start/POSIX session, launcher sources, four separate
root identities, fixed sandbox/profile bytes and bounded clocks. Prepare/review
the receipt and grants in that still-live owner process. Reobserve current stable
fields without resealing approved bytes. Keep the engine host receipt separate.

Add optional stdin and last-pre-spawn controls to the shared supervisor; existing
callers retain normal stdin behavior. Native qualification passes DEVNULL,
explicit close-fds and exactly three environment keys. Its hook checks the opened
private log, captures the current owner before consuming final bytes, then checks
source/tool/packet/staging/root bindings and context expiry again before spawn.
An already cancelled hooked launch starts no worker. Preserve failures, owned
cleanup and unrelated processes. Hash-to-exec remains non-atomic under hostile
same-user writes; reviewed quiet ownership is still required.

Add a separate explicit read-only collector for three fixed Data-volume queries
and at most sixteen reviewed local files. No directory walk, backup mounting,
Full Disk Access change, root privilege, deletion or encryption operation is
provided. Target readbacks carry intervals and never invent an original time or
an absence onset. Successful command responses and even empty inventories leave
all complete-coverage and authority flags false.

## Consequences and alternatives

The fixed Python process fixture can establish pre-start stdio/environment and
owned-process behavior. Mocked native packets establish bounded verifier behavior.
Neither establishes Node bootstrap/confinement, native numerical acceptance,
actual setup or effective removal. Broadly allowing checkout reads, executing Node
to discover its version before admission, or treating query success as backup
closure would bypass the selected boundary.

The supervisor source identity changes; historical inventories remain historical.
New packets and qualification receipts must bind the new source. Existing workers,
readers, registries, locks, scientific baselines and tolerances remain unchanged.
Revisit after exact runtime/rights/setup decisions, admitted native cases and a
reviewed actual recovery scope supply evidence described in the
[implementation record](../research/ot062-lt1-prestart-recovery-probe.md).
