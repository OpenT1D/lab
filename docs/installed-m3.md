# Frozen synthetic M3 comparisons in the shared workbench

The explicit descriptor-6 SDK wheel adds the existing `m3-compare` task to the
shared project ledger, Python API, CLI and workbench. Its unchanged M3 coordinator
runs frozen predictors and persistence on the same invented observations.
The [M3 comparison guide](m3-candidate-comparison.md) owns input declarations,
causal history, common support, metrics and interpretation. This increment
performs no fitting, human-data intake or clinical evaluation.

## Install the bounded increment

Use the [SDK build/install procedure](installed-sdk.md#build-and-install), adding
`--m3-workbench` to `scripts/build_sdk.py`. That explicit build selects descriptor
6 with the existing four developer routes followed by `m3-compare`. The default
builder and `--mmtt-only`/`--integrated-candidate` retain descriptors 3/4/5 and
their exact task rosters. Those switches are mutually exclusive.

This source/data wheel requires POSIX CPython 3.12 and ships no numerical runtime.
The two supplied predictors use the standard-library worker, including the
existing portable Ridge prediction arithmetic. Genuine Ridge fitting and its
verification use the separately locked, policy-allowed M3 estimator environment;
never install it into the root or SDK environment. M4 retains its separate,
application-bound reviewed attachment. A new M3 wheel does not inherit the
previous M4 candidate's exact-artifact qualification.

## Use one project through Python or CLI

From an unrelated directory, run the installed environment's Python:

```python
import opent1d_lab as lab

inputs = lab.example("m3-compare", "/private/tmp/m3-inputs")["inputs"]
checked = lab.inspect_inputs("m3-compare", inputs)
project = lab.create_project("/private/tmp/m3-project", "Invented CGM comparison")
plan = project.freeze("m3-compare", inputs,
                      expected_input_sha256=checked["input_sha256"])["plan"]
project.check(plan)
attempt = project.run(plan)
project.reconstruct(attempt["attempt"], "/private/tmp/m3-report")
```

Choose fresh canonical absolute paths with existing parents. `inspect_inputs`
validates predictor metadata and captures input identities without executing
supplied Python. It copies readable observation bytes, but does not establish
valid CGM observations: `observation_bytes_verified` remains false. Missing or
unreadable observations retain their capture status; malformed and hash-mismatched
observations become explicit native failures when run. Every planned person,
origin and candidate remains in the frozen comparison.

The equivalent installed CLI uses the same service calls:

```bash
opent1d-lab example --task m3-compare --output /private/tmp/m3-cli-inputs
opent1d-lab create --project /private/tmp/m3-cli-project --name 'Invented CGM'
opent1d-lab freeze --project /private/tmp/m3-cli-project --task m3-compare \
  --config /private/tmp/m3-cli-inputs/comparison.json
opent1d-lab check --project /private/tmp/m3-cli-project --plan PLAN_ID
opent1d-lab run --project /private/tmp/m3-cli-project --plan PLAN_ID
opent1d-lab reconstruct --project /private/tmp/m3-cli-project \
  --attempt ATTEMPT_ID --output /private/tmp/m3-cli-report
```

Substitute the returned IDs. Incomplete evidence requires `--allow-failed` or
`allow_failed=True`. Retain every failed attempt; retries explicitly name the
previous terminal attempt. Interrupted starts use the existing explicit offline
recovery after the old executor has stopped. Capture and invocation copies are
retained in the project. A parent-linked derived plan uses `export_inputs` to
make fresh editable copies of retained resources.

## Use the workbench

Start `opent1d-lab gui --workspace /private/tmp/m3-workspace`. Create a project,
select **Frozen synthetic CGM predictors**, and prepare the invented example.
Alternatively, edit/upload a comparison JSON referencing absolute local synthetic
observation and reviewed predictor-declaration paths. The bounded raw editor is
limited to 128 KiB; larger configurations can use the SDK/CLI.

Validate the concept, inspect the complete roster and input hashes, then freeze
and run. Changing referenced bytes after validation refuses publication; freezing
checks the captured identities again inside the SDK transaction. Concepts and
revisions reopen through the existing workbench. Derivation exports private
copies; it never imports a predictor. Generic cross-plan comparison controls do
not replace the task-owned M3 common-support comparison.

The callback runs trusted local Python with the user's permissions. The worker
and deadline supervise it; they are not an operating-system sandbox. Review
supplied source before running. No dependency installation occurs. The causal
request contains only six exact five-minute CGM measurements, integer elapsed
microsecond timestamps and a 30-minute horizon, in mg/dL. Missing, censored, late
or cross-segment measurements are not imputed. Future meal/insulin features are
outside this contract.

## Reopen authoritative evidence

Verify a saved report before reading/downloading it. The parent report preserves
all candidate/person/origin outcomes, persistence, common support and exclusions.
A completed execution can still have incomplete cohort coverage. Shared slot
status records candidate/person completion; the native report owns scientific
eligibility, including complete workers, at least 288 shared origins and a
24-hour span. A long failed prefix never contributes to the primary result.

`project.relocate` copies the entire ledger. Open the copy and reconstruct its
original attempt with the same current trusted M3 readers. Original observation,
predictor and invocation paths are not opened. Archived Python remains opaque;
unknown reader/source/protocol identities and changed saved reports refuse.
The original native CLI/archive schemas remain available and unchanged.
This increment adds no reader migration exception or general archive importer.
Explicit `import_attempt`/CLI `import` can retain an existing direct M3 comparison
with exactly matching configuration and frozen predictor/observation bytes.
The ledger labels it retrospective `import`; it cannot stand in for prospective
execution. The same authoritative readers verify it after relocation.

The [integration record](research/installed-m3.md) distinguishes installed,
reference, browser and hosted checks, failures and outstanding evidence.
