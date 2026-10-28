# 0045 — Make researcher-owned methods the platform priority

**Status:** Accepted on 26 September 2026 for project direction and future work allocation.

## Context

OpenT1D's M1/M2, M3, P1, C1 and M4/M5 work has produced bounded research
workflows, adapters and verification tools. The earlier direction in
[decision 0006](0006-model-controller-development.md) made an original
controller and a physiological improvement project objectives;
[decision 0016](0016-parallel-control-cure-research.md) placed control and
cure-oriented preparation in parallel. The maintainer has clarified that
OpenT1D should supply **research tools that connect to existing methods**.
Researchers bring their own models, controllers and appropriately authorized
data. The recent G2P2C work passes a narrow technical M1 boundary, not a
comparative efficacy gate ([decision 0044](0044-c1-g2p2c-native-readiness.md)).

## Decision

Make the reusable laboratory the primary deliverable: documented boundaries
for external models and controllers, capability and rights checks, causal
inputs, units and clocks, reproducible execution, complete failure accounting,
and reports reconstructible from saved artifacts. Develop these through
bounded user tasks, beginning with the existing P1 workflow, rather than
promising a universal host before one is demonstrated.

OpenT1D does not supply a patient dataset or claim ownership of a researcher's
restricted observations. Public examples may use clearly labeled invented
data; source assessment, converters and local authorized evaluation tools may
support researcher-managed data without bundling or publishing it. Upstream
models and small attributed reference implementations may remain as test
fixtures or supported integrations, subject to their rights and evidence.

An original controller, a new physiological mechanism or a treatment model
is an **optional, separately justified research contribution**, not a gate
for the platform, the glucose-control tools or the cure-oriented tools.
The historical C1 and B1 protocols remain reviewable; a new original-method
attempt requires a specific question, evidence and a fresh declared work
package. Cross-method tools should accept suitable external candidates and
must not depend on both an OpenT1D controller and OpenT1D physiology.

Preserve the distinction between a working adapter, source reproduction,
simulation behavior, external biological evidence and clinical benefit.
Technical compatibility does not establish comparator eligibility, better
glucose control or a cure.

## Alternatives

- Require an original controller and improved physiology before declaring
  platform success: this makes optional scientific hypotheses prerequisites
  for researchers to use the tools.
- Stop the bounded C1 and M4/M5 experiments: this would discard useful
  interface and evidence work rather than retain it with its limits.
- Publish or host datasets as a core product: this is outside the stated
  tool-only scope and would change rights and data responsibilities.

## Consequences and revisit condition

This supersedes decisions 0006 and 0016 **only for future priorities and the
requirement to build original methods**. Their scientific evidence rules,
parallel application areas and completed historical protocols remain intact.
The [roadmap](../../ROADMAP.md) is the canonical plan; update public-facing
guides to match it. Keep old experiment results, negative findings, source
identities and evidence limits unchanged. Revisit this scope only after a
documented user need and a separate decision; do not infer it from a
successful synthetic run.
