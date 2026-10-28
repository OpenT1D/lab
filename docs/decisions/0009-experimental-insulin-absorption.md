# 0009 — Experimental Cambridge insulin-absorption comparison

Date: 20 September 2026. Status: accepted for bounded exploratory implementation.

## Context

LIT-001 recovered and numerically checked a published insulin-kinetic specification, but did not change OpenT1D's existing engines. The next requested capability is to compare absorption assumptions and observe their effect on the same native Cambridge scenario. The source-to-engine audit identifies different subcutaneous structures, native unit conventions and incomplete formulation-specific parameter ancestry.

## Decision

Implement LIT-002 as an isolated experiment using the pinned LT1 Cambridge patient and native numerical solver. Keep the existing M0/M1/M2 execution paths unchanged. Add three explicitly named experimental arms:

- `cambridge_native`: the intact Cambridge equations and parameters.
- `cambridge_mean_matched`: intact equations with only `tmaxI` changed to match the literature model's mean appearance time, including delay. This is analytical matching, not calibration against observations.
- `faggionato_sc`: independently implement the source's subcutaneous equations and input delay, replacing the native subcutaneous derivative terms and appearance into native plasma. Preserve Cambridge distribution volume, clearance, insulin action, glucose and gut processes.

The third arm is a hybrid, not a reproduction of the complete Faggionato population model. Its source volume, clearance, random effects, covariate effects and assay-noise parameters are deliberately outside the mapping. The native source checkout remains intact; the selected patient instance supplies the experimental derivative override.

Use identical predefined delivered insulin and carbohydrate inputs without a controller or pump. This avoids attributing controller or bolus-callback differences to physiology. Initialize each subcutaneous system at its own equilibrium for the same native basal rate, with constant basal history filling the delay line; retain identical plasma/action/glucose equilibrium. Record delay-line insulin as part of unabsorbed insulin. Split integration at the same original and delayed input-event boundaries in every arm.

Freeze the cases, mappings and engineering tolerances before the main runs. Compare native subcutaneous states with an independently implemented analytic solution, test process ownership and native-baseline equivalence, and examine numerical refinement of both trajectories and between-arm contrasts. Preserve unsuccessful runs. Source claims, numerical correctness and biological accuracy remain separate.

## Consequences

A researcher can run one bounded comparison and inspect absorption, plasma insulin and glucose differences from saved artifacts. Simulator-free report reconstruction retains source, input and analysis provenance. A nonzero difference is not evidence of physiological improvement; a small difference is a valid result.

This implements an exploratory extension-path experiment. It does not close B1, change M3/C1 priority, establish a lispro-specific virtual population or validate insulin decisions. General pump schedules, controllers, participant fitting and application-specific human evaluation need their own supported contracts.

The [protocol](../research/lit002-protocol.md), [usage guide](../lit002-tutorial.md) and [LIT-001 source audit](../research/lit001-engine-audit.md) define the implementation boundary.
