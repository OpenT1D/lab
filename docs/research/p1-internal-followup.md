# P1/0.4 — Internal controller compatibility follow-up

**Scope:** repeat the pinned simglucose PID on the second supported synthetic
profile/seed pair, then pass a different third-party controller through the
unchanged P1/0.2 two-file intake. This is internal software verification.
Neither run is an efficacy comparison, clinical assessment, general plugin
interface, or P1 product acceptance.

## Second supported PID configuration

The [P1/0.3 source and method record](p1-upstream-pid-verification.md) uses
`adult#001` and seed `101`. From clean revision `6b862b3`, the same pinned PID
bundle passed preflight and ran on `adult#002`, seed `102`. Each of A–D
completed 960 intervals. All case manifests recorded `worktree_dirty: false`.
Source-only verification replayed 3,840 actions; simulator-free reconstruction
produced byte-identical JSON and Markdown reports. The reconstructed JSON
SHA-256 is `55ebc39132a525509ebf22c5a4325a03a952092989aaadc91b901ca446348d96`.
The complete ignored local study is at
`results/p1/upstream-pid-adult002-102-6b862b3/`.

| PID configuration and condition | 70–180 mg/dL (%) | Below 70 mg/dL (%) | Delivered insulin (U) |
| --- | ---: | ---: | ---: |
| `adult#001`, 101, A | 38.958 | 13.958 | 97.083 |
| `adult#001`, 101, D | 38.958 | 13.958 | 97.146 |
| `adult#002`, 102, A | 53.750 | 18.750 | 61.965 |
| `adult#002`, 102, D | 53.750 | 19.167 | 61.720 |

Within each configuration, A/B/C numerical glucose, CGM and action traces
match because this PID ignores meal announcements. The D sensor mask changed
24 commanded intervals in the first configuration and 147 in the second.
In `adult#002` A, 394 basal commands were zero and none reached the P1
0.2 U/min maximum; the highest recorded command was 0.196042 U/min. The
profile **and** seed changed together, so the rows are separate technical
exercises, not a paired population comparison or a controller ranking.

## Different external source: GlucoSim proportional basal agent

The second source is Hass Dhia's
[`HeuristicBasalAgent`](https://github.com/HassDhia/glucosim/blob/6422a91d533125a8feb4f2e8737aecd67fec95c9/src/glucosim/agents/heuristic.py)
from `HassDhia/glucosim` commit `6422a91d533125a8feb4f2e8737aecd67fec95c9`,
package version `0.1.2`. The installed `heuristic.py` SHA-256 is
`8528202b65e2068f5520e066add8293c944136f5d936dc2e30d5e9512878e6aa`.
The repository declares [MIT terms](https://github.com/HassDhia/glucosim/blob/6422a91d533125a8feb4f2e8737aecd67fec95c9/LICENSE).
The native environment pins the Git commit; the [two-file P1 adapter](../../experiments/p1_external/glucosim_heuristic/controller.py)
imports the installed class and checks that source hash. It does not copy
the upstream controller code.

This agent is a proportional CGM policy, unlike the M1 PID's proportional,
integral and derivative state. Its upstream `predict` reads only `obs[0]`:
CGM in mg/dL. Default target 120 mg/dL, base 1 U/hour and gain 0.005
U/hour per mg/dL yield a basal action clipped upstream to 0–3 U/hour.
The adapter supplies only the released P1 CGM, including the held value
during a mask, and divides the upstream action by 60 to obtain U/min. It
ignores announcements, returns zero bolus, and does not supply IOB, patient
parameters, latent glucose or future events. It checks the three-minute P1
clock; upstream `reset` has no controller state to clear. The 0–3 U/hour
upstream bound maps to 0–0.05 U/min, within P1's 0–0.2 U/min bound. This
explicit conversion preserves the upstream policy equation, but its
simulation setting and available observations differ from GlucoSim's own
environment. Its published description is not evidence of clinical validity.

Method-specific native tests passed for the upstream source hash, proportional
arithmetic, held CGM, rate units, clock and reset. P1 preflight returned
`contract_checked`. From clean revision `d6e97db`, all four 960-interval
synthetic `adult#001`, seed `101` cases completed with clean manifests.
Source-only verification replayed 3,840 actions, and simulator-free
reconstruction gave byte-identical reports. The reconstructed JSON SHA-256
is `f76ae684480fbfc5210349e4010775512a0642cc94f6554364b15dc6363983f6`.
The complete ignored local study is at
`results/p1/glucosim-heuristic-clean-d6e97db/`.

| GlucoSim condition | 70–180 mg/dL (%) | Below 70 mg/dL (%) | Delivered insulin (U) |
| --- | ---: | ---: | ---: |
| A, full announcements | 29.167 | 0.000 | 34.292 |
| B, no announcements | 29.167 | 0.000 | 34.292 |
| C, half announcements | 29.167 | 0.000 | 34.292 |
| D, 30-minute CGM mask | 29.167 | 0.000 | 34.298 |

A/B/C numerical traces match as expected for an announcement-blind method.
D changed 240 commanded intervals relative to A. In A, the recorded basal
commands ranged from 0.016662 to 0.031461 U/min; none reached a P1 rate
bound. These rounded outcomes from one invented profile/seed do not compare
clinical safety or efficacy with PID or any other method.

## Reproduce and interpret

From a clean checkout, use Git, `uv` and Python 3.12 on the supported
macOS arm64 or Linux x86-64 setup. Choose new output directories under
ignored `results/`; the commands refuse existing directories.

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose \
  python -m unittest experiments.p1_external.test_glucosim_heuristic_native
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external preflight \
  --source experiments/p1_external/glucosim_heuristic
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external run \
  --source experiments/p1_external/glucosim_heuristic \
  --output results/p1/my-glucosim-heuristic
uv run --locked python -S -m experiments.p1_external reconstruct \
  --study results/p1/my-glucosim-heuristic \
  --output results/p1/my-glucosim-heuristic-rebuilt
uv run --locked --project experiments/m0/simglucose \
  python -m experiments.p1_external verify-actions \
  --study results/p1/my-glucosim-heuristic
```

For the second PID configuration, use the
[P1/0.3 guide](../p1-upstream-pid-tutorial.md) with
`--profile 'adult#002' --seed 102` on its `run` command. Preserve each
complete study directory as the numerical record. A new run may have
different report hashes because manifests include elapsed runtime; verify
byte identity within that run and compare numerical metrics separately.

The dependency and adapter declarations establish source identity for this
local task, not redistribution permission. Human review of upstream notices,
parameter provenance and intended distribution, plus independent intended
user execution, remain open [P1 product gates](../../ROADMAP.md#p1--first-usable-research-product).
The [acceptance exercise](../p1-acceptance-exercise.md) and
[review packet](p1-product-acceptance-review.md) define the next records.
