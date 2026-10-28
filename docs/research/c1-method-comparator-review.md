# C1/1.0 — Feedback method and comparator review

**OT-019 decision review, 26 September 2026.** This review uses the two
already inspected, synthetic [target-160](c1-feedback-development.md) and
[target-140](c1-target-alignment-results.md) feedback rounds. It selects no
new gains, opens no new native or held-out case, and does not turn an
engineering ablation into a published comparator. [Decision 0036](../decisions/0036-c1-feedback-family-retirement.md)
records the resulting method choice.

## Reconstructible cross-round audit

Run the [simulator-free review](../../experiments/c1/feedback_family_review.py)
from the repository root:

```sh
uv run --locked python -m experiments.c1.feedback_family_review \
  --first-study results/c1-feedback-0a6b0e6 \
  --second-study results/c1-target-f43bb85 \
  --second-assessment results/c1-target-assessment-f43bb85.json \
  --output results/c1-feedback-family-review-f2e9588.json
```

The review was run from clean commit
`f2e9588b6456d1aa6814e22473ede4adf34ed760` and produced local
SHA-256 `270b018bf3bfe8d74f05764eb45150537df00239899016f7ee661dd18af939ee`.
A second fresh process produced byte-identical JSON. The ignored local
artifact is indexed in the [C1 evidence index](../../experiments/c1/evidence-index.json),
but is not an external backup. The reader replays and checks all **96/96**
native case bundles across the two rounds before comparing the eight A/B
cells. It confirms that the only planned feedback setting change is target
160 to 140 mg/dL, all **16** paired basal-bolus initial points, traces and
native diagnostics are byte-identical, the controller/M1 adapter source
hashes match, and the pinned native simglucose fingerprint matches. Each
round used a different clean revision because the study runner changed;
this audit makes that boundary explicit.

The two cells that still fail are from the same virtual profile and seed:

| adult#001 / seed 102 | Target 160 | Target 140 | Fixed gate |
| --- | ---: | ---: | --- |
| B: candidate − basal-bolus 70–180 | −7.292 pp | **−0.833 pp** | Must be positive |
| B: in-range intervals lost above 180 | 35/480 | **4/480** | Diagnostic, not a substitute gate |
| A: candidate − basal-bolus 70–180 | −4.167 pp | **−2.292 pp** | Must not decrease |
| A: in-range intervals lost above 180 | 20/480 | **11/480** | Diagnostic, not a substitute gate |
| Pre-breakfast commanded correction | −2.135 U | −1.694 U | Diagnostic |
| First positive B correction after breakfast | 57 min | 42 min | Diagnostic |

All 140 scored pre-breakfast B actions are downward corrections at both
targets. There are no low-side in-range losses in either failing cell;
their remaining losses cross the high boundary. The other B cells move
from +9.375 to +12.708, −0.625 to +2.292, and −3.750 to +3.750 pp as the
target changes; the fixed B gate still requires **all four** cells to
benefit. A adult#001/102 remains negative. A lower target therefore
improves this matched synthetic comparison but does not rescue the
prespecified advancement screen. The one-factor change isolates the total
simulated effect of that target change under these conditions; aligned
action timing alone cannot attribute later glucose differences to a
particular pre-breakfast command or prove a biological mechanism.

## Method decision

Retire the current **two-sided PI-plus-rise feedback family as the lead**
for this missing-announcement claim. Keep its C1/0.6 kernel, C1/0.7 and
C1/0.9 runs, and the zero-rise ablation as historical development evidence
and software examples. This is a method-selection decision, not a claim
that every possible gain or predictive controller would fail. Both declared
setting attempts per feedback method are spent. A third search on these
known cells would require a newly justified method and budget and could
not turn the same cells into untouched evaluation evidence.

No replacement original controller is selected in this review. The
pre-breakfast negative correction and persistent high-side losses motivate
assessing an **insulin-action-aware, causal disturbance response** as one
possible new family. It would need an explicitly sourced insulin-action
model, observable own-delivery history, initialized state, stale-CGM
fallback, command limits and a declared experiment before implementation
or scoring. It is a hypothesis to assess, not an implemented or validated
controller. Selecting it now from these two failed trajectories would be
premature.

## Published-comparator feasibility

The [C1 protocol](c1-controller-protocol.md#reference-and-candidate-assessment)
requires a source-traced, equivalently informed strong feedback reference
before a superiority test. We checked the following primary materials on
26 September 2026. A paper's clinical outcome cannot be inserted as a
numerical comparator into a different simulator.

| Source | What is available | C1 fit and unresolved work | Decision now |
| --- | --- | --- | --- |
| [Pinsker et al., 2016](https://pubmed.ncbi.nlm.nih.gov/27289127/) | Randomized personalized MPC/PID crossover with an unannounced lunch and 70–180 outcome | Relevant task design; no verified executable implementation, full parameter set or C1 input/action mapping here | Scientific benchmark, not an executable C1 reference |
| [OpenAPS `oref0` source](https://github.com/openaps/oref0) and [reference design](https://openaps.org/reference-design/) | Public MIT-licensed reference implementation; documented CGM, pump-history, IOB, carbohydrate and profile inputs and temporary-basal decisions | Pin exact revision, feature variant and transitive licenses; verify released-only CGM and own insulin history, announced-only carbohydrates, profile configuration, temporal cadence and temporary-basal-to-native-action fidelity | **First source-feasibility candidate**, not yet qualified |
| [G2P2C source](https://github.com/RL4H/G2P2C) and [published article](https://www.utupub.fi/server/api/core/bitstreams/9a4f6dc1-b4ef-40e8-8776-ad0cc2a08ea6/content) | Published, MIT-licensed reinforcement-learning code using a modified simglucose-based environment without meal announcements | Training data, checkpoint identity, environment changes, population overlap, compute and adaptation to unchanged M1 need audit; no ready matched frozen policy has been verified here | Secondary feasibility candidate, not yet qualified |
| LT1 native `MPC_Hovorka2004`, traced to [Hovorka et al.](https://pubmed.ncbi.nlm.nih.gov/15382830/) | Already pinned and runnable on the separate Cambridge track | Different engine, observation/action semantics, one parameterization and known numerical sensitivity; cannot stand in for an M1 comparator | Retain as Cambridge reference only |
| M1 native PID and the C1 zero-rise scaffold | Locally executable | The [C1/0.5 audit](c1-method-revision.md#why-the-current-pid-is-not-the-strong-comparator) finds PID clamp/anti-windup and outcome reversals; zero-rise is an ablation of the same family | Historical anchors, not strong published comparators |

For `oref0`, feasibility means a **source-pinned, non-clinical adapter
preflight**, not running 16 known cells immediately. It must demonstrate:

1. Exact source commit, license and dependency inventory, selected
   `oref0`/`oref1` feature variant (including unannounced-meal and
   microbolus options), upstream reference examples and output parity
   before any OpenT1D-specific changes. A [published oref0/oref1 simulation](https://pmc.ncbi.nlm.nih.gov/articles/PMC9739839/)
   used the newer feature set; it does not validate a different variant.
2. A mapping for each required input to C1's released CGM, own past doses,
   announced meals or frozen profile; no true meal, latent model state or
   future values. If the algorithm needs a forbidden input, it is ineligible
   for that comparison.
3. A declared clock and temporary-basal representation preserving action
   meaning on M1's three-minute U/min route, plus bounded stale-sensor,
   reset and failure behavior. An adaptation that substantially changes the
   algorithm needs a separate method label and cannot inherit the published
   result.
4. A reproducible matched development budget, complete failure accounting
   and simulator-free command reconstruction. Only after those pass may a
   new comparative plan and an untouched evaluation freeze be declared.

Thus **no M1 strong published comparator is qualified today**. The first
implementation package should test `oref0` source and contract feasibility;
if it cannot preserve the information and action contract, record that
negative result and consider G2P2C or another fully sourced reference.
Cambridge transfer and final two-family C1 evaluation remain separate.
