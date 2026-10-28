# C1/0.9 — Target-alignment development result

**OT-019 known synthetic development, 25 September 2026.** This is the
single one-factor follow-up declared in the [C1/0.8 timing audit](c1-feedback-diagnostic.md)
before native scoring. Feedback target changed from 160 to 140 mg/dL for
both the candidate and its zero-rise comparator. The M1 basal-bolus base,
all other feedback settings, 16 known cells and four criteria groups stayed
fixed. The comparison is development evidence, not a held-out controller
evaluation or a result in people.

## Reproduce and verify

The [runner](../../experiments/c1/feedback_target_study.py) and tests were
committed at `f43bb85b71b30182b95009f485d5a6afd1a3fb71` before native
execution. From a clean checkout of that revision with the locked M0
simglucose environment installed, run:

```sh
experiments/m0/simglucose/.venv/bin/python -m experiments.c1.feedback_target_study run \
  --output results/c1-target-f43bb85 --workers 4
uv run --locked python -m experiments.c1.feedback_target_study report \
  --study results/c1-target-f43bb85
uv run --locked python -m experiments.c1.feedback_target_study assess \
  --study results/c1-target-f43bb85 \
  --output results/c1-target-assessment-f43bb85.json
```

The ignored local store is `results/c1-target-f43bb85`. Its study plan,
declaration copy, matrix report and separate assessment have SHA-256 values
in the [evidence index](../../experiments/c1/evidence-index.json). The
predeclared, separately materialized canonical plan has its earlier hash;
the study's `plan.json` has a different byte layout but the same verified
48-case content. A fresh-process simulator-free report was semantically
identical to the saved report. A fresh-process assessment was byte-identical
to the first assessment. These local artifacts are not an external backup.

All **48/48** separately recorded processes returned zero and passed the
strict readers, with **960/960** three-minute intervals per case. All
manifests record the same clean source revision. The feedback source map
and pinned native simglucose fingerprint are each consistent across their
respective cases. The readers check causal CGM and meal boundaries,
command/trace identity, replay the feedback state, and retain incomplete
or failed attempts in the planned denominator with no fabricated deltas.
No native stops occurred in this matrix.

## Scored-day results

The values below are **percentage-point differences** over the scored
second day. B has no scored-day meal announcements. Each row is one known
profile/seed cell, not an independent person. The zero-rise comparator is
an engineering ablation, not a strong published-method reference.

| B profile / seed | Candidate − base 70–180 | No-rise − base 70–180 | Candidate − no-rise 70–180 | Candidate − base below 70 | Candidate − base below 54 | Candidate − base above 250 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| adult#001 / 101 | +12.708 | +11.667 | +1.042 | −13.750 | 0 | −8.333 |
| adult#001 / 102 | **−0.833** | −3.333 | +2.500 | 0 | 0 | −10.833 |
| adult#002 / 101 | +2.292 | +1.250 | +1.042 | 0 | 0 | −7.708 |
| adult#002 / 102 | +3.750 | +2.708 | +1.042 | 0 | 0 | −8.750 |

The candidate gains B 70–180 exposure in **3/4** cells versus basal-bolus;
the adult#001/102 cell loses four of 480 scored intervals above 180, for
−0.833 pp. B below-70 and below-54 exposure never increases; B above-250
exposure falls in all four cells. The rise term improves B 70–180 relative
to no-rise in all four cells, but that does not meet the base comparison
criterion. A's adult#001/102 cell loses 11 in-range intervals above 180,
or **−2.292 pp**. Its other three A cells change by +11.250, 0 and 0 pp;
none increases below-70 or below-54 exposure. Across C and D separately,
candidate/base 70–180 changes are one gain, one loss and two ties each;
these are visible in the complete report but were not advancement gates.

In B, the target reduction lessens the negative commanded correction
before breakfast relative to C1/0.7, but does not remove it: each candidate
still has 140/140 downward correction intervals from minute 1440 to 1860.
The net pre-breakfast correction is −1.897, −1.694, −1.555 and −1.428 U
in table order. The first positive correction after breakfast is 39, 42,
57 and 51 minutes later, versus 60, 57, 60 and 66 minutes in C1/0.7.
These are commanded action timings, not insulin-on-board or causal proof
that the earlier correction caused later high glucose.

The assessment records per-cell scored-day commanded basal and bolus,
modeled delivered insulin, correction U, threshold crossing counts and
limit events. For B, candidate modeled delivery is 33.862, 34.546,
35.343 and 36.030 U in table order, versus basal-bolus 30.420, 30.420,
32.868 and 32.868 U. B has zero scored-day commanded bolus because
announcements are omitted. Across all 32 feedback cases there are zero
final-rate clamps, upward-slew limits and anti-windup freezes; each method
has 40 held-observation base fallbacks in the four D sensor masks. The
absence of activated limits here is not native evidence about their
behavior under activation.

## Prespecified decision

The [declared development screen](c1-feedback-diagnostic.md#one-factor-follow-up-declared-before-new-native-work)
requires a positive B 70–180 difference in **every** cell, no B increase
below 70, below 54 or above 250, no A 70–180 decrease or below-70/below-54
increase in **any** cell, and all 48 attempts complete and verify. It
**fails twice**: adult#001/102 B lacks positive in-range benefit, and the
same profile/seed A loses in-range exposure. No other prespecified gate
fails. The lower target improves the B comparison against the earlier
target-160 attempt in all four known cells, but that descriptive difference
cannot override the fixed gate or create an untouched evaluation.

The second cumulative setting attempt per feedback method is spent. This
result remains a negative development screen for the current feedback
family and settings budget. The next C1 work should reassess the method and
strong-comparator eligibility before a newly declared experiment, rather
than search for a third target or gain on these same known cells. Cambridge
transfer, an eligible published comparator and an exact new-scenario freeze
remain open. No controller superiority or treatment benefit follows.
The subsequent [C1/1.0 review](c1-method-comparator-review.md) compares
both feedback rounds and records the method/comparator decision.
