# Integrating models

OpenT1D's primary role is to provide tools for researchers to connect and assess suitable existing models. It accepts integrations based on usefulness, provenance and evidence. An upstream simulator, a controller or a biological module can all be meaningful contributions. A new OpenT1D model is optional research under the [tool-first direction](../decisions/0045-tool-first-research-platform.md), not a prerequisite for the laboratory.

## Candidate selection

Start with a concrete experiment. Identify what the candidate adds, which alternatives already exist and whether it should be integrated, improved upstream or reimplemented for a documented reason.

Assess scientific scope, actual software behavior and redistribution rights separately. Record the upstream revision, publication, parameter source, maintenance state, runtime and dependencies. A popular repository or open license alone does not establish scientific quality.

The initial candidates are simglucose for a first upstream reproduction and LT1's Cambridge/Hovorka implementation for a second physiological family. APS TestBed is an existing framework to assess for reusable capabilities. simglucose and LT1 Cambridge are integrated for bounded synthetic reference tracks, not endorsed for human prediction. APS TestBed remains a framework candidate. The [M0 source assessment](m0-assessment.md) records inspected revisions, execution hazards and proposed reproduction gates. Broader references and alternatives are in [the landscape review](../onderzoek/projectopzet.md#3-het-bestaande-landschap).

The [M3 Ridge card](models/m3-ridge.md) records the separate existing statistical estimator used for CGM-only forecast preparation. Neither physiological track is a justified human CGM adapter under the currently documented data constraints.

The [LIT-001 execution](lit001-results.md) traces published claims, parameters and model ancestry for conventional lispro kinetics. Its source-to-engine audit and numerically checked synthetic implementation prepare model choices; they do not establish a physiological improvement. The separate [LIT-002 decision](../decisions/0009-experimental-insulin-absorption.md) specifies the experimental coupling and its limited claims. The [source dossier](lit001-source-dossier.md) records population-model uncertainty and missing clinical inputs.

The [Pedersen–Cobelli model card](models/pedersen-cobelli2013.md) records the separate BC-001 evoked-secretion reference. Its published theoretical relationships and synthetic numerical checks do not establish T1D, transplant or coupled metabolic validity.

The [Polonsky C-peptide card](models/polonsky1986-cpeptide.md) records BC-003's forward observation model, nominal parameter profiles and known-input synthetic recovery. It is distinct from glucose-driven secretion and inverse reconstruction from human C-peptide measurements.

## Integration sequence

1. Complete a [model card](../templates/model-card.md) with unknowns explicitly recorded.
2. Run a documented upstream example without an adapter and preserve its environment and output.
3. Define the adapter's supported inputs, observations, actions and lifecycle.
4. Compare direct and adapted execution using a justified numerical tolerance.
5. Check supported combinations in an end-to-end experiment and document failures.
6. Evaluate the intended scientific application with suitable evidence.

Missing evidence may limit a contribution to exploratory use. Missing redistribution rights prevent distribution of the affected asset; they do not have to block work on an independent interface or synthetic example.

## Biological compatibility

Preserve tightly coupled physiology inside a whole-engine module when splitting it would introduce unsupported assumptions. Before connecting a smaller module, identify who owns each biological process, which compartment a quantity belongs to and how time and units are translated.

For example, an endogenous-secretion extension must account for its delivery route and any extraction already present in the metabolic model. It cannot be treated as an extra pump command without justification. The same caution applies to absorption already modeled by an engine and an added insulin formulation module.

## Attribution and maintenance

Record the original scientific and software authors. Preserve upstream notices and cite the model actually used. Document patches and distinguish upstream behavior from OpenT1D changes.

Each supported adapter will need an owner or a clearly stated maintenance status, a supported upstream version range and a small reference experiment. Changes to upstream equations, parameters or solvers must be checked for scientific impact rather than treated as ordinary dependency updates.
