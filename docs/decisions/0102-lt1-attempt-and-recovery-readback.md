# ADR 0102: Correlate LT1 attempt and recovery readbacks

- Status: accepted for bounded implementation; operational admissions stay empty
- Date: 2026-11-03

## Context

The fixed launcher and durable journal reader have separate process/byte bindings.
The recovery probe records point intervals, while the logical recovery assessor
expects copy observations with whole-second timestamps. Manual correlation can
mix attempts, drop registered copies or invent an exact absence time.

## Decision

Add two read-only consumers. Reuse the existing journal reader without changing
its bytes or process owner. Bind its exact journal, process receipt and plan to
both grants and the existing packet, owner, launcher and profile identities.
Preserve failed/interrupted prefixes. Keep all six native case families visible
as unrun: a consistent ordinary attempt contains no case-specific confinement,
module/addon or IPC instrumentation and cannot qualify those families.

Bridge retained recovery-probe bytes into an explicitly proposed successor
register and v1 observations. Preserve all subjects, copies, original clocks,
holds, policy and coverage. Retain exact per-copy provenance and both interval
bounds. A whole-second floor of the interval start is only a conservative
freshness anchor. Never derive absent_since or complete recovery coverage.
Unknown readbacks retain their prior registered state and remain unknown evidence.
No proposal is saved, approved or admitted automatically.

## Consequences

Externally expected byte identities establish consistency, not independent truth.
All setup, execution, deletion, effective-erasure and general native-qualification
flags remain false. Existing workers, readers, registries, locks and scientific
references stay byte-identical. Actual native instrumentation/C15-C18, ordinary
restore coverage, original timing and admitted removal remain separate work.
