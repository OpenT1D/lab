# C1/0.2 — Method selection and native feasibility

**OT-019 preparation, 25 September 2026.** This is a development artifact
under [C1/0.1](c1-controller-protocol.md), not the final evaluation freeze or
a controller-performance result. [Decision 0032](../decisions/0032-c1-causal-overlay.md)
records the selected method. The original M1/M2/IV/P1 source and evidence
remain unchanged.
The later [C1/0.5 revision](c1-method-revision.md) retires this method as
the lead after the complete known-case development matrix. This record and
its tested code remain historical evidence.

## Selected method

Choose a **causal, bounded glucose-trend overlay** on a frozen native basal
controller. The native reference computes its action using exactly the same
permitted observation and announcement history as before. The overlay may
increase its *basal infusion rate* when successive fresh observations show
a rise above a declared target. It never modifies a meal bolus, extrapolates
a masked sensor value or receives the true meal stream. It tracks its own
past extra commands as an explicit anti-stacking proxy and suppresses an
extra command at low glucose or when no fresh observation is available.
That proxy ignores native basal and meal bolus delivery and cannot establish
physiological insulin-on-board or safety.
The base action, overlay amount, clamp and final action must be separately
recorded in a future native run.

This is original OpenT1D control logic in its exact state/update and
cross-engine boundary, **not** a claim that unannounced-meal detection or
trend feedback is novel. Published work already explores [unannounced-meal
detection](https://pmc.ncbi.nlm.nih.gov/articles/PMC5876595/) and
[fully closed-loop control without meal announcements](https://pmc.ncbi.nlm.nih.gov/articles/PMC5647490/).
The latter reports the challenge of extra insulin after rising glucose and
possible hypoglycemia, motivating the explicit anti-stacking and low-glucose
gates. These sources do not validate our proposed numerical policy.

The next code unit is a simulator-independent, **unconfigured** state machine
that accepts only time, fresh/held glucose, the current base rate and
explicitly supplied engineering parameters. There are no built-in patient
doses, target or gains. Root tests can verify information flow, reset,
bounded action and missing-observation behavior without producing a clinical
or simulation efficacy result. An engine-specific adapter must translate
M1 U/min or LT1 U/h to a shared U/h calculation, then translate back, and
record delivery separately. The overlay must never receive the native
patient/solver object. The initial implementation is an interface preflight,
not an evaluated controller.
The subsequent [C1/0.3 simglucose development route](../c1-simglucose-development.md)
implements that native adapter and an adapted bounded PID on known M1 cases;
its example gains and local outputs do not freeze an evaluation.

## Why this method first

| Candidate | Causal two-track fit | Extra dependencies | Selection |
| --- | --- | --- | --- |
| Bounded trend overlay | Needs only released sensor history, own commands and a reference rate; preserves each native engine | No fitted model or training set | Selected for a small auditable first implementation. |
| New robust MPC | Requires a verified state estimator, model/solver and cross-engine mismatch plan; LT1 MPC already has numerical sensitivity | More numerical validation and tuning | Retain as a later candidate, not the first C1 method. |
| Learned/hybrid policy | Requires a data/rights and allocation contract that does not exist for insulin decisions | Training, distribution-shift and calibration evidence | Not selected. |

Selecting the simplest feasible method is not a prediction of superiority.
No coefficients may be chosen from the future evaluation. Record all
development attempts, including unsuccessful settings, before freezing.

## Comparator and integration audit

| Track | Existing native comparison | Verified constraint | Required work before a superiority test |
| --- | --- | --- | --- |
| simglucose | Native basal-bolus and PID, separate M1/M2 evidence | M2 fixed PID completed only 56/320 evaluation runs; M2 config, worker and reader admit only those two controllers and the fixed schedule | Preserve both anchors. Add and verify a bounded feedback comparator with the same causal inputs and declared tuning budget; establish adequate planned-case coverage. Build a separate C1 runner/reader for new controllers and scenarios. |
| LT1 Cambridge | Native PID and `MPC_Hovorka2004`, separate M2 evidence | Only one reference parameterization; MPC numerical sensitivity in IV-001. M2's controller boundary and reader are tied to A–D and the fixed meal schedule | Preserve both anchors. Verify an overlay wrapper around the native MPC without changing its predictor or the native simulator, and establish exact command/delivery provenance. Run the predeclared solver/replay stress; never infer population superiority. |

M2 run artifacts and hashes cannot be relabeled C1 results. Its Python and
Node validators reject new controller names or scenario rosters by design.
Changing them in place would invalidate historical M2 reconstruction. C1
therefore needs versioned workers, schemas and readers, reusing bounded
helpers where safe but preserving all historical references.

## Freeze boundary and next executable work

All M1/M2/P1/IV-001 cases are development-known. All ten available
simglucose adult profiles in the current native M2 roster have been used or
inspected, so a new seed or meal schedule tests **scenario transfer on known
virtual profiles**, not unseen physiology. Cambridge remains a singleton.

Before any C1 evaluation run, create a clean exact-commit freeze that names:
the chosen base reference and strong comparator per track; source/rights and
settings; candidate gains and action limits; a scenario roster disjoint from
inspected meal schedules; profile/seed streams; complete-case coverage
minimum; profile-level interval calculation; numerical refinement limits;
and the failure/verdict procedure in C1/0.1. The freeze must hash the actual
runner, adapters and analysis code after they are verified in development.
Until that package and a strong simglucose feedback comparator exist, the
selected method may be developed and checked but **no superiority claim or
held-out evaluation** is authorized by this preparation record.
