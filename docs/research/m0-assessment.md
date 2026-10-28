# M0 source assessment and proposal

**Historical scope:** this page records the original milestone and its then-pending work. The separate [M2 evidence record](m2-reproduction.md) tracks the later Cambridge integration and OT-014 evaluation; earlier outputs and acceptance claims remain unchanged.

**Historical source assessment, 12 September 2026. No upstream simulator was installed or executed for this assessment. No numerical reference has been reproduced and no patient dataset has been acquired.** Public repositories, source files, papers and dataset documentation were inspected. Source-level behavior below must still be verified at runtime.

Subsequent execution is recorded in the [native reproduction record](m0-reproduction.md), [data card](m0-data-fit.md), and accepted [decision 0002](../decisions/0002-m0-reference-first.md). The conclusions below describe the original proposal, not the later completion status.

The [roadmap](../../ROADMAP.md) remains the implementation plan. This page supplies evidence for OT-001–OT-004 and OT-013; the [first experiment](first-experiment.md) is the canonical protocol candidate and [decision 0002](../decisions/0002-m0-reference-first.md) records the proposed reuse boundary. The earlier [landscape report](../onderzoek/projectopzet.md) remains broader background.

## Recommendation

Start with a reproducible native simglucose scenario. In parallel, probe LT1's existing Cambridge example and audit DCLP3's data dictionary and rights. Decide the integration boundary from those results. The useful OpenT1D contribution is likely a small layer for explicit experiment information, model ancestry, unit and time translation, failure retention and reconstructable evidence. This is an inference from the inspected projects, not an established gap that requires a new framework.

Do not build a solver, controller library, GPU platform or generic data parser during M0. Existing projects provide substantial parts of each. Keep extending LT1 directly as a live alternative if the two native probes show that it can supply the complete workflow with less maintenance.

## Candidate engines and comparable projects

### Revisions and evidence boundary

The following repository revisions were checked against fetched source on the assessment date; the two primary engine revisions were also checked using `git ls-remote`. The primary engine pins are proposed reproduction inputs, not tested supported versions. Commit dates are author dates and provide context, not a maintenance-quality score.

| Candidate | Inspected revision | Commit date | Declared code license | Relevance |
| --- | --- | --- | --- | --- |
| simglucose | [`a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`](https://github.com/jxx123/simglucose/tree/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc) | 2025-04-18 | [MIT](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/LICENSE) | First Python reference; UVA/Padova 2008 lineage |
| LoopInsighT1 / LT1 | [`9a6092065bd821f88691cd8d03b0550acd665573`](https://github.com/hpeuscher/loopinsight1/tree/9a6092065bd821f88691cd8d03b0550acd665573) | 2025-02-18 | [MIT](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/LICENSE.md) | Modular TypeScript engine; explicitly select Cambridge/Hovorka for structural diversity |
| APS TestBed | [`35a34e85f334ee17a33f17d21e23b0fb9a39f065`](https://github.com/UVA-DSA/APS_TestBed/tree/35a34e85f334ee17a33f17d21e23b0fb9a39f065) | 2023-08-11 | [GPL-3.0 at root](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/LICENSE); separate component notices | Existing multi-simulator comparison and fault framework |
| GluCoEnv | [`f78e11aa66acef162938597c58226d0a56270cbb`](https://github.com/RL4H/GluCoEnv/tree/f78e11aa66acef162938597c58226d0a56270cbb) | 2024-09-05 | [MIT](https://github.com/RL4H/GluCoEnv/blob/f78e11aa66acef162938597c58226d0a56270cbb/LICENSE.txt) | Vectorized control environment in the simglucose lineage |
| py-mgipsim | [`b985f8c2ea385d1b2b8480957b730866e07772f1`](https://github.com/illinoistech-itm/py-mgipsim/tree/b985f8c2ea385d1b2b8480957b730866e07772f1) | 2026-02-25 | [GPL-3.0](https://github.com/illinoistech-itm/py-mgipsim/blob/b985f8c2ea385d1b2b8480957b730866e07772f1/LICENSE) | Adjacent activity and Extended-Hovorka work |
| GluPredKit | [`e5bd6357a6d86fb97ab8a13d02dc73823241e860`](https://github.com/replicahealth/GluPredKit/tree/e5bd6357a6d86fb97ab8a13d02dc73823241e860) | 2026-01-13 | [MIT](https://github.com/replicahealth/GluPredKit/blob/e5bd6357a6d86fb97ab8a13d02dc73823241e860/LICENSE.txt) | Forecasting and data-processing boundary comparison |

The root licenses establish repository declarations. They do not independently establish the provenance or redistribution rights of every parameter table, dependency, image or clinical asset. No third-party source or parameter file is added to OpenT1D by this proposal.

### simglucose: smallest first reference, with consequential conventions

The [native tutorial](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/examples/advanced_tutorial.py) provides a headless custom scenario, basal-bolus controller and saved output. The [package configuration](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/setup.py) still includes Gym 0.9.4 and broad numerical dependencies. A native execution path avoids relying on a Gym wrapper's behavior, but does not remove installation requirements. A fresh environment and exact dependency lock are an OT-003 deliverable; compatibility with current Python is untested here.

The audit found these specific contract risks:

- The [environment](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/simulation/env.py) advances one-minute physiology steps inside the sensor interval and averages outputs. The logged `BG` is the patient's subcutaneous glucose observation, not plasma glucose. Sensor choice also changes controller cadence.
- The [basal-bolus controller](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/basal_bolus_ctrller.py) uses actual meal-event information from the preceding interval and privileged profile configuration. Both action fields are rates in U/min. An announcement-controlled comparison needs a separately specified information boundary.
- The [PID reset](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/pid_ctrller.py) initializes its previous observation to zero, causing a derivative startup transient when the derivative gain is nonzero. Preserve that in reproduction; assess initialization and integral behavior before accepting the benchmark settings.
- The [native simulation loop](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/simulation/sim_engine.py) continues to the horizon despite the environment's terminal flag and saves by patient name. Reusing output directories can overwrite runs. Successful process exit alone does not establish valid completion.

Inventory and hash `vpatient_params.csv`, `Quest.csv`, sensor and pump tables. The [patient table](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/params/vpatient_params.csv) contains ten adult profiles, but the inspected CSVs have no separate per-file provenance declarations. The [parameter-definition notes](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/definitions_of_vpatient_parameters.md) themselves acknowledge inferred meanings and unknowns. Record those limits; do not present the table as an independently verified population or transfer another simulator's regulatory status to it.

### LT1: an existing modular laboratory and a concrete second family

LT1 already separates patient, controller, sensor and actuator. Its [Cambridge implementation](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts) includes constants, units and attribution to Hovorka and Andersen under a MIT header. This is a configurable model, not a virtual cohort matched to simglucose's adults.

The convenient [MinimalDemoTS](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/examples/MinimalDemo/MinimalDemoTS.ts) uses UVA/Padova. Instead, target the existing [Cambridge reference scenario](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts): 24 hours, a 40 g meal at 08:00 over 15 minutes, an announcement at midnight, IdealCGM, StaticInsulinPump and MPC_Hovorka2004. Its early announcement is part of that native reference, not the information policy proposed for M1. The [headless entry script](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/examples/MPC/IFAC_EDT_2025_Hauser/IFAC_EDT_2025_Hauser.ts) documents execution using Node and ts-node; it runs multiple scripts, so any narrower harness must identify the selected reference and its changes.

LT1's [signal definitions](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/types/Signals.ts) distinguish infusion rate in U/h, bolus amount in U, meal ingestion rate and independent announcements. Its [simulation loop](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/Simulator.ts) has its own event ordering and per-module seed offsets; a zero seed becomes one. Map these explicitly. Copying a simglucose U/min value into LT1's U/h boundary would produce a factor-of-60 error.

The [package file](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/package.json) uses dependency ranges; the [ignore rules](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/.gitignore) exclude the npm lockfile. Record Node, loader and resolved dependencies in the reproduction package. Verify full result objects and saved-file success rather than relying only on the helper's reduced glucose/insulin export.

### Reuse versus extension

| Project | Existing capability and limitation | Proposed OpenT1D treatment |
| --- | --- | --- |
| [APS TestBed](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/README.md) | Multi-simulator controller comparison and fault injection; substantial overlap with the first research task. Uses a bundled simglucose fork and Glucosym, with a mixed Python/Node stack and component licenses. | Reuse methodological ideas and assess individual components. Compare the cost of extending it before adopting a new orchestration layer. |
| [GluCoEnv](https://github.com/RL4H/GluCoEnv/blob/f78e11aa66acef162938597c58226d0a56270cbb/README.md) | PyTorch parallel environments and control/RL experiments; shares simglucose/UVA 2008 ancestry. | Possible later acceleration, not the independent second physiological family. |
| [py-mgipsim](https://github.com/illinoistech-itm/py-mgipsim/blob/b985f8c2ea385d1b2b8480957b730866e07772f1/README.md) | Multivariable glucose-insulin simulation relevant to later activity and physiological extensions. | Assess a specific model and coupling when the research question requires it; avoid expanding M0 into another full engine integration. |
| [GluPredKit](https://github.com/replicahealth/GluPredKit/blob/e5bd6357a6d86fb97ab8a13d02dc73823241e860/README.md) | Existing forecasting, data processing and evaluation tooling. Forecasting is a different task from closed-loop intervention simulation. | Inspect supported parsers and analysis before creating equivalents; preserve source semantics and license obligations. |

The [APS TestBed paper](https://arxiv.org/abs/2208.06479v4) demonstrates that combining two simulators, controllers and faults is already an established project direction. OpenT1D's novelty cannot be the existence of that combination. The practical proposal is to make the selected experiment and its evidence reconstructable across native model families while retaining a path to biological extensions.

APS TestBed's [fault injector](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/UVA-Padova/simglucoseFI/tests/run_Faultinjection_monitor.py) rewrites source files; a benchmark needs isolated execution and explicit patch provenance. Its [Glucosym component](https://github.com/UVA-DSA/OpenAPS-Glucosym-3.9/tree/3cf65df8ba6e888f11778dc36bcafcd466a900e0) is separately pinned and licensed; the [setup script](https://github.com/UVA-DSA/OpenAPS-Glucosym-3.9/blob/3cf65df8ba6e888f11778dc36bcafcd466a900e0/closedloop3.9-setup.sh) combines Python 3.9, Node 12.22.1 and patched oref0. The [bundled simglucose setup](https://github.com/UVA-DSA/APS_TestBed/blob/35a34e85f334ee17a33f17d21e23b0fb9a39f065/UVA-Padova/simglucoseFI/setup.py) identifies version 0.2.1. These are concrete additional reproduction obligations before adopting the whole stack.

GluCoEnv's [packaging](https://github.com/RL4H/GluCoEnv/blob/f78e11aa66acef162938597c58226d0a56270cbb/pyproject.toml) differs from its [setup.py route](https://github.com/RL4H/GluCoEnv/blob/f78e11aa66acef162938597c58226d0a56270cbb/setup.py), and its [environment](https://github.com/RL4H/GluCoEnv/blob/f78e11aa66acef162938597c58226d0a56270cbb/glucoenv/env/env.py) automatically resets episodes. Installation and retained failure records need testing before a fixed-horizon evaluation. These observations favor small native probes before choosing a host framework. They are not claims that these projects are unusable.

## Data fit

**Propose DCLP3 as the first dictionary and rights audit, not as a ready meal-replay dataset.** Use MetaboNet later for harmonization, preserving source identity. OhioT1DM is a conditional option where richer meal annotations justify its access requirements and small cohort.

| Source | Documented fit | Access and scientific limit | M0 deliverable |
| --- | --- | --- | --- |
| [JAEB DCLP3](https://public.jaeb.org/dataset/573) | Study-level CGM and pump records from a closed-loop trial; useful for a bounded observational assessment. | Provider registration and terms; no access obtained. Native dictionary and released analysis cohort still need verification. | Variable/rights card and explicit list of questions supported by CGM and recorded insulin. |
| [MetaboNet dictionary](https://metabo-net.org/data-dictionary) | Harmonized CGM, insulin and source-dependent meal records. Basal is an amount in IU over the preceding five minutes. | Mixed source terms; harmonization does not establish complete inputs or independent participants. | Unit/field crosswalk and source-overlap map; no new generic importer yet. |
| [OhioT1DM owner page](https://webpages.charlotte.edu/rbunescu/data/ohiot1dm/OhioT1DM-dataset.html) | Five-minute CGM, insulin and self-reported meal/event data for 12 people over eight weeks. | Current owner requires institutional email; historical documentation describes a DUA. Neither access nor applicable agreement confirmed here. | Conditional fallback assessment for a small forecasting task, not a dependency of public M0 reproduction. |

[Babelbetes' DCLP3 converter notes](https://nudgebg.github.io/babelbetes/latest/data_sets/DCLP3/) identify `CommandedBasalRate` in U/h, bolus records without `CarbAmount`, and incomplete extended-bolus timing. These are the converter maintainers' interpretations, not a replacement for the native JAEB dictionary. [MetaboNet-Bench v2](https://arxiv.org/html/2606.18640v2) also marks DCLP3 carbohydrate data unavailable. Missing meal records must not become zero carbohydrate inputs. Pump-reported doses and commanded basal settings are not independent measurements of insulin entering tissue.

The [MetaboNet methods](https://arxiv.org/html/2601.11505v1) include DCLP3 and OhioT1DM and describe duplicate-participant handling with residual multiple identifiers. Do not put an original study in training and its aggregate copy in evaluation. Its [benchmark preprint](https://arxiv.org/html/2606.18640v2) describes non-commercial research/education restrictions for the consolidated data; verify the actual release terms and original component terms before use. The separately published [DUA processor license](https://github.com/replicahealth/metabonet_processor/blob/main/LICENSE) is CC BY-NC-ND 4.0; it is not an Apache-compatible implementation to copy into this proposal.

The [OhioT1DM descriptor](https://pmc.ncbi.nlm.nih.gov/articles/PMC7881904/) explains that actual weight is unavailable and 99 is a placeholder. It also describes shifted dates and self-reported meals. These details matter for physiological personalization, even when a forecasting parser accepts the files.

Before acquiring an analysis-ready release, specify the intended claim. Then record release and rights, source-study arm and usable cohort, units, time shifts and clock alignment, amount/rate semantics, bolus timing, actual versus announced meals, CGM quality flags, missingness, covariate placeholders and participant overlap. Inspect [Babelbetes](https://nudgebg.github.io/babelbetes/latest/data_sets/overview/) and [DIAX](https://github.com/Center-for-Diabetes-Technology/DIAX) before writing another converter. Conflicting cohort counts must be reconciled against the exact release and selection rules.

Use human observations initially to assess data coverage and, later, prespecified reconstruction or held-out prediction under observed care. They cannot by themselves establish how a new controller would change outcomes. A meal-replay task requires suitable known inputs and initialization; [ReplayBG's requirements](https://gcappon.github.io/py_replay_bg/documentation/data_requirements.html) make that dependence concrete. If the required inputs or rights are absent, narrow the claim and continue the public synthetic workflow.

## Proposed native reproduction probes

| Probe | Preserve | Record separately | Evidence required |
| --- | --- | --- | --- |
| First: simglucose tutorial custom scenario | `adolescent#001`, Dexcom seed 1, Insulet, upstream BBController, 24-hour horizon and documented five meals | Fixed calendar origin instead of the tutorial's current date; selected tutorial segment; unique output paths | Fresh installation, complete configuration and output, repeated process and native-reset execution, event/unit checks and named reference comparison |
| Second: LT1 Cambridge reference | Original Cambridge parameters, MPC settings, IdealCGM, StaticInsulinPump, meal and announcement timing | Selected reference script versus full multi-script entry; output collection and dependency lock | Headless Cambridge execution, signal and timing audit, reset/seed checks, preserved outputs and documented differences from simglucose |

These are different native reference scenarios, not matched controller-performance comparisons. Apply the proposed adult meal experiment only after native behavior is understood. simglucose custom scenarios do not automatically repeat the first day's meals: explicitly encode both days when implementing the 48-hour candidate.

For each probe, preserve the exact source revision and harness diff, asset inventory and notices, interpreter/runtime, resolved dependency lock, commands, environment, solver settings, seeds, configuration, logs, status and outputs. Separate intended runs from completed ones. Verify monotonic timestamps, horizon, sample meaning, meal totals and integrated delivered insulin. Structural missing terminal action cells must not be confused with missing glucose observations.

Compare events, timestamps and completion status exactly. Start repeatability checks in an identical environment; investigate divergence before choosing a numerical tolerance. Justify any later platform or adapter tolerance from observed numerical behavior. Different engines should not be expected to produce identical trajectories.

Identify an upstream numerical or figure reference whose inputs and provenance can actually be reconstructed. An old CSV without matching configuration is not a trustworthy oracle. If only a documented example is available, preserve repeatable output as a new baseline and explicitly keep published-reference agreement pending. Installation, same-run repeatability, upstream-reference agreement and independent reproduction are separate evidence statements.

## Work proposal and stopping rules

The identifiers below refer to the existing roadmap; this table makes their deliverables reviewable without introducing a second backlog.

| Work package | Next deliverable | Acceptance before proceeding |
| --- | --- | --- |
| OT-001 | Review the scientific scope in the [protocol candidate](first-experiment.md), then resolve and freeze executable timing, controller and metric choices using OT-002/OT-003 evidence | Initial scope approval enables engine assessment; the final freeze is required before M1 evaluation, not before native reproduction |
| OT-002 | Finish model/asset cards for both engine pins and the APS reuse comparison | Sources, parameters, rights, runtime constraints and unknowns recorded separately |
| OT-003 | Run the two native probes, complete at least the first reference package | Clean rerun and reference evidence with justified tolerances; failures retained |
| OT-004 | Accept or revise [decision 0002](../decisions/0002-m0-reference-first.md) using probe results | Explain why a thin adapter, an upstream extension or another host is the smallest useful change |
| OT-013, alongside the above | DCLP3 dictionary/rights card and MetaboNet crosswalk | State which observed-data questions are feasible and which inputs/access remain missing |

If installation fails, preserve the failure and try a documented compatible runtime before replacing the engine. If a fix changes model or controller behavior, keep the original reference and record the patch independently. If parameter rights cannot be resolved, do not vendor the affected assets or label their redistribution verified. If the second engine cannot support an equivalent observation or population, retain an explicit separate comparison track and revisit the contract.

M0 is complete only when the roadmap's acceptance is met. This proposal advances research and review; runtime compatibility, reference reproduction, asset provenance, protocol acceptance, data-release verification and the final integration choice remain open. Repository documentation checks establish only that these materials build and meet repository conventions.
