# 0007 — Bounded causal CGM forecasting

Status: accepted for software preparation, 19 September 2026; human execution conditional on a verified authorized release.

## Decision

Implement [M3/1](../research/m3-protocol.md) as a small offline forecasting workflow: a strict normalized CGM contract, a source-specific intake boundary, explicit release/rights and identity registry, causal windows, temporal split/freeze, isolated existing Ridge estimator and persistence, and simulator-free analysis. Preserve M0/M1/M2 and IV-001 artifact versions and historical bytes. Reuse their strict JSON reader, stable byte snapshots, interruption conventions and evidence archiver where suitable. Introduce separate M3 contract and metric identifiers instead of reinterpreting plasma or interval-mean simulation artifacts as clinical CGM.

## Rationale and alternatives

The [feasibility review](../research/m3-data-feasibility.md) selects a small conditional OhioT1DM cohort. Missing physiological parameters and incomplete meal records preclude a defensible human adapter for either existing physiological engine. Fictitious virtual-profile matching, treating absent meals as zero, or equating plasma with CGM would answer a different question. Preserve those engines as internal reference tracks and explicitly leave physiological prediction unassessed.

An existing statistical estimator supplies a useful bounded observed-care forecast question without a biological extension. Direct scikit-learn reuse avoids adopting GluPredKit's broader parsing and cross-validation choices. No universal datahost, ontology, generic plugin system, controller or UI is needed. ReplayBG is assessed but not integrated because its required inputs and initialization assumptions are unresolved.

## Consequences

This narrowing cannot produce evidence that simglucose or Cambridge predicts actual people, nor identify a biological correction for B1. It prepares causal data/evaluation mechanics and a first human forecast comparator. A physiological M3 extension requires a new protocol with suitable data, justified parameters, observation model and state initialization. Human-data acceptance and independent human reproduction remain open separately.

Public examples and CI contain only self-authored synthetic fixtures. Human input, derived records, identity links and private provenance stay outside Git and external services. Split/freeze metadata cannot itself confer access rights or guarantee that a person has never inspected a file. Record attestations and access events, retain failures, and distinguish conditional specification from an executable release freeze.
