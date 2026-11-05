# Vision

OpenT1D builds an open, shared virtual laboratory to better understand type 1
diabetes and accelerate research into preserving, restoring and replacing
endogenous insulin production. Researchers should be able to connect authorized
human measurements with suitable biological models, investigate disease
progression and interventions, and reproduce or extend each other's experiments.
The primary product is a **common research laboratory**, connecting experiment
design, model integration, execution, analysis and evidence. OpenT1D supplies
research tools, not a patient dataset or a clinical treatment.

The long-term ambition is scientifically assessed **digital twins that help
advance prevention, better treatment and cures**. Compatible multiscale models
could link glucose metabolism, insulin dynamics, beta-cell function, immunity,
devices and therapies, while representing meaningful differences between people.
The laboratory should help researchers test explanations, identify informative
measurements and design better experiments, including disease-modifying and
cell-replacement studies. These ambitions require progressively stronger models,
observations and external assessment; this repository does not currently provide
a validated multiscale digital twin or evidence of treatment benefit.

## From measurements to research twins

A research twin is a model linked to a specified physical counterpart, updated
with new measurements, with predictive capability and a defined use in the
research process. Its identity includes the model and observation assumptions,
data lineage, estimated parameters or states, uncertainty and evidence for that
use. A personalized fit or a synthetic virtual patient alone does not establish
these properties. A first bounded twin could help choose the next measurement
or experiment, with researchers assessing the resulting observations. Real-time
operation and autonomous treatment decisions are not prerequisites for that
research use.

The laboratory is the primary software product; twins are scientific artifacts
developed and assessed within it. Shared data intake, analysis, calibration,
simulation and reporting should serve one coherent research workflow through
GUI, Python and CLI access. Separate tools or services are justified by a real
boundary or user need, rather than by creating an application for each stage.

The first selected scientific focus is **beta-cell function and disease
progression**: how endogenous insulin production changes over time, which
individual differences can be measured or explained, and what evidence would
distinguish an intervention effect from the natural course. Repeated MMTT,
C-peptide and relevant glucose observations are a starting point to assess with
researchers, not an assumed available dataset. Existing synthetic observation
and secretion tasks provide useful infrastructure and reference cases. The
current MMTT tasks remain synthetic-only; human-data execution needs a separately
qualified method and authorized protocol while preserving those contracts. Their
fixed-kinetics inverse MMTT estimator does not calibrate the causal M4 model,
establish anatomical beta-cell mass or identify an intervention effect.

This focus connects a tractable starting task to the larger ambition. Richer
immune and cell-replacement mechanisms can follow when suitable measurements,
scientific reviewers and intervention-specific evaluation support them. A virtual
graft study is a conditional feasibility direction, requiring an experimental
question and appropriate collaborators; it is not a second implementation
commitment or an existing partnership. The
[roadmap](../ROADMAP.md#research-direction-data-to-assessed-digital-twins) owns
the ordered steps and their evidence gates.

## Reliable data as an entry into the laboratory

The first data contribution is a trustworthy path from a selected research
source to a reproducible study. Participant and visit linkage, units, clocks,
missing or censored observations, extraction versions and quality decisions
must remain inspectable. A repeated export should not require rebuilding the
study by hand. Ambiguous linkage or an unsupported measurement needs an explicit
decision rather than a silent correction.

Build only the source-specific bridges and scientific checks needed for that
path. Reuse suitable hospital extraction, identity, storage and interoperability
systems, and existing models and estimation tools. Research groups should be
able to keep restricted data in their approved local environment. OpenT1D's
contribution is the preserved connection between measurements, assumptions,
models and assessable results, rather than a universal hospital integration
platform or a centrally owned patient-data collection.

The research direction has external precedent: the
[NIDDK data-standards workshop](https://www.niddk.nih.gov/news/meetings-workshops/2025/data-standards-2025)
addresses integration and interoperability gaps; the
[NIH digital-twin topic](https://grants.nih.gov/funding/find-a-fit-for-your-research/highlighted-topics/129)
emphasizes fit-for-purpose twins, updating and uncertainty assessment.
[C-Path's 2025 trial-simulation pilot announcement](https://c-path.org/c-paths-t1d-consortium-to-release-a-clinical-trial-simulation-tool-for-new-onset-trial-design/)
also shows existing work on longitudinal C-peptide and trial design. These are
reasons to test a useful complementary contribution, not evidence of demand for
OpenT1D, access to those resources or a reason to rebuild their tools. Establish
that need with intended users and compare against their competent existing
workflow before broadening the product.

## A connected laboratory

A researcher should be able to define a question, select appropriate models,
observations or a virtual cohort, configure an experiment and inspect its
results and uncertainty. A colleague should be able to open the saved study,
understand its assumptions and failures, replace a compatible method or
condition, and assess how the conclusion changes. Work already done to
connect, run and report an experiment should be reusable for the next task.

The same laboratory should serve researchers who work through a graphical
interface and those who use code, notebooks or a command line. They need a
shared experiment plan and scientific result, with task-appropriate controls
and complete programmatic inspection. This is a product direction, not a
claim that a stable general API or common project system already exists.

Possible tasks include comparing automated insulin delivery, evaluating
forecasters, investigating insulin formulations and residual secretion,
assessing meal-test observations, and studying selected cell-replacement or
immune mechanisms. Each needs an explicit population, disease stage,
timescale, scientific contract and evidential basis. A common workbench does
not make these different questions interchangeable.

## Infrastructure and building blocks

OpenT1D develops shared laboratory infrastructure and attributed integrations
through complete research tasks. Project and experiment organization,
configuration, capability checks, runtime setup, execution, failure accounting,
comparison and durable reports should work together across supported tasks.
The [product requirements](product-laboratory.md) describe this intended
experience. The [architecture direction](architecture.md) separates that
future common core from the current bounded implementations.

Reuse existing models where suitable. A whole simulator can be a module,
retaining its native equations, solver and process lifecycle. Replace smaller
components when their responsibilities and biological meaning support a
sound boundary. For example, replacing a controller is different from
splitting tightly coupled glucose and insulin equations. An original model
or method remains a separately justified research choice; platform success
does not depend on OpenT1D inventing one.

Small reference implementations and clearly labeled invented fixtures can
exercise a workflow. They are not a supplied patient population or biological
validation. Researchers retain responsibility for the rights, suitability and
interpretation of their own data and methods.

## Principles

1. **Deliver complete research jobs.** Connect design, execution, interpretation
   and preservation so another researcher can use the result.
2. **Demonstrate reuse beyond the first example.** A second method, engine or
   question, followed by a third task or domain, should reuse the same
   infrastructure without a separate core or GUI for each route. Measure the
   additional integration and maintenance effort.
3. **Preserve scientific meaning.** Units, compartments, routes, clocks,
   available information and process ownership determine compatibility.
   Unsupported combinations need an actionable explanation.
4. **Carry evidence with the experiment.** Preserve source identities,
   assumptions, planned attempts, failures, analysis and reader versions.
5. **Keep evidence layers distinct.** Software checks, native reproduction,
   independent use, empirical assessment and treatment benefit answer
   different questions. Agreement between simulators is not real-world
   validation.
6. **Make independent use and contribution possible.** Support appropriate
   installation, accessible task flows, programmatic use, documentation,
   attribution and reviewable integration boundaries.

## Growth from the existing laboratory

The M0–M2 references and bounded internal verification provide the foundation.
P1 supplies a fixed synthetic task, local controller intake and attributed
examples. A human reviewer conditionally approved the distribution rights for
one exact internal P1 Git-bundle handoff; independent intended-user execution
and product acceptance remain open. That decision does not authorize a general
release or broader distribution. The [P1 review record](research/p1-product-acceptance-review.md)
keeps the scope and remaining evidence explicit.

M3 forecasting, M4 secretion/glucose/C-peptide and M5 prognosis supply
implemented bounded researcher workflows. The two synthetic MMTT tasks reuse
one observation-analysis core. Their existing contracts and historical
results remain authoritative while shared capabilities are extracted and
migrated route by route. Coexistence of tasks is useful preparation; it does
not establish an interchangeable general model interface. The current M5 GUI
supports report review and verification, not M5 execution.

[Decision 0070](decisions/0070-common-research-laboratory.md) extends the
[tool-first direction](decisions/0045-tool-first-research-platform.md) with
explicit common-laboratory delivery and reuse criteria. The
[roadmap delivery plan](../ROADMAP.md#common-laboratory-delivery-plan) is
canonical. The [product-direction research](research/product-direction.md)
provides its evidence and alternatives, not a competing backlog.

Standards-based exchange, larger compute backends, devices, personalization
and biological extensions can join when a concrete task, suitable sources,
review and maintenance capacity justify them. Beta-cell exploration need not
wait for every device feature. A therapy-efficacy claim still needs evidence
specific to the intervention. Historical C1 and B1 studies remain optional
research, with their negative findings and separate evidence preserved.

AI can help build the platform immediately. Research uses such as parameter
search, experimental design, surrogate models and new control strategies join
when there is a reproducible task and a suitable evaluation protocol.

## Progress

Measure progress by complete studies independently used and extended,
additional integration effort for a second and third task, useful modules
contributed, successful project handoffs and conclusions assessed against
appropriate external evidence. For the data-to-twin direction, measure repeated
data-preparation effort and correctness, independent reconstruction, predictive
or scientific information beyond simpler methods, and whether results improve
the choice of a subsequent measurement or experiment. Preserve unfavorable and
inconclusive findings. More code, engines, screens or simulated
profiles alone do not demonstrate product value or scientific progress.

The common laboratory grows through these reusable capabilities and complete
research jobs, without assuming a team size, release date or development speed.
