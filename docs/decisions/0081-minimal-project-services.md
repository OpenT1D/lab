# 0081 — Preserve the ledger around isolated native tasks

Date: 29 October 2026

Status: accepted for internal extraction increment 2.

## Context

[Decision 0080](0080-two-route-contract-packet.md) froze metadata but left
storage/lifecycle with the tasks. A supplied manifest cannot establish an
all-attempt history. M4 activation changes module bindings and cannot safely
serve concurrent in-process callbacks. The MMTT historical-reader helper does
not cover the selected offline route.

## Decision

Use an exclusively locked local project with an append-only, hash-linked,
sequenced event directory and a committed head. Each event seals its complete
file inventory; the head binds the complete event roster. Publish immutable
events with the existing atomic no-replace primitive. Register attempts before
launch; terminal events seal native and forensic files. Interrupted store
transactions fail closed and retain their staging evidence. This is integrity
checking, not authentication against a person rewriting an entire store.

The first implementation claims the tested local POSIX host only. Run existing
coordinators in isolated processes. Use their own graceful cancellation and
process ownership; hard stops preserve partial evidence without inventing a
native result. Recovery never signals a stored PID and requires explicit user
attestation that a previous execution has stopped.

Retain scientific input, native implementation and additional static reader
snapshots explicitly. Select readers from a trusted fixed registry in the
checkout, in separate processes, and require exact matching retained identities
in this first compatibility matrix. Snapshots are opaque and never imported.
Keep every stricter native reader gate. Moving a project authorizes no setup,
code execution from the archive or reader upgrade. No SDK stability is implied.

## Consequences

Task protocols, native reports, source ancestry, locks, numerical tolerances and
failure denominators stay authoritative. Administrative slots do not replace
draw/stage ledgers. Native M4 success/complete relocation, approved reader
upgrades, other operating systems and independent intended-user use remain
separate gates. Private references and support-bundle export are outside this
public-synthetic fixture increment.
