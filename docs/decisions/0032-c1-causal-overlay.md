# 0032 — C1 causal trend overlay as first method

Status: superseded on 25 September 2026 by
[decision 0033](0033-c1-feedback-redesign.md) for the next OT-019 method.
Its original implementation and development evidence remain historical.

## Context

C1/0.1 selected missing meal announcements as the first controller question,
without selecting an algorithm. M1/M2 expose bounded observations and
actions, but their frozen workers accept only native controllers and fixed
scenarios. The simglucose native PID stopped often in M2, and Cambridge has
one parameterization with documented MPC numerical sensitivity. Published
unannounced-meal methods already exist; an originality claim must name our
concrete contribution rather than the broad idea.

## Decision

Select an auditable, age-aware trend overlay on native reference output as
the first C1 method. It consumes only released sensor history and its own
previous extra commands, modifies basal rate under declared limits, and
leaves native bolus and physiology ownership intact. Implement the
simulator-independent state machine first with no preset patient dose or
gain. Then build separate C1 adapters and strong matched-information
comparisons. Treat all existing trajectories as development-known and freeze
an exact new scenario evaluation only after the code and comparators pass
development verification. See the [method record](../research/c1-method-feasibility.md).

## Alternatives and consequences

A new MPC would require estimator and solver evidence before it can be a
small first contribution. A learned policy lacks an authorized training
contract. Using basal-bolus alone as the comparator would be too weak, and
calling M2's incomplete PID subset a win would select successful cases.
This decision enables bounded interface development without asserting
superiority, novel clinical practice, patient safety or a frozen OT-019
assessment. Revisit the method if development exposes infeasible limits or
the strong comparator cannot be established; retain the failed attempts.
