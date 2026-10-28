# M2 structural sensitivity protocol

**OT-014, version 1.0. Specified before M2 evaluation; implementation and acceptance status are tracked in the [M2 evidence record](m2-reproduction.md).** This is a separate protocol; [OT-001](first-experiment.md) and the M1 artifact interpretation remain unchanged. The [roadmap](../../ROADMAP.md) owns milestone acceptance and [decision 0004](../decisions/0004-m2-native-process-tracks.md) owns integration boundaries.

## Question and permitted conclusions

How do the direction and coverage of simulated responses to missing meal information and unavailable sensor observations depend on the complete engine/controller combination? Report within-engine paired changes and controller differences, then compare qualitative directions across separately labeled tracks. Do not pool glucose values, rank unmatched virtual populations, attribute complete-system differences solely to physiology or claim clinical superiority.

## Tracks and fixed settings

| Property | simglucose track | Cambridge track |
| --- | --- | --- |
| Engine | M1 pinned UVA/Padova 2008 lineage | LT1 `9a6092065bd821f88691cd8d03b0550acd665573`, Cambridge/Hovorka |
| Parameters | Upstream adult virtual profiles, existing asset provenance | Single IFAC reference Cambridge parameterization, Gpeq 124.91784824923789; native remaining defaults |
| Controllers | Existing native basal-bolus and PID; unchanged M1 settings | Native LT1 PID defaults; native MPC_Hovorka2004 with original IFAC reference settings |
| Controller provenance | M1 source and upstream examples | Same LT1 revision; MPC source cites [Hovorka et al., 2004](https://pubmed.ncbi.nlm.nih.gov/15382830/), “Nonlinear model predictive control of glucose concentration in subjects with type 1 diabetes”; implementation fidelity to every paper detail is not established |
| Sensors/pumps | Dexcom/Insulet, unchanged | IdealCGM, five-minute samples; StaticInsulinPump defaults |
| Clock | Synthetic naive 2024-07-20 midnight | UTC 2024-07-20 midnight |
| Steps | One-minute physiology, three-minute mean observations/actions | Native adaptive SolverRK1_2; one-minute outer maximum, shortened at events; PID/MPC five-minute updates |
| Main signal | Three-minute mean subcutaneous glucose | Point plasma Gp, duration-weighted left endpoint approximation |

MPC settings are copied from the pinned reference (including process/measurement noise, target 110, samplingTime 5 and kaggr 1000), not retuned after evaluation. Native PID defaults include target 120, basalRate 1, kP 0.5, kI 0.01 and kD 0. Unequal targets and controller assumptions remain visible: this is reference sensitivity, not an optimized head-to-head trial. The stronger published-method candidate is integrated only after numerical, information and lifecycle verification; broad performance claims remain outside this protocol.

## Development and evaluation gate

Development: simglucose adult#001–002, seeds 101–102, all four conditions; Cambridge's single reference parameterization, seed 101, all four conditions. No parameter search is planned. Preserve existing development failures.

Evaluation: simglucose adult#003–010, seeds 1–10, all four conditions and both controllers (640 planned runs). Cambridge has no verified held-out cohort or stochastic sensor in this track. Its eight controller/condition cases remain structural development demonstrations, not held-out physiological evaluation; repeated ideal-device seeds would be pseudoreplication. Do not invent parameter variants to fill that gap.

Before opening simglucose evaluation, freeze source revision, protocol hash, configurations, controller settings and analysis hashes in an evaluation plan, after all applicable development/equivalence checks pass. Do not change settings based on evaluation. If a correction requires rerunning inspected cases, retain the first results and label the later execution evaluation reuse. A complete M2 report must state separately which evidence is held out and which is not.

## Meals, information and initialization

Use the same intended two-day meal schedule as OT-001: daily 07:00/45 g, 12:00/70 g, 16:00/15 g, 18:00/80 g and 23:00/10 g. Encode both days. Cambridge ingests each meal over 15 minutes, matching the native MPC predictor's assumed ingestion duration; simglucose preserves its own native absorption/ingestion semantics. This difference is not hidden by equal meal totals.

Run 48 hours; retain the first 24 hours as initialization, score the second 24. Native reset occurs once per run, including controller, solver and component streams; no reset at scoring. Initialization is a fixed convention, not established steady-state convergence.

Condition A announces 100% at meal start; B announces nothing on the scored day; C announces 50%; D announces 100% but masks sensor timestamps from scored-day 12:00 inclusive to 12:30 exclusive. Initialization always uses A. Meals themselves are unchanged. Record true intake, newly announced information, retained controller history, raw samples, observation availability and held-observation age independently. Generate native sensors normally before masking. Never pass hidden state or unrestricted native objects. Native MPC may keep already announced meals to propagate its private predictor; it cannot see later unannounced meals. Controllers may use their fixed, recorded profile parameters and own history only.

## Metrics, comparisons and failure policy

Keep M1 `ot001-exposure/1` unchanged. Cambridge receives a new metric identifier `ot014-plasma-point/1`: weight the left endpoint Gp by each completed interval's duration overlapping minutes 1440–2880. Thresholds are 70–180 inclusive, below 70 and 54, above 180 and 250 mg/dL. Also report weighted mean, population SD, CV, modeled delivered U, observed/scheduled duration and status. These are quadrature summaries of point samples, not measured continuous exposure. Sensor metrics use only available sampled values and their explicit represented intervals; never substitute latent glucose or held controller data for missing sensor data. Undefined denominators and entirely unobserved insulin duration produce null, not zero.

For each condition/controller report planned, attempted, complete, failed and interrupted counts, coverage and every exclusion. Pair only complete runs with matching within-track profile/seed. Aggregate seeds within profile before equal profile weights; show seed ranges, profile medians/ranges, paired condition changes and controller differences. Report positive, negative and zero changes and rank/sign reversals; with fewer than two usable profiles, between-profile reversal is unassessable. Cambridge has one deterministic parameterization: no cohort uncertainty interval is estimable. Cross-track direction differences are descriptive complete-system sensitivity only.

Record every scheduled run before execution. Preserve native terminations, errors, diagnostics and partial traces; no filled tails or removal of failed cases. Nonfinite required signals, internal states, negative modeled delivery, invalid units/times, unsupported combinations and initialization failures stop the run. A full-looking trace does not imply successful completion. Timeout or interruption retains completed checkpoints; hard kills remain visibly unfinished. No arbitrary numerical tolerance or baseline enrollment is allowed.

## Verification and independent execution

Required gates: direct versus adapted native equality; native reset and fresh-process equality; unchanged historical M0/M1 references; independent unit/duration fixtures; event ordering and once-only delivery; masking after sensor generation; supported-combination rejection; finite internal state; partial/failure/timeout retention; complete provenance and byte-identified reconstruction without simulation. Preserve selected evidence outside Git with verified inventories.

Prepare a canonical tutorial, exact commit and environment requirements, expected artifacts, checks and a result-recording template for another person. Another subprocess, CI job or AI session is not independent human reproduction. Until another person executes and records their result, this M2 criterion stays open. Parameter rights, external biological validation and patient-data access are not supplied by this experiment.
