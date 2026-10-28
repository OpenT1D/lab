# 0005 — Internal verification before external review

Status: accepted on 14 September 2026 for the maintainer-directed development sequence. This changes scheduling and evidence labels, not historical results or evidence requirements.

## Decision

Continue internal verification and bounded development without waiting for an independent person. Track four separate dimensions: implemented software, internally verified numerical/model behavior, evaluation against human observations, and independent human reproduction. No dimension substitutes for another.

M2's original human-reproduction criterion remains open, with its original frozen checkout and reproduction packet. It is now a later external-review acceptance item rather than a prerequisite for internal development or M3 preparation. Do not mark the original criterion completed or describe the project as independently reproduced. The historical M2 acceptance record remains authoritative for what was executed.

Add the separate [IV-001 protocol](../research/internal-verification-protocol.md) for numerical verification, selected fault detection and robustness. Keep M0/M1/M2 engines, equations, controllers, baselines, protocol bytes and archived outputs intact. Isolate experimental probes under `experiments/verification/`, using the existing locked native environments. A probe may configure a verified native solver instance or wrap an input boundary with recorded settings; it must not overwrite upstream sources or become a replacement production engine.

## Reason and alternatives

Waiting for another person would delay useful internal work without supplying missing biological evidence. Treating additional self-runs as independent reproduction would misstate the evidence. Removing the original criterion would erase the historical agreement. A separate later gate preserves that agreement while allowing the requested development sequence.

A general host, controller retuning, new virtual cohort, patient-data import and new biological mechanisms are not required for IV-001. They would introduce confounding changes before the existing calculations have been characterized.

## Consequences

Use an exact native control trajectory for fixed-input numerical comparisons, and separate these from feedback comparisons. LT1 passes the host solver to component resets, but the pinned MPC_Hovorka2004 implementation ignores that argument and retains its own SolverRK1 with a five-minute reset step. Refining the host SolverRK1_2 therefore leaves that internal prediction solver unchanged; feedback effects still include the controller's response to changed observations. simglucose and Cambridge retain their distinct glucose compartments, sampling and populations.

The existing evaluated profiles have already been inspected. IV-001 is a development verification campaign, not a new untouched evaluation. Preserve native stops and disclose partial coverage. Parameter perturbations are local engineering sensitivity probes, not validated biological ranges or new patients.

A result may be internally reproducible yet numerically sensitive or scientifically inadequate. Report that limitation rather than changing a baseline, excluding the case or weakening a threshold after observing the matrix. Human-data evaluation and independent review remain separate future evidence.
