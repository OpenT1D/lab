# 0003 — Bounded M1 interval contract

Status: accepted for implementing OT-001 version 1.0. This is an experimental internal contract, not a general host or stable public API.

## Decision

Use standard-library immutable Python records and strict JSON-compatible numeric values for the first adapter. Name units in fields. Reject booleans, null, strings and nonfinite required numbers. Preserve negative finite commands for native pump limiting; delivered rates must be nonnegative. Keep the root environment for tooling and use the existing isolated, pinned simglucose runtime for M1 execution. No new simulator dependency or upstream source patch is introduced.

One output row represents a completed three-minute interval: glucose and raw CGM describe the preceding interval ending at `end_min`; commands and delivery describe the interval starting at `start_min`. Store controller input separately, with its original source time. Sensor availability belongs to the end observation and controls sensor metrics, independently of the controller input used at interval start. True meals and newly delivered announcements are separate amounts in grams. There is no terminal action row to confuse with a missing glucose observation.

The native engine owns physiology, integration, patient state, sensor randomness and pump limiting. OpenT1D owns the outer control clock, announcement delivery, post-generation masking, recording and analysis. The adapter calls native reset; the controller resets only at run start. The experiment stops after a native terminal interval. The initial point observation is recorded separately and excluded from duration-weighted metrics.

## Consequences and verification

The [contracts and metrics](../../experiments/m1/contracts.py) follow the [protocol](../research/first-experiment.md). The metric version is `ot001-exposure/1`; undefined statistics are null. Missing or unfinished duration remains in coverage denominators. Commands are rates in U/min, including native `bolus`; delivered amount is modeled rate multiplied by the completed duration. Metrics do not sum commanded insulin or held CGM substitutes.

The first executable configuration deliberately permits only development profiles and seeds. Evaluation requires a separately frozen implementation and evidence gate. This supports a bounded demonstration without silently executing the full scientific study. M2 must reconsider host selection and cross-family semantics; this decision supplies no universal engine interface.

Unit tests include independently calculable thresholds, weighted population variance, partial coverage, the warmup boundary, command-versus-delivery integration, strict invalid examples and output after termination. Native equivalence, native controller/reset behavior, once-only announcements, continued sensor generation during masking, invalid states and native terminal handling are exercised by `experiments/m1/test_native.py`. The [M1 tutorial](../m1-tutorial.md) documents the saved-artifact workflow and reconstruction.

The critical review retains `ot001-exposure/1`: interval calculations and controller formulas are unchanged. Report schema `opent1d.report/2` adds exact consumed-input hashes and explicit observed durations; the readable table treats an entirely unobserved insulin day as undefined. Profile sign reversal requires at least two included profiles. The verification gate additionally requires one complete, independently retained M1 historical collection, with exact context and output digests and no automatic enrollment. These clarify evidence and presentation without extending the model contract.
