# 0055 — Prioritize task entry and bounded M3 model comparison

**Status:** Accepted, 2 October 2026. OT-029 and OT-030 are implemented and
internally verified; the [execution record](../research/ot029-ot030-verification.md)
binds their bounded acceptance. External evidence requirements remain open.

## Context

The [combined execution record](../research/researcher-workflow-integration.md)
completes the bounded M3 forecast, M4 secretion/C-peptide and M5 prognostic
researcher increments. P1's local controller route is also internally
verified. The entry-page status and task navigation lag those capabilities;
commands, runtime setup and report discovery differ across the four routes.
These differences come from source/document inspection, not an independent
usability study. The requested follow-up prioritizes improving task entry and
comparing multiple models within a fixed task.

The existing M3 researcher reader verifies the exact source inventory,
including every Python file in its package. An additive file there can
invalidate old archives under a later checkout. P1's external preflight
executes supplied code, so it cannot silently become a metadata-only check.

## Decision

Refine [decision 0045](0045-tool-first-research-platform.md) through the
[roadmap's OT-028–030 packages](../../ROADMAP.md#post-integration-internal-work-packages).
First correct canonical status/navigation. Next add one checkout-based entry
for the existing controller, forecast, secretion and prognosis tasks. Use an
explicit task registry and delegate execution/reconstruction to their current
runners and contracts. Keep numerical locks separate and keep original
commands available. Put new entry/coordinator code outside source-hashed
historical packages.

Distinguish metadata/runtime validation from an explicitly requested smoke
or model run. Metadata checking must not import researcher code. Preserve
fresh-output refusal, failure archives, process ownership, route-specific
budgets, source requirements and report locations. State runtime/setup
requirements rather than installing dependencies or activating human-data
routes implicitly. This entry does not define a universal model schema,
public package release or cross-engine score.

Start multiple-model comparison with the existing synthetic M3 forecast task.
Before implementation, freeze a new versioned protocol for at least two
candidate declarations, source/settings identities, one observation/roster/
origin identity, execution budgets and analysis/support rules. Reuse unchanged
single-candidate execution. Keep causal history, persistence, eligibility,
participant weighting, failures and reconstruction limits explicit.

Show each candidate's planned denominator, coverage and paired persistence
comparison. A direct candidate comparison must use the same people and
origins, recomputing eligibility on that common support itself. Require
complete workers and the inherited 288-window/24-hour floor per contributing
person; show common-support losses and null metrics when empty.
Do not rank errors on unmatched subsets, refit on evaluation observations or
select a winner automatically. Preserve individual archives and reconstruct
the combined report without model execution or original observations. The
new protocol owns its source/provenance; existing protocols and results keep
their original meanings. Broader M4/M5 comparison needs its own task decision.

## Alternatives

- Keep separate entry points only: retains unnecessary task-discovery and
  setup differences after the supported routes already exist.
- Build a general plugin API now: adds compatibility promises unsupported by
  the current task contracts.
- Compare all workflows in one ranking: combines different units, endpoints
  and evidence contexts without a valid common research question.

## Consequences and revisit conditions

Verify task discovery, validation, representative execution/reconstruction
and retained failures for the entry. Verify unequal/empty support, mismatched
inputs, two predictor structures, repeats and artifact-only reconstruction
for the separate M3 comparison. The roadmap owns detailed acceptance/order.

Independent P1 usability and M2 reproduction remain external acceptance
steps. M3–M5 human/biological assessment remains separate; these internal
packages require no new patient dataset. Revisit the registry or comparison
scope when a concrete researcher model needs another runtime, state contract,
observation boundary or empirical study. No such extension is implemented by
this planning decision.
