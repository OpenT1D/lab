# P1/0.3 — Run the pinned upstream PID yourself

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This worked example connects an existing third-party CGM controller to the
bounded [P1/0.2 research task](p1-external-controller.md). It uses invented
meals and a synthetic virtual profile. It is research software, not a dosing
method or a test with a person. The [verification record](research/p1-upstream-pid-verification.md)
documents source, behavior, rights questions and the internal run.

## Supported setup

Use Git, `uv` and Python 3.12 on macOS arm64 or Linux x86-64. Start from an
identified clean checkout of OpenT1D. The supplied PID bundle depends on
`simglucose==0.2.11` at the exact revision in the locked native environment.
It accepts the fixed three-minute CGM/U/min contract; it does not support
discrete insulin doses, a general model API, or human data.

From the repository root:

```sh
git rev-parse HEAD
git status --short
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose \
  python -m unittest experiments.p1_external.test_simglucose_pid_native
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external preflight \
  --source experiments/p1_external/simglucose_pid
```

The test should report two passing tests and preflight should return
`contract_checked`. A source-hash or dependency error means the installed
controller is not the declared one; stop and record the error. Review the
two-file bundle and the installed dependency before running: supplied Python
executes locally with your permissions. The declaration alone does not grant
rights to redistribute code or output.

## Run, reconstruct and interpret

Choose a new directory below ignored `results/` for each attempt:

```sh
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external run \
  --source experiments/p1_external/simglucose_pid \
  --output results/p1/my-upstream-pid

uv run --locked python -S -m experiments.p1_external reconstruct \
  --study results/p1/my-upstream-pid \
  --output results/p1/my-upstream-pid-rebuilt

uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external verify-actions \
  --study results/p1/my-upstream-pid
```

Open `results/p1/my-upstream-pid/report/report.md` first. Check that all
four scheduled conditions are accounted for, including any failures, then
inspect `report/report.json` and the case manifests. Reconstruction should
report `byte_identical_to_original: true`; action verification should report
3,840 replayed actions when all four cases reach the full horizon. Preserve
the entire study directory when sharing a result, with its access controls.
The commands reject an existing output directory; choose another name for
a retry.

The upstream PID uses CGM alone. Equal A/B/C outcomes are therefore an
expected method property, not proof that meal announcements never matter.
D repeats a held CGM value during the mask, and the PID still updates its
state. The adapter clips upstream signed basal output to 0–0.2 U/min and
returns zero bolus. Inspect the [verification record](research/p1-upstream-pid-verification.md)
before interpreting any metric; these synthetic results establish neither
clinical safety nor benefit.

## Independent intended-user exercise

An intended simulation researcher or algorithm developer who did not build
this workflow should complete the setup and run above without live coaching.
The research task is to connect the supplied external PID bundle, identify
what A–D change, and explain what the report supports. If the participant
also has a trusted local controller that fits the two-file contract, they
may test it in a separate private study; this is optional and must not be
uploaded without its rights review.

This worked bundle is maintained with the pinned M1 environment. A changed
upstream PID file must fail its source-hash check until the source, rights,
method behavior and lock are reviewed together. The project currently
supports this declared checkout task, not arbitrary controller packages;
report reproducible installation, contract or reconstruction failures through
the project's [support route](../SUPPORT.md) with the checkout revision and
synthetic error details. Keep private controller code and health information
out of issue reports.

The facilitator should give this guide and the repository revision, then
record the following without filling in answers for the participant:

| Field | Record |
| --- | --- |
| Participant role and prior OpenT1D experience | |
| Date, OS, Python/uv versions, checkout commit | |
| Start/end time and whether assistance was requested | |
| Preflight, four-case, reconstruction and replay outcomes | |
| Participant's explanation of A/B/C and D | |
| Errors, confusing instructions and workarounds, with exact step | |
| Rights or source questions they could not resolve | |
| Participant's verdict: usable for the declared task, with reasons | |

Keep a non-identifying record unless the participant agrees to attribution.
Retain actual commands, exit codes and report hashes in a private review
packet; do not commit private code, contact details or health records. A
maintainer then reviews the deviations and rights packet against the
[P1 acceptance criteria](../ROADMAP.md#p1--first-usable-research-product).
An agent-run repetition or CI pass cannot substitute for this user exercise.
