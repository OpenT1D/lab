# 0044 — Keep G2P2C technical readiness separate from comparator eligibility

**Status:** Accepted for the C1/1.10 M1 integration gate, 26 September 2026.

## Context

[Decision 0039](0039-c1-comparator-route.md) closed unchanged `oref0` on M1
and selected pinned G2P2C as a conditional published-method route. Decisions
[0042](0042-c1-g2p2c-training-freeze.md) and
[0043](0043-c1-g2p2c-missing-cgm.md) fixed three-minute source training and
the missing-CGM adaptation. Both full source attempts and the two frozen
native M1 smokes have now completed. Their artifact hashes and the
byte-identical readiness repeat are in the
[C1 evidence index](../../experiments/c1/evidence-index.json).

## Decision

Accept the two trained weights-only actors as passing the **bounded technical
M1 integration gate**: source/intake forward paths match on invented states,
both known condition-D native cases complete 960 intervals with ten exact
profile-basal fallbacks, saved action replay passes, and each fresh-process
repeat is byte-identical. The readiness audit reports
`technical_m1_boundary_pass: true`.

Do not mark G2P2C an eligible strong comparator yet. The source is a
three-minute adaptation trained on the same known virtual profiles, its
missing-CGM fallback is an OpenT1D convention, and two condition-D smoke
cases do not establish glucose-control quality or equivalent development
budgets. A matched known-case development roster, native reference coverage,
equal-information rules, failure accounting and an original candidate route
must be frozen separately before a comparison. No new efficacy matrix is
authorized by this decision.

The C1/1.10 command sequence said to wait for both checkpoint intakes before
native execution. Adult#001 ran after its own intake while adult#002 was
still training. Keep this ordering deviation visible in the evidence and
review it before any comparator-eligibility claim. It changed no frozen
case, actor weights, action rule or technical acceptance condition.

## Consequences

The [native smoke record](../research/c1-g2p2c-native-smoke-plan.md) and
[roadmap](../../ROADMAP.md) may report a passed technical boundary, while
`eligible_m1_comparator` remains false. Earlier negative controller and
`oref0` evidence stays intact. A later matched development freeze must be
reviewed as a separate decision; this one does not score efficacy or imply
benefit for people.
