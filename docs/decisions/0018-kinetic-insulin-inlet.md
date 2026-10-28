# 0018 — An incremental insulin inlet with a kinetic-only claim

Status: accepted for the requested next OT-026 engineering step on 20 September 2026. Biological interpretation remains exploratory.

## Context and decision

[BC-001](../research/m4-results.md) supplies evoked secretion but neither a supported basal rate nor a calibrated whole-body secretion scale for a T1D virtual profile. The pinned simglucose reference has liver/plasma insulin compartments but no separate endogenous inlet and no direct portal-insulin action in glucose production. Adding secretion to a pump command would introduce inappropriate subcutaneous absorption.

Implement [BC-002](../research/m4-kinetic-protocol.md) as an explicit additive inlet around the original native derivative. Nonzero calculations advance only insulin inventories and mass ledgers; the original full patient is advanced only for exact zero-extension regression. Native kinetics own exchange and removal. The primary inputs use native pmol/(kg min), with zero incremental baseline and initial inventory. A secondary BC-001 trace replay uses a sourced mass-to-mole conversion and an explicitly uncalibrated whole-body mass interpretation. This does not supply missing biological calibration.

Reuse the locked M0 simglucose environment without changing its source, parameters or historical experiments. Keep forcing, native execution, independent matrix-exponential calculation and report reconstruction separate. Preserve source artifacts, both locks, attempted-run failures and original thresholds. BC-002/1's transfer-tolerance failure remains recorded; BC-002/2 adds one finer interval before executing the amended comparison.

## Alternatives and consequences

A full glucose-feedback connection would add unsupported basal, scale and portal-action interpretations before resolving whether the inlet is numerically correct. A wholly reimplemented kinetic simulator would weaken the direct connection with the pinned engine. The wrapper plus independently derived oracle gives a bounded native check without adding a general plugin framework.

OT-026 is partial after this experiment. It establishes numerical transfer and kinetic accounting, not reduced pump requirements, human identifiability or a treatment effect. Before extending it, review the supported glucose regime, resolve source discrepancies and specify independent paired glucose/C-peptide/insulin observations, exogenous treatment and route information. An oral challenge may require a different secretion reference. Revisit this decision when that scientific question and evidence support a full metabolic experiment.
