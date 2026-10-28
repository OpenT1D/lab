# IV-001 — Internal numerical verification and robustness

Version: 1.0. Status: prespecified implementation protocol, 14 September 2026. No IV-001 numerical result is claimed by this document. This is separate from the unchanged OT-001 and OT-014 protocols. [Decision 0005](../decisions/0005-internal-verification-and-external-review.md) records the development sequence.

## Questions and permitted conclusions

1. How much do tighter native solver settings change fixed-input and feedback trajectories?
2. How sensitive is the scored day to initialization history?
3. Do tests detect the selected consequential implementation faults?
4. Which within-engine conclusions survive specified changes in meals, announcements, observation gaps and local parameters?

This campaign characterizes software and numerical/structural sensitivity. It cannot establish human predictive accuracy, clinical suitability, independent reproduction, population confidence intervals or physiology-only effects across different engine/controller systems.

## Reference configurations and ancestry

Use simglucose revision `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, adult#001 and adult#002, seeds 101 and 102, with unchanged native basal-bolus and PID settings from M1. Use LT1 revision `9a6092065bd821f88691cd8d03b0550acd665573`, the single Cambridge reference parameterization and seed 101, with unchanged LT1 PID and MPC settings from M2. These are ten development configurations. Never equate similarly numbered patients or treat the Cambridge singleton as a cohort.

Keep the native Dexcom/Insulet and IdealCGM/StaticInsulinPump devices respectively. Keep three-minute simglucose observation/action intervals and five-minute LT1 sensor/controller cadence with native one-minute outer callbacks. Preserve native solver steps, event ordering, ingestion and sensor random streams. The Cambridge ideal sensor has no stochastic uncertainty to estimate.

Baseline: 48 hours, first 24 hours initialization and last 24 hours scoring, native initial conditions and the existing daily 07:00/45 g, 12:00/70 g, 16:00/15 g, 18:00/80 g, 23:00/10 g meals. Announce the full meal at its start (A). Scored day is the same calendar day/time in initialization comparisons; histories may start earlier or later. Preserve naive synthetic time for simglucose and UTC for LT1. Do not silently interpret either as clinical timestamps.

## Numerical campaign and pilot gate

First inspect the effective native tolerances and configuration hooks. Persist baseline settings rather than assuming library defaults. Use three relative refinement levels: native tolerance, one tenth and one hundredth; refine simglucose absolute tolerance in the same proportion. Keep controller/sensor/outer schedules fixed. For LT1, a narrowly configured native SolverRK1_2 instance may set its protected tolerance after a checked source/attribute assertion; record this experimental access. No native source edit or replacement equation is permitted.

Run an initial pilot using adult#001/101/basal-bolus and Cambridge/PID, under A, with all three levels. Pilot outputs remain archived. Before running the full matrix, freeze a separate threshold record identifying the protocol, source/lock hashes, pilot inputs and the numerical rationale per signal. Threshold selection must not inspect the full matrix. A threshold is an IV-001 engineering criterion, not a clinical target or a change to historical exact regressions.

For each configuration, retain the nominal closed-loop command sequence. Replay that exact sequence with each solver level, without feedback adaptation. Verify matching meal and delivered-insulin histories over the common interval; a mismatch invalidates a fixed-input comparison. Separately run feedback at all levels. Distinguish convergence toward the finest computed trajectory from accuracy against an analytic truth. A tighter run is a numerical comparator, not biological ground truth.

Compare common timestamps and exposure intervals only. Report maximum and mean absolute glucose deviation, glucose exposure differences in percentage points, delivered insulin difference, terminal status/time, common scored duration and excluded duration. Report both adjacent refinement differences; do not assume monotonic convergence. Near-zero differences, threshold crossings and different termination times need explicit handling. No whole-day stability claim is allowed when only a partial day is shared.

Initialization comparison: 0, 24 and 48 hours of repeated baseline history before the same scored calendar day, with native resets and otherwise unchanged settings. This measures combined physiological, controller and sensor-history dependence. It does not isolate a single initial physiological state. Native initial-state perturbations may be added only through a documented consistent state construction and a protocol amendment before their runs.

## Selected fault detection

Prespecify seven fault classes: rate/amount conversion by a factor of 60; duplicate meal/announcement delivery; event assignment to the wrong interval; skipped sensor generation during masking; access to unannounced future information; false completion of a partial run; and changed data/provenance without detection.

Each fault must be applied in a temporary copy or synthetic boundary fixture and produce a failure of a relevant production check. Run an unmodified control first. Retain the exact mutation, target/source hashes, command, exit status and diagnostic. Syntax/import failure, unrelated failure and timeout are not evidence of fault detection. A surviving mutant is a finding requiring a relevant test/fix or an explicit unsupported classification with reason. Do not invent a target test-count or interpret a selected mutation score as coverage of every possible defect.

## Robustness matrix

Run one factor at a time on the ten development configurations, keeping the existing controller settings. Changes apply only on the scored day unless explicitly described as initialization:

- Meal amount: 0.5 and 1.5 times baseline, with truthful announcements reflecting the changed amount.
- Meal timing: all scored-day meals 30 minutes earlier or later, with truthful simultaneous announcements.
- Announcements: none, half amount, or 15 minutes late, preserving actual meals.
- Sensor information: hold the last available observation during [12:00,12:15), [12:00,13:00), or [18:00,18:30); generate and record all native sensor samples before masking.
- Local physiology: vary two named positive native parameters separately by factors 0.9 and 1.1. Select their identity from source descriptions before the matrix, record baseline values/units/source, and preserve all other parameters. These are local engineering probes, not a biological range or a validated population. If changing a parameter requires a different equilibrium, use the native reset and disclose its effect; do not alter controller profile knowledge to compensate.
- Initialization: the 0/24/48-hour history comparison above.

The full robustness schedule and selected parameter identities must be frozen in a machine-readable plan before execution. Every planned case must retain a status including not attempted, initialization failure, partial native stop, timeout and completion. Invalid configurations must be rejected rather than silently coerced.

No automatic combinatorial expansion. If one-factor results identify an interaction worth investigating, record a separate amendment before running that interaction. The original matrix remains intact. All IV-001 runs are development evidence; the inspected OT-014 evaluation is not reused for tuning or represented as untouched data.

## Analysis, acceptance and failure policy

Keep simglucose interval-mean subcutaneous glucose and Cambridge point plasma glucose in separate tracks. Reuse their existing metric definitions where semantics match, with explicit probe versions for extended horizons or quadrature. Integrate actual delivery over duration and exclude terminal commands. Missing scored exposure gives undefined insulin totals/metrics, not zero. Commands and delivery remain separate.

Report paired differences within profile, seed and controller. Describe both simglucose seeds rather than treating them as population samples. Show per-condition coverage, failures, differences between controllers and rank/sign reversals. A comparison without sufficient complete pairs is undefined. Parameter perturbed cases are not extra profiles. Partial numerical comparisons may be reported with their exact common duration, separately from complete-day rankings.

Scientific outcomes are `stable_within_prespecified_limits`, `sensitive`, or `inconclusive`; a reproducible sensitive result is a legitimate campaign result. Software acceptance requires complete accounting, strict finite/unit/time/status/provenance checks, exact replay within environment, retained historical references, and report reconstruction without native engines. Unexpected numerical differences are investigated before accepting the report; no baseline relaxation is authorized.

A failed run remains in the denominator and archive. Preserve the primary error when diagnostics fail. The supervisor must bound execution and retain partial output. Write into new output directories only. Reports identify consumed bytes, protocol, configurations, effective settings, source revision, dirty state, dependencies, thresholds and analysis. An unfinished study must not appear complete.

## Delivery sequence and review

1. Accept the evidence-label decision and this protocol.
2. Implement isolated numerical workers, pilot/freeze, numerical and initialization reports, meaningful tests and CI.
3. Implement selected fault-detection experiments and fix demonstrated gaps with regression evidence.
4. Freeze and execute the robustness matrix; publish a canonical tutorial and evidence record with limitations.

Use sequential codex worktrees/PRs, exact-head checks and post-merge main CI. Keep original M0/M1/M2 checks. Archive complete runs and failures outside Git with hashes; commit only compact evidence metadata. An external reviewer is not needed to proceed, but independent human reproduction remains open. No human data, access request, new biological extension or public release is part of IV-001.
