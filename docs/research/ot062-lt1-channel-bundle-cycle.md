# OT-062 dedicated process channels and bundle removal cycle

PR #65 was critically reviewed again and merged as
`be18d23f5b58fa17304b1a3356aba592688b94fe`, with the same tree as tested
`a5606d58af2ff0d85a0895266e753619f25c97d8`. Its retained full local check passed
2,215 tests with 32 expected skips, and all sixteen required jobs in hosted run
41741931904 passed. Fresh agent reviews added stream, deadline, byte-ownership,
reader and registration controls without open findings. These results belong to
the preceding [handoff/registration increment](ot062-lt1-handoff-copy-registration.md).

[ADR 0105](../decisions/0105-lt1-dedicated-channels-bundle-cycle.md) selects a concrete
process-channel adapter and a full fresh-metadata bundle removal fixture. This
increment's PR owns its exact implementation and verification results.

## Selected process boundary

The explicit adapter uses fixed inherited POSIX socket descriptors 3 for ACK input
and 4 for frame output. Before adopting either, check both descriptor identities,
their separation from each other and all open stdio identities, and socket type.
The owner must supply these trusted, exclusively transferred channels; local stat
checks do not prove peer identity or native confinement.

The current-process wrapper performs existing observation admission before any
descriptor inspection, then the bounded handoff performs its own observation and
admission again. Both synchronous observations precede the asynchronous handoff
budget; this is not a total startup deadline. No worker or model is imported after
ACK. There is no CLI or automatic launcher route. The old launcher, fixed worker,
profile and descriptor-inheritance policy remain unchanged.

The integrated fixture uses ordinary tooling Node and invented facts in real
parent/child processes under the existing shared process owner. It exercises
separate frame/ACK channels, stdout/stderr separation, bounded parsing, EOF,
failure, deadline and cancellation. Native setup/execution and all six actual
native case families remain unrun. Actual selected-runtime descriptor inheritance,
profile permissions, bootstrap/phase/modules/addons and C15–C18 stay open.

## Selected whole-bundle removal boundary

Create and publish only new invented metadata in a private temporary directory.
Propose one explicit new bundle-copy ID for every old subject without activating
the register. Prepare an exact removal request against the bundle's stored original
base, not the separate registration successor. Preserve the active original
register, origins, holds and all other files.

First prove that production removal refuses the request. Only the trusted fixture
seam may then admit this exact new test request. Run removal in an owned process
and independently read back its journal and remaining target/quarantine names.
Completion concerns only the closed bundle namespace. Deadline/cancel retains its
exact prefix and remaining metadata. The registration proposal stays unchanged
and its new copy states remain conservatively present in all outcomes; no automatic
reconciliation or active-register transition follows fixture absence.

This does not establish complete live/quarantine/snapshot/backup accounting,
ordinary restore coverage, physical sanitization, actual retention compliance or
effective private-data erasure. No existing private pilot, backup, snapshot or key
is read or removed. All four production authority lists remain empty. Public
records contain no actual names, host/account/storage values or private receipts.
