# C1/0.5 — Failure audit and feedback redesign

**OT-019 development, 25 September 2026.** This is a simulator-free audit
of the already inspected [C1/0.4 matrix](c1-known-development-matrix.md),
followed by a method/comparator decision. It opens no new scenario, changes
no M1/M2 native result and makes no superiority or human-use claim.
[Decision 0033](../decisions/0033-c1-feedback-redesign.md) supersedes the
first-method selection in decision 0032 while retaining that work as
history.

## Reconstructible inputs and method

`experiments.c1.diagnose` first invokes the C1/0.4 simulator-free reader.
It requires the saved report to match reconstruction, the indexed plan and
report hashes to match, all 64 cases to be completed with 960 intervals,
zero worker exit codes, one clean native commit and identical source
inventories within each engine route. It then reads the already verified
action traces. All calculations use commanded rates and scored-day
three-minute intervals; they do not infer actual insulin-on-board or
physiological causality.

From the repository root:

```sh
uv run --locked python -m experiments.c1.diagnose \
  --study results/c1-known-0c367fc \
  --output results/c1-method-audit.json
```

The `results` directory is ignored. Its retained JSON can be regenerated
from the 64 local native bundles listed by the
[evidence index](../../experiments/c1/evidence-index.json). If those local
bundles are unavailable, the committed C1/0.4 numerical record remains a
report, not a substitute for independently rerunning the simulator.

The audit was run from clean code commit `97f583a` against the unchanged
native C1/0.4 bundles from `0c367fc`. Its local JSON has SHA-256
`a5a050c4ba851e6215d4f48eadac91004d6911f5759150f317404d87e65e5a31`;
a fresh-process repeat was byte-identical. The evidence index records these
local files and the source revision. This verifies deterministic offline
analysis, not a new native controller result.

## What failed in the first overlay

The first scored-day true meal occurs at minute 1860; condition B announces
none of that day's meals. In all four B cells, the original overlay's first
extra command occurs **63–72 minutes later**. Its total scored-day extra
commands are **0.321–0.403 U**. The higher-target variant first acts
**114–366 minutes** after that first meal and commands **0.148–0.268 U**
over the scored day. These are small, late adjustments in the saved
controller traces, not a measured meal detector. Later true meals and sensor
feedback also contribute; the latency is only relative to the first meal.

In adult#001/101/B, the original overlay's additional below-70 interval
starts at minute **1773**, before the first scored meal and before its first
scored extra command at **1926**. Its warmup extra commands total **0.191 U**;
the higher-target variant has **0.007 U** and no added below-70 interval.
The trace order excludes a preceding scored-day extra command as the direct
trigger. It does not isolate warmup commands as the cause of the glucose
difference.

The original overlay gives **no positive 70–180 difference in any B cell**
and worsens below-70 exposure in one. The higher-target variant removes
that observed low-exposure regression but has **zero 70–180 gain in all four
B cells**. Increasing the threshold alone therefore leaves the selected
missing-meal benefit hypothesis unsupported on these known cases.

## Why the current PID is not the strong comparator

The C1 adapter adds the pinned native PID correction to basal-bolus and
then clamps the combined basal rate to 0–4 U/h, with an upward slew limit.
The [pinned native PID source](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/pid_ctrller.py)
accumulates the glucose error on every update; the [M1 wrapper](../../experiments/m1/control.py)
provides no feedback about that later
clamp. That is a source-level **anti-windup gap**. It does not by itself
prove why a particular modeled glucose trajectory changed.

On the B scored day, the saved *requested* rate reaches a clamp boundary
in many of the 480 intervals:

| Virtual profile / seed | Requested 0 U/h | Requested 4 U/h | Either bound |
| --- | ---: | ---: | ---: |
| adult#001 / 101 | 220 | 250 | 470/480 |
| adult#001 / 102 | 229 | 238 | 467/480 |
| adult#002 / 101 | 113 | 174 | 287/480 |
| adult#002 / 102 | 134 | 305 | 439/480 |

These are request-clamp counts, not delivered insulin or patient events.
The PID has 70–180 gains in three B cells and a loss in one; below-70 and
above-250 exposure each worsen in two B cells. Across A–D it increases
below-54 exposure by 4.167 percentage points in adult#001/102/C.
Completing all 16 cells demonstrates software coverage, while this action
pattern and the outcome reversals prevent treating the adapted PID as a
qualified strong reference.

## Method and comparator decision

Retire the original one-sided overlay as the **lead** C1 method for this
hypothesis, preserving both tested settings and their negative results.
The next method family is a bounded **two-sided feedback correction** on
the unchanged basal-bolus base action. It must have an explicit anti-windup
state update and use only released CGM/announcement history and its own
actions. A fresh-CGM trend term is an optional candidate component. The
matched engineering comparator uses the same scaffold with that term
disabled, so their difference tests the added trend response under equal
limits and development opportunity. The native PID and basal-bolus remain
historical anchors.

For the next **unconfigured kernel**, use an explicit correction in U/h:
proportional error plus an anti-windup integral of elapsed glucose error,
with an optional term from the rise between successive fresh observations.
The matched engineering comparator sets only that rise gain to zero. The
adapter must clamp the **final basal rate** between zero and the declared
maximum and keep the native meal bolus unchanged. Log the requested rate,
clamp and actual command separately. A fresh low observation permits a downward
correction but blocks a positive correction; a held observation falls back
to the native base without integrating stale error. The exact discrete
integral, slew and reset equations and all gains remain to be specified
and tested **before** native scoring. No physiological insulin-on-board is
inferred from a command history.

A source-traced published comparator is still required for a C1 superiority
test. A small published PID-plus-insulin-feedback crossover study found less
late hypoglycemia in its own setting
([Ruiz et al., 2012](https://pubmed.ncbi.nlm.nih.gov/23063039/)); a separate
randomized MPC/PID crossover included an unannounced meal
([Pinsker et al., 2016](https://pubmed.ncbi.nlm.nih.gov/27289127/)).
Neither supplies verified numerical settings or direct validation for our
proposed kernel. Before native scoring, specify the exact new state update,
limits, stale-observation fallback and matched setting-attempt budget.
Cambridge integration and the final new-scenario freeze remain closed.

The subsequent [C1/0.6 kernel](c1-feedback-kernel.md) fixes and tests the
discrete conventions above without selecting gains or running a native
simulation. This C1/0.5 audit remains the record of the earlier evidence.
