# 0015 — Separate PhysioCGM timing follow-up

Status: accepted for synthetic software implementation, 20 September 2026.
Human preparation and execution remain separate steps.

## Context

The original [PhysioCGM forecast protocol](../research/physiocgm-external-freeze-protocol.md)
requires exact registered times. Inspection of known study material motivated
a separate question about small timestamp differences. Widening the old
matching rule in place would change the meaning of preserved evidence and
obscure that the new question arose after inspection.

## Decision

Add the isolated `experiments.m3.physiocgm_timing` namespace under
[M3-PHYSIOCGM-TIMING/0.1](../research/physiocgm-timing-protocol.md), schema
`opent1d.physiocgm.timing/1` and metric `physiocgm-timing-forecast/1`.
Preserve earlier protocols, sealed implementation sources and artifacts.
This decision supersedes none of them.

Fix three matching radii: zero seconds for exact reconciliation, one second
for the main post hoc comparison and five seconds for sensitivity. Keep the
origin exact, select nearest timestamps independently of value/status, reject
ties and unusable nearest observations, and preserve causal availability and
clock/interval boundaries. Do not interpolate, round or refit. Require nested
prediction/scoring sets and identical outputs on shared eligible origins.

Retain the original full-variant participant contribution and uncertainty
rules. Report added scored subsets separately without substituting absent
people's results or bootstrapping those subsets. Improved coverage and
improved prediction are different outcomes.

Implement only the matching component and a bounded synthetic demonstration
with internally generated observations and a hand-defined model. Expose
`demo --output` and `verify --study`; do not accept human inputs or models
through this command surface. The new human plan, source bindings, access
history, execution and reconciliation with saved real results require a
separate implementation and authorized execution step.

## Alternatives

Changing the original exact matcher would undermine historical reproduction.
Rounding or interpolating would impose additional measurement assumptions.
An unrestricted radius would allow outcome-driven selection. The fixed
separate route makes the approximation, earlier access and evidence boundary
explicit without changing the predictor.

## Consequences and conditions for revisiting

The project gains a testable timing comparison, not a new prediction method,
physiological model, controller or human-performance claim. The intended
human follow-up remains post hoc even after its new plan is frozen. Synthetic
verification cannot establish real sensor availability or participant
independence.

Before human execution, preserve the original evaluation, verify zero-second
agreement and implement a private source-bound workflow with explicit access
evidence. Another matching policy, model or selection rule requires a new
version and disclosure of the material already inspected.
