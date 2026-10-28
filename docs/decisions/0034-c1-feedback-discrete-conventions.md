# 0034 — C1 feedback discrete conventions

Status: accepted locally on 25 September 2026 for OT-019 development.

## Context

[Decision 0033](0033-c1-feedback-redesign.md) selected a bounded,
two-sided feedback family after negative known-case results, but left its
discrete integral, limit order, stale-sensor behavior and matched comparison
unspecified. Those choices affect control behavior and reproducibility.

## Decision

Implement an unconfigured pure kernel with an explicit proportional term,
elapsed-error integral and optional positive fresh-rise term, as specified
in the [C1/0.6 record](../research/c1-feedback-kernel.md). Rate correction
is relative to a caller-owned native basal base; clamp the final basal rate,
apply upward slew to the correction, and freeze integral only when its error
pushes farther into a binding total-rate or upward-slew limit. A fresh low
clears positive integral memory and blocks positive correction, while a
held observation returns the native base without stale integration.
The matched engineering comparator changes only the rise gain to zero.

## Alternatives and consequences

A one-sided overlay was retired after its known-case matrix. Integrating
held CGM or clamping output while continuing to accumulate error would
make the stored state depend on unobserved periods or binding limits.
Unbounded upward correction could also hide the native base transition.
The chosen order makes those cases explicit and testable, but it does not
establish gain suitability or numerical/clinical performance. A later
native adapter owns unit conversion and the unchanged meal bolus; it must
not retroactively reinterpret the old C1 evidence.

Revisit these conventions if source-level native integration exposes a
contract mismatch or bounded development evidence shows unacceptable
behavior. Such a change needs a new record and fresh comparison; it cannot
be tuned on a reserved evaluation.
