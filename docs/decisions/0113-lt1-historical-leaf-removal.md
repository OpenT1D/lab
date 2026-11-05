# 0113 — Exact LT1 leaf removal in a mixed historical directory

## Context

The flat remover requires every immediate entry to be an approved regular file.
The native tree remover admits only its fixed output, evidence and packet roles.
Neither represents one legacy private record in a historical directory containing
unrelated files and subdirectories. Deleting the whole directory would exceed the
requested scope. Existing setup, execution and removal admissions remain empty.

## Decision

Implement one additive, versioned single-leaf helper and its strict reader in the
same increment as its fixture qualification and copy/recovery scope assessment.
Keep the historical flat/tree helpers, scientific readers, source inventories and
all operational admissions unchanged. Do not merge a separate design-only layer.

An exact request names one ordinary single-link file, a private canonical parent,
a bounded closed immediate sibling inventory and a separate private same-volume
evidence parent. Bind independently reviewed source, host, context, parent,
evidence-parent and target identities. Sibling metadata establishes only the
reviewed immediate namespace; it does not attest every descendant's bytes or
grant any sibling deletion. Do not traverse subdirectories or follow links.

Check request membership in the existing canonical removal registry before
parsing caller bytes or acquiring private paths. No caller-selected registry or
automatic request publication is added. Retain private fixture injection for
newly created invented objects only. Actual private data still needs separate
review and exact removal admission after process, storage and recovery checks.

Hold and recheck file/directory descriptors, exact bytes, ownership, link count,
private modes, source and journal identities. Require separately reviewed ACL
and process-quiescence context; Unix modes alone do not prove either. Quarantine
only the target through exclusive same-volume rename before unlinking it. Reject
unexpected immediate entries, parent/target/journal replacement, changed sibling
metadata and collisions. Preserve failures and move-before-journal gaps without
resuming or manufacturing missing events. Retain the existing exclusive-owner
assumption: POSIX unlink does not atomically compare an expected inode, and this
helper does not isolate a hostile same-UID process.

Readback requires independent exact request, journal and outer-receipt identities.
Only coherent complete process/journal/current-namespace observations may report
target absence. Incomplete, interrupted or failed evidence remains incomplete.
That result establishes neither recursive sibling immutability, complete copy
coverage, timely retention nor effective erasure. Every setup, native execution,
new-authority and effective-erasure result remains false.

## Verification and scope

Two agents implement and separately challenge the bounded change. The integration
owner alone runs the final full repository check. Exercise actual owned processes
on fresh invented mixed directories: success, deadline, cancellation, exact
quarantine prefix and untouched sibling/process sentinels. Challenge stale bytes,
source/context/pins, parent/evidence/journal swaps, links, namespace changes and
late transitions. Keep portable fixtures separate from selected native runtime
qualification; no existing private file is a destructive test input.

The private copy/recovery assessment may narrow actual previous exclusions using
bounded passive reads. Preserve owner statements separately from technical
observations, original clocks, predecessor history, holds and unknown coverage.
Current empty snapshots/destinations and FileVault do not prove global recovery
absence or per-file cryptographic erasure. New evidence itself needs private
retention accounting; publish no actual identity, host/path map or private policy
hash. Complete native qualification and actual removal remain separately gated.
