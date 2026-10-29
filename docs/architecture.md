# Architecture direction

**Status: bounded M1/M2 execution and P1/M3/M4/M5 researcher method workflows are implemented.** The [combined M3–M5 record](research/researcher-workflow-integration.md) verifies coexistence of the separate tasks, rather than a new multiscale model. [Decision 0004](decisions/0004-m2-native-process-tracks.md) preserves separate native M2 processes; its [evidence record](research/m2-reproduction.md) keeps independent human acceptance open. No stable general model API is established.

Under the [tool-first direction](decisions/0045-tool-first-research-platform.md)
and [common-laboratory decision](decisions/0070-common-research-laboratory.md),
the architecture should connect suitable researcher-owned models, controllers
and authorized data through supported, versioned boundaries. A shared laboratory
core should make projects, experiment plans, execution, comparison and evidence
reusable across scientific tasks. This direction and its proposed interfaces
are not an implemented common core or a stable public API. Current adapters
demonstrate particular engines and methods, not an interchangeable public
plugin system. OpenT1D keeps invented fixtures and provenance with its tools,
not a patient dataset.

[Decision 0055](decisions/0055-task-entry-and-m3-comparison.md) supplies the
implemented checkout entry and M3 comparison. [Decision 0057](decisions/0057-m4-source-comparison.md)
adds the implemented fixed M4 comparison. The registered routes preserve their
runner contracts, isolated locks and historical readers. [Decision 0058](decisions/0058-configurable-study-and-local-research-tools.md)
adds the separately versioned initial-load study, local campaigns, catalogue
and explicit setup, developed in separate worktrees. Their
[verification record](research/ot032-ot037-verification.md) separates numerical
study evidence from administration, reconstruction and environment readiness.

The entry now registers ten routes, including the two offline synthetic MMTT
tasks. [Decision 0068](decisions/0068-synthetic-observation-analysis-contract.md)
binds the shared observation-analysis core: frozen inputs, fixed kinetics,
conditional uncertainty, retained failures and trusted native reconstruction.
[Decision 0069](decisions/0069-mmtt-sampling-reuse.md) binds Task 2's
raw-time subsets and fresh calls through that same core. These observation
analyses remain separate from the causal M4 simulation boundary.

The [OT-057 interface changes](research/ot057-uiux-verification.md) reuse those
scientific contracts. Editing a saved plan produces a new checked freeze;
recognizable names belong to GUI metadata. Report views distinguish execution,
completeness and reconstruction, while original native reports retain authority.
The [OT-056 chain](research/ot056-researcher-pilot.md) verifies both tasks and
same-estimator notebooks internally; empirical and human acceptance remain open.

## Common laboratory: intended structure and migration

The [product requirements](product-laboratory.md),
[research assessment](research/product-direction.md) and
[roadmap delivery plan](../ROADMAP.md#common-laboratory-delivery-plan) define
the accepted direction and future acceptance work. The following describes
responsibilities to extract from existing routes; it does not introduce
implemented schemas, API signatures, a runtime or additional model validity.

The shared core should cover:

- Projects and reusable references to models, observations, scenarios and
  protocols, with user work stored outside installation or disposable checkouts.
- Experiment plans and capability checks, preserving source identities, units,
  clocks, causal availability, development/evaluation allocation and task scope.
- Runtime readiness, execution ownership, planned work and every attempt,
  including cancellation, failures and explicitly supported recovery.
- Result context, comparison support, durable archives and trusted report
  readers, with complete provenance and separate verification states.

GUI, CLI and programmatic access should use the same scientific plan,
validators, execution and analysis. The GUI may offer task-specific controls;
a programmer must be able to inspect and reuse the corresponding objects.
The core owns the common lifecycle. Each scientific task owns its admissible
inputs, estimand, metrics, numerical criteria and interpretation. For example,
controller co-simulation and retrospective C-peptide estimation need different
scientific contracts despite sharing projects, workers and result handling.
The present M5 GUI remains report review and verification, not M5 execution.

Extract and migrate route by route, with native conformance and reconstruction
checks before claiming parity. Keep historical protocols, source identities,
locks and compatible readers available. A new route must not silently alter
old experiments; a result-changing correction needs its own recorded scope.
A common wrapper over task-specific copies of all infrastructure would not
complete the migration.

Acceptance must exercise a second method, engine or research question and a
third task or domain using the same core and user flow. Measure new adapter
work, necessary core/GUI changes, maintenance effort and correct independent
reports. Demonstrate that the shared layer permits genuine reuse without
flattening model differences. Current M2 native tracks do not yet establish a
general engine swap or isolate an engine effect. A shared plan across engines
requires an explicit scientific compatibility assessment, not only a common
configuration file.

The existing bounded contracts below remain the record of what is implemented.
Detailed common schemas and public API boundaries follow concrete adapter and
research jobs, with their own decisions and verification.

## Main responsibilities

| Part | Owns | Does not establish by itself |
| --- | --- | --- |
| Experiment definition | Question, population, scenario, interventions, analysis plan | A valid scientific comparison |
| Execution layer | Scheduling, configuration, compatibility checks, run lifecycle | Correctness of an engine's equations |
| Model adapters | Translation to a specific engine and its supported capabilities | Validity outside the upstream model's scope |
| Modules | Declared physiological, sensing, delivery or control behavior | Validity of a new composition |
| Analysis and evidence | Metrics, provenance, uncertainty, references and reports | Clinical efficacy of an intervention |

M1 uses Python for its bounded experiment and adapter; see [decision 0003](decisions/0003-m1-interval-contract.md). M2 schedules whole runs in isolated Python and Node processes. Cambridge retains LT1’s Simulator, solver and component lifecycle; the parent owns configuration, process deadlines and artifacts, not physiological stepping. The controller boundary copies permitted observations and announcement history. Separate readers retain M1 mean subcutaneous metrics and M2 plasma point metrics. See the [M2 tutorial](m2-tutorial.md) for supported combinations and runnable commands.

## Two levels of modularity

**Engine integration** treats a simulator as a larger unit. This preserves coupled internal physiology and provides a practical starting point for reuse. Inputs, observations and actions must still have clear meanings.

**Biological composition** connects smaller modules where a defensible boundary exists. Each process has one owner: absorption, secretion, clearance or sensor delay must not accidentally be modeled twice. Inputs and outputs must describe compartments and routes as well as units.

Support both levels. Do not require third-party authors to rewrite a functioning model into an OpenT1D-specific equation language. Conversely, a file format or adapter cannot make a biologically incoherent combination valid.

## Implemented bounded contracts

The two native tracks establish explicit conventions for:

- Model identity, upstream revision, parameter provenance and supported population.
- Time origin, horizon, sampling intervals, event order, initialization and solver settings.
- Units and whether an input is a point event, amount or rate over an interval.
- What a controller can observe and when; keep latent physiology and future events separate.
- Reset behavior, random streams, stopping conditions and failed or partial runs.
- Ownership of overlapping biological processes and supported coupling directions.
- Output meaning, missing values, metric definitions and reconstruction of a report.

Capability checks should reject unsupported combinations with an actionable explanation. Do not silently invent a measurement, replace a missing mechanism or reinterpret an input to make an experiment run.

## Reproducibility record

Each M1/M2 experiment records a machine-readable manifest containing the protocol version; OpenT1D and upstream revisions; parameters and source data references; full configuration; random seeds; runtime and dependency environment; numerical settings; output locations or hashes; and analysis version.

The manifest must distinguish the intended run from what actually completed. Preserve failures, warnings and exclusion reasons. Reproducibility tolerances must match the model and environment; bitwise identity across all hardware is not an initial promise.

The Markdown [protocol template](templates/experiment-protocol.md) defines the information requirement. The [M1 tutorial](m1-tutorial.md) remains canonical for OT-001; [OT-014](research/m2-protocol.md) and the [M2 tutorial](m2-tutorial.md) define the separate two-track workflow. Evaluation freezes implementation, protocol and locks before the evaluation profiles run.

## M3 observed-data boundary

[Decision 0007](decisions/0007-m3-causal-forecast.md) adds a bounded offline CGM forecast workflow with new artifact/metric versions. Intake preserves source and signal meaning; the plan freezes rights, identities and splits. A separate locked estimator process fits only development data, then saves coefficients and a learned-model freeze before evaluation. Prediction receives only six permitted historical CGM values; scoring receives the future target afterward. The artifact reader needs neither estimator nor simulators. This does not add a clinical bridge to either physiological engine.

## Standalone biological reference

[Decision 0017](decisions/0017-standalone-beta-cell-reference.md) adds BC-001 as a separately locked two-state secretion calculation. Its new artifact schema records native secretion units, synthetic input, explicit initialization, failure status and reconstructible outputs. Existing engine physiology and M1/M2 contracts are unchanged. The [OT-015 boundary](research/m4-coupling.md) specifies a possible liver-inlet experiment, with basal/scaling and missing portal-action limitations; its kinetic-only stage is now implemented by [BC-002](research/m4-kinetic-protocol.md). [Decision 0018](decisions/0018-kinetic-insulin-inlet.md) keeps nonzero glucose feedback out of this bounded experiment. The existing M0 lock is reused; native package physiology and historical references remain unchanged.

[Decision 0019](decisions/0019-cpeptide-observation-reference.md) adds a separate forward C-peptide observation reference. BC-003 reuses the BC-001 numerical lock and BC-002 finite forcing without changing either. Its own central/peripheral C-peptide states and removal ledger are independent of insulin distribution and hepatic loss. Numerical integration, an analytical kernel, synthetic recovery and artifact reconstruction are separate. The subsequent BC-004/005 paired contract and execution use explicit synthetic baseline, scale and equimolar-processing assumptions; biological review and glucose feedback remain open.

## Standards and dependencies

Consider SBML, CellML, SED-ML/OMEX, FMI and PEtab for concrete exchange and calibration needs. Their roles and limitations are reviewed in the [research report](research/project-design.md). Compatibility with any standard is a future claim that needs a test.

Keep the experimental core independent of unnecessary engines and optional
analysis packages. Preserve native environments and add integrations with
explicit installation, source and license requirements. Standards and external
workflow/HPC executors should solve an identified exchange, calibration or
scale need, with a tested supported subset. Further biological composition
requires suitable mechanisms, population evidence and clear process ownership;
a registration or interface label is not biological validation.

[OT-058](../ROADMAP.md#planned-windows-installer-ot-058) fixes the Windows
user outcome: one graphical installer and launch shortcut without separate
Git, WSL/Ubuntu, Python, environment or terminal setup. Runtime packaging and
platform process behavior need an explicit architecture assessment. The
requirement does not choose native execution over every possible
application-managed compatibility mechanism. A launcher around the current
WSL instructions is insufficient. Verify every advertised workflow and preserve
user projects and reader compatibility through update and uninstall; macOS and
Linux support also needs declared, actually tested conditions.

Cloud services, a plugin marketplace, distributed execution and a universal
biological ontology remain future choices. Add them when a concrete researcher
job and operational/maintenance ownership justify them, rather than making
them prerequisites for common local laboratory reuse.

[Decision 0020](decisions/0020-paired-observation-contract.md) adds the BC-004 paired observation boundary preflight in the standard-library tooling environment. It normalizes one declared whole-body synthetic rate, separates basal/evoked input and checks proposed insulin/C-peptide initial inventories. BC-004 executes no coupled ODE; the historical BC-002 runner supports only zero incremental initialization. The conditional measurement protocol and domain-review packet remain distinct from the implemented arithmetic checks.

[Decision 0021](decisions/0021-paired-kinetic-execution.md) adds [BC-005 paired kinetic execution](research/m4-paired-kinetics-results.md). A standard-library parent starts explicit workers in the unchanged insulin and C-peptide runtimes. A new insulin wrapper accepts nonzero initial inventories through the original guarded native derivative; C-peptide reuses its existing solver. Both consume the checked BC-004 archive. Reports reconstruct from complete, hash-checked artifacts without either numerical runtime. This provides synthetic paired concentrations, with no glucose feedback or human calibration.

[Decision 0022](decisions/0022-glucose-secretion-kinetic-chain.md) adds the [BC-007 chain](research/m4-chain-results.md). A fresh, checked BC-001 archive supplies evoked secretion to both existing kinetic functions through one molar/body-mass conversion. The separate synthetic basal convention and initial inventories remain explicit. Source-sampling refinement is assessed separately from solver accuracy; glucose remains prescribed throughout. BC-001 through BC-006 and both numerical locks are unchanged.

[Decision 0023](decisions/0023-bounded-glucose-feedback-protocol.md) specifies the subsequent [BC-008 feedback boundary](research/m4-feedback-protocol.md). Its selected Dalla Man source separates pancreatic appearance, portal transit and liver arrival. An executed arithmetic/native-derivative preflight checks basal route replacement while preserving plasma insulin. The [BC-008 implementation](research/m4-feedback-results.md) now integrates native/source states and flux ledgers monolithically, independently audits glucose fluxes, compares native and equal-arrival controls and reconstructs reports from hash-checked artifacts. Source equations are verified analytically before feedback execution. The native route's fixed extraction and missing direct portal EGP signal remain explicit limitations.

[Decision 0024](decisions/0024-hepatic-structure-sensitivity.md) adds a separate [BC-009 hepatic comparison](research/m4-hepatic-assessment.md). It reuses the BC-008 source, native derivative and runtime, replacing hepatic loss and/or EGP through an isolated wrapper with explicit basal intercepts. Loss ledgers and the glucose derivative seen by secretion change at the same solver stage. Disabled states must match BC-008 exactly; no upstream parameter or historical reference is edited. Reports reconstruct the complete four-variant matrix, analytic source checks, independent flux balances and fresh-process repeat. This is a structural sensitivity experiment, without population calibration or new observations.

[Decision 0025](decisions/0025-feedback-cpeptide-observation.md) adds the [BC-010 forward observation branch](research/m4-feedback-observation-protocol.md). A completed BC-009 archive supplies pancreatic appearance Spo directly in molar per-kg units; the unchanged C-peptide module runs in its existing separate lock. The observer owns its inventories and removal and cannot mutate the parent glucose/insulin trajectory. Its finite input, source-solver and coarsening checks are explicit; post-portal arrival is retained only as a fault comparator. This prepares paired observations without fitting human data or asserting hepatic identifiability.

[Decision 0026](decisions/0026-joint-synthetic-identifiability.md) adds the separate [BC-011 experiment](research/m4-joint-identifiability-protocol.md). It reuses the BC-008 RHS and appends passive C-peptide equations inside the existing native numerical lock for repeated fitting. Initial insulin and C-peptide inventories are recomputed under explicit basal G/I conditioning. Known/unknown-clearance fits, shared synthetic observations and local sensitivity checks remain separate from numerical model verification and standard-library artifact reconstruction. Historical references and locks remain unchanged.

[Decision 0027](decisions/0027-cpeptide-volume-sensitivity.md) adds [BC-012](research/m4-volume-sensitivity-protocol.md), a separate observation-volume stress experiment. Its wrapper preserves the BC-011 dynamical model and amount inventories while scaling C-peptide concentration by inverse central volume. Fixed-correct, fixed-wrong and estimated-volume fits share the original synthetic observations, with one matched GI control. The experiment retains separate numerical verification, inference and standard-library reconstruction; it does not add a treatment mechanism or modify historical references.

[Decision 0028](decisions/0028-conditional-profile-likelihood.md) adds [BC-013](research/m4-profile-likelihood-protocol.md) around the unchanged BC-012 forward model. The numerical layer profiles a fixed coordinate while reoptimizing all remaining unknowns, using exact conditional volume minimization where applicable. A separate driver owns grid refinement, solver checks and atomic checkpoints; standard-library reconstruction verifies contour geometry and failure accounting. The nominal likelihood threshold and imposed bounds remain explicit statistical assumptions.
