# 0002 — Reference reproduction before integration

Status: accepted for intact engines and a first Python simglucose adapter in M1; a general cross-engine host is not accepted by this decision. Reviewed 2026-09-13. This does not establish scientific validity or a stable public API.

## Context and evidence

The [source assessment](../research/m0-assessment.md) compared existing engines and frameworks. The [reproduction record](../research/m0-reproduction.md) now demonstrates native simglucose and explicitly Cambridge-based LT1 scenarios locally and in Linux CI, with recorded configurations, dependencies, failures and reset behavior.

Those probes expose different glucose compartments, action units, sampling and announcement conventions. They can run through native APIs without rewriting equations. The [first protocol](../research/first-experiment.md) specifies the information-controlled experiment; the subsequent [M1 tutorial](../m1-tutorial.md) records its bounded development implementation.

## Decision

Preserve each physiological engine as a whole, including its solver, native absorption and tightly coupled internal processes. Build the first thin simglucose adapter in M1, while using the LT1 Cambridge probe to challenge its assumptions from the start. Keep their dependencies optional and isolated. No universal equation language or public plugin API is introduced now.

The initial adapter must translate declared units and timing, allowlist controller information, preserve random/reset behavior, distinguish commands from modeled delivery, and retain completed and failed runs. Native reproduction remains separate from the announcement-controlled experiment. Direct versus adapted equivalence is required before final evaluation.

Keep the scientific experiment intent above engine-specific configuration. Where compartments, populations or cadence cannot be matched, create explicit separate tracks rather than fabricate equivalence. Do not split endogenous secretion, absorption or clearance into independently owned modules without a new justified coupling decision.

## Reuse and alternatives

Reuse the native models, controllers, sensor/pump implementations and published examples. The new code so far consists of small reference recorders and evidence checks; it does not supply a generic simulation framework. Prefer upstream fixes for upstream defects, preserving the original reference and any patch provenance.

The comparison below is against the **fixed OT-001 requirements**, not the number of features in each project. Runtime evidence covers the two native probes; APS and the proposed extensions are source assessments. Required changes are estimates of work scope, not measured implementation costs.

| Requirement from the probes/protocol | Extend LT1 as the host | Extend APS TestBed | First Python adapter around native simglucose |
| --- | --- | --- | --- |
| Preserve the pinned simglucose physiology, solver, devices and Python BB/PID behavior exactly | Native LT1 modules exist, but they are not the pinned Python implementation. A process bridge or an equivalent reimplementation would be additional work. | Has a bundled simglucose fork with BB/PID. Replace or reconcile that fork against the chosen upstream pin and rerun equivalence checks. | Calls the already executed Python environment/controller APIs. Add the adapter and direct-versus-adapted tests. |
| Keep Cambridge/MPC as a distinct native reference | Already supplied and executed; strongest fit if Cambridge is the primary workflow. | Current documented second engine is Glucosym. Cambridge requires another integration and toolchain. | Keep the executed LT1 process as a separate reference; a shared second-family adapter belongs to M2. |
| Deliver once-only meal announcements and mask observations after sensor generation | Announcement lists and controller/sensor interfaces already exist. A shim must preserve OT-001's once-only delivery and simglucose cadence. | Actual-meal controller inputs and fault injection exist. Add an announcement boundary and replace/adapt source-rewriting faults for observation-only masking. | Add an allowlisted information object and post-generation observation filter around the native step. This remains new M1 work. |
| Preserve exact reference PID reset, units and integral order | LT1 PID uses basal feed-forward, its own gain units and a different first-derivative/reset convention; using it unchanged would change OT-001. Wrap the pinned Python controller or validate a separate port. | Related Python PID is present in the fork; verify its exact source and configuration before reuse. | Reuse the pinned native controller; only information delivery changes under the new protocol. |
| Keep output compartment, interval and delivery semantics explicit | Native types and module metadata help, but a Python bridge must translate U/min versus U/h and interval means versus point samples. | Existing engine-specific loops also need this mapping and separate compartments. | First adapter retains native three-minute semantics. The LT1 card and reference constrain later mapping; no claim of interchangeable patients. |
| Preserve failures, manifests and reviewed baselines with isolated dependencies | Add the evidence recorder/verification around LT1 and its Python bridge. | Add/reconcile recording and locks across the fork and Node/server stack. | Extend the small existing recorder; current review fixes verify failure recording and historical baselines. |

Source evidence for this table:

- LT1's [synchronous patient interface](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/types/Patient.ts), [controller interface](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/types/Controller.ts) and [simulation ordering](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/Simulator.ts) support native composition. The inspected interfaces do not supply a bridge to the pinned Python environment. A bridge is feasible; its implementation and lifecycle synchronization are additional work, not a reason to declare LT1 unsuitable.
- LT1 already includes [PID](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/controllers/PID.ts) and [basal-bolus composition](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/controllers/BasalBolus.ts). PID resets its previous error to NaN, includes a basal term and integrates before evaluating its output; the [pinned simglucose PID](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/pid_ctrller.py) does not share those conventions. Equal names do not imply equal controllers.
- APS's [documented simulator/controller stack](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/README.md) and [fault-injection runner](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/UVA-Padova/simglucoseFI/tests/run_Faultinjection_monitor.py) demonstrate useful prior capabilities. The runner rewrites source and executes engine-specific cases; those mechanisms do not yet implement OT-001's information boundary.

For **M1's selected simglucose-first experiment**, staying in Python avoids an otherwise unnecessary language bridge or controller port while reusing the exact executed implementation. The adapter must still earn its correctness through equivalence and information-boundary tests. This is the concrete reason for the first adapter, not an inference that a new general framework is inherently better.

LT1 is the preferred existing-host alternative for a Cambridge-first scope or if a demonstrated bridge makes the complete two-engine workflow simpler. Reassess host selection before M2 integration using the actual adapter and bridge changes. This decision does not approve a generic scheduler, universal schema, controller library or permanent cross-engine host. GluCoEnv and py-mgipsim remain later candidates for their respective acceleration/activity tasks.

## Consequences, rights and reconsideration

OpenT1D owns experiment scheduling and translation only at declared boundaries; each engine retains its internal processes. The additional adapter has a maintenance cost justified by the explicit cross-engine task and evidence requirements, not by novelty of modular simulation.

Code and parameter rights remain separately recorded in the model cards. Fetch pinned upstream sources rather than vendor parameter tables with unresolved independent provenance. The legacy simglucose runtime compatibility dependency and its bounded security exposure are recorded in the maintainer guide. A separate process is not a blanket license exemption.

Revisit this decision if direct-versus-adapted equality fails, the required observation boundary cannot be enforced, source/asset rights prevent the selected use, or a concrete LT1/APS extension supplies the same workflow with less maintenance. A new biological coupling or broader scientific claim requires its own evidence and, where applicable, decision record.

## History

- 2026-09-12: proposed, based on source inspection only.
- 2026-09-13: accepted for M1 software integration after two native runtime probes and their Linux reproductions. Self-review subsequently narrowed acceptance to the first Python adapter and added the requirement-by-requirement LT1/APS comparison; general host selection remains open for M2. External biological validation, independent researcher reproduction and a stable public interface remain unclaimed.
