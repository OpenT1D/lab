# M3 data feasibility

Public-source review: 19 September 2026. No patient records, access request, correspondence, agreement acceptance or download occurred. No `data/` directory exists in the inspected checkout. The historical [M0 card](m0-data-fit.md) remains unchanged. This assessment selects a **conditional OhioT1DM 2018-cohort, CGM-only forecasting study**; an authorized release has not been verified.

## Question before acquisition

Can a fixed ridge-regression procedure using the preceding 30 minutes of CGM predict CGM 30 minutes ahead more accurately than persistence during later periods of the same six adults? This is a modest descriptive forecast assessment under recorded care, not a population efficacy trial or a physiological-mechanism test. It requires no invented meals, insulin delivery, body weight or mapping to virtual patients. The [protocol](m3-protocol.md) specifies the analysis before any human evaluation.

## Candidate comparison

| Property | Direct DCLP3 | Direct OhioT1DM | MetaboNet aggregate |
| --- | --- | --- | --- |
| Fit | CGM forecasting possible; meal-driven physiology not supported by assessed documentation | Small established forecasting cohort; selected provisionally | More data adds overlap and harmonization obligations without answering this small question better |
| Glucose / sensor | CGM with special high/low indicators; native release still unchecked | Five-minute Medtronic Enlite CGM; finger sticks are separate | Harmonized CGM; original censoring recovery unverified |
| Insulin | Commanded basal and bolus records; extended-bolus duration uncertain | Basal settings, temporary basal and bolus records; recorded dose is not independently measured tissue delivery | Amounts in preceding five minutes require source-specific interpretation |
| Meals | Complete usable carbohydrate field not established | Self-reported times and estimates; absence never proves no meal | Source-dependent; harmonization cannot restore unobserved events |
| Profiles | Native dictionary and released cohort unchecked | Actual weight unavailable; 99 is a placeholder | Source-dependent, including inherited placeholders |
| Time | Local/adjusted device clocks; corrections need native verification | Shifted participant dates; retain local elapsed clock and isolate discontinuities | Cross-source time alignment needs verification |
| Missing / invalid | Preserve zero-plus-indicator meaning and missingness | Sensor gaps and unverified censoring conventions; do not interpolate | Processing may obscure original flags |
| People / usable periods | Trial enrollment does not establish released or usable count | Owner describes 12 people, eight weeks each; six 2018 participants selected, usable periods unknown | Not independent of its source studies |
| Rights | Current request page requires identity, use description and click-through terms | Institutional-email request route; historical descriptor requires institutional DUA | Aggregate and original-source terms both need review |
| Publication / commerce | Current terms require attribution/disclaimer; release-specific permissions unresolved | Research distribution described; redistribution, commercial use and derived-output permissions unresolved | No inference of commercial or redistribution rights from availability |

Primary source links: [JAEB access and terms](https://public.jaeb.org/dataset/573), [Ohio owner/access page](https://webpages.charlotte.edu/rbunescu/data/ohiot1dm/OhioT1DM-dataset.html), [Ohio authors' descriptor](https://ceur-ws.org/Vol-2675/paper11.pdf), [MetaboNet dictionary](https://metabo-net.org/data-dictionary). The dictionary page did not expose readable text in this review; earlier M0 mappings are historical, not newly verified release properties.

[Babelbetes' maintainers](https://nudgebg.github.io/babelbetes/latest/data_sets/DCLP3/) document DCLP3 conversion assumptions, including censor flags, adjusted clocks and uncertain extended boluses. Their [tested-release list](https://nudgebg.github.io/babelbetes/latest/data_sets/overview/) names Release 3, 2022-08-04. This is a converter's tested input identity, **not confirmation of the provider's latest release**. Neither its inferred bolus durations nor boundary replacements are adopted here. DIAX and Babelbetes solve broader conversion tasks; a narrow CGM adapter avoids importing their unneeded insulin assumptions.

## Selected source and remaining release audit

Select the six adults in the original 2018 cohort, with their provider training/testing files, conditional on current authorization and release verification. Preserve the additional 2020 cohort unopened for possible B1 assessment, subject to suitability and overlap review. Do not count 2018 records distributed again in a 2020 package as new people. Do not mix source files with their MetaboNet copies. The public cohort description determines the target; actual counts, censoring, usable duration, timestamp precision and file hashes remain unknown.

The smallest study is this existing six-person cohort, not a powered claim about all people with T1D. It can describe later-period performance for the same people. It cannot establish generalization to unseen people. Release verification must reconcile the cohort, native XML grammar, units, device flags, duplicate timestamps, adjusted clocks and the train/test chronology before a human freeze. Published example counts must not be substituted for measured coverage.

## Model fit and exclusions

Use the existing scikit-learn Ridge estimator, with its own locked environment and declared settings, against persistence. [GluPredKit's pinned ridge implementation](https://github.com/replicahealth/GluPredKit/blob/e5bd6357a6d86fb97ab8a13d02dc73823241e860/glupredkit/models/ridge.py) was inspected as a reuse candidate. Its grid-search and grouping behavior are not the proposed temporal protocol. Reuse the underlying estimator directly; do not claim reproduction of GluPredKit results. No new biological model or controller is introduced.

The existing simglucose profiles are virtual parameter sets, not estimable human identities. Cambridge requires physiological parameter/state and observation assumptions absent from this CGM-only question. Its plasma output cannot silently become observed CGM. Neither engine is enabled for human forecasting in M3/1. Their existing native verification remains regression evidence, including solver/initialization sensitivity; it is not a human forecast adapter.

[ReplayBG requirements](https://gcappon.github.io/py_replay_bg/documentation/data_requirements.html) include a regular time grid, meal/insulin inputs and steady-state initialization assumptions; its [twinning interface](https://gcappon.github.io/py_replay_bg/documentation/twinning_procedure.html) also requires body weight. Incomplete inputs and placeholder weight do not justify fitting a twin. No ReplayBG dependency, parameter fit or intervention replay is added. A later physiological study needs independently justified inputs, state estimation, compartment mapping and identifiability, under a new protocol. CGM forecast residuals alone cannot identify a biological mechanism for B1.

## Rights and storage handoff

An authorized researcher must obtain the current agreement and release from the provider. This task does not initiate that process. Before processing, record the actual release label and archive hash, terms/dictionary hashes, institutional authorization reference, permitted local processing, derived-artifact retention and publication rules. Confirm the institutional access route is available. Commercial use and redistribution remain unverified; do not infer either from OpenT1D's Apache license.

Store raw and derived human material in an access-controlled, encrypted local location **outside the repository and cloud-synced folders**, with an authorized-user list and agreement-specific retention/deletion plan. Keep the identity crosswalk, raw hashes, filenames, row-level predictions and diagnostics private. Disable uploads and external telemetry. Review even aggregate outputs before sharing. Raw records need not be distributed to reconstruct a permitted derived report: retain prediction/error sufficient statistics and provenance privately under the agreement. If retention is disallowed, record the resulting reproducibility limitation rather than promising a permanent archive.

The missing external actions are authorization by an eligible recipient, acceptance by the proper signatory, explicit permission for the concrete download/use, and native release verification. Until then the public workflow uses self-authored synthetic fixtures only. A synthetic format test is not verification against the provider's actual XML release.
