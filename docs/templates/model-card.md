# Model-card template

Copy this structure when proposing an engine, controller, device or biological module. Replace the prompts with evidence, or explicitly state what is unknown or not applicable. This is a documentation template, not a machine-readable interface specification.

## Identity and provenance

Name and module type; upstream repository; exact revision; original publications; authors; parameter sources; code and asset licenses; OpenT1D modifications and maintenance owner.

## Intended use

Research question; population and disease stage; mechanisms; supported interventions; timescale and horizon; unsupported uses. Distinguish the original model's scope from the proposed OpenT1D application.

## Inputs, outputs and coupling

Variables and units; compartments and routes; time conventions; state initialization; observable versus latent information; process ownership; required neighboring modules; incompatible combinations.

## Execution

Runtime and dependency versions; solver and tolerances; random streams; reset behavior; commands and configuration for an upstream reference; resource requirements and stopping behavior.

## Evidence

Separate implementation checks, upstream reproduction, empirical evaluation and independent reproduction. Link inputs, expected and observed outputs, numerical tolerances, reviewers and limitations for each.

## Uncertainty and failures

Parameter identifiability; sensitivity to assumptions; known failure modes; missing-data policy; unsupported parameter ranges; extrapolation risks; comparison with simpler alternatives.

## Attribution and distribution

Required citations and notices; permitted distribution of code, parameters and data; restricted components and instructions for authorized access; review date and unresolved rights questions.
