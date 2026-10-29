<a id="productrichting-een-gemeenschappelijk-t1d-onderzoekslaboratorium"></a>

# Product direction: a shared T1D research laboratory

Translated from Dutch on 29 October 2026. Historical findings and source
references below retain their original scope; this is not a new research review.
Editorial wording was clarified on 29 October 2026 to describe contributions
and comparison scopes without ranking projects.

**Research date: 25 October 2026.** This report supports OpenT1D's product
direction. The [product document](../product-laboratory.md) is the canonical
requirements description; the [roadmap](../../ROADMAP.md) is the canonical
implementation plan. The design choices and usage trials below are research
conclusions, not additional implementation commitments.

<a id="vraag-aanpak-en-bewijskracht"></a>

## Question, approach and strength of evidence

The central question is what value OpenT1D adds when existing projects already
provide simulation, controllers, glucose forecasting and biological analysis.
The opportunity is a coherent laboratory in which researchers combine, compare
and later reuse suitable models, methods, scenarios and observations. The
scientific algorithms need not be new. Practical benefits must be demonstrated
through less integration work for the second engine, second method and second
research question.

Three research agents investigated scientific interoperability, researcher
workflows and product experience/adoption in parallel. The lead agent
investigated architecture, quality, distribution and maintenance and integrated
the findings. This is research by three agents plus the lead agent, not an
independent human or scientific review. Sources consulted were repository code
and documentation, original publications, official documentation and upstream
issues. Source links accompany their claims.

No researchers were interviewed, partners recruited, private health records
opened or new scientific benchmarks run. The described user needs and cost
savings are hypotheses. Public documentation shows that a feature is offered;
it does not prove superiority. A preprint and an open issue have a different
strength of evidence from a replicated study or independent product test.

<a id="uitgangspositie-van-opent1d"></a>

## OpenT1D's starting position

The existing [architecture](../architecture.md) includes bounded native M1/M2
tracks and researcher intakes for controllers, predictors, secretion sources
and prognostic models. There are also a local GUI, runtime locks, campaigns,
source registration, retained failures and report reconstruction. These are
useful laboratory building blocks. A stable general model interface and a
published installable SDK are not current capabilities.

The [general task entry](../local-workflow-entry.md) registers ten routes.
The registry, checks and dispatch contain task-specific choices. The
[campaigns](../maintained-campaigns.md) manage repeated M4 studies but do not
form a general import, fit, simulation and analysis chain. The two
[MMTT tasks](../mmtt-sampling.md) already demonstrate concrete reuse of one
analysis core. The largest product gap is the transition between such tasks:
a useful fit result, observation artifact or scenario should feed a subsequent
question without new project management and report parsing.

Several boundaries determine the assessment. The current
[M2 comparison](../m2-tutorial.md) uses separate native tracks with different
controllers, signals and parameterizations. It does not run one common
controller on two interchangeable engines and is not an isolated experiment
on physiology alone. The
[M5 archive library](../research/m5-archive-library-verification.md) provides
inspection and verification of saved prognostic reports, not a general M5
execution GUI. Many current examples are synthetic and internally verified;
independent user acceptance and application-specific empirical evidence remain
separate open requirements.

<a id="het-bestaande-functionele-landschap"></a>

## The existing functional landscape

| Project or ecosystem | Existing function | Implication for OpenT1D |
| --- | --- | --- |
| [simglucose](https://github.com/jxx123/simglucose) | Physiological simulator, virtual profiles, controllers, scenarios, batch execution and Gymnasium | Reuse a native engine; do not build another copy of the same simulation |
| [LoopInsighT1](https://lt1.org/method/) | Multiple models and components, controllers, sensors and interactive experiments | Both a native host and a component source; more than a visualization tool |
| [APS_TestBed](https://github.com/UVA-DSA/APS_TestBed) | Multiple simulators, controllers and fault injection | Reuse existing multi-engine and fault-injection capabilities where suitable |
| [RL4T1D](https://github.com/RL4H/RL4T1D) and [GluCoEnv](https://github.com/RL4H/GluCoEnv) | RL environments, algorithms and training experiments | Connect training and inference; do not rebuild a general RL framework |
| [GluPredKit](https://github.com/replicahealth/GluPredKit) | Data processing, model training, prediction, evaluation and reports | Integrate an existing prediction pipeline rather than maintaining a parallel model catalogue |
| [ReplayBG](https://gcappon.github.io/py_replay_bg/documentation/twinning_procedure.html) | Personal parameter estimation through MAP/MCMC and [replay](https://gcappon.github.io/py_replay_bg/documentation/replaying.html) with changed inputs | Connect observations, fitting and scenario execution without reimplementing the estimation method |
| [BioSimulators](https://docs.biosimulators.org/Biosimulators_test_suite/) | Capabilities, standards and simulator conformance tests | Reuse general conventions and validators; focus custom work on T1D semantics |

Several existing projects support prediction research.
[GlucoBench](https://arxiv.org/abs/2410.05780) provides datasets, tasks and
reference models. The
[June 2026 MetaboNet-Bench preprint](https://arxiv.org/abs/2606.18640) addresses
multimodal forecasting, multiple data sources and subgroups. The
[May 2026 From Prediction to Practice preprint](https://arxiv.org/abs/2605.00645)
combines task-oriented prediction evaluation with simulator interventions.
These capabilities provide starting points for reuse and task-specific
comparison. Assess whether connecting or extending them helps the intended
research workflow, and retain their source attribution.

Biological analysis also has existing solutions.
[ISEC](https://pubmed.ncbi.nlm.nih.gov/8894385/) and the open R package
[`insulin.secretion`](https://cran.r-project.org/web/packages/insulin.secretion/index.html)
provide C-peptide deconvolution; [AOMM](https://www.nanomath.us/aomm) provides
Windows batch analysis of meal and glucose tolerance tests. The
[AOMM publication](https://journals.sagepub.com/doi/10.1177/19322968251365274)
describes validation against manually extracted reference results from an
earlier study. A comparison with OpenT1D still requires matching endpoints,
accessible software and appropriate usage rights. Assess estimator behavior,
scientific interpretation and interface usability separately.

<a id="waar-een-geïntegreerd-laboratorium-waarde-kan-leveren"></a>

## Where an integrated laboratory can add value

The relevant product unit is a study being extended. A controller researcher
wants to investigate the same question in another engine. A modeler wants to
replace an absorption component while retaining a simpler parameter change as
a comparator. A data researcher wants to use the same cohort selection for a
second predictor. A biomedical analyst wants to investigate which measurement
times add information after a sensitivity analysis. These roles need common
management, but not identical mathematical interfaces.

A common route can lead from question and project to sources, compatibility,
scenario/cohort, development, frozen evaluation, execution, comparison and
handoff. A Python user can start in a notebook and follow the same plan in the
GUI. A colleague can open an authorized export and check the analysis. New
domains supply their own scientific payload and report sections while reusing
project storage, execution status and archive facilities.

This is a product hypothesis with testable benefits. Measure how much extra
code, configuration, installation, assistance and interpretation work the
second and third tasks require. Compare with capable existing tools and a
good notebook, including preparation and maintenance on both sides. Fewer
steps are beneficial only when the user also reaches a correct result and
interpretation. An audit function supports this work; it does not replace the
broader laboratory ambition.

<a id="wetenschappelijke-compatibiliteit-als-kernfunctie"></a>

## Scientific compatibility as a core function

Compatibility must concern concrete capabilities. An engine may suit a basal
rate controller and be unsuitable for a policy that depends on pump history.
An offline estimator need not invent a time-step function. Whole-engine
integration preserves solver, state and component lifecycle. Biological
composition is a separate integration level, with explicit ownership of
absorption, secretion, transit, extraction, clearance, delay and measurement
noise.

Every relevant boundary needs units, compartment, administration route,
amount versus rate, whole-body/per-kg scale, temporal support and availability.
Solver steps, sensor acquisition, receipt, controller decision and delivery
are different clocks. A five-minute policy does not become an equivalent
three-minute policy merely by converting the action unit. The existing
[oref0 route assessment](../research/c1-comparator-route.md) demonstrates such
a practical incompatibility. An adapter must explain it before a lengthy
experiment starts.

Equal grams likewise do not mean an equal meal when one engine uses an
instantaneous bolus and another an absorption profile. Plasma, interstitium
and CGM are different signals; point measurements and interval averages are
not interchangeable. A scenario records both intent and effective native
translation. Virtual profile 1 in two engines is not a paired person.
Identical seeds do not automatically pair different random processes.

First compare suitable contrasts within engines, then investigate sensitivity
to engine choice. Retain tuning budget, complete planned grids, unsupported
cells and failures. Distinguish numerical, parameter, measurement, random,
structural and population uncertainty. A synthetic parameter stress test is
not an empirical population distribution. A technically valid composition does
not automatically inherit its components' biological validity.

An adapter conformance test must compare native and adapted execution under
meaningful stimuli and check reset, events, delivery, causality, errors and
numerical refinement. File integrity helps but does not replace these checks.
The existing [absorption replacement](../lit002-tutorial.md) is a useful
starting point: it compares a component change with native behavior and a
simpler parameter alternative.

<a id="gegevens-voorspelling-kalibratie-en-biologische-analyse"></a>

## Data, prediction, calibration and biological analysis

A shared data layer must distinguish time series, events, visits and derived
artifacts. Preserve source identity, actual measurement times, availability
where known, units, missingness, censoring, context and participant/visit
relationships. One five-minute grid cannot support every task. Unknown meal
or insulin data must not silently be interpreted as zero to make an importer
pass. ReplayBG's
[data requirements](https://gcappon.github.io/py_replay_bg/documentation/data_requirements.html)
illustrate how much semantics lie behind a seemingly simple table.

In forecasting, preprocessing, fitting, model state and evaluation belong
together as recognizable phases. A frozen model can be evaluated in its own
environment; changing reporting need not repeat training. Preserve fitting
data, splits and earlier evaluation access. A new folder does not make known
data unseen. Imports of existing predictions enable reanalysis, but do not
retrospectively prove which information the model actually used.

The [September 2026 reproducibility study by Lu et al.](https://journals.plos.org/digitalhealth/article?id=10.1371%2Fjournal.pdig.0001633)
examined 67 papers and eight models. Alongside technical and statistical
reproducibility, it investigated performance on other data sources. Models
were retrained per dataset with five-fold cross-validation; this was not
frozen model transport from OhioT1DM. Our design conclusion is that suitable
independent evaluation remains necessary and intended frozen cohort transport
requires a separate test. The study does not prove demand for OpenT1D;
synthetic platform tests do not establish human prediction performance.

Calibration adds another chain: observations and measurement model,
parameters, fitting, uncertainty, identifiability and testing under other
conditions. A better CGM fit does not automatically identify absorption or
hepatic extraction. Reuse existing estimators such as ReplayBG or suitable
[PEtab tooling](https://petab.readthedocs.io/en/latest/). A fitted parameter is
bound to its model structure; it does not automatically become valid in
another engine. Historical replay with given treatment does not itself prove
a counterfactual treatment effect.

MMTT is a valuable second domain trial because it adds inverse analysis and
assays. The current [observation analysis](../observation-analysis.md)
estimates total whole-body secretion including basal over 0–120 minutes,
with follow-up minus baseline, under fixed synthetic kinetics. This differs
from measured C-peptide AUC. Therefore assess separately the added value of
this model step against simpler suitable measures, and the product value
against a notebook with the same estimator. Notebook parity does not prove
additional scientific value.

Empirical use requires suitable paired visits, actual sample times, assay/LOQ,
medication and renal context, justified kinetics and a suitable interpretation
plan. The [Van Cauter standard kinetics](https://pubmed.ncbi.nlm.nih.gov/1551497/)
do not confer individual T1D validity on synthetic settings. Existing
[research on 90-minute measurements](https://pmc.ncbi.nlm.nih.gov/articles/PMC3554273/)
also does not automatically support the longitudinal secretion endpoint. The
[current empirical preparation](../research/mmtt-sampling-empirical-plan.md)
rightly keeps these requirements separate from software development.

<a id="architectuur-standaarden-en-hergebruik"></a>

## Architecture, standards and reuse

The recommended direction is a small shared project, experiment, capability,
execution and result layer with task-specific scientific contracts. Python
API, CLI and GUI use the same services. Migrate existing routes through this
core incrementally and retain their historical readers. A new abstraction
alongside unchanged route management would create a second codebase.

A multi-environment adapter can invoke an existing Python environment, Node
process, R script, native executable or container. Start with complete runs
and batches. Components coupled in time require a separate contract; a file
workflow must not imitate tightly coupled ODE feedback without numerical
coupling analysis. It must be possible to describe a plugin without executing
the model merely by opening a project.

Use a general result manifest with task-specific tables for trajectories,
events, parameters, metrics, coverage and attempts. Each metric carries
meaning, version, unit, support and aggregation unit. Different task outcomes
may share a library without a common quality ranking. Ordinary data/figure
export also makes the lab useful alongside notebooks and existing analysis
tools.

Standards serve different roles:

| Boundary | Suitable tool | Limitation to preserve |
| --- | --- | --- |
| Executable model exchange | [FMI](https://fmi-standard.org/docs/3.0.2/) | An FMU does not determine the co-simulation algorithm or biological ownership |
| Model representation | [SBML](https://sbml.org/documents/specifications/) and [CellML](https://www.cellml.org/specifications/cellml_2.0/index) | Equal syntax or units do not prove suitable scale or population |
| Experiment and bundle | [SED-ML](https://sed-ml.org/documents/sed-ml-L1V5.pdf) and [OMEX](https://github.com/combine-org/combine-specifications/blob/main/specifications/omex.md) | Support an explicit subset; arbitrary callbacks do not automatically become portable |
| Calibration | [PEtab](https://petab.readthedocs.io/en/latest/) | No replacement for a causal controller interface |
| Execution provenance | [Workflow Run RO-Crate](https://www.researchobject.org/workflow-run-crate/profiles/) | Metadata does not prove correct execution or valid physiology |

Add a bridge when it enables a useful source integration or exchange.
Translating all engines into one standard first is not a prerequisite for
shared laboratory value. Custom development should focus on T1D semantics,
compatibility checks, experiment flow and fair comparisons. Solvers,
inference, plotting and generic schedulers are suitable reuse targets.

For larger studies, [Snakemake](https://snakemake.readthedocs.io/en/stable/executing/cli.html)
and [Nextflow](https://docs.seqera.io/nextflow/executor) provide existing
executor boundaries. First connect one backend to a real study; do not build
custom cluster management. Limit resources and prevent oversubscription by
internally parallel fitters. Retain a complete planned-run/attempt register of
your own: the described
[Nextflow lineage](https://docs.seqera.io/nextflow/tutorials/data-lineage)
does not include failed and aborted tasks.

Cache identity applies per step. Changed metrics require new analysis, but
unchanged simulation or prediction artifacts can be reused. Changed inputs,
scenarios, models or runtimes affect the corresponding upstream steps. A cache
hit is not independent replication. Native checkpointing and rerunning are
different capabilities. [MLflow](https://mlflow.org/docs/latest/ml/tracking)
can support existing teams with runs and model registration; a central
tracking service need not be a mandatory dependency for every local user.

<a id="werkbank-installatie-en-toegankelijkheid"></a>

## Workbench, installation and accessibility

A project outside the installation/checkout is a more stable unit of use than
a collection of output folders. The workbench must connect a question,
sources, draft plan, freeze, execution and comparison understandably.
Programming experts retain access to scripts and full configurations; other
researchers should not need to manage Python objects or hashes to run a
supported task. Domain limitations appear at the choices they affect.

The examples of [Galaxy history](https://training.galaxyproject.org/training-material/topics/galaxy-interface/tutorials/history/tutorial.html)
and the [nf-core launcher](https://nf-co.re/docs/nf-core-tools/cli/pipelines/launch)
show reusable history and configuration patterns. They do not prove demand
for a new OpenT1D interface. Use such patterns without rebuilding an IDE or a
complete collaboration suite.

The selected Windows outcome of [OT-058](../../ROADMAP.md#planned-windows-installer-ot-058)
is one installer and launch shortcut, without requiring the user to manage
Git, WSL/Ubuntu, Python, dependencies or terminal commands. The current
POSIX-dependent lifecycle requires product work to achieve this. A native
backend is an option to investigate; app-managed WSL is not ruled out in
advance. The chosen solution must meet the user outcome and real clean
Windows checks. Prepared macOS use does not prove Windows installation.

Accessibility belongs in the ordinary flow: keyboard operation, focus,
readable status, labels, contrast and errors with recovery actions. Use
[WCAG 2.2](https://www.w3.org/TR/WCAG22/) as an explicit assessment framework;
do not claim conformance without testing. Tutorials, task guides, API
reference and explanation serve different functions, as
[Diátaxis](https://diataxis.fr/start-here/) describes. Test independent
installation, correct execution and reopening with actual researchers, and
record assistance and interpretation errors as well.

<a id="kwaliteit-privacy-en-houdbaarheid"></a>

## Quality, privacy and sustainability

Make execution, completeness, integrity, report reconstruction and scientific
acceptance separately visible. Reconstruction checks the saved selection and
analysis; it does not automatically reproduce an arbitrarily supplied
algorithm. Independent model re-execution and model-specific arithmetic
replay are stronger, separate guarantees. A correctly reconstructed failed
study remains failed.

Combine fast contract tests with native regressions, numerical oracles,
platform lifecycle and GUI/CLI parity. More tests do not replace individual
source and numerical checks. Retain suitable trusted readers for historical
archives; a new app version must not silently change old plans. API,
protocol, parameter, metric and reader versions answer different questions.

Researcher code currently runs under local trust; workers and deadlines do
not form a sandbox. Opening a shared project must not start a callback,
notebook or installation hook. Containers also provide no automatic guarantee
for hostile shared execution; see [Docker security](https://docs.docker.com/engine/security/).
Data access, network, secrets and resources must suit the chosen backend and
usage situation.

Private source data, individual outcomes and logs belong separately from a
shareable protocol package. Current native archives deliberately retain input
bytes and traces. A shareable export must explicitly select authorized parts;
hashes do not anonymize data. Without suitable data access, a colleague can
check metadata or released analysis, but cannot fully rerun the empirical
result. A synthetic fixture makes the route testable without replacing that
result.

Distribution rights apply per asset: code, parameters, checkpoints, data and
binaries may have different terms. Process isolation is not a general license
exception. Preserve source identity, notices and distribution scope and assess
appropriate rights before bundling; see the [licensing guide](../licensing.md).
Release identity and any citations must actually exist.

Keep official, experimental, community and historical integrations
recognizable. A supported adapter requires maintenance ownership, an upstream
policy, conformance fixtures and documentation. Supported core environments
and explicit historical locks can coexist; the
[Scientific Python maintenance framework](https://scientific-python.org/specs/spec-0000/)
is a reference, not a reason to replace research baselines silently. Measure
support burden and storage growth before promising extra engines or services.
[JOSS review](https://joss.readthedocs.io/en/latest/reviewer_guidelines.html)
may help later but does not replace a demonstrated research application.

<a id="welke-productproeven-de-richting-kunnen-beoordelen"></a>

## Product trials that can assess the direction

A convincing trial includes a suitable controller study through two engines,
followed by a second controller and question without a new core or GUI route.
Another trial uses the same project facilities for MMTT sensitivity and
sampling loss. A forecasting route then tests fitting/evaluation and separate
runtimes. A colleague must be able to open an authorized handoff and
reconstruct a report; an interrupted campaign must retain its full attempt
history. These are usage criteria, not additional work packages alongside the
roadmap.

Measure time to first correct result, assistance, new integration code,
configuration work, critical interpretation errors, handoff and actual reuse
in a subsequent study. Set boundaries per trial in advance; do not invent a
universal percentage time saving. If every new question again requires
project management, supervision and report logic, the core needs
consolidation. If an existing tool solves the complete task better, an
upstream contribution or small adapter may be more valuable than a new
internal feature.

Immunology, cell therapy, multiscale models, surrogates, optimization and
cloud teams remain possible directions. Each admission requires a concrete
research question, suitable source and rights, defensible coupling,
appropriate evaluator and maintenance capacity. Unit conversion does not turn
a cell model into a human whole-body T1D engine. A synthetic prognosis is not
a therapy or immune simulation. These open evidence questions need not block
useful internal platform development; they bound the claims of each extension.

The main conclusion is therefore a broad but testable product goal: make
existing models and methods usable together for successive studies while
preserving their differences. Concrete requirements belong in the
[product document](../product-laboratory.md); selection, dependencies and
implementation remain recorded in the [roadmap](../../ROADMAP.md).
