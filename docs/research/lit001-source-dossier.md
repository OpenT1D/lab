# LIT-001 source and parameter dossier

This dossier records source extraction and reference feasibility for [LIT-001](literature-research-plan.md), inspected on 20 September 2026. It is a bounded source review, not a completed clinical validation or an assertion that the reviewed models describe every adult with T1D. Search coverage and screening are recorded separately by the work package. No patient records, restricted data, author code or correspondence were acquired.

**Decision:** Faggionato et al. provides a usable specification for an independently implemented, explicitly synthetic single-bolus example. Exact reproduction of its individual fits or reported cohort response is not supported by the recovered assets. The Wilinska study provides an informative pump-related comparison, but source ambiguities and missing scenario inputs prevent selecting its published result for numerical reproduction.

The structured records are [sources.json](../../experiments/literature/lit001/sources.json), [studies.json](../../experiments/literature/lit001/studies.json) and [parameters.json](../../experiments/literature/lit001/parameters.json). They preserve source locations, units, statistical meanings, source hashes and unresolved information. The parameter record contains all 22 Table 2 estimates; only six fixed effects and the derived transfer rate are needed for the deterministic example.

## Source access and identity

| Source | Material checked | Role and limit |
| --- | --- | --- |
| [Faggionato, Schiavon and Dalla Man, 2021](https://doi.org/10.3390/metabo11040235), *Metabolites* 11(4), 235 | Full publisher PDF; equations, covariance, parameter tables and license visually checked | Main population-model specification; development and assessment reuse the earlier 116-person database |
| [Schiavon, Dalla Man and Cobelli, 2018](https://pubmed.ncbi.nlm.nih.gov/29989928/), DOI 10.1109/TBME.2017.2784101 | Abstract and bibliographic metadata; publisher/institutional access search | Earlier structural-model development; full original text not retrieved, so unreported equations and conventions are not attributed to a full-text check |
| [Wilinska et al., 2005](https://pubmed.ncbi.nlm.nih.gov/15651559/), DOI 10.1109/TBME.2004.839639 | Full journal-formatted PDF from a public Yale academic mirror; model equations and tables visually checked | Separate seven-person pump/bolus study; incomplete adult eligibility and parameter-table numbering ambiguity |
| [Wilinska, 2004 thesis](https://openaccess.city.ac.uk/id/eprint/30944/) | Chapter 5 and selected source pages in the institutional PDF | Earlier version of the same Graz study; ten candidates and selected model 9, unlike the journal's eleven candidates and selected model 10 |
| [Heinemann et al., 2012](https://pubmed.ncbi.nlm.nih.gov/21981286/), DOI 10.1111/j.1463-1326.2011.01516.x | Abstract and linked trial protocol | Original clinical origin of the first lispro control arm; not an independent test of the subsequent modeling work |

The Faggionato [publisher PDF](https://mdpi-res.com/d_attachment/metabolites/metabolites-11-00235/article_deploy/metabolites-11-00235.pdf) is attributed to Edoardo Faggionato, Michele Schiavon and Chiara Dalla Man and is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), verified in its first-page statement and Crossref metadata. Its equations and tabulated factual values are transcribed here with explicit OpenT1D interpretations; the original article is unchanged. Its original patient data remain restricted according to the article's Data Availability statement. Article licensing does not grant access to those records.

The Wilinska journal PDF states copyright 2005 IEEE. It and the thesis remain outside version control; their availability is not treated as an open code/data license. The [Schiavon institutional record](https://www.research.unipd.it/handle/11577/3255823?mode=complete) explicitly lists no attached full text. No supplementary code or author implementation was located in the checked Faggionato PDF. This describes the inspected assets, not an exhaustive claim that no code exists elsewhere.

Correction checks used DOI-specific correction/erratum searches, PubMed metadata and source consistency inspection. Crossref metadata for Faggionato and Schiavon contained no update or relationship record; Wilinska's Crossref request returned a rate-limit error. No formal correction or retraction was located. This bounded check cannot guarantee their absence, and the internal notation issues below remain unresolved.

## Clinical lineage and applicability

Faggionato's sections 2.1.1-2.1.3 and ethics statement link the three component studies to the following public trial records. The registered enrollment is kept separate from the modeling analysis count.

| Trial | Registry enrolled / model analyzed | Lispro administration used in model paper | Conditions and insulin assay threshold | Adult/formulation evidence |
| --- | --- | --- | --- | --- |
| [NCT01235039](https://clinicaltrials.gov/study/NCT01235039) | 43 / 42 | One 12 U injection | Overnight fast; clamp near 100 mg/dL; samples through 480 min; lispro-specific radioimmunoassay, 5 microU/mL quantification limit | Registry age 19-65; lispro arm explicitly 100 IU/mL |
| [NCT02146651](https://clinicaltrials.gov/study/NCT02146651) | 38 / 37 | One 0.2 U/kg injection | Overnight fast; clamp near 100 mg/dL; samples through 720 min; radioimmunoassay, 5.5 microU/mL limit | Registry age 18-64, male; Humalog control, concentration not located in checked records |
| [NCT02344992](https://clinicaltrials.gov/study/NCT02344992) | 38 / 37 | One 0.2 U/kg injection | Overnight fast followed by standardized meal; samples through 480 min; radioimmunoassay, 5.6 microU/mL limit | Registry age 18-64; Humalog control, concentration not located in checked records |

The last two trials also contain BioChaperone lispro administrations. Those accelerated-formulation visits must not be silently included in the conventional-lispro evidence group. Adult eligibility is supported by the trial protocols; individual records and compliance were not inspected. U100 is directly documented for the first study only in the material recovered here, so the entire pooled dataset is not labeled verified U100.

The exact participant exclusions that account for 43 versus 42 and 38 versus 37 were not established. Faggionato reports discarding all observations below the assay quantification limit and unreliable measurements associated with assay issues. The exact omission masks are unavailable. The article itself discusses an upward bias in empirical low percentiles associated with discarding below-limit values. Such plotted percentiles cannot be treated as uncensored raw observations.

The 2018 and 2021 publications are a shared model/data lineage. Three trial identifiers are not proof of independently sampled people across every trial: no participant identifiers were available for cross-trial deduplication. Preserve the authors' reported total of 116 while marking uniqueness as not independently verified. Only one analyzed lispro administration per person is represented in the 2021 model; its between-person variability does not estimate within-person or day-to-day variability.

Wilinska's journal study used seven people with T1D, nondetectable C-peptide and Humalog via an abdominal pump cannula. Six started after an overnight fast; one started in postprandial conditions at night. A 40 g carbohydrate meal and individual bolus preceded 12 hours of observation; infusion changed every 15 minutes and insulin was sampled every 30 minutes. The reported mean age, 31.7 years with SD 14.1, does not establish that all participants were adults. Its original individual age range and insulin concentration were not located. It therefore remains contextual evidence for the adult U100 target, rather than confirmed primary-scope evidence.

## Faggionato deterministic specification

The structural model is in Equation (3) and Figure 3 on PDF page 5, with the rate-ordering convention in section 2.3 on page 6. The first two states represent non-monomeric and monomeric subcutaneous insulin; the third represents plasma insulin. For a fixed parameter vector, the implemented interpretation is:

```text
dI_sc1/dt = -(k_a1 + k_d) I_sc1 + u(t - tau)
dI_sc2/dt = k_d I_sc1 - k_a2 I_sc2
dI_p/dt   = -k_e I_p + k_a1 I_sc1 + k_a2 I_sc2
y         = I_p / V_I
k_d       = k_a2 + alpha
```

The paper calls the states insulin masses and reports the volume in L/kg. A dimensionally consistent OpenT1D representation normalizes all states to mU/kg and input to mU/(kg min); output is mU/L, numerically equal to microU/mL. This normalization is an explicit interpretation, not an additional independently measured quantity. It avoids mixing a total-body mass with a body-weight-normalized volume.

**Source notation issue:** the printed plasma equation contains `k_a1(t)`, while the surrounding text, diagram and population equation define a per-person rate constant. The deterministic example interprets it as constant for a fixed person. The printed expression and this interpretation are retained in the machine record. No author confirmation or formal correction was obtained.

| Parameter | Fixed-effect estimate | Unit | RSE (%) | Meaning |
| --- | --- | --- | --- | --- |
| `tau` | 5.62 | min | 7.5 | Input delay |
| `V_I` | 0.135 | L/kg | 3.58 | Distribution volume |
| `alpha` | 0.0155 | 1/min | 10.5 | Positive difference between `k_d` and `k_a2` |
| `k_a1` | 0.000134 | 1/min | 36.9 | First subcutaneous compartment to plasma |
| `k_a2` | 0.0128 | 1/min | 3.43 | Second subcutaneous compartment to plasma |
| `k_e` | 0.113 | 1/min | 3.33 | Systemic fractional elimination |

These are Table 2 estimates, not six directly measured physiological constants. At zero random effects and zero covariate deviation, `k_d = 0.0283 /min`. The paper uses the ordering `k_d >= k_a2` to resolve exchangeable rate labels, and an informative prior on distribution volume during identification. Re-estimating the model would require reconstructing that prior and the estimation configuration as well as obtaining appropriate data.

## Population and observation specifications

Equation (12) on PDF page 9 defines each positive parameter as its population fixed effect multiplied by `exp(eta)`. For `k_a2` it additionally uses:

```text
k_a2 = k_a2_pop * exp(beta_BMI_k_a2 * (BMI - mean_BMI) + eta_k_a2)
beta_BMI_k_a2 = -0.0865 m^2/kg
```

The numerical cohort mean BMI was not found. It cannot be recovered by dividing mean weight by squared mean height. Setting BMI deviation to zero is a declared reference setting; it does not assign a known BMI to an original participant or recover the cohort's BMI distribution.

Random effects are multivariate normal with covariance Equation (13). Their standard deviations, ordered as `tau, V_I, alpha, k_a1, k_a2, k_e`, are `0.731, 0.319, 1.02, 1.86, 0.322, 0.303`. The only nonzero off-diagonal correlations are `rho(V_I,k_a2)=0.681`, `rho(V_I,k_e)=-0.579` and `rho(k_a2,k_e)=-0.506`; covariance entries equal the correlation times both standard deviations. These log-scale SDs differ from the RSE of the estimates. Independently sampling marginal parameter ranges would change the specified model.

Equation (7) uses measurement noise with standard deviation `sqrt(a^2 + b^2*y^2)`, multiplied by a standard-normal error in the observation model. Study-specific `(a,b)` values are `(1.96,0.0773)`, `(2.33,0.0516)` and `(2.77,0.0559)`, with `a` in microU/mL and `b` dimensionless. The deterministic example uses no measurement noise. Biological variability and this residual measurement model are kept distinct.

Table 3 contains summaries of fitted individual parameters, not complete individual vectors. Its column header `Q2` conflicts with the caption describing that column as the third quartile (75%); that ambiguity is recorded. No Table 3 vector is treated as an actual person, and no population-average response is inferred from a vector of averages.

## Alternative-model and missing-evidence assessment

Schiavon's abstract describes three candidates and a selected delayed two-subcutaneous-compartment model. It explicitly requests further assessment under variable delivery and multiple doses. Full original parameter and initial-condition conventions remain unavailable; the later explicit Faggionato specification is the selected executable source, rather than an assumed exact reconstruction of the 2018 implementation.

Wilinska's selected journal Model 10 splits input into two pathways, with saturable local degradation in both initial subcutaneous pools and systemic elimination. Its Table I has four state equations. However, Table III(a) labels are inconsistent with Table I/II and the discussion: the discussion's Model 10 absorption rates and fraction match values in table row 9; row 10 contains no absorption-rate values and resembles the empirical model. The thesis provides a plausible version-history explanation, but does not authorize silently renumbering the journal table. A complete numerical parameter mapping would require resolving the discrepancy. The exact variable inputs, individual initial states and parameter vectors for its example fit are also unavailable.

The Wilinska paper states that the two pathways have no immediate physiological interpretation. Its selected model's volume and elimination estimates individually raised plausibility concerns even though their metabolic-clearance product was retained as plausible. It is therefore evidence for comparing competing descriptions and their limitations, not proof that every modeled pathway was separately identified.

## Reference-feasibility verdict

| Candidate result | Verdict | Consequence |
| --- | --- | --- |
| Faggionato structural equations at a declared reference parameter vector | Feasible with explicit notation/normalization interpretations | Independent numerical implementation can be checked against an analytic or separately calculated response |
| Faggionato representative fitted individuals, Figure 4 | Incomplete | Original individual parameter vectors, covariates, input histories and observations unavailable |
| Faggionato cohort percentiles/predictive intervals, Figure 6 | Incomplete | Mean BMI, covariate distribution, censoring details and original simulation configuration unavailable |
| Wilinska selected-model example fit | Incomplete | Parameter-label ambiguity and original individual input/state information unresolved |
| Refit either original estimation study or claim new clinical predictive performance | Outside the recovered assets and this numerical case | Requires separately authorized data, estimation/evaluation protocol and suitable independent assessment |

The permitted standalone case uses a synthetic 0.2 U/kg bolus at time zero, no prior input, all-zero states, no measurement noise, zero random effects and zero BMI deviation. Converting the dose gives 200 mU/kg. Under an ideal impulse convention it enters the first subcutaneous state at `tau=5.62 min`. Those initial/history/event choices are explicitly synthetic; the corresponding clinical state was not recovered from the article.

The resulting curve can establish implementation behavior under those assumptions. It cannot be described as a reproduced published cohort curve, a validated U100 population, a personalized person or evidence that OpenT1D's existing physiological engines should be replaced. The next useful evidence is the missing source conventions and compatible independent insulin-concentration observations, not further tuning to the inspected development figures.

## Verification record

Public originals were downloaded outside the repository and identified by SHA-256 in the structured records. Faggionato's equations and Table 2 were compared with rendered pages; the selected covariance and Wilinska's model/table discrepancy were also visually inspected. Poppler rendered the first equation pages; PDFium supplied remaining renders after a local font-configuration failure. Extracted PDF text was used for navigation, not as the sole check of mathematical layout.

This extraction is AI-assisted internal work. A separate internal check of the executable source values is recorded by the numerical work package. No independent human scientific review, patient-level reproduction or source-author confirmation is claimed. The execution subsequently copied the checked original PDFs and available public source material into ignored `results/lit001/source-material/`; the [execution inventory](../../experiments/literature/lit001/execution.json) and source manifests record their hashes. Those local files are outside version control and are not a shared permanent archive. The full-text follow-up additionally distinguishes the thesis's adult glucose-modeling chapter from its age-uncertain insulin-kinetic chapter.
