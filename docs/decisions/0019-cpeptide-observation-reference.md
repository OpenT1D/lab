# 0019 — A forward C-peptide observation reference

Status: accepted for the user-requested next M4 contribution on 20 September 2026; biological applicability requires independent domain review.

## Context and decision

BC-001 supplies an illustrative evoked secretion reference; BC-002 verifies an insulin inlet. Neither establishes how residual secretion can be assessed from observations. Implement the small forward two-compartment C-peptide model specified by Polonsky et al. ([1986](https://doi.org/10.1172/JCI112308)), using its published analytical response and tabulated group-mean coefficients as explicit nominal profiles. The [BC-003 protocol](../research/m4-cpeptide-protocol.md) fixes the experiment before implementation.

Retain separate meanings for glucose-driven secretion, secretion-to-C-peptide prediction and reconstruction of secretion from measured C-peptide. This contribution implements only the second operation, plus bounded noiseless synthetic parameter recovery with known input. It adds no glucose feedback or therapy mechanism. Primary input is already a molar rate per body mass, so missing BC-001 scale/basal assumptions are not silently supplied.

Reuse the existing locked numerical environment and finite forcing representation. Keep ODE execution, published analytical kernel, sensitivity analysis and artifact-only reconstruction independently inspectable. Preserve the original physiological references. The paper and figures are inspected locally but not redistributed; original code is written from equations and process definitions.

## Alternatives, evidence and consequences

Van Cauter et al. ([1992](https://doi.org/10.2337/diab.41.3.368)) provide demographic population kinetics derived from normal, obese and non-insulin-dependent diabetic participants. The original full parameter procedure was not accessible in this search; its abstract is insufficient to implement it. It must not be relabeled a T1D parameter model. Hovorka et al.'s [ISEC (1996)](https://doi.org/10.1016/0169-2607(96)01755-5) addresses inverse secretion estimation and requires a separate method/asset review. A public modern [R implementation](https://github.com/kstier/isr.deconv) has a GPL-3.0 license and an inverse focus; it is not the 1986 authors' reference code and is not needed for this forward calculation. No upstream code is copied or executed here.

Polonsky's full paper supplies the required equations, units, experimental inputs and kinetic parameters, including a small T1D sample without clinically significant renal complications. That permits a bounded equation/stimulus reproduction; it does not supply raw concentration records or validate future residual-function or graft applications. Numerical use of printed mean parameters is distinct from reconstructing a mean of individual trajectories. The original article's inverse-error percentages will not be presented as OpenT1D results.

OT-025 gains a separate C-peptide reference with its own evidence record. BC-001's initialization and original-input gaps remain open. Revisit the model choice when the intended population, renal function, assay, stimulus or licensed observations favor another reference. Full OT-026 and M5 acceptance still require their biological questions and independent evidence.
