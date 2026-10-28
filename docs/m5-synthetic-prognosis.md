# M5 synthetic prognostic comparison

This OT-027 tool runs the proposed **analysis shape** on 32 invented people.
It compares a simple prediction of later reported insulin use with the same
prediction plus one observed C-peptide/glucose index. It builds its own fixed
fixture and has no command for loading participant records. The code is a
software rehearsal, not a CIT-07 analysis, transplant model, empirical
protocol freeze, treatment-effect estimate or cure result. OpenT1D supplies
the tool, not participant data.

## Run and reconstruct

From the repository root, choose a new output directory:

```sh
uv sync --locked
uv run --locked python -m experiments.m5.synthetic_prognosis.run run \
  results/m5-synthetic-prognosis
uv run --locked python -m experiments.m5.synthetic_prognosis.run reconstruct \
  results/m5-synthetic-prognosis
```

The archive contains the invented fixture, a complete-roster report, a copy
of the implementation and their hashes. Reconstruction verifies the hashes,
the current implementation, the fixed fixture and the recalculated report.
It does not refit a human cohort. The code is at
[`experiments/m5/synthetic_prognosis/run.py`](../experiments/m5/synthetic_prognosis/run.py).

## Fixed demonstration rules

| Part | Invented rule |
| --- | --- |
| Clock | First infusion is day zero; all later infusions remain recorded. |
| Landmark | Named visit V10, MMTT, day 70–80; fasting and 90-minute C-peptide/glucose must be observed. |
| Baseline | Prior reported insulin amount, prior glycemic status and landmark day, all available by the landmark. |
| Added feature | Invented index: 90-minute C-peptide divided by concurrent 90-minute glucose/100. It is not an estimated secretion rate or graft mass. |
| Outcome | Mean of seven invented, consecutive daily reported insulin amounts at the named **Y1** visit. Visit V15 is never a substitute, even when it occurs on day 365. |
| Split | Every fourth `SYNnnn` person is assigned to evaluation before fitting; every row and infusion of one person stays in that split. |
| Fit | The same eligible development people train both illustrative ridge models. Their feature means/scales and coefficients come from development only; a fixed slope penalty of 1 is used. |
| Comparison | Both models predict the same eligible held-out people. The report gives each prediction, mean absolute error (MAE) for each model and added-minus-baseline MAE. No success threshold is applied. |

The fixed fixture includes distinct failures: confirmed graft failure causing
protocol-directed day-75 noncollection, a general unavailable challenge, a
below-limit C-peptide value, a V15 record without Y1 and an incomplete
seven-day diary. They remain in the 32-person roster. Missing diary entries
are never imputed as zero. A later infusion on day 150 remains visible even
for an eligible person. The fixture uses days 359–365 for its seven diary
entries only to test arithmetic; the actual released mean-insulin interval
and Y1 association remain unverified.

The checked run has 24 development and 8 evaluation roster entries. After
the stated eligibility rules, the **synthetic** paired comparison uses 20
development and 7 evaluation entries. On these invented values, baseline
MAE is about 0.751 U/day and added-feature MAE about 0.699 U/day. These
numbers are consequences of the hand-built fixture, including its invented
outcome formula. They do not estimate human predictive performance, justify
the feature or choose a clinical threshold. The five excluded records and
their reasons are in the report rather than being silently dropped.

## Boundary to an empirical study

The [OT-027 protocol](research/m5-cell-therapy-protocol.md),
[data contract](research/m5-cell-therapy-data.md) and
[public form/laboratory audit](research/m5-cit07-form-lab-audit.md) leave
critical source facts open: participant and infusion linkage, released V10,
Y1 and V15 codes, true challenge identity, assay/limit rules, clinical
missingness, and the construction and semantics of the seven-day diary
mean. The [review packet](research/m5-domain-review-brief.md) also requires
transplant, assay, kinetics and statistical review. An authorized release,
source-specific converter and new empirical freeze must settle the exact
variables, model, split, uncertainty, minimum benefit and failure policy
**before** human fitting or reserved scoring. This toy ridge specification
does not fix those decisions.
