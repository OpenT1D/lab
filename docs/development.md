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
| Repository tooling and documentation | `scripts/check.py`, `docs/conf.py`, `docs/_toc.yml` | `tests/test_repository.py`: navigation, build failure, publication exclusions and rendered language. Markdown/YAML/style checks run separately in `scripts/check.py`. |
| Task registry, dispatch and setup | `experiments/workflows/`, `experiments/setup/` | `test_workflow_entry.py`, `test_workflow_study.py`, `test_task_setup.py`: passive checks, explicit runtime selection, dispatch, source binding and installation refusal. Test files in this table are under `tests/` unless stated otherwise. |
| Shared MMTT estimator and paired sensitivity | `experiments/observation_analysis/` | `test_observation_estimator.py`: separate RK4/Decimal references and unit covariance; `test_observation_import.py`, `test_observation_workflow.py`: intake, CLI, interrupted evidence and reconstruction. |
| Reduced MMTT measurement schedules | `experiments/mmtt_sampling/`, reused `experiments/observation_analysis/analysis.py` | `test_mmtt_sampling_masking.py`, `test_mmtt_sampling_estimator.py`, `test_mmtt_sampling_comparison.py`, `test_mmtt_sampling_workflow.py`: masking, shared estimator boundary, descriptive comparisons and saved workflow. |
| Local GUI and HTTP lifecycle | `experiments/gui/server.py`, `service.py`, route managers and `static/` | `test_local_gui.py`, `test_gui_observations.py`, `test_gui_sampling.py`: local HTTP, jobs, cancellation, reports and tampering. `test_gui_observation_frontend.py`, `test_gui_sampling_summary.py` and other frontend wrappers exercise their controlled fixtures with Node where declared. |
| File and process primitives | `experiments/platform_files.py`, `platform_process.py`, `experiments/gui/windows_process.py` | `test_regular_file_snapshots.py`, `test_windows_primitives.py`: stable reads and platform boundaries. Process callers also need their lifecycle tests, for example `test_local_campaign_process.py`, `test_maintained_campaign_process.py`, `test_task_setup.py`; host-specific cases can skip. |
| Campaigns, catalogue and durable archives | `experiments/campaigns/`, `maintained_campaigns/`, `catalogue/`, `durable_archives/`, `historical_readers/` | `test_local_campaigns.py`, `test_maintained_campaigns.py`, `test_experiment_catalogue.py`, `test_durable_archives.py`, `test_historical_readers.py`: scheduling, eligibility, reconstruction and reader compatibility, with synthetic/fixture inputs. |
| M0/M1/M2 and controller work | `experiments/m0/`, `m1/`, `m2/`, `p1_external/`, `c1/` | Root `test_m1_contracts.py`, `test_m1_artifacts.py`, `test_m2.py`, `test_p1_external.py` and `test_c1_*.py` cover their declared contracts/fixtures. Separately selected native tests and numerical runs in the task guides verify actual engines. |
| M3 forecasting | `experiments/m3/` | Root `test_m3_artifacts.py`, `test_m3_researcher_study.py`, `test_m3_comparison_study.py` and source-specific families cover declared intake, causal/artifact and report contracts. Native estimator execution uses the separate M3 guide/environment. |
| M4 secretion and kinetic studies | `experiments/m4/` | Root `test_m4_researcher_workflow.py`, `test_m4_secure_study.py`, `test_m4_comparison_run.py` and study-specific families cover bounded configuration, execution/report fixtures and compatibility. Task-specific `test_numerical.py` files select their documented native environment. |
| M5 prognostic tasks | `experiments/m5/` | `test_m5_researcher_workflow.py`, `test_m5_native_rehearsal.py`, `test_m5_release_preflight.py`: frozen supplied-model task, synthetic rehearsal and conditional preflight. These do not verify human predictive validity. |
| Desktop admission, packaging and publication | `experiments/desktop/`, `scripts/build_windows_installer.py`, `scripts/publication_ci_scope.py` | `test_packaged_runtime.py`, `test_windows_packaging.py`, `test_publication_security.py`: runtime identity, staging/refusal and allowed execution scope. Actual installer lifecycle needs the separately recorded host/artifact checks. |

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

It checks Python tooling style, Markdown, YAML, citation metadata, navigation, documentation regression tests and a clean documentation build. Sphinx warnings, including unresolved document references, fail the build. The file checks include untracked, non-ignored files, so they also cover a first contribution before it is committed.

The Markdown configuration allows long prose lines and template checklists. It checks structure rather than imposing hard wrapping on research reports. The root suite also checks bounded contracts, artifact validation and analysis fixtures. It does not execute native physiology; run the isolated checks in the canonical tutorials as appropriate. Neither passing tooling tests nor native regression equality establishes biological validity.
The [public source policy](publication-security.md) limits the initial supported
exercise to the two synthetic MMTT tasks. Public Actions is currently disabled;
local results must not be reported as hosted CI. When deliberately enabled, the
workflow's default scope is the root suite and standard-library boundary checks;
historical native jobs require explicit private-archive dispatch and cannot run
in the public snapshot. CI activation and broader platform coverage are separate
roadmap work.

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

## Individual checks

```sh
uv run --locked ruff check docs/conf.py scripts tests experiments
uv run --locked ruff format --check docs/conf.py scripts tests experiments
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

Review dependency changes for compatibility and workflow impact. GitHub Actions are pinned to full commit hashes with readable release comments. The inactive `.github/dependabot.example.yml` preserves a future update configuration. Automatic version updates are disabled for the initial source publication.

## Documentation conventions

Use a clear title and short sections. Prefer relative links to repository files, primary sources for scientific claims and explicit status for proposed features. Add an explanation of units and assumptions when an example depends on them.

Keep Dutch research reports under `docs/onderzoek/`. The site uses that directory and the explicitly retained historical `docs/research/internal-verification-results.md` report to set their document language to Dutch while retaining English interface labels. Other guides and generated index/search pages use English. If a new document needs another language, update this convention, the language configuration and its rendered-HTML regression test together.

The M1 and M2 tutorials each own their runnable workflow. How-to guides explain specific tasks, reference pages define exact contracts and explanations describe design choices. Avoid documenting a hypothetical API as if it already exists.
