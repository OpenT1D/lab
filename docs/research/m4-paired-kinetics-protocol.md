# BC-005: paired insulin and C-peptide kinetic execution

BC-005/1 is specified on 20 September 2026 before implementation/outcome inspection, based on `c9008d8` in the isolated beta-cell worktree. The [machine protocol](../../experiments/m4/paired_kinetics/protocol.json) fixes source identity, cases, solver settings and criteria. It executes the synthetic [BC-004 boundary](m4-paired-protocol.md), without changing BC-001/002/003/004 or their evidence records. [Decision 0021](../decisions/0021-paired-kinetic-execution.md) defines orchestration across the existing scientific environments.

## Question and permitted conclusions

Can one declared molar secretion input drive the two kinetic branches reproducibly, including nonzero basal inventories, while preserving native insulin behavior and agreeing with independent calculations? Paired means two concentration outputs driven by one prescribed input. There is no feedback between the branches, computed glucose, new secretion model, patient fit or therapy mechanism.

The source basis remains [Dalla Man et al. 2007](https://doi.org/10.1109/TBME.2007.893506), the pinned simglucose insulin derivatives documented in [BC-002](m4-kinetic-boundary.md), and [Polonsky et al. 1986](https://doi.org/10.1172/JCI112308) as specified in the [C-peptide card](models/polonsky1986-cpeptide.md). BC-004's explicit equimolar assumption, nominal-profile pairing, whole-body scale and synthetic baseline are inherited. Their numerical success is not evidence of T1D or transplant applicability. No new human parameters or observations are introduced.

## Inputs, states and execution

Require a completed, hash-checked BC-004 archive matching the frozen boundary protocol hash. Copy only its declared artifacts into the run, retaining original units and exact input/initial inventories. Time is elapsed minutes; forcing is finite piecewise linear in pmol/(kg min), with explicit jumps. Both branches use the same complete reporting grid at 0.5-minute intervals, augmented by forcing edges. Concentrations are pmol/L; inventories and all ledgers are pmol/kg.

Insulin state order is plasma amount, liver amount, hepatic loss, peripheral loss, delivered input. A new wrapper accepts finite nonnegative initial plasma/liver inventories, with all ledgers initially zero. It calls the unchanged verified native derivative through BC-002's guarded inlet. No additional first-pass fraction or SC absorption is added. Only insulin states advance; the other native state entries are a fixed carrier and have no trajectory interpretation. The original BC-002 zero-initial function remains unchanged and serves as a regression reference.

C-peptide uses BC-003's existing central/peripheral amount states, central elimination and input ledger. Its existing solver already accepts explicit initial inventories. No insulin hepatic extraction is applied to this branch. Each branch owns its distribution and removal. Conservation includes initial inventory: `remaining + eliminated - delivered = initial central/plasma + initial peripheral/liver`.

The standard-library parent runs an insulin worker in the existing locked M0 simglucose environment and a C-peptide worker in the existing BC-001/003 environment. They exchange explicit artifacts, not package installations or hidden shared state. Workers verify parameters/identities and runtime versions. The parent rejects a missing, failed or incomplete branch. No general plugin interface or new runtime lock is introduced.

## Cases and independent checks

Execute BC-004's zero increment, incremental pulse, pulse plus synthetic basal, and whole-body mass ramp. Add a basal-only case using the total case's baseline and initial equilibrium over 240 minutes. Add a 60-minute unforced washout with nonstationary initial insulin amounts `[2,3]` and C-peptide amounts `[4,2]` pmol/kg; these are engineering fixtures. All cumulative ledgers start at zero. The initial condition is never silently replaced by a zero state or reconstructed from a pump rate.

For insulin, independently calculate the forced zero-inventory matrix-exponential solution from BC-002 and add homogeneous propagation of the initial inventory, including its cumulative removal. For C-peptide, independently assemble the four-state exchange/removal/input matrix and propagate affine input by a matrix exponential. Constant-input cases additionally compare concentration with the published analytical kernel in BC-003. These references do not call the numerical ODE derivative.

Compare tight RK45 against DOP853 and each reference against the independent calculation. Store the coarser RK45 trajectory descriptively. Check all inventories/ledgers, both concentration conversions, the exact input integral, nonnegativity, zero-input output, constant basal equilibrium, deterministic repetition, and total = basal-only + incremental superposition including ledgers. Compare zero-initial insulin trajectories directly with unchanged BC-002 using identical settings. A zero-input washout must retain and eliminate its initial inventory; it must not be treated as the all-zero case.

For the ramp, communicate interval-average forcing at 2, 1, 0.5, 0.25 and 0.125 min; preserve each interval's exact amount. Compare concentrations against continuous piecewise-linear input on the common output grid. This tests discretization of the input signal; it is not a delay or portal transit model. The pulse boundaries are integrated exactly rather than smoothed.

## Frozen acceptance

| Quantity | Limit |
| --- | --- |
| Reference versus independent state calculation | 1e-7 pmol/kg |
| Tight/reference and analytical concentration disagreement | 1e-5 pmol/L |
| Mass conservation and input integral discrepancy | 1e-7 pmol/kg |
| Negative inventory tolerance | 1e-9 pmol/kg |
| Basal equilibrium drift | 1e-8 pmol/kg |
| Superposition disagreement, all states/ledgers | 1e-7 pmol/kg |
| Existing zero-initial insulin regression and repeated output | Exactly zero |
| Finest communicated-input concentration difference | 0.01 pmol/L |
| Finest/coarsest communicated-input error ratio | At most 0.35 |

Maxima are over the declared cases/output times, not continuous-time guarantees or biological error bounds. Communication errors use the reference solver to separate input discretization from solver settings. Keep failed runs and original criteria; any later amendment must preserve the original negative result.

## Provenance, reconstruction and limits

Retain input protocol/archive, source snapshots including reused files, native identity, both locks and runtime versions, settings, all solver/reference states, communicated-input trajectories, checks, worker logs and final report/figure. Started/failed/completed status must be explicit; interruption or nonfinite/incomplete solver output cannot become a completed report. Never overwrite an output directory.

Standard-library reconstruction checks hashes and completeness and recomputes numerical summaries from saved states, without integrating, fitting or executing archived code. Figure reconstruction uses checked artifacts. Fresh-process output repetition and failure-mode tests are separate from domain review.

OT-026 gains a bounded paired kinetic demonstration if these criteria pass. Glucose feedback, appropriate secretion regime, BC-001 scale/initialization, empirical assessment and the [domain-review questions](m4-collaboration-brief.md#paired-boundary-review-packet) remain open. The [measurement assessment](m4-cpeptide-measurements.md) does not establish ready authorized data. No contact, access request or clinical experiment is part of BC-005.
