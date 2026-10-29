# P1 — Independent researcher exercise

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This exercise asks a simulation researcher or algorithm developer who did not
build the P1 workflow to connect one declared external controller, complete a
synthetic experiment, and explain its reconstructible report. It is the
intended-user exercise for [P1 product acceptance](../ROADMAP.md#p1--first-usable-research-product).
The [acceptance review packet](research/p1-product-acceptance-review.md)
records the conditional distribution-rights decision made by a human reviewer
for the exact internal handoff
and what the maintainer must decide after the run.
Completing this exercise alone does not accept the product.

Use invented scenarios only. Do not enter personal glucose records, use the
software to choose insulin doses, or connect a medical device. The supplied
controller is local Python that runs with your permissions: inspect its
two-file bundle and installed dependency before executing it. Preserve errors
and incomplete runs instead of repairing the source during this exercise.

## Task and supported setup

Use an identified clean OpenT1D checkout, Git, `uv`, and Python 3.12 on
macOS arm64 or Linux x86-64. The supplied
[`glucosim_heuristic` bundle](../experiments/p1_external/glucosim_heuristic/controller.py)
imports GlucoSim from an exact Git revision and accepts the three-minute
held-CGM/U/min rate contract. The experiment uses one invented M1 profile,
`adult#001`, seed `101`, and four scheduled conditions A–D. It does not
accept a discrete pen dose or human observations.

The facilitator provides this page and the checkout revision. Work without
live coaching. If you need help, ask normally and record what help was
needed; do not hide it to make the exercise appear independent.

From the repository root, record these outputs first:

```sh
git rev-parse HEAD
git status --short
uv --version
```

Check the declaration and source in
`experiments/p1_external/glucosim_heuristic/`, and the pinned dependency in
`experiments/m0/simglucose/pyproject.toml`. Record any source, license or
rights question you cannot answer. Then install and check the bundle:

```sh
uv sync --locked
uv run --locked python --version
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external preflight \
  --source experiments/p1_external/glucosim_heuristic
```

Preflight should return `contract_checked`. Stop and record a source-hash,
dependency or contract error; it is part of the usability result.

## Run and inspect

Choose a new output name under ignored `results/`. For a first attempt:

```sh
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external run \
  --source experiments/p1_external/glucosim_heuristic \
  --output results/p1/acceptance-glucosim-1 \
  --profile 'adult#001' --seed 101

uv run --locked python -S -m experiments.p1_external reconstruct \
  --study results/p1/acceptance-glucosim-1 \
  --output results/p1/acceptance-glucosim-1-rebuilt

uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external verify-actions \
  --study results/p1/acceptance-glucosim-1
```

The commands refuse existing output directories. Use a new name for a retry
and keep the failed attempt. Open `results/p1/acceptance-glucosim-1/report/report.md`
first. Check the status of all four cases, then inspect `report/report.json`,
`study.json`, and one case manifest. If all four cases complete, action
verification should replay 3,840 actions. Reconstruction should record
`byte_identical_to_original: true` in its `reconstruction.json`. Record any
different outcome with its command and exit code.

Explain in your own words, using the report and source:

1. What changes between conditions A, B, C and D, and what remains fixed?
2. Which observations can the controller use during the CGM mask? Does it use
   meal announcements?
3. What is the difference between a commanded rate and delivered insulin in
   this report? What do the rate units mean?
4. What can the synthetic results support, and what can they not establish
   about another controller, a person or clinical safety?
5. Could you repeat or investigate this workflow from the saved study
   directory? Which step or message was unclear?

Do not compare these numbers with the PID as an efficacy ranking. The
[P1/0.4 technical record](research/p1-internal-followup.md) provides source
and method details for later review; read it after recording your own
interpretation if you have not already seen it.

## Exercise record

The facilitator records the participant's responses without filling them in.
Keep a non-identifying private record unless the participant agrees to
attribution. Do not commit contact details, private controller code, health
records or the full study directory.

| Field | Record |
| --- | --- |
| Participant role and prior OpenT1D experience | |
| Date, OS, Python/uv versions and checkout commit | |
| Start/end time and any assistance requested | |
| Actual commands, exit codes and output locations | |
| Preflight, A–D status, reconstruction and replay outcomes | |
| Report hashes and retained study location | |
| Participant's answers to questions 1–5, in their own words | |
| Errors, confusing instructions and workarounds, with exact step | |
| Source and rights questions raised | |
| Participant's verdict on usability for this task, with reasons | |

The maintainer reviews the actual record and deviations against the
[P1 acceptance criteria](../ROADMAP.md#p1--first-usable-research-product).
An agent run or CI pass cannot substitute for this independent exercise.
