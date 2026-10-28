# P1/0.1 — First researcher workflow

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

**Task:** a simulation researcher asks how missing meal announcements or a
short sensor gap change the recorded outcomes of two existing reference
controllers under one fixed synthetic scenario. This workflow runs the
unchanged M1 simglucose physiology, basal-bolus and PID references for one
development profile and seed. It schedules both controllers under all four
information conditions before execution, retains failed runs, and produces
one readable report. It is an executable checkout workflow, not a general
model plugin API, clinical dosing tool, human-data analysis or a completed P1
usability assessment.

## Install

Use a checkout of an identified commit on macOS arm64 or Linux x86-64 with
Git, uv and Python 3.12 available. The first installation needs access to
the pinned public simglucose source and Python packages. From the repository
root:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked python scripts/check.py
```

The root environment contains tooling. The separate locked M0 environment
contains simglucose; P1 checks its version and the existing M1 native runner
checks the reviewed upstream source fingerprint. OpenT1D supplies no
participant data. The [M1 tutorial](m1-tutorial.md) records the source,
runtime advisory and original numerical verification in more detail.

## Run one question

Choose a new output directory each time. The default is development profile
`adult#001` and seed `101`:

```sh
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1 run --output results/p1/first-run
```

The only alternatives in P1/0.1 are `--profile adult#002` and `--seed 102`.
For example:

```sh
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1 run --profile adult#002 --seed 101 \
  --output results/p1/second-run
```

Open `results/p1/first-run/report/overview.md` first. It lists all eight
statuses, in-range and below-70 exposure, observed scored time and modeled
delivered insulin, then shows paired changes only for completed pairs. The
full `report/report.md` explains other metrics and limitations;
`report/report.json` retains the detailed inventory. Each case directory
contains its configuration, checkpoints, native diagnostics, logs, warnings,
source/environment identities and status. `workflow.json` binds the selected
profile/seed and P1 source hash; `study.json` preserves the full
schedule even if execution stops early. Existing output paths are rejected
instead of overwritten.

| Condition | Controller information on the scored day |
| --- | --- |
| A | Full meal announcements and sensor observations |
| B | Meal announcements absent; true meals unchanged |
| C | Half meal announcements; true meals unchanged |
| D | A 30-minute noon sensor mask; true meals unchanged |

This is the original M1 two-day protocol: day one initializes the native
simulation, and only day two is scored. Both controllers are existing
references. A reported direction for one profile and seed is a description
of this simulation, not evidence of superiority, a human effect, or a
recommended insulin dose. A native stop remains a failure in the eight-run
denominator; an unobserved scored interval does not become zero exposure or
zero delivered insulin. The possible `adult#001` seed-102 PID stop is
documented in the [M1 evidence record](research/m1-reproduction.md).

## Reconstruct without simglucose

Keep the whole study directory and use the same recorded source revision.
Rebuild into a new directory with root tooling and disabled site packages:

```sh
uv run --locked python -S -m experiments.p1 reconstruct \
  --study results/p1/first-run --output results/p1/rebuilt-first-run
```

The command validates the supported eight-case P1 schedule and M1 saved
artifacts, rebuilds the three report files without importing simglucose, and
compares them byte for byte with the original report when present.
`reconstruction.json` records the result and hashes. A started, interrupted
study with no original report can still be reconstructed; scheduled cases
without artifacts remain visible. A changed report or incomplete original
report is an error.

## What remains before P1 acceptance

The workflow must be run by an intended researcher outside its development
work. Record the checkout revision, operating system, install commands,
selected profile/seed, study status, report/reconstruction hashes, points of
confusion, failures and whether they could interpret the result without help.
That observation has not occurred. The separate independent M2 reproduction
criterion also remains open. The supported scope, upstream rights and
clinical-use limits are in the [model card](research/models/simglucose.md),
[licensing guide](licensing.md) and [roadmap](../ROADMAP.md#p1--first-usable-research-product).
