# Internal installed Python and CLI candidate

This OT-060 developer candidate installs selected tasks into a separate
CPython 3.12 virtual environment. It runs synthetic standard-library MMTT
sensitivity outside a checkout. The historical `m4-study-secure` identity keeps
passive intake, frozen plans, explicit native-runtime refusal and matching failed
readers. The original two-route
[verification record](research/ot060-installed-route.md) retains that scope.
The [two-task internal candidate](internal-mmtt-candidate.md) adds a separately
bounded, pinned MMTT comparison-reader transition and exact-artifact procedure.
The default wheel below retains its broader developer scope.

The wheel version `0.0.0.dev0` is internal; no release, stable API, general upgrade
support or independent usability is claimed.

The explicit [installed M4 successor](installed-m4.md) adds a version-2 artifact
with reviewed, separately attached dependency directories. Its own
[native verification record](research/ot060-native-m4.md) separates current
execution/parity/relocation evidence from the historical task and this initial
candidate's passive M4 checks. Both selected native plans now pass local macOS
execution, exact scientific parity and complete physical-removal relocation.
The [thin installed GUI](installed-gui.md) consumes these same public services;
its guide also covers candidate-bound formative exercise preparation.
The current version-3 descriptor also includes `mmtt-sampling`, with its original
development seal, native schedule reports and unchanged inverse estimator. Its
[integration record](research/installed-mmtt-sampling.md) owns the new evidence.
Version-1 and version-2 descriptors retain their exact historical task rosters
and cannot declare sampling. Version 1 still refuses native execution; version 2
retains its existing explicit reviewed-attachment policy.
The [editable workbench](installed-gui.md#edit-save-and-recover-a-study) reuses
passive SDK input inspection, explicit development sealing and original-input
export. Its concepts remain workspace convenience state; SDK freezes stay
authoritative and immutable.

An explicit [M3 workbench build](installed-m3.md) selects descriptor 6 with
`--m3-workbench`; default and prior candidate rosters remain unchanged.

## Build and install

The builder uses the separately locked root tooling. Start from a clean source
revision and choose a fresh build directory whose parent exists:

```bash
uv sync --locked
uv run --locked python scripts/build_sdk.py \
  --output /private/tmp/opent1d-sdk-build --build-label internal-a
uv venv --python 3.12 /private/tmp/opent1d-sdk-env
uv pip install --offline --no-deps --link-mode=copy \
  --python /private/tmp/opent1d-sdk-env/bin/python \
  /private/tmp/opent1d-sdk-build/opent1d_lab-0.0.0.dev0-py3-none-any.whl
```

The build receipt records source revision/dirty state and wheel SHA-256. The
wheel has no third-party runtime dependencies or native simulation runtimes.
`--allow-dirty` exists only for development fixtures; a formal candidate uses a
clean source build. Retain its receipt and wheel together. The complete installed
manifest detects missing, changed or unexpected payload files and unsafe
filesystem entries. Checksums provide consistency, not authenticity against
replacing the whole installation.

These example paths select macOS's canonical `/private/tmp`; its `/tmp` symlink
is refused by the path checks. Choose other fresh canonical absolute directories
as needed, without linked ancestors.

The launcher requires a POSIX virtual environment and CPython 3.12. Local
qualification is macOS arm64; Linux installation and Windows support have their
own open gates. A platform-independent wheel tag does not claim those host
checks. Build/install uses uv, while installed operations use their own absolute
interpreter and payload without uv or Git. Keep projects, input copies and report
outputs outside the installed environment. Output directories must be fresh and
cannot be nested inside any existing project store.

## Python exercise outside the checkout

Use the installed environment's Python from an unrelated working directory.
This creates only invented synthetic data and a new project:

```python
from pathlib import Path
import opent1d_lab as lab

root = Path.cwd()
inputs = lab.example("mmtt-sensitivity", root / "inputs")["inputs"]
lab.validate("mmtt-sensitivity", inputs)
project = lab.create_project(root / "study", "Invented installed MMTT study")
plan = project.freeze("mmtt-sensitivity", inputs)["plan"]
admission = project.check(plan)
first = project.run(plan, timeout=600)
retry = project.run(plan, retry_of=first["attempt"], timeout=600)
project.reconstruct(first["attempt"], root / "first-report")
project.relocate(root / "moved-study")
reopened = lab.open_project(root / "moved-study")
reopened.reconstruct(first["attempt"], root / "moved-report")
print(reopened.info())
```

`validate` checks intake without estimation. `freeze` retains exact input bytes,
planned slots, native identities and matching source/reader snapshots. `check`
performs admission without setup or execution. `run` starts a retained attempt;
every repeat must explicitly name the previous terminal attempt with `retry_of`.
The result separates process status, scientific completeness and slot
availability. The selected MMTT plan retains three variants, 128 draws and seed
117. A completed process can still have incomplete scientific evidence.

For censored evidence use `lab.example(..., case="censored")` in a fresh input
directory. Reading incomplete/interrupted native evidence requires explicit
`allow_failed=True`; this does not turn unavailable slots into estimates.
`project.import_attempt(plan, archive, retry_of=...)` copies and verifies matching
native evidence without executing archived code. Imports are separate attempts.

`Project` holds a path. Each call acquires and releases its own live store lease.
`run` accepts a `threading.Event` as `cancel`. SIGINT, SIGTERM and SIGHUP on the
main thread also request cancellation, with live owned cleanup and retained
evidence. The broker queues run cancellation through project publication and
terminal sealing. For an admitted run, queued cancellation before native launch seals an
interrupted forensic attempt with unavailable slots. Cancellation before the
broker reaches request dispatch can refuse without creating an attempt.
If an external crash leaves an unfinished attempt, first establish
independently that execution has stopped, then call
`project.recover(attempt, execution_stopped=True)`. Recovery does not signal PIDs
from a stored journal or claim observed cleanup of an earlier process.

## CLI exercise

Successful commands emit JSON. `run` exits 1 for an incomplete result;
refusals/errors exit 2. Set an absolute CLI path and run outside the checkout:

```bash
SDK=/private/tmp/opent1d-sdk-env/bin/opent1d-lab
"$SDK" installation
"$SDK" example --task mmtt-sensitivity --output "$PWD/cli-inputs"
"$SDK" create --project "$PWD/cli-study" --name "Invented CLI study"
"$SDK" validate --task mmtt-sensitivity \
  --package "$PWD/cli-inputs/package.json" \
  --csv "$PWD/cli-inputs/observations.csv" \
  --settings "$PWD/cli-inputs/settings.json"
"$SDK" freeze --project "$PWD/cli-study" --task mmtt-sensitivity \
  --package "$PWD/cli-inputs/package.json" \
  --csv "$PWD/cli-inputs/observations.csv" \
  --settings "$PWD/cli-inputs/settings.json"
```

Copy the returned plan identifier into `PLAN`, then use:

```bash
"$SDK" check --project "$PWD/cli-study" --plan "$PLAN"
"$SDK" run --project "$PWD/cli-study" --plan "$PLAN" --timeout 600
"$SDK" info --project "$PWD/cli-study"
```

Use the returned attempt identifier with `reconstruct --attempt ... --output ...`;
add `--allow-failed` for incomplete/failed evidence. `run --retry-of ...`,
`import --archive ...`, `relocate --output ...` and
`recover --attempt ... --execution-stopped` mirror the Python operations.
`--help` lists each command's required fields.

## Inspect and derive user-chosen synthetic inputs

`lab.inspect_inputs(task, inputs)` performs native admission and returns original
hashes, planned slots and bounded observation diagnostics without estimation.
`valid=True` admits the metadata/settings/native freeze, while
`observations.valid`, per-visit errors, missing/censored counts and explicit
truncation describe the input separately. It does not promise a complete model
result. `validate` retains its original minimal admission interface.

Export exact frozen inputs to a fresh directory, change explicitly selected
settings, inspect and freeze with the original parent:

```python
import json

copied = project.export_inputs(plan, root / "derived-inputs")
settings_path = Path(copied["inputs"]["settings.json"])
settings = json.loads(settings_path.read_bytes())
settings["uncertainty"]["draws"] = 64
settings_path.write_text(json.dumps(settings), encoding="utf-8")
inspection = lab.inspect_inputs(copied["task"], copied["inputs"])
derived = project.freeze(copied["task"], copied["inputs"], parent=plan)["plan"]
```

This MMTT example reuses the earlier `project`, `plan` and `root`. Export preserves
all original file bytes, including sampling development evidence. M4 export
recreates the selected trusted source bundle and original configuration; archived
Python is never executed. Unsupported historical tasks/readers refuse.

`inspect` uses the same explicit flags as `validate`; original-input export is:

```bash
"$SDK" export-inputs --project "$PWD/cli-study" --plan PLAN_ID \
  --output "$PWD/derived-inputs"
```

For own sampling inputs, prepare an explicit development-only seal before normal
inspection/freezing. Supply a development package containing exactly the design's
selection participants, its matching CSV and the study design:

```python
prepared = lab.prepare_development(
    root / "development-package.json", root / "development-observations.csv",
    root / "design.json", root / "development-import",
)
```

Use `prepared["development"]` as the `development` input alongside the four full
study files. CLI equivalent: `prepare-development --package ... --csv ...
--design ... --output ...`. Roster/allocation checks precede development CSV
interpretation. The unchanged native importer and schedule-time checks supply
the seal; no evaluation estimator or automatic schedule selection runs.

## Reduced measurement schedules

The sampling route uses the same project methods and retains all native parent
and child reports. Export one of `information-loss`, `constant`, `incomplete` or
`steep-response` explicitly:

```python
inputs = lab.example("mmtt-sampling", root / "sampling-inputs",
                     case="information-loss")["inputs"]
lab.validate("mmtt-sampling", inputs)
plan = project.freeze("mmtt-sampling", inputs)["plan"]
result = project.run(plan, timeout=600)
project.reconstruct(result["attempt"], root / "sampling-report")
```

`inputs` contains `package.json`, `observations.csv`, `settings.json`, `design.json`
and `development`, a sealed development-only observation import. The raw files
must match the sealed selection evidence. Evaluation participants cannot enter
development selection. Selection, allocation, original bytes and effective native
freeze remain bound to the plan. Validation and freezing perform no estimation.

The CLI uses the same explicit inputs for both `validate` and `freeze`:

```bash
"$SDK" example --task mmtt-sampling --case information-loss \
  --output "$PWD/sampling-inputs"
"$SDK" freeze --project "$PWD/cli-study" --task mmtt-sampling \
  --package "$PWD/sampling-inputs/study/package.json" \
  --csv "$PWD/sampling-inputs/study/observations.csv" \
  --settings "$PWD/sampling-inputs/study/settings.json" \
  --design "$PWD/sampling-inputs/study/sampling-design.json" \
  --development-import "$PWD/sampling-inputs/development"
```

Use the returned plan with `check`, `run` and the normal attempt/retry/reader
commands. All four schedules, five participants and three variants retain their
60 planned slots, including unavailable ones. Supplied settings retain 128
draws per slot. The result's `report_sha256` includes the parent JSON/Markdown
and each available `studies/<schedule>/report.json` and `.md`. Reconstruct the
whole directory to preserve native relative links. A full curve is a comparison
reference, not biological truth; the information-loss reversal is engineered
synthetic evidence. Incomplete and interrupted native reports require the same
explicit `allow_failed` option. Hard stops can instead retain forensic evidence.

## Reproducible variants and frozen-plan comparisons

Create the complete comparison before executing any selected plan. These methods
use the same project ledger as the workbench. `comparison_options(plan)` returns
the task-owned assumption, schedule/variant or source/load selectors present in
that exact frozen plan. Comparisons remain within one task and compatible
observations, allocation, endpoint, protocol, source and reader support.

For a fresh unattempted MMTT sensitivity plan:

```python
definition = {
    "schema": "opent1d.plan-comparison/1",
    "name": "Synthetic volume assumptions",
    "question": "How does the declared volume change the same paired endpoint?",
    "baseline": "nominal",
    "variants": [
        {"id": "nominal", "label": "Nominal volume", "plan": fresh_plan,
         "selector": {"variant": "nominal"}},
        {"id": "volume", "label": "20 percent volume stress", "plan": fresh_plan,
         "selector": {"variant": "volume-120"}},
    ],
}
frozen = project.freeze_comparison(definition)
comparison = frozen["comparison"]
project.run(fresh_plan)  # One native attempt serves both selected variants.
saved = project.reconstruct_comparison(comparison, root / "comparison-report")
tip = saved["snapshot"]["tip"]
project.comparison(comparison)  # Current fixed-first-attempt statuses.
project.reconstruct_comparison(comparison, root / "same-snapshot", at=tip)
```

`fresh_plan` must be a newly frozen, unattempted plan. The earlier tutorial plan
has already run and is refused here; derive a fresh plan when repeating its
assumptions. Freeze 2–16 unique labelled members, optionally across compatible
derived plans. Only each plan's first attempt is selected. Later retries stay
in history, while failures, partial evidence and unattempted members remain in
the comparison denominator. A saved ledger tip reproduces an old report even
after another member first runs. Full project relocation retains those tips.
The first attempt of a comparison member must execute through the shared
services. Importing an existing archive cannot establish this prospective order
and is refused without changing the project. Import into a separate plan instead.
Later imported retries remain in history and cannot replace the selected first
executed attempt.

Sampling selectors use `{"schedule": "full", "variant": "nominal"}` or a
preselected reduced schedule. The original observations and development seal
remain fixed. Installed M4 selectors use, for example,
`{"source": "dalla_man", "scenario": "fasting"}`; compare supported sources or
explicit initial loads with their native complete-grid descriptive metrics.
No concentration curve is treated as a secreted amount or pooled score.

Native attachments admit the exact historical three-task or current four-task
application roster including sampling. Extra, missing, reordered or duplicate
tasks refuse. Recreate attachments for the current artifact: this admission
correction changes its helper/source identity and does not qualify an older
artifact or enable an unsupported reader transition.

The CLI takes a bounded JSON definition file:

```bash
"$SDK" comparison-options --project "$PWD/cli-study" --plan FRESH_PLAN_ID
"$SDK" freeze-comparison --project "$PWD/cli-study" --definition comparison.json
"$SDK" comparison --project "$PWD/cli-study" --comparison COMPARISON_ID
"$SDK" reconstruct-comparison --project "$PWD/cli-study" \
  --comparison COMPARISON_ID --output "$PWD/comparison-report"
"$SDK" reconstruct-comparison --project "$PWD/cli-study" \
  --comparison COMPARISON_ID --at SAVED_LEDGER_TIP --output "$PWD/exact-replay"
```

Each reconstruction writes sealed JSON, Markdown and CSV with exact input/plan,
first-attempt, native report, comparison-reader and ledger-prefix bindings. It
uses existing authoritative readers, without executing supplied models or
archived code. MMTT's existing offline reader repeats verification arithmetic;
that is distinct from a native model run. Changed comparison-reader bytes refuse
without a separately supported transition. Comparisons add no runtime setup,
native distribution permission, scientific validity or human acceptance.

## Connected synthetic study

A connected study composes the existing `m4-study-installed` forward observer
with `mmtt-sampling`. It adds no task, model, runtime or estimator. Freeze its
question and the complete protocol before the forward plan first executes:

```python
study = project.freeze_study(
    "Known synthetic secretion",
    "Does the matched inverse recover the known 0–120-minute input?",
)
identity, forward = study["study"], study["forward_plan"]
project.study(identity)  # Fixed stages, all planned support and next explicit action.
project.check(forward, runtime_attachment=attachment)
project.run(forward, runtime_attachment=attachment, timeout=10800)
bridge = project.materialize_study(identity)
project.run(bridge["sampling_plan"], timeout=600)
report = project.reconstruct_study(identity, root / "connected-report")
project.reconstruct_study(identity, root / "connected-replay", at=report["snapshot"]["tip"])
```

`attachment` is a newly created reviewed attachment for this installed artifact,
following the [M4 guide](installed-m4.md). A missing attachment retains a failed
first forward attempt and blocks observation materialization. Each stage runs
explicitly through the existing execution/cancellation service. Retrying retains
later attempts but cannot replace the study's first executed attempt. An archive
import cannot serve as that prospective first attempt.

The default freeze creates one unattempted M4 plan containing both supported
sources and both fasting/initial-15-g scenarios. Alternatively supply
`forward_plan=...` for an unused plan with exactly that supported configuration.
The question, two source-method cases, allocation, bridge, four inverse variants,
32 engineering perturbations and full/one-minute/fifteen-minute schedules are
fixed in [decision 0088](decisions/0088-connected-synthetic-observation-study.md).
`observation_case="missing-evaluation"` prospectively blanks the evaluation
case's after-visit C-peptide at minute 60; the row and every planned endpoint
remain present. Declare that control before running the shared forward plan.

Materialization verifies the original complete forward evidence, seals converted
observations and separate development evidence, then freezes a sampling child
and a six-member comparison. Its committed intent supports an explicit repeat
of `materialize_study` after interruption without duplicating or retargeting
plans. The cross-task bridge is distinct from existing same-task parent links.

The CLI uses the same service operations:

```bash
"$SDK" freeze-study --project "$PWD/cli-study" \
  --name "Known synthetic secretion" --question "Does the matched inverse recover its input?"
"$SDK" study --project "$PWD/cli-study" --study STUDY_ID
"$SDK" check --project "$PWD/cli-study" --plan FORWARD_PLAN_ID \
  --runtime-attachment REVIEWED_ATTACHMENT_JSON
"$SDK" run --project "$PWD/cli-study" --plan FORWARD_PLAN_ID \
  --runtime-attachment REVIEWED_ATTACHMENT_JSON --timeout 10800
"$SDK" materialize-study --project "$PWD/cli-study" --study STUDY_ID
"$SDK" run --project "$PWD/cli-study" --plan SAMPLING_PLAN_ID --timeout 600
"$SDK" reconstruct-study --project "$PWD/cli-study" \
  --study STUDY_ID --output "$PWD/connected-report"
```

Use the returned forward and sampling plan IDs with the ordinary `check`/`run`
commands. Add `--forward-plan` or `--observation-case missing-evaluation` at
freeze, and `--at SAVED_LEDGER_TIP` for a report's exact historical snapshot.
Reconstruction writes sealed `report.json`, `report.md` and `study.csv`. All
72 case/schedule/variant/endpoint rows retain known truth, inverse point values,
point and interval status, and explicit failures. Numerical acceptance reports
six matched point and eighteen mismatch checks separately from native evidence
completeness. The companion comparison preserves its fixed six selectors;
all twelve native schedule/variant combinations remain in the study report.

Only the unchanged first 120 minutes of the original 240-minute forward run
enter the inverse. Known totals independently integrate pancreatic pmol/kg/min
and apply body weight once. C-peptide concentrations and AUC remain separate from
secreted amounts. These source methods represent two synthetic cases, not two
people. Fasting versus 15 g is a stimulus contrast, not a treatment effect.
See the [verification record](research/connected-synthetic-study.md) for observed
recovery, sparse-schedule failures and remaining limits. Reader identities stay
strict; this increment does not implement the roadmap's changed-reader upgrade.

## M4 and compatibility boundaries

Export M4 inputs with `example --task m4-study-secure --case fasting --output ...`
or `lab.example("m4-study-secure", output, case="fasting")`. Preserve its exported
directory layout: the configuration uses relative paths to both model and
declaration pairs. Validate/freeze with `--config` or the returned `config.json`
input mapping. Export `case="gastric_load_15g"` separately and freeze it with
`parent=fasting_plan` / `--parent` to retain derivation. Both plans retain
adult#001, 240 minutes and 961 quarter-minute samples. `check` reports unavailable
native runtimes; explicit `run` retains a forensic failed attempt with every
planned slot unavailable. It never installs, discovers or bypasses the native
runtime policy. Matching controlled failed M4 archives can be imported and
reconstructed with their authoritative report/figure bytes.

Application provenance is distinct from native scientific identity. Each new
installed freeze retains `application.json` containing the verified application
descriptor and its identity; attempts retain the executing/importing application
identity in `host.application`. `descriptor_sha256` hashes canonical descriptor
JSON, while the build receipt separately identifies wheel bytes. Reconstruction
returns the current reader application's identity. Original application records
remain intact across a compatible wrapper-build change.

The first tested upgrade case installs wrapper builds A and B with identical
native reader bytes, relocates A's project and reads it through B. A candidate
with changed native reader bytes is refused. The manifest, archived source and
application labels never authorize executing archived code. General old-version
compatibility and automatic project migration remain open. Normal Python API
startup trusts its host Python environment; the CLI starts with `-I -B -S`,
verified source and an independent bytecode-cache location. Process isolation is
not a hostile-code sandbox. SDK subprocesses use the system default PATH for
host metadata helpers; direct internal bootstrap use trusts its caller's host
environment. Distribution rights, broader historical native parity, other hosts,
general compatibility and intended-user evidence retain their
[roadmap gates](../ROADMAP.md#shared-core-extraction-queue).
