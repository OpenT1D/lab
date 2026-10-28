# Use the local researcher task entry

The initial public exercise uses `mmtt-sensitivity` and `mmtt-sampling` with
root tooling. The [current publication policy](publication-security.md) excludes
automatic installation of vulnerable historical native projects. The catalogue
also retains implemented research routes outside that initial acceptance scope.

The checkout command `python -m experiments.workflows` discovers, checks and
starts the supported researcher tasks, then identifies their reports. It
delegates to the existing runners and keeps their protocols, numerical
runtimes, failure archives and reconstruction rules. Use it from the root of
the recorded checkout. It is a local entry, not an installable simulation
package or a general model interface.

## Choose a task and install its environment

Setup is explicit and separate from execution. Install the root tooling first:

```sh
uv sync --locked
.venv/bin/python -m experiments.workflows list
.venv/bin/python -m experiments.workflows describe m3-forecast
```

The entry prints JSON with each task's input option, canonical guide and
reconstruction capability. The existing guide owns the model contract and
scientific interpretation:

| Task | Supplied input | Execution environment | Canonical guide |
| --- | --- | --- | --- |
| `p1-controller` | `--source` directory containing `controller.py` and `controller.json` | Locked simglucose project | [P1 controller intake](p1-external-controller.md) |
| `m3-forecast` | `--config` synthetic study and frozen predictor declaration | Root Python | [M3 researcher forecast](m3-researcher-forecast.md) |
| `m3-compare` | `--config` frozen candidate roster on the same synthetic forecast task | Root Python | [M3 candidate comparison](m3-candidate-comparison.md) |
| `m4-secretion` | `--config` causal source and declaration | Root orchestration, simglucose and beta-cell projects | [M4 researcher workflow](m4-researcher-workflow.md) |
| `m4-compare` | `--config` ordered frozen secretion sources and shared worker budgets | Root orchestration, simglucose and beta-cell projects | [M4 source comparison](m4-source-comparison.md) |
| `m4-study` | `--config` frozen sources and selected 0/15/30 gram initial gastric loads | Root orchestration, simglucose and beta-cell projects | [Configurable M4 study](m4-configurable-study.md) |
| `m4-study-secure` | `--config` under the explicit maintained-study schema | Root orchestration, maintained simglucose and beta-cell projects | [Maintained M4 study](m4-maintained-study.md) |
| `m5-prognosis` | `--bundle` containing `model.py`, `state.json` and `model.json` | Root Python | [M5 researcher workflow](m5-researcher-workflow.md) |
| `mmtt-sensitivity` | `--config` sealed synthetic observation/analysis-plan directory | Root Python, standard-library calculation | [Observation analysis](observation-analysis.md) |
| `mmtt-sampling` | `--config` sealed development-selected schedule plan and synthetic paired observations | Root Python, shared standard-library calculation | [Sampling information loss](mmtt-sampling.md) |

For P1 or historical M4 routes, install their recorded native environment. M4 needs the
separate observation environment as well:

```sh
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
```

The maintained `m4-study-secure` route instead selects
`experiments/m0/simglucose_secure`. Use its canonical guide or task-directed
setup for the explicit project selection. The [local GUI](local-gui.md) exposes
that maintained route with the same native archive and reconstruction contract.

The M3 researcher run itself does not fit a model. Its separate donor
verification command in the canonical guide needs the existing M3 runtime;
that fitting/verification route is outside this entry's registered tasks. Preparing
the M5 example is likewise an explicit command in its guide.

[Task-directed setup](task-setup.md) provides a passive plan/check and an
explicit locked installation operation. [Local campaigns](local-campaigns.md)
manage repeated `m4-study` configurations with retained attempts and explicit
resume; the [experiment catalogue](experiment-catalogue.md) indexes existing
archives and separately verifies their native reconstruction.

## Check metadata before running

```sh
.venv/bin/python -m experiments.workflows check p1-controller \
  --source experiments/p1_external/example
.venv/bin/python -m experiments.workflows check m4-compare \
  --config experiments/m4/comparison/example.json
```

`check` reuses each route's declaration validators, checks source/settings/state
identities and reports the installed Python and distribution metadata. It
does not import supplied Python, call the model or run a simulation. P1's
original `preflight` executes a smoke test; it remains available as an explicit
operation in that guide and is not called by this passive check.

For both M3 tasks, `check` examines observation paths but does not open observation
contents or verify their byte hashes. Its JSON states
`observation_bytes_verified: false`. Invalid observation content, measurement
semantics and actual input hashes remain the native runner's responsibility.
A missing observation path gives `ready: false` and appears in
`observation_path_issues`; an explicitly requested `run` still preserves that
person and their failed origins through the native accounting. A missing
runtime or invalid model/configuration prevents dispatch.

For `mmtt-sensitivity`, `--config` selects its sealed plan directory. The
check verifies frozen input bytes and source/runtime identities; it does not
calculate secretion or interpret observations. The canonical guide owns the
explicit freeze operation and the separate synthetic analysis rules.

`ready: true` means metadata and required installed environments passed this
check. It does not prove callback behavior, source rights, training history,
predictive quality or biological validity. Rights and training declarations
remain researcher attestations. All nine registered tasks retain bounded
synthetic protocols; `m4-study` varies only its declared initial solid load.

## Run and find the report

Choose a fresh output directory. For example:

```sh
.venv/bin/python -m experiments.workflows run p1-controller \
  --source experiments/p1_external/example --output results/p1-entry
.venv/bin/python -m experiments.workflows run m4-secretion \
  --config experiments/m4/researcher_workflow/dalla_man.json \
  --output results/m4-entry
.venv/bin/python -m experiments.workflows run m3-compare \
  --config inputs/comparison/comparison.json --output results/m3-comparison
```

The task-specific execution options preserve the original meanings:

| Task | Additional options |
| --- | --- |
| P1 | `--profile adult#001` or `adult#002`; `--seed 101` or `102` |
| M3 forecast | `--timeout` is seconds per participant worker, default 120 |
| M3 comparison | The single shared `timeout_seconds` stays in the frozen configuration; the entry has no timeout override |
| M4 | `--reference` reuses a verified, source-matched BC-008 archive; worker budget stays in the configuration |
| M4 comparison | `--reference` reuses one verified BC-008 archive for every source; shared stage and source budgets stay in the configuration |
| M4 study | `--reference` supplies the verified historical BC-008 anchor; new load-specific reference/control curves are always generated. Scenarios and both budgets stay in the configuration |
| M5 | `--timeout-seconds` is seconds per fresh prediction worker, default 5 and maximum 60 |
| MMTT sensitivity | All variants, error assumptions and ordered visits stay in the frozen plan; no entry override |

Execution uses each selected project's existing `.venv/bin/python` directly.
It does not run an outer uv setup. Native children inherit no-sync,
no-Python-download, offline and no-user-configuration controls, including
M4's nested uv calls. Foreign uv/project/active-environment and Python-path
selectors are cleared for these children. Missing or wrong environments give
the appropriate locked setup instruction; the entry does not install them.

The final JSON identifies `child_exit_code`, `report_completeness` and an
absolute `report` path. The command preserves the child's exit code; a child
killed by a signal maps to the conventional `128 + signal` shell status.
An entry admission error exits with status 2 and no child execution. Native
console output is suppressed; inspect the retained native reports and logs
using the reported path. No launcher files are inserted in the native archive.

Report completeness is separate from process success. For example, a M5
run can return zero with a valid report labeled `incomplete`. A M3 worker
failure can produce a nonzero child exit and a reconstructible partial
report. The M3 comparison task uses `report.common.complete_cohort` for its
completeness and preserves every candidate's own coverage and coordinator
status in the native report. Its candidate roster and shared support rules
are defined in the [M3 comparison guide](m3-candidate-comparison.md). The M4
comparison uses `report.passed`; an unsuccessful source remains in its joint
report and makes the full comparison failed even when another pair is eligible.
`report_status_scope: recorded_native_report` means the entry read
the recorded native status; it has not independently revalidated that report.
Missing report artifacts have `report_completeness: unavailable`.

Ctrl-C and SIGTERM are forwarded to the native supervisor. SIGHUP is translated
to SIGTERM so legacy supervisors can seal their failure archives; the JSON
retains the original SIGHUP in `forwarded_signal`. The entry waits for its
cleanup and archive sealing and then restores its signal
handlers. The original runner owns worker budgets, descendant cleanup and
failure evidence; keep the complete archive.

## Reconstruct with the route's original reader

P1, both M3 tasks and all three M4 tasks require a new reconstruction output directory:

```sh
.venv/bin/python -m experiments.workflows reconstruct p1-controller \
  --archive results/p1-entry --output results/p1-entry-reconstructed
.venv/bin/python -m experiments.workflows reconstruct m4-secretion \
  --archive results/m4-entry --output results/m4-entry-reconstructed
.venv/bin/python -m experiments.workflows reconstruct m3-compare \
  --archive results/m3-comparison --output results/m3-comparison-reconstructed
```

For a preserved failed M4 single-source or comparison archive, explicitly add
`--allow-failed` and retain
its failed status. This mode does not promote the comparison into a passing
result. M3's report reader already retains failed and unattempted people.

M5's existing reader rebuilds analysis and checks it against the saved report
bytes in place. It has no separate output-directory option:

```sh
.venv/bin/python -m experiments.workflows reconstruct m5-prognosis \
  --archive results/m5-entry
```

All reconstruction dispatch uses root Python with `-S`. Keep the recorded
implementation checkout: the native readers retain their original
source/protocol requirements. P1 reconstruction includes source-only action
replay of the retained controller. Both M3 tasks and M5 reconstruct recorded candidate
outputs without executing the predictor; their analysis does not independently
reproduce an arbitrary supplied algorithm. M4 reconstructs its saved numerical
evidence without supplied-source execution or numerical packages. Each guide
describes the exact scope. A successful reconstruction has
`report_status_scope: native_reader_verified`, while the report may still be
incomplete or failed.

This entry adds task access and execution checks. Independent researcher
usability, human observation assessment and treatment evidence remain the
separate requirements recorded in the [roadmap](research/roadmap-history-2026-10-28.md#post-integration-internal-work-packages).
