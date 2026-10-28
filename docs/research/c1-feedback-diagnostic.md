# C1/0.8 — Feedback timing audit and next development gate

**OT-019 development, 25 September 2026.** This audit reconstructs the
already completed [C1/0.7 native matrix](c1-feedback-development.md) from
sealed local artifacts. It opens no new scenario, selects no successful
controller and changes no earlier numerical result. [Decision 0035](../decisions/0035-c1-target-alignment-followup.md)
records the bounded next hypothesis.

## Reproducible audit

From the repository root:

```sh
uv run --locked python -m experiments.c1.feedback_diagnose \
  --study results/c1-feedback-0a6b0e6 \
  --output results/c1-feedback-audit-273d29d.json
```

The simulator-free reader first verifies the saved 48-case report against
reconstruction, the [evidence index](../../experiments/c1/evidence-index.json),
all process returns, 960 intervals per case, clean native revision, source
maps and pinned upstream fingerprints. It then classifies each paired
three-minute interval using M1's scored **subcutaneous glucose** criterion
`70 ≤ G ≤ 180` mg/dL. It records gains from below 70 or above 180,
losses to below 70 or above 180, and commanded correction in U. The
seven fixed windows are warmup (0–1440), scored pre-breakfast (1440–1860),
breakfast-to-lunch (1860–2160), lunch-to-snack (2160–2400),
snack-to-dinner (2400–2520), dinner-to-late (2520–2820), and the final
hour (2820–2880), all in minutes. Net interval counts must reproduce the
scored 70–180 percentage-point difference exactly within floating-point
rounding.

The audit ran from clean analysis commit `273d29d`; the local JSON SHA-256
is `eeedfc714083c8c49bcbebe1d8a01cddd7c739462c11b2c3a8073e29e3e21f60`.
A second fresh process produced byte-identical JSON. The JSON inventories
the analysis Python sources and all 16 A–D cells. The ignored local store
is not an external backup. The committed C1/0.7 report remains the
numerical source for scored-day outcomes.

## Where the differences appear

On scored condition B, all four candidate runs command **140/140
downward corrections** before the first scored breakfast at minute 1860;
the net commanded corrections in that seven-hour window are −1.850 to
−2.344 U. Warmup correction is also negative, −1.089 to −2.167 U across
these four cells. The first positive correction after breakfast occurs
57–66 minutes after that meal. These are commanded rates integrated over
time, not measured delivery or physiological insulin-on-board.

| B profile / seed | Pre-breakfast correction U | First positive correction after breakfast | 70–180 intervals gained from below 70 vs base | 70–180 intervals lost above 180 vs base | Net scored 70–180 change |
| --- | ---: | ---: | ---: | ---: | ---: |
| adult#001 / 101 | −2.344 | 60 min | 80 | 35 | +45 intervals (+9.375 pp) |
| adult#001 / 102 | −2.135 | 57 min | 0 | 35 | −35 intervals (−7.292 pp) |
| adult#002 / 101 | −1.993 | 60 min | 0 | 3 | −3 intervals (−0.625 pp) |
| adult#002 / 102 | −1.850 | 66 min | 0 | 18 | −18 intervals (−3.750 pp) |

Every B in-range loss is a candidate value **above 180** while the paired
base is within 70–180; none is a loss to below 70. The first B loss begins
at minute 2091 in both adult#001 seeds, 2214 in adult#002/101 and 2040
in adult#002/102. The sole positive B net result depends on 80 pre-breakfast
intervals in which the candidate is in range and basal-bolus is below 70;
it also has 35 later high-side losses. This is a threshold decomposition,
not attribution of those losses to any particular earlier command.

Under full announcements (A), adult#001/102 loses 20 in-range intervals
**above 180** between lunch and snack, first at minute 2214. Its
pre-breakfast correction is −2.135 U. Adult#001/101 instead gains 80
pre-breakfast intervals from below 70 and loses 21 high-side intervals
after lunch. The two adult#002 A cells have no net threshold differences.
The rise term is active in 65–73 of the 140 scored pre-breakfast intervals
per B cell, even though no scored meal has yet occurred. It is therefore
an observed CGM-rise feature, not a demonstrated meal detector. Against
the matched no-rise scaffold, the candidate recovers 1, 1, 15 and 5 B
in-range intervals from the high side, with no low-side threshold changes.
Neither method reaches its basal clamp or upward slew limit in this matrix.

Because candidate and base trajectories already diverge during warmup,
these aligned traces show **when** actions and threshold differences
occur, not the physiological cause of the later difference. A separately
controlled native ablation would be needed for causal attribution. The
current setting still fails the development screen against basal-bolus in
three B cells and one A cell; a rise-term advantage over its ablation does
not repair that.

## One-factor follow-up, declared before new native work

The [pinned M1 basal-bolus wrapper](../../experiments/m1/control.py)
uses a 140 mg/dL target. The C1/0.7
feedback error target was 160 mg/dL. A lower feedback target could reduce
the persistent pre-breakfast downward correction and advance the first
positive post-meal action; it could also remove the observed low-exposure
benefit or worsen lows. This is a falsifiable **engineering hypothesis**,
not a predicted benefit. The
[C1/0.9 declaration](../../experiments/c1/feedback-target-alignment.json)
changes **only** the feedback target from 160 to 140 mg/dL. Proportional,
integral and rise gains, low cutoff, all limits, native base and native
bolus stay fixed. The matched comparator again changes only its rise gain
to zero. The [plan generator](../../experiments/c1/feedback_target_plan.py)
rejects any second parameter change.

```sh
uv run --locked python -m experiments.c1.feedback_target_plan \
  --output results/c1-feedback-target-plan.json
```

The committed declaration and materialized 48-case plan are hash-indexed
locally. Materializing the plan does not execute or score a simulator.

That declaration permits **one new setting attempt per feedback method**
(two cumulative attempts per method including C1/0.7), on the same 16
already known profile/seed/condition cells. A future native round would
run a fresh basal-bolus case and both feedback methods in each cell: 48
separate planned processes. It must retain every attempt, failure and
partial run, replay commands without a simulator, and report B and A
threshold flows, below-70/below-54 and above-250 exposure, commanded and
modeled insulin, stops and limit events. No C1/0.9 native run has been
started in this audit.

The **development advancement screen** is fixed before that round:
candidate versus basal-bolus must have positive B 70–180 differences in
each of the four cells, no B increase below 70, below 54 or above 250,
and no A decrease in 70–180 or increase below 70 or below 54 in any cell.
All 48 cases must complete and verify. Failure leaves this one-factor
attempt negative and calls for a new method assessment rather than an
undeclared third setting search. Passing would permit further comparator
and transfer work, not establish superiority: an eligible published
reference, Cambridge integration and a prespecified new-scenario freeze
remain separate gates.

The subsequently executed [C1/0.9 result](c1-target-alignment-results.md)
completes this fixed round and records a failed development screen.
