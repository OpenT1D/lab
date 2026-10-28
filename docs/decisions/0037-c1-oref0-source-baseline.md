# 0037 — Use upstream tests and a locked local fingerprint for `oref0`

Status: accepted locally on 26 September 2026 for OT-019 source preparation.

## Context

[Decision 0036](0036-c1-feedback-family-retirement.md) required upstream
example parity before adapting an OpenAPS reference. [C1/1.1](../research/c1-oref0-preflight.md)
found that the pinned CLI disagreed with upstream `examples/suggested.json`.
The [C1/1.2 source-history audit](../research/c1-oref0-example-history.md)
reproduces the mismatch at the fixture's introduction, both 0.7 releases
and the current pinned source. At introduction, upstream IOB and meal
examples regenerate exactly; only the suggested output differs. The
upstream basal unit suite passes, while the full suite has syntax, shell
and JavaScript runtime failures on this host. Exact published-example
parity cannot be claimed from these tested source/fixture pairs.

## Decision

Retain the failed committed example as a visible negative result. For
**source fidelity during simulator-free adapter development**, use the
upstream-authored `determine-basal` tests together with an OpenT1D-owned
CLI output fingerprint, exact source commit, Node/npm versions and a
separate dependency lock. The fingerprint confirms repeatability of this
configured source; it is not an upstream-validated example, a scientific
outcome, or a substitute for causal/action verification. Do not relabel
this result as a parity pass under decision 0036.

The reference remains ineligible as an M1 strong comparator. Before any
native C1 scoring, verify causal IOB and announcement construction,
five-minute/three-minute timing and persistent temp-basal action meaning,
stale/reset/failure behavior, dependency rights and a matched declared
development budget. If these require changing algorithm semantics, give
the adaptation a distinct method label and do not inherit OpenAPS's
published outcomes.

## Alternatives considered

Selecting the tested older releases does not repair their example output.
Editing the upstream fixture would erase the discrepancy. Abandoning the
candidate before testing its M1 information/action mapping would leave a
source-backed possibility unexamined. The local fingerprint gives that
mapping work a repeatable starting point while preserving the mismatch.

## Consequences and revisit rule

The locked baseline permits a bounded simulator-free adapter prototype
without pretending that the stale upstream fixture agrees. Changing the
source revision, output fingerprint or lock requires a new explicit
source-review record. Revisit the original example gate if upstream fixes
or explains its fixture, or if a different exact source/example pair is
verified under its own appropriate runtime. The current audit covers four
revisions, not all upstream history or Node 8. No clinical or human
performance conclusion follows.
