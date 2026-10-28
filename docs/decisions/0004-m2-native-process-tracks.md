# 0004 — M2 native process tracks

Status: implemented for bounded M2; the [evidence record](../research/m2-reproduction.md) documents verification and the open independent human acceptance gate. No stable API or general host is introduced.

Scheduling update: [decision 0005](0005-internal-verification-and-external-review.md) retains independent human reproduction as a later open gate, not a prerequisite for internal development.

## Decision and concrete evidence

Retain the M1 Python loop and run Cambridge through LT1's own Simulator in an isolated Node process. A small controller boundary copies permitted sensor values and announced-meal history; it never passes native patient state or future scenario objects. The parent schedules complete runs, preserves failures and reconstructs separate analysis tracks. It does not schedule physiological steps. Use the existing two locked environments.

The [feasibility probe](../../experiments/m2/probe.mjs) compares direct native Cambridge/MPC callbacks with a copied information boundary and the retained M0 digest. It intentionally keeps the original reference's midnight announcement. It does not establish the later controlled protocol. Run from the repository root after the [LT1 setup](../research/m0-reproduction.md#lt1-cambridge-commands):

```sh
TS_NODE_PROJECT=experiments/m0/lt1/tsconfig.json node \
  --loader ./experiments/m0/lt1/node_modules/ts-node/esm.mjs \
  experiments/m2/probe.mjs results/m2-host-probe
```

## Alternatives against the implemented M1

| Requirement | Extend LT1 as overall host | Extend APS TestBed | Bounded native process tracks |
| --- | --- | --- | --- |
| Preserve M1 native Python physiology, controller/reset and historical artifacts | Needs a Python bridge and either synchronous step transport or whole-run delegation | Reconcile bundled older simglucose fork with pinned M1 and replace its scenario/output path | Reuse existing M1 execution and artifacts |
| Preserve Cambridge and native MPC | Native support; best fit for Cambridge execution | Add Cambridge, Node toolchain and semantic mapping | Reuse the executed native Simulator and locked import graph |
| Information, clocks and events | Native LT1 boundary still needs post-sensor filtering and announcement-history policy | Existing source-rewriting fault injector is not the required observation boundary | Two explicit local boundaries; no universal cadence |
| Reset, random streams, failure, timeout and cancellation | Bridge lifecycle plus artifact handling | Reconcile lifecycle across fork, faults and new Cambridge path | Native resets; process deadline; per-run checkpoints and errors |
| Provenance and report reconstruction | Migrate or delegate M1 artifact semantics | Add M1-compatible evidence path and lock/source checks | Preserve M1 reader and add versioned Cambridge reader |
| Additional maintained mechanisms | Overall Node coordinator plus Python bridge and two boundaries | Fork reconciliation, Cambridge integration and replacement evidence path | One bounded dispatcher, one LT1 boundary and separate metrics |

This comparison concerns the pinned versions in [decision 0002](0002-m0-reference-first.md), inspected again against M1's actual `adapter.py`, `control.py`, `simulation.py` and artifact/verification code. APS remains a source assessment, not an executed stack. Its documented fork and fault runner do not remove the concrete Cambridge or information-boundary work. The selected solution uses LT1 as the Cambridge host; adopting it as the overall host adds a migration without removing either runtime. Costs here are counts of required mechanisms, not measured engineering hours. Revisit if a concrete bridge reduces those obligations.

## Scientific conventions and limits

The [separate M2 protocol](../research/m2-protocol.md) preserves OT-001/M1. Cambridge is one documented parameterization, not an invented adult cohort. Comparisons remain within each engine; replacing an engine/controller combination cannot isolate physiology. LT1 PID is a different controller from simglucose PID. MPC's private Cambridge predictor is an estimator, not a second source of insulin or physiology in the simulated subject.

LT1 timestamps are UTC point samples. Its native outer step is one minute, shortened at events; sensor and control cadence remain distinct. Integrate the prior callback's modeled infusion over the actual elapsed interval. Exclude terminal commands. Report plasma point-sample exposure separately from M1's mean subcutaneous exposure; neither is a reconstructed continuous clinical time-in-range.

Announcements cross the boundary once by stable identity, but native MPC receives accumulated permitted history because its predictor uses previously announced ingestion. Retaining history is not repeated delivery. Generate sensors before masking; retain original observation time and age. No future unannounced meals or latent state enter the controller.

StaticInsulinPump converts a bolus amount into a one-minute rate and its source flags earlier callbacks as unresolved. The first M2 Cambridge support therefore excludes bolus-producing controllers and arbitrary pump replacements. Native PID may command a negative rate, and this pump does not clamp a lower bound: reject negative modeled delivery as a retained failure rather than altering either module. Validate internal controller state as well as output. Seed zero aliases one natively; use positive explicit seeds.

Keep engines, solver equations, M0 references, M1 contracts, baseline collections and asset rights unchanged. No patient data, vendored upstream parameters, new tolerance or public release is implied. Independent execution by another person remains a separate acceptance gate.
