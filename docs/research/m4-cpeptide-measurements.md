# M4 C-peptide measurement and review specification

This is preparation for observation assessment after [BC-003](m4-cpeptide-results.md). The subsequent [BC-004 paired protocol](m4-paired-protocol.md) freezes the synthetic input/baseline contract and specifies the conditional empirical analysis. It authorizes no clinical experiment, data request or contact. No research collaboration currently follows from this document. The [existing unsent brief](m4-collaboration-brief.md) remains the collaboration entry point; the questions below make its measurement request concrete.

## First empirical question

For an explicitly defined residual-function T1D population, does a frozen secretion-to-C-peptide observation model explain held-out concentration dynamics better than the prespecified simpler comparator, while respecting uncertainty in kinetics, assays and input? A known-input C-peptide kinetics dataset would first test the observation model separately. A spontaneous glucose/C-peptide series alone combines uncertain secretion and kinetics; it is not an equivalent kinetic calibration experiment.

First agree the population, renal-function criteria, stimulus and endpoint with domain reviewers. Do not combine healthy, T2D, residual T1D and transplant records into one interchangeable validation cohort. No quantitative clinical performance threshold is frozen without assessing permitted data and assay precision.

## Required records and why they matter

| Record | Minimum content for feasibility review | Purpose |
| --- | --- | --- |
| Glucose and C-peptide | Paired laboratory values, exact elapsed timestamps, original units, specimen type, missing-value flags | Drive secretion and compare its observation branch without interpolated CGM being mistaken for plasma glucose |
| Kinetic stimulus, if present | Actual administered C-peptide amount/rate, timing, formulation and body mass | Distinguish known-input kinetics from reconstruction of unknown secretion |
| Challenge conditions | Fasting duration, glucose/meal composition and dose, oral/IV route, start/end times, sampling schedule | Avoid imposing an IVGTT secretion model on an oral or mixed-meal test without justification |
| Baseline | Repeated prechallenge paired samples and recent treatment/food | Establish baseline convention and check an equilibrium assumption |
| Insulin treatment | Formulation, dose, route, timing, pump/infusion changes and relevant assay cross-reactivity | Separate administered insulin, endogenous secretion and their effects on glucose |
| Assay and handling | Assay identity/calibration, detection/quantification limits, precision, batch, collection/processing/storage | Model measurement error and censoring; a below-limit value is not exact zero |
| Participant context | Body mass, age, relevant diabetes duration and renal function with timestamps; permitted pseudonymous linkage | Assess per-kg normalization and clearance applicability |
| Transplant context, when applicable | Graft site, product/procedure, dates, immunosuppression and concurrent treatments | Define an actual therapy/population question without inventing a survival or immune mechanism |
| Governance | Versioned dictionary/protocol, actual available variables, consent/use restrictions, authorization and permitted derived outputs | Establish usable access before execution or redistribution |

The 1986 known-bolus schedule spans 2–180 minutes with dense early sampling; it is a historical reference, not a clinical sampling recommendation. BC-003 compares that schedule with an early-only window and three samples. For a future observational protocol, request both early dynamics and a late decay window, plus prechallenge values. Final timing and burden require clinical review. Known stimulus, late observations and precision matter as much as sample count. No C-peptide administration study is proposed for execution here.

## Existing sources and access verdict

| Source | What is actually available/established | Fit and unresolved access |
| --- | --- | --- |
| [Polonsky 1986](https://www.jci.org/articles/view/112308) | Public full article inspected; process definitions, coefficients, sampling and infusion schedule | Suitable for equation and nominal-stimulus replay. Raw participant series and body weights were not found; no data reuse permission inferred |
| [Van Cauter 1992](https://doi.org/10.2337/diab.41.3.368) | Primary abstract and bibliographic record; complete original parameter procedure not retrieved in this search | Population model for normal/obese/non-insulin-dependent diabetes; insufficient original specification and no T1D applicability established |
| [NIDDK CIT-07/08 catalogue](https://repository.niddk.nih.gov/study/92) | Public protocol/laboratory manual and catalogue assessed in the [BC-001 dossier](m4-evidence-dossier.md); no authorized participant data | Relevant transplant setting, but availability of required variables and permission remain unverified. Catalogue access itself failed during this BC-003 check, so prior document inspection is not fresh access confirmation |
| Local OpenT1D synthetic traces | Fully declared generated data; no patient records | Useful for numerical checks and synthetic recovery, not independent empirical validation |

The CIT protocol records posttransplant IVGTT C-peptide at baseline **-10, -5 and -1 min**, then 1, 2, 3, 4, 5, 7 and 10 min. This exact baseline schedule replaces the earlier shorthand “0” after the BC-004 source recheck. Longer insulin/glucose sampling does not supply a missing C-peptide decay window. [BC-015-P4](m4-sampling-window-results.md) quantifies the consequence for one synthetic known-pulse kinetic problem; it does not infer the information content of actual CIT-07 records. A Miami mixed-meal substudy describes later C-peptide sampling, but actual released fields, completeness and access have not been verified, and its stimulus is not BC-001's declining IVGTT condition. A public study page is neither data delivery nor authorization. The repository's existing access gates remain in force; no application or restricted download was made.

## Paired protocol source check

BC-004 rechecked the following primary material on 20 September 2026. Polonsky's publisher PDF was accessible; the NIDDK catalogue returned HTTP 403 and the public document URLs could not be retrieved through the web tool. The already inspected local public-protocol copies were reread; no participant files were accessed and no current data-release availability is inferred.

| Candidate | Exact observed information | Verdict for the proposed paired question |
| --- | --- | --- |
| Polonsky known-input C-peptide experiments | Paper pp. 99–100: known exogenous stimulus, C-peptide decay sampling through 180 min, separate insulin/glucose sampling, pre-infusion baseline subtraction and individual kinetic estimation | Supports kinetic reference design. No raw paired participant records or reuse permission located; exogenous C-peptide administration is not a paired equimolar insulin stimulus |
| CIT-07 posttransplant FSIGT | Protocol v8 pp. 81–82: baseline -10/-5/-1 min; C-peptide only through 10 min; insulin/glucose continue to 180 min, with exogenous insulin at 20 min | Early response could be a distinct question. This schedule does not establish the late C-peptide series needed for this dynamic paired assessment; administered insulin must be separated |
| CIT-07 core MMTT | Protocol v8 pp. 80–81: glucose/C-peptide at baseline, 60 and 90 min | Sparse endpoints cannot supply the proposed full kinetic assessment; oral stimulation requires a different secretion model |
| CIT-07 Miami MMTT substudy | Laboratory manual v8 p. 13: paired serum glucose/C-peptide at 15, 30, 60, 90, 120, 150, 180, 210, 240, 270 and 300 min, with separate fasting samples | Promising for a separately specified oral question; actual participant coverage, insulin measurements, assay fields, renal information and authorized access are unverified |

The CIT-07 test clock places glucose injection at -30 seconds (protocol p. 82). Preserve that source clock and the actual stimulus timestamp; do not silently relabel its sample times as minutes after an assumed zero-time injection. This matters when constructing paired records or driving a secretion model.

Inspected local document hashes: [CIT-07 protocol v8](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_Protocol_Version_8.0_20Aug12.pdf), SHA-256 `bcc4dac6540a00a43663318fa552f24de4cec24772934cd535fd1509e541c4d7`; [laboratory manual v8](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_SpecificLabManualv8.0.pdf), SHA-256 `6f0aa490a417d9b8f03ee8e832a7939f3b54da0b230a9c645b44127ab5f6cb85`. Only factual schedule information is transcribed; the documents are not redistributed. The [Polonsky model card](models/polonsky1986-cpeptide.md) preserves its original PDF identity.

No candidate currently meets all four requirements: verified usable paired variables, appropriate stimulus/population, documented authorized access and a prespecified independent evaluation allocation. This is a current feasibility verdict, not proof that suitable data do not exist. The next external step, if separately authorized, is a metadata/rights inquiry about existing observations rather than a patient-data download or a new clinical test.

## Analysis and independent evaluation plan

1. Review only permitted metadata first: confirm units, timestamps, stimulus, population, assay and renal information. Freeze inclusion/exclusion and missing/censored-value handling before fitting.
2. Separate kinetics from secretion where known-input information permits. Otherwise state which coefficients are fixed externally and quantify the resulting assumptions; do not jointly estimate an unrestricted input and all kinetics from one concentration curve.
3. Split by participant before development. Reserve independent participants or an independent study for evaluation; repeated samples or visits from a participant must not leak across those roles. Freeze the model, scale/baseline, comparator, fitting method, noise model and endpoints before held-out execution.
4. Compare held-out concentration time courses, residual patterns, concentration integrals and uncertainty under the same inputs. Check censoring and missingness. Use assay-informed error criteria and uncertainty coverage; a refit to the development curves is not validation.
5. Assess sensitivity and practical identifiability with the actual sampling, noise and parameter correlations. Report failed fits and boundary solutions. The BC-003 noiseless recovery and local rank are only preparation.

## Concrete review request and next interface

Ask a C-peptide secretion/kinetics group: “For residual-function T1D or a separately defined islet-transplant cohort, which kinetics and basal convention are defensible, and is there an existing, legally shareable paired glucose/C-peptide dataset with early and late samples, assay/renal metadata and an independent evaluation subset? Could you review our forward equations, nominal-profile use, equimolar appearance assumption and the distinction between known-input calibration and unknown-secretion reconstruction?” This is an unsent question, not an access application.

A kinetic modeller should review model choice and identifiability; an endocrinologist and, for graft applications, a transplant specialist should review population, stimulus and route; an assay specialist should review units, processing and limits; a statistician should review splits, noise and uncertainty. Resolve BC-001's initialization and whole-body/basal scale with the primary source or authors' clarification before treating its output as total secretion.

The [BC-004 observation contract](m4-paired-protocol.md) now carries secretion in pmol/min, body mass, baseline convention and equimolar-processing assumption into **two distinct input requests**: insulin for the verified BC-002 inlet and C-peptide for BC-003. Its [executable preflight](m4-paired-results.md) checks conversion, bookkeeping and proposed initial states. The C-peptide branch owns its distribution and removal; insulin retains its own hepatic/distribution processes. [BC-005](m4-paired-kinetics-results.md) now executes both kinetic branches and verifies a separate nonzero-initial-inventory insulin wrapper for the synthetic-total case, preserving BC-002 unchanged. Review the biological assumptions and resolve source scale before full glucose feedback.

Later OT-027 must select an actual treatment, population, graft site and observable endpoint. A hypothetical capacity multiplier can explore mathematical sensitivity; it cannot represent engraftment, immune protection, cell survival or a therapy outcome without separate evidence.

## Conditional joint-recovery evidence

[BC-011](m4-joint-identifiability-results.md) now compares shared synthetic G, G+I and G+I+C-peptide observations under exact basal G/I and fixed nuisance physiology. C-peptide improves separation in the specified examples, while noisy G/GI fits often reach clearance bounds despite locally resolved sensitivities. This supports assessing joint measurements and independent kinetic information; it does not validate a clinical sampling schedule, assay noise model or human inference. [BC-012](m4-volume-sensitivity-results.md) now compares fixed-correct, fixed-wrong and unknown central C-peptide volume. In the synthetic estimated-rate cases, a wrong fixed volume is partly absorbed by biased removal rates, and free volume reduces precision despite full local numerical rank. [BC-013](m4-profile-likelihood-results.md) now executes conditional nuisance profiles within that model. It finds both closed and bound-limited volume contours, and some interior rate/gain endpoints depend on the nuisance-volume limit. Those two development examples did not assess coverage; [BC-014](m4-coverage-results.md) has since measured conditional synthetic gain inclusion on new draws, without establishing human coverage. [BC-015-P1](m4-measurement-readiness.md) checks public source metadata, and [BC-015-P2](m4-cit07-public-crosswalk.md) verifies the public CIT-07 dictionaries: they do not establish a same-challenge dynamic glucose/insulin/C-peptide release. Independent volume/kinetic information, repeated basal measurements, actual observation access and external domain review remain open; the ±20% volume stress is not an empirical human uncertainty distribution.
