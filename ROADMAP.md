# OpenT1D roadmap

OpenT1D is building an open research laboratory for type 1 diabetes. The aim is
for researchers to bring a model or method, compare it across suitable studies
and share results that a colleague can reproduce. The first biological focus is
how endogenous insulin production changes over time. [Project vision](docs/vision.md)

## Current position

The public starting point is a pair of synthetic mixed-meal tolerance test
(MMTT) analyses. Researchers can explore how assumptions and fewer blood samples
affect estimates of insulin secretion. A shared SDK and workbench already support
internally verified studies, comparisons and reopening saved results. Independent
use and supported distribution remain open milestones. [Research tasks](README.md#first-research-task)

## Now, next and later

**Reusable controller experiments.** Work on the LT1 and simglucose adapters
(OT-062) is well underway. LT1 is in native qualification. The simglucose
adapter has been tested against a scripted engine. Native qualification is
still open. Comparison design (OT-063) proceeds alongside qualification,
with the research question defining
which observations and outcomes can be compared. The milestone is a second
controller and research question using the same integration, with the same
study and results available through Python, the command line and the graphical
workbench. [Native adapter scope](docs/research/ot062-adapter-audit.md)

**A study using measured data.** In parallel, the research track asks how an
individual's insulin secretion changes between two MMTTs a year apart. TrialNet
TN05 is the candidate source. Its ability to support that question depends on
linking the visits, actual sample times and assay measurements. A measured-data
study also requires authorized access and a scientifically reviewed method.
[Paired MMTT study decision](docs/research/ot067-068-mmtt-data-decision.md)

## Common laboratory delivery plan

Independent use is the next product milestone. It is reached when a researcher
can install the laboratory, adapt a study to a second question and hand the
result to a colleague who can reopen and interpret it. Early user studies can
start with the existing MMTT candidate while controller integration continues. Distribution follows for
the tasks and platforms that have demonstrated this workflow.
[Researcher workflows and product requirements](docs/product-laboratory.md)

## Research direction: data to assessed digital twins

A reproducible study with measured data provides the basis for a personal model.
Calibration depends on the question, the observations and a way to evaluate
predictions on reserved data. A secretion study can advance on its own evidence.
A claim involving two simulation engines also needs both adapters to be
qualified. The longer-term goal is a research twin whose predictions can be
tested prospectively as new measurements arrive, ultimately supporting research
into preserving, restoring or replacing insulin production. [Scientific evidence ladder](docs/research/roadmap-history-2026-11-22.md#evidence-ladder-and-scientific-horizon)

The [November planning record](docs/research/roadmap-history-2026-11-22.md)
preserves the detailed milestones and package dependencies. The
[October record](docs/research/roadmap-history-2026-10-28.md) covers the
earlier experiments and their evidence.

<details>
<summary>Earlier roadmap sections</summary>

- ### [Current execution selection](docs/research/roadmap-history-2026-11-22.md#current-execution-selection)

- ### [Evidence ladder and scientific horizon](docs/research/roadmap-history-2026-11-22.md#evidence-ladder-and-scientific-horizon)

- ### [Next bounded research-data increment](docs/research/roadmap-history-2026-11-22.md#next-bounded-research-data-increment)

- ### [Public development priorities](docs/research/roadmap-history-2026-11-22.md#public-development-priorities)

- ### [Integrated-main smoke and current status](docs/research/roadmap-history-2026-11-22.md#integrated-main-smoke-and-current-status)

- ### [Selected development window: first integrated laboratory](docs/research/roadmap-history-2026-11-22.md#selected-development-window-first-integrated-laboratory)

- ### [Starting point and selection rationale](docs/research/roadmap-history-2026-11-22.md#starting-point-and-selection-rationale)

- ### [Ordered implementation and acceptance](docs/research/roadmap-history-2026-11-22.md#ordered-implementation-and-acceptance)

- ### [Scientific bridge for the connected study](docs/research/roadmap-history-2026-11-22.md#scientific-bridge-for-the-connected-study)

- ### [Working cadence, review and first-use evidence](docs/research/roadmap-history-2026-11-22.md#working-cadence-review-and-first-use-evidence)

- ### [Stretch and subsequent expansion](docs/research/roadmap-history-2026-11-22.md#stretch-and-subsequent-expansion)

- ### [Implemented AI development and ongoing review practice](docs/research/roadmap-history-2026-11-22.md#implemented-ai-development-and-ongoing-review-practice)

- ### [Reliability cases and remaining work](docs/research/roadmap-history-2026-11-22.md#reliability-cases-and-remaining-work)

- ### [Public CI and documentation boundaries](docs/research/roadmap-history-2026-11-22.md#public-ci-and-documentation-boundaries)

- ### [Mac feasibility and distribution boundary](docs/research/roadmap-history-2026-11-22.md#mac-feasibility-and-distribution-boundary)

- ### [Outcome and boundaries](docs/research/roadmap-history-2026-11-22.md#outcome-and-boundaries)

- ### [Delivery slices and integration order](docs/research/roadmap-history-2026-11-22.md#delivery-slices-and-integration-order)

- ### [Shared-core extraction queue](docs/research/roadmap-history-2026-11-22.md#shared-core-extraction-queue)

- ### [Parallel streams and handoffs](docs/research/roadmap-history-2026-11-22.md#parallel-streams-and-handoffs)

- ### [Bounded workbench design preparation (OT-065)](docs/research/roadmap-history-2026-11-22.md#bounded-workbench-design-preparation-ot-065)

- ### [Selected Concept v1 implementation slice (OT-065)](docs/research/roadmap-history-2026-11-22.md#selected-concept-v1-implementation-slice-ot-065)

- ### [Deferred screen-reader qualification](docs/research/roadmap-history-2026-11-22.md#deferred-screen-reader-qualification)

- ### [Planned core and product work packages](docs/research/roadmap-history-2026-11-22.md#planned-core-and-product-work-packages)

- ### [Windows installer and platform sequencing](docs/research/roadmap-history-2026-11-22.md#windows-installer-and-platform-sequencing)

- ### [Acceptance, evidence and stopping rules](docs/research/roadmap-history-2026-11-22.md#acceptance-evidence-and-stopping-rules)

- ### [Scientific milestones and evidence gates](docs/research/roadmap-history-2026-11-22.md#scientific-milestones-and-evidence-gates)

- ### [P1 — First usable research product](docs/research/roadmap-history-2026-11-22.md#p1--first-usable-research-product)

- ### [C1 — First original OpenT1D controller](docs/research/roadmap-history-2026-11-22.md#c1--first-original-opent1d-controller)

- ### [M5 — One defined cell or immune therapy question](docs/research/roadmap-history-2026-11-22.md#m5--one-defined-cell-or-immune-therapy-question)

- ### [Planned Windows installer (OT-058)](docs/research/roadmap-history-2026-11-22.md#planned-windows-installer-ot-058)

- ### [Historical implementation and planning](docs/research/roadmap-history-2026-11-22.md#historical-implementation-and-planning)

- ### [Next implementation: AI development](docs/research/roadmap-history-2026-11-22.md#next-implementation-ai-development)

- ### [Proposed internal follow-up — OT-031: multiple M4 secretion sources](docs/research/roadmap-history-2026-11-22.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources)

</details>
