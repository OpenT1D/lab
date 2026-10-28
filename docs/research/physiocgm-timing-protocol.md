# M3-PHYSIOCGM-TIMING/0.1 — Timing sensitivity of CGM forecasts

Accepted for synthetic software implementation, 20 September 2026, under
[Decision 0015](../decisions/0015-physiocgm-timing-followup.md).
The implementation is an isolated matching component and a bounded demonstration
using invented observations and a hand-defined model. Human preparation and
execution remain separate steps. This protocol does not replace
[M3-PHYSIOCGM-EXTERNAL/0.1](physiocgm-external-freeze-protocol.md) or change any
historical result.

## Question and evidence boundary

The question is whether the comparison between the unchanged Ridge predictor
and persistence is sensitive to allowing small timestamp differences around
the required CGM observations. Earlier inspection of the study motivated this
question. It is therefore a post hoc follow-up on known material, not an
untouched external test or a prespecified confirmation of model performance.

Keep the earlier exact-time comparison and its artifacts. The new route varies
only timestamp matching; it does not train, recalibrate, personalize or clip the
predictor. It adds no physiological model or controller. Increased scoring
coverage alone does not show better forecasts, and forecasts under recorded
treatment cannot establish what another controller would have caused.

Use schema `opent1d.physiocgm.timing/1`, protocol
`M3-PHYSIOCGM-TIMING/0.1` and metric `physiocgm-timing-forecast/1`.
No arbitrary tolerance setting is exposed. The three fixed variants are:

| Radius | Role | Required interpretation |
| --- | --- | --- |
| 0 seconds | Exact reference | Reproduce the original exact-time rule and arithmetic. |
| 1 second | Main follow-up | Compare the same frozen predictors with this fixed allowance. |
| 5 seconds | Sensitivity analysis | Describe dependence on a wider allowance; do not select a preferred result after scoring. |

All variants use the same planned people, registered origins, half-open
observation intervals, units, clock segments and model. Keep every registered
origin in the denominator. Coverage is a fraction of those origins, not a
fraction of elapsed time or all possible five-minute positions.

## Matching contract

Preserve integer microsecond timestamps and original observation lineage. Do
not round times, interpolate values, make a regular replacement grid or fill
missing observations. Retain the earlier naive-local-clock convention and
the declared measurement-time-as-availability assumption for the intended
human follow-up. They do not establish the sensor's real online delivery time
or resolve daylight-saving changes.

At a registered origin `t`, retain the 60-minute warm-up and six ordered nominal
feature times: `t−25`, `t−20`, `t−15`, `t−10`, `t−5` and `t` minutes. The current
observation at `t` must remain exact; neither the origin nor persistence moves.
Every nominal historical time must lie within the declared interval.

For each of the five earlier feature times:

1. Search registered timestamps inside the declared interval and no later than
   `t`. Select the closest timestamp by absolute distance, before considering
   its status, value, availability or segment.
2. Require that distance to be within the variant's radius. Reject equally
   close timestamps; do not choose one using its glucose or usability.
3. Require a measured, unambiguous value, availability by `t`, and the origin's
   clock segment. An unusable nearest record remains unusable; do not substitute
   a farther usable record.

The six selected records must be distinct and strictly time-ordered. Exact
records take precedence because their distance is zero; an exact invalid or
censored record cannot be replaced by a nearby measured record. Eligibility
uses only observations available by the origin. The original six nominal
feature positions remain the model's inputs; no time-offset feature is added.
Consequently, tolerant matching makes an explicit approximation to the frozen
model's original five-minute feature convention.

Decide and retain the forecast before the future target is considered. For
scoring, first require the nominal target `t+30` minutes to lie inside the
declared interval. Find the nearest registered timestamp inside that interval
with the same distance/radius/tie rule, and then check its status and clock
segment. Do not search another segment for a more convenient target. A missing,
censored, invalid or ambiguous target excludes its point score, not an
otherwise eligible prediction. No target-availability-by-origin requirement
applies: the target is a later observation used for retrospective assessment.

Retain the selected timestamp, signed offset and reason for each selection or
exclusion in synthetic artifacts and, in a later authorized human route,
private artifacts. Describe target offsets because a nearby target changes the
observed horizon slightly; it is not an exactly 30-minute measurement.

## Comparisons and participant accounting

For each variant, compare Ridge and persistence only on their jointly scored
origins. The model and scaler bytes must remain unchanged in the intended
human follow-up. The synthetic demonstration uses a clearly identified
hand-defined model solely to check arithmetic and reconstruction; its
coefficients are not a trained human predictor.

The following invariants must hold:

- Predicted-origin sets are nested: 0 seconds is contained in 1 second, which
  is contained in 5 seconds. The jointly scored sets obey the same nesting.
- On a shared predicted origin, narrower and wider variants retain the same
  selected history and forecasts. On a shared scored origin, the selected
  target and errors also remain identical. Expanding the radius does not
  change the nearest candidate or resolve a tie.
- The zero-second variant reproduces the original exact-time eligibility,
  target status and numerical outputs. A difference is a verification failure,
  not a new scientific result.

Report each full variant separately. A person contributes to a full-variant
aggregate only after completed execution with at least 288 jointly scored
origins spanning at least 24 hours. Keep the complete planned roster and every
failure or noncontributor visible. Any noncontributing planned person makes
that variant's cohort incomplete. These are coverage floors, not a power
calculation or an accuracy standard.

The primary outcome is the equal-person mean of paired MAE differences,
Ridge minus persistence; negative values favor Ridge. Retain equal-person
MAE, RMSE and bias, coverage and exclusion counts. For full variants, use the
existing descriptive whole-person bootstrap: 2,000 draws, seed 301, and the
50th and 1,950th one-based order statistics. Fewer than two contributing
people leaves the interval undefined. Repeated timestamps are not independent
people, and the interval does not remove this follow-up's post hoc status.

Also describe newly scored origins separately: the 1-second scored set minus
the 0-second set, the 5-second set minus the 0-second set, and the 5-second set
minus the 1-second set. These overlapping descriptions must not be summed.
A person enters
an added-subset description with at least one paired score in that subset;
report how many people and origins contribute and their equal-person paired
MAE difference. Do not import the full-variant coverage floor into this
description, insert zero errors for absent people or bootstrap these subsets.
The subsets expose differences in the added material; they do not establish
an accuracy improvement caused by admitting more observations.

## Run the synthetic demonstration

From the repository root, use a fresh output directory:

```sh
uv run --locked python -m experiments.m3.physiocgm_timing demo --output /tmp/timing-demo
uv run --locked python -m experiments.m3.physiocgm_timing verify --study /tmp/timing-demo
```

The demonstration generates its invented inputs internally and uses the fixed
hand-defined model. It accepts no observation-input or human-model argument.
It retains synthetic matching, forecast and summary artifacts for all three
variants; verification reconstructs them and checks the exact reference and
nested comparisons. Use this as a software example, not as a human result.

If execution fails or is interrupted, retain the written trace prefixes,
failure status and artifact inventory in that attempt's directory. Use a new
directory for another attempt. The current `verify` command accepts only a
completed demonstration; it does not reconstruct a failed campaign or present
its partial work as a complete comparison.

Synthetic checks should cover exact equivalence, signed jitter, inclusive
radius boundaries, ties, interval edges, late availability, unusable nearest
records, clock segments, ordered distinct history, target-independent
forecasts, nested subsets and altered-artifact rejection. Passing those
checks demonstrates the matching and reporting mechanics only.

## Separate human-use step

The current demonstration does not implement a new human authorization request,
source-bound preparation, read ledger or supervised human execution route.
Before any human follow-up, prepare and review those boundaries separately:

- Bind the retained normalized observations, unchanged donor model, original
  people/origins/intervals and this exact implementation in a new private plan.
  Disclose earlier inspection and retain the limited donor provenance scope.
- Bind the saved exact-time results and require zero-second reconciliation
  before interpreting the tolerant variants. Do not overwrite the original
  evaluation or silently widen its matching policy.
- Record authorization covering the concrete reads, predictions, scoring and
  private reconstruction; create durable receipts before protected reads and
  retain failed attempts and the complete roster.
- Keep health observations, individual derived outputs, model parameters and
  private source identities outside Git and public services. This protocol
  authorizes no download, transfer or publication of those artifacts.

No actual human observations are needed to complete this synthetic technical
step. Human source reconciliation and an executable protected workflow remain
open; changes to the scientific rules require another explicit version with
the known evaluation material disclosed.
