# ADR 0103: Prepare entry observations and preserve private review bundles

- Status: accepted for bounded implementation; production authorities stay empty
- Date: 2026-11-03

## Context

An ordinary attempt journal has no case-specific native instrumentation. A retained
recovery proposal also needs durable provenance before someone can review its
exact bytes. Neither a normal completed attempt nor a saved proposal grants
native qualification or permission to remove private data.

## Decision

Prepare a fixed entry-observation producer and strict frame reader. The producer
has no CLI or automatic launch route. Its production observation function checks
exact source-local engine/integration/setup and observation-grant memberships
before acquiring process/binary facts. It observes an already running Node; it
does not establish that admission preceded Node startup or that the record was
made before model imports. Pure supplied facts always produce invented records.
Use bounded returned frame bytes; do not fill the required-empty journal output
or add unreviewed writes to the existing sandbox profile. Match separate parent
entry PID/start/executable evidence with owner/attempt/nonce/profile/grants. Keep
all native families unrun; actual fixed-entry/transport wiring remains separate.

Save review proposals in a new private closed flat bundle. Preserve exact input
and proposal/provenance bytes, predecessor, original clocks and holds. Write an
intent before copied inputs; use private descriptors, fsync and exclusive publish.
Keep interrupted prefixes and uncertain published output, without cleanup/retry
that overwrites data. Reopen against external manifest/current-register/context
identities, verify stored replay and compute a separate current assessment.
Never move the assessment clock backward or replace the active register.

Prepare only an unadmitted exact removal request for the entire own bundle.
Capture signatures after publication/readback; retain the request, context and
later journal outside its target. Do not infer a closed directory from one probe
or grant complete ordinary recovery coverage from successful queries.

## Consequences

Existing workers, journal, process owner, launcher/profile, registries and
scientific references remain unchanged. New evidence is private and subject to
the inherited clocks and holds; creation does not restart retention. Runtime,
rights/security/setup and actual execution decisions, full native instrumentation,
C15-C18 and complete restore/effective-removal evidence remain open.
