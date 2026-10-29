# Validation and scientific claims

OpenT1D records evidence for a specific model version, composition and application. There is no universal "validated" label that automatically transfers to every use.

Internal development may proceed before independent human reproduction. [Decision 0005](../decisions/0005-internal-verification-and-external-review.md) preserves that open external-review item and defines the separate [IV-001 campaign](internal-verification-protocol.md).

## Different questions require different evidence

| Question | Relevant evidence |
| --- | --- |
| Is the implementation doing what was specified? | Software and numerical verification, units, invariants and boundary cases |
| Does the adapter preserve the upstream model? | Direct upstream execution compared with the adapter under controlled conditions |
| Does the model represent the target application adequately? | Relevant measurements, population, interventions, timescale and error assessment |
| Can someone reproduce the result? | Independent execution from the recorded protocol, inputs and environment |

A run can be reproducible and scientifically wrong. A model can fit observed glucose while failing to predict a changed intervention. Agreement between related simulators is not independent clinical validation.

## Evidence labels

Use explicit descriptions such as **proposed**, **implemented**, **upstream reference reproduced**, **evaluated for a named application**, and **independently reproduced**. These describe different dimensions; they are not a single maturity score. Record dates, versions, reviewers and links to the evidence behind each statement.

Candidate modules remain candidates until their documented behavior has actually been checked. Label hypothetical parameter sweeps as exploratory. Do not present residual secretion scenarios as proof that a therapy restores that secretion.

## Before running an evaluation

Specify the question, intended use, population, horizon, interventions, primary outcomes, tolerances and decision criteria. State which information is visible to the controller or estimator. Describe missing-data handling, failures and exclusions.

Separate parameter fitting and algorithm development from final evaluation. Check for overlapping participants, shared data sources and closely related model families. Define the comparison so that differences in population or available information do not masquerade as treatment effects.

## Reporting results

Report outcomes per relevant population and condition, with uncertainty and sensitivity to assumptions. Show failures and incomplete runs alongside successes. Explain whether a metric is computed from physiological glucose or simulated sensor readings. Preserve its threshold and interval conventions.

Evaluate parameter identifiability when fitting a model. Different parameter sets can fit the same data while implying different interventions. Compare added complexity with a meaningful simpler reference.

Reproduce the coupled system as well as its individual modules. Check shared process ownership, conservation where appropriate, numerical convergence and communication intervals. New coupling creates new assumptions to assess.

## Review and corrections

Record what each reviewer assessed: implementation, reproduction, methods or biological interpretation. Seek relevant domain review before making a new biological or therapeutic claim. If it is not available, state the limit while continuing useful exploratory work.

When a correction changes prior results, retain the affected version, describe the impact and issue corrected artifacts. Do not silently replace published results; see [maintenance](../maintenance.md#scientific-corrections).

The scientific basis, including context-of-use guidance and parameter identifiability, is documented with primary references in [the project research report](../onderzoek/projectopzet.md#8-validation-as-core-functionality).
