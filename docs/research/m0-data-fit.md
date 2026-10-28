# M0 data card and source crosswalk

Status: public documentation assessed on 13 September 2026. No patient records, archive, account or data-use agreement was acquired. Native release verification and numerical data-quality assessment remain pending. This card implements the bounded OT-013 assessment; it is not a working importer.

## DCLP3 source card

The [JAEB DCLP3 access page](https://public.jaeb.org/dataset/573) provides a study-specific request and terms route. No access or redistribution right is inferred from a public listing. Applicable archive terms, attribution and permitted derived outputs must be recorded by an authorized recipient before use. The current native release and its dictionary have not been retrieved.

The relevant context is a six-month closed-loop versus sensor-augmented pump study, including adolescents and adults. Trial enrollment, public-release participants and complete usable traces are different cohorts. Reconcile study arm, age, device, observation period and exclusions against the actual release before selecting an adult-only analysis. The original trial's intervention evidence is not evidence for OpenT1D's BB/PID implementations. [Original study](https://www.nejm.org/doi/full/10.1056/NEJMoa1907863).

[Babelbetes' DCLP3 documentation](https://nudgebg.github.io/babelbetes/latest/data_sets/DCLP3/) describes its converter's handling of CGM, `CommandedBasalRate`, bolus amounts and adjusted timestamps. It reports no carbohydrate field in the bolus table and incomplete extended-bolus duration. These are documented converter interpretations, not independently checked native observations. The [tested-release overview](https://nudgebg.github.io/babelbetes/latest/data_sets/overview/) identifies its input release; that is not proof of the latest provider release. [DIAX](https://github.com/Center-for-Diabetes-Technology/DIAX) is another candidate to assess before implementing a converter.

## Unit and observation crosswalk

This is a proposed semantic mapping. Names from a converter or aggregate source do not establish that every source record exists or has the same meaning.

| Concept | DCLP3 documentation | MetaboNet dictionary | OpenT1D assessment rule |
| --- | --- | --- | --- |
| CGM | `CGMValue` plus `HighLowIndicator`, `DataDtTm` and optional `DataDtTm_adjusted` | CGM signal, mg/dL on a five-minute grid; source censoring flags are not established as separate fields | Preserve measured versus censored status before resampling; zero is not a usable glucose measurement |
| Basal | `CommandedBasalRate`, U/h | `basal`, IU during preceding five minutes | Separate commanded rate from derived amount and reported delivery |
| Bolus | `BolusAmount`; standard/extended handling needs assumptions | `bolus`, IU during preceding five minutes | Preserve delivery interval and attribution; do not count a bolus again inside total insulin |
| Total insulin | Requires explicit construction from available records | `insulin`, IU during preceding five minutes | Verify definition and conservation before using with basal/bolus components |
| Meals | Complete usable meal input is not established | Source-dependent `carbs`, user-reported grams | Missing records are unknown, not zero; separate actual and announced meals |
| Time | Device and adjusted clocks; interval meaning needs native verification | Sometimes ambiguous timezone; values refer to a resampled grid | Record clock changes, time shifts, interval closure and cross-device alignment |
| Identity | Study, arm, participant and released period | Source dataset/file plus aggregate identifiers | Preserve source identity and resolve repeat participants before splitting |

The [MetaboNet dictionary](https://metabo-net.org/data-dictionary) defines its insulin amounts over the preceding five minutes. For a purely synthetic illustration, a constant command of 0.6 U/h over five complete minutes integrates to 0.05 U. Dividing an observed five-minute amount of 0.05 U by five gives an interval-average rate of 0.01 U/min. This arithmetic does not establish actual tissue delivery or justify filling missing events. A rate change inside the interval must be integrated piecewise.

[MetaboNet-Bench v2](https://arxiv.org/html/2606.18640v2) marks DCLP3 carbohydrate data unavailable and describes non-commercial research/education restrictions on the consolidated dataset alongside original source terms. Its preprocessing choices are not permission to replace unknown causal inputs with zeros. Verify the actual downloaded license if this resource is later used.

## CGM censoring is not missingness

The public [DCLP3 converter documentation](https://nudgebg.github.io/babelbetes/latest/data_sets/DCLP3/#special-values), referring to the native glossary, specifies `HighLowIndicator`: 0 means `CGMValue` holds the reading, 1 means above the measurement range with `CGMValue=0`, and 2 means below the range with `CGMValue=0`. Its stated device bounds are 40–400 mg/dL. These are documented source conventions, still requiring verification against an authorized native release.

A future importer must retain the original value, indicator, device limits and observation category (`measured`, `censored_low`, `censored_high`, `missing` or `invalid`). Do not infer a direction from a zero alone. Unknown indicators, zero without a usable indicator and inconsistent value/indicator pairs must remain invalid or unresolved. They are neither ordinary numeric measurements nor assumed absent records. Preserve the raw and adjusted timestamp fields and record which was used.

| Synthetic input | Interpretation to preserve | Consequence for comparison |
| --- | --- | --- |
| Value 115, indicator 0 | Measured glucose, 115 mg/dL | Numeric comparison is possible after time alignment |
| Value 0, indicator 1 | Censored above the stated upper limit | Actual magnitude is unknown; not glucose zero |
| Value 0, indicator 2 | Censored below the stated lower limit | Actual magnitude is unknown; not missing by default |
| Value 0, indicator absent | Unresolved/invalid reading | Do not guess high versus low or silently fill it |

Babelbetes describes replacing censored values with 40 or 400. That may be useful for its converter but loses the distinction between a boundary replacement and a measured value at that boundary unless the indicator is retained. The assessed MetaboNet numeric CGM field does not by itself prove preservation of this distinction. Mark censoring recovery from that field as unsupported; inspect the exact release and preprocessing before claiming equivalent missingness, extreme-glucose exposure or numeric error metrics. This audit specifies the required semantics, not an implemented patient-data importer.

## Overlap, rights and fallback

[MetaboNet's methods](https://arxiv.org/html/2601.11505v1) include DCLP3 and OhioT1DM and describe participants whose data occur under multiple identifiers. Do not place a source trial in development and its aggregate copy in evaluation. Start with one source study; document unresolved identity linkage and do not claim participant-independent evaluation while it persists.

The separately distributed [MetaboNet processor](https://github.com/replicahealth/metabonet_processor/blob/main/LICENSE) declares CC BY-NC-ND 4.0. Its code terms differ from data terms and from OpenT1D's license. It is not vendored or modified here. Inspect the exact code, dependency and source-data terms of any chosen converter separately.

[OhioT1DM](https://webpages.charlotte.edu/rbunescu/data/ohiot1dm/OhioT1DM-dataset.html) is a conditional meal-annotated alternative, with current institutional-email access requirements. Its [descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC7881904/) notes unavailable actual body weight, a placeholder value of 99, shifted dates and self-reported events. It can support a separately defined small forecasting study if access and input quality are established. It is not a dependency of M0's public synthetic reproduction.

## Supported questions and acceptance gates

The first proposed human-data question is whether an authorized DCLP3 release supports traceable characterization of CGM availability and recorded insulin under the observed treatment. Subsequent held-out prediction needs a separate protocol, causal information cutoff, history requirements and simple prediction references. Neither fitted traces nor matching glucose distributions validate an alternative feedback controller's counterfactual effect.

Before accepting an importer or numerical analysis:

- Record the exact archive release, dictionary, terms, attribution, intended outputs and authorized access.
- Reconcile study arm, usable participants and periods; report coverage and exclusions without assuming the trial enrollment count survives processing.
- Verify every required signal's units, timestamps, observation status and missingness; check amount conservation on synthetic fixtures before applying a converter.
- Resolve source overlap and freeze development/evaluation partitions before fitting or inspecting evaluation results.
- For meal replay, require defensible insulin and meal histories and initial-state assumptions. DCLP3 is not currently approved for that task; do not manufacture meals.

The public dictionary review and explicit feasibility limits satisfy the assessment scope. They do not close later data-access, native-dictionary, converter-verification or external-validation requirements. No access request or communication has been sent.
