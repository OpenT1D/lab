# P1/0.2 — Bring one rate controller to the M1 research task

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

**Task:** a simulation researcher supplies a local Python controller and asks
how missing meal announcements and a short sensor gap affect its recorded
outcomes under one synthetic M1 profile and seed. The workflow runs the
unchanged native simglucose physiology in conditions A–D. It records every
scheduled attempt, preserves native failures and reconstructs its report
without the simulator. This is a bounded checkout workflow, not a general
plugin API, an efficacy comparison, a clinical tool or P1 product acceptance.
The [P1/0.1 guide](p1-research-workflow.md) retains the two native references.
The [P1/0.3 worked example](p1-upstream-pid-tutorial.md) connects the pinned
third-party simglucose PID through this two-file intake. It reuses an M1
reference method and does not add an efficacy comparator. The
[P1/0.4 internal follow-up](research/p1-internal-followup.md) also checks a
distinct pinned proportional basal agent, within the same contract.

## Install and inspect the example

Use an identified checkout with Git, uv and Python 3.12 on macOS arm64 or
Linux x86-64. From the repository root:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python scripts/check.py
uv run --locked python -m experiments.p1_external preflight \
  --source experiments/p1_external/example
```

The example is invented OpenT1D code that demonstrates the interface. Its
commands are not a validated insulin strategy. The root environment is for
tooling; native execution uses the separately locked simglucose environment.
No participant records are included. A researcher can replace the two example
source files with their own trusted local controller; keep private code and
outputs outside version control. The intake copies those two files into its
output directory, so choose a location with suitable access controls.

## Controller contract

The source directory contains exactly `controller.py` and
`controller.json`, both regular files. The declaration names a source
identity, SHA-256 of the Python file, license, rights basis
(`author-owned`, `licensed` or `authorized-private`), exact installed
dependency versions and these fixed capabilities:

| Field | Required value |
| --- | --- |
| `schema` | `opent1d.p1-controller/1` |
| `step_minutes` | `3` |
| `observation` | `held-cgm-with-age/1` |
| `action` | `simglucose-pump-rate-u-min/1` |
| `missing_sensor` | `true` |

The Python file exports `make_controller(seed)`. Its returned object
implements `reset()` and `command(observation, announced_g)`. Each call
receives only the current synthetic scenario's released input:
`time_min`, `glucose_mg_dl`, `source_time_min`, `available`,
`age_min`, and the newly announced meal amount in grams. A held sensor
value keeps its original source time and has `available: false`. The
controller owns any memory it needs; it resets at the beginning of each case.
The supplied source must reproduce the same commands after that reset when
given the same seed and recorded inputs.

`command` returns exactly `basal_u_min` and `bolus_u_min` as finite,
nonnegative **rates**. The P1 intake bounds them at 0.2 and 2.0 U/min
respectively. The native pump may further clip or quantize a command;
reported delivered insulin is the modeled delivered rate integrated over
completed intervals. The `bolus` field is not a discrete pen dose. The
native engine owns physiology, sensor and pump behavior; the P1 workflow
owns the three-minute clock, announcements, masking and record.

The declaration validates syntax, exact source bytes, declared dependency
versions and required capabilities. Preflight also executes invented fresh,
held and recovery inputs. This is an **attestation by the supplier**, not a
legal determination of rights or an isolation sandbox. Supplied Python
executes with the user's local process permissions. Run code only when its
source and dependencies are trusted. The local user remains responsible for
license review and for keeping restricted inputs out of the repository.

## Run and inspect

Choose a new output path for each attempt:

```sh
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external run \
  --source experiments/p1_external/example \
  --output results/p1/external-example
```

The default is development profile `adult#001` and seed `101`. Only
`adult#002` and seed `102` are also supported. Four cases are scheduled
before execution. A case failure remains in `study.json`, its case
`manifest.json`, trace prefix and the report; the command exits nonzero
after writing the report. An interruption retains unattempted cases. Existing
output directories are refused. Open `report/report.md` first and retain
the whole study directory. The directory includes a copy of the declared
source, exact source and implementation hashes, native lock and source
fingerprints, per-case diagnostics, warnings and failure details.

Condition A has full announcements; B has none; C has half; D masks 30
minutes of noon CGM on the scored day. True meals stay the same. Each run
lasts up to 48 simulated hours, with the second day scored. A terminated or
incomplete run stays in the four-case denominator and unobserved minutes
are not assigned zero exposure.

## Reconstruct and verify actions

```sh
uv run --locked python -S -m experiments.p1_external reconstruct \
  --study results/p1/external-example \
  --output results/p1/external-rebuilt

uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external verify-actions \
  --study results/p1/external-example
```

`reconstruct` validates the schedule, source and case inventories, causal
observations, meals, masks and interval metrics, then compares both report
files byte for byte with the original. It neither imports simglucose nor
executes the supplied controller. `verify-actions` separately reloads the
copied controller and replays its recorded inputs without the simulator.
That command needs the controller's declared dependencies and proves action
repeatability for this saved trace, not biological or clinical validity.

## Remaining product gates

This invented example and local execution verify the software boundary. The
[pinned upstream PID example](p1-upstream-pid-tutorial.md) and
[distinct proportional source](research/p1-internal-followup.md) additionally
verify bounded third-party intake, but their rights packets need human review
and an independent intended researcher's execution, interpretation and
usability record are still needed for the P1 product claim. Neither a
comparison with the P1/0.1
references nor a benefit for people follows from these four synthetic
cases. See the [roadmap](../ROADMAP.md#p1--first-usable-research-product)
and [decision 0046](decisions/0046-p1-external-controller-boundary.md).
