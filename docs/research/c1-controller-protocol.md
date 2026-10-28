# C1/0.1 — Original controller study design

**OT-018, design protocol, 25 September 2026.** This document selects a
falsifiable question and the comparison rules for OT-019. It is **not** an
evaluation freeze, an implemented controller or a result. The [roadmap](../../ROADMAP.md#c1--first-original-opent1d-controller)
owns acceptance; [decision 0031](../decisions/0031-c1-missing-meal-study.md)
records the study choice. M1, M2, IV-001 and P1 remain unchanged.
The subsequent [C1/0.2 method record](c1-method-feasibility.md) selects one
development method without freezing or evaluating it.

## One question and one estimand

**Hypothesis:** On a scored day with real meals but no meal announcements, a
new causal OpenT1D controller can increase modeled glucose exposure in
70–180 mg/dL relative to the strongest eligible, equivalently informed
reference controller in each supported engine track, without increasing
modeled exposure below 70 or 54 mg/dL, extreme high exposure, or native stops.
Condition B of [M2](m2-protocol.md) motivates this question; its observed
results are development evidence, not evidence for this new hypothesis.

The primary comparison is a *paired, within-track, scored-day* difference in
the existing 70–180 mg/dL exposure percentage (new controller minus the
eligible comparator) under missing scored-day announcements. Pair only the
same engine, virtual profile/parameterization and scenario, using the same
stochastic sensor realization; observed glucose may differ when actions
change.
Use M1 `ot001-exposure/1` for simglucose mean subcutaneous intervals and M2
`ot014-plasma-point/1` for Cambridge plasma points. These are different
modeled signals, so never pool their values or estimate a common effect.
The 70/180, 54 and 250 mg/dL bins retain the [M2 definitions](m2-protocol.md#metrics-comparisons-and-failure-policy)
and align with the [international CGM reporting consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC6973648/);
the simulated scores are not personal clinical targets or measured CGM time.

No method, architecture, parameter set or gain is selected here. Success is
falsified by absent primary gain, a failed non-degradation gate, insufficient
comparison coverage, or unresolved numerical sensitivity. A result may be
negative or inconclusive. This protocol does not claim a causal physiological
mechanism, human benefit or a device-ready insulin policy.

## Reference and candidate assessment

| Option | Role and ancestry | Fit to this question | Limitation / decision before OT-019 |
| --- | --- | --- | --- |
| M1 native basal-bolus | Fixed upstream simglucose reference, with original settings | Meal-aware anchor; documents the cost of lost announcements | Cannot be the only strong comparator against a feedback method; keep unchanged as a historical anchor. |
| M1 native PID | Fixed upstream simglucose feedback reference | Uses observed glucose and no hidden meal truth | M2's PID stopped in 264/320 evaluation runs; a complete-case win would be selected. Require explicit coverage and a feasible stronger feedback comparison. |
| LT1 native PID | Fixed LT1 reference | Simple feedback anchor on the Cambridge track | Different signal, target and action cadence from M1 PID; no cross-engine equivalence implied. |
| LT1 `MPC_Hovorka2004` | Pinned LT1 implementation of a published method, [Hovorka et al.](https://pubmed.ncbi.nlm.nih.gov/15382830/) | Required strong Cambridge reference, alongside PID | The paper studied fasting control; the implementation's fidelity to every paper detail is unverified. M2/IV-001 found numerical sensitivity and only one Cambridge parameterization. |
| Bounded feedback plus a causal disturbance estimate | Candidate family, original logic would require a source/ancestry record | Could respond to unannounced meals using only observed history | Estimation lag, insulin stacking and missing-observation behavior must be checked; no architecture chosen. |
| Robust/constrained predictive controller | Candidate family; distinguish original contribution from inherited equations or solvers | Could optimize the specified trade-offs explicitly | Requires state estimation, limits and numerical checks; a native MPC label alone is not originality. |
| Learned or hybrid policy | Candidate family; any training data and model license must be recorded | Could exploit histories if allowed data exist | No verified training set, transfer evidence or safe out-of-distribution behavior exists; not selected by default. |

Before implementation, record a source/license and configuration card for each
retained implementation and state the exact original contribution. Compare
the candidate families on causal fit, feasible two-track interface, failure
behavior, computational budget and reproducible tuning. Select one method in
an OT-019 amendment *before* coding and scoring it. Keep fixed native
references as historical anchors. For a superiority comparison, give eligible
tunable references the same declared development cases, information, tuning
opportunities and evaluation budget as the new method. If a strong comparable
reference cannot be implemented or verified, report the track as an
integration demonstration rather than claiming superiority over a weak one.

## Causal information and action contract

At time *t*, the controller may receive only the latest released sensor
observation and its timestamp/availability, its own previous observations,
announcements and actions, elapsed time, and explicitly frozen profile
configuration. An announcement is visible only when M2 releases it at the
meal event; the true meal stream, future events, latent glucose, solver state
and native patient object stay private. Condition A provides full
announcements; B provides none on the scored day; C provides half; D provides
full announcements but masks the scored-day 12:00–12:30 sensor window.
Initialization remains M2's native reset plus 24-hour A history, followed by
a 24-hour scored day without another reset. An implementation must declare
whether it retains observation age and any announced-meal history.

Use a shared causal decision interface but preserve engine-specific adapters:
M1's three-minute mean subcutaneous observation and insulin command in U/min;
LT1's five-minute IdealCGM/plasma-point observation and command in U/h.
Record command and modeled delivered insulin separately, with native pump and
event timing unchanged. Declare action range, rate change limits, basal
fallback, internal state initialization, and behavior for missing, delayed or
nonfinite observations before running a candidate. A missing sensor interval
must not silently become a zero glucose reading or a peek at latent glucose.
Reject unsupported controller/engine combinations. No physical pump or pen
interface is in scope.

## Outcomes and decision rule

The scored-day primary difference is evaluated against the *strongest
eligible comparator* selected by the frozen development procedure in each
track, not the weakest reference after results are seen. OT-019 must name
that comparator and its eligibility/selection rule before evaluation access;
every native anchor is reported separately even when ineligible for a
superiority claim. The simglucose point estimate is the equal-profile mean
of within-profile paired seed means; Cambridge has one paired value. The
following zero-margin rules are **study decision
constraints**, not clinical safety guarantees or empirical precision claims:

| Gate | Required paired scored-day result |
| --- | --- |
| Primary B benefit | Difference in 70–180 exposure is positive. For a multi-profile simglucose evaluation, its predeclared profile-level 95% interval must exclude zero on the positive side. |
| B low exposure | Differences in exposure below 70 and below 54 mg/dL are each at most 0 percentage points; report individual profile deteriorations even when aggregate passes. |
| B high extreme | Difference in exposure above 250 mg/dL is at most 0 percentage points; also report above 180 and mean glucose without substituting them for the primary outcome. |
| A preservation | With full announcements, 70–180 exposure must not decrease and below-70/below-54 exposure must not increase. C and D are prespecified stress outcomes, not silently added to the primary claim. |
| Delivery and stopping | No additional native stop or invalid action versus the comparator on paired planned cases; report insulin totals, maxima and action-limit events. Missing coverage cannot be scored as success. |

Compute every difference per complete matched case. Report all planned cases,
attempts, partial scored intervals, failures, stops and exclusions before the
complete-case summary; compare stop rates on the planned denominator. The
95% interval method, profile weighting, multiplicity treatment and exact
required coverage fraction must be frozen in OT-019 before evaluation access.
Cambridge's single parameterization cannot yield a population interval or
meet a multi-profile superiority claim; its paired result is descriptive.
If a zero-margin rule is not estimable because of coverage or uncertainty,
the verdict is **inconclusive**, not a pass. A positive point estimate alone
does not override a failed gate.

## Development, freeze and evaluation boundary

All inspected M1/M2/P1 and IV-001 trajectories, profiles, seeds, native
initialization variants and robustness outcomes are known development
material. The M2 640-case simglucose evaluation and eight Cambridge cases
are **not** an untouched C1 test. Development may use them to check
feasibility and choose one method, but record every tuning attempt and keep
the original M2/IV results intact. Do not present a new seed of the same
profile as a new physiological population.

The OT-019 freeze must be committed and hash-identify code, upstream locks,
method and reference settings, action/fallback rules, exact scenario roster,
profile/parameter roster, seed allocation, analysis, uncertainty method,
coverage requirement, numerical tolerances and evidence inventory **before**
opening new evaluation outputs. Predeclare scenario-disjoint meal timing and
size variants and announcement/sensor conditions, with independent random
streams where relevant. Test every selected scenario with both candidate and
eligible references on the same native track. The roster must say which
profiles have already been inspected: new scenario cases on known profiles
can test scenario transfer, never new-person generalization. Cambridge's
singleton remains a structural stress test unless a separately verified
population becomes available; do not manufacture independent subjects by
perturbing its parameters. No human data are needed for this bounded
simulation design, and none are supplied by it.

Run clean native/reference equivalence and fresh-process repeats before
evaluation. On held-out cases, preserve all terminal flags and partial
traces; never impute a successful tail, replace a failed reference, or tune
after inspecting outcomes. Report distributions and paired sign reversals by
profile and condition; show uncertainty at the profile level rather than
treating timestamps or seeds as independent people. For Cambridge MPC,
compare nominal feedback and fixed-action replay under the IV-001 solver
refinement settings and record whether the proposed benefit changes sign or
exceeds the prespecified numerical scale. Initialization sensitivity requires
a separately declared stress analysis. If a numerical or lifecycle defect
requires correction after inspection, retain the first evaluation and label
the rerun as reuse; a fresh assessment requires genuinely reserved material.
Reconstruct the complete report from hash-checked artifacts without either
simulator. Preserve unsupported or incomplete comparisons in the verdict.

## Next executable gate

OT-019 begins with a feasibility and freeze package: choose one candidate
method after the assessment above, establish matched-information strong
comparators on both tracks, verify action/observation adapters and fallbacks,
and seal the exact new scenario roster plus statistical/numerical criteria.
Only then implement/tune on declared development cases and evaluate on the
sealed roster. If strong comparison or adequate coverage fails, keep the
software experiment as exploratory and revise the protocol *before* a new
evaluation. C1 acceptance and superiority remain open.
