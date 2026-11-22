# 0116 — MMTT input limits and exact reader transition

Date: 22 November 2026

Status: accepted.

## Context

The installed MMTT sensitivity service used a generic 4 MiB original-input
limit when it captured and reopened a plan. The task supports a 16 MiB
observation CSV and two 1 MiB JSON inputs. The shared route source participates
in the exact reader identities of comparisons, installed M4 and connected
studies. Correcting the limit changes those fingerprints.

## Decision

Use the task limits when capturing and verifying original MMTT inputs. Qualify
one readback edge from the exact reader inventories on
`e63a32be2592f9a68681d2a848d71495f209a32c` to the inventories recorded in
`reader_compatibility_mmtt_input_limits.json`. Pin the complete predecessor
identities in the implementation. For comparison readback, the existing
historical packets still authorize only their recorded MMTT predecessors,
through the pinned intermediate comparison reader.

Retain original project events, source inventories, scientific bindings and
report bytes. Verify both source inventories on M4 readback, including each
opaque saved source snapshot and the frozen attachment's file hashes and sizes.
Apply the same attachment check to stored reference and stage receipts. A prior
M4 plan needs a new freeze for execution under the current implementation and
runtime attachment. M4 input limits and GUI intake limits retain their contracts.

## Alternatives and consequences

Refreshing frozen hashes would discard evidence of the actual reader and source
versions. Accepting arbitrary changed fingerprints would remove exact admission.
The bounded edge keeps existing evidence and rejects other reader changes. Any
future successor needs its own decision and evidence. The installed regression
uses a valid synthetic CSV at exactly 16 MiB and checks the one-byte-over refusal.
Readback checks exercise preserved projects through separately installed wheels.
They cover an executed synthetic MMTT comparison, a connected study with a
retained forward failure, and a relocated incomplete M4 archive read through
the installed report reader. Actual native runtime and release qualifications
keep their original scope.
