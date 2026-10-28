# 0033 — Retire the first C1 lead and redesign the feedback comparison

Status: superseded locally on 26 September 2026 by
[decision 0036](0036-c1-feedback-family-retirement.md) for the feedback
family's lead role. The historical retirement of the first overlay stands.

## Context

[Decision 0032](0032-c1-causal-overlay.md) selected the trend overlay as the
first small C1 method, with an explicit instruction to revisit it if
development exposed a poor fit. The [C1/0.4 matrix](../research/c1-known-development-matrix.md)
completed all 64 known-case processes. The original overlay had no B-cell
in-range gain and one B-cell low-exposure regression. Raising its target to
180 mg/dL removed that observed regression but still gave no B-cell in-range
gain. The adapted PID completed all cases, but its outcomes reversed and its
native integral is unaware of the post-processing clamp. The
[C1/0.5 audit](../research/c1-method-revision.md) quantifies the action
timing and clamp requests from saved artifacts.

## Decision

Retire the C1/0.2 trend overlay **as the lead candidate for the missing-meal
benefit claim**. Preserve its implementation and both tested settings as
development history. Do not freeze either setting or tune it on the future
evaluation.

The next candidate family is a **bounded, two-sided causal feedback
correction** on the unchanged basal-bolus feedforward, with an explicit
anti-windup rule and optional fresh-observation rise term. Its matched
engineering comparator is the same bounded feedback scaffold with the rise
term disabled. This pair is intended to isolate the added trend response,
not to establish novelty of feedback control. Both consume the same released
CGM/announcement history and have the same action limits, base bolus,
initialization, reset and missing-observation fallback. The kernel must be
unconfigured and simulator-independent before a native adapter is added.

Keep unchanged M1 basal-bolus and native PID as historical anchors. The
current adapted bounded PID remains a negative development comparator, not
the selected strong reference. A superiority claim still requires a
separately source-traced, reproducible **published-method** comparator with
equivalent information and declared development budget. A published PID
plus insulin-feedback trial motivates examining delayed insulin action and
feedback, but does not supply verified gains or validation for our new
kernel ([Ruiz et al., 2012](https://pubmed.ncbi.nlm.nih.gov/23063039/)).
A randomized published MPC/PID comparison included an unannounced meal, but
its systems and participants are not equivalent to this pinned simulator
([Pinsker et al., 2016](https://pubmed.ncbi.nlm.nih.gov/27289127/)).

## Consequences and next gate

The next implementation must first define the exact state update, bounds,
units, anti-windup behavior, response to stale/nonfinite observations and
source ancestry. Then exercise reset, finite-state, limit, stale-sensor and
zero-rise equivalence checks without a simulator. Before native scoring,
declare the same 16 known profile/seed/condition cells and the same maximum
number of setting attempts for candidate and matched comparator; retain
every attempt and failure. The development analysis must report paired B
70–180, below-70/below-54 and above-250 directions and A preservation.

The matched engineering comparator is not automatically an eligible strong
published reference. If source fidelity, equivalent information or
numerical reliability cannot be established for a strong comparator, C1
remains a development demonstration. Cambridge adaptation and the exact
new-scenario freeze wait for that evidence. No clinical device behavior,
human benefit or efficacy is inferred from the synthetic matrix.
