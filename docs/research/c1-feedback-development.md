# C1/0.7 — Matched native feedback development

**OT-019 synthetic development, declared 25 September 2026.** This
pre-execution plan attaches the [C1/0.6 feedback kernel](c1-feedback-kernel.md)
to the pinned M1 simglucose basal-bolus route. It uses already inspected
M1/M2 profiles and schedules. Every numerical result is development
feedback, not an untouched evaluation or human treatment result.

## Fixed native boundary and settings budget

The M1 native controller computes basal and meal-bolus rates from only the
released CGM and meal announcement. The adapter converts **basal** U/min
to U/h, applies the feedback kernel, converts the bounded result back to
U/min, and passes the native meal bolus through unchanged. The native
patient, sensor, pump, three-minute step, meals, terminal condition and
profile parameters stay in M1. The candidate and matched comparator use
the same M1 base, observation, reset, limits and source ancestry; the
comparator alone sets the fresh-rise gain to zero. The earlier overlay and
bounded PID remain historical development routes.

The committed [setting declaration](../../experiments/c1/feedback-development.json)
allows **one setting attempt per feedback method** and no tuning within this
matrix. Its target is 160 mg/dL and fresh-low cutoff 90 mg/dL; `Kp` is
0.004 U/h per mg/dL, `Ki` is 0.00002 U/h per (mg/dL·min), and candidate
`Kr` is 0.05 U/h per (mg/dL/min), versus zero for the comparator. The
maximum rise is 2 mg/dL/min, fresh gap 6 min, absolute integral 600
mg/dL·min, upward correction step 0.2 U/h per update and final basal limit
4 U/h. These deliberately modest **invented engineering settings** are a
single exploratory attempt, not fitted gains, a clinical limit, or evidence
that either controller is suitable for a person. The 4 U/h and 0.2 U/h
boundaries retain the previous C1 native example's basal limit and upward
step for inspectability; the new target/gains test the redesigned two-sided
rule without claiming optimization.

The fixed roster is adult#001–002 × seeds 101–102 × conditions A–D:
**16 cells**, each with three separate native processes (unchanged M1
basal-bolus, feedback with rise, feedback without rise), or **48 planned
attempts**. The same schedules and seeds pair methods within each cell;
the repeated measurements are not independent people. A fresh base run
avoids comparing actions across different code revisions. Each worker has
its own input, process return record, sealed manifest, native runtime
inventory, interval trace and C1 command audit. The reader replays every
feedback state transition without importing simglucose. It checks the
action/trace relation, unchanged bolus, observation and meal boundaries,
source inventory and one clean revision across the matrix.

The scored second day uses the existing M1 interval percentages in
70–180, below 70, below 54 and above 250 mg/dL. Report each of the four
missing-announcement B cells separately and all A–D directions. A pair
with a failed, terminated, incomplete or unverifiable run has no invented
metric difference and stays in the planned denominator. Report candidate
versus base, comparator versus base and candidate versus comparator. A
positive in-range change alone cannot establish the C1 benefit claim; low
and high extremes, A preservation, coverage and reversals remain visible.

## Execution and evidence

From a **clean committed checkout** with the locked M0 simglucose native
environment already installed:

```sh
experiments/m0/simglucose/.venv/bin/python -m experiments.c1.feedback_study run \
  --output results/c1-feedback-development
```

Reconstruct without the simulator:

```sh
uv run --locked python -m experiments.c1.feedback_study report \
  --study results/c1-feedback-development
```

The output directory is ignored by Git. The
[local evidence index](../../experiments/c1/evidence-index.json) pins its
plan/report hashes and auxiliary native manifest hashes; it is not an
external backup.

## Completed known-case matrix

The matrix ran from clean commit `0a6b0e6` in
`results/c1-feedback-0a6b0e6`. All **48/48** processes returned zero,
passed their strict readers and completed **960/960** three-minute
intervals. Every manifest reports a clean worktree and the same revision.
All 32 feedback runs have one identical C1 source-hash inventory, and all
48 share one pinned native simglucose source fingerprint. A separate
fresh-process, simulator-free reconstruction was semantically identical to
the saved report. The report includes a manifest hash for every case;
the evidence index fixes the plan, settings and report hashes.

Paired scored-day differences below are **percentage points**. B has no
scored-day meal announcement. Rows are ordered by the declared profile and
seed; they are not independent human participants.

| B profile / seed | Candidate − base 70–180 | No-rise − base 70–180 | Candidate − no-rise 70–180 | Candidate − base below 70 | Candidate − base above 250 | Candidate − base A 70–180 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| adult#001 / 101 | +9.375 | +9.167 | +0.208 | −16.667 | −3.125 | +12.292 |
| adult#001 / 102 | −7.292 | −7.500 | +0.208 | 0 | −5.000 | −4.167 |
| adult#002 / 101 | −0.625 | −3.750 | +3.125 | 0 | −3.750 | 0 |
| adult#002 / 102 | −3.750 | −4.792 | +1.042 | 0 | −5.000 | 0 |

The rise term improves B 70–180 in **4/4** cells relative to its matched
zero-rise scaffold. That comparison isolates a term within this one
engineering setting. Relative to unchanged basal-bolus, the candidate
improves B 70–180 in **1/4** cells and decreases it in **3/4**. Its A
70–180 exposure decreases in adult#001/102. B below-54 exposure changes
by zero in every cell; B below-70 exposure improves in one and is equal in
three. B above-250 exposure decreases in all four candidate/base pairs.
Across A–D, candidate/base 70–180 improves in four, decreases in six and
is equal in six cells. These mixed directions and the A loss prevent
promoting this setting as a frozen beneficial controller. The matched
comparator is still an engineering ablation, not the separately required
strong published-method reference.

The saved feedback action audit contains 15,360 commands per method. Each
method has 40 held-observation base fallbacks (the four D sensor masks).
For these modest settings, no final-rate clamp, upward-slew limit or
anti-windup freeze activates in either native method. Those paths have
simulator-free arithmetic tests, but this matrix does not verify their
native behavior under activation. On B, the candidate's maximum commanded
basal rates by cell are 1.855, 1.940, 1.865 and 1.981 U/h, all below the
declared 4 U/h basal limit. The unchanged base bolus passes through each
feedback adapter; the strict reader checks it for every interval.

An additional **zero-gain adapter diagnostic**, outside the one-attempt
candidate/comparator setting budget, used the same adult#001/101/B native
case. Its initial point, complete 960-row trace and native diagnostic were
byte-identical to the new basal-bolus run. A fresh-process repeat of the
planned adult#001/101/B candidate also matched its initial point, trace,
command audit and native diagnostic byte for byte. Both auxiliary runs
retain separate local bundles and manifest hashes in the evidence index.
They are software checks, not further gain searches.

This synthetic matrix does not establish a controller improvement,
patient benefit or a treatment recommendation. A separate published-method
comparator, Cambridge adapter, exact new-scenario freeze and two-family
evaluation remain open. Further changes to the feedback method or gains
need a newly declared development attempt and retention of this mixed
result; the one-attempt C1/0.7 budget is spent.
The [C1/0.8 timing audit](c1-feedback-diagnostic.md) reconstructs the
saved interval crossings and declares one new matched target-alignment
attempt. It does not revise this C1/0.7 result.
