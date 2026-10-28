# 0035 — One-factor C1 feedback target alignment

Status: accepted locally on 25 September 2026 for OT-019 development.

## Context

The [C1/0.7 matrix](../research/c1-feedback-development.md) completed a
matched native comparison but lost 70–180 exposure versus basal-bolus in
three of four missing-announcement B cells and one full-announcement A
cell. The [C1/0.8 timing audit](../research/c1-feedback-diagnostic.md)
locates persistent pre-breakfast downward correction and later high-side
threshold losses. Native basal-bolus uses target 140 mg/dL, while that
feedback attempt used 160 mg/dL. The traces do not prove causation.

## Decision

Permit one additional **matched** known-case setting attempt per feedback
method, changing only their shared feedback target from 160 to 140 mg/dL.
Keep all other feedback settings, native actions, roster and analysis
boundaries fixed. The candidate retains its rise gain; the matched
engineering comparator sets only that gain to zero. Materialize the 48-case
plan and preserve the full denominator before any native execution. The
one-attempt C1/0.7 results remain visible; the cumulative budget becomes
two setting attempts per feedback method. No new native score is part of
this decision.

## Alternatives, consequences and revisit rule

Changing several gains together would obscure what this audit tests.
Suppressing all downward feedback could also discard the only observed
pre-breakfast low-exposure benefit. This one-factor alignment tests a
specific timing hypothesis while preserving a matched comparison, but
could worsen low exposure. Apply the predeclared B and A development
screen in the [audit record](../research/c1-feedback-diagnostic.md).
If it fails, preserve the negative attempt and reassess the method before
another settings search. Even if it passes, a qualified published-method
comparator, Cambridge route and separate frozen evaluation remain open.
