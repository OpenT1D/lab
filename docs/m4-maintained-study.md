# Run the maintained M4 initial-load study

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

`m4-study-secure` is an explicit execution successor to the
[configurable M4 study](m4-configurable-study.md). It inherits the same synthetic
0/15/30 gram initial gastric conditions, secretion equations, adult#001,
240-minute grid, controls, refinement limits and fresh-process repeats. Its
[separate protocol](research/m4-secure-runtime-protocol.md) binds a maintained
native environment and an explicitly identified reference execution.

The old M4-STUDY/2 and M4-COMPARISON/1 protocols, locks and records retain their
original meanings. The successor does not relabel an old execution or establish
biological validity. Use the [historical-reader route](historical-readers.md)
to reconstruct an old archive with its identified trusted reader checkout.

## Install and check explicitly

From an identified checkout with Python 3.12 and uv:

```sh
uv sync --locked
.venv/bin/python -B -S -m experiments.setup plan m4-study-secure \
  --output results/maintained-setup-plan
.venv/bin/python -B -S -m experiments.setup install \
  --plan results/maintained-setup-plan --output results/maintained-setup-install
.venv/bin/python -m experiments.workflows check m4-study-secure \
  --config experiments/m4/secure_study/example.json
```

The maintained project is `experiments/m0/simglucose_secure`; observation still
uses the separate beta-cell runtime. The new lock changes HTTP/setup packages,
retaining the attributed engine and core numeric pins. A narrow explicitly
activated resource compatibility adapter replaces the two removed
`pkg_resources` operations used by those pinned engines. Runtime attestation
checks the complete installed package inventory and upstream source identities.
Readiness remains separate from numerical acceptance.

## Configure, run and reconstruct

Start with `experiments/m4/secure_study/example.json`, whose schema is
`m4-secure-study-config/1`. Declare two to eight reviewed Python source and
declaration pairs, select an ordered nonempty subset of `fasting`,
`gastric_load_15g` and `gastric_load_30g`, and retain explicit stage and source
budgets. Sources are trusted local code and execute with your permissions.
The configuration introduces no meal-event times or parameter fitting.

```sh
.venv/bin/python -m experiments.workflows run m4-study-secure \
  --config experiments/m4/secure_study/example.json \
  --output results/maintained-study
.venv/bin/python -B -S -m experiments.workflows reconstruct m4-study-secure \
  --archive results/maintained-study --output results/maintained-study-rebuilt
```

Every output is fresh. Without `--reference`, the coordinator generates its own
`m4-secure-reference-run/1` archive: inherited BC-008 science, explicit maintained
execution. A supplied reference must pass its authoritative verification.
Failed archives require explicit `--allow-failed` reconstruction and retain
their failed status. Inspect `report.md`, `report.json`, `figure.svg` and the
manifest; planned/accepted source, load and pair denominators remain visible.

The [local GUI](local-gui.md) calls this registered route. The catalogue and
task-directed setup register its explicit identity alongside the seven existing
routes. Historical local campaigns initially remain bound to `m4-study`; a
maintained campaign successor needs its own frozen administration contract.

## Interpretation

Model ancestry, units, basal ownership, actual installed runtime, scientific
source snapshots and failures are recorded separately from GUI administration.
The successor's report distinguishes descriptive synthetic contrasts from
numerical checks. It does not infer a treatment effect, human calibration or
general model compatibility. Actual verification and independent-user evidence
are recorded separately in the roadmap.
