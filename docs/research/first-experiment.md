# First experiment protocol

**OT-001, version 1.0, 13 September 2026. Status: implemented as a bounded M1 development demonstration; the full held-out controller comparison has not been run.** The [M1 tutorial](../m1-tutorial.md) describes the implemented development subset. The native references and development feasibility checks are recorded in the [reproduction record](m0-reproduction.md). Software implementation, scientific interpretation and independent reproduction remain separate evidence questions.

This is the canonical protocol. Fixed first-engine settings are also recorded in [protocol-settings.json](../../experiments/m0/simglucose/protocol-settings.json); code and document changes must be reviewed together. The [roadmap](../../ROADMAP.md) owns the implementation sequence and [decision 0002](../decisions/0002-m0-reference-first.md) fixes the initial integration boundary.

## Question, use and evidence tracks

How does the relative behavior of reference insulin-control strategies change with meal information, sensor availability and physiological model choice?

The first user is a researcher verifying the laboratory's behavior and exploring sensitivity to assumptions. M1 establishes one controlled experiment; M2 tests structural model differences. This protocol does not support clinical superiority, dosing or device-control claims. Virtual profiles and sensor seeds are not sampled human participants.

Keep the native reproduction separate. M0 executes the original simglucose tutorial and LT1 Cambridge/MPC reference with their original controller information and numerical behavior. M1 introduces the announcement boundary specified below; it is a new experiment, not an unchanged upstream reference. No controller ranking from the two different native scenarios is meaningful.

## First-engine configuration

| Item | Fixed choice |
| --- | --- |
| Engine | simglucose `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`; isolated lock in the reproduction directory |
| Population | Adult virtual profiles; development `adult#001`–`adult#002`, evaluation `adult#003`–`adult#010` |
| Start and duration | Synthetic naive clock 2024-07-20 00:00; 48 hours, first 24 for initialization, second 24 scored |
| Meals | Each day: 07:00/45 g, 12:00/70 g, 16:00/15 g, 18:00/80 g, 23:00/10 g; encode both days explicitly |
| Devices and cadence | Native Dexcom and Insulet presets; native one-minute physiology, three-minute observation/action interval |
| Basal-bolus | Native formula, target 140 mg/dL, pinned Quest CR/CF and vpatient basal configuration; announcement input replaces true meal input in M1 |
| PID | Native formula with P=0.001, I=0.00001, D=0.001, target 140 mg/dL from the pinned upstream PID example |
| Initialization | Native patient/device initialization; native controller reset at run start only; preserve all state across the 24-hour boundary |
| Randomness | Sensor seeds 101–110 for development and 1–10 for evaluation; deterministic meals; pair profile and seed across conditions/controllers |

The schedule comes from the [native tutorial](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/examples/advanced_tutorial.py). Gains come from the [native PID example](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/examples/run_pid_controller.py). These are transparent reference settings, not optimized treatments. No gain tuning was performed and evaluation profiles remain unused.

The four native development cases reached 48 hours with finite outputs, but the PID on `adult#001` ended at approximately 46.35 mg/dL. A zero native stop-flag count does not imply absence of low glucose. The fixed 24-hour initialization period is an experimental convention, not demonstrated convergence to a periodic steady state. Preserve and expose startup transients, integral accumulation, clipping and low-glucose behavior. These simple references serve functional verification; broader performance claims need a stronger published comparator in M2.

The profile split and seed count bound the first study; they are not a power calculation. Do not select profiles or seeds after inspecting evaluation outcomes. Any subsequent change creates a new protocol revision and discloses prior evaluation reuse.

## Controller information and event order

At each control time `t`, use the observation from the just-completed native interval, or the native initial observation at the start. Deliver announcements whose announcement time is `t` once, then compute the command and advance native physiology over the next interval. True meal events remain with the engine; future meals and latent patient state never enter the controller's information object.

Allowed information consists of observation value, observation time and age, past commands/deliveries, announcements already delivered, and an explicit profile configuration. Both controllers may receive the same preconfigured basal, CR and CF values; their actual usage differs. Basal is computed from pinned `u2ss * BW / 6000` in U/min. These settings derive from virtual-profile assets and are not claimed to be measurable patient information. Neither controller receives the unrestricted upstream `info` dictionary.

For M1 basal-bolus, convert newly announced grams to `meal = announced_grams / 3` for the native formula's rate-shaped input and retain its native target/correction rule. This deliberately changes the native tutorial's use of the preceding interval's actual meal input. PID ignores meal announcements and retains its native zero integral/previous-observation reset. Do not add antiwindup, basal feed-forward or undocumented startup corrections to either reference.

Both output fields in simglucose are U/min. Preserve native pump clipping and quantization. A finite negative PID command is passed through the native pump's limiting behavior, not silently replaced by a different controller. Save commanded and modeled delivered insulin separately; require delivered insulin to remain finite and nonnegative.

## Conditions and missing observations

Apply perturbations only on the scored day; initialization uses condition A for each strategy.

| Condition | True meal schedule | Announcement at meal start | Sensor observations |
| --- | --- | --- | --- |
| A | Fixed | 100% of grams | Native |
| B | Same | None | Native |
| C | Same | 50% of grams | Native |
| D | Same | 100% of grams | Mask observation timestamps from 12:00 inclusive to 12:30 exclusive |

These are engineering stress cases, not estimated clinical event frequencies. There is no combined-fault or altered-noise-distribution condition in version 1.0.

For D, generate the native sensor values and advance its random state normally, then mask the controller-facing value. Hold the last available value, retain its original observation time and publish its age; PID's control clock and integral continue normally. Scheduled meal announcements still arrive once, including at noon. A held value must not duplicate or suppress an announcement. This is a specified simulation fallback, not a recommended device-safety behavior.

Keep raw generated sensor values, availability flags and controller-facing values distinct. Sensor exposure metrics use available observations, never the held substitute or latent glucose. The same named random streams are used across paired runs; differing physiology can still produce different sensor values.

## Outcomes and interval semantics

The primary descriptive outputs are paired changes in the percentage of valid recorded glucose intervals within **70–180 mg/dL inclusive** and below **70 mg/dL**. Always report the percentage below **54 mg/dL** alongside them. Secondary outputs are intervals above 180 and 250 mg/dL, weighted mean, population standard deviation, coefficient of variation, modeled delivered insulin, coverage, completion/failure counts and runtime. The cutpoints follow the [international CGM consensus](https://pmc.ncbi.nlm.nih.gov/articles/PMC6973648/); the sampling and simulation interpretation below are OpenT1D conventions.

For simglucose, label the main glucose metric **exposure of three-minute mean subcutaneous glucose**. It is not plasma glucose and thresholding interval means does not reconstruct actual time within a range inside those intervals. Sensor metrics are reported separately with the same sampling caveat. A future native-resolution metric requires a new documented output track.

A glucose row at time `t` after initialization describes the preceding three-minute interval. Score rows with `24 h < t <= 48 h`. Action rows describe the following interval: integrate rows with `24 h <= t < 48 h`, multiplying U/min by three minutes. Exclude the structurally empty terminal action cells. Initial point observations do not represent a preceding interval.

Weight observations by their represented duration. Compute weighted variance with denominator equal to valid duration, SD as its square root and CV as 100 × SD/mean. Report observed duration, scheduled duration and missing duration. A masked observation contributes no valid sensor duration; do not infer missing glucose from another signal. Invalid denominators are undefined outputs, not zeros. Do not pool incompatible compartments or sampling semantics across engines.

Aggregate seeds within each profile before giving profiles equal weight. Publish all profile-level paired changes and controller differences, with medians and ranges across profiles, including sign reversals. Seed variability characterizes simulator randomness, not confidence in human treatment effects. Do not declare an overall winner from a single composite score or a selected successful subset.

## Failures, verification and evaluation gate

Create a record for every scheduled run before execution. Fail on solver exception, nonfinite state/observation/action, invalid timing or unsupported input semantics. Stop M1 execution after a native terminal flag (`BG < 10` or `BG > 600` in the pinned environment), retaining the last completed interval and the flag reason. These extreme numerical flags are not the low/high-glucose outcome thresholds above. Record low-glucose exposure even when a run completes normally.

Preserve logs, warnings, partial outputs and completion coverage. Do not fill terminated tails. Show incomplete runs separately; compute paired complete-run comparisons only where both runs complete and list excluded pairs against the denominator of all scheduled runs. A differential failure rate limits interpretation of controller ranking.

Before M1 evaluation, require:

- Direct versus adapted replay with identical timestamps, events, native numeric values and status in the same locked environment. Start with exact equality; investigate discrepancies rather than relaxing tolerances to pass.
- Unit and amount-conservation fixtures, correct action/output interval alignment, native reset and random-stream tests.
- Tests proving no latent/future information leakage, once-only announcements, and continued native sensor generation during dropout.
- Independently calculable metric fixtures including threshold boundaries, missing intervals and partial runs.
- A fixed implementation revision, configurations, output schema and environment recorded before evaluating profiles 003–010.

The small observed Mac/Linux difference in the native simglucose reference is a diagnostic result, not a universal adapter tolerance. LT1 native results were exactly equal across those two platforms. No general cross-platform equivalence promise follows.

## Second family, data and interpretation

Use LT1 Cambridge `9a6092065bd821f88691cd8d03b0550acd665573` for the M2 structural case study. Its native reference has a different controller, meal announcement policy, plasma output and five-minute sampling. A same-index patient pairing is invalid; an adult cohort and matched controller configuration have not been established there. Keep separate cadence/compartment tracks until a justified comparison is implemented and documented.

The [data card](m0-data-fit.md) identifies DCLP3 for bounded CGM/insulin assessment, not complete meal replay. No human records are needed for M1's public synthetic workflow. Access, native dictionary verification, permitted outputs and external biological evaluation remain later requirements. Historical observational agreement alone does not establish an alternative controller's counterfactual effect.

The permitted result is reproducible simulated behavior under these explicit assumptions. Scientific domain review, a stronger controller comparator and independent researcher execution remain outstanding for broader claims. Neither the native probes nor the development cases validate a therapy.

## Changes

- Version 0.1, 2026-09-12: proposed scope, perturbations and unresolved execution gates, before numerical runs.
- Version 1.0, 2026-09-13: specified first-engine settings and event/metric/failure conventions using native reproduction and development-only feasibility evidence. Preserved the weak PID behavior without tuning. M1 implementation and evaluation remain pending.
