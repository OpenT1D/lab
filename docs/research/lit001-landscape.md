# LIT-001 landscape update

Version 1.0, 20 September 2026. **L2: bounded source map completed.** This update supports the topic decision in the [LIT-001 plan](literature-research-plan.md). It is a targeted verification of five source routes, not the completed lispro search, an exhaustive T1D review or numerical reproduction. No patient records were acquired.

## Scope and source checking

The five topics and their project connections are inherited from the [Dutch research report](../onderzoek/projectopzet.md), especially its landscape and later-extension sections. That report remains unchanged. The original publications below were rechecked during this update; the Dalla Man meal paper adds a more specific source route. Access depth is recorded explicitly because finding a publication does not establish that every equation, parameter or executable asset is available.

| Original source and inspected version | Material rechecked on 20 September 2026 | Remaining access/specification limit |
| --- | --- | --- |
| Faggionato et al., 2021 journal article | Europe PMC full-text XML: methods, equations and parameter tables | Complete scenario and cohort eligibility still require the deep dossier |
| Dalla Man et al., 2007 journal PDF, hosted by the ISB research group at Linköping University | Main text; Table I and equation (13) also checked visually | Gastric-emptying function traces to the paper's reference 17 |
| Rashid et al., 2019, PMC author manuscript available in 2020 | Methods, Appendix 1, Table A-1 and limitations | Current code/parameter releases and manuscript-to-release correspondence unverified |
| Breda et al., 2001 original-study abstract in PubMed | Method, measurements and sampling comparison | Complete equations and parameter tables not rechecked |
| Shoda et al., 2010 PMC journal text | Model scope, parameter provenance and supplement description | Linked full-model supplement and runnable assets not retrieved |
| Reichman et al., 2025 original-study abstract in PubMed | Intervention, mixed-meal assessment and analysis limitations | Publisher returned an access error; full text and supplements not inspected |

Direct web access was intermittent. Public Europe PMC XML and PMC article retrieval resolved the first, third and fifth routes; indexed PubMed abstracts supported the two abstract-only checks. No claim of executable completeness follows from this map.

## 1. Exogenous insulin kinetics

[Faggionato et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC8069884/) describe a lispro model combining subcutaneous compartments, systemic elimination, delay and a population variability model. Equations (3), (12) and (13), and Table 2 expose a concrete structural and parameter route. The article explicitly restricts access to the underlying individual data. Its covariates, correlations and parameter transformations must remain attached to any reconstruction; reported population parameters do not reproduce the original fitted individuals.

**Answerable first question:** which complete published specification can produce a checked concentration response under a declared lispro input, and how does its process description relate to the pinned engines? This can yield useful ancestry or numerical evidence from papers. Individual calibration and predictive assessment require suitable insulin concentration measurements, dosing history, assay information and population context. This topic has the strongest immediate connection to the existing insulin pathways and the narrowest practical first boundary.

## 2. Meals and glucose appearance

[Dalla Man, Rizza and Cobelli, 2007](https://pubmed.ncbi.nlm.nih.gov/17926672/), with an [original journal PDF](https://isbgroup.eu/files/Dalla%20Man%202007.pdf), provide a detailed glucose-insulin meal model. Equation (13) specifies stomach/gut transit and glucose appearance; Table I reports parameters. The gastric-emptying function also requires its cited predecessor. The reference parameterizations describe average normal and T2D subjects; they are not adult T1D population estimates. This distinction matters when tracing the ancestry of later T1D simulators.

**Useful next question:** which assumptions about meal appearance drive an observed difference between the current engines under a fully specified meal? A paper-based structural comparison is feasible. Establishing a correction for T1D would require appropriately characterized meals, insulin and glucose observations, with tracer-derived appearance measurements where the question requires separating appearance from disposal. Meal composition and incomplete event records complicate identification. This is the nearest alternative if the insulin dossier cannot support a useful decision.

## 3. Activity and short-term context

[Rashid et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC7449052/) extend Hovorka-type dynamics with immediate and persistent activity effects driven by heart-rate information. The inspected author manuscript includes equations in Appendix 1 and variable/parameter definitions in Table A-1. Some personalized entries are interquartile ranges, not complete joint participant parameter sets. The study describes model development using adults with T1D and moderate aerobic exercise; this does not establish coverage of all activity, illness, stress or sleep conditions.

**Useful next question:** under a declared exercise/recovery scenario, what behavior is attributable to the added activity states compared with the unchanged and parameter-adjusted model? Empirical evaluation needs synchronized activity intensity/type, heart rate, glucose, insulin and meal information. Mapping the current Python implementation to this manuscript remains separate work. The route is promising for later C1 robustness questions, but introduces more inputs and physiological coupling than the first lispro reference.

## 4. Residual secretion and C-peptide

[Breda et al., 2001](https://pubmed.ncbi.nlm.nih.gov/11147781/) provide an original route from sampled glucose, insulin and C-peptide during an oral glucose tolerance test to secretion and sensitivity indices. The abstract describes a small methodological sampling comparison; it does not establish performance for OpenT1D's adult T1D application. Complete equations and parameters remain a source-retrieval task for a later dossier.

**Useful next question:** what residual secretion can a specified dynamic test identify under defensible C-peptide kinetics? That requires measured C-peptide with assay limits, glucose and a documented stimulus, alongside the characteristics needed by the kinetic model. A later metabolic coupling must distinguish endogenous delivery and extraction from subcutaneous insulin. This remains a strong bridge to the biological roadmap, with greater measurement and coupling dependencies than lispro.

## 5. Defined cell and immune applications

[Shoda et al., 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2909407/) offer a literature-based immune/beta-cell model of the NOD mouse. The article describes equations and source attribution in supplements, including a full-model file; their current usability was not checked. Its animal population and disease-development scope prevent treating it as a human therapy module.

For a distinct human application, [Reichman et al., 2025](https://pubmed.ncbi.nlm.nih.gov/40544428/) report a stem-cell-derived islet study with portal infusion, immunosuppression and mixed-meal C-peptide assessment. The abstract identifies interim, non-prespecified analyses. It supplies an outcome/protocol route, not a complete graft or immune-system model.

**Useful later question:** can a bounded secretion model describe a defined post-transplant stimulation response? That requires longitudinal functional measurements, treatment and graft context, and a justified observation/coupling model. Immune-intervention prediction additionally needs disease-stage and mechanism-specific evidence. These are separate research questions; combining them now would expand beyond the available physiological foundation.

## Priority decision

**Retain conventional lispro as the first deep dossier.** The directly inspectable equations and parameter descriptions, existing engine connections and bounded concentration output offer a useful decision even if exact numerical reconstruction proves infeasible. Meals are the closest alternative; activity follows when the intended controller question needs it. Residual secretion and defined therapy applications remain question-dependent later work.

Revisit this choice if checked insulin sources cannot resolve a meaningful ancestry, sensitivity or specification question, or another topic addresses a demonstrated project limitation with better evidence. Missing numerical inputs alone do not require abandoning a useful evidence-gap dossier. This decision preserves [M3 and C1 priorities](roadmap-history-2026-10-28.md#development-sequence-after-m2). Current CGM-only M3/1 cannot identify an absorption defect, and L2 does not satisfy B1's human-assessment requirements.
