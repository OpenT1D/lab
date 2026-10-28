# OpenT1D roadmap

## Direction and status

OpenT1D is building an **open, modular virtual laboratory for type 1 diabetes research**. Its primary output is reproducible research software for connecting and assessing researcher-chosen models, controllers and authorized data. It develops shared experiment infrastructure and attributed reference integrations where a concrete workflow needs them. The long-term ambition is to help investigate metabolism, beta-cell function, immunity, devices and therapies across compatible models; a general multiscale digital twin has not been built. [Decision 0045](docs/decisions/0045-tool-first-research-platform.md) records this tool-first direction.

Source-publication preparation is separate from releasing a supported product.
The [maintainer guide](docs/maintenance.md#proposed-first-release-scope) proposes
an initial two-task synthetic source-checkout scope; its
[dated audit](docs/research/publication-preparation.md) separates completed
source-only rights/security preparation from pending hosted-CI, destination
activation and independent-use actions. Original-material authority and
contact receipt are confirmed; [source-only rights and security policy](docs/publication-security.md)
excludes unresolved parameter rows and vulnerable historical automatic runtimes.
On 28 October 2026 the maintainer authorized the reviewed development source
publication on `OpenT1D/lab`. Its independent public root is `60a756b37078`;
GitHub Actions remains disabled and main uses pull-request protection without
a required CI status. The original development archive remains private.
Later product-release acceptance remains open.
This preparation does not accept
the shared laboratory, a Windows installer or any empirical/clinical claim.

The [private installer/publication integration](docs/research/installer-publication-integration.md)
combines the OT-058 branch with this plan and the source-publication safeguards.
Its local checks do not create a new signed/verified Windows release or widen
the two-task source offering. Public source publication does not complete the
separate Windows or product-release acceptance.

## Common laboratory delivery plan

**Planning decision, 25 October 2026 — all OT-059–074 deliverables below are planned.**
The next product increment develops a shared laboratory around the existing
working routes. [Decision 0070](docs/decisions/0070-common-research-laboratory.md)
records the direction; the [product requirements](docs/product-laboratory.md)
own the research jobs, acceptance criteria and 48-capability traceability map.
The [Dutch research report](docs/onderzoek/productrichting.md) owns the
comparative evidence and its limits. This section is the canonical future
implementation sequence. The dated sections below retain earlier plans,
completed work and outstanding evidence; they do not require repeating completed
software or waiting for every external review before starting this increment.
No runtime, public API, installer, release, user study or scientific result is
created by this planning change.

### Outcome and boundaries

A researcher should be able to bring a suitable method, reuse a checked project
across compatible models, compare outcomes, recover interrupted work and hand a
readable result to a colleague. The decisive test is the **second and third
research task**: does shared infrastructure reduce installation, adapter,
configuration, analysis and maintenance work compared with competent existing
tools and notebooks? Engine count and passing tests do not establish that value.

Keep both modularity levels: intact native engines and scientifically justified
component replacement. Shared project, plan, execution and result services sit
above task-specific scientific contracts. A controller, passive observer and
offline estimator need different capabilities; none must invent a common
physiological stepping method. Preserve solver behavior, units, compartments,
action support, information availability and process ownership. Current M2
tracks compare different complete systems; they do not yet demonstrate one
interchangeable controller or isolate an engine effect.

Reuse current runners, locks, validators, numerical oracles and historical
readers. Extract shared services through explicit adapters, one route at a time;
do not maintain a new core alongside permanently separate implementations.
Migration acceptance requires old commands and recorded archives to retain their
specified behavior, or an explicit versioned successor with a documented
compatibility boundary. Historical scientific protocols are not silently
rewritten to fit new contracts.

### Delivery slices and integration order

| Slice | Complete researcher outcome | Packages and integration gate |
| --- | --- | --- |
| 0 — Shared foundation on real tasks | One existing execution route and one unlike offline analysis route use the same project, plan identity, attempt and result services, while retaining their scientific contracts | OT-059; minimal OT-060/061/064. Inventory all ten registered routes and historical readers. Freeze representative valid, invalid, failed and relocated fixtures before extraction. First implementations may use the currently supported host; cross-platform claims wait for actual host checks. |
| 1 — Reusable control experiment | LAB-A/B/C: the same compatible controller contract is exercised on two native engines, then a second controller and a second research question reuse the integration through CLI/Python and GUI | OT-060–065, two OT-062 adapters and the minimal OT-066 ledger/resource controls needed by this task. Full stage caching and campaign recovery are accepted in their later consuming jobs. Show native parity, explicit compatibility refusals, causal inputs, matched within-engine contrasts and GUI/CLI plan parity. If a pair cannot preserve the declared contract, record the mismatch and narrow the claim; do not silently substitute controllers. |
| 2 — Reuse across a different research task | LAB-E, followed by a bounded LAB-D preparation: the existing MMTT analyses and an M4 observation chain reuse the product services; a fit/freeze/evaluate chain uses them where its task permits | OT-067 and bounded OT-068 on OT-063/064, using only the OT-066 stages needed by the selected chain. Synthetic execution is sufficient for internal integration. Human-data access and empirical evaluation require their separate authorized protocols. Domain-specific estimators and reports remain authoritative. |
| 3 — Independently usable laboratory | LAB-F/G and relevant LAB-A–E: an intended user installs the declared distribution, performs a second task, recovers a failure and hands off a project that a colleague reopens | OT-058 for the Windows installer outcome, OT-072/073 and OT-074 contributor exercise. Prepare pilots and packaging earlier; claim each OS/task only after its own installation, lifecycle, reader and independent-use evidence. Unavailable participants leave that acceptance open without blocking internal fixes. |

Slices describe incremental integration, not four large batches. Complete and
verify a small route before adding another capability. The first biological and
forecast preparations can proceed alongside control integration once their
shared boundaries are usable. Neither original C1 controller development nor
new human measurements is a prerequisite for the shared-core extraction.

### Immediate implementation queue

Start slice 0 with two named existing routes: `m4-study-secure` and
`mmtt-sensitivity`. The first exercises two isolated numerical runtimes and a
causal source/observer chain; the second exercises offline observation analysis.
Use the [maintained M4 contract](docs/m4-maintained-study.md) with its two
existing example sources and `fasting`, then derive a plan using the existing
`gastric_load_15g` condition. Preserve the native horizon, grid, numerical gates
and reference verification. Use the [MMTT example](docs/observation-analysis.md)
with one invented visit pair and its three required variants. These are known
synthetic integration fixtures, not reserved scientific evaluation.

| Increment | Bounded artifact and exit check |
| --- | --- |
| 1 — OT-059 contract/extraction packet | Map all ten routes at metadata level; inventory exact source/reader dependencies. Freeze only the shared fields needed by the two selected routes and cross-check the control-family contract. Retain each task's scientific payload and positive, refused, failed and relocated fixtures. Contract families remain provisional until the second native engine exercises them. Do not require migrating all ten routes to close this packet. |
| 2 — Minimal OT-061/064 services | Wrap the existing workers and readers with shared project storage, frozen identity and all-attempt accounting on one declared host. Start, interrupt and retain a controlled failed attempt; relocate and reconstruct complete and incomplete evidence. Preserve required source/reader snapshots explicitly. The current historical helper does not support MMTT; specify and verify that reader path rather than assume the helper covers it. |
| 3 — Minimal OT-060 installed route | Outside a checkout, create a project, check/freeze/run both selected tasks, derive the changed plan and reopen authoritative reports through Python/CLI. Original plans and attempts remain intact; native outputs meet the existing task-specific criteria. Use the declared reader/app compatibility cases for the first upgrade test. This closes the first usable slice, not the whole future SDK or portability matrix. |
| 4 — Early OT-065/072 feedback | Add the thin GUI path over those same plans and services. Prepare the formative exercise now and run it as soon as a technically verified candidate and an actual intended user are available. Use early observations of help, wrong interpretations and recovery to prioritize broader multi-engine work. An unavailable participant leaves user acceptance open and the usability risk recorded; internal integration and fixes can proceed. |

After each increment, record its verified scope and any contract change before
selecting the next artifact. Full campaign caching, new scientific mechanisms,
additional data sources and the complete supported-OS matrix retain their own
packages. Packaging/runtime probes for OT-058/073 can proceed in parallel; a
Windows candidate for the existing bounded routes need not wait for the full
SDK or two-engine study. This queue does not change the scientific acceptance
criteria of the selected routes.

### Parallel streams and handoffs

| Stream | Can start now | Shared handoff and dependency |
| --- | --- | --- |
| Scientific contracts and study design | Inventory meanings, comparison scopes, evidence labels and golden fixtures (OT-059); draft scenarios and estimands (OT-063) | Publish a small versioned fixture set with positive and refused cases before adapters, GUI or SDK claim conformance. Revise it from actual integrations rather than designing every future domain. |
| Core, SDK and native adapters | Inventory/extraction design (OT-060); separate simglucose and LT1 adapter audits (OT-062) | Implement against OT-059 and the OT-061 lifecycle. Native adapter work can proceed in parallel after the common boundary is frozen; integrated parity is checked per engine before comparison. |
| Projects, results and data | Storage/readers/private-export design (OT-064); owned-data lineage (OT-068) | Use the same frozen identities and failure semantics; a relocated archive must reconstruct before a route is declared migrated. Data intake has source-specific authorization gates. |
| GUI and researcher experience | Prototype task/project flow and accessible forms against fixtures (OT-065); prepare formative/comparative protocol (OT-072) | Render the shared plan and native reports; integrate only through the same core services. New controller adapters must not require new core/GUI dispatch branches. |
| Runtime, packaging and operations | OT-061 process audit and clean-host spikes; review the existing OT-058 installer candidate and remaining gates; OT-073 rights/build inventory | Reuse the recorded native-Windows decision and bounded host evidence; verify new source/artifact identities separately. Package only declared, distributable runtimes. Packaging preparation can start before the SDK is complete. |
| Biological and forecast applications | Select representative existing M4/MMTT and M3 chains (OT-067/068), preserve their current numerical evidence | Consume shared projects/results rather than building another isolated workflow framework. Shared science conventions depend on OT-059/063; empirical claims remain independently gated. |
| Maintenance and contributors | Assign ownership when available, write compatibility/review rules and adapter documentation (OT-073/074) | Templates and support can start early; external integration acceptance requires an actual contributor and recorded assistance. No contributor, reviewer or partner is presumed. |

Do not allocate every package simultaneously. Select an unblocked bounded
artifact per active stream according to actual capacity. Each selected package
records its owner when assigned, immediate consumer, dependencies, next artifact,
verification scope and remaining external gate. Integration fixtures are shared;
file and service ownership are explicit. A disagreement about scientific meaning
is resolved before either side hard-codes a conversion.

### Planned core and product work packages

Dependencies below are prerequisites for integrated acceptance, not prohibitions
on earlier design, fixture creation or feasibility probes. IDs reserve work in
this repository; no issue, delivery date or release version is implied.

| Package | Deliverable and acceptance | Integrated dependencies |
| --- | --- | --- |
| OT-059 — Contracts, capabilities and extraction inventory | Inventory the ten routes, locked runtimes, source inventories and reader boundaries. Define minimal versioned project/plan/asset/attempt/result descriptors plus task capability families. Preserve time, units, compartments, data availability, process ownership, planned denominators and separate evidence states. Valid/invalid fixtures cover a native control task, causal M4 route and offline MMTT analysis. Freeze an extraction map and layered quality matrix; no universal stepping API. | Existing contracts and evidence; decision 0070. First implementation package. |
| OT-060 — Installable SDK/CLI and route migration | A user creates a project outside a checkout, validates, freezes, explicitly executes and reads a supported synthetic task through documented Python and CLI entry points. Extract services from current routes and retain regression/readers. Migrate one native and one offline route first; schedule remaining routes explicitly from the inventory. Do not repackage the root tooling environment as a simulator. | OT-059; minimal OT-061/064 for execution and storage. |
| OT-061 — Portable execution and runtime management | One lifecycle owns explicit setup, start, crash, deadline, cancel and app-close behavior; retains all attempts and reuses identified isolated environments. Two conflicting adapter environments coexist. Test owned process cleanup and unrelated-process preservation on each claimed OS, including native Windows or a justified application-managed backend. Opening a project/report does not execute supplied code. Document trust/file/network scope; a subprocess/container alone is not a hostile-code sandbox. | OT-059; existing native runtime contracts and distribution rights. Integrate into OT-060 without requiring the whole SDK first. |
| OT-062 — Two native adapters and conformance kit | Wrap simglucose and LT1 through the smallest suitable native boundaries, preserving solvers and source identity. Demonstrate native-reference parity and applicable negative tests for reset, timing, event order, observation availability, action support, units, partial outputs and unsupported combinations. Keep stateful sampled controllers separate from pure continuous RHS callbacks; retain repeated/out-of-order callback probes without claiming they prove arbitrary code pure. Exercise one suitable controller contract across both only where its meaning is preserved, then a second controller. Ship a reusable adapter template/conformance suite. | OT-059/060/061; source-specific runtime and rights checks. |
| OT-063 — Scenarios, comparisons and uncertainty | Declare actual versus announced events, availability times, native translations, cohorts, seed schedules and development/evaluation exposure. Reconstruct within-engine contrasts before any cross-engine interpretation; retain full planned support and failed pairs. Distinguish solver error, parameter, measurement, stochastic, structural and population uncertainty. Add only analyses needed by LAB-A/E and an explicit estimand; no automatic universal ranking. | OT-059; OT-062 for engine acceptance and existing MMTT contracts for offline acceptance. |
| OT-064 — Project/result store, historical readers and private handoff | Preserve drafts, immutable freezes, assets, all attempts, original results and task-specific analysis outside disposable installations. Distinguish API/schema/model/metric/reader versions. Publish the supported archive-format/reader/app/host matrix. Move a project, reconstruct complete/failed/partial reports without native runtimes and reopen after an application upgrade within that matrix using trusted compatible readers; retain the required reader snapshots and explicit unsupported behavior. Export permitted assets with explicit private references and test absence of restricted payloads/tokens in example support bundles. Opening imported code never executes it. | OT-059; existing durable archives, catalogue and native readers. |
| OT-065 — Common task workbench and onboarding | GUI, CLI and Python expose the same scientific plan and core validations. Support project/draft/freeze, compatible asset selection, clear error recovery, real progress, cancellation, question-led comparison and native report/table export. Keyboard, screen-reader, zoom and non-color status checks cover the supported route. Reopening preserves work. Supply one tutorial for an analyst and one adapter/notebook route for a programmer. M5 execution is a separately specified extension; current M5 GUI support remains read/verify/download. | OT-059/060/064; OT-061 for lifecycle and OT-063 for comparison. Prototype against fixtures earlier. |
| OT-066 — Campaigns, stage cache and resource budgets | Generalize the existing planned-slot/all-attempt ledger, explicit retries and identity-checked resume. Bound local concurrency, deadlines, storage and memory with measured representative examples. Native checkpoint resume is a declared capability, distinct from starting another attempt. Cache simulation, fit, prediction and analysis by their relevant full identities: a metric change reruns affected analysis while unchanged upstream artifacts may be reused; changed inputs/model/runtime invalidate affected upstream stages. Report every reused artifact; a cache hit is not an independent repetition. | OT-060/061/063/064. |
| OT-067 — Biological and observation tasks on the shared laboratory | Route the existing M4-to-C-peptide observation chain and both MMTT analyses through shared project, runtime, attempt, result and GUI services. Preserve causal simulation versus retrospective inverse-analysis boundaries and current numerical/kinetic scope. A second question reuses the shared services and the same controlled observation-analysis core. Compare product effort with a competent same-estimator notebook; compare biological endpoints separately with appropriate C-peptide measures and glucose context. | OT-060/061/063/064; OT-065 for GUI acceptance. Existing OT-053–057 protocols remain authoritative. |
| OT-068 — Owned data and fit/freeze/evaluate chain | Separate source conversion, fit, frozen model, prediction/simulation and scoring artifacts. Retain participant/visit/episode identity, measurement versus availability time, missing/censored values, rights and holdout exposure. A changed score need not refit; changed training/preprocessing creates a new fit identity. Reuse existing M3/M5 boundaries; assess a concrete GluPredKit, ReplayBG or R-method integration before selecting dependencies. Complete LAB-D acceptance includes transfer of the frozen workflow to a second cohort. Synthetic fixtures verify plumbing; authorized source-specific intake and independent empirical evaluation are separate outcomes. Replay does not itself identify a counterfactual treatment effect. | OT-059/060/061/063/064; suitable rights/protocol before restricted access. |
| OT-069 — Mechanistic composition, calibration and identifiability | Reuse LIT-002 absorption and M4 secretion/observation cases to test common ownership/port principles, basal/initial-state conventions, disabled/native parity, amount balance and numerical refinement. Separate observation functions from mechanisms and fitting. Use mature calibration tools when suitable, with fixed/estimated parameters, objective, bounds, multistart/failures, identifiable/nonidentifiable synthetic controls and reserved assessment. A better fit is not proof of the mechanism. | OT-062/063/067; OT-068 where measured-data lineage is needed. Conditional on a specific composition/calibration question and maintained source. |
| OT-070 — Selective standards bridge | Select one useful donor model or exchange task and a supported standard subset. Demonstrate meaning-preserving import/export and suitable independent-runner comparison, including units, events, initialization, outputs and refused features. Choose among FMI, SBML/CellML, SED-ML/OMEX, PEtab or workflow provenance for the actual boundary; do not require every engine to implement them all. | OT-059/060 plus the applicable OT-062/063/069 boundary, donor rights and a named consumer when selected. Conditional; no standard or donor is selected here. |
| OT-071 — Optional external executor | If measured local limits obstruct a real campaign and backend access exists, connect one existing workflow/cluster executor. Run the same small frozen plan locally and remotely, retain late failures/denominators, translate job identity/cancellation and compare supported outputs within declared tolerances. Reuse upstream scheduling; avoid a new cloud control plane. | OT-061/064/066; actual resource need, backend and maintenance capacity. Conditional. |
| OT-072 — Independent second/third-task acceptance | Prepare formative then comparative tasks for method authors, domain analysts and report recipients. Actual intended users complete the selected LAB jobs, including their required second method and question, run, interpret limits, recover and hand off; record time, new glue code, core/GUI edits, critical errors, assistance and repeated use against their competent baseline. Freeze task-specific acceptance criteria before observations; preserve inconclusive/negative findings. Distinguish installation, usability, interoperability and empirical evidence. | Technically verified candidates for the selected LAB jobs, frozen exercises and actual participants. OT-058 gates Windows installer acceptance, not unrelated internal development or other OS scopes. |
| OT-073 — Maintained distribution and release practice | Declare supported OS/tasks, runtime/code/data rights, notices, dependency/build inventory, verifiable artifact identity, update/rollback/uninstall behavior, private project preservation, reader compatibility, diagnostics, security reporting and support scope. Exercise clean-machine installation and old-result access for each distributed artifact. Publish only real release identities, evidence and limitations. Prepare inventories and candidate builds before final acceptance. | Candidate builds use the applicable existing or migrated runtime/reader boundaries; a shared-SDK release requires OT-060 and the applicable OT-061/064 scope. Final Windows release acceptance consumes the OT-058 installer receipt and relevant OT-065/072 user evidence. Building the candidate does not require that receipt. No release or broad compatibility claimed now. |
| OT-074 — External extensions and maintenance continuity | Document adapter discovery versus explicit execution trust, family conformance, version policy, upstream attribution, review/triage and ownership. An actual external contributor integrates a second kind of method without editing core/GUI dispatch and hands it to another user; record assistance and maintenance cost. Define deprecation and reader-retention rules before publishing compatibility promises. A marketplace is optional, not a prerequisite. | OT-059/060/062 and applicable task family; OT-073 maintenance policy and actual contributor availability. |

### Windows installer and platform sequencing

[OT-058](#planned-windows-installer-ot-058) remains a first-class product outcome:
one graphical installer and launch shortcut on a clean declared Windows system,
with application-managed runtimes and no separate user-managed Git, WSL/Ubuntu,
Python or terminal setup. A launcher around today's prerequisite instructions
does not satisfy it. Establish the applicable OT-061 lifecycle and OT-064
project/reader boundaries. OT-073 first prepares the distributable candidate,
rights inventory and update/support policy; OT-058 verifies that installer on
clean Windows and records its separate internal and independent acceptance.
Final OT-073 Windows release acceptance then consumes those receipts. Candidate
construction does not depend on already passing installer acceptance, and a
bounded existing-workflow installer does not require the complete future SDK.
The separately developed OT-058 candidate now selects native Windows in
[decision 0073](docs/decisions/0073-native-windows-installer.md), with bounded
Windows VM evidence in its dossier. This supplies an internal existing-workflow
candidate; it does not complete the future common OT-061/064 services or the
OT-073 distribution acceptance. Preserve actual clean-host outcomes, failed
cases, source/runtime identities and unresolved distribution/maintenance rights.

Keep the existing Windows/WSL packet as an interim testing route. Its successful
execution, if obtained, would not by itself complete installer acceptance.
Do not claim macOS/Linux packaging or Windows parity from one macOS checkout
check. Define and test each supported platform/task combination separately.

### Acceptance, evidence and stopping rules

Each implementation package has a bounded internal acceptance record: exact
source/environment identity, changed behavior, applicable fixture/native/
numerical/process/GUI checks and remaining limits. Allocate fast contract checks,
native regression, numerical oracles, OS lifecycle, end-to-end task and release
checks by risk. Do not rerun all scientific studies for a documentation change,
and do not replace model checks with a CI badge. Preserve historical evidence
and failures as the core is extracted.

Keep implementation, internal numerical verification, reproduced reference,
independent use, empirical applicability and biological/therapy claims separate.
Human review or data rights constrain the affected claim/access; they do not
block unrelated internal work. A reconstructed report checks stored data,
selection and analysis. Re-executing an arbitrary supplied model requires its
code/runtime and separate evidence; retain stronger model-specific replay claims
only for routes that actually provide them.

For product evaluation, measure the full baseline: installation, preprocessing,
adapter/glue code, configuration, execution, interpretation, recovery and
maintenance. Record assistance and unsuccessful attempts. Set task-specific
thresholds before the exercise; do not invent universal success rates or treat
OT-056's proposed pilot targets as already achieved platform-wide acceptance.
Independent acceptance remains open until real observations exist.

Revisit a contract when the second engine or unlike task needs special cases
that conceal scientific meaning. Narrow an adapter when causality, native parity,
rights or ownership cannot be preserved. Reconsider a feature when a mature
upstream tool meets the same task with comparable effort and integration adds
no demonstrated reuse. Restrict the supported matrix when ownership or release
maintenance exceeds real capacity; preserve readable historical results.

Third engines, richer immunology/cell therapy, multiscale dynamics, personalization,
optimization/surrogates, AI assistance, live team collaboration, cloud execution
and model marketplaces remain candidates. Select one only with a concrete
research question, suitable source/rights, an evaluator, integration boundary and
maintenance commitment. New biology needs the observations and domain review
appropriate to its claim. These candidates do not gate slices 0–3.

## Recorded implementation and evidence

**Current status, 22 October 2026: M2 software, IV-001 and P1/0.1–0.4 bounded internal technical verification are complete. The current M3 forecast, M4 secretion/C-peptide and M5 prognostic researcher workflows are also implemented, integrated and internally verified.** The [combined execution record](docs/research/researcher-workflow-integration.md) identifies the completed software scope. The common local entry and multiple-candidate M3 comparison are implemented and internally verified as OT-029 and OT-030. OT-031 adds an implemented multiple-source M4 comparison with locally verified native execution and artifact reconstruction; its [verification record](docs/research/ot031-verification.md) owns the exact check scope. OT-032/033/034/037 add the separately versioned initial-load study, local campaigns, catalogue and locked setup; their [verification record](docs/research/ot032-ot037-verification.md) binds the separate local scopes. The common entry registers ten routes, including the explicit maintained M4 successor and synthetic observation analysis; its local GUI pilot and dependency maintenance have a separate [verification record](docs/research/ot035-maintenance-verification.md). OT-038 maintained campaigns, OT-039's read-only archive library and OT-040 GUI campaign management are implemented and internally verified locally; their [workspace record](docs/research/experiment-workspace-verification.md) binds the distinct native, process and browser evidence. OT-041 adds implemented and locally internally verified durable maintained-M4 archive packages, with preserved reader identities and relocated reconstruction; its [acceptance record](docs/research/durable-archive-verification.md) binds the separate native/browser checks. OT-042 adds implemented and locally internally verified synthetic M3 forecast/comparison GUI routes and explicit M3 durable readers; its [acceptance record](docs/research/m3-gui-verification.md) retains native/browser/relocation and unsealed-retention evidence. OT-043 adds schema-aware recorded manifest checks and fixed native M3 report verification/downloads to the general GUI archive library; the [acceptance record](docs/research/archive-library-verification.md) binds the corrected 34 M4 diagnostics, complete/failed/partial native reports, preserved original archives and integration into local main. OT-044 adds implemented and locally internally verified native synthetic M5 report verification/downloads in that same library, with full roster/attempt accounting and bound supplier declarations; its [acceptance record](docs/research/m5-archive-library-verification.md) preserves the exact native/HTTP/browser and locked-check scope. Independent human M2 reproduction, P1 product acceptance and the broader M3–M5 empirical/biological acceptance criteria remain open. The original M0 references, M1 workflow and frozen M2 results remain reproducible within their recorded scope; the [M2 evidence record](docs/research/m2-reproduction.md) retains their limits. No public release, independent researcher execution, external biological validity or treatment benefit is established.

Researchers manage their own models, controllers and permitted observations. OpenT1D does not distribute a patient dataset; public invented examples verify software mechanics only. Current P1 and M3–M5 method intakes each support a declared task and contract; they do not establish a stable general model API. This roadmap is based on dependencies and demonstrable outcomes. It makes no assumptions about staffing, available capacity or development speed. Technical preparation can advance while scientific evidence is being collected; claims advance only when their evidence supports them.

**MMTT increment, 22 October 2026:** OT-053–057 implement two
related synthetic tasks for retrospective mixed-meal tolerance test (MMTT) analysis:
assess whether a change in estimated endogenous insulin secretion depends on
analysis assumptions, then assess information loss when measurement times are
removed within the same test period. The [two-task plan](#planned-mixed-meal-analysis-tasks)
defines reuse, implementation, comparison with existing tools and acceptance.
The bounded synthetic OT-054/055 implementations reuse one controlled core;
[OT-056 technical integration](docs/research/ot056-researcher-pilot.md) is complete
with a verified two-task CLI/GUI/notebook chain. The seven OT-057 interface
fixes are integrated into local and GitHub main; the
[UI verification record](docs/research/ot057-uiux-verification.md) binds their
19 October macOS checks and 22 October remote verification. The human comparative
pilot is open. Suitable participant data, collaborating researchers, empirical validity and
comparative benefit remain unestablished. Existing software
completion and independent Windows/P1/GUI evidence requirements remain as recorded.

**GUI usability preparation, 13 October 2026:** the version-bound test packet,
explicit installation/check/start files and local observation worksheet are
implemented, internally verified and integrated into local and GitHub main.
The [session verification record](docs/research/gui-test-session-verification.md)
owns the actual macOS/native/browser checks and Windows preparation limits.
The separate [22 October MMTT packet](docs/research/mmtt-beginner-packet-verification.md)
is locally prepared and verified from main plus the packet extension.
The next practical steps are a real Windows/WSL host check, the first human
session and observation-driven fixes with human retests; see the
[usability plan](#planned-usability-work). These remaining acceptance steps do
not block unrelated internal development.

**Windows installation candidate, 27 October 2026:** [OT-058](#planned-windows-installer-ot-058)
implements an offline Windows 11 x64 installer for all current GUI routes, with
three private runtimes and a local browser launcher. Candidate J corrects the
Windows directory-inventory failure found during I's focused maintenance
preparation. J's build, independent payload audit and locked host check passed
(1,545 tests, 32 skips and strict documentation checks). The I-to-J upgrade test
phase failed at the installed-payload audit's 1,800-second limit. The graphical
Finish screen and automatic browser startup were observed separately. The full
payload audit later passed outside that limit and normal application stop was
confirmed; the original phase remains failed. Separate CompleteUpgrade passed a
fresh full audit within the same limit, preserved all 366 original files
byte-for-byte and passed 18 installed-J native tests without skips. The synthetic
32-draw MMTT API case and its fresh native reader passed with unchanged report
bytes. Repair passed with a fresh reader and unchanged original reports;
Reinstall also passed, starting with the application running. Attempt 08 passed
a clean J baseline, offline installation, shortcut reuse and one 32-draw MMTT API
workflow with fresh reconstruction; a separate agent browser review verified the
healthy Start page, results library and saved report. No active numerical-job
maintenance is claimed.

Recovery attempt 10 passed licensed clean installation from the genuine Edge
download, healthy automatic first GUI startup, shortcut reuse, normal exit and
124 native tests (six declared skips), with an exact full payload audit. Root
completed a fresh 32-draw Task 1 MMTT analysis and reader through the GUI, with
unchanged original reports. A separate sampling-information-loss API case also
passed with fresh readers. New synthetic M3 forecast/comparison and saved
readers passed; a separate genuine cancellation retained raw byte copies, with
integrity/reconstruction false and completeness unknown. Activation followed
explicit user authorization; the
candidate remains unsigned and public SmartScreen reputation is untested.
Two M3 durable-package export/integrity/reconstruction routes passed across
restart. Private-workspace launcher/session controls also passed, including
reopen, authentication/schema refusals, genuine stale-session recovery and
normal API/CLI stops. Further agent-operated GUI export, external Task 1 archive
index/reader, reversible visibility and normal exit passed. Two M3 raw-retention
receipts are fully preserved, with byte-copy checks only. Eleven-case lifecycle
preparation passed within its independently reviewed preparatory scope. The first
Maintain attempt failed before launch on its input path. The second completed
installation, launch refusal, full payload audit and data preservation, but its
report wrapper failed on an output-filename collision; the phase remains failed.
Separate report-only comparison and normal stop passed, with the full comparison
report independently verified. The original Uninstall05 and later observer failed. A separate controlled
Uninstall test then cancelled an observed native analysis cleanly. Post-removal
checks passed for both retained payloads, all 7,023 original data files and
Windows registration/shortcuts; eleven fresh retained-case readers passed with
22 unchanged report hashes, normal stop and a final full payload audit.
These targeted passes preserve the original failed phases and private-controller
failures. Full maintenance acceptance remains open. A separate fresh I-to-J upgrade passed
its full J payload audit, original-case preservation, fresh J reader, 18 native
checks and normal stops. The preservation check found 93 of 95 original files
byte-identical, exactly two precomputed verification-bookkeeping transitions and
zero additions; both original reports stayed identical. Original InstallI,
admission-wrapper and guard-controller failures remain recorded. This bounded
pass does not complete OT-058 or the remaining workflow/release gates.
The new campaign and M4 tests failed at fixed 600-second reference-worker
deadlines before candidate source evaluation. Their failures remain open.
Remaining workflows/lifecycle checks, full VM/TPM restore validation and
independent human acceptance remain open.

I's clean installation/startup and shortcuts passed. Its initial native failure,
unchanged warm retry pass, failed M4 run and failed maintenance preparation remain
recorded. The [verification record](docs/research/ot058-installer-verification.md)
separates these from earlier candidates' results. Complete Windows workflow and
lifecycle acceptance, independent user acceptance and public release remain open.

**Internal GUI fixes, OT-050, 14 October 2026:** eight agent-walkthrough
findings were resolved and locally retested on the separate
`codex/gui-usability-fixes` branch, then integrated into local and GitHub main
through [PR #37](https://github.com/OpenT1D/OpenT1D/pull/37).
The [fix verification record](docs/research/gui-usability-fixes-verification.md)
binds actual browser checks, a complete and a cancelled native M4 run,
artifact comparisons and the locked 1,282-test checks. Windows/WSL and the
independent human OT-048/049 steps remain open.

**Second internal GUI follow-up, OT-051, 17 October 2026:** the five findings
from the next internal UI/UX review are implemented and locally verified in
the separate `codex/uiux-round2-fixes` worktree/branch. The
[follow-up verification record](docs/research/gui-uiux-round2-verification.md)
covers draft recovery, action-specific M3 messages, reversible archive-reference
hiding, dated result ordering and display-only metric rounding. All five browser
retests and the locked 1,288-test checks passed, with 13 existing C1 skips.
Integrated into main on 17 October with the maintainer-requested `[skip ci]`
marker. Hosted CI was intentionally skipped; external Windows/human gates
remain open.

### Software completion and remaining milestone evidence

| Track | Completed bounded software | Evidence still open for broader acceptance |
| --- | --- | --- |
| M2 and IV-001 | Two native physiological tracks, frozen comparisons, numerical/fault/robustness verification and artifact reconstruction | Independent human M2 protocol execution |
| P1/0.1–0.4 | Fixed researcher task and external rate-controller intake, verified with two source structures and a second profile/seed pair | Independent intended-user exercise and product acceptance; broader distribution rights remain separate from the conditional exact internal handoff |
| M3 researcher forecast | Frozen local predictor intake, causal 30-minute forecast/persistence comparison, multiple-candidate comparison on common support, full synthetic accounting and reconstruction, locally verified GUI execution and native archive-library reports | Authorized source-specific human evaluation and independent usability |
| M4 researcher secretion | Configured causal source-to-glucose/insulin/C-peptide workflow, multiple frozen sources under identical conditions, two source structures, numerical checks and reconstruction | Suitable paired observations, biological interpretation, population calibration and independent domain/user review |
| M5 researcher prognosis | Frozen source/state intake, development-only reference, participant-disjoint synthetic comparison and reconstruction | Independent usability, authorized release linkage, domain review, empirical freeze, human prognosis and any treatment claim |
| MMTT tasks, OT-054/055/057 | Shared fixed-kinetic synthetic core, paired sensitivity and reduced-sampling CLI/GUI routes, 22-case CLI/notebook chain and seven internally retested interface fixes integrated into main | Authorized suitable observations, empirical kinetics, independent comparative researcher pilot and demonstrated product value |
| GUI usability preparation, OT-045–049 | Version-bound source/reference packet, Dutch session cards, explicit launch files and local observation export/restore/retest worksheet; integrated into main | Actual Windows/WSL installation, localhost and lifecycle checks; actual handoff review, human observations and observation-driven fixes/retests |

The completed researcher workflows are usable internal tools. Their original M3, M4 and M5 milestone sections retain the broader scientific goals and acceptance criteria. Further software work is declared as a new increment rather than relabeling these completed implementations as unfinished.

### Current GitHub main and verification

**Current private main, verified 28 October 2026:** the private remote remains at
`3787cc076d8a4850da5e91563c8fa8852a0a3393`, including the common-laboratory plan.
The installer and publication preparation are combined separately on
`codex/installer-publication-integration`; they have not been merged into remote
main. The [integration record](docs/research/installer-publication-integration.md)
binds its source inputs and checks. A fresh independent source root exported
from `0a030a7` also passed 1,560 tests with 32 existing skips, both complete
synthetic MMTT examples and 12 byte-identical reconstructed reports. These are
local source checks; no new Windows executable, hosted CI or public release is
established by them. On 28 October, source publication was authorized for the
independent `OpenT1D/lab` root, with a documentation-only status follow-up.
No private history is merged into that public root.

**Earlier software integration, 19 October; remote verified 22 October 2026:**
OT-057 is integrated into local and GitHub main at
`ac94080c70b855b4e67a86c677e654caf0395bde`. Its file tree matches the tested
implementation `7447831ee4995f4cdd4b0179253d2d71d60af02b` exactly. The seven
MMTT interface fixes passed internal macOS browser retests, four native report
reconstructions and the locked repository check: 1,393 tests with 13 existing
skips, plus lint/formatting and the strict documentation build. The
[OT-057 verification record](docs/research/ot057-uiux-verification.md) owns this
scope. The merge includes `[skip ci]` as requested; the 22 October GitHub check
found zero Actions runs for that merge SHA. This is local verification, not a
hosted pass. The later [MMTT beginner packet](docs/research/mmtt-beginner-packet-verification.md)
has its own local verification; Windows/human testing remains open.

**Earlier software integration, 17 October 2026:** OT-051 and OT-052 are
integrated into main with `[skip ci]` at the maintainer's request. OT-052 adds
a plain-language product introduction and two research questions with example
inputs and report contents. Its checked implementation is
`955d5ab25285c1164f7d4f0d28bc029ba08e7112`; locked repository checks passed
with 1,288 tests and 13 existing C1 skips, plus the warning-as-error
documentation build. Local browser checks covered both navigation paths and
the responsive start page. A new Windows test packet must bind the integrated
revision and be checked separately; actual Windows/WSL and human comprehension
checks remain open. Hosted CI is intentionally skipped for this integration.

**Earlier software integration, 14 October 2026:**
[PR #37](https://github.com/OpenT1D/OpenT1D/pull/37) merged OT-050 into GitHub
main at `7df6594bf4d54238027fbd8418f9de879c03b1de`; local main was
fast-forwarded to that same commit. The merged tree is identical to the PR head
`6398359cff5484906cbaad70675754ce75df11be`. Its only differences from checked
code candidate `83440ccb74e565114e403116ae1a95022577afa2` are roadmap,
documentation navigation and the verification record. The locked 1,282-test
checks and actual native/browser scope are bound by the
[OT-050 verification record](docs/research/gui-usability-fixes-verification.md).

The maintainer explicitly requested skipping hosted CI/CD for this integration.
The merge message includes `[skip ci]`; the configured automatic workflow uses
`push`/`pull_request`, and no push run was recorded for that merge SHA. The
workflow files were not changed. The prior
[PR check run](https://github.com/OpenT1D/OpenT1D/actions/runs/38467919481)
was blocked before repository job execution by the account payment/spending
restriction. Hosted verification remains unexecuted; local passes are not a
hosted pass. Subsequent integration-status documentation is also published with
the requested skip marker. Windows/WSL and independent human gates stay open.

**Earlier software integration, 13 October 2026:**
[PR #35](https://github.com/OpenT1D/OpenT1D/pull/35) merged the OT-045–049
technical preparation into GitHub main at
`e8eac8dfa665bd1d39979d5f79a156cde40620ad`. Local main was fast-forwarded to
the same commit and its working tree was clean. The merged file tree is
identical to checked candidate `2e37f38c2b5e6aaeaef6d021b1d49cf134861667`.
On that exact candidate, `uv sync --locked` and
`uv run --locked python scripts/check.py` passed: 1,280 tests in 231.533 seconds,
with 13 existing C1 runtime skips, plus lint/formatting, documentation metadata,
navigation and the warning-as-error documentation build. Subsequent roadmap-only
updates preserve that software implementation.

All 16 jobs in the [PR Actions run](https://github.com/OpenT1D/OpenT1D/actions/runs/38438184336)
were rejected before executing steps because GitHub reported an account payment
or spending-limit restriction. Integration used the passing local checks and
the recorded native/browser evidence; hosted verification remains open. When
the restriction is resolved, run the hosted checks on an identified main
candidate and retain the actual results. The prior hosted result below does
not cover this increment.

The local integration receipt and job annotations are retained under
`results/usability/20261013/main-integration/`. The standalone packet remains
frozen at its verified implementation `bd96d50cce473a3746fc1fc193f43dd556361c45`
under `results/usability/20261011/`; merging or updating status text does not
silently regenerate its source bundle. The
[session verification record](docs/research/gui-test-session-verification.md)
binds its separate evidence scope. Real Windows-host verification, handoff
review, participant sessions and human retests remain open. No public release
or broader scientific acceptance is established.

**Earlier integration, 6 October 2026; status reviewed 7 October 2026:**
[PR #33](https://github.com/OpenT1D/OpenT1D/pull/33) merged the preceding local
increments, including OT-041–044, the simplified GUI and its CI configuration
correction, into GitHub main at
`9414fc451bb2665d9565195936a416561a9db503`. The integration synchronized
local and GitHub main at that commit.
The merged file tree is identical to locally tested head
`5262dda0885ece20fc6b0c18baa6a77696ed8cd1`: `uv sync --locked` and
`uv run --locked python scripts/check.py` passed, with 1270 tests, 13 existing
C1 runtime skips and a warning-as-error documentation build. The local
integration receipt is `results/ui-user-study-20261006-main-integration.json`.
Repository integration is complete; repository visibility is unchanged and
no public release has occurred.

The [resulting main Actions run](https://github.com/OpenT1D/OpenT1D/actions/runs/37512644767)
was marked failed without executing any job step. GitHub reported an account
payment or spending-limit restriction; the maintainer confirmed exhausted
Actions capacity. Integration used the completed local checks as an exception
to the usual wait-for-hosted-checks procedure. Hosted verification of this main
candidate remains open until capacity is restored; no hosted pass is claimed.
The earlier successful hosted candidate below does not cover these later
increments. Independent usability, human M2 reproduction and M3–M5
empirical/biological acceptance retain their separate evidence requirements.

**Repository verification, 3 October 2026:** the integrated runtime-fix candidate `e4b631de436f1bec9acf49a9887a237a6bfeafbb` passed all 13 hosted CI jobs, including 878 repository tests, the documentation build and the native numerical campaigns. The [hosted execution record](experiments/integration/runtime_fix_hosted.json) and [runtime follow-up](docs/research/runtime-baseline-extension.md) bind the actual checks and preserved historical criteria. The fix was published to `main`; publication commit `5fd36595c989f4da338fed90a13df952d10286df` adds only evidence/documentation to that tested candidate and also passed 878 tests and the documentation build locally. Its [automatic main CI run](https://github.com/OpenT1D/OpenT1D/actions/runs/37128348205) was rejected before any job step executed because the GitHub Actions limit was reached. Hosted verification of that published main commit remains pending until the account restriction is resolved. Local internal development can continue; these software checks do not establish independent usability or scientific validity.

**OT-043 local verification, 5 October 2026:** OT-043 was fast-forwarded into local main at `4e5cf48464af3fc479acdd7fd636718f90112914`; `8b08fef6c2148ae0eccce7402e612c7c791009be` records the integration status. The primary main checkout passed `uv sync --locked`, all 1246 repository tests and the warning-as-error documentation build. The [OT-043 record](docs/research/archive-library-verification.md) owns that local scope. GitHub integration subsequently completed through PR #33, as recorded above; hosted verification remains open. The 3 October hosted result does not cover these later increments.

**OT-044 branch verification, 6 October 2026:** feature candidate
`fe1e1f8e21f3084ba197d965ca95739dad96707c` passes locked installation, the full
1264-test repository suite (13 existing C1 PyTorch-runtime skips) and the
warning-as-error documentation build. Four actual M5 cases, six retained M3/M4
regressions, original-byte browser downloads and the existing durable reader
pass separate checks. Two agents complete internal cross-review with resolved
integrity findings. This was the isolated implementation branch result.
The verified increment is now integrated into local and GitHub main through
PR #33; hosted verification remains open. See the
[OT-044 record](docs/research/m5-archive-library-verification.md).

**OT-044 main integration and cleanup, 6 October 2026:** local main was
fast-forwarded from `ca3bc66` to
`537680a7e630cf52c478ebd4e0275bfabb47184b` without conflict. Locked installation,
the full 1264-test suite (13 existing C1 runtime skips) and warning-as-error
documentation build pass from the primary checkout. The managed implementation
worktree is archived and its merged branch removed. Before cleanup, all 575
cached GUI evidence files were preserved outside the worktree, without its
manager lock or process authority. After cleanup, all four retained M5 native
archives still reconstruct from main without importing the candidate; their
report bytes, original receipt digests and all 345 protected scientific/lock
files agree. The main-integration record owns this separate execution scope.
The final documentation-only status commit receives its own documentation checks.

### Internal development and later evidence gates

OpenT1D is in an internal, pre-release development phase; a public release is not imminent. A bounded software increment may proceed with self-run checks appropriate to its risk: source and rights inspection where relevant, unit and numerical checks, failure behavior, reproducible execution and an honest evidence record. Use invented or otherwise permitted inputs. An external sign-off, independent user run or new patient dataset is **not** required before each internal change. Prefer a concrete researcher workflow or demonstrated defect over extra synthetic experiments that do not answer a new question.

Keep three separate decisions visible:

| Stage | What permits progress | What remains unclaimed |
| --- | --- | --- |
| Internal development | A scoped task, appropriate self-run verification and recorded limitations | Independent usability, human predictive accuracy, biological validity or treatment benefit |
| Empirical study with restricted observations | Verified data rights before access; a source-specific protocol, evaluation separation and domain input when the claim needs it | Permission or scientific validity inferred from synthetic tests |
| Public release, later | Comprehensive testing and review of the supported release candidate, including installation, workflows, numerical behavior, failure handling, provenance, documentation, rights and independent use; claim-specific evidence where applicable | Automatic promotion of internal checks into external validation |

Existing M2 independent reproduction and P1 intended-user acceptance remain open criteria, not gates for unrelated internal work. M3/M4/M5 may keep improving their tools while observation access and expert review are unresolved. Before making an empirical or biological claim, meet that claim's own evidence requirements; before processing restricted data, establish its rights. The future public-release review does not need to be repeated for every internal increment.

## First research task

**Determine whether conclusions about reference insulin-control strategies remain stable when meal information, sensor conditions and the physiological model change.**

M1 supplies the first complete workflow; M2 integrates a second physiological family. The completed IV-001 campaign characterizes numerical and scenario sensitivity. P1 has an internally verified external-controller workflow with PID and a distinct proportional source; a human reviewer has conditionally cleared one exact internal technical handoff, while independent usability remains open for product acceptance. M3–M5 now also support researcher-owned predictors, secretion sources and prognostic models on their separate synthetic tasks. Glucose-control tools and cure-oriented research tools remain parallel application areas, with their own empirical and biological evidence requirements. The historical C1 original-controller and proposed B1 model-improvement studies remain optional research, not platform dependencies.

The glucose-control comparison is the first research task supported by the laboratory. Its infrastructure should also support later questions about biological function and treatment. See the [first experiment proposal](docs/research/first-experiment.md).

## Tool-first acceptance direction

The bounded P1 workflow connects one declared external rate controller to a
supported M1 experiment without editing the physiological engine, runs
synthetic scenarios, and reconstructs inputs, actions, failures and outcomes
from saved artifacts. Its observation/action contract, clocks, units,
permitted history, missing-sensor behavior and source identity are recorded;
distribution rights require human review before a product claim.
Do not infer pump or pen interoperability from M1's current rate-action
callback; a pen/discrete-dose route requires its own declared contract and
verification. Independent intended-user execution remains the P1 acceptance
gate. Broader model and biological-module interchange follows only from
specific supported experiments, not from a generic API promise.

For scientific use, describe the question and the model's context of use;
separate software verification from reference reproduction, matched
simulation comparison, observation-based assessment and treatment evidence.
Keep synthetic fixtures clearly labeled and restricted real observations
under their researcher's authorization and control.

The [next two-task increment](#planned-mixed-meal-analysis-tasks) applies this
direction: one useful observation-analysis task establishes the shared core;
a second related task tests its reuse. [Decision 0066](docs/decisions/0066-observation-analysis-tasks.md)
selects a separate offline route without promising general model compatibility.

## Foundation — Repository and project agreements

**Outcome:** a coherent, reviewable place to build and collaborate.

The foundation includes the README, vision, contribution and governance documents, research standards, model and protocol templates, licensing, citation metadata, issue forms and local/CI documentation checks. The [maintainer guide](docs/maintenance.md) separately tracks the GitHub settings and contacts required before public onboarding.

**Acceptance:** the documents agree about scope and status, the local checks pass, the site builds from the canonical Markdown files, and any unconfigured external service is identified explicitly. Hosted CI and publication are verified when activated.

## M0 — Research contract, upstream quality and data fit

**User outcome:** a researcher can assess the first experiment and reproduce a candidate model's own reference before relying on OpenT1D.

**Evidence, 13 September 2026:** the [native reproduction record](docs/research/m0-reproduction.md), [model cards](docs/research/models/simglucose.md), [data-fit card](docs/research/m0-data-fit.md), [specified protocol](docs/research/first-experiment.md) and [accepted integration decision](docs/decisions/0002-m0-reference-first.md) support the completed items below. This completion concerns the documented native scenarios and research contract. It does not claim paper-figure agreement, independent researcher reproduction, verified human-data access, a distributable parameter collection or clinical validity.

- [x] Finalize the question, population, horizon, events, controller information, outcomes and failure policy.
- [x] Compare simglucose, LT1 and APS TestBed against that task: installation, scriptable execution, controls, outputs, reset behavior and reproducibility. APS assessment remains source-based; its full stack was not executed.
- [x] Record exact upstream revisions, physiology families, parameters and rights for code and assets separately. Unresolved independent parameter origins remain explicit; no upstream tables are vendored.
- [x] Reproduce at least one documented upstream scenario from a clean environment and preserve its inputs, outputs and manifest. Both native probes repeat locally and in Linux CI; this is not reproduction of a separate published figure.
- [x] Assess a genuinely different second family before treating the first engine's interface as general.
- [x] Assess relevant real-data sources now: required variables, actual availability, access terms and the questions they can test. Authorized access and native release verification remain pending.
- [x] Decide which existing capabilities to reuse, where an adapter is needed and what OpenT1D itself must build. The reviewed LT1/APS comparison supports the first Python adapter; a general cross-engine host is not yet selected.

**Acceptance:** a reference is reproducible; important upstream limitations are recorded; the first protocol and data-assessment plan are concrete; and the integration decision explains its added value. Successful installation alone is insufficient.

**Selected native references:** simglucose for the first reproduction; LT1 Cambridge/Hovorka for a different family. Both have now been executed; the model cards record exact revisions. GluCoEnv is a potential acceleration route within related physiology. Alternatives remain available if installation, model scope or rights make a candidate unsuitable.

**Dependency:** usable source code and assets for the chosen reference. Data access requests can proceed alongside the public synthetic workflow.

## M1 — One complete laboratory experiment

**User outcome:** a researcher can define, run and reconstruct the first comparison locally.

- [x] Specify the minimal model, scenario, observation, action, run-manifest and output contracts.
- [x] Build one engine adapter while preserving upstream physiological behavior.
- [x] Connect basal-bolus and PID references with explicit settings and information constraints.
- [x] Implement a reference meal scenario and separately controlled changes in announcement and sensor conditions.
- [x] Compute versioned glucose metrics, delivered insulin, variability, failures and runtime.
- [x] Save all configurations, inputs, outputs, warnings and analysis provenance.
- [x] Generate the report entirely from saved artifacts and publish a runnable tutorial with the implementation.

**Acceptance:** direct and adapted execution agree within justified tolerances; amounts and rates cannot be confused; event order is explicit; reset and random-state behavior are checked; incomplete runs remain visible; and a fresh environment reconstructs the report.

**Evidence limit:** this establishes software behavior and the described simulation experiment. It is not clinical validation or evidence of a superior treatment.

**Evidence:** the [tutorial](docs/m1-tutorial.md) and [acceptance mapping](docs/research/m1-reproduction.md) cover the 32-case development demonstration, including incomplete runs. M1 remains the original development demonstration. The separately frozen OT-014 evaluation is reported under M2; it does not retroactively change M1 artifacts or claims.

**Dependency:** M0's reference and protocol. Choose machine-readable schemas from this real task rather than designing a universal model language in advance.

## M2 — Demonstrated modularity across model families

**User outcome:** a researcher can replace the physiological engine or controller and understand which conclusions persist and which depend on model choice.

- [x] Reassess LT1/APS hosting against the implemented first adapter, then integrate a second physiological model family and document shared ancestry and assumptions.
- [x] Define supported combinations and reject unsupported ones with useful errors.
- [x] Keep each glucose/insulin engine intact where a finer split would be scientifically unjustified.
- [x] Establish comparable population and information conditions; use separate comparison tracks where necessary.
- [x] Add a suitable stronger published control reference before making broad performance claims.
- [x] Separate tuning from evaluation, and report uncertainty, rank reversals and failures per condition.
- [ ] Later external-review acceptance: have another person execute the protocol independently and record the outcome. This original M2 criterion remains open; it does not block internal development.

**Acceptance:** model replacement does not require rewriting the experiment's scientific intent; differences are interpretable; provenance is complete; and independent reproduction is demonstrated for full original milestone acceptance. Internal development can proceed before that later gate, as recorded in [decision 0005](docs/decisions/0005-internal-verification-and-external-review.md). Patient number 1 in one engine is not assumed to represent patient number 1 in another.

**Evidence:** [decision 0004](docs/decisions/0004-m2-native-process-tracks.md), the separately versioned [OT-014 protocol](docs/research/m2-protocol.md), [tutorial](docs/m2-tutorial.md) and [criterion-by-criterion record](docs/research/m2-reproduction.md). Cambridge supplies a deterministic structural track and native MPC published-method reference, not a held-out cohort or an optimized cross-engine comparator. Broad performance claims remain outside this evidence.

**Status:** implementation complete with independent human execution pending as a later external-review item. Another person must run the documented frozen checkout and record the outcome; CI cannot substitute for that acceptance point.

**Dependency:** M1. Assessment of the second model starts in M0; its completed integration is required here. If independent reproduction has not yet occurred, label the implementation complete and that acceptance item pending.

## Internal verification before external review

The [IV-001 protocol](docs/research/internal-verification-protocol.md) adds a bounded development campaign without changing OT-001/OT-014 or their historical results. Implementation, internal numerical verification, human-data evaluation and independent reproduction remain separate evidence dimensions.

- [x] Record the internal-development sequence and preserve the open human-reproduction criterion.
- [x] Characterize solver refinement and initialization sensitivity in separate native tracks. The [IV-001 record](docs/research/internal-verification-results.md) reports stable, sensitive and incomplete comparisons; the [tutorial](docs/internal-verification.md) reproduces them.
- [x] Demonstrate detection of selected consequential fault classes: seven controlled mutations are detected; the [evidence record](docs/research/internal-verification-results.md) states the limited scope and resolved test/provenance findings.
- [x] Execute a frozen robustness matrix and reconstruct its coverage, failures and sensitivity report: 170 development cases, 151 completed and 19 native stops, with exact full-matrix repetition and separate within-engine comparisons. See the [IV-001 evidence record](docs/research/internal-verification-results.md).

**Acceptance:** a reproducible report states which calculations and conclusions are stable, sensitive or inconclusive under the specified probes. No new virtual population, controller tuning or biological validation is implied. Independent reproduction follows later; M3 still requires suitable human data and rights.

## Development sequence after M2

The dated increments below retain their original scope and evidence. New shared
laboratory work follows the [current delivery plan](#common-laboratory-delivery-plan);
its package dependencies replace any older implied allocation order.

The laboratory supports two parallel application areas: glucose regulation and cure-oriented biology. Both reuse experiment provenance, numerical verification, data boundaries and reconstruction where suitable. Better control, improved physiology and treatment benefit are hypotheses to test, not current capabilities. [Decision 0045](docs/decisions/0045-tool-first-research-platform.md) puts the shared tools first and supersedes the original-method priorities of [decisions 0006](docs/decisions/0006-model-controller-development.md) and [0016](docs/decisions/0016-parallel-control-cure-research.md), while preserving their historical protocols and evidence requirements.

### Post-integration internal work packages

The 2 October 2026 planning review inspected the [combined execution record](docs/research/researcher-workflow-integration.md), the four canonical researcher guides and their command/validation/report implementations. It found outdated entry-page status, differing commands and runtime requirements, and separate single-candidate M3 reports. These are observed documentation and implementation differences; independent user experience has not yet been measured. [Decision 0055](docs/decisions/0055-task-entry-and-m3-comparison.md) records the selected boundaries. The [multi-agent execution plan](docs/research/ot029-ot030-execution-plan.md) assigns ownership, protocol choices, phased implementation and acceptance in a separate worktree. The [OT-029/030 verification record](docs/research/ot029-ot030-verification.md) binds the completed local entry, multiple-candidate comparison, 866 repository tests, native execution/reconstruction and retained failures. That dated record predates hosted CI; the [3 October hosted record](experiments/integration/runtime_fix_hosted.json) records all 13 passing jobs on the subsequent integrated candidate, with 878 repository tests. The later published main commit's hosted rerun remains blocked by the Actions limit as described above.

| Order / package | Current status | Researcher outcome and acceptance |
| --- | --- | --- |
| 1 — OT-028: task-first navigation and status | Documentation updated in this planning increment | The canonical [start page](docs/index.md) identifies controller, forecast, secretion and prognosis tasks, their required files, reports and evidence limits. README and roadmap distinguish completed software from open scientific acceptance; existing guides own execution commands. |
| 2 — OT-029: one local workflow entry | Implemented and internally verified, 2 October 2026 | From one checkout-based entry, a researcher can discover a supported task, check its configuration/runtime requirements, explicitly run it, reconstruct its archive and find its report. Existing runners, contracts and isolated locks remain authoritative. |
| 3 — OT-030: multiple frozen M3 candidates on one task | Protocol frozen; implemented and internally verified, 2 October 2026 | A researcher compares at least two frozen predictors and persistence on one synthetic roster and causal origin schedule, with coverage-aware common-support comparisons and an artifact-reconstructed report. |
| 4 — OT-031: multiple frozen M4 sources on one task | Protocol frozen; implemented with native execution and reconstruction internally verified locally, 3 October 2026 | A researcher compares frozen secretion sources under identical synthetic fasting and gastric-load conditions, with exact shared-control checks, full failure accounting and one reconstructible glucose/insulin/C-peptide report and figure. |

**OT-029 scope and verification:** support the existing P1 controller, M3 forecast, M4 secretion and M5 prognosis tasks through a small explicit registry. Distinguish metadata/runtime checking from an explicit model smoke run: P1's existing external preflight executes supplied code. A metadata check must neither import a candidate nor run a simulation. Report missing runtimes and configuration/hash/path problems before long execution, show the applicable locked setup command, and preserve route-specific timeouts, exit/failure behavior, fresh-output rules and report paths. Do not install runtimes or activate human-data routes implicitly. Keep original commands available and use each route's recorded source requirements when reconstructing historical archives.

Acceptance checks cover representative execution/reconstruction for all four supported tasks, a missing runtime, invalid configuration/hash, existing output, interruption/timeout and a retained incomplete archive. Reuse existing numerical evidence when execution behavior is unchanged; add a clean-runner configured M4 composition/reconstruction check where existing CI only covers its new numerical tests. Independent usability remains a separate evidence step. A package release, general plugin API and additional model states are outside this increment.

**OT-030 scope and verification:** first freeze a separate versioned comparison protocol, candidate roster/source/settings identities, common synthetic observation identity, planned people/origins, analysis rules and execution budgets before reading assessment observations. Retain M3's six exact causal five-minute CGM values, 30-minute horizon, persistence, eligibility rules and participant-level weighting. Fit or select preprocessing/settings only on development material; the comparison runner performs no tuning, refitting or automatic winner selection. Known synthetic fixtures and repeat runs remain known material.

Preserve every candidate, person, planned origin, exclusion and failed/partial attempt. Report each candidate's coverage and paired error against persistence, and compare candidates directly only on explicitly identical eligible people and origins. Freeze whether support is pairwise or an all-candidate intersection. Recompute primary eligibility on that common support itself: complete workers and at least 288 paired windows spanning 24 hours per contributing person, with the inherited participant weighting. Individual eligibility alone is insufficient; failed prefixes remain diagnostics. Keep full planned denominators and common-support attrition visible; never compare errors from different subsets as a model ranking or pool timestamps as independent people. An empty comparison has null metrics with its reason. Freeze the precise support rules before implementation; extend M4/M5 comparison only through their own task-specific protocols.

Build the coordinator outside the existing source-hashed M3 researcher package and give it its own provenance. Reuse unchanged single-candidate execution and retain historical reconstruction; adding files to that package changes the source inventory currently checked by its reader. Verification must cover two existing predictor structures, unequal/failed coverage, empty common support, mismatched inputs, fresh-process repetition and reconstruction without original observations or candidate execution. Saved arbitrary candidate outputs remain execution evidence; report reconstruction does not independently reproduce the supplied algorithm.

The [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) supports development-only fitting and fixed preprocessing; its [evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html) supports explicit participant/time separation and reserved assessment after model selection. The exact M3 support and archive rules come from OpenT1D's protocol and source audit, not those general references. No new dependency is selected by this planning review.

OT-028–030 completed in that order: navigation/status correction, local entry, then the separately frozen M3 comparison through that entry. Their dated local execution record and the subsequent hosted candidate record retain their separate source revisions and check scopes. The published main commit's hosted rerun remains pending; independent evidence remains open. These internal packages require no new human dataset or independent sign-off. The separate P1 intended-user exercise remains the next external product-acceptance step; M2 reproduction and M3–M5 empirical/biological steps retain their own requirements. No external executor, partner, date or data access is assigned here.

### Proposed internal follow-up — OT-031: multiple M4 secretion sources

**Status, 3 October 2026:** implemented software increment, with native execution and simulator-free report/figure reconstruction internally verified locally. The original proposal addressed separate Dalla Man and ultradian reports from the unchanged [single-source M4 workflow](docs/m4-researcher-workflow.md). The implemented [multiple-source comparison](docs/m4-source-comparison.md) now gives that researcher one declared synthetic task and combined report. [M4-COMPARISON/1](docs/research/m4-source-comparison-protocol.md) and [decision 0057](docs/decisions/0057-m4-source-comparison.md) were frozen before implementation and comparison execution. The [OT-031 verification record](docs/research/ot031-verification.md) identifies the actual checks and their limits; no hosted CI, independent use or biological assessment is claimed for this increment.

**Question:** how do the chosen causal secretion responses differ in modeled glucose, insulin and C-peptide under identical fixed conditions?

**Implemented scope:** one frozen configuration declares the source roster, source/declaration/parameter identities, common verified BC-008 reference, execution order and worker budgets. The coordinator reuses the existing single-source workflow and its fasting and 30 g gastric-load scenarios, one-state callback, units, basal/portal ownership, initial conditions, fixed SC schedule, complete 961-point observation grid and separate numerical locks. It lives outside the source inventories required by historical readers and records its own provenance. Direct pairwise signed AUC, signed time-mean and maximum absolute pointwise contrasts require both entire source workflows to pass and shared controls to agree exactly. Failed sources stay in the roster, and unsupported contrasts are null with explicit reasons.

**Acceptance criteria for this bounded software increment:**

- Check configuration and common reference identities before dispatch; reject incompatible scenario, initial-state, time-grid, unit or runtime settings rather than silently adapting them.
- Produce one readable report and figure containing every frozen source, its glucose/insulin/C-peptide trajectories, source versions and numerical checks. Compute descriptive contrasts only for complete, accepted cases on identical conditions and sample times; unsupported comparisons have null results with a reason.
- Preserve the full planned source/scenario roster, failed, interrupted and unattempted runs. A failed source stays in the report; its partial output cannot become an accepted comparison by shortening the interval or dropping it from the roster.
- Verify the existing Dalla Man and ultradian sources, reference/control agreement, rejected or failed source handling, exact fresh-process repeats and report/figure reconstruction without simulator or supplied-source execution. Retain unchanged single-source commands and historical reconstruction.
- Expose the separately versioned task through the common local entry after its native route and reconstruction pass their checks.

This increment uses no human observations or new secretion physiology. It introduces no source tuning, automatic winner selection, biological model ranking, treatment-effect claim or public release. Independent usability and M4's empirical/biological criteria remain open; the P1 intended-user exercise remains the next external product step. Broader M5 dependency environments and local report browsing remain unselected alternatives that need their own concrete task and bounded proposal.

### Functional development after OT-031

The selected internal implementation goal of 3 October 2026 adds study
configuration, local campaigns, archive discovery and explicit locked setup.
[Decision 0058](docs/decisions/0058-configurable-study-and-local-research-tools.md)
and the [isolated execution plan](docs/research/ot032-ot037-execution-plan.md)
freeze scope, worktree grouping and acceptance. The
[execution record](docs/research/ot032-ot037-verification.md) binds the completed
internal verification. Historical protocols and scientific evidence keep their
meanings.

| Package | Scope and status | Acceptance and dependencies |
| --- | --- | --- |
| OT-032 — Configurable M4 initial-load study | Implemented and internally verified under [M4-STUDY/2](docs/research/m4-configurable-study-protocol.md) | 0/15/30 gram matrix, accepted scenario-specific controls, historical numerical parity, refinement, repeats, failed-source/deadline checks and reconstruction. No timing events or source tuning. |
| OT-033 — Small local campaigns | Implemented and internally verified | Frozen two-cell/two-repeat native campaign, full denominators, retained interrupted attempt, identity-checked resume/reuse and tamper refusal. Initially m4-study only. |
| OT-034 — Local experiment catalogue | Implemented; internally verified with OT-037 | Seven registered readers, actual archive indexing/reconstruction, metadata filters and conservative same-experiment repeat eligibility. Missing legacy runtime conditions remain explicit. |
| OT-035 — GUI pilot | Implemented and locally internally verified, 4 October 2026; independent usability open | A local browser route for one maintained M4 initial-load study; explicit configuration/check/setup/run/cancel/report/reconstruction, native CLI parity and honest failed-study accounting. |
| OT-036 — Additional model type or coupling | Conditional, outside this goal | Concrete question, suitable attributed source/rights, versioned units/clocks/ownership and native verification. |
| OT-037 — Task-directed locked setup | Implemented and internally verified | Missing-environment detection, explicit locked installation and full readiness checks in a fresh managed checkout; reconstruction needs root only. macOS verified locally; other clean systems remain unverified. |

The maintained M4 successor and coherent C1 runtime migration preserve historical
protocols, locks and results under their original identities. The
[OT-035 execution record](docs/research/ot035-maintenance-verification.md)
owns dependency, native, browser/process and reconstruction evidence. The
[independent GUI exercise](docs/gui-researcher-exercise.md) is prepared and
unexecuted; it remains a later external usability step.

These increments introduce no human observations or secretion mechanism.
Own-observation fitting remains a conditional OT-026 follow-up based on existing
synthetic inverse analyses; selected intervention/function dynamics remain under
OT-027. Suitable authorized data, mechanism selection and domain review are
separate dependencies. The independent P1 user exercise remains parallel and
open. Main was preserved during the separate-worktree implementation goal.

[OT-035 with maintained runtimes](docs/research/ot035-maintenance-execution-plan.md) was selected
under [decision 0059](docs/decisions/0059-maintained-runtimes-and-local-gui.md).
Separate branches maintained root HTTP tooling, native HTTP execution and C1
PyTorch intake while preserving historical evidence and explicit reader
compatibility. The local GUI exposes one declared M4 study; it does not advance
biological or independent-user evidence. The dated execution record identifies
the completed implementation and its locally verified scope.

### Completed internal increment — local experiment workspace

**Status, 4 October 2026:** Goals 1 and 2 are implemented and internally
verified locally under
[decision 0060](docs/decisions/0060-maintained-campaigns-and-experiment-workspace.md).
The [execution record](docs/research/experiment-workspace-verification.md) binds
their separate native, process and browser outcomes. OT-038–040 extend
OT-033–035 while preserving their historical evidence.

| Goal / package | Scope | Acceptance and dependency |
| --- | --- | --- |
| Goal 1 — OT-038: maintained campaigns | Separate versioned campaign CLI for `m4-study-secure`; frozen small matrices, retained attempts and explicit resume | Internally verified: two configurations with two repeats, interrupted-attempt retention, accepted reuse, failure/tamper refusal and model-free reconstruction |
| Goal 1 — OT-039: GUI archive library | Explicit read-only archive roots; metadata for eight tasks, maintained M4 verification/report/figure | Internally verified: original external archives unchanged, success/failure and snapshot freshness visible, bounded owned indexing/reconstruction and browser downloads |
| Goal 2 — OT-040: GUI campaign management | Configuration, check, explicit setup, execution, cancel, resume, report and reconstruction | Internally verified after Goal 1: shared CLI semantics, full attempt/planned-slot accounting, native parity, nested cleanup, browser operation and existing study regression checks |

The integration owner controls shared GUI transport/service contracts, the ADR,
roadmap and canonical documentation. Separate agents own the campaign CLI and
library/frontend; a third agent reviews each frozen integration candidate.
Goal 2 branches started from accepted Goal 1. Local locked repository checks,
meaningful native/process checks and actual browser verification establish
internal software evidence; hosted verification remains open while Actions
minutes are exhausted. Independent human GUI use can proceed separately using
its prepared exercise. No human observations, treatment claim, model extension,
M3 GUI or publication to main is included in this implementation goal.

### Completed internal increment — OT-041: durable experiment archives

**Status, 4 October 2026:** implemented and internally verified locally under
[decision 0061](docs/decisions/0061-durable-experiment-archives.md).
The [acceptance record](docs/research/durable-archive-verification.md) binds
native candidate `887cb329b362067055b3d296d2f7a589e5c0a8aa` and final GUI
candidate `d9ad693846411c8724d5b42a453202c75cb28125` separately, with retained raw
packages and their compatible reader checkouts. The concrete consumer can retain
a maintained M4 study or campaign after its implementation worktree disappears.
The [OT-038–040 main integration](docs/research/experiment-workspace-verification.md#main-integration)
still records unavailable earlier ignored raw artifacts; this increment does
not recover them.

**Scope:** a separately versioned directory package for `m4-study-secure` and
`maintained-campaign`: complete original files and directories, all unsuccessful
attempts and sessions, compatible trusted-reader Git/source identities,
fixed-reader export evidence, bounded integrity verification and fresh restore.
Preserve native bytes and historical path fields. Add explicit GUI export to
an independently retained startup storage root and read-only package registration;
keep package integrity, authoritative reconstruction and numerical completeness
separate. Reuse fixed native readers without changing scientific protocols or
locks. Restoring a package does not resume execution or adopt recorded PIDs.

**Acceptance evidence:** a fresh synthetic maintained campaign produced one
accepted study with two supplied-source cases, then retained a SIGTERM-interrupted
second attempt. Its planned denominator remains two study slots; one is accepted.
The native study and partial campaign were exported/restored in independently
retained storage and reconstructed with a second clean compatible checkout after
the original execution worktree, archive and numerical environments were removed.
Native bytes, report bytes and failed/interrupted accounting remain unchanged.
Bounded CLI/GUI checks cover unsafe, tampered, incompatible, overlapping and
existing destinations; actual browser checks cover export, registration,
reconstruction and native report downloads. The record identifies the locked
local repository checks and retained raw evidence. Agent checks remain internal
evidence; exhausted Actions minutes leave hosted verification open.

**Execution ownership:** the integration agent owns roadmap/decision/guide,
contract and acceptance evidence. Separate implementation agents delivered the
archive CLI and GUI adapter in separate branches/worktrees; a separate agent
reviewed the combined candidate and its retained evidence. The user subsequently
requested [main publication](docs/research/durable-archive-verification.md#main-integration),
completed with separately passing local checks and retained evidence.
The implementation preserves 112 native scientific
source files byte-for-byte against main `6e339cc1d01109c27787e45f11e9ddca72793041`;
protocols, numerical behavior and locks retain their historical identities.

### Delivered increment: OT-042 — Synthetic M3 in the local GUI

**Status:** implemented and internally verified locally on 4 October 2026.
Separate GUI/backend/archive branches and worktrees were independently reviewed;
[the acceptance record](docs/research/m3-gui-verification.md) binds actual
CLI/browser/relocation, interrupted retention and the full locked local check.
Integrated into local main following the user's request on 4 October 2026;
the locked main check passed. GitHub integration subsequently completed through
PR #33; hosted checks remain open under the account restriction recorded above.

**Scope:** expose the existing `m3-forecast` and `m3-compare` synthetic workflows
in the local interface, using fixed CLI commands and one owned active operation.
Choose existing frozen predictors, explicitly prepare exact synthetic input
bytes, check readiness, run, follow observed progress and cancel. Preserve the
30-minute causal information contract, all planned people/origins, failures,
unattempted cases, native errors/coverage and common-support comparisons.
Separate execution, authoritative reconstruction and cohort completeness.
Download original JSON/Markdown and explicitly reconstruct without predictors.
Add the two fixed M3 durable readers while keeping M4 packages compatible.
Unsealed interrupted evidence receives separate bounded raw retention in the
explicit external store, without a verified-package or reconstruction claim.
[Decision 0062](docs/decisions/0062-synthetic-m3-gui.md) fixes the architecture;
[the M3 GUI guide](docs/gui-m3.md) owns the workflow.

**Acceptance:** actual CLI/GUI parity for two frozen predictors; native complete,
failed and cancelled accounting; browser selection, operation, cancellation,
reports and downloads; byte-identical JSON/Markdown after fresh restore and
reconstruction with a second compatible clean checkout; unsafe/tampered inputs,
incompatible readers and overlapping destinations refused; bounded process
cleanup and M4 regression. Preserve raw evidence outside disposable worktrees,
unchanged scientific sources/protocols/models/locks and run the full locked
repository check. Synthetic preparation is explicit byte access; a native
metadata check alone does not verify observation contents or execute a model.
No fitting, human observations or changed numerical criteria are introduced.

**Ownership:** integration owns roadmap/contract/decision/guides and acceptance;
separate agents own GUI presentation, the owned M3 adapter and fixed durable
readers. A separate agent reviews the combined candidate and evidence. No
independent researcher or human-data result follows from agent verification.
Hosted checks remain separate while Actions minutes are exhausted; independent
GUI/P1 researcher exercises remain external acceptance work.

### Implemented increment: OT-043 — Reliable M3/M4 archive browsing

**Status:** implemented and internally verified on 5 October 2026, in separate
catalogue, library-adapter, presentation and integration worktrees/branches.
The [OT-043 record](docs/research/archive-library-verification.md) binds actual
retained CLI/browser cases, byte-exact downloads, source preservation,
independent code review and 1246 passing repository tests. At the user's
request, local main was fast-forwarded to the verified candidate on 5 October
2026. GitHub integration subsequently completed through PR #33; hosted checks
remain open under the account restriction recorded above.

**Scope:** correct recorded file-hash claims using the supported manifest
schema's path base, including the maintained M4 reference seal rooted at
`reference/`. Keep genuine missing/changed files detectable and distinguish
unsupported schemas and invalid claims from checked matches. Never guess a
schema's path base or rewrite an original archive. Add fixed native report-only
verification for `m3-forecast` and `m3-compare` in the general GUI archive library,
with original JSON/Markdown downloads, full participant/origin/failure accounting
and common-support results. Preserve the existing M4 report/figure route, shared
operation ownership, read-only roots and snapshot freshness. Keep indexing,
recorded digest agreement, reconstruction and cohort completeness separate.
[Decision 0063](docs/decisions/0063-reliable-archive-library.md) fixes these
boundaries; [the archive-library guide](docs/gui-archive-library.md) stays canonical.

**Acceptance:** reproduce and resolve the 34 known catalogue warnings on the
retained M4 archive without changing its files; retain true tamper, missing-file,
unsafe-path and unknown-schema diagnostics. Actual CLI/GUI/browser verification
must cover existing full and failed/partial M3 forecast/comparison archives,
byte-identical native downloads, originals unchanged, unavailable original inputs,
unsealed refusal, changed snapshots, cancellation and existing M4/durable routes.
Use a separate combined review, preserve raw evidence outside worktrees and run
`uv sync --locked` plus `uv run --locked python scripts/check.py`. No predictor
execution, fitting, human data, changed native scientific conventions or locks,
independent-human usability claim or hosted run is included.

### Delivered increment — OT-044: native M5 archive reports, 6 October 2026

OT-041 through OT-044 are delivered within their bounded internal scopes.
The M5 library reader and report view now pass local native/HTTP/browser and
repository checks. Remaining human and hosted evidence is separate from this
completed implementation.

| Priority / work item | Next artifact | Status and remaining gate |
| --- | --- | --- |
| Internal software — OT-044 | Native M5 prognostic reports in the general GUI archive library | Implemented and internally verified locally under decision 0064 and the OT-044 acceptance record |
| Independent user evidence | Actual [GUI researcher exercise](docs/gui-researcher-exercise.md) and the separately scoped [P1 exercise](docs/p1-acceptance-exercise.md), with observed problems and interpretation | Prepared tasks; no independent participant/result recorded. A named researcher and the actual handoff's rights scope remain to be established |
| GitHub main and hosted verification | Restore Actions capacity and retain exact-candidate hosted results when execution becomes available | Integrated through PR #33 at `9414fc4`, with a tree identical to locally tested `5262dda`; main CI executed no job steps because of the account restriction. Hosted verification remains open |

**OT-044 scope:** let a researcher register an existing synthetic
`m5-prognosis` archive, explicitly verify its native analysis, inspect the complete
32-person development/evaluation roster and download original JSON/Markdown.
Show eligibility, both prediction attempts, failures/unattempted cases and
paired coverage. Keep the full evaluation baseline separate from the same-person
paired baseline; empty support retains native null metrics with explicit UI
context for absent paired support. Preserve
model/state identities, self-attested training/rights statements and `U/day`
units. Use the unchanged [M5 researcher contract](docs/m5-researcher-workflow.md).

**Reader boundary:** the current M5 `reconstruct` command verifies existing
report bytes in place and returns the native report; it has no fresh-output
argument. [Decision 0064](docs/decisions/0064-native-m5-archive-library.md) freezes
the implemented fixed owned adapter for that exact behavior. Copy only verified
native report bytes into fresh GUI-owned output, check source
inventories around the operation and preserve original archives. Reuse the one
active owner, cancellation/deadlines, safe roots, snapshot withdrawal and
recorded-verification rules. The native CLI, scientific sources and locks stay
unchanged. The native M5 reader and GUI adapter are implemented; new
durable-package support is outside this increment.

**Acceptance:** actual native CLI/browser parity and byte-identical
JSON/Markdown for complete, failed and interrupted sealed M5 cases; complete
planned-roster and paired-subset accounting; no candidate import/execution,
candidate refitting or reopening original external input paths during report
verification; true tamper, unsafe paths, unsealed refusal and changed-snapshot
withdrawal; bounded owner
cleanup, restart semantics and existing M3/M4/durable regressions. Retain raw
proof outside disposable worktrees and run the locked repository checks.

The maintainer/integration role owns the local main integration and retained evidence.
Two implementation agents cross-reviewed the combined increment; no independent
researcher exercise is claimed. M5 GUI execution, example export/fitting,
additional runtimes, human-data intake and therapy claims remain outside this
report-only increment. Existing M3/M4/M5 empirical and biological work keeps its
own observation/right/review gates; independent M2/P1 execution does not block
internal software preparation.

### OT-044 execution plan — 6 October 2026

**Status:** implemented, internally verified and integrated into local main on
6 October 2026. Implementation used `codex/ot044-m5-archive-library` from
`ca3bc66`; the worktree is now archived and the merged branch removed. This
retained plan records the method used. The maintainer owns integration;
two agents reviewed the plan and the combined implementation separately.
Their review is internal technical evidence, not independent researcher use.

**Researcher outcome:** register an existing synthetic `m5-prognosis` archive,
explicitly verify its native analysis, inspect its complete roster and attempts,
and download the original JSON/Markdown report bytes. Keep native execution
accounting, paired comparison completeness, verification and freshness distinct.
The existing eight-task metadata registry already includes M5.

#### 1. Freeze the adapter decision before implementation

Write a short decision record for the fixed M5 reader and GUI-owned snapshot.
The existing native command is
`python -B -E -s -S -m experiments.m5.researcher_workflow.run reconstruct ARCHIVE`;
it checks the archive in place and accepts no fresh-output argument. Reuse the
catalogue's fixed argv, environment, supervised deadline and completeness result.
Select the current authoritative reader only; archived Python is retained evidence
and must never be executed. Preserve the native CLI, source files, protocol,
scientific calculations and locks. M5 GUI execution, model export/fitting, human
input and additional durable-package support stay outside this increment.

Freeze the existing native presentation contract: schema
`m5-researcher-workflow/1`, invented-only claim, false human/treatment flags,
32 planned people split 24 development / 8 evaluation, 20 / 7 eligible people,
and two attempt positions for each eligible evaluation participant. Native
`comparison_status` and `candidate_execution_complete` are separate fields;
all attempted predictions can fail even when execution accounting is complete.
The existing catalogue completeness rule requires a complete comparison and
complete execution. Preserve null paired metrics when no participants pair.

#### 2. Implement the fixed library adapter

Extend the explicit task/artifact whitelist and GUI contract with
`m5-prognosis` and exactly `report.json` / `report.md`. Reuse
`experiments/catalogue/core.py:verify_one` for in-place verification. After
success, create a fresh GUI-owned `reconstructed` child and copy only the two
original reports. Compare source inventories before verification, after native
verification and after copying. Bind copied artifact digests to the original
frozen inventory as well as to the receipt, preventing a transient source change
from publishing substituted bytes even if the source is subsequently restored.
Validate copied native schema/accounting before publishing the snapshot.

Retain existing safe-root/opaque-pointer rules, regular-file and no-symlink
checks, the exact native file inventory and 500,000-byte per-file limit, one
active operation, deadlines and process-group cleanup.
Missing M5 reports, extra files, unsealed archives and incompatible saved
source/lock identities must fail native verification; the M3 missing-report
fallback does not apply. Passive metadata visibility never enables downloads.
No candidate import/execution, refitting, simulation or reads from original
external input locations occur during verification.

#### 3. Bind the report API and declared provenance

Return the native report in an explicit M5 envelope with task/schema, artifact
hash, verification scope, recorded completeness and source-freshness state.
Preserve `not_rechecked_since_worker`; HTTP requests must not perform a hidden
archive inventory scan. Reuse existing report/download hash checks, snapshot
withdrawal and restart downgrade to `recorded_verification`.

The native report retains source/state hashes and a self-attestation label but
omits the actual rights and training declaration. Freeze a bounded projection
from the worker-verified catalogue model declaration into the owned receipt and
API envelope. Bind model ID, source/state hashes, output unit, runtime, rights
basis and training declaration to the same verified inventory/report. Display
these as supplier declarations, not independently established rights or training.
Never reread source declarations in the HTTP handler or add a `model.json`
download. Withdrawing the report also withdraws the projected declaration.

#### 4. Add explicit M5 presentation

Replace the current non-M4-means-M3 dispatch with explicit M3/M4/M5 task
selection in `experiments/gui/static/app.js`. Add a dedicated bounded M5
validator/renderer and accessible section in `index.html`; reuse existing
selection/request-generation guards and shared controls.

Show all 32 roster rows, development/evaluation membership, eligibility,
exclusion reasons and later infusions. Show eligible evaluation predictions and
both attempt positions with saved prediction/runtime identities, including
failures, interrupted, missing-repeat,
not-reproducible and unattempted outcomes. Development or excluded participants
must not appear to have unattempted evaluation predictions. Display the full
eligible baseline separately from baseline/candidate errors on the paired subset,
with native counts, coverage, signed difference and `U/day` labels. Preserve
native values without computing new scientific metrics. For zero pairs, explain
the unavailable paired metrics using native zero-support context; do not invent
a stored native reason field or substitute zero. Synthetic scope and declared
provenance remain visible. Provide original JSON/Markdown downloads.

Preserve open details and keyboard focus when the same snapshot is rechecked;
a change or artifact failure affecting the current snapshot withdraws its report
and download controls. Ignore late success/error responses for obsolete selections
or request generations, preserving any current valid snapshot. Existing M3/M4
renderers and the M4 figure remain supported.

#### 5. Verify the behavior with retained synthetic cases

| Case | Required evidence |
| --- | --- |
| Complete M5 archive | Native CLI, worker, HTTP and actual browser agree on all native fields; both downloads are byte-identical to originals; all 32 people remain visible |
| Mixed failures / nondeterminism | Native verification can succeed for an incomplete comparison; both attempt positions and excluded/unattempted distinctions remain visible; paired subset and full baseline stay separate |
| Zero successful pairs | Native null paired metrics and zero coverage remain; completed execution never becomes a successful comparison |
| Sealed interrupted archive | Active interruption and remaining unattempted records survive verification and relocation |
| Missing reports / unsealed / tampered / unsafe archive | Explicit refusal; no M3-style synthesis, candidate execution or verified download claim |
| Change during verification or copy | Source/receipt/hash mismatch withdraws output, including a transient mutation restored before the final inventory |
| Snapshot, selection and lifecycle changes | Obsolete responses leave the current valid snapshot intact; current snapshot failures withdraw its controls; cancellation/deadline, restart, shared ownership and details/focus retention pass |
| Existing routes | M3 forecast/comparison, M4 report/figure, campaigns and existing durable workflows retain their behavior |

Use the real native M5 runner to prepare permitted complete, failure,
zero-support and sealed interrupted fixtures outside the feature's GUI path.
Retain original archives and inventories; move or remove original supplied
bundle paths before verification. Use explicit guards/markers to demonstrate
that verification never imports the candidate, refits or opens those paths.
Combine focused backend/native/HTTP tests with the existing controlled Node
frontend harness and actual browser checks. Record skipped or unavailable checks
honestly; a sandbox denial of loopback sockets or process inspection is not a
successful test and requires verification in a suitable execution environment.

#### 6. Review, document and finish the branch

Agent A reviews reader/source integrity, declaration binding and API behavior;
Agent B reviews roster/metric presentation, asynchronous ownership and test
coverage. Both inspect the final combined diff independently and report concrete
findings. The maintainer resolves findings and reruns affected checks, then runs
`uv sync --locked` and `uv run --locked python scripts/check.py` on the integrated
branch, with Node available for frontend checks. Agent review cannot replace the
native/HTTP/browser acceptance cases.

Update the canonical `docs/gui-archive-library.md`, GUI contract, changelog and
roadmap status after the behavior exists. Add a separate OT-044 verification
record with exact revision, commands, artifact identities, outcomes and limits;
list new public decision/evidence documents explicitly in `docs/_toc.yml`.
Retain raw receipts, logs and browser downloads outside disposable worktrees in
the ignored primary-checkout `results/ot044-verification/` store; keep identifying
or restricted observations out. Worktree deletion must not remove the evidence.

**Completion condition:** the fixed native M5 reader and GUI agree for accepted
and diagnostic archives, original bytes remain unchanged, preserved reports are
reconstructible with the identified reader, focused and full checks pass in a
suitable environment, review findings are resolved and documentation describes
only that verified scope. Leave the reviewed implementation on the isolated
branch for integration. Publication, hosted verification, independent usability
and empirical/treatment evaluation retain their separate evidence steps.

### Next work after OT-044

This section records the October GUI follow-up. The subsequently selected
product work is [OT-053–056](#planned-mixed-meal-analysis-tasks); the independent
usability and Windows checks below retain their own acceptance scope.

OT-044 is complete in local and GitHub main within its report-only synthetic scope.
Prioritize the prepared independent GUI/P1 researcher exercises when an actual
participant and permitted handoff are available, retain observed installation,
interpretation and usability issues, and scope fixes from those observations.
GitHub integration is recorded above; hosted verification remains open because
Actions capacity is exhausted. Independent usability still needs actual
participant observations; the prepared packet contains no participant results.
Further internal software work may proceed from a concrete researcher task or
reproduced defect; these external exercises do not block it. The 6 October
integration assigned no new software package or empirical study. The subsequent
[usability plan](#planned-usability-work) selects OT-045–049 to make the first
human session easier to prepare, run and record. M3/M4/M5 observation rights,
domain review and scientific evaluation retain their separate requirements.

**Local GUI usability follow-up, 6 October 2026:** at the maintainer's request,
the interface now opens with only two experiment choices, Results and a small
More menu. There is no dashboard/sidebar. Optional files, settings and recent
operations are disclosed on request; check/run actions follow the existing
native readiness gates. Missing M4 environments expose explicit installation.
Browser history, in-session draft/report state, invalid-field access and a
cross-view active operation remain available. Campaigns reuse the existing
secretion-study form; M5 remains report-only. This presentation/navigation
change preserves the existing workflow contracts and the separate independent
GUI/P1 acceptance and scientific evidence requirements. The earlier dashboard
iteration's local verification is retained in `results/ui-ux-workspace/`;
the simplified interface passes its own locked repository check (1265 tests,
13 existing C1 runtime skips) and warning-as-error documentation build. Final
frontend checks cover nine navigation/disclosure cases and 31 M3 cases. Actual
browser checks cover hidden-field validation, explicit missing-environment
installation, example preparation/readiness and the 390-pixel layout.

**GUI follow-up after UX review, 6 October 2026:** the maintainer authorized a
bounded follow-up to the read-only UI/UX review. Results now provides shortcuts
to own M4 runs, M3 workflows, campaigns and registered durable packages through
their existing routes, alongside the read-only added archive library. Selected
models, fixed profile/time context and synthetic scope are visible before a
run. Saved-analysis actions use **Check saved analysis**; execution, numerical
acceptance, comparison coverage and reconstruction retain separate meanings and
full failure accounting. These presentation changes grant no additional reader,
execution or resume rights. Added-archive metadata outcomes are not interpreted
as process completion when a separate execution status is unavailable.

**Local internal verification passes for this follow-up:** `uv sync --locked`
and `uv run --locked python scripts/check.py` completed successfully. The suite
ran 1270 tests in 260.628 seconds with 13 existing C1 runtime skips; the
warning-as-error Sphinx build and 11 focused frontend Python tests pass. Nine
controlled graph checks and the retained native
`results/ot044-verification/cli-regression-native-study/report.json` verify the
graph helper against the maintained M4 report's saved values. The ignored local
record is `results/ui-ux-followup/verification.json`; the earlier 1265-test
record above belongs to the preceding interface candidate.

Actual desktop (1280 pixels) and narrow (320 CSS pixels) browser checks cover
the two start choices, visible M4 context, missing-native-environment setup,
hidden invalid-field recovery, M3 selection focus and the saved-study repeat
selector. A synthetic standard-library M3 comparison completed, sealed and
verified its native saved analysis with 2/2 contributing participants; Results
opened that own experiment. Result focus and opened participant details survived
more than six seconds of polling. The checked Start, M4 options, Results, M3 and
campaign views had no page overflow at 320 pixels, and the browser console
recorded no errors. In that initial verification, fresh native M4 execution and
a live M4 graph-table check were not repeated because the native runtime and a
usable original maintained archive were unavailable. Its graph check uses
retained JSON. The subsequent technical preflight below resolved this M4 check
gap with actual native execution and live table verification. Sources, models,
scientific protocols and locks are unchanged.

The [independent GUI researcher exercise](docs/gui-researcher-exercise.md) now
proposes a first formative round with four to six independent researchers across
domain and computational roles. Freeze actual candidate/source/report identities
and task criteria before sessions; assess finding own Results, interpreting
incomplete evidence, error recovery, keyboard use and an identified narrow
viewport. Resolve observed blocking or misinterpretation issues and repeat
affected tasks before recommending scoped usability acceptance. No recruitment,
participant availability, sessions or independent results are recorded. This
plan does not authorize publication, human-data execution or scientific claims.

### Planned usability work

**Planning decision, 10 October 2026:** select five bounded work packages to
make the prepared GUI exercise practical for a first tester. A potential first
tester was identified by the maintainer; at that decision, their platform,
domain/software experience and session date were unrecorded. Their platform was
subsequently identified below; experience and session date remain unrecorded.
No human session or participant result is claimed. Package owners are not yet
assigned.

**Technical implementation, 11 October 2026:** the first tester will use their
own Windows computer. The separate `codex/gui-usability` branch implements
version-bound preparation and a local observation worksheet under
[decision 0065](docs/decisions/0065-observed-gui-test-packets.md).
This technical preparation was integrated into local and GitHub main through
[PR #35](https://github.com/OpenT1D/OpenT1D/pull/35) on 13 October 2026.
The [session entry guide](docs/gui-test-session.md) owns packet preparation,
explicit setup/start and recovery. Native Windows Python is not a supported
execution route: the existing workers require Unix locking/signals. Windows
launch files therefore prepare an explicit Ubuntu/WSL 2 route; actual Windows
installation, localhost access and lifecycle verification remain open until
checked on that host. Internal implementation evidence is recorded separately
from OT-048 participant observations and OT-049 human retests.

**Existing facilities:** the local GUI already runs the maintained synthetic M4
study with two supplied models and 0/15/30 gram initial loads. It supports
configuration checks, explicit runtime installation, execution, cancellation,
result discovery and saved-analysis verification. The locally retained
`results/ui-user-study-20261006/` packet contains English participant/moderator
cards, a frozen source bundle, complete and genuinely interrupted reference
archives, an observation CSV and six blank session records. These are prepared
materials, not an automatically configured or independently executed test.
The [GUI exercise](docs/gui-researcher-exercise.md) owns the task and observation
criteria; the [GUI guide](docs/local-gui.md) owns operation instructions.

| Package | Planned work | Completion criterion |
| --- | --- | --- |
| OT-045 — One complete test packet | Reuse the existing cards, source bundle and native complete/interrupted reports. Identify the selected checkout, sources, compatible readers, platform and setup state; provide one entry page, participant goals and moderator instructions. Keep canonical public instructions in English; prepare a private Dutch session card for the first tester from those same goals. | The identified packet opens with an understandable task and references to the canonical guide. Both reference archives are accessible through the existing read-only library and reconstruct with their selected trusted reader, preserving original bytes. Verify the actual handoff's rights and identities before transfer; record any deviation from the prepared candidate. |
| OT-046 — Easier installation and startup | Record the first tester's operating system and select a supported platform. Provide a short prerequisite/bootstrap procedure and a start file that opens the local interface and explains missing requirements. Reuse existing locked setup and the GUI's explicit installation actions. | On a clean identified system, the documented first-install steps and subsequent start file work without composing commands. Missing prerequisites and setup failures have actionable messages. Installation is explicit and separate from model execution; existing server ownership and cancellation behavior are preserved. Record the tested platform rather than implying Windows or general cross-platform support. |
| OT-047 — Simple observation form | Reuse the existing task fields and outcome categories in one human-readable form per session, initially a separate fillable sheet. Record assistance, participant explanations, observed issues and relevant platform/software/archive identities without editing JSON manually. | A moderator can record and retain a complete session using completed without help, completed with help, blocked and not assessed. Unobserved fields remain empty; records are local/private and outside scientific archives and version control. An in-app feedback system is not required for this first increment. |
| OT-048 — First human usability session | Run the standard M4 task with the identified tester: context, readiness/run, navigation, finding Results, complete/incomplete report interpretation, saved-analysis check/download, reversible error recovery and a separate cancelled run. Record domain/software experience and all assistance. | Retain actual task outcomes and the tester's own explanations from a planned 45–60 minute session, with longer setup/execution recorded separately if needed. A preinstalled environment assesses interface use only; assess independent installation/startup separately after OT-046. A novice session supplies usability findings without automatically satisfying intended-researcher or P1 acceptance. |
| OT-049 — Observed fixes and human retest | Select changes from OT-048 observations, prioritizing blocked tasks and mistaken evidence interpretations, followed by recoverable navigation/text difficulties. Preserve the original observations and failed attempts. | Every observed blocking or interpretation issue is resolved and its affected tasks are repeated by a human on an identified fixed candidate. Run checks appropriate to each change and retain remaining difficulties, unassessed tasks/platforms and the scoped usability verdict. Internal automated checks do not substitute for the human retest. |

**Delivery status, 13 October 2026:** the technical preparation is integrated
into local and GitHub main through PR #35. The
[internal verification record](docs/research/gui-test-session-verification.md)
binds the checked implementation and actual scopes; integration and exact-candidate
repository checks are recorded [above](#current-github-main-and-verification).

| Package | Current delivery and remaining acceptance |
| --- | --- |
| OT-045 | Implemented and internally verified: bound source bundle, private Dutch cards, offline canonical guides and complete/interrupted native references; actual external handoff review remains open. |
| OT-046 | Explicit installation/check/start files implemented and integrated into main; fresh macOS receiving-checkout installation and GUI startup verified. Windows/WSL files pass syntax and controlled-call checks; an actual Windows host is the next platform check, with clean-system setup, localhost access and lifecycle acceptance still open. |
| OT-047 | Implemented and internally verified: standalone/session worksheets, bounded export/restore, refusal without data replacement and separate empty retest records. No participant result is prefilled. |
| OT-048 | Technically prepared; no actual human session or observation is recorded. The first tester's own Windows host still needs its readiness assessment. |
| OT-049 | Retest recording prepared; observed human issues, resulting fixes and human retests remain unexecuted. Internal implementation fixes do not stand in for these observations. |

**OT-050 — Internal usability fixes:** the maintainer requested a separate
worktree and `codex/gui-usability-fixes` branch for eight findings from the
internal agent walkthrough of main `6cbc8c90f3a7ca7754da834c2f17d8b54e4104c7`.
Original notes and screenshots stay private under ignored
`results/usability/20261013/agent-walkthrough-6cbc8c9/`. This increment precedes
the first human session; it does not close OT-048 or OT-049.

| Finding | Selected fix and local acceptance |
| --- | --- |
| F01 — Language and file terminology | Add a Dutch/English glossary to the private participant card and explain Python code versus its matching JSON declaration in the GUI. Keep public guides English and record glossary assistance. |
| F02 — Long-run feedback | Show observed operation state and elapsed computer time. Explicitly label 240 minutes as simulated model time; disclose unavailable per-case progress without inventing percentages or an ETA. |
| F03 — Interrupted report | Display the original native interrupted status separately from numerical acceptance and reconstruction. Preserve original artifacts and all planned denominators. |
| F04 — Disabled archive check | Explain the single-operation restriction beside the disabled action and offer a working shortcut to the ongoing task. |
| F05 — Hidden archive detail | Move focus and scroll to the selected archive heading after an explicit selection; passive polling must retain reading position. |
| F06 — Source ID error | Use one field name, an actionable format error and accessible invalid state; restoring a valid value must permit a fresh check. |
| F07 — Message in wrong view | Keep archive completion text out of the M4 activity panel; the existing global operation shortcut must open the correct workflow. |
| F08 — Restore wording | State that previously exported values were restored and no new observations added, in both supported worksheet languages. |

Completion requires meaningful regressions, the locked repository checks and
actual local browser retests of all eight affected tasks on an identified
candidate. Preserve original observations and remaining platform/human limits.
**Delivery, 13 October 2026:** all eight scoped fixes are implemented and
internally retested. Final code candidate
`83440ccb74e565114e403116ae1a95022577afa2` passed 1,282 tests in 246.041 seconds,
with 13 existing C1 runtime skips and the warning-as-error documentation build.
The [verification record](docs/research/gui-usability-fixes-verification.md)
separates the initial implementation/native run from the subsequent polling
harness correction and narrow-window scroll refinement. A real standard study
accepted 2/2 sources, 6/6 cases and 1/1 pair; a separate cancelled run retained
all planned denominators and an interrupted report. Nine native report artifacts
matched their reconstructions byte for byte. Dutch worksheet export/restore,
specific Source ID recovery, task-scoped activity, busy shortcuts and final
390 × 844 archive-detail focus/scroll were actually exercised. This closes the
internal OT-050 implementation and local verification scope. Main integration
completed through PR #37 on 14 October 2026 with the maintainer-requested
`[skip ci]` marker; hosted checks and external human/platform acceptance remain
open. Original private observations and intermediate failed attempts
are retained; no participant findings are inferred.

**Next practical steps, 17 October 2026:**

**OT-051 — Second internal UI/UX follow-up, verified 17 October 2026:** resolved
UX2-01–05 from the internal review of main
`84f7b992e04d0d802ce34813bf5b09f17adcca53` on the separate
`codex/uiux-round2-fixes` branch/worktree. Original observations remain private
under ignored `results/usability/20261015/uiux-round2-84f7b99/`.

| Finding | Scoped change and acceptance |
| --- | --- |
| UX2-01 | Retain bounded M4 draft inputs in per-tab, workspace-scoped browser storage. Restore editable inputs after reload, require a fresh setup check and provide reset/failure feedback. Never restore readiness or execution authority from browser data. |
| UX2-02 | Give M3 example preparation and setup checks their own completion messages, in both the global operation strip and M3 panel. Refer to report coverage only for actual execution/reconstruction. |
| UX2-03 | Identify local references by registration/location context and explain unavailable-root recovery. Add reversible hide/restore controls without deleting or changing archive files, broadening allowed roots or bypassing operation ownership. |
| UX2-04 | Sort own results across workflow types by latest recorded activity; consistently show date/time and explicitly label missing timestamps. Retain failed/cancelled items and keyboard focus during polling. |
| UX2-05 | Display M3 metric summaries compactly with an explicit rounding label; keep exact retained values accessible and original report downloads unchanged. No numerical gate or calculation changes. |

Implementation and internal verification were completed on this branch and
integrated into main on 17 October 2026 with `[skip ci]` at the maintainer's
request. Hosted CI was intentionally skipped. The
[verification record](docs/research/gui-uiux-round2-verification.md) covers
actual browser retests of all five tasks, restored drafts with fresh readiness,
unavailable-reference hide/restore/reconnection, a fresh 2/2 synthetic M3
comparison, dated mixed-workflow ordering and 390-pixel layouts. All 885 original
reference files retained their byte identities. Locked repository checks passed
with 1,288 tests and 13 existing C1 skips. This is internal software verification;
Windows/WSL, OT-048 human observations and OT-049 human retests remain open.

**OT-052 — Explain the GUI start page, 17 October 2026:** integrated into main
with `[skip ci]` at the maintainer's request. Introduce the virtual lab before
showing two research questions, each with example inputs, expected report
contents and a separate Explore action. Keep invented-data scope visible.
Local navigation and responsive browser checks cover the presentation;
equations and runners are unchanged. Preserve earlier frozen packets and
prepare a new version-bound Windows packet from integrated main. Actual
Windows/WSL checks and independent human comprehension checks remain open.

1. Identify and review the actual OT-045 packet's source, archive, reader and
   dependency rights before transfer. Retain its frozen identity and record any
   difference from the preserved candidate.
2. Check the identified Windows host for OT-046. Record its Windows version,
   Ubuntu/WSL 2 state and existing prerequisites, then assess explicit install,
   check and start, browser access through localhost, cancellation and server
   cleanup. Record assistance and failures; do not describe an existing personal
   computer as a clean-system test without evidence.
3. Execute OT-048 with the identified tester. Plan 45–60 minutes for the standard
   M4 tasks, retaining setup/execution time separately. Record experience,
   actual task outcomes, explanations and assistance in the OT-047 worksheet.
   Assess installation/startup separately from interface use. If setup is
   blocked, retain that outcome before using prepared software or verified saved
   reports for the remaining interpretation tasks.
4. Select OT-049 changes from those observations, prioritizing blocked tasks
   and mistaken interpretations. Preserve the original session and failed
   attempts, identify each fixed candidate and repeat affected tasks with a
   human. No observation-driven fix or human retest is claimed yet.

**Sequence:** OT-045 and OT-047 technical preparation is delivered. OT-046's
actual Windows verification is the next practical check for the tester's own
computer; a preinstalled environment can still support an interface-only
OT-048 session. Follow actual observations with OT-049, and assess independent
installation/startup as a separate task. Keep the participant's goals separate
from the moderator's expected outcomes; do not provide a click-by-click route
or hide assistance. If execution is blocked, record the block before using a
verified saved report for later interpretation tasks.

**Scope and later decisions:** reuse the existing local browser interface,
scientific runners, model/source bytes, protocols, numerical criteria, units,
clocks and locks. The 22 October [OT-058 requirement](#planned-windows-installer-ot-058)
selects one Windows installer as the product installation goal. Its native packaging
architecture is recorded in [decision 0073](docs/decisions/0073-native-windows-installer.md);
installer acceptance is not required before the first interface session using
a prepared environment.
No new model, empirical study, public release or clinical claim is selected.
Retain the proposed four-to-six-researcher formative round as a later intended-user
step. The first session and its retest do not close the separate P1 exercise,
independent M2 reproduction or M3–M5 scientific acceptance criteria.

### MMTT interface follow-up (OT-057)

**Implemented and internally verified, 19 October 2026:**
an internal browser walkthrough of main
`9e8078f` exercised four examples across OT-054/055. Execution, reconstruction
and reopening worked; seven interface problems were observed. This follow-up
was implemented in a separate worktree on `codex/mmtt-uiux-fixes`, then merged
and pushed to main at `ac94080` on 19 October with `[skip ci]`. Local and remote
main matched when checked on 22 October. The
[canonical verification record](docs/research/ot057-uiux-verification.md) binds
the implementation, integration and evidence limits.

- [x] UX-01: edit a saved plan without a disabled-action dead end or lost edits;
  preserve the original plan and require a fresh checked freeze.
- [x] UX-02: identify invalid fields and variants, reveal/focus the problem and
  retain entered values through correction.
- [x] UX-03: take completed operations directly to their report; keep running
  operation progress and cancellation reachable.
- [x] UX-04: provide a short supplied-example route with explained assumptions
  and optional technical settings.
- [x] UX-05: lead sampling results with the bounded conclusion and compact
  schedule comparison, retaining all failures and separate allocations/variants.
- [x] UX-06: retain recognizable example or user names across saved plans,
  analysis lists, reload and Results, outside the scientific archive.
- [x] UX-07: consistently distinguish execution, result completeness and saved
  report checks, including expected incomplete examples and actual failures.

Local browser retests on macOS exercised the supplied compact routes, a hidden
invalid volume (0), focused correction to 5, a new frozen plan from each task,
unchanged original plans, direct report navigation, explicit reconstruction and
named Results after reload. Task 1 completed its original and edited analysis.
Task 2 retained 60/60 required variant pairs and 7,680/7,680 perturbation pairs
for the direction-reversal control; its low/censored control retained 36/60
and 6,000/7,680 respectively and stayed visibly incomplete after reconstruction.
The per-assumption comparison preserves 2 development and 3 evaluation
participants, including unavailable results; variants are never counted as
additional people.

Focused regressions cover both plan-copy routes, changed-input refusal, field
recovery, delayed navigation/polling, native summary counts, retained failures,
names/restart/legacy fallback and execution/check distinctions. Browser evidence
is retained in the implementation worktree under
`results/uiux-mmtt-fixes-2026-10-19/`.
The locked repository check passes 1,393 tests with 13 existing skips, all
format/lint checks and the strict documentation build. All four browser-run
analyses were reconstructed with the native reader, including the incomplete one.
These fixes do not change the estimator, frozen scientific conventions or the
open human pilot. Windows and independent human usability remain separate checks.

The [22 October packet refresh](docs/research/mmtt-beginner-packet-verification.md)
now completes local packet preparation, receiving installation and both task
checks. Next record installation, start/stop and both MMTT routes on an actual
Windows host. Existing packets do not update when main changes.
Keep a beginner's usability session separate from the OT-056 comparative
researcher pilot; use that pilot's task-specific protocol and forms to assess
researcher value. Record observed problems and retest fixes before claiming
human acceptance.

### MMTT beginner Windows/WSL packet refresh

**Implementation, 22 October 2026:** refresh the existing version-bound
OT-045–049 generator from verified remote main `9d418dc`, including the OT-057
interface fixes. The [session guide](docs/gui-test-session.md) now selects an
MMTT beginner session: two Dutch participant goals, separate moderator
expectations, offline installation/startup/task feedback and the existing safe
export/restore/retest route. Preserve separate M4 cards, forms, complete and
interrupted references and all existing runners/readers. Public guides stay
English. The packet is frozen from a clean committed implementation; an older
packet never silently follows main.

**Local completion:** clean implementation `c967296` produced the identified
69,315,062-byte Dutch ZIP. Fresh disposable macOS receiving installation/check/
start, both native task flows, reopening after restart, exact reconstruction and
browser feedback export/restore/retest checks passed. The locked repository
check passed 1,395 tests with 13 existing skips and the strict documentation build.
The [verification record](docs/research/mmtt-beginner-packet-verification.md)
binds identities and limitations. Before integration, the complete packet and
verification material were preserved and checked byte-for-byte in the primary
checkout under `results/usability/20261022/windows-mmtt-c967296/`. The
packet remains bound to `c967296` when Git branches advance.
Actual Windows/WSL installation,
localhost access and lifecycle checks require the tester's host; macOS execution
cannot close that gate. No human observations are prefilled. OT-048/049 human
sessions/retests and the OT-056 comparative researcher pilot remain open.

### Planned Windows installer (OT-058)

**Planning decision, 22 October 2026:** make independent Windows installation
and startup a product requirement. A user downloads one OpenT1D installer,
installs it through a graphical flow and opens OpenT1D from the Windows Start
menu or a shortcut. No GitHub account, source checkout, separate Git/WSL/Ubuntu/
Python setup, environment management or terminal commands are user prerequisites.
The installer and application manage their required runtime components.

**Implementation status, 22 October 2026:** implemented on the separate
`codex/ot058-windows-installer` branch. [Decision 0073](docs/decisions/0073-native-windows-installer.md)
selects a per-user offline NSIS installer with three hash-pinned portable
CPython 3.12.15 runtimes and the existing locked dependencies. **All current GUI
routes are in scope for the first installer**, including M3, maintained M4,
campaigns, both MMTT analyses, the results library and durable archives; M5
retains its existing report-only GUI scope. The desktop entry separates data
from immutable application versions, verifies included components without Git
or uv, preserves retained readers across update/removal and coordinates launch
with installation. Windows Job Objects own descendants and bounded cleanup;
POSIX execution and numerical locks are preserved.

The builder, desktop routes, native file/locking/process primitives and manual
Windows payload-verification workflow are implemented. The
[internal verification record](docs/research/ot058-installer-verification.md)
records local checks and their limits. On 23 October, an activated Windows 11
Enterprise Evaluation x64 VM on local QEMU passed clean-system prerequisite
checks and a normal shutdown/reboot. No GitHub Actions run was used. The first
graphical install failed while inspecting a not-yet-created installation path.
The targeted correction passed all three native regression tests, including
spaces/Unicode and junction refusal. Corrected candidate A was built from clean
`f661a63d2231726cc2fba6fc5ab0b288d9ad363c`; the full local check passed 1,459
tests with 24 explicit skips. After verified baseline restoration, the second
ordinary-user baseline and clean offline graphical installation passed. The
terminal Install phase completed at 10:12:01 UTC on 23 October, with controller
exit code zero, the expected installed identity, registration, shortcuts and
payload audit. The default Finish action opened the local OpenT1D Start page;
More navigation and the MMTT screen worked. Preparing the **Consistent increase
control** MMTT example then failed with **Entry owner exited with live descendants**;
no calculation completed. The native suite also ran 23 tests in 36.447
seconds with one failure, four errors and one expected symlink-permission skip.
All three installer-path and all three directory tests passed. Native diagnostics
identified two causes: path and descriptor file snapshots used different Windows
`st_ctime_ns` meanings, and `CREATE_NO_WINDOW` left a console-host process alive
after its Python worker exited. A controlled detached-process comparison removed
the latter symptom without changing the cleanup budget. The corrected source
passed 34 native regression tests in 174.221 seconds, with one expected
symlink-permission skip. This diagnostic used a separate dirty source copy and
left installed A unchanged; it does not establish clean packaged acceptance.
The final local repository check passed 1,470 tests with 26 explicit skips and
strict documentation checks. Clean candidate C (`4c84773e6fd4`) then passed a
fresh ordinary-user offline graphical installation and default browser startup.
Its actual MMTT browser route completed preparation, freeze, the unchanged
128-draw analysis and native reconstruction with identical report bytes; normal
GUI shutdown removed the server, listener and session file. C's native suite
ran 34 tests with one nested live-admission failure, no errors and the expected
permission skip. Its shortcut phase reused the same session but failed the first
M3 readiness check during repeated runtime ancestor checks. Candidate E
(`c897c6ac0c10`) was subsequently built and audited; it has not been installed.
The full host check passed 1,511 tests with 27 explicit skips. An isolated
modified-source Windows preflight ran 84 tests in 257.594 seconds with one
failure, no errors and four skips. A targeted repeat failed the test's start-phase
precondition while its worker was still in `snapshot`; cancellation had not been
requested. This does not establish a cancellation defect or packaged acceptance.
Candidate F (`e4ffb0927698`) subsequently passed the graphical C-to-F update and
its complete installed native phase: 84 tests, no failures or errors, four allowed
skip entries. The update preserved saved data and the retained C reader. Its
first shortcut workflow failed at M3 fixture preparation; one unchanged-candidate
repeat advanced through fixture/intake/configuration but failed forecast readiness
with `WinError 5` during atomic phase-status replacement. Both failed attempts
and normal GUI shutdowns are retained. Candidate G (`9fe00f84fc5f`) then passed
its graphical F-to-G update, preserving all 176 original saved files and the
retained C reader, and the installed native suite (87 tests, no failures/errors,
four allowed skip entries). G's shortcut workflow reused one session but failed
with the final M3 comparison state left unpublished; both candidate children had
finished with exit code zero. A separate fresh-file Windows probe reproduced
the shared writer's failure while a reader holds the destination open. Those
failures remain preserved. Candidate H (`4c9fcf2a03c6`) includes the shared
publication correction and passed the graphical G-to-H update, preserving all
343 saved files and the original C report through retained-reader reconstruction.
Its installed native suite passed 92 tests with no failures or errors and four
allowed skip entries. H's M3 forecast/comparison checks, runs and explicit
readers completed, but Shortcuts exhausted its 2,820-second aggregate wait and
durable export its original 900-second command limit during a final reader
runtime inventory check. The child's separate 900-second smoke observation also
failed; its process exit code was not captured. Normal GUI Exit was confirmed.
The separate FullSmoke run subsequently failed M4's historical reference at its
unchanged 600-second limit. Its nested worker was interrupted during NumPy import;
both supplied source evaluations remained unattempted. Why the reference exceeded
its deadline and how that time was distributed remain unproven. Four separate H
API checks then passed: both 32-draw MMTT examples with byte-equal native
reconstruction after restart, controlled sampling cancellation with its interrupted
report, and the M5 report-only library. These do not replace the failed suites.
The separate campaign then failed both historical-reference stages at their
unchanged 600-second limits: 0/2 slots and 0/4 source/scenario evaluations were
accepted. It ended before controlled cancellation; resume was not reached.
Separate lifecycle preparation and same-version reinstallation passed. The latter
preserved all 668 original files with no additions, verified the complete H payload
and freshly reconstructed both H M3 reports and the original C MMTT report.
Repair restored the complete H payload and default browser startup, but its strict
preservation phase failed: a later 689-file comparison found 687 unchanged, two
verification-status changes and no missing or added files. Reversing only those
status changes reproduced both original hashes and byte counts, consistent with
H's startup normalization; the before-file bodies were not separately retrieved.
Repair remains failed and its six subsequent launch/reader proofs were not reached.
Uninstall passed: all 689 saved files remained unchanged with no additions,
registration and main shortcuts were removed, and complete H/C reader inventories
passed. Fresh post-uninstall readers then reconstructed both H M3 reports and
the original C MMTT report with unchanged bytes, exit zero and no forced cleanup
or surviving owned processes; full H/C reader inventories passed again. Complete
workflow and independent-user acceptance remain open. Curated, hash-verified closed records and screenshots
support these outcomes; complete synthetic archive bodies remain in the guest.
The earlier 22 October hosted Actions attempt was blocked by account billing/
spending limits. No independent user session is claimed. The canonical
[installation guide](docs/windows-installation.md) owns package use, building,
data/reader retention and the remaining platform acceptance exercise.

**Current candidate J, 27 October:** clean source `f47868a9b135` corrects the
unstable Windows directory-size comparison without changing regular-file checks,
model execution or deadlines. Its build, independent payload audit and locked
1,545-test host check passed (32 skips; strict documentation checks passed).
The I-to-J upgrade test phase failed when the installed-payload audit exceeded
its 1,800-second observation limit. The graphical Finish screen and automatic
browser startup were observed. The full audit later passed outside that limit,
followed by a confirmed normal application stop; the original phase remains
failed. Separate CompleteUpgrade passed its fresh full audit within the same
limit, preserved all 366 original files byte-for-byte and passed 18 native tests
without skips against installed J. Normal start/stop and retention of I's manifest
and reader shortcut passed; I's reader was not executed. One synthetic 32-draw
MMTT API case and its fresh native reader passed with unchanged report bytes.
Repair passed with a fresh reader and unchanged original reports;
Reinstall also passed, starting with the application running. Attempt 08 passed
a clean J baseline, offline installation, shortcut reuse and one 32-draw MMTT API
workflow with fresh reconstruction; a separate agent browser review verified the
healthy Start page, results library and saved report. No active numerical-job
maintenance is claimed. Attempt 09 installed J passed 124 native tests
with the six declared skips, no failures/errors and a full post-test payload
audit; selected-file attestation passed separately. The five-person, four-schedule
sampling-information-loss API case passed at 32 draws, with fresh readers and
unchanged reports across restart. Genuine sampling cancellation and fresh
interrupted-report readers also passed without forced cleanup or survivors.
Attempt 09's M3 forecast remains unresolved after the private environment loss.
Recovery attempt 10 passed licensed clean installation from the genuine Edge
download, healthy automatic first GUI startup, shortcut reuse, normal exit and
124 native tests (six declared skips), with an exact full payload audit. Root
completed a fresh 32-draw Task 1 MMTT analysis and reader through the GUI, with
unchanged original reports. A separate sampling-information-loss API case also
passed with fresh readers. New synthetic M3 forecast/comparison and saved
readers passed; a separate genuine cancellation retained raw byte copies, with
integrity/reconstruction false and completeness unknown. Activation followed
explicit user authorization; the
candidate remains unsigned and public SmartScreen reputation is untested.
Two M3 durable-package export/integrity/reconstruction routes passed across
restart. Private-workspace launcher/session controls also passed, including
reopen, authentication/schema refusals, genuine stale-session recovery and
normal API/CLI stops. Further agent-operated GUI export, external Task 1 archive
index/reader, reversible visibility and normal exit passed. Two M3 raw-retention
receipts are fully preserved, with byte-copy checks only. Eleven-case lifecycle
preparation passed within its independently reviewed preparatory scope. The first
Maintain attempt failed before launch on its input path. The second completed
installation, launch refusal, full payload audit and data preservation, but its
report wrapper failed on an output-filename collision; the phase remains failed.
Separate report-only comparison and normal stop passed, with the full comparison
report independently verified. The original Uninstall05 and later observer failed. A separate controlled
Uninstall test then cancelled an observed native analysis cleanly. Post-removal
checks passed for both retained payloads, all 7,023 original data files and
Windows registration/shortcuts; eleven fresh retained-case readers passed with
22 unchanged report hashes, normal stop and a final full payload audit.
These targeted passes preserve the original failed phases and private-controller
failures. Full maintenance acceptance remains open. A separate fresh I-to-J upgrade passed
its full J payload audit, original-case preservation, fresh J reader, 18 native
checks and normal stops. The preservation check found 93 of 95 original files
byte-identical, exactly two precomputed verification-bookkeeping transitions and
zero additions; both original reports stayed identical. Original InstallI,
admission-wrapper and guard-controller failures remain recorded. This bounded
pass does not complete OT-058 or the remaining workflow/release gates.
The new campaign and M4 tests failed at fixed 600-second reference-worker
deadlines before candidate source evaluation. Their failures remain open.
Remaining workflows/lifecycle checks, full VM/TPM restore validation and
independent human acceptance remain open.

I's initial native failure and unchanged warm retry pass (121 tests, six allowed
skips), both M4 harness failures, actual M4 run failure and failed
maintenance preparation remain preserved in the dossier. Complete workflow and
lifecycle acceptance remain open.

The existing OT-046 Windows/WSL route remains available for interim technical
checks. No public release version or delivery date is assigned. The comparative
researcher pilot is not a prerequisite for this implementation work.

**Delivery sequence:**

1. Declare the supported Windows versions, architectures and GUI workflow set.
   Assess private runtime packaging and the current Unix file-lock, signal,
   process-group and cancellation dependencies. Record the architecture in a
   short decision before changing shared process ownership. Wrapping today's
   WSL instructions in a launcher does not meet the requirement.
2. Build one versioned Windows installer that supplies or automatically obtains
   the pinned components, preserves their identities and attribution, and creates
   a recognizable launch shortcut. Keep runtimes application-managed and data
   outside the installation directory. State any network, administrator or
   restart requirements in the graphical flow; users must not perform separate
   prerequisite installations or shell configuration.
3. Reuse the local GUI and authoritative runners/readers. Opening the shortcut
   starts the application and opens its interface. Provide understandable
   installation progress, failures and recovery. Verify shutdown, cancellation,
   repeated launch, update/reinstallation and uninstall without silently deleting
   saved experiments or losing the reader identities needed for reconstruction.
4. Verify the packaged workflows on actual clean Windows installations, then
   observe an independent user install, start and complete a supplied example.
   Record supported conditions, assistance, failures and retests. Include both
   synthetic MMTT tasks and all other current GUI routes in the first installer;
   each needs packaged execution or reader checks within its existing scope. Keep M5's current report-only scope explicit.

**Acceptance:**

- [x] A declared clean Windows system with no Git, Python, WSL, Ubuntu or
  OpenT1D checkout can install from one installer, without terminal commands
  or separate dependency setup. Any required component provisioning is managed
  by that installation flow. Internally demonstrated for candidates A, C and I
  and J's attempt 08 on the declared Windows 11 x64 VM, offline under an ordinary
  account; independent
  human use remains a separate criterion below.
- [ ] An independent user can launch from the shortcut, complete the supplied
  MMTT examples, save their reports, close and reopen OpenT1D, and reconstruct
  the saved analyses without developer assistance.
- [ ] Packaged results match the existing numerical and reconstruction criteria;
  failures, cancellation and process cleanup retain their recorded guarantees.
  Installation, update and uninstall checks preserve user-owned archives.
- [ ] The delivered package has recorded source/runtime identities, applicable
  distribution rights and notices, a documented supported-platform scope and
  one canonical installation guide. Local packaging tests and independent user
  acceptance are recorded separately.

This increment changes delivery and portability. It preserves scientific
contracts and the separate P1, M2 and empirical acceptance requirements. Keep
the repository/CLI route for developers and reproducible technical work; a
working installer does not itself establish a public release or model validity.

### Planned mixed-meal analysis tasks

**OT-056 internal technical acceptance, 18 October 2026:** complete within the
synthetic OT-053 boundary. Controlled OT-054/055 CLI/GUI handoffs are adopted;
both same-estimator notebooks pass the combined 22-case native chain,
independent analytical answers, omitted-value/missing-time controls, fresh
execution and reconstruction after removal of the original output directory.
The final integrated code, including the Task 2 library correction, passes
1,390 tests with 13 existing skips and the strict documentation build.
The [verification record](experiments/ot056_pilot/verification.json) keeps
technical completion separate from the open human pilot and product decision.

**OT-056 preparation, 18 October 2026:** the
[comparative pilot protocol](docs/research/ot056-researcher-pilot.md) and
[blank forms](docs/research/ot056-pilot-forms.md) specify strong comparators,
counterbalanced slots, independent correctness review, failure-aware timing and
first/repeated-study effort. Local bookkeeping prepares empty packets and audits
their coverage; it supplies no human observations or product decision. Verified
Software handoffs and executable cases are verified above. The human session
freeze still requires comparator qualification/access/exports, six researchers
across two teams, independent case/difficulty review and an independent reviewer.

**Planning decision, 18 October 2026:** build two related research tasks on a
shared observation-analysis core, following [decision 0066](docs/decisions/0066-observation-analysis-tasks.md).
Prioritize a useful complete task and demonstrate reuse with its companion.
The first scope is retrospective analysis of existing standardized MMTTs in
adults with T1D and measurable endogenous secretion, with two linked visits
per participant. The [OT-053 feasibility dossier](docs/research/ot053-mmtt-feasibility.md)
now gives a **narrow** decision: fixed-kinetic synthetic OT-054 preparation may
proceed, followed by synthetic OT-055 reuse. No authorized complete adult visit
pairs, human kinetic protocol, researcher participation or empirical outcome is
confirmed. No owner or delivery date is assigned. [Decision 0067](docs/decisions/0067-mmtt-feasibility-boundary.md)
fixes the bounded endpoint and initialization conventions; it selects no
upstream R dependency or empirical uncertainty distribution.

This extension supports research on endogenous secretion. It does not model
cell implantation, immune protection or a cure. Existing synthetic M4
workflows remain completed within their recorded scope; this is a new route
for fitting observations, not an input option on the current causal callback.
The [Mari source audit](docs/research/m4-independent-source-preflight.md)
illustrates why whole-trace analysis must retain its own scientific contract.

#### Shared question, observations and endpoint

Use one primary endpoint for both tasks: estimated total endogenous insulin
secretion over the observed **0–120-minute** window, and its paired change
between visits. OT-053 must freeze physical units, normalization, basal and
initial-state conventions, visit comparison and any cohort summary before
evaluation. Display measured C-peptide area under the curve as a separate,
model-light reference; it is not the same endpoint or ground truth for secretion.
Keep glucose exposure and test conditions visible: a change in secretion under
a different glucose stimulus does not itself establish restored beta-cell
function or a treatment effect.

The local observation package must preserve participant, visit and challenge
identities; actual sample times; glucose and C-peptide values and units; meal
and test protocol; assay and detection/quantification limits; missing or
censored values; and the demographic, renal and medication/insulin context
required by the selected method. Preserve source bytes and document conversion.
Use participant-disjoint development and evaluation allocations, retaining all
visits of one person in the same allocation. Public fixtures remain invented;
restricted observations stay under the researcher's authorized local control.

#### Task 1 — Sensitivity of the secretion conclusion

**Synthetic implementation:** the shared core, paired CLI/GUI, fixed-engineering
assumptions, complete failure accounting and readers are internally verified in
the [OT-054 record](docs/research/ot054-verification.md), with combined OT-056
verification above. Population-appropriate kinetics, defensible human ranges
and empirical interpretation retain separate evidence requirements.

**Researcher question:** does the conclusion about change between visits remain
consistent under defensible analysis assumptions?

- [x] Provide local CSV import, a documented example and actionable validation
  of units, sample times, visit linkage and missing/censored observations.
- [x] Freeze the endpoint, one source-faithful estimation method, assumption
  variants, error/uncertainty procedure and interpretation rules in an analysis
  plan before evaluation.
- [x] Execute a small prespecified set of defensible variants, such as
  C-peptide distribution/removal parameters, interpolation or basal handling.
  Source their ranges and population applicability; engineering stress bounds
  must not be presented as an empirical human uncertainty distribution.
- [x] Report estimates, paired changes, uncertainty conditional on each variant,
  between-variant sensitivity, fit/boundary failures and full participant
  coverage. Do not average away disagreement or silently exclude failed fits.
- [x] Classify the conclusion using frozen rules: consistent within the
  investigated assumptions, assumption-dependent, or insufficiently determined.
  Do not equate a nonsignificant change with evidence of no change.

**Bounded implementation:** these software items are implemented for synthetic
fixed-kinetic observations only, under OT-053. Engineering stresses do not
qualify human ranges, and no empirical/user-value gate is closed. The
[OT-054 verification record](docs/research/ot054-verification.md) binds the
CLI/GUI, numerical, failure and reconstruction checks.

Begin with one estimation method and justified variants. Linear and spline
interpolation are variants, not independent biological models. A later second
method must produce the same physical endpoint before being compared; similarly
named beta-cell parameters need not have the same meaning. Do not estimate an
unrestricted secretory input and all kinetic parameters from a single curve
without establishing identifiability.

**Deliverable:** a complete import-to-report workflow, with source/runtime and
plan identities, retained attempts and independently reconstructible analysis.
Numerical checks and an independent reference calculation establish software
agreement within declared tolerances; human interpretation requires appropriate
observations and domain review.

#### Task 2 — Information loss with fewer measurement times

**Synthetic implementation:** CLI, GUI, raw-subset shared-core refits, all
failure-aware comparisons and reconstruction are internally verified in the
[OT-055 record](docs/research/ot055-verification.md). The remaining boxes below
refer to empirical use of appropriate participant observations. Engineered
evaluation IDs exercise allocation logic and do not supply held-out evidence.

**Researcher question:** which prespecified reductions in measurement times
preserve enough information for the same endpoint and paired-change conclusion?

- [x] Reuse Task 1's observation package, estimation method, assumptions,
  uncertainty procedure and report infrastructure.
- [ ] Define the full observed schedule and two or three candidate subsets of
  actual measurement times within the same 0–120-minute window. Choose subsets
  on development participants and freeze them before held-out evaluation.
- [x] Remove observations before interpolation or estimation, then rerun the
  analysis using only retained measurements. Do not initialize or constrain a
  reduced analysis with participant-specific values learned from removed data.
- [ ] Compare absolute differences, systematic bias, precision, paired-change
  conclusions and failures, including behavior at low C-peptide concentrations.
  Correlation alone is not an equivalence criterion; preserve planned denominators.
- [ ] Report the tradeoff between omitted measurement times and information
  loss. Claim fewer blood draws only where the whole study protocol permits
  omitting those draws, including samples for other required analytes.

Freeze acceptable endpoint/paired-change differences and precision requirements
with researchers before held-out assessment, informed by the scientific use
and assay limitations. The evaluation sample size must support that assessment;
report uncertainty rather than deriving clinical margins from a convenient
percentage. The full curve is a reference analysis, not true secretion.
"No reduced schedule meets the criteria" is an admissible result.

Test duration stays fixed. Comparing two- and four-hour endpoints is a separate
study; [Boyle et al.](https://pubmed.ncbi.nlm.nih.gov/27208317/) demonstrate that
the captured C-peptide responses can differ. Retrospective agreement does not
validate a new prospective clinical sampling protocol.

#### Reuse and required platform work

| Component | Reuse candidate | Required extension |
| --- | --- | --- |
| Local execution and archives | Common entry, locked setup, process ownership, retained failures and durable archives | Explicit task registration, schemas, trusted readers and private observation handling; existing routes are not a general execution API |
| C-peptide calculations | BC-003 equations and independent numerical controls | Check source/population applicability, initialization and scale for the selected measured-data task |
| Sensitivity and uncertainty | BC-011–014 numerical checks, sensitivity, nuisance profiles and synthetic coverage preparation | Adapt fixed synthetic prototypes to actual times, assay errors, censoring and the chosen estimator; validate the new procedure |
| Sampling comparisons | BC-015-P4 paired schedule design and failure accounting | Remove actual observations before fitting and evaluate on held-out participants; the known synthetic pulse is not an MMTT model |
| Presentation | Local GUI and archive library | Observation validation, frozen analysis-plan controls and two task reports, with explicit source and evidence scope |

The existing [profile analysis](docs/research/m4-profile-likelihood-results.md)
and [sampling experiment](docs/research/m4-sampling-window-results.md) are
preparation, not measured-data tools. Reuse suitable code and verification
patterns after reviewing their assumptions; do not route MMTTs through the
current one-state feedback model merely to preserve its interface.

The external R package [insulin.secretion](https://kstier.r-universe.dev/insulin.secretion)
is a candidate for an existing deconvolution implementation. OT-053 must pin
its source, inspect numerical behavior and redistribution/license obligations,
and assess population-specific kinetic inputs before adoption. Its availability
does not establish T1D applicability. The original [Van Cauter parameter study](https://pubmed.ncbi.nlm.nih.gov/1551497/)
included normal, obese and non-insulin-dependent diabetes populations; do not
silently map T1D to a type-2 category. No new dependency is selected by this plan.

#### Comparative value and acceptance

Use strong existing workflows as comparators. [AOMM](https://www.nanomath.us/aomm)
already describes batch MMTT analysis, secretion indices and precision measures;
[SAAM II](https://www.nanomath.us/saamii) provides model construction and parameter
estimation. Batch processing, plots or uncertainty alone are not a demonstrated
OpenT1D advantage. Compare the researcher's actual tool plus competent scripts,
and a well-prepared notebook using the same open estimator, with OpenT1D.
An experienced user should prepare the comparator, with matched data, methods,
assumption/schedule options, information and support. Verify licensed access and
actual export support; no AOMM API or connector is assumed.

| Evidence layer | Required assessment |
| --- | --- |
| Numerical correctness | Source-faithful reference agreement under declared tolerances, independent known synthetic cases and selected failures; reconstruction checks analysis, not biological truth |
| Research usefulness | Appropriate measured observations, domain-informed interpretation rules, frozen empirical protocol and held-out Task 2 assessment with uncertainty; retain negative or indeterminate results |
| Product value | Correct and complete reports with lower total effort or better decision quality than strong existing workflows, assessed by independent intended users |

Plan a formative product pilot with **six researchers from at least two teams**,
matched cases and counterbalanced tool order. The primary measure is active
researcher time to a correct, complete report judged against a frozen rubric
by an independent domain reviewer. Retain incomplete sessions and timeouts;
faster incorrect reports do not count as success. Record interpretation errors,
missed problems, unnecessary warnings, assistance, installation and compute
time. Include comparator preparation, integration and maintenance work, and
report total effort for both first and repeated studies.

Proposed product progression criteria, to freeze before the pilot, are:

- At least five of six researchers complete each task independently and correctly.
- At least 30% lower median active time to a correct report for each task against
  the strongest applicable comparator, with paired results and variability shown.
- No additional critical interpretation errors, such as incorrect units/visits,
  dropped failures or presenting an indeterminate result as reliable.

These are proposed product targets, not observed results, clinical thresholds or
a powered market-effect claim. Participant availability, actual sessions and
independent assessment remain open. The research dataset size is a separate
scientific design decision; six tool users are not six clinical observations.
Task 2 must demonstrate shared import, model execution, diagnostics and archive
code rather than duplicating Task 1; record the actual changes and maintenance
cost instead of promising a percentage of reuse.

#### Delivery sequence and decision points

| Package | Next artifact and acceptance | Status |
| --- | --- | --- |
| OT-053 — Task and data feasibility | One intended research task, candidate source/data inventory, rights and population-fit assessment, common endpoint, strong comparator and a proceed/narrow/stop disposition | Complete: [narrow dossier and controlled handoff](docs/research/ot053-mmtt-feasibility.md); analytical and WebAssembly R-function controls only; researcher and usable authorized pairs unconfirmed |
| OT-054 — Shared core and Task 1 | Versioned observation/analysis contract, source-pinned method, import-to-report implementation, independent numerical checks, failure handling and reconstruction | Implemented within the OT-053 narrow synthetic scope: shared core, frozen paired analysis, local GUI, archive readers and internal verification; [OT-054 record](docs/research/ot054-verification.md); controlled estimator/uncertainty retained; Task 2 required-time admission follows decision 0069; human/empirical and comparative-user gates remain open |
| OT-055 — Task 2 on the shared core | Fixed-window schedule subsets, isolated refitting, full failure accounting and reusable reports; separate frozen held-out empirical assessment when observations are available | Implemented and internally verified within the synthetic scope: shared-core raw refits, CLI/GUI, all comparisons/failures and reconstruction; [OT-055 record](docs/research/ot055-verification.md). Separate empirical acceptance remains open; no clinical schedule recommendation |
| OT-056 — Comparative researcher pilot | Frozen task criteria/comparators, independently assessed sessions, total-effort/error results and a documented product continuation decision | Internal technical acceptance complete within synthetic scope: controlled OT-054/055 CLI/GUI, both notebooks, 22 cases, retained failures and relocated reconstruction; final 1,390-test check passes with 13 existing skips. Human pilot, independent assessment and product decision remain open |

The feasibility dossier is delivered with a narrow disposition. Internal source review
and bounded fixed-kinetic synthetic implementation may proceed without new human data or an
external sign-off for every change. Restricted observations require verified
rights before access; empirical conclusions require the specific protocol and
domain assessment. Do not represent synthetic preparation as completion of the
empirical or user-value gates. Existing Windows/GUI/P1 exercises remain separate
and can run when their participants and environments are available.

Narrow or reconsider this increment if appropriate measurements or defensible
kinetics cannot be established, users lack a consequential decision, or the
strong baseline delivers the same quality with comparable effort. A negative
sampling result may be scientifically useful without proving product value.
The [common laboratory delivery plan](#common-laboratory-delivery-plan) now adds
explicit shared-platform consumers across control, forecast and observation tasks.
These MMTT tasks retain their own value test; broad composition and implant/immune
modeling still require separately justified questions and evidence.

### Parallel priorities and current status

**GUI intended-user preparation, 6 October 2026:** the subsequent internal
technical preflight ran the complete maintained M4 GUI route on clean candidate
`974fe7d9ea39ba566dc3cfc9f50f95e05824ecaf`, after explicit locked installation.
Both sources and all six source/load cases passed the existing numerical gates;
the saved-analysis check reproduced the native JSON, Markdown and SVG bytes.
The twelve live graph tables displayed 11,532 saved time-point rows (46,128
cells) with an exact native-text digest match. A separate real cancellation
retained an interrupted report, full planned denominators and 0/6 accepted
source/load cases, with successful failed-archive reconstruction and no remaining
owned processes. Both complete and cancelled archives reconstructed byte for
byte after relocation and through the registered reader in a fresh clone of the
frozen source bundle. The local packet binds source and archive identities and
six blank observation records. The [researcher exercise](docs/gui-researcher-exercise.md)
retains its independent-human criterion: participants and observations are not
yet available. These are internal technical checks, not participant results or
new biological evidence.

| Track | Current evidence | Next evidence milestone | Dependencies that remain specific to this track |
| --- | --- | --- | --- |
| Glucose regulation tools — M1/M2/M3/P1 | M1/M2 and IV-001 synthetic experiments; completed bounded M3 researcher forecast workflow; P1/0.1–0.4 bounded internal technical verification and conditional human rights decision for one internal handoff; C1 external G2P2C technical M1 integration | Independent intended-user P1 exercise; authorized M3 evaluation when feasible | Broader third-party distribution rights and user verification for P1 product acceptance; human-data rights and suitability for any M3 empirical claim |
| Cure-oriented biology — M4/M5 | [BC-001](docs/research/m4-results.md): standalone reduced IVGTT secretion; [BC-002](docs/research/m4-kinetic-results.md): verified incremental insulin inlet and synthetic transfer; [BC-003](docs/research/m4-cpeptide-results.md): forward C-peptide kinetics and synthetic identifiability; [BC-004](docs/research/m4-paired-results.md): paired boundary preflight; [BC-005](docs/research/m4-paired-kinetics-results.md): paired kinetic execution; [BC-006](docs/research/m4-source-audit-results.md): internal source reconciliation; [BC-007](docs/research/m4-chain-results.md): prescribed-glucose to paired-kinetics chain; [BC-008-P1](docs/research/m4-feedback-readiness.md): source selection and basal preflight; [BC-008](docs/research/m4-feedback-results.md): analytic source verification and bounded synthetic glucose feedback; [BC-009](docs/research/m4-hepatic-results.md): primary-source hepatic assessment and matched structural comparison; [BC-010](docs/research/m4-feedback-observation-results.md): pancreatic-source C-peptide observation; [BC-011](docs/research/m4-joint-identifiability-results.md): conditional joint recovery; [BC-012](docs/research/m4-volume-sensitivity-results.md): volume misspecification/recovery; [BC-013](docs/research/m4-profile-likelihood-results.md): conditional nuisance profiles; [BC-014](docs/research/m4-coverage-results.md): synthetic gain inclusion; [BC-015-P1–P4](docs/research/m4-sampling-window-results.md): public-source readiness and synthetic sampling stress; [OT-027/0.2](docs/research/m5-cell-therapy-protocol.md): islet-function question and data requirements; completed configured M4 and frozen-source M5 researcher workflows; no human or therapy evaluation | Verify authorized paired observations and expert review; source-screen OT-027 and freeze an empirical protocol only if feasible | Population-specific basal/scale calibration, confirmed initialization/model scope, appropriate observations, domain review and intervention evidence |
| Shared laboratory — P1 and existing infrastructure | Integrated P1/M3/M4/M5 bounded workflows and internal verification; OT-028 navigation updated, OT-029 common entry and OT-030 M3 comparison internally verified; [P1/0.1](docs/p1-research-workflow.md) packages the fixed task, [P1/0.2](docs/p1-external-controller.md) accepts one local rate controller, [P1/0.3](docs/p1-upstream-pid-tutorial.md) verifies pinned upstream PID intake, and [P1/0.4](docs/research/p1-internal-followup.md) tests a second profile and distinct proportional source; conditional human rights decision for one exact internal bundle | Execute the [P1 intended-user task](docs/p1-acceptance-exercise.md), record usability issues and complete the [acceptance decision](docs/research/p1-product-acceptance-review.md) | Actual independent user execution for P1 acceptance; broader rights and independent M2 reproduction remain separately open |

Parallel means that each application area has its own evidence milestones, while internal software increments can continue independently of their timing. It does not assume extra staff or simultaneous implementation of every module. At each planning review, record the named owner when assigned, next artifact, evidence status and blocker for each selected work package. If capacity supports only one implementation at a time, alternate bounded deliverables explicitly; do not defer cure-oriented tools until original controller work is complete. A blocked human-data run can coexist with source assessment or synthetic preparation in either area.

Review both tracks when a bounded deliverable finishes or a data/access assumption changes. Continue, narrow or pause a particular question based on model fit, measurement availability and review findings; preserve negative results. Prioritize shared work only when its concrete consumer is identified. More accurate CGM forecasting is not evidence of a cell or immune mechanism, and cure-oriented work does not require a new controller.

The following table describes intended outcomes; implemented preparation is identified in the immediate deliverables and milestone records below. No human data access, generally supported external-method interface, original controller, improved physiological engine, product release or commercial demand is established by this roadmap. M0/M1/M2 protocols, native references, baselines and archived results remain historical evidence; new work receives separate versioned protocols and artifacts.

| Track | Can start when | Intended result |
| --- | --- | --- |
| M3 — External evaluation | A bounded question is specified; human-data execution additionally requires suitable data and rights | Measured predictive strengths and limitations of existing models |
| M4 — Beta-cell function | A bounded functional question and candidate evidence can be assessed; coupling requires a suitable verified engine | Tools to connect and assess a sourced secretion/capacity model with explicit limits |
| M5 — Cell or immune therapy | A disease stage, intervention question and candidate observations can be assessed | Tools and an evidence contract for a researcher-selected treatment hypothesis; any empirical evaluation is separate and authorization-bound |
| C1 — Optional original-controller study | A separate question, source comparisons, information contract and evaluation design justify it | A documented original-method result, without making superiority a platform gate |
| B1 — Optional physiological-model study | Evidence identifies a specific limitation and suitable observations exist | A tested model change compared with the unchanged source and simpler calibration |
| V1 — Optional cross-evaluation study | Compatible frozen candidate methods and supported interfaces exist | Attribution limited to the declared model/controller combinations |
| P1 — First research product | One intended user and research workflow are defined | Independently usable, reproducible tools with external-method intake and a bounded evidence package |

P1's bounded internal technical work is complete; one exact internal handoff has a conditional human rights decision, and independent usability is the current product-acceptance step. The current M3/M4/M5 researcher software increments are complete; OT-028–030 are internally verified, while empirical/biological assessment remains open. OT-031 above implements a separately frozen multiple-source M4 comparison from the observed single-source reporting limit, with locally verified native execution and artifact reconstruction. The bounded OT-024 dossier and relevant OT-015 boundary are delivered; BC-014 assesses conditional synthetic profile coverage after BC-013; BC-015-P1–P4 check public paired-observation metadata, CIT-07 fields, one alternate aggregate meal source and a synthetic C-peptide sampling window. An authorized release with participant-linked measurements and domain review remains the next M4 evidence step. OT-027/0.2 specifies one M5 prognostic question, its data requirements, a synthetic visit-linkage preflight, a pinned public-dictionary crosswalk and a fixed [invented prognostic comparison](docs/m5-synthetic-prognosis.md); human-data review, empirical freeze, human prognostic evaluation and therapy evidence remain open. Further C1 original-method development and B1 remain conditional optional studies. P1's verified external-method contract remains bounded to the declared rate-controller task; wider compatibility needs separate evidence. None of these areas waits for the later independent M2 reproduction, but that original acceptance item stays open.

### Non-P1 planning review, 27 September 2026

No owner is assigned to the following external steps. The listed local artifacts can be checked without participant records; an external gate stays open until its own evidence is recorded. No outreach or data-access application follows from this planning review.

These are evidence milestones, not a pause on internal implementation. Select further local work by a concrete tool use or defect and verify it internally; do not present another synthetic run as a substitute for the missing observation or independent review.

| Work package | Local bounded deliverable and status | Next evidence artifact | External gate or conditional decision |
| --- | --- | --- | --- |
| OT-023 / LIT-001–002 | Source-linked Cambridge parameter ancestry and a [concentration-comparison boundary](docs/lit002-tutorial.md#source-linked-concentration-comparison-boundary) added; original study records show a plasma-peak versus model-appearance endpoint gap; unchanged synthetic comparison retained | Inspect full experimental methods and numerical derivation where accessible; select a versioned concentration dataset/protocol only if permitted and suitable | Product/delivery identity, body mass/history, insulin assay and rights must be verified before human fitting or scoring; CGM-only data cannot directly assess absorption |
| OT-026 / M4 | [BC-006 synthetic source audit](docs/research/m4-source-audit-results.md#local-verification-follow-up-27-september-2026) repeats with an identical reconstructible report; BC-015 public metadata and sampling checks remain the current observation preparation | Versioned same-challenge glucose/insulin/C-peptide linkage and independent domain-review disposition | Authorized paired observations, assay/treatment context, population-specific basal/scale calibration and reviewer interpretation are absent; further synthetic recovery does not close them |
| OT-017 / M3 | Ohio, AZT1D and PhysioCGM software preparation remains synthetic or authorization-bound as documented under M3; worker deadlines now use bounded subprocess waits with retained partial-output checks | Source-specific rights/variable assessment, split freeze and permitted held-out report | Suitable authorized observations and release-specific time/units/participant-overlap checks are needed for an empirical claim |
| OT-027 / M5 | Public CIT-07 field review, invented join rehearsal, review packet and synthetic prognosis are complete | Authorized release linkage and written domain-review decisions, followed by a participant-disjoint empirical protocol if feasible | Actual same-person function/insulin-burden coverage, repeat-infusion handling, assays, treatment context and rights are unverified |
| M2 external acceptance | Internal software and IV-001 verification are complete | Another person's frozen-checkout execution and deviation record | An independent human executor is needed for the original M2 acceptance criterion |

C1, B1 and V1 remain optional studies. Each needs its own newly declared question and freeze; B1 additionally needs suitable reserved observations, and V1 needs compatible frozen candidates. None is a prerequisite for the local source, numerical or data-contract work above.

### Delivered preparation and remaining evidence work

- [x] Add a separate [AZT1D protocol](docs/research/m3-azt1d-protocol.md), phase-bound importer and [causal development preparation](docs/m3-azt1d-tutorial.md), verified with synthetic cases. The separate study runner adds isolated fitting, a learned freeze, durable access history, evaluation and artifact reconstruction. Preserve the original Ohio rules and the private allocation; actual-release policy binding and authorized human evaluation remain open.

- [x] Specify [M3/1](docs/research/m3-protocol.md): a conditional OhioT1DM CGM-only 30-minute forecast question, Ridge/persistence comparison and causal evaluation rules. [Feasibility](docs/research/m3-data-feasibility.md) records publicly checked documentation and unresolved native release/rights; this is not an executable human-data freeze.
- [x] Add a separate [AZT1D protocol](docs/research/m3-azt1d-protocol.md), phase-bound importer and [causal development preparation](docs/m3-azt1d-tutorial.md), verified with synthetic cases. The separate study runner adds isolated fitting, a learned freeze, durable access history, evaluation and artifact reconstruction. Preserve the original Ohio rules and the private allocation; actual-release policy binding and authorized human evaluation remain open.
- [x] Deliver the bounded OT-024 [question/evidence dossier](docs/research/m4-evidence-dossier.md): candidate references, measurement/rights gaps and an [unsent domain-review brief](docs/research/m4-collaboration-brief.md). Actual human-data access and domain review remain open; no partnership or contact is claimed.
- [x] Specify the relevant OT-015 [secretion boundary](docs/research/m4-protocol.md) and [future coupling](docs/research/m4-coupling.md): units, route, ownership, initialization, baseline, identifiability and checks. Evidence narrows the implemented question to evoked release under declining IVGTT glucose. Effects on glucose and external insulin remain a later coupled question.
- [x] Add the bounded [BC-003 C-peptide reference](docs/research/m4-cpeptide-results.md): published equation/stimulus replay, synthetic known-input recovery, simpler comparator and concrete [measurement/review needs](docs/research/m4-cpeptide-measurements.md). No human concentration-curve reproduction or validation.
- [x] Specify and execute the bounded [BC-004 paired input/baseline preflight](docs/research/m4-paired-results.md) with a conditional measurement protocol and source-specific review packet. Its historical boundary result is preserved; paired trajectories follow in BC-005 and human review remains open.
- [x] Execute the bounded [BC-005 paired kinetic experiment](docs/research/m4-paired-kinetics-results.md): nonzero initial insulin inventories, shared synthetic input, separate locked workers, independent calculations, conservation, superposition, numerical refinement and reconstructible outputs. This does not close glucose-feedback or human-assessment criteria.
- [x] Complete the bounded [BC-006 internal source audit](docs/research/m4-source-audit-results.md): document pancreas/basal conventions, quantify the pre-bolus initialization hypothesis and observation multiplier, and verify the reduction distinctions. Author confirmation and external domain review remain open; no historical model is changed.
- [x] Execute the bounded [BC-007 prescribed-glucose chain](docs/research/m4-chain-results.md): fresh unchanged secretion reference, one-time molar transfer, paired kinetic outputs, source-sampling refinement and reproducible artifacts. Glucose stays imposed; OT-026 remains partial.
- [x] Specify [BC-008 glucose feedback](docs/research/m4-feedback-protocol.md) and execute [BC-008-P1 readiness checks](docs/research/m4-feedback-readiness.md): select a static/dynamic source, distinguish portal transit, preserve basal plasma insulin by explicit route replacement and freeze controls/criteria. No coupled trajectory or human assessment is claimed.
- [x] Execute [BC-008 bounded glucose feedback](docs/research/m4-feedback-results.md): separate analytic source reference, same-stage liver coupling, native/constant/equal-arrival controls, two mass balances, solver/replay refinement and exact fresh-process repetition. Biological/observation assessment remains open.
- [x] Assess the two hepatic assumptions in [BC-009](docs/research/m4-hepatic-results.md): primary-source review, baseline-matched extraction/portal-EGP comparison, unchanged BC-008 control, independent balances and reproducible artifacts. This tests structural sensitivity; population calibration, expert review and independent observations remain open.
- [x] Execute [BC-010 feedback-source C-peptide observation](docs/research/m4-feedback-observation-results.md): direct molar pancreatic appearance, independently checked kinetics/baseline, source-sampling and wrong-boundary diagnostics, unchanged parent outputs and fresh-process repetition. Joint/human identifiability remains open.
- [x] Execute [BC-011 joint synthetic recovery](docs/research/m4-joint-identifiability-results.md): 36 analyses, known/unknown clearance, shared noisy observations, nested sampling, local sensitivity/refinement, both-start recovery and exact full repetition. Exact k3 non-observability without Cp and noisy bound-hitting fits remain visible. This does not establish human/global identifiability.
- [x] Execute [BC-012 volume sensitivity](docs/research/m4-volume-sensitivity-results.md): 60 analyses and 120 starts with a complete fresh-process repeat, unchanged observations/dynamics, fixed-correct/fixed-wrong/estimated volume and matched GI controls. Wrong fixed volume can yield biased low-residual fits; free volume reduces noisy precision despite resolved local rank. BC-013 follows with conditional profiles; independent kinetic information and human assessment remain open.
- [x] Execute [BC-013 conditional profiles](docs/research/m4-profile-likelihood-results.md): nine cases and 27 curves, nuisance reoptimization, fixed-volume/GI/slice controls, every detected crossing refined, reference-solver refits and complete fresh-process repetition. Interest and nuisance bounds remain visible; nominal contours are not demonstrated confidence coverage.
- [x] Prespecify and execute [BC-014 independent synthetic coverage](docs/research/m4-coverage-results.md) after BC-013: 96 new noise realizations, 224 gain analyses across paired interior designs and a separate boundary diagnostic, planned-denominator failure accounting, Wilson intervals, reference-solver checks and exact full repetition. No threshold calibration, human validation or domain review is claimed.
- [x] Execute [BC-015-P1 metadata-only paired-measurement readiness](docs/research/m4-measurement-readiness.md): a frozen source-level contract, strict executable evidence accounting and a reconstructible CIT-07 core FSIGT gap report. Two requirements are supported, five unverified and one contradicted; this is not a human-data evaluation or access grant.
- [x] Execute [BC-015-P3 targeted alternate-source screen](docs/research/m4-alternative-observation-screen.md): compare nearby public CIT catalogues and audit the source-pinned NCT01817959 aggregate MMTT record for all three analytes, visit labels and denominators. Preserve the 120-minute label discrepancy and unequal counts. This supplies neither linked IV observations nor permission for human model evaluation.
- [x] Execute [BC-015-P4 synthetic C-peptide window stress](docs/research/m4-sampling-window-results.md): compare documented early timing against hypothetical late C-peptide additions under a known synthetic pulse, with 64 paired noise draws, independent analytical checks and exact repetition. This does not establish CIT-07 secretion input or human identifiability.
- [x] Prepare [OT-027/0.2 islet-function question and data feasibility](docs/research/m5-cell-therapy-protocol.md), with a separate [source-screening contract](docs/research/m5-cell-therapy-data.md). It proposes a prognostic comparison for later insulin burden and identifies the mechanism and evidence gates; no source-specific empirical freeze, therapy software or treatment claim follows.
- [x] Complete the [OT-027-P2 CIT-07/08 public-source screen](docs/research/m5-cit07-feasibility.md): align a candidate 75-day mixed-meal function landmark with a one-year seven-day diary insulin summary, distinguish first/final infusion clocks, retain repeat-infusion confounding and avoid beta-score contamination of the isolated function predictor. Public metadata do not establish eligible linked participants, rights or treatment benefit.
- [x] Implement the [OT-027 synthetic visit-linkage preflight](docs/m5-release-preflight.md): check the candidate first-infusion clock, paired MMTT availability, seven consecutive diary days, repeat infusions and complete-roster issue accounting with reconstructible invented examples. It does not accept or assess a human release.
- [x] Complete the [OT-027-P3 public-dictionary crosswalk](docs/research/m5-cit07-dictionary-crosswalk.md): pin five CIT-07 documents, map repeat-infusion and IEQ-order fields, and distinguish the mean-insulin interval start from an MMTT or outcome visit day. Actual same-visit linkage and diary coverage remain unverified.
- [x] Rehearse the [OT-027 source-shaped CSV joins](docs/m5-native-rehearsal.md) on invented rows: compare transplant counts/orders, candidate day-75 function rows and seven-day insulin intervals while preserving missing cases and additional infusions. The tool rejects human inputs and leaves challenge, visit, diary and cohort eligibility unverified.
- [x] Prepare the [OT-027-P4 scientific review packet](docs/research/m5-domain-review-brief.md) with explicit transplant, assay, kinetics and statistical decisions, release-stage evidence requirements and an empty review record. No external review or empirical freeze has occurred.
- [x] Audit the [OT-027-P5 public CIT-07 forms and laboratory manual](docs/research/m5-cit07-form-lab-audit.md): distinguish visit 15 from first-infusion Y1, identify routine versus conditional MMTT sampling and confirm dated self-reported insulin entries. Released visit codes, day-75 missingness and seven-day mean linkage remain unverified.
- [x] Implement the [OT-027 fixed synthetic prognostic comparison](docs/m5-synthetic-prognosis.md): demonstrate development-only fitting and person-disjoint paired scoring of a baseline and an added observed-function index, with Y1/V15 separation, missingness and intervening infusions visible in a reconstructible invented report. Human fitting, an empirical freeze and therapy evidence remain open.
- [x] Add the [M5 researcher workflow](docs/m5-researcher-workflow.md) under [M5-RESEARCHER/1](docs/research/m5-researcher-protocol.md): accept a hash-bound trusted Python source and frozen state on the unchanged 32 invented participants, retain projected landmark inputs and fresh-worker repeats, compare paired coverage and error with the development-only baseline, and reconstruct without importing candidate code or refitting. Self-attested training/rights, independent usability, human loading, empirical model freezing and treatment evidence retain separate gates.
- [ ] Verify an authorized versioned dynamic paired release, assay/renal/treatment fields and a participant-disjoint allocation; obtain independent domain review and freeze a population-specific empirical protocol before fitting or held-out scoring.
- [ ] Complete OT-025 beyond its implemented equation references: [BC-001](docs/research/m4-results.md) verifies published theoretical functions and synthetic dynamics; exact published dynamic reproduction remains unresolved because the cohort input is missing and paper/code initializations differ.
- [ ] Advance OT-027 beyond its public-source and synthetic screens: verify one authorized versioned release and its participant/visit/infusion linkage, confirm or revise the 75-day/one-year candidate and exact diary-burden definition, obtain domain review, and freeze a participant-disjoint empirical assessment before fitting. Do not label simulated secretion a cure.
- [x] Write the separate [C1/0.1 design protocol](docs/research/c1-controller-protocol.md): select missing scored-day meal announcements as one falsifiable question, assess candidate families and native references, define the causal contract and zero-margin outcome constraints, and separate inspected development evidence from a future evaluation. No algorithm or improvement result is selected; OT-019 still needs a sealed exact roster and remaining statistical/numerical criteria before tuning and assessment.
- [x] Select the [C1/0.2 method and native feasibility boundary](docs/research/c1-method-feasibility.md): a causal trend overlay with an unconfigured simulator-independent kernel and tests. M2 remains immutable; strong simglucose feedback comparison, C1 native adapters and the exact evaluation freeze remain open.
- [x] Implement the [C1/0.3 simglucose development route](docs/c1-simglucose-development.md): connect the trend overlay and adapted bounded PID to known M1 cases without changing historical code, record base/correction/final actions and native status, and reconstruct case artifacts without simglucose. Clean-commit examples show adverse non-degradation directions in one known case; strong-comparator eligibility, Cambridge and the evaluation freeze remain open.
- [ ] Before adaptation or tuning, freeze the respective development and evaluation rules, failure policy, uncertainty analysis and numerical criteria. Record feasibility blockers and the next executable work if data or a supported comparison is unavailable.

These deliverables specify the next experiments; they do not authorize data-access applications, messages to third parties or patient-data downloads by themselves.

## M3 — External evaluation and bounded personalization

**User outcome:** a researcher can evaluate existing models against selected human observations and distinguish reconstruction, prediction and intervention replay.

**Software status:** the current bounded researcher forecast intake and synthetic preparation routes are implemented and internally verified. Broader human-observation acceptance remains open. [M3/1](docs/research/m3-protocol.md) and its [executable synthetic workflow](docs/m3-tutorial.md) implement a bounded existing Ridge/persistence CGM forecast study. The [acceptance record](docs/research/m3-reproduction.md) maps each criterion. Human evaluation, native release verification and applicable rights remain open. Existing physiological engines are explicitly unsupported for this CGM-only application; their human accuracy remains unassessed.

- [x] Implement the separate [external frozen-model route](docs/m3-external-tutorial.md) under [M3-EXTERNAL/0.1](docs/research/m3-external-protocol.md): portable verified model export, metadata-only external cohort freeze, no refitting, access history, failure accounting and offline reconstruction. Its evaluation boundary accepts synthetic observations only.
- [x] Add [PhysioCGM human pre-scoring preparation](docs/research/physiocgm-external-freeze-protocol.md): bind completed private conversion and reconstruction evidence, all ten normalized exports, unchanged donor model and fixed analysis rules. Preserve the limited four-file donor metadata check, source-bound read history and explicit disabled human-scoring gate; this implements preparation, not a human forecast result.
- [x] Implement the separate [PhysioCGM execution route](docs/research/physiocgm-execution-protocol.md): new authorization-bound plan, unchanged original freeze, supervised and exclusively claimed workers, complete-roster failure accounting and private numerical reconstruction. Verify the mechanics with invented observations; actual human execution and its results remain a separate step.

- [x] Implement a separate [researcher forecast intake](docs/m3-researcher-forecast.md)
  under [M3-RESEARCHER/0.1](docs/research/m3-researcher-protocol.md): frozen
  trusted Python source/settings, exact causal six-value CGM input,
  30-minute prediction, persistence and complete synthetic participant/origin
  accounting. Reconstruct retained windows and metrics without original
  inputs or candidate execution. This does not independently replay an
  arbitrary supplied algorithm or close human evaluation and intended-user
  acceptance.

The separate [M3-EXTERNAL/0.1 preparation](docs/m3-external-tutorial.md) adds transfer of an already frozen model to a new synthetic cohort without refitting. It preserves exact timing rules and defines external reporting eligibility without a development requirement. This historical evaluator continues to reject human input.

[PhysioCGM source review](docs/research/physiocgm-source-assessment.md) records v1 metadata, dataset rights and the completed authorized private CGM audit. The separate [human conversion protocol](docs/research/physiocgm-conversion-protocol.md) adopts the full raw-export period and explicit clock/status/availability assumptions. Its [workflow](docs/physiocgm-intake-tutorial.md) binds source and code evidence before native reads, retains all ten planned cases and reconstructs private conversion artifacts. This conversion plan is not an external model/cohort freeze and does not execute model evaluation.

[M3-PHYSIOCGM-EXTERNAL/0.1](docs/research/physiocgm-external-freeze-protocol.md) adds a separate pre-scoring bridge from the completed conversion to an unchanged donor. It checks existing conversion/reconstruction evidence, privately snapshots all ten normalized exports, fixes the complete origin schedule and analysis rules, and records access before reads. The donor seal checks only the original plan, fit state, learned freeze and model; it does not repeat development/validation verification or claim a complete historical export. The [execution supplement](docs/research/physiocgm-execution-protocol.md) implements a separate authorization-bound execution plan, worker supervision and private reconstruction, tested with invented observations. The original freeze remains disabled and unchanged; human scoring has not been performed as part of this software step. Different source studies do not establish verified participant independence.

- [x] Implement a separate [PhysioCGM timing follow-up](docs/research/physiocgm-timing-protocol.md) with fixed zero-, one- and five-second matching, exact-reference checks, nested comparisons and a bounded synthetic demonstration. Preserve historical sources and results; the intended human follow-up is post hoc, and its protected preparation/execution route remains open.

- [ ] Turn the M0 data assessment into one reproducible workflow with documented access, usage, processing and redistribution rights.
- [ ] Check units, timestamps, glucose compartments, sensor semantics, missingness, meal records, delivery versus commands and participant overlap. Unknown inputs remain unknown; select a narrower question if essential variables are absent.
- [ ] Freeze participant/time/study splits appropriate to the intended claim before fitting. Fit preprocessing and calibration on development data only; specify which observed history may initialize each prediction.
- [ ] Evaluate relevant behavior against external observations and a suitable simple predictor. Separate fixed-model evaluation from personalization; where useful, reproduce a bounded calibration or ReplayBG workflow with explicit identifiability assumptions.
- [ ] Reserve evaluation material and report error, uncertainty, coverage, exclusions and failures by relevant condition. Account for repeated measurements within participants rather than treating every timestamp as an independent person.
- [x] Implement simulator-free reconstruction and the [synthetic mechanics example](docs/m3-tutorial.md). Reconstruction of actual human results remains conditional on execution and permitted artifact retention.

**Acceptance:** a reproducible evaluation measures predictive strengths and limitations on held-out observations, with no tuning leakage. A negative result can complete the research question. Historical observations describe the treatment actually given; matching them does not establish the effect of another controller's actions.

**Dependency:** suitable data and rights, plus the relevant model interface. A synthetic example can complete software preparation but cannot close human-data evaluation. M3 evaluation data become known material after inspection; B1 must preserve an untouched assessment for its subsequent model changes or explicitly label later reuse exploratory.

## C1 — First original OpenT1D controller

**Status: historical study; optional continuation.** The original user outcome was to run an original control method and assess a specific improvement hypothesis against strong published references. This research record remains intact, including its negative findings and unfinished comparison gates. Under [decision 0045](docs/decisions/0045-tool-first-research-platform.md), selecting a replacement original method or completing this efficacy study is optional and requires a new declared work package. The reusable external-controller intake belongs to P1.

**Preparation:** [OT-018 / C1/0.1](docs/research/c1-controller-protocol.md)
selects the missing-meal question and comparison boundaries. It is a design
protocol, not a frozen OT-019 evaluation. [C1/0.2](docs/research/c1-method-feasibility.md)
selects a bounded trend overlay and verifies only its unconfigured causal
kernel. [C1/0.3](docs/c1-simglucose-development.md) adds a simglucose
development adapter and adapted PID comparison on known cases. The
[C1/0.4 known-case matrix](docs/research/c1-known-development-matrix.md)
completes 64 synthetic attempts, preserves an overlay low-glucose regression
and finds no B in-range gain after a targeted adjustment; the PID outcome
reversals prevent calling it a strong comparator. The
[C1/0.5 failure audit](docs/research/c1-method-revision.md) retires
the first overlay as lead and specifies a bounded two-sided feedback family
with a matched engineering comparator. [C1/0.6](docs/research/c1-feedback-kernel.md)
implements and checks the unconfigured, simulator-independent feedback
kernel and zero-rise comparator. [C1/0.7](docs/research/c1-feedback-development.md)
adds their native simglucose adapter and completes one matched 48-run
known-case development matrix. Candidate/base benefit is mixed, so method
development, a strong comparator and the evaluation freeze remain open.
[C1/0.8](docs/research/c1-feedback-diagnostic.md) audits the sealed action
timing and threshold flows without a simulator, and declares a one-factor
target-alignment plan with equal new setting budgets. [C1/0.9](docs/research/c1-target-alignment-results.md)
executes its 48 known native cases and fails the prespecified B and A
advancement gates in adult#001/102. Both feedback methods have spent their
two cumulative setting attempts. Further known-case setting search calls
for a new method assessment and declaration; strong-comparator, Cambridge
and exact evaluation work remain open.
[C1/1.0](docs/research/c1-method-comparator-review.md) completes the
simulator-free cross-round audit, retires the present feedback family as
lead and selects a preflight to pin and assess the OpenAPS reference source
as the next C1 implementation package. No M1 strong comparator has yet
qualified; a replacement original method remains unselected.
[C1/1.1](docs/research/c1-oref0-preflight.md) pins and executes that
source preflight. The upstream basal tests pass, but its committed example
does not match the current CLI output; dependency locking and M1 causal,
clock and temp-basal fidelity remain open. It is not an eligible comparator.
[C1/1.2](docs/research/c1-oref0-example-history.md) checks the example's
introduction and both 0.7 releases under a recorded runtime: none matches
the committed suggested output. A separate locked current-source baseline
passes and permits simulator-free adapter work; causal inputs, persistent
temp-basal fidelity, dependency rights, matched budget and M1 comparator
eligibility remain open.
[C1/1.3](docs/research/c1-oref0-adapter-boundary.md) verifies synthetic
source-native IOB from explicit pump receipts and a bounded temp-basal
projection. It shows that M1 commands are not confirmed delivery and that
five-minute source decisions can split M1's three-minute actions. The
information/timing interface, causal glucose and profile mapping and strong
comparator eligibility remain open; no native outcome matrix is run.
[C1/1.4](docs/research/c1-comparator-route.md) makes the unchanged `oref0`
route a tested no-go on this M1 interface and selects G2P2C for a conditional
source-feasibility route. Its pinned causal CGM/command and rate-action
boundary passes simulator-free checks, but source checkpoints are absent and
the source training default uses five-minute CGM. Three-minute policy
training or verified transfer, full source-policy parity, stale-CGM behavior,
matched budget and comparator eligibility remain open; no native outcome
matrix is run.
[C1/1.5](docs/research/c1-g2p2c-state-parity.md) replays the pinned G2P2C
state class in a separate locked NumPy environment. Sixteen synthetic
three-minute frames, history wrap, selected-feature isolation and reset match
the causal M1 boundary exactly after source `float32` conversion. The actor
checkpoint, three-minute training/transfer, inference and matched-development
gates remain open; this replay makes no comparator-effectiveness claim.
[C1/1.6](docs/research/c1-g2p2c-actor-boundary.md) executes the pinned
source actor on causal synthetic M1 inputs with a separate locked CPU
environment. It verifies sampled-action parity, isolated RNG/reset, strict
hash-bound weights-only checkpoint intake and failure atomicity using random
weights; no policy is trained or scored. Three-minute training/transfer,
checkpoint provenance, missing-CGM policy and fair comparator eligibility
remain open.
[C1/1.7](docs/research/c1-g2p2c-training-preflight.md) rejects the bundled
G2P2C simulator as M1-equivalent because its meal equation and termination
limits differ. A separately locked M1-engine, three-minute source debug loop
passes 4,096 interactions. This is training integration only: physical-time
settings, full budget, checkpoint selection, causal verification, matched
development comparison and comparator eligibility remain open.
The separate [core-runtime check](docs/research/c1-g2p2c-training-preflight.md#m1-numeric-runtime-parity)
verifies matching locked and installed M1/C1 simglucose, NumPy, SciPy,
pandas, gym, pathos and python-dateutil versions; it does not replay a
native trajectory. A separate fixed-action engine replay now matches all
201 M1 snapshots byte-for-byte across the two locked environments, including
the first meal; it does not test a trained controller.
[C1/1.8](docs/research/c1-g2p2c-training-freeze.md) fixes one source
training attempt per known adult profile, the three-minute physical-time
settings, terminal checkpoint rule and an exclusive-output launcher that
seeds before actor construction. Two fresh-process short runs repeat actor
weights. A separate actor-constructor check confirms matching settings,
initialized tensors, source forward outputs and weights-only cross-source
loading for both profiles. Both full training attempts and trained actor
intakes now pass. A separately frozen matched development matrix remains open.
[C1/1.9](docs/research/c1-g2p2c-missing-cgm.md) specifies a 30-minute
profile-basal fallback for masked M1 CGM and a causal actor-history restart
on the first fresh reading. Synthetic callback and weights-only checks pass;
trained-policy native cases, full comparator eligibility and the separate
matched development freeze remain open.
[C1/1.10](docs/research/c1-g2p2c-native-smoke-plan.md) freezes two known M1
native integration cases and checks completion, sensor fallback and action
bounds, with simulator-free replay and fresh-process repeats, without an
efficacy comparison. Both 960-interval native cases pass saved verification
and byte-identical repeats. The combined technical readiness audit passes;
adult#001's early execution relative to the both-checkpoint instruction is
recorded. A separate matched development freeze remains open.

The following gates apply **if the original-controller study is resumed**;
they are not prerequisites for the platform's external-method workflow.

- [ ] Prespecify the target conditions, primary benefit, acceptable degradation limits for other outcomes, uncertainty method and failure policy before tuning. Include low-glucose exposure, in-range exposure, extreme outcomes and native stops as relevant to the question; a single favorable average is insufficient.
- [ ] Assess candidate methods against that task without preselecting MPC, machine learning or a hybrid. Record source ancestry, configuration, rights and the original contribution.
- [ ] Define causally available observations, meal announcements, profile information, history, initialization, action units and modeled delivery. Verify reset, internal finite state, action limits and behavior with missing observations.
- [ ] Reproduce suitable strong comparators under equivalent information and development budgets where meaningful. Native Cambridge MPC alone does not establish a fair cross-engine comparator.
- [ ] Develop on declared cases; freeze code, settings and analysis before evaluation. Previously inspected M2 and IV-001 cases are known development evidence, not a new untouched test set. New seeds alone do not create an unseen physiological population.
- [ ] Evaluate supported configurations in both existing model families. Retain separate tracks where compartments, populations or information differ, and expose incompatible combinations instead of forcing a pooled ranking.
- [ ] Report uncertainty, coverage, losses, stops, numerical sensitivity and reversals; reconstruct the complete comparison from saved artifacts.

**Conditional C1 acceptance:** if this optional original-method study resumes, the controller implementation and a reproducible two-family evaluation must be complete. Superiority is a separate verdict requiring the prespecified benefit and non-degradation criteria; failure to meet them is recorded as a negative or inconclusive result, not a successful improvement. Unsupported required comparisons remain open. Simulation performance does not establish treatment benefit in people.

**Dependency:** the verified M2 interfaces and a defensible protocol/comparator set. M3 completion is not required for bounded simulation development. Existing Cambridge/MPC numerical sensitivity, initialization effects and singleton population limit the claims and must be addressed in the new experiment design.

## B1 — Optional original physiological-model study

**Conditional user outcome:** if evidence justifies an original physiological change, a researcher can assess whether it predicts unseen observations better than existing alternatives. This study is not required to provide biological-model integration tools.

- [ ] Select one limitation identified using M3 development evidence, with a proposed mechanism, suitable measurements and a falsifiable improvement hypothesis.
- [ ] Compare the unchanged model, parameter-only calibration and the proposed structural change under the same permitted inputs and evaluation rules. Record parameter identifiability and the effect of removing the new component.
- [ ] Preserve ancestry, units, compartments and ownership of physiological processes. Check coupling, quantities, limiting behavior, reset and numerical refinement; avoid duplicate absorption, secretion or delay processes.
- [ ] Freeze model structure, parameters, fitting procedure and analysis before the reserved assessment. A dataset already inspected to select the change cannot also substantiate an untouched evaluation claim.
- [ ] Measure predictive errors, uncertainty, coverage and regressions on unseen observations; preserve the original model and all failed variants as evidence.

**Acceptance:** the candidate and comparison are reproducible. Label it an improvement only if it meets the prespecified criteria on held-out human observations without unacceptable regressions. Otherwise retain the negative result and do not promote the candidate as a better physiological model. A better glucose fit alone does not establish that an inferred mechanism is biologically correct.

**Dependency:** a measured limitation, suitable data/rights and an identifiable bounded question. A complete replacement engine is not required; an original engine may grow from independently supported changes.

## V1 — Optional cross-evaluation of candidate model and controller

**Conditional user outcome:** a researcher can distinguish a controller effect, a physiological model change and their interaction when compatible frozen candidates exist. Candidates may come from external researchers; neither an OpenT1D controller nor an OpenT1D physiological model is required for the platform.

| Physiological model | Controller | Purpose |
| --- | --- | --- |
| Existing | Existing reference | Retained baseline |
| Existing | Candidate controller | Test the controller outside the candidate physiology |
| Candidate physiology | Existing reference | Characterize the changed model under established control |
| Candidate physiology | Candidate controller | Assess their interaction |

- [ ] Freeze candidates and a new cross-evaluation protocol before running the reserved comparisons; specify supported cells and information equivalence.
- [ ] Execute the matrix across the applicable existing families and new model. Keep population and compartment differences explicit; a shared profile number is not a paired patient.
- [ ] Report interaction effects, per-condition coverage, uncertainty, reversals and failures. Missing or scientifically incompatible cells prevent the corresponding attribution claim.
- [ ] Maintain the B1 assessment against real observations separately. Favorable closed-loop simulations do not validate the body's response to unobserved interventions.

**Acceptance:** evidence identifies which conclusions persist outside the combined OpenT1D system and which depend on the model/controller pairing. No joint tuning on the final evaluation or universal-best claim is permitted.

**Dependency:** compatible frozen candidates, supported boundaries and evaluation material not used to choose the candidates. A specific original C1/B1 study may supply candidates, but is not required.

## P1 — First usable research product

**User outcome:** a researcher or algorithm developer can independently connect a supported controller, execute an experiment and understand a reconstructible report.

**Current software status:** [P1/0.1](docs/p1-research-workflow.md) packages
one supported, fixed M1 development task over native simglucose, basal-bolus
and PID into eight scheduled cases. [P1/0.2](docs/p1-external-controller.md)
adds one hash-bound, researcher-supplied rate controller under four synthetic
M1 conditions, with source-only action replay and simulator-free report
reconstruction. [P1/0.3](docs/p1-upstream-pid-tutorial.md) verifies the
source-pinned upstream simglucose PID through that intake. This method is
already the M1 PID reference; it does not extend scientific method coverage.
[P1/0.4](docs/research/p1-internal-followup.md) repeats that PID on the
second supported profile/seed pair and verifies a distinct, source-pinned
GlucoSim proportional basal agent through the unchanged intake. The latter
uses released CGM only and converts upstream U/hour to P1 U/min.
These routes are locally executable from an identified checkout. P1's
**internal technical verification is complete**, including four synthetic
cases per declared run, action replay and
report reconstruction. The methods' causal inputs, units, clocks, held-CGM
behavior, rate bounds and results are recorded in the
[PID verification packet](docs/research/p1-upstream-pid-verification.md) and
[P1/0.4 follow-up](docs/research/p1-internal-followup.md).
The [P1 acceptance packet](docs/research/p1-product-acceptance-review.md)
also records a clean-worktree facilitator rehearsal of the intended-user
commands; it does not close the independent-user gate.
An authorized human reviewer has conditionally cleared one exact Git bundle
for a named-researcher internal technical exercise, while retaining the
unverified table-level provenance and excluding broader distribution. No
independent tester is currently available; independent intended-user
execution, broader compatibility and P1 product acceptance remain open. The G2P2C two-profile
smoke does not establish a general interface or fair comparator.
Pen/discrete-dose support requires a separate capability decision.

**Next bounded increment:** identify an intended researcher who did not build
P1, record the named recipient under the conditional rights decision, and
have them independently perform and interpret the
[P1 acceptance exercise](docs/p1-acceptance-exercise.md) with the distinct
GlucoSim source. Record actual problems and deviations using the
[acceptance packet](docs/research/p1-product-acceptance-review.md). Only after
the independent record exists can a maintainer decide product acceptance.

- [x] Implement and locally execute the first bounded P1 researcher task with
  locked installation, explicit supported choices, complete run accounting
  and reconstructible report. Retain clinical and scientific claim limits.
- [x] Implement a bounded local researcher-supplied rate-controller intake
  on M1 with a versioned causal contract, capability and declaration checks,
  four-case failure accounting, replay and reconstruction. The included
  invented source is an interface example, not a third-party method.
- [x] Verify one source-pinned third-party controller through this contract:
  upstream simglucose PID source hash, method-specific arithmetic and
  held-CGM behavior, four synthetic cases, action replay and report
  reconstruction. It is the existing M1 reference and remains bounded by
  P1 rates; no efficacy comparison follows.
- [x] Repeat the pinned PID on `adult#002`/seed `102` and verify a distinct
  pinned proportional basal source on `adult#001`/seed `101`, with explicit
  U/hour-to-U/min conversion, native tests, four-case accounting, action
  replay and report reconstruction. These synthetic exercises do not rank
  the methods or establish broad controller compatibility.
- [x] Complete human source, parameter and distribution-rights review for
  the exact internal technical Git-bundle offering. The authorized reviewer
  approved a conditional transfer to one named researcher; table-level
  provenance remains unverified and public, runtime and output distribution
  remain outside this decision.
- [ ] Select one intended user and task; define the minimum installation, configuration, execution and reporting workflow. Assess usability with actual intended users rather than assuming demand.
- [ ] Deliver the [OT-058 Windows installer](#planned-windows-installer-ot-058)
  and verify independent installation/startup without user-managed GitHub,
  WSL, Python or terminal commands; retain the developer checkout route.
- [ ] Provide canonical instructions, worked examples, meaningful errors, supported-combination guidance, versioned outputs and clear distinctions between implementation, simulation evidence and human-data evidence.
- [ ] Record code, parameter and data rights for the intended distribution and use; distinguish original contributions from upstream components. Define support and maintenance expectations.
- [ ] Obtain independent execution of the product workflow and retain outcome/deviation records. Keep the original M2 reproduction criterion separately traceable to its frozen protocol; a different product exercise does not automatically close it.
- [ ] Review the evidence supporting every product claim. Evaluate commercial interest separately; passing tests does not demonstrate willingness to pay.

**Acceptance:** an intended user can independently complete and interpret the declared research workflow, with a reviewed evidence/rights package. Development can precede external participation, but this acceptance cannot be self-certified by CI or another agent. A UI, stable API, hosted service or release is not claimed until actually delivered for the selected workflow.

**Dependency:** a bounded usable workflow and rights to use its integrations. Original-model/controller claims additionally require their own C1/B1/V1 evidence if pursued. Personal treatment advice or device control requires a separate intended-use, safety, clinical and applicable regulatory development plan; P1 does not authorize it.

## Parallel biological research and later extensions

M4 and M5 retain their identifiers and provide biological research-tool preparation alongside P1 and M3. Their implementation advances when a specific question and suitable evidence justify it; neither is gated by completing original-controller or device development. M6 remains a later, question-dependent integration path. Device, activity and formulation extensions are selected by their research question rather than milestone number. Exploratory work must identify hypothetical mechanisms and unsupported predictive claims.

## M4 — Residual secretion and beta-cell function

The new [OT-053–056 observation-analysis plan](#planned-mixed-meal-analysis-tasks)
selects two related MMTT tasks as the next product increment. Its offline
analysis contract and empirical evidence are separate from the completed
synthetic M4 routes and historical acceptance items below.

**User outcome:** a researcher can use attributed model and coupling tools to explore how different levels of endogenous insulin secretion affect modeled glucose and external insulin requirements, while seeing where source and empirical evidence remain insufficient.

**Status and sequence:** standalone references and the configured researcher secretion/C-peptide workflow are implemented and internally verified. The broader M4 biological milestone remains incomplete. [BC-001](docs/research/m4-results.md) begins the reference sequence. OT-024 evidence/measurement feasibility and the relevant OT-015 specification are delivered. OT-025 has numerical equation verification and reconstructed theoretical relationships; [BC-003](docs/research/m4-cpeptide-results.md) adds a completed forward C-peptide equation/stimulus reference and synthetic identifiability. Exact published dynamic cohort reproduction remains partial. OT-026 has an executed [BC-002 kinetic-only inlet](docs/research/m4-kinetic-results.md), including native equivalence, conservation, communication refinement and simpler baselines. [BC-004](docs/research/m4-paired-results.md) verifies the paired input and proposed initial-state contract; [BC-005](docs/research/m4-paired-kinetics-results.md) now executes both kinetic branches with synthetic basal inventories and independent numerical checks. [BC-006](docs/research/m4-source-audit-results.md) narrows source gaps with a numerically checked pre-bolus initialization hypothesis and explicit basal/observation scale; author confirmation and population calibration remain open. [BC-007](docs/research/m4-chain-results.md) now joins a fresh BC-001 execution to both kinetic outputs, including source-sampling refinement and equal-amount comparison. [BC-008-P1](docs/research/m4-feedback-readiness.md) selects a source suited to rising/falling glucose and verifies basal arithmetic. [BC-008](docs/research/m4-feedback-results.md) now implements the independently checked source and bounded monolithic glucose feedback, with native, constant and equal-arrival controls, conservation, solver/replay sensitivity and exact fresh-process repetition. [BC-009](docs/research/m4-hepatic-results.md) adds a scoped primary-source assessment and a separate baseline-matched comparison of variable hepatic extraction and direct portal EGP action. [BC-010](docs/research/m4-feedback-observation-results.md) observes the pancreatic source through the unchanged C-peptide kinetics, with separate input/initial-state ownership and sampling/boundary verification. [BC-011](docs/research/m4-joint-identifiability-results.md) now verifies conditional joint sensitivity and synthetic parameter recovery under known basal G/I and fixed non-varied physiology, showing that local rank and noiseless recovery do not ensure stable noisy estimates. [BC-012](docs/research/m4-volume-sensitivity-results.md) adds fixed-correct, fixed-wrong and estimated C-peptide volume to the unchanged model and observations, with matched GI controls and explicit rate/volume distinctions. [BC-013](docs/research/m4-profile-likelihood-results.md) now quantifies conditional nuisance-reoptimized profiles, with fixed-volume/GI/slice controls, reference-checked crossings and explicit interest/nuisance-bound limitations. [BC-014](docs/research/m4-coverage-results.md) now assesses conditional synthetic pointwise gain inclusion on independent noise draws, with explicit Monte Carlo precision, numerical gates and a separate boundary diagnostic. [BC-015-P1](docs/research/m4-measurement-readiness.md) now identifies the CIT-07 core FSIGT metadata gap without importing patient data. [BC-015-P2](docs/research/m4-cit07-public-crosswalk.md) verifies public dictionary fields: subject/day keys are documented, but a same-challenge dynamic glucose/insulin/C-peptide crosswalk is not. [BC-015-P3](docs/research/m4-alternative-observation-screen.md) audits one alternate public registry source: aggregate mixed-meal values have neither participant linkage nor IVGTT compatibility. [BC-015-P4](docs/research/m4-sampling-window-results.md) finds that hypothetical late C-peptide samples improve two-parameter synthetic kinetic recovery under a known pulse; it does not validate the CIT-07 IVGTT. The conditional human measurement protocol remains unexecuted and unreviewed externally. Biological interpretation, broader coupling assessment and independent observation assessment remain open. No T1D, transplant or therapy validation is claimed.

The [researcher-supplied secretion workflow](docs/m4-external-secretion.md)
now adds a bounded tool path on BC-007's unchanged synthetic glucose
challenge. It checks one hash-declared local source, paired kinetic outputs,
numerical accounting and artifact-only reconstruction against a verified
BC-007 archive. This is an internal synthetic capability; independent user
execution, biological interpretation and human evidence remain separate.

The separate [causal secretion intake](docs/m4-causal-secretion.md) now lets
one hash-declared, one-state researcher source respond to the same-stage
glucose and glucose derivative inside BC-008's existing fasting and gastric
load tasks. The host retains basal replacement, portal transit and liver
arrival. A BC-008-equivalent adapter, constant-basal control, two numerical
solvers, fresh-process repeat and artifact reconstruction have been checked
internally. The fixed SC schedule does not estimate external insulin need;
multi-state models, real-user compatibility and biological evidence remain
open.

The [synthetic basal-equivalence task](docs/m4-synthetic-basal-equivalence.md)
now varies only the fixed post-zero SC infusion against a prespecified BC-008
meal AUC while keeping source basal and initial states fixed. Its example
adapter matches at the 75% starting rate; the smaller-beta/K parameter
variant has no solution in the 50–100% domain. These are bounded numerical
results, not an external insulin requirement for a person. Other outcomes,
model families, population calibration and human evaluation remain open.

The [independent Mari 2002 compatibility preflight](docs/research/m4-independent-source-preflight.md)
finds that the complete multiple-meal method cannot faithfully enter the
current one-state causal callback: its potentiation trajectory is fitted from
the complete glucose/C-peptide experiment, and the published output scale
and basal relation are not mapped to the host contract. This source audit
produces no adapter or feedback trajectory. The next internal gate is to
source a prospective potentiation rule or a different complete causal source
component, then decide from its equations whether a versioned input/state
contract is needed. The following worked example completes that bounded
source-component gate; empirical and biological claims keep their separate
evidence requirements.

The [ultradian f1 worked example](docs/m4-ultradian-secretion.md) now implements
the complete stateless sigmoid response specified by Karamched et al. (2021),
with Sturis ancestry, nominal shape parameters and explicit synthetic basal
normalization. Assigning the original plasma-input response to the host
pancreatic/portal inlet is an exploratory route adaptation. Independent
equation and portal checks, the unchanged fasting/30 g load comparison,
two solvers, fresh-process repetition and artifact-only reconstruction pass.
This is a different sourced response structure; it does not reproduce the
full ultradian physiology or validate a prehepatic human secretion rate.
No contract extension, patient data or external sign-off was needed.

The [ultradian SC-equivalence example](docs/m4-ultradian-basal-equivalence.md)
now verifies that distinct response in the unchanged frozen search task.
Both solvers confirm all five prescribed grid points and an `unbracketed`
result within 50–100% native SC infusion. A source-pinned artifact report
retains meal AUC, peak, nadir and final glucose, with a separate unchanged
causal run for fasting at the 75% starting factor and exact shared-anchor
parity. Complete fresh-process repeats and source-free reconstruction pass.
No equivalent rate, wider-domain search, human insulin requirement or new
source calibration is inferred.

The [configured M4 researcher workflow](docs/m4-researcher-workflow.md) now
connects a supplied causal source to the unchanged feedback route and forward
C-peptide observation, then produces one reconstructible report for the
intended researcher task. [Decision 0052](docs/decisions/0052-m4-researcher-workflow.md)
preserves the source, units, initialization and separate numerical runtimes.
The [M4-RESEARCHER/1 execution record](experiments/m4/researcher_workflow/execution.json)
retains passing runs for the existing Dalla Man and ultradian structures,
exact fresh-process repeats, a rejected negative-rate source and byte-identical
simulator-free reconstruction of all three report artifacts. This completes
the bounded internal composition increment while authorized observations and
review remain pending. A subsequent interface extension needs a concrete
researcher model/task; this work does not replace P1's independent-user
acceptance priority or satisfy M4's biological acceptance criteria.

- [x] Begin with a limited functional question: prescribed declining post-bolus glucose to evoked secretion.
- [x] Offer one bounded researcher-owned secretion input on the fixed BC-007 challenge, with source identity and reconstructible insulin/C-peptide comparisons; wider interfaces and empirical claims remain open.
- [x] Offer a separate causal one-state researcher source on BC-008's fixed synthetic feedback scenarios, with explicit portal and basal ownership, numerical controls and reconstructible outcomes; this does not estimate an insulin dose or establish human validity.
- [x] Compare fixed post-zero SC infusion rates on one frozen synthetic meal-AUC target, retaining no-solution cases, numerical controls and reconstructible search histories; do not infer a clinical insulin requirement.
- [x] Audit one genuinely independent published secretion method against the causal intake, document the incompatible potentiation/scale/basal requirements, and state a source-first internal implementation gate without claiming a model run.
- [x] Source and preflight a complete prospective causal secretion response component, then verify it on invented feedback scenarios: the ultradian f1 example preserves its full sigmoid shape with explicit amplitude and route adaptations; the existing interface suffices. Full-engine and broader model compatibility remain open.
- [x] Verify that structurally different source on the frozen SC-equivalence task, preserve its no-solution outcome and report glucose-shape and starting-factor fasting diagnostics with unchanged sources, protocol and initial states.
- [x] Deliver one configured causal source-to-glucose/insulin/C-peptide workflow; both existing source structures, exact repeats, preserved failure and readable report/figure reconstruction pass bounded internal checks under M4-RESEARCHER/1.
- [ ] Select a published secretion or C-peptide model and appropriate dynamic observations. Published reduced IVGTT and forward C-peptide models are selected; suitable authorized observations remain unavailable.
- [x] Define the proposed endogenous delivery route, compartments, extraction and process ownership in the [OT-015 boundary](docs/research/m4-coupling.md); the kinetic inlet is implemented in BC-002; biological applicability remains open.
- [ ] Verify the module and its coupling; assess plausible limits and numerical behavior. Standalone numerical verification is complete within BC-001 and BC-003; BC-002 verifies insulin-only coupling, BC-005 verifies paired insulin/C-peptide kinetics including nonzero initial inventories, and BC-007 verifies the prescribed-glucose source-to-output chain. BC-008 verifies bounded metabolic feedback under its frozen synthetic protocol; BC-009 quantifies two hepatic structural assumptions with preserved baselines and numerical controls. BC-010 verifies the forward C-peptide observation of pancreatic feedback output; BC-011 independently checks the equilibrium-conditioned joint wrapper and inverse-analysis numerics. Broader biological plausibility remains open.
- [x] Distinguish functional capacity from anatomical beta-cell mass; BC-001 capacity is an explicitly hypothetical common amplitude multiplier.
- [ ] Evaluate identifiability and compare against a simpler model without the extension. Standalone amplitude confounding and zero-capacity baseline are demonstrated; BC-002 adds zero/equal-amount kinetic baselines and linear amplitude scenarios. BC-003 adds synthetic known-input kinetic recovery, dose/volume confounding and a one-compartment comparator; BC-005 verifies zero-input, washout and basal-superposition comparisons; BC-007 adds half/full evoked scaling and an equal-amount constant comparator to the prescribed-glucose chain. BC-008 adds numerically resolved synthetic glucose contrasts and an equal-arrival timing diagnostic; BC-009 adds a four-variant structural comparison and identifies paired kinetic/tracer observation needs; BC-010 adds paired synthetic observations and a conditional appearance/volume ambiguity; BC-011 adds restricted joint local sensitivity and synthetic recovery, including explicit unobservable parameters and noisy bound hits. BC-012 isolates central-volume misspecification and conditional recovery without establishing an empirical volume distribution. BC-013 adds conditional nuisance-reoptimized objective contours, including bound-limited regions and interior endpoints affected by nuisance bounds; BC-014 adds independent conditional synthetic gain-profile inclusion frequencies but does not establish human confidence coverage. BC-015-P4 compares early and hypothetical late C-peptide sampling for a known synthetic pulse with fixed exchange and volume; it does not establish IVGTT human identifiability. Global/human identifiability, broader nuisance physiology and biological glucose assessment remain open.
- [ ] Obtain domain review for the biological interpretation and record its scope.

**Acceptance:** the functional question, evidence and limitations are explicit; the coupling is checked; and the contribution of the extension is assessed. If evidence is incomplete, release only a clearly exploratory scenario capability.

**Dependency:** a verified suitable metabolic engine and coupling. Completing all personalization or device work is not a prerequisite. A secretion scenario does not establish that a therapy produces that secretion.

## Extension path — Devices, activity and insulin formulations

**User outcome:** a researcher can evaluate one additional mechanism relevant to delivery or control.

Choose a specific sensor/pump behavior, activity mechanism or insulin kinetic model using a concrete question and available measurements. Reproduce the standalone reference; specify the device version or formulation, route and population; then verify the coupled effect on glucose and control. Check for duplicated absorption, delay or noise.

**Literature preparation:** [OT-023 / LIT-001](docs/research/lit001-results.md) has an executed bounded landscape/search, conventional-lispro source and parameter dossier, audit of both pinned engines and standalone synthetic verification of published equations. Missing source inputs prevent claiming exact published patient/cohort reproduction. This work proceeds alongside M3 and C1; it does not identify an absorption mechanism from M3/1 CGM forecasts or satisfy B1's human-evaluation criteria. Parameter ancestry remains open. The separately specified [LIT-002 experiment](docs/lit002-tutorial.md) adds a bounded native Cambridge coupling and a mean-transit-matched comparator under synthetic inputs; it does not establish human validity or close B1.

**Acceptance:** the implemented behavior and coupled application have relevant evidence. A brand name or a changed parameter alone does not constitute a validated product model.

## M5 — One defined cell or immune therapy question

**User outcome:** a researcher can use protocol, data-compatibility and analysis tools to evaluate one treatment-related hypothesis with an evidence package, if suitable authorized observations and domain review become available.

**Software status:** the current bounded frozen-source researcher prognosis workflow and synthetic preparation are complete. The broader M5 empirical and treatment-evidence milestone remains open.

**Status and sequence:** [OT-027/0.2](docs/research/m5-cell-therapy-protocol.md) prepares one islet-transplant question: whether an observed post-graft function measure improves prediction of later documented insulin burden over a simpler baseline. Its [data contract](docs/research/m5-cell-therapy-data.md) distinguishes source metadata from authorized participant-level verification. The [CIT-07/08 public-source screen](docs/research/m5-cit07-feasibility.md) narrows the candidate to a 75-day mixed-meal observation and a one-year seven-day diary insulin summary after the first infusion, while retaining repeat-infusion and beta-score predictor-contamination risks. A [synthetic visit-linkage preflight](docs/m5-release-preflight.md) exercises the proposed structural rules with invented availability records and a reconstructible report. The [public-dictionary crosswalk](docs/research/m5-cit07-dictionary-crosswalk.md) pins the native infusion and insulin-window meanings; the [public form/laboratory audit](docs/research/m5-cit07-form-lab-audit.md) separates visit 15 from first-infusion Y1 and identifies conditional day-75 sampling. A [fixed invented prognosis run](docs/m5-synthetic-prognosis.md) now checks a baseline-versus-function pipeline with person-disjoint evaluation; its toy metric is not human evidence. The [scientific review packet](docs/research/m5-domain-review-brief.md) states the decisions and evidence needed from transplant, assay, kinetics and statistics reviewers; it is unsent and unreviewed. The actual release linkage, independent review, empirical freeze, human prognostic evaluation and treatment evaluation remain open. The current M4 gain is not a graft-survival or therapeutic mechanism. Choose a different entry question if available evidence supports it better; no access or collaboration is claimed.

The [M5 researcher workflow](docs/m5-researcher-workflow.md) extends that
invented task to a researcher-owned frozen prognostic source and JSON state,
under the separate [M5-RESEARCHER/1 protocol](docs/research/m5-researcher-protocol.md)
and [decision 0054](docs/decisions/0054-m5-frozen-prognostic-intake.md).
Its standard-library workers receive only landmark predictor fields;
source/state hashes and training declarations bind the local bundle.
Reports retain all 32 roster entries, two attempts per eligible held-out
participant, full-baseline and paired errors, incomplete coverage and
repeat infusions. Reconstruction verifies saved baseline normal equations
and report arithmetic without importing the candidate or refitting.
This bounded tool adds no human loader, rights adjudication, empirical
freeze, independent usability or treatment-effect claim.

For cell therapy, a first question may relate graft functional capacity and its decline to metabolic outcomes. For immune therapy or progression, choose a disease stage, intervention and endpoint matched to available study data. These are alternative entry points, not a requirement to model all immunity first.

- [ ] Specify the intervention mechanism, target population and permissible claim before extending the model.
- [ ] Reproduce a relevant reference with its original limitations.
- [ ] Evaluate against an independent intervention, study or suitable held-out material.
- [ ] Compare with a simpler reference and report sensitivity to unsupported mechanisms.
- [ ] Publish the permitted protocol, software and results with a separate evidence record.

**Acceptance:** the intervention claim is supported by appropriate independent evidence. Re-fitting the study used to build the model is insufficient.

**Dependency:** the mechanisms and data needed for the selected question; cell-therapy applications will usually build on suitable secretion/capacity modeling. Whole-immune-system completeness is not an entry requirement.

## M6 — Selected multiscale integration and AI research

**User outcome:** a researcher can answer a defined question better by connecting scales or using computational experiment design.

Select only the scales required by that task. Assess coupling intervals, delays, balances and feedback against finer references. Adopt SBML/CellML, SED-ML/OMEX, PEtab or FMI for concrete exchange needs and verify compatibility.

Profile actual experiments before GPU or distributed optimization. Add parameter search, surrogates, experimental design or reinforcement learning when there is a meaningful baseline and evaluation protocol. Preserve reproducibility and assess performance beyond the development cases.

**Acceptance:** additional complexity or automation provides demonstrated value with characterized uncertainty. This is a recurring research program, not a single final release promising a universal digital twin.

## Initial work packages

These identifiers are local planning references, not GitHub issue numbers.

| ID | Work package | Dependency | Deliverable |
| --- | --- | --- | --- |
| OT-001 | Finalize the first protocol | Foundation | Question, scope, information, outcomes and failure rules |
| OT-002 | Audit engines, ancestry and asset rights | OT-001 | Candidate comparison and exact source revisions |
| OT-003 | Reproduce first upstream scenario | OT-002 | Locked environment, input, output and provenance |
| OT-004 | Decide integration boundaries and reuse | OT-002, OT-003 | Decision record, including second-family assessment |
| OT-005 | Specify time, units, observations and actions | OT-001, OT-003 | Contracts with valid and invalid examples |
| OT-006 | Build first adapter | OT-004, OT-005 | Direct-versus-adapted reference comparison |
| OT-007 | Add reference controllers | OT-005, OT-006 | Equivalent information conditions and reset checks |
| OT-008 | Implement metrics and failure handling | OT-001, OT-005 | Independently calculable reference cases |
| OT-009 | Add meal and sensor variants | OT-006, OT-007 | True events and observable information separated |
| OT-010 | Build manifest and report generation | OT-006, OT-008 | Report reconstructed from stored artifacts |
| OT-011 | Verify clean installation and reconstruction | OT-007, OT-009, OT-010 | Reproduction record and tutorial |
| OT-012 | Prepare first bounded demonstration | OT-011 | Reviewable release candidate and limitations |
| OT-013 | Assess real data and define external evaluation | OT-001; runs alongside OT-002–OT-012 | Variables, rights, gaps and a testable evaluation plan |
| OT-014 | Exercise contracts with second model family | OT-004, OT-005, OT-010 | Compatibility and meaningful cross-model experiment |
| OT-015 | Specify first residual-secretion coupling | OT-005, OT-006 and OT-024 evidence assessment; no M3/C1 completion gate | Functional question, process ownership and evidence plan |

## Follow-up work packages

These local identifiers continue the original work-package list without renumbering milestones or creating GitHub issues. Decision 0045 changes future priorities, not the meaning or results of past work. M3 preparation is implemented within its stated synthetic scope; cure-oriented packages have the bounded status recorded below. Execution retains the separately stated evidence gates.

| ID | Work package | Dependency | Deliverable |
| --- | --- | --- | --- |
| OT-016 | Specify M3 question and data feasibility | OT-013, M2 interfaces | Versioned protocol, rights/variable assessment, splits and blockers |
| OT-017 | Implement and execute M3 evaluation | OT-016, suitable authorized data | Reproducible processing and held-out prediction report |
| OT-018 | Specify historical C1 hypothesis and comparators | M2, IV-001 findings | [C1/0.1 design protocol](docs/research/c1-controller-protocol.md) delivered; method selection followed in C1/0.2. The original-method evaluation freeze remains an OT-019 gate only if that optional study resumes |
| OT-019 | Optional original-controller study; historical development retained | OT-018 and a newly declared study decision before more tuning | C1/0.2–1.10 results remain preserved, including negative original-method rounds, unchanged-OpenAPS no-go and trained two-profile G2P2C technical integration. A fair strong M1 comparator, replacement original method, Cambridge, exact freeze and two-family assessment remain open; none blocks P1 |
| OT-020 | Optional physiological-model improvement | Measured limitation, suitable reserved observations and separate study decision | If pursued, unchanged/calibrated/modified comparison and held-out assessment; not a tool-platform prerequisite |
| OT-021 | Optional candidate cross-evaluation | Compatible frozen candidates and supported interfaces; OT-019/020 are possible sources, not requirements | V1 matrix, attribution limits and reconstruction for the declared methods |
| OT-022 | Deliver the first research product workflow | Selected user/task and supported components | P1/0.1 fixed workflow, P1/0.2 local intake, P1/0.3 pinned upstream PID and P1/0.4 second-profile/distinct-controller checks complete the bounded internal technical scope; human rights review conditionally clears one exact internal handoff, while the independent-user exercise remains open, without claiming a general host |
| OT-023 | Map literature and assess a lispro kinetic reference | Existing research/model cards; complete source specification and usable rights additionally required for reproduction | [LIT-001](docs/research/literature-research-plan.md) evidence dossier, engine audit, reference-feasibility verdict and conditional standalone reconstruction |
| OT-024 | Assess the first cure-oriented question, evidence and collaboration needs | Existing research standards; preparation independent of original C1 work | Question/population/endpoint dossier, candidate model and measurement inventory, rights/access gaps, domain-review brief and feasibility verdict |
| OT-025 | Reproduce a standalone secretion or C-peptide reference | OT-024, relevant OT-015 specification, usable source/assets | Attributed reference implementation, numerical checks, parameter provenance and separate synthetic versus empirical evidence |
| OT-026 | Couple and assess beta-cell function | OT-015, OT-025, suitable verified metabolic engine; observations required for empirical claims | Coupling checks, identifiability and simpler-baseline comparison, reconstructible scenarios and a conditional independent-observation assessment |
| OT-027 | Specify and conditionally evaluate one M5 therapy question | Preparation alongside OT-024; execution requires the chosen mechanisms, authorized observations and frozen protocol; cell applications usually need OT-026 | Treatment/population/endpoint protocol, data feasibility, independent assessment plan and, only when executed, an evidence report |
| OT-028 | Update task-first navigation and software/evidence status | Completed bounded P1/M3/M4/M5 workflows | Canonical start page and aligned summaries; documentation updated in this planning increment |
| OT-029 | Add a common local entry for four supported researcher tasks | OT-028 and unchanged task contracts; decision 0055 | Implemented and internally verified checkout launcher, metadata/runtime check, explicit run/reconstruction and report discovery; representative success/failure checks; OT-030/031/032 add the fifth, sixth and seventh registered routes |
| OT-030 | Compare multiple frozen predictors on one synthetic M3 task | Existing M3 researcher route, OT-029 entry and the separately frozen comparison protocol | Implemented and internally verified coordinator, per-candidate coverage/persistence assessment, common-support comparisons and model-free reconstruction |
| OT-031 | Compare multiple frozen secretion sources on one synthetic M4 task | Existing M4 researcher workflow and OT-029 entry; frozen M4-COMPARISON/1 and decision 0057 | Implemented coordinator, roster/configuration checks, identical-condition glucose/insulin/C-peptide comparison, full failure accounting and one report/figure; native execution and simulator-free reconstruction internally verified locally under the linked evidence record |
| OT-032 | Configure one synthetic M4 initial gastric-load study | Frozen M4-STUDY/2 and unchanged causal/observer equations and locks | Implemented and internally verified: 0/15/30 gram study, controls, numerical parity/refinement/repeats/failures and reconstruction |
| OT-033 | Run small frozen local campaigns | OT-032 intake/runner/reader | Implemented and internally verified: frozen matrix/repetitions/budgets, retained attempts, explicit resume/reuse and tamper refusal |
| OT-034 | Index and verify local archives | Explicit supported task readers | Implemented and internally verified: metadata filters, seven-route reconstruction verification and conservative exact-condition repeat eligibility |
| OT-035 | Pilot a GUI for one research route | Maintained M4 execution successor and decision 0059 | Implemented and locally internally verified: configuration/check/setup/run/cancel/report/reconstruction, native CLI parity and retained failed-study evidence; independent usability remains open |
| OT-036 | Add one question-driven model type or coupling | Concrete question, suitable source/rights and versioned boundary | Conditional: attributed native reference and controlled comparison |
| OT-037 | Simplify task-directed locked setup | Explicit registry and unchanged numerical locks | Implemented and internally verified on macOS: passive plan/check, explicit locked install and readiness; broader platform/user acceptance remains open |
| OT-038 | Run maintained M4 campaigns | `m4-study-secure`, MAINTAINED-CAMPAIGN/1 and decision 0060 | Implemented and internally verified: frozen ordered matrices, retained attempts, sealed sessions, identity-checked resume, failure accounting and model-free reconstruction |
| OT-039 | Browse explicitly registered scientific archives in the GUI | Declared read-only roots and fixed supported catalogue/readers | Implemented and internally verified: eight-task metadata and maintained M4 reports; OT-043 adds fixed M3 forecast/comparison verification and corrected schema-aware claims; originals and snapshot freshness remain explicit, other historical tasks retain compatible-reader requirements |
| OT-040 | Manage own-workspace campaigns in the GUI | Accepted OT-038/039 and fixed maintained CLI/readers | Implemented and internally verified: frozen study cells, explicit check/setup, run/cancel/resume, complete slot/attempt/session accounting, native CLI parity and report reconstruction; independent usability remains open |
| OT-041 | Preserve maintained experiments outside disposable worktrees | OT-038–040, fixed authoritative readers and decision 0061 | Implemented and internally verified locally: byte-exact bounded packages, full trusted-reader identity, integrity checks, fresh restore, GUI export/registration and model-free reconstruction after removal of the original execution worktree; partial accounting preserved, no historical artifact recovery |
| OT-042 | Expose synthetic M3 forecasts and frozen-candidate comparisons in the GUI | Existing M3 CLI, OT-030 comparison, OT-041 storage and decision 0062 | Implemented and internally verified locally: bounded preparation, check/run/cancel, native reports, explicit M3 durable readers, five literal relocated reconstructions, raw unsealed retention and M4 regression; independent use and empirical evaluation remain open |
| OT-043 | Correct catalogue claim roots and browse native M3 reports in the GUI library | OT-039/042, existing native readers and decision 0063 | Implemented and internally verified: schema-aware recorded claims, fixed M3 library reports/downloads, actual retained M3/M4/durable cases and 1246 passing local tests; included in local main on 5 October 2026 and GitHub main through PR #33 on 6 October; hosted checks and independent researcher use remain open |
| OT-044 | Browse and verify native synthetic M5 prognostic reports in the GUI library | Existing M5 researcher CLI, OT-043 library and decision 0064 | Implemented and internally verified locally: original JSON/Markdown, all 32 people and both evaluation attempts, bound supplier declarations, native null/paired support, preserved originals, actual browser parity and M3/M4/durable regressions; full locked checks pass with separately recorded C1 skips; integrated into local and GitHub main on 6 October 2026 and worktree/branch cleanup complete; hosted verification remains open, GUI execution and human evaluation excluded |
| OT-045 | Prepare one complete GUI test packet | Existing GUI exercise, source bundle and complete/interrupted native M4 references | Implemented, internally verified and integrated into main through PR #35: bound source bundle, private Dutch cards, offline canonical guides and native complete/interrupted references; actual handoff review remains open; see the [usability plan](#planned-usability-work) |
| OT-046 | Simplify first installation and local startup | Identified tester platform, existing locked setup and local GUI | Installation/check/start files integrated into main through PR #35; fresh macOS receiving checkout verified, Windows/WSL syntax and controlled calls checked; actual Windows host verification is next, with clean-system installation, networking and lifecycle acceptance still open |
| OT-047 | Make session observations easy to record | Existing exercise criteria, observation CSV and blank session records | Implemented, internally verified and integrated into main through PR #35: local/private worksheet, bounded export/restore and separate retest records with empty outcomes; no manual JSON editing or feedback API |
| OT-048 | Execute the first human GUI usability session | OT-045/047 and identified tester; OT-046 only for independent-installation assessment | Technically prepared; actual human execution/observations remain open for the standard synthetic M4 task; preinstalled use and novice feedback do not imply installation or intended-user acceptance |
| OT-049 | Fix observed usability problems and retest | Actual OT-048 observations and identified fix candidates | Retest form prepared; actual observed fixes and human retests remain open and must follow real OT-048 findings; retain original records and remaining limitations |
| OT-050 | Resolve eight internal GUI usability findings | Internal agent walkthrough of main 6cbc8c9; original private observations retained | Implemented, internally retested and integrated into local/GitHub main through PR #37 on 14 October: eight scoped fixes, real complete/cancelled M4 runs, nine identical reconstructed artifacts and locked 1,282-test checks; CI skipped at the maintainer's request; hosted verification, Windows and human OT-048/049 gates remain open |
| OT-051 | Resolve five findings from the second internal UI/UX review | Internal review of main 84f7b99; preserved private observations | Implemented and internally verified in codex/uiux-round2-fixes, integrated into main on 17 October with maintainer-requested [skip ci]; all five browser retests passed, including fresh synthetic M3 and narrow layouts; 1,288 tests with 13 existing C1 skips; hosted CI intentionally skipped; external platform/human gates remain open |
| OT-052 | Explain the product and research questions on the GUI start page | Existing synthetic M3 and maintained M4 workflows | Integrated into main on 17 October 2026 with [skip ci]: virtual-lab introduction, two explicit research questions, example inputs and report contents, accessible Explore actions and invented-data scope; local browser/navigation checks; actual Windows/WSL and human comprehension testing remain open |
| OT-053 | Establish feasibility for two related MMTT analysis tasks | Tool-first direction, decision 0066 and source/data/comparator assessment | Complete: controlled narrow dossier cd10cb0 and handoff 4f38f01 adopted; fixed-kinetic synthetic preparation permitted; authorized adult pairs, human kinetics and researcher benefit remain unconfirmed |
| OT-054 | Build a shared observation-analysis core and Task 1 | OT-053 technical source/scope feasibility; rights and empirical freeze additionally required for human use | Implemented and internally verified within OT-053 narrow scope: shared fixed-kinetic synthetic core, paired CLI/GUI reports, full failure accounting and archive reconstruction; [OT-054 record](docs/research/ot054-verification.md); controlled estimator/uncertainty retained; Task 2 required-time admission follows decision 0069; empirical and independent user-value acceptance remain open |
| OT-055 | Assess information loss from fewer MMTT measurement times | OT-054 shared core; appropriate dense observations and frozen participant split for empirical assessment | Implemented and internally verified within the synthetic boundary: shared-core raw-subset refits, CLI/GUI, failure-aware comparisons, native catalogue reconstruction and reusable case packet; [OT-055 record](docs/research/ot055-verification.md). Empirical and independent user-value acceptance remain open |
| OT-056 | Compare both tasks with existing researcher tools | Usable OT-054/055 workflows, strong baselines, frozen criteria and actual intended users | Technically complete within synthetic scope: controlled handoffs, 22-case CLI/notebook chain, GUI/readers, independent answers, isolation/failure controls and relocated reconstruction; final 1,390-test locked check passes. Six-researcher pilot across two teams, independent review and product decision remain open |
| OT-057 | Resolve seven observed MMTT UI/UX problems | Internal four-example walkthrough of main 9e8078f; OT-054/055 native workflows | Integrated into local and remote main at ac94080 with [skip ci], verified 22 October: all seven fixes, both browser recovery routes, four native reconstructions and a passing 1,393-test locked check with 13 existing skips. [Verification record](docs/research/ot057-uiux-verification.md); Windows/human usability and empirical acceptance remain open |
| OT-058 | Install and start OpenT1D through one Windows installer | Existing GUI/runners/readers, declared Windows/workflow scope, runtime distribution rights and process/packaging design | Candidate J: build, host payload audit and host checks passed. The original upgrade test phase remains failed despite a late full payload audit pass and confirmed normal stop; graphical Finish/browser startup were observed separately. Separate CompleteUpgrade passed a fresh full audit, preserved all 366 original files and passed 18 native tests without skips. One synthetic 32-draw MMTT API case and its fresh reader passed. Repair passed with a fresh reader and unchanged original reports; Reinstall also passed, starting with the application running. A separate clean J baseline passed offline installation, shortcut reuse and one 32-draw MMTT API/reader workflow; an agent separately viewed its healthy Start page, results library and report. Current J also passed 124 native Windows tests with six declared skips, no failures/errors and a full post-test payload audit; selected-file attestation passed separately. The five-person, four-schedule sampling-information-loss API case passed at 32 draws, with fresh readers and unchanged reports across restart. A genuine sampling cancellation and fresh interrupted-report readers passed without forced cleanup or survivors. No active numerical-job maintenance is claimed. I's initial native failure, unchanged warm retry pass and M4/maintenance failures remain preserved. Attempt 09 M3 remains unresolved after its environment loss. Recovery attempt 10 passed licensed clean installation from the genuine Edge download, healthy automatic first GUI startup, shortcut reuse, normal exit and 124 native tests with six declared skips plus a full payload audit. A fresh root-operated GUI 32-draw Task 1 MMTT analysis and reconstruction passed with unchanged original reports; a separate sampling-information-loss API case passed with fresh readers. New synthetic M3 forecast/comparison runs and readers passed. Actual native-started M3 cancellation and forensic byte-copy retention passed their bounded scope; integrity/reconstruction remain false and completeness unknown. Attempt 09 M3 remains unresolved. Explicit user authorization resolved activation. The new Campaign and M4 tests failed at fixed 600-second reference-worker deadlines before candidate source evaluation; cancellation/resume/fresh-reader campaign gates remain unmet. A separate native-library phase passed for the three available M3/sampling inputs, with full metadata and nine original jobs collected and independently reviewed. Two M3 durable-package API routes passed export/integrity/reconstruction across restart (ten jobs). Separate 14-check launcher/session controls passed with two held native-zero normal stops. Remaining GUI observations closed with a new M3 export and Task 1 external archive index/reader/visibility/exit proof; two raw-retention receipts are fully host-preserved without member-body export or integrity/reconstruction claims. Eleven-case lifecycle preparation passed within its independently reviewed preparatory scope. The first Maintain test failed on an Unsafe root path before launch. Maintain02 installed graphically, refused concurrent launch, passed full payload audit and preserved original data, but its report wrapper failed on an output-filename collision; original phase remains failed. Separate GET-only report comparison and normal stop passed their targeted gates, with the full comparison report independently verified; the failed Maintain02 outcome is unchanged and that phase did not prove active numerical cancellation. The original Uninstall05 and later observer failed. Separate controlled cancellation during observed native analysis, post-removal payload/data/registration checks and eleven fresh retained-case readers passed; all 7,023 original data files were unchanged at the post-removal check, and all 22 original report hashes were preserved by the reader run. Earlier private-controller/preflight failures remain recorded. These targeted gates do not relabel the original failed phases. Full maintenance acceptance remains open. A separate fresh I-to-J upgrade passed its full J payload audit, original-case preservation, fresh J reader, 18 native checks and normal stops. The preservation check found 93 of 95 original files byte-identical, exactly two precomputed verification-bookkeeping transitions and zero additions; both original reports remained identical. Original InstallI, admission-wrapper and guard-controller failures remain recorded. This bounded upgrade pass does not complete OT-058 or remaining workflow/release gates. The candidate is unsigned; public SmartScreen reputation and full VM/TPM restore validation remain open. Remaining MacBook tests, complete Windows workflow/lifecycle acceptance, independent use and release remain open. See the [verification record](docs/research/ot058-installer-verification.md) and [delivery plan](#planned-windows-installer-ot-058). |
| OT-059 | Contracts, capabilities and extraction fixtures | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-060 | Installable SDK/CLI and route migration | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-061 | Portable execution and runtime management | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-062 | Two native adapters and conformance kit | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-063 | Scenarios, comparisons and uncertainty | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-064 | Projects, results, readers and private handoff | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-065 | Common task workbench and onboarding | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-066 | Campaigns, stage cache and resource budgets | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-067 | Biological/observation tasks on shared services | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-068 | Owned-data fit/freeze/evaluate chain | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-069 | Mechanistic composition and calibration | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Conditional proposal; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-070 | Selective standards bridge | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Conditional proposal; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-071 | Optional external executor | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Conditional proposal; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-072 | Independent second/third-task acceptance | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-073 | Maintained distribution and release practice | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |
| OT-074 | External extensions and continuity | See the [canonical package dependencies](#planned-core-and-product-work-packages) | Planned; acceptance is defined in the common laboratory delivery plan, not established by this document |

OT-016 is specified in M3/1, conditional on authorized release verification. OT-017 software preparation is implemented; its human-data execution remains conditional. [OT-018/C1/0.1](docs/research/c1-controller-protocol.md) specifies the historical missing-meal controller question and comparison design. OT-019 preserves C1/0.3–1.10 development and G2P2C integration results, including negative original-method findings and technical-only comparator readiness. A replacement original method, fair strong comparison, exact freeze and evaluation remain open; further original-method work is optional under decision 0045. OT-022/P1 has completed its bounded internal technical scope and a conditional human rights review for one internal handoff; product acceptance awaits an independent intended-user run. OT-024 and the relevant OT-015 specification are delivered in BC-001; OT-025 adds a completed BC-003 forward C-peptide equation/stimulus reference but remains partial for exact published dynamic cohort reproduction, and OT-026 is partial: BC-002 implements verified incremental insulin kinetics, BC-004 checks a paired observation boundary and BC-005 executes both kinetic branches including synthetic basal inventories and BC-007 composes the complete prescribed-glucose chain, while BC-008 implements and numerically verifies bounded glucose feedback following its separate source tests and native preflight. BC-009 assesses two hepatic assumptions with primary sources and a matched structural comparison; BC-010 adds a verified C-peptide observation branch. BC-011 executes restricted joint synthetic sensitivity/recovery; BC-012 tests C-peptide volume misspecification; BC-013 executes conditional nuisance profiles; BC-014 adds independent conditional synthetic profile coverage. BC-015-P1–P4 record public-source measurement gaps and a hypothetical synthetic sampling-window contrast. Human observation assessment, biological interpretation, population calibration and external domain review remain open. OT-027/0.2 has a question/data preparation protocol, synthetic visit-linkage preflight, public-dictionary crosswalk and fixed invented prognostic comparison, not a verified release crosswalk or therapy evaluation. No release date, human predictive performance or cure outcome is promised.

OT-023's [bounded execution](docs/research/lit001-results.md) includes recorded screening/access gaps, source extraction, a pinned-engine audit and a passing synthetic published-equation example. Exact clinical-curve reproduction and independent human scientific review remain open. It adds a literature route to the existing insulin-formulation extension without changing the historical acceptance criteria of M3, C1 or B1. Future allocation follows the tool-first priorities above.

## Acceptance for each milestone

State who can do what, which research question it serves, what has actually been demonstrated, which uncertainty remains and whether another person has reproduced it. Track implementation and evidence separately when necessary.

Preserve model, parameter, data, protocol and analysis versions; justify numerical tolerances; account for failed runs; reconstruct primary results automatically; document permitted distribution and original authorship. No milestone is complete merely because the code runs or the interface accepts a module.
