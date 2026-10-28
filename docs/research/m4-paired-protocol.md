# BC-004: paired insulin/C-peptide boundary and measurement protocol

Version BC-004/1, 20 September 2026, based on `166da30` in the existing isolated beta-cell worktree. The [machine protocol](../../experiments/m4/paired_observation/protocol.json) is specified before implementation and execution. It freezes a **synthetic interface verification**, not an empirical study. The conditional human assessment below requires an actual permitted data release, assay information and domain review before an empirical protocol can be frozen. [Decision 0020](../decisions/0020-paired-observation-contract.md) records the boundary.

## Question and allowed result

Can one declared secretion signal produce consistent insulin and C-peptide inlet requests, with explicit scaling, baseline, time, initial inventories and ownership? The deliverable is an executable boundary preflight and reviewed source/measurement specification. It constructs inputs and proposed initial states, checks accounting and stationary balances, and records unsupported downstream operations. It does not execute a paired kinetic trajectory or full glucose feedback.

The intended later empirical question is paired concentration prediction during a defined challenge in residual-function T1D. Transplant cohorts form a separate population and protocol. No human parameter is fitted here. No information about functional capacity is converted into a cell count, graft survival or treatment effect.

## Source decisions and unresolved assumptions

| Decision | Evidence or explicit assumption | Consequence |
| --- | --- | --- |
| One molar insulin secretion produces one molar C-peptide appearance | Working approximation grounded in Polonsky 1986 pp. 98–99; applicable population/processing still requires review | Ratio fixed at 1 for this contract; this is a rate ratio, not a plasma concentration ratio |
| Insulin enters the liver compartment | Original Dalla Man insulin balance and the verified BC-002 route | No additional first-pass fraction; the insulin module owns hepatic removal |
| C-peptide enters its central compartment | Polonsky process scheme; no significant hepatic extraction in the source's interpretation | Do not apply insulin clearance, SC absorption or a second hepatic fraction to C-peptide |
| Body mass and mass-to-mole conversion | BC-002 virtual `adult#001`, 102.32 kg; human-insulin rounded molar mass 5808 g/mol | Normalize both branches exactly once; reject a mismatched insulin-profile body mass |
| Kinetic profiles | Fixed BC-002 native insulin coefficients and BC-003 nominal T1D C-peptide coefficients | An intentionally synthetic combination, not two models fitted to the same participant |
| Basal release | Zero increment for the primary contract; one separately named synthetic basal fixture | Do not infer endogenous basal release from a pump rate, BC-001 mobilization parameter or a single fasting C-peptide value |
| BC-001 scale and initialization | Unresolved source discrepancies in its existing dossier | No automatic BC-001 import or claim that its illustrated pool mass is whole-body secretion |

Primary sources: [Polonsky et al. 1986, DOI 10.1172/JCI112308](https://www.jci.org/articles/view/112308/files/pdf), [Dalla Man et al. 2007, DOI 10.1109/TBME.2007.893506](https://doi.org/10.1109/TBME.2007.893506) and the [BC-002 exact source/parameter assessment](m4-kinetic-boundary.md). The original C-peptide experiments subtracted pre-infusion baseline under their stated experimental conditions. That does not justify indiscriminate subtraction during a glucose challenge whose secretion baseline or clearance may change.

## Input and process contract

Time is elapsed minutes from the declared stimulus origin. A finite piecewise-linear evoked rate is supplied as whole-body **pmol/min** or **ug/min**, never U/h, plasma concentration or a per-kg rate relabeled as whole-body. Segment endpoint values preserve jumps; no extrapolation or invented interpolation of missing measurements occurs. Basal secretion is a separate constant in pmol/min, never included twice in an evoked trace.

```text
S_evoked_pmol_min = S_evoked_ug_min * 1e6 / 5808   (mass input only)
S_total_pmol_min  = S_basal_pmol_min + S_evoked_pmol_min
q_insulin_liver   = S_total_pmol_min / BW_kg
q_cpeptide       = 1 * S_total_pmol_min / BW_kg
```

Both rates are pmol/(kg min). Equality refers to the imposed appearance rates and their integrals. Plasma insulin and C-peptide concentrations must **not** be equated because distribution volumes and clearance differ. Insulin owns liver/plasma distribution and its two irreversible losses. C-peptide owns its central/peripheral distribution and central loss. Exogenous insulin remains a separate pharmaceutical input; it generates no C-peptide in this contract. SC delivery and transplant-specific delays are outside the paired preflight.

`incremental_zero` requires basal input zero and both branches' initial incremental inventories zero. Outputs would represent increments above an independently specified background, not total fasting concentrations. `synthetic_equilibrium` declares a constant basal rate and stationary initial inventories:

```text
Il0 = q_b / [m30 + m1*m4/(m2+m4)]
Ip0 = m1*Il0/(m2+m4)
Q1_0 = q_b/K3
Q2_0 = (K1/K2)*Q1_0
```

All inventories are pmol/kg. Each branch's loss and input ledgers start at zero; subsequent conservation must include its initial inventory. Basal insulin concentration would be `Ip0/Vi`, C-peptide `Q1_0/Vp`. These equilibrium identities assume fixed linear kinetics, the stated route, constant basal input and no exogenous insulin. They are not a physiological steady state of the complete glucose system.

The preflight only accepts evoked forcing starting at zero in the equilibrium mode, so the stated initial state is stationary at the origin. A later step is explicit in the input. The insulin route is fixed to liver; changes in site, processing ratio, delay or extraction require another versioned contract rather than extra silent parameters.

## Frozen verification cases and criteria

The four cases are zero increment, a 9 pmol/(kg min) extra pulse from 10–30 minutes over a 240-minute horizon, that same pulse above a synthetic 1.5 pmol/(kg min) baseline, and a 60-minute whole-body mass ramp from 0 to 5.808 ug/min. The baseline is 153.48 pmol/min at the declared 102.32 kg; it is an engineering example. Expected integrated amounts per branch are respectively 0, 180, 540 and `30000/102.32 = 293.1978107896794` pmol/kg.

Require paired-rate and analytic-integral relative discrepancies at most 1e-12 (absolute comparison to zero), initial equilibrium derivative residuals at most 1e-10 pmol/(kg min), and deterministic repeated output equality. The independent expected amounts come from pulse/triangle areas, not copied computed output. Check invalid units, unknown fields, baseline/scale omissions, nonfinite or negative values, body-mass mismatch, ambiguous source semantics, unsupported ratio/route and nonstationary starts. No solver tolerance or clinical performance criterion is implied: no ODE is integrated in BC-004.

The error denominator is `max(1, abs(reference))` in the stated units, so zero and small anchors use an absolute tolerance. This convention is for boundary arithmetic only; it is not an assay-error model.

Freeze input/protocol hashes, source files, reused forcing source and root runtime lock with each run. Preserve failed attempts; refuse to overwrite output. Reconstruct the preflight from archived configuration using only standard-library code, without importing an engine or executing archived Python. [Execution and commands](m4-paired-results.md) record actual outcomes.

## Concrete downstream implementation boundary

BC-002's `native.simulate` currently hardcodes zero incremental initial state. Consequently only the incremental bundle matches its existing initial-state contract. A synthetic-total bundle is a **proposal**, not a drop-in supported BC-002 execution. Before total paired execution, extend a new wrapper to accept nonzero kinetic initial inventories, preserve native negative-state guards, update conservation to include initial inventory and prove zero/incremental regression equivalence. Keep the native package and historical protocols unchanged.

BC-003 already accepts explicit central/peripheral initial amounts. Both branches can consume the unchanged finite `Forcing` representation, but their pinned scientific runtimes remain separate. A future paired runner should orchestrate them through versioned artifacts and compare to independent constant-forcing solutions; it must not install a simulation package into the root tooling environment. Validate exact source pins, units, initial states, communication refinement and failures before reporting concentration trajectories. A shared source is not a shared clearance module.

## Conditional measurement and analysis freeze

The [canonical measurement inventory](m4-cpeptide-measurements.md) remains authoritative. For an actual release, build one visit-level record with permitted pseudonymous participant/visit identifiers, stimulus origin and route, body mass, fasting/treatment history, renal information, assay identity, and separate sample records per analyte. Preserve actual sample time, specimen matrix, original value/unit, assay batch, LOD/LLOQ and flags. Link analytes by a declared collection event where possible; do not silently pair nearest timestamps or mix plasma, serum and CGM. The eventual protocol must declare an assay/source-justified pairing tolerance and allowable missingness before evaluation.

Record missing, below-detection, below-quantification and measured values as distinct states. Do not substitute zero, half a limit or an interpolated concentration by default. Baseline-adjusted observations can be negative because of measurement variation; retain that information separately from nonnegative physical secretion. Select a censoring/noise likelihood using assay metadata, preserve baseline uncertainty and predefine exclusions. No patient import, censoring estimator or inverse secretion algorithm is implemented by this preparation.

The first human freeze must name the dataset/release and permitted purpose, specify participant-level development/evaluation allocation with visits grouped by participant, reserve evaluation before model selection, and record kinetic parameters kept fixed versus estimated. Fixing population kinetics is an assumption, not identified clearance. Do not simultaneously estimate unrestricted secretion, volume, all clearance rates and functional capacity from one concentration series. BC-003's unknown dose/volume ambiguity and BC-001's amplitude confounding still apply.

Primary proposed outcome: held-out C-peptide concentration error at actual sample times, reported per participant with assay-informed uncertainty and missing/censored counts. Secondary outcomes: insulin concentration agreement when exogenous insulin and assay cross-reactivity can be accounted for, and paired residual/time-integral summaries over observed support. Compare identical input/baseline assumptions against the prespecified simpler kinetic model. Numeric empirical thresholds, sample-size/power calculations and a clinical superiority claim remain unfrozen until the target population, release and assay support them. No refitting after inspecting the reserved evaluation outcomes.

## Feasibility verdict and review handoff

No currently assessed source is an authorized ready-to-run paired human validation dataset. The [updated source assessment](m4-cpeptide-measurements.md#paired-protocol-source-check) records why. The present contract can therefore be completed and numerically checked as a synthetic preparation, while the empirical freeze remains open.

The [unsent review brief](m4-collaboration-brief.md#paired-boundary-review-packet) asks named disciplines to assess these specific decisions. It does not claim completed review. Reviewer identity, expertise, date, assessed artifact hashes, population/claim scope, findings and resulting changes must be recorded when review actually occurs. Contact, access applications and restricted data downloads still require separate user authorization. Full OT-026 and OT-027 acceptance are unchanged.
