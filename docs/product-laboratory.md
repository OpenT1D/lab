# Product requirements: a shared T1D research laboratory

**Planning requirements, 25 October 2026; contribution and scope clarification,
29 October 2026.** OpenT1D aims to provide one coherent
laboratory in which researchers can combine, replace and compare suitable
existing models and methods. Its contribution is shared research infrastructure
and useful integrations. Developing an original controller or physiological
engine is an optional research choice.

This guide owns the product requirements and acceptance jobs. The
[roadmap](../ROADMAP.md) is the sole authority for implementation order,
dependencies and status. OT-059–074 identify work packages with separately
recorded increments and open requirements. Their inclusion here is not evidence
that a capability is delivered. [Architecture](architecture.md) describes the
current bounded implementation; existing task guides and evidence records remain authoritative
for what can actually be run.

## Product definition and users

A researcher should be able to define a question, choose compatible methods,
configure data or scenarios, run a frozen experiment, inspect complete results
and failures, and give another researcher a usable project. A subsequent method
or question should reuse that work without requiring another infrastructure
project.

The laboratory must serve method authors working in code, analysts using their
own authorized observations, physiological model authors, researchers using the
GUI, and reviewers reading preserved results. They need different controls and
explanations over the same scientific plan and evidence. A notebook-created plan
must be inspectable in the GUI; a GUI-created plan must be available to Python
and CLI users without a separate scientific implementation.

Existing assets include native M1/M2 tracks, bounded external method intakes,
synthetic M3/M4/M5 workflows, the shared MMTT analysis core, campaigns, archives
and selected GUI routes. M5 currently has GUI report inspection, not GUI
execution. These assets are starting points for migration, not proof of general
interchangeability or independent researcher acceptance.

## Shared laboratory requirements

### Projects, plans and results

A project must live outside the installation or checkout and retain recognizable
studies, editable drafts, frozen plans, all attempts and authoritative results.
Cloning or editing a study must preserve the original and show what changed.
Readiness must be checked again when relevant inputs or settings change.

The shared plan must identify the question and contrast, method and source
versions, population or synthetic scope, inputs, scenario, observation meanings,
initialization, time window, numerical settings, random streams, evaluation
rules, resource limits and required outputs. Task-specific contracts must define
their own estimands and scientific eligibility. An offline analysis does not
need a simulation step interface.

Results must expose the complete planned roster, attempted and unattempted work,
errors, exclusions, coverage and valid comparison support. Missing performance
metrics remain undefined with a reason; unattempted work must not become a
zero-valued performance observation. Shared tables and readers must retain
task-specific signal and metric meanings.

Migration must pass existing routes through the shared facilities while
preserving their historical contracts and readers. A second parallel collection
of demonstrations would not meet this requirement.

### Native engines and scientific compatibility

A whole native engine is a valid module. Preserve upstream equations, solver,
reset and lifecycle where supported. The laboratory must also support selected
component replacement when its biological boundary is defensible. It must not
require every donor to use one language, solver, physiological timestep or
exchange standard.

Capability descriptions must declare units, compartments, routes, amount versus
rate, point versus interval observations, normalization, timestamps and
availability, events, initial state and prehistory, random streams, stop rules,
supported populations and process ownership. Compatibility is a relationship
between particular capabilities. Unsupported combinations require a concrete
explanation before scientific execution.

Keep solver, communication, sensor, controller and delivery clocks distinct.
Specify event ordering, once-only delivery, interval support, delays and any
rollback requirement. A controller command is not confirmed delivery. Plasma
and interstitial glucose are not interchangeable because their units match.

Component composition must assign absorption, secretion, transit, extraction,
clearance, delay and measurement noise to explicit owners. Replacement must
remove the process it supersedes and address basal equilibrium, volumes,
inventories and scaling. Coupled models need appropriate conservation,
initialization and numerical refinement checks. Co-simulation requires a
validated communication strategy; FMI does not supply that strategy merely by
packaging a model. The [FMI specification](https://fmi-standard.org/docs/3.0.2/)
distinguishes model exchange, co-simulation and their importer responsibilities.

Capability families must preserve callback evaluation and state semantics.
A sampled controller may update state at declared decision points. The existing
[M4 continuous-source contract](m4-causal-secretion.md) instead requires a pure
function of its supplied arguments: an adaptive solver can repeat an evaluation
or evaluate times out of order. A derivative callback must not advance hidden
state on each call; component state must follow its declared solver ownership.
Retain applicable repeated/out-of-order evaluation probes and refusals in the
conformance kit. Finite probes can detect violations; they cannot prove
arbitrary supplied code pure.

### Scenarios, comparison and uncertainty

A shared scenario must separate actual events from information available to a
method. For example, meal intake and its announcement have distinct quantities,
times and availability. Each native translation must disclose how that intended
scenario is realized; equal carbohydrate totals do not imply identical ingestion
or absorption dynamics.

Comparisons require a declared outcome, time window, weighting, denominator and
matching rule. Preserve development, tuning and reserved evaluation boundaries,
including known evaluation exposure. Report within-engine contrasts before
interpreting differences between engines. The current M2 tracks do not isolate
an engine effect: controllers, sensors, populations and signal meanings differ.
Identically numbered profiles across engines are not matched people, and new
seeds are not a new physiological population.

Distinguish numerical, parameter, observation, stochastic, structural and
population uncertainty. Show convergence, failures, extreme outcomes and
reversals when relevant to the question. An engineering stress distribution is
not an empirical population distribution. Do not add a universal winner or
default significance test to every result table.

### Owned data, fitting and biological analysis

Data intake must preserve raw-source identity, units, actual measurement and
availability times, missing or censored values, participant/visit/episode
relationships, conversion rules and authorized access. Unknown treatment or
meal events must not silently become zeros.

Separate preparation, fitting, frozen model artifacts, simulation or prediction,
and scoring where the task requires it. Observation functions, noise models,
fixed and estimated parameters, bounds and shared parameters need explicit
definitions. Reuse established calibration tools where suitable; for example,
[PEtab](https://petab.readthedocs.io/en/latest/) specifies parameter-estimation
problems separately from the underlying dynamical model.

The M4 source/observer and MMTT tasks must use shared project, execution and
result facilities while retaining their distinct forward and inverse contracts.
The current fixed-kinetic MMTT estimator does not automatically calibrate the
causal M4 model. Assess identifiability and compare suitable simpler analyses;
better fit alone does not identify the correct biological mechanism.

### Execution, runtime and resource management

The execution layer must preserve every attempt, explicit retries, cancellation,
deadlines, crash outcomes and accepted results. Genuine native checkpoint resume
is a declared adapter capability; rerunning an unfinished case is a new attempt.
Only owned workers may be terminated.

Keep conflicting model environments separate and identifiable. Installation must
be explicit and recoverable; previously prepared environments should support
declared offline use. Observe real progress and resource use without invented
percentages or estimates. Bound concurrency and record CPU, memory, storage and
scheduler overhead on representative tasks.

Cache each step using its complete relevant identity. A changed metric requires
new analysis but may reuse unchanged simulation outputs. Changed scenarios,
models, inputs or runtimes invalidate the affected execution steps. Reuse is not
a new independent repetition.

An optional external executor must preserve the same plan, attempt ledger,
failure meanings and result semantics. Parallel independent runs and coupled
timesteps within one simulation are different responsibilities.

### Workbench, delivery and long-term use

The GUI must support question-led project creation, understandable intake,
compatibility checks, draft recovery, freeze, observed progress, cancellation,
comparison and reopening. Errors must identify the problem and a usable next
step without discarding input. Keyboard, screen-reader, zoom and narrow-window
use require verification; figures need units and accessible tables or exports.

The existing [OT-058 requirement](../ROADMAP.md#planned-windows-installer-ot-058)
remains: one graphical Windows installer and launch shortcut, with no separate
user-managed Git, WSL, Python or terminal setup. The application must manage its
required components. This requirement does not select a runtime architecture;
wrapping the current WSL instructions in a launcher is insufficient. Every
advertised platform and workflow needs actual installation, execution or reader,
shutdown, update and uninstall checks that preserve user projects.

Sharing must distinguish included artifacts from private references. Export must
exclude prohibited records, identity mappings, credentials and sensitive logs.
Opening a report or project must not execute supplied model code. Source hashes
record identity; they do not establish trust, rights or scientific validity.
Reader execution requires an explicit trust policy. Publish an archive-format,
reader, application and host compatibility matrix and verify upgrades against
its declared historical cases. Preserve the required reader/source identities;
current source-bound readers may require an exact clean historical checkout.
The [historical helper](historical-readers.md) has a fixed allowlist that does
not currently include MMTT, so a compatible MMTT migration path needs its own
implementation and evidence.

If no supported trusted reader is available, retain the original archive and
explain the unsupported scope. Any available metadata-only view must carry no
scientific reconstruction claim. Never silently rewrite the archive, execute
its supplied model or reinstall an outdated environment to bypass a refusal.
Reading historical results is a tested compatibility commitment within the
published policy, not an unlimited promise for every format and host forever.

## Seven laboratory acceptance jobs

These jobs specify intended outcomes, not completed exercises or delivery order.
The roadmap assigns their implementation and acceptance work. Record the actual
revision, platform, assistance, failures, interpretation and remaining limits for
each exercise.

| Job | Required researcher outcome | Acceptance boundary |
| --- | --- | --- |
| LAB-A | Investigate one suitable supplied controller through two physiological engines using shared scenario, execution and result facilities. | Verify each supported cell and disclose timing, information, population and signal differences. This requires new explicit contracts; current M2 does not already establish it. |
| LAB-B | Add a second controller and a second research question to the same project. | An independent author uses documented extensions without a new core or GUI route for every method; measure integration work and scientific interpretation. |
| LAB-C | Create, inspect and execute the same scientific plan through Python/CLI and GUI. | Equivalent frozen scientific fields, eligibility, failures and results; changed settings create a checked derivative plan without replacing the original. |
| LAB-D | Compare a supplied predictor on suitable owned data and transport its frozen workflow to a second cohort. | Preserve preparation/fit/input/evaluation lineage and coverage. Human execution needs source-specific authorization and protocol; synthetic checks establish no general human performance. |
| LAB-E | Perform paired MMTT sensitivity and sampling-loss analyses in the same project workbench. | Preserve the current synthetic scope and distinct estimands. Assess empirical kinetics/endpoints separately; compare scientific usefulness with suitable C-peptide summaries and product usefulness with a competent same-estimator notebook. |
| LAB-F | Interrupt a campaign, relocate it, reopen it and continue supported work. | Preserve every attempt and frozen identity. Distinguish native resume from explicit retries; completed accepted work is not counted twice. |
| LAB-G | A colleague opens a shared project and reconstructs its report after an application upgrade. | Respect private-data exclusions and explicit reader trust; preserve historical semantics and disclose what was included, referenced, verified and not independently rerun. |

Component composition also needs the process-ownership and numerical acceptance
above. Passing the controller jobs alone does not establish that arbitrary
biological components can be connected.

## Build, reuse, procure and contribute upstream

| Decision | Product requirement |
| --- | --- |
| Build | T1D meaning and compatibility contracts, coherent plans/projects, native translations, full attempt accounting, task-specific comparisons and a shared workbench. |
| Reuse | Upstream physiology, controllers and solvers; suitable ML/calibration methods; environment tools, OS process facilities, plots and established provenance formats. Preserve their attribution and exact-version rights. |
| Connect | Existing workflow executors for a justified remote study. Use selective FMI, SBML/CellML, SED-ML/OMEX or PEtab bridges when a concrete donor or exchange task benefits. Declare and test supported subsets. |
| Procure when justified | Commodity signing, distribution, storage or compute services may serve a defined delivery need and budget. No provider, purchase, hosted-data permission or cloud dependency is selected by these requirements. |
| Contribute upstream | Generally useful unit, reset, timing, delivery and extension-hook corrections belong with their upstream owners where possible; OpenT1D can consume the maintained integration. |

The laboratory should demonstrate reuse of simglucose and LT1 through its shared
core before advertising a general engine interface. Additional engines and
GluPredKit, ReplayBG, R or standard-model integrations need their own bounded
task, rights, semantics and maintenance assessment. Their mention is not an
implemented adapter or partnership.

## Evidence and scientific boundaries

Maintain separate claims for implementation, internal numerical verification,
native or published-reference reproduction, independent use, empirical
assessment for a specified population/task, and biological interpretation.
Missing evidence limits the corresponding claim rather than blocking every
unrelated software increment. CI and generated code are not model validation.

Report reconstruction verifies preserved data, selection and analysis. For an
arbitrary supplied method it does not independently reproduce the algorithm's
outputs; that requires separate re-execution. Preserve stronger model-specific
replay guarantees where they exist. Predictions imported after execution do not
prove which information the original method used.

Simulation agreement is not proof of human predictive validity. Historical
replay under recorded treatment does not by itself identify counterfactual
treatment effects. MMTT estimated total secretion is not C-peptide AUC, and
same-estimator notebook parity does not demonstrate additional scientific value.
Therapy benefit, clinical operation and a validated multiscale digital twin
require separate intended use and evidence; none follows from these plans.

## Product value measurement

OpenT1D aims to make a useful contribution alongside existing research tools.
Reusable integration, clearer assumptions, reliable handoff, maintainability and
upstream improvements are contributions to assess in their own right. Describe
the research task, who benefits and the effort needed to provide and maintain it.

Comparisons help identify strengths, gaps and opportunities to improve. Select
an applicable reference workflow and agree on the question, versions, inputs,
endpoints, preparation, assistance and evaluation rules before observations.
Give each workflow competent preparation and report favorable, similar,
unfavorable and inconclusive outcomes, including costs and tradeoffs. Claims of
improvement apply to the measured task and conditions. A comparison may support
reuse, collaboration or an upstream change as the most useful next step.

Measure the second and third integration or research task, not only a prepared
first example. Compare with competent existing tools and a good notebook,
including setup, connecting code, failure diagnosis, interpretation and
maintenance on both sides.

Record time to a correct run and engine change, adapter work, required core/GUI
changes, help, critical errors, correct interpretation of limitations, recovery,
handoff, reopening after updates and subsequent reuse without developer help.
Observe real intended researchers and distinguish installation, usability,
integration and scientific acceptance. Set task-specific decision rules before
the exercise; no general success percentage, user result or adoption claim is
established here. Correctness, usability, interoperability and sustainable
maintenance define the selected laboratory acceptance exercise. Comparative
productivity is a separate question when relevant; a useful integration need
not outperform another tool on every measure.

The [original OT-056 pilot](research/ot056-researcher-pilot.md) retains its
proposed 30% time-reduction target and matching evaluator for that specific
study. That target is not a shared-laboratory delivery threshold. Amending the
pilot requires a declared protocol/evaluator revision before new observations,
with the original criteria and any prior results retained.

## Optional extension gate

Extensions such as immunity, cell therapy, multiscale models, new devices or
formulations, surrogates, optimization, AI assistance, remote execution and live
team collaboration remain possible parts of the laboratory. Their scope follows
the roadmap and these evidence gates:

1. **Admission:** identify the researcher question, reusable upstream assets,
   capability to connect or extend, necessary observations and rights, evaluator
   and maintenance responsibility. Explain why the integration is useful and
   what will be reused or contributed upstream. Identify a suitable reference
   workflow when the question calls for a comparison.
2. **Bounded exploratory integration:** demonstrate suitable contracts,
   ownership, causal/data boundaries, numerical behavior, failures and a
   reconstructible complete task. Label hypothetical mechanisms and unavailable
   evidence explicitly.
3. **Supported capability:** retain independent integration/use evidence,
   documented platform and reader compatibility, sustainable maintenance and
   claim-specific empirical/domain assessment where needed. Add only the
   advertised scope to installation, documentation and release evidence.

These gates do not require an original OpenT1D model or external approval of
routine fixes. A source label or synthetic curve alone does not establish a
working immune, graft-survival or treatment mechanism.

## Research capability traceability

The 48 IDs below retain the scope of the 25 October 2026 product research. They
are requirement identifiers, not implemented APIs. Package references identify
planned ownership or supporting work, not order or proof of completion. The
[roadmap](../ROADMAP.md) controls dependencies and status; OT-058 retains its
existing Windows installer scope.

| Capability ID | Requirement | Planned work packages |
| --- | --- | --- |
| SCI-01 | Capability and scientific semantics registry | OT-059 |
| SCI-02 | Experiment and scenario definitions | OT-059, OT-063 |
| SCI-03 | Native adapter families and executable conformance | OT-062 |
| SCI-04 | Multiple clocks, events and delivery | OT-059, OT-061, OT-062 |
| SCI-05 | Comparison design and result semantics | OT-063 |
| SCI-06 | Mechanistic composition and replacement | OT-069 |
| SCI-07 | Calibration, observations and identifiability | OT-068, OT-069 |
| SCI-08 | Numerical, parameter, measurement and structural uncertainty | OT-063, OT-069 |
| SCI-09 | Selective standards bridges | OT-070 |
| SCI-10 | Evidence descriptions and independent integration | OT-059, OT-072 |
| FLOW-01 | Common experiment envelope and task interfaces | OT-059, OT-067 |
| FLOW-02 | SDK and adapter protocol across separate environments | OT-060, OT-061, OT-062 |
| FLOW-03 | Scientifically defined data and observation artifacts | OT-067, OT-068 |
| FLOW-04 | Fit, frozen model, simulation/prediction and evaluation | OT-068 |
| FLOW-05 | Shared result tables and task-specific reports | OT-063, OT-064, OT-067 |
| FLOW-06 | Campaigns and complete planned-work ledger | OT-066 |
| FLOW-07 | Optional external executor | OT-071 |
| FLOW-08 | Source, model, data and adapter catalogue | OT-059, OT-074 |
| FLOW-09 | Local private data and reproducible handoff | OT-064 |
| FLOW-10 | Researcher interface and independent integration | OT-060, OT-072 |
| UX-01 | Question-led projects and workbench | OT-064, OT-065 |
| UX-02 | Standalone installation and application lifecycle | OT-058, OT-061, OT-073 |
| UX-03 | One plan across GUI, CLI and programming access | OT-060, OT-065 |
| UX-04 | Understandable data and model intake | OT-065, OT-068 |
| UX-05 | Predictable execution lifecycle | OT-061, OT-065, OT-066 |
| UX-06 | Question-led comparison and visualization | OT-063, OT-065 |
| UX-07 | Understandable evidence and limitations | OT-059, OT-065 |
| UX-08 | Handoff, archives and collaboration | OT-064 |
| UX-09 | Onboarding, tutorials and programmer entry | OT-065 |
| UX-10 | Accessibility, correction and diagnosis | OT-065, OT-073 |
| UX-11 | Independent user validation and adoption evidence | OT-072 |
| UX-12 | Support, governance and maintained extensions | OT-073, OT-074 |
| CORE-01 | Architecture inventory and gradual route extraction | OT-059, OT-060 |
| CORE-02 | Versioned public contracts | OT-059 |
| CORE-03 | Installable Python SDK and CLI | OT-060 |
| CORE-04 | Portable owned-process lifecycle | OT-061 |
| CORE-05 | Runtime and adapter environment management | OT-061 |
| CORE-06 | Project/results storage outside installation | OT-064 |
| CORE-07 | Adapter registration and conformance kit | OT-062, OT-074 |
| CORE-08 | Layered quality and verification scopes | OT-059, OT-062, OT-073 |
| CORE-09 | Reproducible distribution and supply chain | OT-058, OT-073 |
| CORE-10 | Private data and shareable projects | OT-064 |
| CORE-11 | Explicit code trust and execution policy | OT-061, OT-073 |
| CORE-12 | Contribution, ownership and continuity | OT-074 |
| CORE-13 | Performance measurement and resource budgets | OT-066 |
| CORE-14 | Useful, redacted diagnostics | OT-061, OT-065, OT-073 |
| CORE-15 | Contract and historical reader lifecycle | OT-060, OT-064, OT-073 |
| CORE-16 | Published evidence and maintained releases | OT-073 |

OT-067 exercises the shared requirements through the existing M4/observer/MMTT
area and LAB-E; it does not invent a separate requirement family. The optional
mechanistic and calibration work remains explicitly represented by SCI-06 and
SCI-07. OT-072 tests reuse across the acceptance jobs rather than treating each
capability row as its own isolated product.
