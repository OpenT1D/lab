# Literature research plan: from evidence map to a lispro reference

Version 1.0, 20 September 2026. **Original plan for OT-023 / LIT-001.** The subsequent [execution and decision](lit001-results.md) records the completed bounded search, source dossier, engine audit and synthetic numerical verification, together with unresolved source access and the limits on published-curve reproduction. The prospective wording below preserves the original plan; use the execution report for actual outcomes. No patient data were acquired. The [roadmap](../../ROADMAP.md#follow-up-work-packages) remains the canonical implementation plan.

## 1. Purpose and intended result

Build a repeatable way to turn published research into traceable scientific specifications and bounded computational references for OpenT1D. Start with a short update of the existing T1D landscape, then investigate one physiological process in depth: subcutaneous delivery and absorption of conventional insulin lispro in adults with T1D, including the systemic kinetics required to compare a model with measured insulin concentrations.

The first package should enable a concrete decision: retain an existing model, improve its documentation, prepare a better justified sensitivity experiment, or propose a separately evaluated extension. A finding that published information is insufficient is also a useful decision, provided the missing information and its consequences are recorded.

The minimum deliverable is a completed evidence dossier and feasibility decision. A standalone numerical reference is an additional, conditional deliverable. Completion of the dossier must not be described as successful numerical reproduction when reproduction is incomplete or infeasible.

## 2. Position in the project

Use the [existing landscape report](../onderzoek/projectopzet.md), [model guide](models.md), [validation guide](validation.md), model cards and archived implementation evidence as starting material. Preserve historical reports and protocols; record newly checked evidence in the LIT-001 outputs.

| Existing track | Contribution from LIT-001 | Boundary that remains |
| --- | --- | --- |
| M0/M2 model ancestry | Trace insulin equations and parameter sources to the pinned implementations | Later papers do not automatically describe the versions in OpenT1D |
| M3 human evaluation | Identify measurements and study designs for a future physiological evaluation | Current M3/1 is CGM-only Ridge/persistence forecasting and cannot identify an absorption mechanism |
| C1 / OT-018 | Supply evidence about insulin-model assumptions and potentially informative robustness conditions | Controller hypothesis, comparator selection and evaluation remain separate work |
| Insulin-formulation extension | Establish a candidate specification and standalone reference | Coupling and product-specific claims need their own evidence |
| B1 / OT-020 | Inform a falsifiable mechanism hypothesis and a data-requirements assessment | A measured relevant limitation and reserved human assessment remain necessary under the roadmap |
| M4 and later biology | Provide a reusable evidence-extraction method | Lispro work does not establish endogenous secretion, graft function or immune mechanisms |

M3 and C1 keep their existing priorities. This preparation can advance alongside them without waiting for patient-data access or independent human M2 reproduction. Existing IV-001 parameter perturbations are engineering probes; this review does not retrospectively turn their factors into measured biological ranges.

This plan applies existing scientific conventions. A later change to shared coupling, process ownership or scientific conventions requires the decision record described in [Contributing](../../CONTRIBUTING.md); ordinary source checks and documentation corrections do not.

## 3. Questions and scope

### Primary question

Which published models and parameter descriptions are sufficiently specified and supported to reproduce a bounded conventional-lispro kinetic reference for adults with T1D, and how do they relate to OpenT1D's existing insulin models?

### Supporting questions

1. Which processes and observation mappings does each model contain: local absorption, degradation, systemic distribution, elimination and measurement?
2. Which equations and parameters were measured, estimated, fixed, inherited or introduced as assumptions?
3. Which observations support bolus delivery, continuous infusion, repeated doses and variability between or within people?
4. Which results can be reconstructed from publications, tables, supplements or reusable author code, and which require unavailable individual records?
5. What is already implemented in each pinned engine, and where are the scientifically meaningful differences or unresolved provenance gaps?
6. What additional observations would distinguish a proposed mechanism from parameter-only calibration or a simpler model?

### Eligibility boundaries

| Dimension | Primary scope | Treatment of adjacent material |
| --- | --- | --- |
| Population | Adults aged 18 or older with T1D | Mixed populations contribute to the primary evidence only when adult T1D results are separable; otherwise retain as indirect/background evidence |
| Formulation | Conventional lispro, with concentration and product recorded; U100 is the intended first reference | Other concentrations, accelerated lispro formulations and other insulin molecules remain separate evidence groups |
| Route | Subcutaneous injection or infusion | Intravenous material may inform systemic kinetics; it does not directly establish subcutaneous absorption |
| Input | A fully described single bolus is the preferred first executable scenario | Basal-plus-bolus and variable pump delivery are assessed separately and may require a later protocol |
| Observation | Time-resolved plasma/serum insulin with assay and baseline semantics | CGM and glucose-clamp infusion rates are contextual or later pharmacodynamic outcomes |
| Time | The source experiment's observation period, typically measured in hours | No arbitrary common horizon or extrapolation beyond the source window |
| Evidence | Original experimental and model-development reports, supplements, corrections and source code | Reviews locate original work; simulations are labeled as simulations; animal/T2D studies remain indirect |
| Language and access | No language exclusion at search; seek accessible originals or lawful repository copies | Record language/access limitations explicitly; abstract-only records can inform mapping but cannot support unreported equations or parameters |

The assay may measure lispro specifically, total immunoreactive insulin, or a baseline-adjusted quantity. Plasma concentration reflects absorption together with systemic distribution and elimination; it is not a direct measurement of absorption rate. Keep the observation model and those assumptions attached to every comparison.

The initial package covers literature synthesis, source-to-engine inspection and conditional standalone reproduction. Therapeutic comparisons, patient-specific fitting, controller optimization and production-engine replacement require subsequent task-specific protocols.

## 4. Brief landscape update

Update the existing landscape sufficiently to justify the first deep study and identify the next candidates. Cover five topics: exogenous insulin kinetics; meal/glucose appearance; activity and other short-term context; residual secretion/C-peptide; and defined cell/immune-therapy applications.

For each topic, produce one compact entry recording the research question, roadmap connection, original model sources, usable published quantitative material, principal evidence gaps and likely data dependency. Label information inherited from the existing report separately from information checked during this update.

Compare candidates on direct project usefulness, traceable equations, recoverable parameters/scenarios, opportunity for an informative comparison and effort required to obtain missing evidence. Use a reasoned comparison rather than a numerical quality score. The preferred lispro topic is provisional until this feasibility check is recorded.

Keep the overview to approximately two pages plus its source register. This is an editorial scope limit, not a cap on eligible studies in the deep review. Finish the update when each topic has a documented route or documented gap and the priority decision is explainable. Expand it only if a newly found dependency changes that decision.

## 5. Search and screening procedure

### Search freeze and coverage

Before systematic extraction, save the exact search strings, databases, date range, run dates and inclusion rules as the LIT-001 search protocol. Preliminary inspection has already exposed the anchor publications below; they are known material and cannot be treated as an untouched evaluation set. Version subsequent changes and retain their reason.

Use PubMed and Europe PMC as the primary freely accessible bibliographic searches. Use publisher and institutional repositories for original full texts, supplements and corrections. Supplement with reference-list tracing and forward citation searches using an accessible citation index, recording which service and version/date were used. General web search is a discovery aid; support scientific claims with the original source.

Search from database inception to the actual search execution date. Do not impose an arbitrary recent-year cutoff: parameter ancestry may be old. Search modern follow-up and correction records as well as the anchors. The search is a focused evidence review; do not claim exhaustive systematic-review coverage from a small web search. Use relevant [PRISMA-ScR](https://www.prisma-statement.org/scoping) and [PRISMA-S](https://www.prisma-statement.org/prisma-search) reporting items to make coverage and methods inspectable, recording omissions.

Starting PubMed queries to pilot and then freeze are:

```text
(lispro[Title/Abstract] OR Humalog[Title/Abstract])
AND (kinetic*[Title/Abstract] OR absorption[Title/Abstract]
     OR pharmacokinetic*[Title/Abstract] OR compartment*[Title/Abstract]
     OR model*[Title/Abstract])

("type 1 diabetes"[Title/Abstract] OR "type I diabetes"[Title/Abstract]
 OR "type-1 diabetes"[Title/Abstract] OR T1D[Title/Abstract])
AND insulin[Title/Abstract]
AND (subcutaneous[Title/Abstract] OR "continuous infusion"[Title/Abstract])
AND (model*[Title/Abstract] OR kinetic*[Title/Abstract]
     OR variability[Title/Abstract])
```

The first query leaves route and population eligibility to screening; the second helps find papers that omit the formulation from the title or abstract. Translate syntax for each database and retain the translated query and actual search interpretation/details. Run exact-title/DOI searches for anchors and their corrections separately. If the pilot misses an anchor, determine why and amend coverage before the main screening run. Record a final search/correction update before closing the dossier; screen new records under the same rules.

### Screening and study identity

Export citations and deduplicate publication records by DOI/PMID and verified bibliographic identity. Screen titles/abstracts, then full texts. Use explicit decisions: primary evidence, indirect/background, excluded with reason, or unresolved because information/access is insufficient. Record counts at each stage after execution; no search counts are assumed by this plan.

Maintain different identifiers for publications, underlying studies/cohorts and model versions. Link repeat reports, subsets and reanalyses. One source can describe several studies; several sources can describe one study. Retain overlap uncertainty rather than inventing a participant linkage. The [Cochrane data-collection guidance](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-05) explains why reports need to be linked to their underlying studies.

Follow references and citations of eligible model families through two documented rounds, screening new eligible records each time. If the second round reveals a new relevant model family or essential parameter source, record a targeted additional round. Finish when the frozen searches and declared tracing rounds are accounted for, including unresolved records. Do not stop because a desired number of supportive papers has been reached.

Retain contradictory results and failed model candidates where they inform the question. An inaccessible full text is a visible evidence gap, not proof that the study is scientifically irrelevant. Requests to authors or rights holders are possible later actions, not prerequisites for completing the desk-review gap report.

## 6. Preliminary source anchors

These are starting points, not a completed inclusion set or a final model selection. Preparation checked the Wilinska and Schiavon abstracts and the Faggionato full text. Exact equations, input histories and release assets must still pass the extraction and reproduction checks.

| Source | Reason to inspect | Preliminary limit |
| --- | --- | --- |
| [Wilinska et al., 2005, DOI 10.1109/TBME.2004.839639](https://pubmed.ncbi.nlm.nih.gov/15651559/) | Lispro kinetics with bolus and continuous infusion; several candidate structures | Small study; complete scenario and parameter availability need verification |
| [Schiavon et al., 2018, DOI 10.1109/TBME.2017.2784101](https://pubmed.ncbi.nlm.nih.gov/29989928/) | Absorption-model comparison following single subcutaneous administration | The authors explicitly identify variable delivery and multiple doses as further testing needs |
| [Faggionato et al., 2021, DOI 10.3390/metabo11040235](https://pmc.ncbi.nlm.nih.gov/articles/PMC8069884/) | Lispro population model with equations, parameter estimates and between-person variability; an [original full-text repository copy](https://research.unipd.it/retrieve/e14fb26e-d89d-3de1-e053-1705fe0ac030/metabolites-11-00235.pdf) is available | Reuses the 116-person database of the preceding model work; this is not an independent validation cohort. Individual records require separate permission |

The Faggionato specification is a promising reconstruction candidate, but the preliminary reading did not locate the numerical cohort-mean BMI needed for covariate centering. Initialization, input normalization and constituent-study eligibility also require checking. A declared synthetic response at zero covariate deviation would be a model implementation example, not reproduction of a reported cohort response. Population parameters do not recover the original fitted individuals; one analyzed administration per person does not establish within-person variability.

Also inspect the original references actually cited by the two pinned engines. The [simglucose card](models/simglucose.md) identifies UVA/Padova 2008 ancestry; the [Cambridge card](models/lt1-cambridge.md) identifies its Hovorka/Andersen implementation. A related later publication is a comparison source until correspondence with the installed code has been demonstrated.

## 7. Extraction and critical appraisal

### Traceable records

Begin with simple versioned tables or JSON/CSV records and a readable dossier. Use the existing model-card and experiment-protocol templates. A new database service, knowledge graph, search application or document-upload system is not needed for the first package.

| Record | Required information |
| --- | --- |
| Source | DOI/PMID, title, authors/year, publication version, correction/retraction check, access date, full-text status, applicable reuse terms |
| Study | Study/cohort identity, recruitment/site, enrolled/completed/analyzed counts and age, diabetes type/duration, treatment arm/visit, overlap links, intervention design, funding and relevant declared conflicts |
| Experiment | Formulation/concentration, route/site, dose and normalization, basal history, other insulin, fasting/meal/clamp conditions, sampling schedule, assay, quantification limits, excluded observations and handling of below-limit values |
| Claim | Exact page/section/equation/table/figure, concise paraphrase, population/conditions, supporting or conflicting evidence, use in OpenT1D, verification status |
| Model | Version/ancestry, states, equations, input and output definitions, compartments, initial/delay history, systemic kinetics, estimated/fixed terms, intended use |
| Parameter | Original symbol/value/unit, definition, normalization, estimated/fixed/inherited status, statistic type, uncertainty, correlations and exact origin |
| Reference target | Source identity and location, measured summary versus model curve, extraction method, time grid/window, baseline adjustment, display uncertainty, permitted comparison |
| Decision | Selected/rejected/unresolved option, evidence, reviewer/checker, date, dependencies and conditions that would change the choice |

Record missing values as unknown, with their consequence. Preserve original units next to any converted values and the conversion derivation. Distinguish quantities such as U, U/h, U/min, U/kg, concentration and mass. Do not use an assumed molecular or assay conversion without verifying its applicability to the insulin and reporting method.

Keep standard deviation, standard error, confidence interval, relative standard error, interquartile range, random-effect variance and residual measurement error distinct. A precision interval for an estimated parameter is not a distribution of people. Preserve transformations such as lognormal random effects and their covariance. Do not generate a population by independently sampling marginal ranges when the source model specifies dependence.

### Appraisal by intended use

Assess each source in a short matrix covering population/route applicability, design and measurement quality, equation completeness, parameter identifiability, uncertainty, comparator fairness, validation independence and reproducibility. Use explicit explanations for concerns and unknowns; avoid a single combined quality score.

Published authors' interpretations remain attributed claims. Distinguish fitting performance, checks on the same data, independent observations, theoretical plausibility and simulation experiments. Keep population-level and individual-level statements separate. Do not pool incompatible assays, doses, formulations or study conditions to obtain a more convenient mean curve.

### Extraction checking and AI assistance

Pilot extraction on two contrasting sources: a mechanistic model report and a population/variability report. Correct the record structure before scaling. A checker compares every equation, executable parameter, conversion and quantitative reference target with the original source. Check disputed screening decisions and all exclusions that could remove a model family. Log unresolved disagreements and their effect on conclusions.

AI may assist discovery, first-pass screening, extraction, algebra and code review. Record substantial use and verify extracted facts against the originals. A second agent can improve internal checking; it is not independent human reproduction or domain review. If only one researcher is available, a separate source-checking pass supports progress while the missing independent review remains explicit. Seek domain review before promoting a new biological interpretation, following the existing validation policy.

## 8. Source-to-engine audit

Audit the exact versions identified by the current model cards, preserving their revisions in the dossier. Follow the actual code and source tables rather than assuming that a simulator family name identifies a particular set of equations.

For each engine, map:

1. External command, modeled delivery and time interval into the native insulin input.
2. Subcutaneous states, absorption pathways, local degradation and delay.
3. Systemic distribution and elimination, including which module owns them.
4. Plasma/tissue insulin states and the relation to measured concentrations.
5. Parameter provenance, body-mass normalization, defaults and initialization.
6. The controller's internal model, where different from the simulated physiology.

Deliver a comparison table with source locations and classify each relationship as verified correspondence, documented difference or unresolved. Shared symbols are not sufficient evidence of equivalence. The external insulin rate is U/min in the simglucose boundary and U/h in LT1; retain each engine's native convention.

The first audit makes no physiological changes. A possible later coupling must identify which existing absorption/systemic processes are retained or replaced, avoiding double absorption or delay. Prefer existing upstream capabilities when suitable. Do not force both engines to share a new abstraction before a concrete compatible case exists.

## 9. Selecting and reproducing one reference

### Feasibility decision before coding

Rank candidate references by applicability, completeness and ability to resolve an OpenT1D question. The first executable reference needs:

- A verifiable model specification, all essential parameters, input history, initial conditions and required delay history.
- A defined observable and a source scenario with sufficient dose, timing, normalization and baseline information.
- A reconstructible numerical or graphical target, or an explicit statement that only implementation verification is possible.
- Usable rights for the intended code and retained/redistributed reference artifacts.
- A meaningful distinction between the model being implemented and the comparison used to check it.

Select one scenario and one main model first. A simpler published alternative may be added if its complete specification is available and it answers a declared comparison question. Record why a more elaborate model is needed before extending the candidate set.

Missing essential information makes a candidate an incomplete reference. Try the next eligible candidate or finish with a gap report. If extra assumptions support an exploratory example, enumerate them and label that example separately. Do not invent individual parameters to match an attractive figure.

### Different achievements and claims

| Achievement | Comparison | Permitted description |
| --- | --- | --- |
| Specification recovered | Source equations, tables, units and scenario reconstructed | Documented model specification |
| Implementation verified | Analytic/limiting checks and, where available, matching author code | Numerically checked implementation for the declared cases |
| Published model curve reconstructed | Recomputed model output versus its published curve/table | Reconstruction of that named model reference |
| Published observation summary assessed | Model versus compatible measured aggregate, with extraction uncertainty | Bounded agreement/disagreement with that summary; identify whether the study informed the model |
| New clinical predictive assessment | Reserved suitable human observations under a separate protocol | A claim restricted to that assessment, outside this initial reproduction |

The core experiment does not re-estimate parameters. A later fit to aggregate points is a new exploratory calibration and cannot substitute for individual parameter estimation. The response at population-average parameters need not equal the population-average response. Simulating a reported distribution may reconstruct a model population, but does not recover the original people or their precise random realization.

### Executable protocol and checks

Before the main run, freeze the selected source assets, equations, parameter set, scenario, observation transformation, outputs and acceptance criteria in a versioned protocol based on the existing template. Record any target already inspected. This is prospective computational specification after literature inspection, not a claim of untouched source evidence.

Prefer a reusable author implementation when available and suitable. Otherwise describe the implementation explicitly as an independent implementation of published equations. Use a separately locked runtime, keeping scientific dependencies out of the repository tooling environment.

Required checks depend on the equations and should include:

- Dimensional consistency and an explicit accounting of administered, retained, transferred and eliminated insulin where the model defines those quantities.
- Positivity and finite state under valid input, zero-input behavior, the specified basal/initial state, and reset reproducibility.
- An analytic solution or independently calculated special case when available; conditional linearity/superposition tests only for models that actually have that property.
- Correct handling of bolus events, rate changes and delays; solver/time-step refinement at fixed inputs.
- Agreement with the frozen reference over the declared common observation window, retaining failures and incomplete output.

Report concentration error over that window, exposure/AUC, peak magnitude and timing where the target supports them. Specify interpolation and integration rules. Use the source's endpoint definition or describe the comparison as a new analysis; do not infer absent peaks or tails. Finer plot sampling does not create additional independent observations.

Set tolerances from parameter rounding, graphical resolution/extraction repeatability and numerical refinement before the main comparison run. Record separate numerical and source-resolution contributions. If no defensible threshold can be specified, provide a descriptive discrepancy report rather than an invented pass/fail criterion. Any later revision is a recorded amendment; preserve the original criteria, results and all failed attempts when investigating differences.

### Figure extraction and preservation

Use original numerical tables or permitted author outputs ahead of digitization. For a figure, record page/panel, axis scale, units, image resolution, calibration points, extraction software/version and whether the line depicts data or a model. Check an independent second extraction or repeated calibration; keep uncertainty envelopes distinct from biological variability. Retain permitted extracted coordinates and the extraction procedure without redistributing source figures unless allowed.

Archive inputs, lockfile, source/code revisions, assumptions, conversions, commands, complete and failed outputs and a report-reconstruction procedure. Reconstruct the report from saved artifacts without rerunning the estimator or model. Keep restricted source material outside the repository; existing [data](data.md) and [licensing](../licensing.md) rules apply. A public article does not by itself grant rights to its original patient records or software assets.

## 10. Work packages and dependencies

The L1-L8 identifiers below are internal subdivisions of roadmap package OT-023. This table defines their planned acceptance criteria; the [execution report](lit001-results.md#acceptance-and-next-decision) records the assessed outcomes.

| Package | Work and tangible output | Depends on | Completion criterion |
| --- | --- | --- | --- |
| L1 — Frame and pilot | Freeze questions, scope, search/extraction pilot and evidence labels | Existing roadmap and sources | Protocol records known material, query coverage, decision rules and unresolved choices |
| L2 — Update landscape | Compact five-topic map and reasoned priority decision | L1 | Each topic has a source route or explicit gap; lispro priority confirmed or amended with reasons |
| L3 — Search and screen | Search exports, deduplicated bibliography, screening and study-overlap records | L1; L2 confirms focus | Declared searches/tracing accounted for, including exclusions and inaccessible records |
| L4 — Extract and appraise | Checked claim/parameter/model records, source dossiers and contradiction table | L3; can process screened batches | Every conclusion/executable item has source location, context, uncertainty and checking status |
| L5 — Audit engines | Pinned source-to-engine mapping and process-ownership assessment | L1; reconcile with L4 | Relevant insulin paths and provenance are traced or explicitly unresolved in both engines |
| L6 — Choose reference | Candidate comparison and standalone protocol or infeasibility report | L4, L5 | One fully specified bounded case selected, or essential gaps recorded without invented inputs |
| L7 — Reproduce conditionally | Isolated implementation, meaningful checks, artifacts and reconstruction report | L6 has an executable case | Declared reference assessed with criteria, discrepancies and failures retained; outcome labeled accurately |
| L8 — Synthesize and decide | Final evidence dossier, acceptance mapping and recommended next package | L2-L6; L7 outcome or documented infeasibility | Each research question answered or bounded; next action and its evidence needs are explicit |

L2 and the initial L5 code inspection can run alongside bibliographic work after L1. Extraction can advance in screened batches. Model selection depends on checked evidence; parameter edits, experiment freezing and final interpretation remain sequential. Automation/agent parallelism does not replace a recorded checker or resolve scientific dependencies.

## 11. Decision points and completion

| Point | Proceed when | Alternative outcome |
| --- | --- | --- |
| D1 — Topic feasibility | The focused lispro dossier can inform a useful project decision, including a consequential evidence-gap finding | Narrow the question or change topic only if its expected decision value is insufficient; numerical infeasibility alone does not require switching |
| D2 — Source completeness | Essential model/scenario/observable information is checked | Record missing items; use another candidate or produce specification-only output |
| D3 — Numerical interpretation | Differences are characterized under the frozen criteria | Report disagreement, incomplete reconstruction or source ambiguity; retain failed variants |
| D4 — Project action | Findings support a precise useful next experiment or documentation change | Retain the current engines and identify the highest-value missing information |

These are scientific decision criteria, not additional approval ceremonies. Routine work proceeds within the authorized scope and existing project rules. New patient access, external correspondence and a change to the intended clinical use are separate actions.

Final dossier acceptance requires all of the following:

1. A versioned scope, executed search record, study/publication linkage and a bounded landscape update.
2. Traceable claims, parameters and uncertainties, with contradictory and unavailable evidence retained.
3. A checked mapping to both existing engines without overstating parameter ancestry or population equivalence.
4. A documented reference-feasibility verdict and, if attempted, a complete record of numerical outcomes and failures.
5. An evidence table separating literature mapping, specification, numerical verification, source reconstruction and independent empirical assessment.
6. A recommendation to retain, clarify, investigate sensitivity or propose an extension, with the required next evidence.
7. Working documentation links and repository checks; numerical checks only when numerical work has actually been added.

A positive model-improvement verdict is not required for research completion. If no candidate is reproducible, the dossier can be complete while numerical reproduction remains unavailable. A second person's independent execution and biological review retain their separate status and scope.

## 12. Deliverables and repository organization

This document is the canonical plan. Extend the roadmap only with package status and links; avoid duplicating detailed instructions. Keep the historical Dutch research reports intact. New public guides and dossiers are in English.

During execution, create a readable LIT-001 results dossier linked from the documentation table of contents, a source register, extraction records, study/model relationships, an engine comparison and a decision/acceptance record. Use ordinary versioned files initially. Final filenames and a minimal record schema are chosen in L1 after the extraction pilot; no machine-readable schema or evidence database is claimed as implemented by this plan.

If L7 proceeds, add a separately locked standalone experiment and its documented artifact manifest. Keep large/raw source assets and restricted records in appropriate external storage, while publishing permissible metadata, code, synthetic mechanics and reconstruction instructions. A later coupling proposal should reuse the model-card/protocol conventions and explain why an existing upstream capability is insufficient.

Do not build a general literature application, retrieval service or automatic updater as a prerequisite. Consider shared tooling only after a second dossier shows which fields and operations actually repeat.

## 13. Capacity and first execution sequence

No staffing, partner or calendar commitment is assumed. Plan for four functions: evidence extraction/synthesis, numerical implementation, source/technical checking and biological interpretation. A person can cover more than one function; record actual reviewers and avoid describing agent checks as external review.

As a planning allocation, spend roughly 10% of effort on the broad map, 50% on the deep review and engine audit, 30% on conditional reproduction and 10% on synthesis/checking. These are effort priorities, not measured estimates or fixed quotas. If reproduction is infeasible, report that promptly and reallocate only after revising the deliverables.

The first execution batch is concrete:

1. Create the search log and pilot extraction records; list all sources already inspected while preparing the plan.
2. Retrieve and inspect the lawful full texts/supplements of the three anchors, including their cohort ancestry and exact formulation/age eligibility.
3. Pilot extraction on two papers and trace one relevant insulin path in each pinned engine.
4. Run and preserve the main search; use the pilot to estimate remaining extraction/checking effort from the actual eligible records and complexity.
5. Finish the broad map and issue D1 before committing to the full numerical effort.

At each package boundary, report completed outputs, unresolved evidence and the next decision. Estimate calendar needs only after the pilot, using available researcher/checker capacity, candidate complexity and source-access delays. A useful forecast separates active analysis time from waiting for external material.

## 14. Principal risks and responses

| Risk | Response |
| --- | --- |
| The overview expands into an unbounded survey | Keep the five-topic map short and require a decision-relevant reason for expansion |
| Positive studies or convenient models dominate selection | Freeze searches/eligibility, preserve competing models and negative/inaccessible results |
| Shared cohorts appear to provide independent confirmation | Maintain study-level links and mark unresolved overlap |
| An absorption parameter absorbs errors in clearance or the assay | Trace the complete observation pathway and assess identifiability/alternative explanations |
| Published variability is converted into an unjustified virtual population | Preserve statistic type, covariance and covariate domain; label unsupported sampling exploratory |
| A mean curve is treated as an individual or an unseen validation set | Preserve aggregation and source role; separate fitting/reconstruction from independent assessment |
| Missing scenario or initial conditions are silently guessed | Record the missing inputs; change candidate or issue an incomplete-reference verdict |
| A standalone model duplicates processes when coupled | Map process ownership first; test a future coupling under its own protocol |
| Source/API/tool availability changes | Preserve query exports and permitted artifacts, record access failures and use original-source alternatives |
| AI extraction appears plausible but is wrong | Check equations, numeric values, source locations and conversions against original material |
| Literature work is promoted to human predictive validity | Apply the named evidence categories and preserve M3/B1 acceptance requirements |

## 15. Follow-up choices

L8 should recommend one immediate next step and explain why it has the strongest evidence-to-effort case:

- **Clarify and retain:** improve parameter ancestry and model documentation while preserving the current physiology.
- **Study sensitivity:** define source-supported, internally consistent scenarios, with exploratory labels where population relevance is unproven.
- **Propose an extension:** specify one process change, an unchanged and parameter-only comparator, coupling ownership and the observations needed to evaluate it.
- **Resolve a data gap:** identify the precise missing measurement or study asset and the access route, without treating access as already granted.

Choose the next deep literature topic after this decision. Residual secretion/C-peptide is a plausible later candidate because of the long-term biological direction, but its priority depends on the map and the measurements required for its own question. Preserve a reusable evidence method while letting each new research question determine the scope.
