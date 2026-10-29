# OpenT1D roadmap

**Updated 29 October 2026.** This is the canonical implementation order for
OpenT1D. The immediate public-development queue comes first; the shared-laboratory
plan below retains its own dependencies and acceptance criteria. The
[historical record](docs/research/roadmap-history-2026-10-28.md) preserves earlier
plans, completed work, exact source records and detailed milestone criteria.
The [product requirements](docs/product-laboratory.md) own the research jobs and
capability requirements; task guides and verification records own working scope.

## Current position

OpenT1D is an open, modular research laboratory under development. The public
source is [OpenT1D/lab](https://github.com/OpenT1D/lab). The initial maintained
public exercise consists of two synthetic MMTT tasks: paired secretion
sensitivity and reduced measurement schedules. Other implemented research
routes and their evidence remain available for inspection under the
[public installation policy](docs/publication-security.md).

The bounded M1/M2 and P1/M3/M4/M5 workflows, MMTT analyses, GUI and archive tools
have internal verification records. They do not establish a stable general
model API, a general multiscale digital twin, independent usability, human
predictive validity or treatment benefit. No supported product release is
published. The private Windows installer is a separately verified internal
candidate with open distribution, maintenance and independent-use gates.

Source publication and the bounded public CI baseline are implemented.
[PR 9](https://github.com/OpenT1D/lab/pull/9) added the explicit public toolchain,
guarded native jobs and retained diagnostics; the
[baseline main run](https://github.com/OpenT1D/lab/actions/runs/40763325611)
passed on `c2db13a`. Main now requires the strict, app-bound `Repository checks`
result, with pull-request and conversation-resolution requirements.
[PR 13](https://github.com/OpenT1D/lab/pull/13) publishes the verified
[documentation site](https://opent1d.github.io/lab/); its actual main deployment,
navigation, search and notebook downloads were checked. [PR 18](https://github.com/OpenT1D/lab/pull/18)
adds complete dependency review and bounded monthly update discovery, with
actual causal negative and safe uv-lock probes. An
[unsigned Apple Silicon MMTT candidate](docs/mac-mmtt-candidate.md) supplies a
bundled standard-library runtime and two enforced capabilities. Signed/public
Mac distribution, independent first use and the shared SDK retain their own open
gates. The
[publication record](docs/research/publication-preparation.md) retains the initial
disabled-Actions state; the [security boundary](docs/publication-security.md)
still governs public execution. Dependency-service runs are not repository
verification.

## Public development priorities

The next product outcome is a reliable public development loop and a small
application that another researcher can use independently. Both start from the
two existing synthetic MMTT tasks. This planning change selects work; completion
requires the artifacts and checks below. Queue names are planning labels, not
new issue numbers, release versions or delivery dates. The AI-development,
public CI baseline, check-family, hosted-documentation and internal Mac-candidate
increments are implemented. Select a bounded intended-user first-use exercise
next when a participant is available. Unfinished distribution or
external-acceptance gates do not block
unrelated internal fixes, contract inventory or feasibility work.

### Now, next and later

| Order | Bounded change | Exit criterion and dependency |
| --- | --- | --- |
| Implemented internal increment — AI development | Refreshed agent guidance, canonical component/test map, issue/PR handoff and two focused repository skills. | The [trial record](docs/research/ai-development-trial.md) records existing review cases and internal numerical checks. Independent usability and productivity gains are not established. Widening the workflow requires a separate selected change. |
| Implemented internal increment — Reliability fixes | Shared POSIX publication, catalogue/setup supervision, setup process-helper identity and sampling cancellation phase checks have bounded fixes and regressions. | The cases below retain their own reproduction and verification scopes; preserve supported complete, failed and relocated results. Permanent regression tests accompany the fixes. |
| Implemented public increment — CI baseline | Reviewed checks are active with explicit Python/uv/Node setup, retained diagnostics and actual hosted runs. | The baseline main run passed and branch protection reads back the strict app-bound `Repository checks` requirement. Keep historical native execution excluded. |
| Implemented public increment — Test families and platform coverage | [PR 11](https://github.com/OpenT1D/lab/pull/11) adds named local style/tests/docs stages, one broad Linux root job, three-host public smokes, four Linux Chromium flows and one required public gate. | The final PR-head families passed; integrated-main acceptance is recorded below. Both MMTT tasks, local HTTP, filesystem/process behavior and byte-exact reconstruction have bounded actual-host coverage. The gate rejects failed, cancelled, skipped or missing public families. Broader root, browser and release coverage remains separate. |
| Implemented public increment — Dependency updates and PR review | Monthly root uv/Action updates and read-only high/critical dependency-delta review, with complete snapshot data bound to the official scan. | The [hosted probes and update-service observations](docs/publication-security.md#prepared-dependency-updates-and-pr-review) record root uv-lock coverage, dependency-driven aggregate failure, all-green safe results and successful corrected uv/Actions discovery. Generated update PRs require separate review. Historical native locks and existing alerts remain separate. |
| Implemented publication; open first-use acceptance | The reviewed-main workflow publishes [the documentation site](https://opent1d.github.io/lab/), with actual navigation, search, assets and byte-exact notebook checks. Improve first-use routes with an actual intended user when available. | A warning-free build and live-site acceptance are recorded for PR 13. Intended-user preparation, freezing, interpretation and reopening still need observed assistance, mistakes and failed attempts. User availability does not block internal fixes or packaging. |
| Implemented internal candidate — Mac application | The [Apple Silicon MMTT candidate](docs/mac-mmtt-candidate.md) bundles real pinned CPython and a native launcher for two existing synthetic tasks. | Qualify each exact artifact with repeat-build inventories, LaunchServices/browser task chains, report reconstruction, lifecycle/data-preservation checks and unchanged bundled-interpreter numerical references. Keep source/runtime/architecture/rights identities. This remains unsigned internal evidence; minimum-OS, clean-host, arbitrary upgrade and independent-user acceptance are separate. |
| Conditional follow-up — Mac distribution | Turn the verified probe into a signed/notarized download with a controlled build/release workflow and clean-host/user evidence. | The exact downloaded artifact passes the lifecycle, data-preservation and interpretation checks below. Signing credentials, runtime rights and actual hosts/users are prerequisites for the affected acceptance, not assumed resources. |
| Subsequent shared-laboratory work | Execute the named two-route extraction queue under OT-059 and minimal OT-060/061/064, followed by the remaining delivery slices. | Existing routes use shared services and preserve their scientific contracts/readers. Inventory can overlap the public work; public native execution needs a reviewed successor environment. Mac MMTT packaging is not gated on native remediation. |

[PR 11's final head run](https://github.com/OpenT1D/lab/actions/runs/40774136075)
passed on `dc4666f`: the Linux root suite ran 1,645 tests with 32 expected
platform/optional-runtime skips; all selected Linux/macOS/Windows smoke cases
passed without skips, and all four Linux Chromium flows passed. Windows ran 20 named smoke cases,
including three HTTP repetitions of each MMTT task with strict owned-process
cleanup and unchanged downloaded/reconstructed bytes. The actual worker passed
Job-membership admission before START under the current-CPython/no-site launch
convention in [decision 0079](docs/decisions/0079-windows-stdlib-worker-identity.md).
The [integrated-main run](https://github.com/OpenT1D/lab/actions/runs/40775999066)
on `a70f79e` also passed the root job, all three host smokes, all four Chromium
flows and the final required `Repository checks` gate.

The [29 October integrated-main run](https://github.com/OpenT1D/lab/actions/runs/40792457095)
on `45fd3aa` passed 1,700 root tests with 33 expected skips, all three host smokes,
the four Chromium flows and the required aggregate. Its same-run Pages deployment
also succeeded after the [publication-condition correction](https://github.com/OpenT1D/lab/pull/21).
Live navigation, search and Mac build-reference/notebook downloads were checked.
[PR 24](https://github.com/OpenT1D/lab/pull/24) integrates the locally qualified
unsigned Mac candidate from `eda8f93`; its [guide](docs/mac-mmtt-candidate.md#recorded-internal-qualification)
records that exact source/artifact scope and the remaining distribution gates.

These runs do not establish a broad Windows/macOS root suite, browser coverage
outside Linux Chromium, release/native qualification, independent usability or
scientific validity. Historical native jobs retain their private/manual guards
and remain excluded from the public gate.

### Implemented AI development and ongoing review practice

The first bounded increment is implemented in the
[development guide](docs/development.md) and repository skills, with
[trial observations](docs/research/ai-development-trial.md). The following
defines its scope and ongoing review practice; it does not select a broader
agent automation or release workflow:

- Update the short root `AGENTS.md` with current scope and navigation. Put
  component ownership, tooling/native environment selection and the test map in
  the canonical [development guide](docs/development.md), with local guidance
  only where a component has genuinely different rules.
- Extend the existing issue/PR conventions with problem/reproduction, bounded
  scope, applicable roadmap item, preserved scientific/compatibility contracts,
  acceptance cases, relevant checks and a concise evidence handoff.
- Trial two focused repository skills: scientific/numerical changes and change
  verification. Point them to canonical guides and commands. Create a release
  skill only after a repeatable candidate-build procedure exists.
- Use isolated worktrees for concurrent writing, one owner for shared interfaces
  and a separate technical review of the diff and counterexamples. Start with at
  most two concurrent implementation changes; revise that limit from actual
  maintainer capacity. Agent review is not independent scientific validation.
- Select targeted checks during development, then run
  `uv sync --locked` and `uv run --locked python scripts/check.py` on the final
  revision. Assign the full check to one owner instead of duplicating it across
  agents. Native changes still need their task-specific numerical checks.
- Evaluate on a small set of real changes: maintainer review time, interventions,
  correction rounds, missed regressions and unnecessary edits. Report observed
  results before claiming productivity gains. Preserve tolerances and source
  ancestry; a green run obtained by silently refreezing expected results is not
  acceptable evidence.

### Reliability cases and remaining work

| Case | Status and required regression boundary |
| --- | --- |
| POSIX temporary-file publication follows an existing symlink | Implemented for the shared byte/text helpers: fresh exclusive byte siblings preserve stale entries; fixed text pending names refuse existing entries. Primitive and actual GUI persistence/restart regressions check unrelated bytes, regular published files and prior journal readers. Independent historical native POSIX writers retain their separate scope. |
| Catalogue/setup supervision returns after leader exit with a live descendant | Implemented for the shared tool supervisor used by catalogue verification, setup and historical readers. Real-process regressions cover normal exit, crash, timeout, cancellation, launch/cleanup signals, partial evidence and preservation of unrelated processes. Windows catalogue/setup supervision still requires its own host evidence. |
| Catalogue/setup cancellation arrives at cleanup entry | Implemented in [PR 10](https://github.com/OpenT1D/lab/pull/10): close the cleanup-entry cancellation window and bound the final direct-worker reap. Transition and real caller regressions retain prior signal handlers, partial logs and timeout/exit receipts. |
| Setup source identity omits process helpers | Implemented by reusing the shared process-helper inventory. Independent byte mutations of each helper are refused before readiness, installation or output creation; unchanged plans and failed-install receipts retain their existing behavior. |
| Sampling cancellation fixture reads incomplete live phase JSON | Implemented in [PR 12](https://github.com/OpenT1D/lab/pull/12): retry absent/incomplete hints within the original deadline and require a running analysis before cancellation. Deterministic malformed-hint and operation-state regressions preserve interrupted accounting and reconstruction. |

Retain a separate low-priority robustness case for the observation estimator's
trapezoid overflow at extreme finite inputs. Require finite output or a retained
explicit failure when addressed; it is not evidence of wrong normal-range
physiological results. None of these repairs changes scientific acceptance by
itself.

### Public CI and documentation boundaries

Keep the stable required public-check result and its explicit root, OS-smoke and
browser dependency roster. The implemented workflow policy tests distinguish
those families from historical native jobs; the public gate accepts only a
successful result from every selected family. Extend scope deliberately and use
actual hosted durations before changing timeouts, caching or shards. The shared
platform smoke runner and Linux Chromium suite complement the controlled DOM
tests; broader coverage needs its own selected scope and actual results.

Use the implemented [reviewed-main publication workflow](docs/documentation-publication.md)
for the canonical Sphinx output. PRs build/check the staged site; a separate
deployment follows the same main run's complete public gate. Verify navigation,
search and example downloads before advertising a homepage. Preserve the historical findings of the research reports and register
new public guides in `docs/_toc.yml`. External link checks remain separate from
unrelated PR acceptance.

Use small reviewed dependency-update PRs
for root tooling and pinned Actions. New Actions may require a revised verified
allowlist; deployment/signing permissions belong only to the jobs that need
them. Historical numerical locks retain their own source identity and reviewed
successor requirements. Public runner availability does not remove concurrency,
storage or runtime limits, or supply agent API credits.

### Mac feasibility and distribution boundary

Prefer a real bundled Python interpreter because current workers execute
`sys.executable -m ...`. Assess the actual ARM64 runtime artifact and its links,
licenses and minimum OS before selecting it. The current packaged-runtime
contract is Windows-specific; version the required descriptor/capability changes
with a short decision record and keep Windows-v1 readers supported. A legitimate
stdlib-only runtime may have an empty third-party distribution inventory.
Do not weaken general archive link checks to accommodate a runtime layout.

The app must expose the two supported tasks, seed only their required examples,
show Finder-start failures and keep projects/archives outside the installation,
using an appropriate Mac application-data location. Reuse existing validators,
scientific calculations and readers. A `.dmg` is the preferred download container
to investigate; a frozen bootloader is not assumed interchangeable with the
interpreter required by the existing worker protocol.

Before distribution, verify the exact signed/notarized artifact on a clean
Apple Silicon Mac with Gatekeeper enabled: both tasks, a failed/interrupted
attempt, quit/cancel/relaunch, double launch, report download/reconstruction,
app relocation and replacement, and preservation of old work when the app is
removed. Record source/runtime/notices, supported reader/app/OS combinations
and artifact checksums. Signing changes delivered executable bytes; define the
payload inventory and signature boundary accordingly. A hosted macOS build
alone does not establish clean-user installation or independent usability.
Intel support, automatic updates and wider native routes require separately
selected scope and evidence. The probe informs OT-061/064/065/072/073; it does
not complete those packages or replace OT-058's Windows requirement.

## Common laboratory delivery plan

**Planning decision, 25 October 2026; packet update, 29 October 2026 —**
OT-059 increment 1 now has an internal
[contract/extraction packet](docs/shared-core-contracts.md), followed by the
bounded [increment 2 services](docs/shared-project-services.md). The full
OT-060–074 packages and later increments remain planned; these internal
artifacts do not supply installed route migration or new native numerical evidence.
The shared-laboratory increment develops common services around the existing
working routes. [Decision 0070](docs/decisions/0070-common-research-laboratory.md)
records the direction; the [product requirements](docs/product-laboratory.md)
own the research jobs, acceptance criteria and 48-capability traceability map.
The [product-direction research report](docs/onderzoek/productrichting.md) owns the
comparative evidence and its limits. This section is the canonical sequence for
shared-laboratory extraction. The public-development queue above selects the
immediate maintainer work. The dated
[history](docs/research/roadmap-history-2026-10-28.md) retains earlier plans,
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

### Shared-core extraction queue

When selecting shared-core implementation, start slice 0 with two named
existing routes: `m4-study-secure` and `mmtt-sensitivity`. The first exercises two isolated numerical runtimes and a
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

Increment 1 is implemented as the [OT-059 packet](docs/shared-core-contracts.md):
ten-route source/runtime/reader metadata, versioned shared descriptors, unchanged
native payloads, two-source fasting/15 g M4 intake, complete/incomplete MMTT and
controlled failed/relocated reader cases. The
[verification record](docs/research/ot059-contract-extraction.md) separates local
checks from missing native success and hosted evidence. Increment 2 now has
[minimal local project services](docs/shared-project-services.md): immutable
freezes, a complete sequenced attempt ledger, isolated workers, forensic
recovery and matching trusted readers. Its [verification record](docs/research/ot061-064-minimal-services.md)
binds actual MMTT, controlled failed M4 and local macOS ownership/relocation
checks. Complete native M4 execution/relocation remains a specific open gate;
retained reader upgrades, installed increment 3 and other service hosts remain
subsequent work. This does not close the full OT-061 or OT-064 packages.

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

## Scientific milestones and evidence gates

Public-development delivery does not retire the original scientific criteria.
The [detailed milestone record](docs/research/roadmap-history-2026-10-28.md#foundation--repository-and-project-agreements)
retains their full text; linked protocols and evidence records own the exact
checks. A passing software or installer check does not establish biological
validity, clinical benefit or independent usability.

| Track | Working or recorded scope | Acceptance still open |
| --- | --- | --- |
| Foundation, M0 and M1 | Repository controls, native references and one bounded experiment have recorded checks. | Maintain exact source/runtime ancestry, units and timing; only claim the recorded environments and reproduced references. |
| M2 and internal verification | Two native tracks, frozen studies and numerical/fault/reconstruction checks are recorded. | Independent human M2 protocol execution; compatible cross-engine comparison must preserve actual scientific meaning. |
| M3 | Synthetic forecasting, frozen candidate comparison and researcher workflows are implemented. | Authorized source/release verification, preserved development/evaluation boundaries, a simpler baseline and independent human predictive assessment. |
| M4 and MMTT | Secretion/observation chains and fixed-kinetic synthetic analyses have bounded numerical evidence. | Suitable authorized observations, calibration/identifiability and simpler comparisons, domain review and independent intended-user assessment. Functional secretion is not anatomical beta-cell mass or therapy efficacy. |
| M5 | Frozen prognostic sources and person-disjoint synthetic comparisons have bounded verification. | Authorized release linkage, domain review, empirical freeze and independent intervention/study or held-out evidence against a simpler reference before human prognosis or treatment claims. |
| M6 and later extensions | Selected multiscale, device/activity/formulation, standards and AI ideas remain conditional. | A concrete question, appropriate coupling/reference checks and demonstrated value with characterized uncertainty; no general digital-twin completion claim. |

### P1 — First usable research product

P1's bounded researcher workflows and controller intake have internal technical
verification; independent intended-user acceptance remains open. Preserve the
[full P1 criteria](docs/research/roadmap-history-2026-10-28.md#p1--first-usable-research-product)
and [conditional handoff scope](docs/research/p1-product-acceptance-review.md).
The new public MMTT and Mac exercises collect task-specific evidence; they do
not automatically accept every older P1 route.

### C1 — First original OpenT1D controller

Original controller research is optional. Preserve negative findings, source
ancestry and [the existing C1 criteria](docs/research/roadmap-history-2026-10-28.md#c1--first-original-opent1d-controller).
A technically integrated controller is not automatically a fair efficacy
comparator or a clinical result. It is not a prerequisite for public delivery
or the shared-core extraction.

### M5 — One defined cell or immune therapy question

Preserve the [M5 question and full acceptance criteria](docs/research/roadmap-history-2026-10-28.md#m5--one-defined-cell-or-immune-therapy-question)
and [domain-review packet](docs/research/m5-domain-review-brief.md). The current
software does not clear participant-data access, graft/immune mechanisms or a
treatment-effect claim. Select another question if actual observations and
review support it better.

### Planned Windows installer (OT-058)

OT-058 retains the clean-Windows installer outcome, including managed runtimes,
upgrade/uninstall preservation and independent installation-to-report use. Its
internal candidate has a [separate verification record](docs/research/ot058-installer-verification.md),
with failed cases and open distribution/maintenance gates. Preserve the
[detailed requirement](docs/research/roadmap-history-2026-10-28.md#planned-windows-installer-ot-058).
The two-task Mac probe neither accepts nor supersedes that Windows outcome.

## Historical implementation and planning

Use the [dated roadmap history](docs/research/roadmap-history-2026-10-28.md) for
completed OT-001–058 work, prior plans, source/verification chronology and the
original detailed scientific milestone criteria. Its older "next" sections
are historical context. Select new implementation from the public-development
queue and shared-laboratory slices in this document.

### Next implementation: AI development

This historical heading preserves the link in the
[AI-development trial](docs/research/ai-development-trial.md). The bounded
increment is implemented; use the
[ongoing review practice](#implemented-ai-development-and-ongoing-review-practice)
above and select new work from the current queue.

### Proposed internal follow-up — OT-031: multiple M4 secretion sources

This historical heading preserves the link in the byte-bound published OT-031
execution plan. See the [original plan](docs/research/roadmap-history-2026-10-28.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources)
and [verification record](docs/research/ot031-verification.md) for its completed
bounded scope. Select new work from the current queue above.
