# LT1 Cambridge model and asset card

Status: native Cambridge reference executed locally and in Linux CI with exact native-reset, new-process and cross-platform replay. Update execution evidence through the [reproduction record](../m0-reproduction.md).

## Identity and intended use

LoopInsighT1 by Heiko Peuscher and contributors, revision `9a6092065bd821f88691cd8d03b0550acd665573`, source package version 2.1.0. Select the Cambridge model explicitly. The convenient minimal demo uses UVA/Padova and cannot demonstrate the required second family.

The [source assessment](../m0-assessment.md) links the Cambridge implementation, Hovorka/Andersen ancestry and IFAC EDT 2025 reference configuration. The model supplies a configurable parameterization, not a cohort matched to simglucose's profile identifiers. The reference uses MPC_Hovorka2004, IdealCGM and StaticInsulinPump; it is not a matched basal-bolus/PID comparison.

## Inputs, outputs and lifecycle

The boundary distinguishes infusion rate U/h, bolus amount U, meal grams, ingestion g/min and time-stamped announcements. Cambridge converts to its internal glucose and insulin units. Preserve that boundary; copying simglucose's U/min values directly would introduce a factor-of-60 error.

Outputs distinguish plasma glucose `Gp` and optional tissue glucose. Native outer timing, sensor/controller sampling and solver integration are distinct. The loop advances physiology, sensor, controller and actuator in its own order; event boundaries may shorten a step. Reset reinitializes modules and solver. The seed policy offsets component seeds and aliases zero to one. Native reset and original-reference timing are reproduced in M0. M2 tests additionally exercise shortened event intervals, unchanged direct/bounded trajectories, and observation masking after generation.

## Assets and rights

The repository and Cambridge file declare MIT; constants, units and scientific references occur together in the model file. This supports attributable source reuse, but not a claim of independent verification of each parameter's origin or a validated virtual cohort.

A [dated parameter-source follow-up](../lit001-engine-audit.md#parameter-source-follow-up-27-september-2026) matches the Cambridge defaults `tmaxI=55 min`, `ke=0.138/min` and `VI=0.12 L/kg` to Hovorka et al. (2004), Tables 1–2, including the `VI*BW` volume convention. Andersen's 2014 example repeats the three numerals, but its virtual-cohort distributions are separate from LT1's fixed profile. The earlier experimental papers cited by Hovorka and the path from those estimates into LT1 have not been independently reproduced.

The selected reference requires Cambridge constants, MPC configuration, sensor/pump definitions and the example's meal schedule. It does not require frontend images, a patient dataset or a clinical-derived cohort. Fetch the exact upstream revision outside version control and retain source/asset hashes and notices. Dependencies, including any applied upstream package patches, require their own inventory. Do not infer that a separate process removes third-party license obligations.

## Execution, evidence and limitations

The native reference is a 24-hour UTC scenario with a 40 g meal at 08:00, consumed over 15 minutes and announced at midnight. Preserve these original settings. Pin Node and the resolved dependencies before running it; the upstream repository does not commit its npm lockfile.

The recorder retains full native callback records and the glucose/insulin CSV, verifies file success and signal semantics, tests native reset and new-process execution, and records nonfinite or partial results. The Cambridge run establishes structural diversity from the UVA lineage, not population equivalence or clinical validity. The initial maintainer owns the M0 harness; the bounded M2 adapter now retains the native loop and supports LT1 PID/MPC with controlled announcement and observation conditions, as specified in the [M2 protocol](../m2-protocol.md). The [M2 evidence record](../m2-reproduction.md) reports the completed two-track study. Cambridge remains one deterministic structural parameterization, not an independently validated cohort or held-out population.

## M3 suitability boundary

The [M3 data assessment](../m3-data-feasibility.md) excludes this engine from its CGM-only human forecasting application: verified physiological profiles/state initialization and a defensible observation mapping are absent. M0/M1/M2/IV-001 synthetic evidence remains unchanged. No real person is matched to a virtual profile or parameterization.
