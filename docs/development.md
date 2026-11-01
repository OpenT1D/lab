# Development guide

The root toolchain checks the research software and builds the repository documentation. It also runs the two standard-library synthetic MMTT tasks; it does not install OpenT1D as a simulation package. No physiological models or clinical datasets are downloaded by the root setup commands.

Read the [README](../README.md), [contribution guide](../CONTRIBUTING.md) and applicable [roadmap item](../ROADMAP.md#now-next-and-later) before substantial work. The roadmap owns implementation order; this guide owns development navigation and verification practice. Task guides own runnable research procedures and their evidence boundaries.

## Set up

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). From your clone, run:

```sh
uv sync --locked
```

The repository selects Python 3.12 through `.python-version`. uv creates an isolated `.venv` and installs the versions in `uv.lock`; it can download Python if the selected version is unavailable. The first setup needs network access. See [uv's Python guidance](https://docs.astral.sh/uv/guides/install-python/) if your environment manages Python separately.

`pyproject.toml` currently contains a development dependency group only. There is no published simulation package. Select an environment from the task, rather than adding native dependencies to root tooling:

| Work | Environment and canonical procedure |
| --- | --- |
| Documentation, root contracts, orchestration and both synthetic MMTT tasks | Root `.venv`, `.python-version`, `pyproject.toml` and `uv.lock`; [paired analysis](observation-analysis.md) and [sampling](mmtt-sampling.md) need no physiological simulator or R. |
| Controlled frontend checks | Root tests invoke the installed `node` executable for `tests/gui_*.mjs` and the usability fixture. These are controlled DOM checks, not a real-browser suite. Some tests skip if Node is absent; record that skip rather than claiming frontend coverage. |
| M0/M1/P1 native physiology | Separate `experiments/m0/simglucose` project and lock; follow [M1](m1-tutorial.md) or [P1](p1-external-controller.md). |
| M2 cross-engine work | Separate simglucose project plus `experiments/m0/lt1/package-lock.json`; follow [M2](m2-tutorial.md), including its Node requirements. |
| M3 statistical estimator | Separate `experiments/m3/runtime` project and lock; follow [M3](m3-tutorial.md). Researcher-supplied predictors retain their own declared runtime contract. |
| M4 native studies | The selected task uses the simglucose, `experiments/m0/simglucose_secure` or `experiments/m4/beta_cell/runtime` project. Use its canonical guide, including the [maintained study](m4-maintained-study.md), and [task setup](task-setup.md) to inspect the explicit selection. |
| Packaged application | The [Windows candidate](windows-installation.md) has its own admitted runtime and build procedure. Its checks do not verify a new Mac package. |

The [public installation policy](publication-security.md) excludes historical native installation from the initial maintained public source scope. Native tutorial commands remain research records; an environment directory or an old `secure` name does not establish current public support. Task setup planning/checking is passive; installation is a separate operation subject to that policy. Do not install every runtime merely to edit root tooling or documentation.

## Component and test map

Ownership below means the implementation boundary responsible for a behavior. Review assignment remains with the maintainer in `.github/CODEOWNERS`; this table does not assign people or announce a stable general API. These are representative existing checks, not a coverage guarantee. Inspect the named test and its fixtures before selecting it, then include callers and readers affected by the change.

| Component boundary | Implementation to inspect | Existing checks and their bounded purpose |
| --- | --- | --- |
| Repository tooling and documentation | `scripts/check.py`, `docs/conf.py`, `docs/_toc.yml` | `tests/test_repository.py`: navigation, build failure, publication exclusions and rendered language. `tests/browser/documentation*.spec.mjs`: rendered-page assets, browser errors, search/theme behavior and fault probes. Markdown/YAML/style checks run separately in `scripts/check.py`. |
| Task registry, dispatch and setup | `experiments/workflows/`, `experiments/setup/` | `test_workflow_entry.py`, `test_workflow_study.py`, `test_task_setup.py`: passive checks, explicit runtime selection, dispatch, source binding and installation refusal. Test files in this table are under `tests/` unless stated otherwise. |
| OT-059 shared contract packet | `experiments/shared_contracts/`; [contract guide](shared-core-contracts.md) | `test_shared_contract_packet.py`: ten-route inventory, two-route metadata/lineage, refusal, actual MMTT and controlled M4 failed-launch/relocation readers. No native M4 success or route migration. |
| Minimal OT-061/064 project services | `experiments/shared_services/`; [service guide](shared-project-services.md) | `test_shared_services.py`: complete event ledger, freezes/retries, isolated MMTT workers, controlled M4 failure, forensic recovery, native readers/relocation and observed nested POSIX ownership. No installed SDK or native M4 success. |
| Internal OT-060 installed developer candidate | `scripts/build_sdk.py`, `packaging/sdk/`, `experiments/shared_services/installed.py`; [installed guide](installed-sdk.md) | `test_installed_sdk.py`, `sdk_ownership_probe.py`, `sdk_cancel_probe.py`, `sdk_early_cancel_probe.py`: noneditable wheels outside checkout, MMTT run/retry/move/read, passive M4 and failed readers, wrapper A/B provenance, incompatible readers, poisoned lookup/cache, unsafe output/FIFO refusal, controlled installed/early cancellation and owned child cleanup. Native M4 success, general upgrades and other-host qualification remain open. |
| Explicit installed M4 successor | `experiments/m4/installed_study/`, `experiments/shared_services/installed_m4.py`, `scripts/prepare_m4_runtimes.py`; [candidate guide](installed-m4.md) | `test_installed_m4.py`: preserved scientific criteria/conditions, reviewed selectors, inert profile/version/provenance consistency, actual stage ownership and FIFO refusal. `test_installed_sdk.py` covers source/data-wheel registration and missing-attachment refusal without native setup. Actual native checks use the separately reviewed native/observer overlays and the [preselected verification record](research/ot060-native-m4.md); source-checkout recorder tests remain distinct from installed scientific execution. |
| Thin installed project GUI and formative packet | `packaging/sdk/opent1d_lab/_gui*`, `gui.py`, `study_packet.py`; [GUI guide](installed-gui.md) | `test_installed_gui.py`: controlled admission, paths, report copies, HTTP deadlines/authentication and lifecycle; `test_installed_sdk.py`: actual installed GUI/CLI MMTT plan/parent/attempt parity, report downloads and relocation. `test_installed_gui_frontend.py` / `installed_gui_frontend.mjs`: reproduced parent/readiness/report identity regressions. `test_shared_gui_packet.py`: reference bindings, unchanged source, unanswered observations and tampering. Actual native GUI/browser and agent checks are separate evidence in the [selected record](research/ot065-072-shared-gui.md), not human sessions. |
| Shared MMTT estimator and paired sensitivity | `experiments/observation_analysis/` | `test_observation_estimator.py`: separate RK4/Decimal references and unit covariance; `test_observation_import.py`, `test_observation_workflow.py`: intake, CLI, interrupted evidence and reconstruction. |
| Reduced MMTT measurement schedules | `experiments/mmtt_sampling/`, reused `experiments/observation_analysis/analysis.py` | `test_mmtt_sampling_masking.py`, `test_mmtt_sampling_estimator.py`, `test_mmtt_sampling_comparison.py`, `test_mmtt_sampling_workflow.py`: masking, shared estimator boundary, descriptive comparisons and saved workflow. |
| Installed/shared sampling extension | `experiments/shared_services/sampling.py`, installed facade/CLI and GUI; [integration record](research/installed-mmtt-sampling.md) | `test_sampling_services.py`: exact native parity, development seal, nested child/draw association and moved reconstruction. `test_sampling_capabilities.py`: strict descriptor v1/v2/v3. `test_installed_sampling.py`: noneditable wheel, four controls, shared GUI/CLI IDs, cancellation/owned cleanup, downloads, tampering and restart/relocation. `tests/browser/installed-sampling.spec.mjs`: actual installed Chromium flow with native child display/download and withdrawal. No numerical core or OT-059 fixture changes. |
| Editable installed studies | `experiments/shared_services/workbench.py`, `_gui_drafts.py`, `_gui_inputs.py`, `drafts.js`; [guide](installed-gui.md#edit-save-and-recover-a-study) and [record](research/editable-workbench.md) | `test_workbench_drafts.py`: immutable byte/revision history, CAS, interrupted writes, corruption, diagnostic bounds and copies. `test_workbench_installed.py`: actual noneditable own MMTT/sampling/M4 intake, native parity, source refusal, parent preservation and restarted/moved concepts. `installed_gui_frontend.mjs`: late-response/upload, picker, safe-seed and conflict regressions. `tests/browser/workbench.spec.mjs`: own files, autosave/focus, restart, conflicts, correction, derivation and keyboard/reflow. |
| Frozen variants and plan comparisons | `experiments/shared_services/comparisons.py`, `comparison_tasks.py`, `comparison_reports.py`, `comparisons.js`; [SDK](installed-sdk.md#reproducible-variants-and-frozen-plan-comparisons), [workbench](installed-gui.md#compare-variants-and-frozen-plans) and [record](research/workbench-comparisons.md) | `test_plan_comparisons.py`: independent constant/trajectory oracles, complete failure/unattempted support, fixed attempts, prefix/unfinished isolation, leases and source binding. `test_installed_comparisons.py`: real noneditable Python/CLI/HTTP, sampling/allocation, supported M4 refusal, downloads/restart/relocation and exact snapshot replay. `installed_gui_frontend.mjs` and `tests/browser/comparisons.spec.mjs`: delayed verification/selector status, roster recovery and actual installed flows. Native M4 success requires its separately recorded exact-artifact rehearsal. |
| Local GUI and HTTP lifecycle | `experiments/gui/server.py`, `service.py`, route managers and `static/` | `test_local_gui.py`, `test_gui_observations.py`, `test_gui_sampling.py`: local HTTP, jobs, cancellation, reports and tampering. `test_gui_observation_frontend.py`, `test_gui_sampling_summary.py` and other frontend wrappers exercise their controlled fixtures with Node where declared. |
| Internal two-MMTT candidate and reader transition | `reader_compatibility.py/json`, `comparisons.py`, `scripts/build_sdk.py`, `scripts/qualify_reader_candidate.py`; [candidate guide](internal-mmtt-candidate.md) | `test_reader_transition.py`: exact predecessor/successor metadata, unchanged evidence and independent constant-input arithmetic. `test_internal_candidate.py`: actual two-task wheel, facade/bootstrap/HTTP refusals, readonly reports and restart. `test_sampling_capabilities.py`: exact descriptor rosters. Controlled DOM and `tests/browser/internal-candidate.spec.mjs`: capability UI and relaunch/reflow. Exact clean A/B artifact qualification runs separately; native/connected upgrades, clean-host and intended-user acceptance remain open. |
| Integrated M4/connected internal candidate | `scripts/qualify_integrated_candidate.py`, `scripts/integrated_candidate_probe.py`, descriptor 5; [integrated guide](internal-integrated-candidate.md) | `test_integrated_candidate.py`: whole scientific payload parity across descriptors 3/4/5, actual installed SDK/CLI/HTTP missing-attachment failure, all slots/rows, prefix/restart/relocation and legacy execution refusal. Strict capability and controlled DOM checks; `tests/browser/integrated-candidate.spec.mjs`: installed candidate controls, downloads, retained failure and relaunch. Actual-host native/reference/parity/connected/cancellation/relocation qualification is separate from root and hosted checks; native reader migration and intended-user acceptance remain open. |
| Connected synthetic study | `experiments/shared_services/connected*.py`, `connected_protocol.json`, installed facade and `connected.js`; [protocol](decisions/0088-connected-synthetic-observation-study.md) and [record](research/connected-synthetic-study.md) | `test_connected_study.py` / `connected_fixtures.py`: independent analytic forward fixture with actual inverse/sampling arithmetic, units, mismatch algebra, missing data, first attempts, interrupted materialization, tampering and exact prefix/relocation. `test_installed_connected.py`: noneditable Python/CLI/HTTP and genuine absent-runtime failure. `installed_gui_frontend.mjs` and `tests/browser/connected.spec.mjs`: selection/report identity, stale responses, explicit stage actions, restart, keyboard and narrow reflow. Actual native forward-to-inverse qualification uses separately reviewed M4 roles outside root CI. |
| File and process primitives | `experiments/platform_files.py`, `platform_process.py`, `experiments/gui/windows_process.py` | `test_regular_file_snapshots.py`, `test_windows_primitives.py`: stable reads and platform boundaries. `test_windows_launch.py`, `test_windows_source_admission.py`: current/base interpreter selection and source-only MMTT guards. Process callers also need their lifecycle tests, for example `test_local_campaign_process.py`, `test_maintained_campaign_process.py`, `test_task_setup.py`; host-specific cases can skip. |
| Campaigns, catalogue and durable archives | `experiments/campaigns/`, `maintained_campaigns/`, `catalogue/`, `durable_archives/`, `historical_readers/` | `test_local_campaigns.py`, `test_maintained_campaigns.py`, `test_experiment_catalogue.py`, `test_durable_archives.py`, `test_historical_readers.py`: scheduling, eligibility, reconstruction and reader compatibility, with synthetic/fixture inputs. |
| M0/M1/M2 and controller work | `experiments/m0/`, `m1/`, `m2/`, `p1_external/`, `c1/` | Root `test_m1_contracts.py`, `test_m1_artifacts.py`, `test_m2.py`, `test_p1_external.py` and `test_c1_*.py` cover their declared contracts/fixtures. Separately selected native tests and numerical runs in the task guides verify actual engines. |
| M3 forecasting | `experiments/m3/` | Root `test_m3_artifacts.py`, `test_m3_researcher_study.py`, `test_m3_comparison_study.py` and source-specific families cover declared intake, causal/artifact and report contracts. Native estimator execution uses the separate M3 guide/environment. |
| M4 secretion and kinetic studies | `experiments/m4/` | Root `test_m4_researcher_workflow.py`, `test_m4_secure_study.py`, `test_m4_comparison_run.py` and study-specific families cover bounded configuration, execution/report fixtures and compatibility. Task-specific `test_numerical.py` files select their documented native environment. |
| M5 prognostic tasks | `experiments/m5/` | `test_m5_researcher_workflow.py`, `test_m5_native_rehearsal.py`, `test_m5_release_preflight.py`: frozen supplied-model task, synthetic rehearsal and conditional preflight. These do not verify human predictive validity. |
| Desktop admission, Windows packaging and publication | `experiments/desktop/`, `scripts/build_windows_installer.py`, `scripts/publication_ci_scope.py` | `test_packaged_admission.py`, `test_admission_exit_observation.py`, `test_packaged_runtime.py`, `test_windows_packaging.py`, `test_publication_security.py`: owned lifecycle, runtime identity, staging/refusal and allowed execution scope. Actual installer lifecycle needs the separately recorded host/artifact checks. |
| Internal Apple Silicon MMTT candidate | `scripts/build_mac_app.py`, `packaging/mac/`, shared desktop/runtime and GUI capability gates | `test_mac_contract.py`, `test_mac_packaging.py`, `test_mac_probe.py`: v2 capabilities, source/runtime closure, binary inspection and adverse QA transitions. `tests/mac_app_probe.mjs` exercises an actual freshly built app; `tests/mac_launcher_probe.py` checks native Quit callbacks. The [candidate guide](mac-mmtt-candidate.md) owns the handoff scope. |

Shared file/process helpers, archive readers and the MMTT analysis core have multiple callers. Assign one implementation owner when changing one of these boundaries, identify every affected caller and preserve source-identity inventories. Do not treat a successful fixture test as proof that the listed runtime or platform was exercised.

## Task and review handoff

Keep one bounded task description in the existing issue or PR; use the repository templates rather than a second planning guide. Before implementation, record:

- The problem and minimal synthetic reproduction, or the unsupported claim and primary source; link the applicable roadmap item.
- The intended behavior, bounded scope and exclusions, files/components affected and anything reused.
- The contracts to preserve: units, timing, causal inputs, source ancestry, failure denominators, frozen results/tolerances, archive readers, runtime selection and rights, as applicable.
- Acceptance cases and a counterexample that could disprove the fix; select relevant checks from the source and test map.

For concurrent writing, use isolated worktrees with explicit file boundaries. Start with at most two implementation changes at once and one owner for shared interfaces. A separate technical reviewer inspects the final diff and relevant callers, challenges the acceptance cases and tries useful counterexamples. Agent review does not establish independent scientific validation. Routine fixes need no extra design approval; changes to shared architecture or scientific conventions need a short [decision record](decisions/README.md).

The repository skills at `.agents/skills/scientific-numerical-change/SKILL.md` and `.agents/skills/verify-change/SKILL.md` provide focused workflows pointing back to the canonical guides. Use the scientific workflow when a change affects numerical behavior or interpretation, and verification for selecting and reporting checks. The [AI-development trial record](research/ai-development-trial.md) records observed review cases and limitations; do not claim productivity gains from an unmeasured workflow.

Hand the reviewer a concise evidence packet: revision and dirty state, changed behavior, commands actually run with outcomes and skips, retained output locations, unresolved checks and risks, and any baseline/tolerance proposal. The reviewer records the revision reviewed, counterexamples attempted, findings and their disposition. Identify one integration owner to run `uv sync --locked` and `uv run --locked python scripts/check.py` on the final revision; other agents run targeted checks during development. Native changes also need the appropriate task-specific numerical checks. Report software checks, numerical evidence and remaining external acceptance separately.

## Check a change

Run the repository entry point defined for local checks and the CI workflow:

```sh
uv run --locked python scripts/check.py
```

The default command retains the full order. For a bounded change, select one
family explicitly:

```sh
uv run --locked python scripts/check.py --stage style
uv run --locked python scripts/check.py --stage tests
uv run --locked python scripts/check.py --stage docs
uv run --locked python scripts/public_smoke.py --output results/ci/local-smoke.json
```

Style includes metadata and navigation checks; tests runs root unittest discovery;
docs performs the clean strict Sphinx build. These focused commands do not replace
the integration owner's final full check. The public smoke receipt needs a fresh
output path. It runs explicit synthetic CLI/HTTP, file and process cases on the
actual host, refuses unexpected skips/missing cases and installs no native runtime.
Windows selects its control-pipe and Job tests; Linux/macOS select POSIX lifecycle
cases. The HTTP fixture uses a separate temporary workspace and an explicit root
interpreter without making a virtual-environment symlink.

Windows source MMTT dispatch requires current CPython 3.12 in addition to the
declared root environment checks. Explicit no-site launches of that same current
interpreter use its verified base path to avoid a venv redirector creating the
worker before Job assignment. Actual membership, immediate cleanup and task
flows still need Windows execution; see [decision 0079](decisions/0079-windows-stdlib-worker-identity.md).

It checks Python tooling style, Markdown, YAML, citation metadata, navigation, documentation regression tests and a clean documentation build. Sphinx warnings, including unresolved document references, fail the build. The file checks include untracked, non-ignored files, so they also cover a first contribution before it is committed.

The Markdown configuration allows long prose lines and template checklists. It checks structure rather than imposing hard wrapping on research reports. The root suite also checks bounded contracts, artifact validation and analysis fixtures. It does not execute native physiology; run the isolated checks in the canonical tutorials as appropriate. Neither passing tooling tests nor native regression equality establishes biological validity.
The [public source policy](publication-security.md) limits the initial supported
exercise to the two synthetic MMTT tasks. Initial publication used disabled
Actions; later activation and exact hosted receipts are recorded in the
[security boundary](publication-security.md). Local results must not be reported
as hosted CI. The active `Root checks` job explicitly installs the selected Python 3.12, uv 0.11.16 and Node 24.22.1,
then runs style/documentation and standard-library boundary checks after four isolated
root-test shards succeed. The default local command still runs all stages and
all tests. The [CI reliability record](research/ci-reliability.md) owns the
measured partition, complete-selection checks and exact-run diagnostics. Its Node preflight
fails when Node is unavailable. Historical native jobs additionally require
literal private-repository/manual-dispatch guards and cannot run in a public
repository, even if a changed scope helper reports them enabled.

The root job keeps dependency caching off and a forty-minute limit. Cold
hosted runs before the editable-workbench tests took 19 minutes 38 seconds and
19 minutes 19 seconds, close to the former twenty-minute limit; the
[workbench record](research/editable-workbench.md) owns the measured extension.
The comparison run's 1,810-test phase took 1,471.308 seconds before a fixture
failure, leaving insufficient room for setup, documentation and boundary checks
within twenty-five minutes. The [comparison record](research/workbench-comparisons.md)
records the fixture correction and measured budget increase. The connected-study
run on `62c0a3c` reached the subsequent thirty-minute limit while its root tests
were still running; the [connected-study record](research/connected-synthetic-study.md)
records that cancelled hosted run and the forty-minute budget. Individual tests,
uncached tooling, scope guards and numerical criteria remain enforced.
No test family or native scope guard is removed. The job attempts to retain setup/check/boundary logs and a selected environment
receipt under `results/ci` for five days, including after a failed check. The
receipt distinguishes the checked-out source SHA, event SHA and PR-head SHA;
command timings remain in the logs. It does not dump environment variables or
upload experiment directories. Cancellation, runner loss or an early setup
failure can leave partial or missing diagnostics. Measure cold hosted runs before
changing timeouts, caching or parallelism; a local duration is not that benchmark.

Follow the [activation procedure](publication-security.md#activate-on-the-selected-public-destination)
to review the exact Action allowlist, enable the intended checks, obtain actual
PR/main results and only then require `Repository checks`. Source changes alone
do not activate GitHub settings. That stable result now aggregates the root job,
the complete four-shard root-test matrix, the Linux/macOS/Windows public-smoke
matrix, the three-shard Linux Chromium application family and
the Chromium/Firefox/WebKit documentation matrix. Every
family must succeed; cancellation or a missing result cannot pass the gate.
Dependency Review is also required on pull requests. Only its explicit skip on
`push` or `workflow_dispatch` is accepted; the other families must still succeed.
Native jobs remain outside its dependency roster. The existing Node fixtures
continue to provide separate controlled DOM checks. See [decision 0076](decisions/0076-public-check-families.md).

Run the real-browser family with the selected Node 24 and the locked root Python:

```sh
npm --prefix tests/browser ci --ignore-scripts --no-audit --no-fund
npm --prefix tests/browser run install:browser
npm --prefix tests/browser test
```

Set `PLAYWRIGHT_BROWSERS_PATH` to an absolute temporary browser-cache directory
first. For Linux system dependencies, run the complete bounded wrapper as root so its
supervisor can terminate owned apt descendants:

```sh
sudo --preserve-env=PLAYWRIGHT_BROWSERS_PATH -- "$(command -v node)" \
  tests/browser/install-browser.mjs --with-deps chromium
```

Use an ephemeral, dedicated browser cache; this command does not launch the app
as root. System
dependencies and browser download share a 300-second budget and log separate
phases. The ephemeral hosted browser runners select the official Ubuntu archive
for the exact Azure mirror URI and retain authenticated, fail-closed APT setup;
see the [bounded CI record](research/ci-reliability.md#selected-implementation). The
suite uses Playwright 1.64.1, one Chromium worker, no retries and 13 synthetic
checkout/installed task, failure, concept and reopen cases. CI partitions those
cases into three isolated jobs, retaining one worker per job and zero retries. Synthetic screenshots, traces, logs and failure
workspaces are under `output/playwright/`. The separate required browser matrix runs the
[documentation browser checks](documentation-publication.md#browser-regression-checks)
in a separate output directory, with a five-minute CI budget for each engine.
All three documentation engines must pass the required gate. The guide includes
installation and local commands. Additional browser/platform coverage, Windows browser
shutdown and OS/release qualification require separate evidence; configured jobs
do not establish hosted passes.

## Preview the documentation

```sh
uv run --locked python scripts/check.py
uv run --locked python -m http.server 8000 --bind 127.0.0.1 --directory _build/html
```

Open `http://127.0.0.1:8000/docs/index.html`. Stop the server with Ctrl+C. You can open `_build/html/docs/index.html` directly for reading; use the local server for search and browser-loaded assets.

Rerun `scripts/check.py` after changes to refresh the preview. It replaces the generated HTML directory, including old pages and downloads. A direct Sphinx rebuild does not remove all obsolete output, even with `-E -a`; use the repository check before sharing or publishing the site.

Markdown files are the canonical content on GitHub and in the generated site. Sphinx, MyST and the external table of contents build root documents and `docs/` together. List each new public guide explicitly in `docs/_toc.yml`; the repository check catches missing entries. Do not create a second copy of the README or roadmap.

The site includes only the listed pages. Data, results, build outputs and hidden directories are excluded from page discovery. Sphinx does not honor `.gitignore`, so those exclusions are configured separately. Review explicit includes, images and downloadable asset links as well: they can copy a file into the site even when it is not a page.

The research report's Mermaid diagram uses a pinned browser library from jsDelivr and requires network access to render. The document text, navigation and search are served locally.

The [M3 tutorial](m3-tutorial.md) owns the separately locked statistical-estimator environment and synthetic forecast checks. Repository tests also validate M3 contracts and artifacts; native estimator execution remains separate, as do all original physiological regression jobs.

For CI diagnosis, a complete root selection can be listed without execution:

```sh
uv run --locked python scripts/root_tests.py --shard 1/4 --list
uv run --locked python scripts/check.py --stage tests --test-shard 1/4
```

Use all four shards to cover the full suite. The default full command never
accepts an implicit partial selection. Root receipts under `results/ci/` bind
the source and selected IDs and record failures and skips. For rerun status,
use the [exact-run diagnostic](research/ci-reliability.md#check-provenance-and-verification-handoff);
a successful latest attempt can coexist with stale failed entries in the PR UI.

## Individual checks

```sh
uv run --locked ruff check docs/conf.py scripts tests experiments packaging/sdk/opent1d_lab
uv run --locked ruff format --check docs/conf.py scripts tests experiments packaging/sdk/opent1d_lab
uv run --locked python -m unittest discover -s tests -v
uv run --locked cffconvert --validate
```

External links can be checked separately:

```sh
uv run --locked sphinx-build -E -a -b linkcheck -c docs . _build/linkcheck
```

Review `_build/linkcheck/output.txt`. Some publishers and private repositories reject automated requests. Investigate those results and retain a narrow, documented exception only when needed. Network availability must not become an unrelated pull-request merge blocker. Internal references are checked in the required HTML build.

## Dependencies

Use `uv add --group dev PACKAGE` for a justified new repository tool. Commit both `pyproject.toml` and `uv.lock`, and run the full checks. To update an existing tool, use `uv lock --upgrade-package PACKAGE`, then `uv sync --locked` and the same checks.

Review dependency changes for compatibility and workflow impact. GitHub Actions
are pinned to full commit hashes with readable release comments. The recognized
`.github/dependabot.yml` prepares monthly grouped updates for root uv tooling and
Actions, with at most three open update PRs per ecosystem. Root uv excludes
`experiments/`, `packaging/` and `tests/`; it does not maintain historical native
locks or browser/package fixtures. Merging this configuration to the default
branch enables that update service; its [observed hosted discovery and refresh runs](publication-security.md#prepared-dependency-updates-and-pr-review)
are recorded separately from repository verification.

Both groups accept only minor/patch version updates, and each ecosystem also
ignores all SemVer-major version updates. A group filter alone leaves unmatched
updates eligible for individual PRs. Major upgrades require a separate manual
proposal with compatibility checks, including the Action SHA allowlist where
applicable; no update is automatically merged. These are
[separate Dependabot options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#groups).

The read-only PR dependency job blocks introduced high/critical advisories in
runtime, development and unknown scopes. It posts no PR comments and applies no
license policy. After the pinned official action succeeds, a bounded API guard
requires every comparison page to be warning-free and its full dependency and
advisory inventory to match the action's scanned output. HTTP, pagination, JSON,
warning/deadline or inventory errors fail the job. No local test proves hosted
uv dependency-graph coverage; that needs a safe root-lock delta and a disposable
known-vulnerable negative PR. See [the security boundary](publication-security.md#prepared-dependency-updates-and-pr-review)
and [decision 0078](decisions/0078-dependency-review-completeness.md).

## Documentation conventions

Use a clear title and short sections. Prefer relative links to repository files, primary sources for scientific claims and explicit status for proposed features. Add an explanation of units and assumptions when an example depends on them.

Write public guides and research reports in English. The reports under `docs/research/` and the historical `docs/research/internal-verification-results.md` report have been translated; their English file names now share the existing research directory. Maintained links use the new paths; section anchors remain for compatibility within each report. Historical file URLs change with this move. Preserve dated findings, numerical values, source references and evidence limits when translating. All articles, interface labels and generated index/search pages use English, checked by the rendered-HTML regression test. Private usability-session cards may still be generated in Dutch as described in the session guide.

The M1 and M2 tutorials each own their runnable workflow. How-to guides explain specific tasks, reference pages define exact contracts and explanations describe design choices. Avoid documenting a hypothetical API as if it already exists.
