# M4-STUDY/2 — Configurable initial gastric-load study

**Status:** Version 1 frozen before implementation; version 2 freezes the
explicit coarse-solver refinement before new execution,
3 October 2026. This is a bounded synthetic software protocol, not a human
or therapy study. [Decision 0058](../decisions/0058-configurable-study-and-local-research-tools.md)
and [OT-032](roadmap-history-2026-10-28.md#functional-development-after-ot-031) own its scope.

## Question and frozen choices

How does descriptive separation between the same frozen secretion sources
change across predeclared synthetic initial gastric loads?

The supported loads are **0, 15 and 30 grams**. Zero and 30 grams reproduce
the conditions of BC-008 and M4-COMPARISON/1; 15 grams is the midpoint chosen
before observing new trajectories. A configuration selects a nonempty subset
in declared order and freezes its source roster and execution budgets. The
internal acceptance configuration includes all three and the existing Dalla
Man adapter and ultradian response component, without parameter fitting.

Use adult#001 and the pinned simglucose route, its existing native parameters,
25% engineering basal replacement, unchanged plasma insulin, adjusted liver
inventory and SC depots, unchanged secretion/portal initialization and fixed
SC input. A load initializes gastric solid mass and last_Qsto at time zero;
last_foodtaken is zero and native Action.CHO stays zero throughout. It is not
an announced meal, dose recommendation or event scheduler.

Retain minutes, glucose mg/dL, plasma insulin pmol/L, secretion pmol/(kg min)
and the observer's inlet pmol/(kg min), amounts pmol/kg and volume L/kg,
giving concentration pmol/L without a second body-weight conversion. Retain
240 minutes and the full 961-point grid from 0 through 240 at 0.25 minutes.
The one-state M4-CAUSAL/1 local source boundary and parameter/declaration
identities remain authoritative. Callback purity and rights are attestations,
not independently established safety or scientific claims.

## Numerical execution and controls

For every selected load generate its own native/no-extension diagnostic,
active BC-008 feedback reference and constant-basal coupled control. Reuse the frozen equations through separate
new wrappers and preserve complete native, source, portal and mass-ledger
trajectories. A reference from a different load is incompatible. Both sources
receive exactly identical initial/input conditions and controls.

Evaluate coarse RK45 (rtol 1e-7, atol 1e-9, max step 0.25 min), tight RK45
(1e-9, 1e-11, 0.125 min) and reference DOP853 (1e-11, 1e-13, 0.0625 min).
The inherited BC-008/causal glucose and insulin solver tolerances are
0.01 mg/dL and 0.01 pmol/L. Preserve inherited source refinement, positivity,
glucose-envelope, flux-conservation and passive observer criteria with their
own units; the machine-readable new protocol must declare all checks before
execution. Observer calculations stay in their separate existing lock.
Compare every sample and check exact complete grid coverage; a scalar endpoint
or a shortened successful prefix is insufficient.

Verify zero-extension/native agreement, matched basal controls, the source
boundary and independent insulin/glucose inventory balance. Retain numerical
refinement and C-peptide reconstruction evidence for each source/load. Perform
fresh-process repeats with exact archived trajectory agreement. Historical
0/30-gram parity compares unchanged old-route tight/reference and observer
trajectories against the new route under identical settings. The refined coarse
setting has no byte-parity claim against the original 0.5-minute setting. A failure remains in the
full source/load matrix; failed controls invalidate its dependent comparison.

## Outcomes and acceptance

Save complete glucose, plasma insulin, source/arrival, source state, portal,
native states and mass ledgers, plus passive C-peptide trajectories. Show
per-source/load numerical status and complete planned denominators. Report
source-pair left-minus-right signed trapezoidal AUC, signed time mean
(AUC/240 minutes) and maximum absolute pointwise difference for G/I/C-peptide
only when both sources pass their full selected-load matrix and fresh-process
repeats, all sample times match and common controls
agree exactly. Keep unsupported contrasts null with an explicit reason.
Changes across loads remain separate descriptive contrasts, never a pooled
source-quality score. No effect direction, magnitude or winning source is
required for acceptance.

Freeze configuration, source/declaration/parameter identities, protocol,
implementation inventory and runtime/lock identities before callback execution.
Own worker processes with finite stage and study budgets; terminate and reap
on failure, deadline or interruption. Retain diagnostic prefixes and all
failed/unattempted cells without clipping, dropping or relabelling them.
Use fresh output directories and never rewrite a historical archive.

Reconstruct JSON, readable report and trajectory figure from the archived
inputs/outputs with the standard library, without a numerical environment,
original external source path, callback execution or new simulation. Verify
identities and semantic consistency; exact reconstruction is evidence of the
archive/report relationship, not independent model validity. Explicit failed
archive reconstruction retains failed status.

Internal acceptance requires both existing sources, all three loads, old-case
parity, full numerical gates, exact repeats and reconstruction, invalid config,
failed source, deadline/interruption cleanup and repository checks. Record
commands, revisions, hashes, outcomes and limits in a separate dated evidence
record. Do not change tolerances in response to results without a new protocol.

## Source and limits

This reuses [BC-008](m4-feedback-protocol.md),
[M4-CAUSAL/1](../m4-causal-secretion.md),
[M4-RESEARCHER/1](../m4-researcher-workflow.md) and
[M4-COMPARISON/1](m4-source-comparison-protocol.md), including their source
attribution, basal engineering assumptions and missing direct portal action.
The ultradian component remains an isolated stateless sigmoid response, not a
reproduction of the complete ultradian engine. No new source citation, model
mechanism, human capacity, empirical fit or treatment effect is introduced.

## Versioned numerical refinement

The independent 15-gram development probe after the version 1 freeze found
coarse source error **1.350865261140477e-5 pmol/(kg min)** for BC-008 and the
Dalla Man adapter, exceeding the new 1e-5 limit. Tight source error was
6.208233238602645e-8; glucose and insulin errors passed. The retained
[probe receipt](../../experiments/integration/ot032-midpoint-v1-probe.json)
and literal command source preserve this failed check. It used unchanged pure
integrators before the complete new executor existed and is not final study
acceptance evidence.

Version 2 halves only the new coarse maximum step from 0.5 to 0.25 minutes
before further execution. Method, tolerances, all acceptance limits, source
parameters, physiology, tight/reference settings and numerical locks stay
unchanged. The exact previous [machine protocol](../../experiments/m4/initial_load/protocol-v1.json)
is retained. This numerical refinement does not make the failed version 1
probe pass retroactively; version 2 needs its own verification.
