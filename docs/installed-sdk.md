# Internal installed Python and CLI candidate

This OT-060 developer candidate installs selected tasks into a separate
CPython 3.12 virtual environment. It runs synthetic standard-library MMTT
sensitivity outside a checkout. The historical `m4-study-secure` identity keeps
passive intake, frozen plans, explicit native-runtime refusal and matching failed
readers. The original two-route
[verification record](research/ot060-installed-route.md) retains that scope.
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
