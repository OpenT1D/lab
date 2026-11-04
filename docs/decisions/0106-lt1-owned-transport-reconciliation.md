# 0106 — LT1 owned transport and bundle-copy reconciliation

## Decision

Use the unchanged shared process owner for a task-local descriptor transport
adapter. A fixed internal exec shim maps two exclusively transferred sockets to
ACK input 3 and frame output 4 before replacing itself with a trusted entry.
Preserve the same owned process identity across exec, exact clean environment,
DEVNULL stdin, closed unrelated descriptors and separate protocol/log channels.

The spawn hook returns promptly. A bounded channel thread waits for complete
frame EOF before trusted verification and one ACK plus EOF; process cancellation,
deadlines and descendant cleanup remain owned by the canonical supervisor. Retain
channel prefixes and process outcomes separately. No hard callback preemption or
native peer/phase/confinement follows from this resource adapter. Only invented
tooling-Node fixtures call it here; no native launcher route or authority changes.

Add an unsaved proposal reader for explicitly allocated bundle-copy IDs. Validate
externally pinned retained base, registration successor, allocation, provenance,
manifest, intent, request/context/journal and outer receipt before namespace intake.
Only fully completed unchanged removal readback may change those new copies to
`absence-observed`. Incomplete evidence leaves exact registration bytes unchanged.
Preserve all older subjects/copies, origins, holds, original deadlines and recovery
horizon. Coverage and authority stay false; no register activation occurs.

## Consequences

The journal has no removal timestamp: absence does not establish timely retention
compliance. New returned metadata requires separate accounting. No actual private
payload or recovery channel is removed or qualified. The old launchers, profiles,
workers, process owner, setup/execution/removal authorities and historical readers
remain unchanged. Native host qualification and effective erasure remain separate.
