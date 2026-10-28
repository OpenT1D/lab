# M3-COMPARISON/1 — Frozen candidates on one synthetic CGM task

**Status:** Frozen for bounded internal synthetic verification, 2 October 2026.
No assessment has been executed under this protocol. This is the separate OT-030 analysis
contract under decision 0055; the historical M3 researcher protocol remains
unchanged.

## Question, scope and inherited boundaries

How do at least two frozen local predictors and persistence compare on the
same planned synthetic people and causal forecast origins, while preserving
coverage, failures and losses from requiring common support?

This route accepts synthetic inputs only. Each predictor retains the
`opent1d.m3.forecaster/1` contract: six exact five-minute CGM measurements at
−25, −20, −15, −10, −5 and 0 minutes, already available at the origin, predict
a measured target exactly 30 minutes later in mg/dL. Inherit the existing
60-minute evaluation warm-up, clock-segment and measurement-status rules,
no interpolation or imputation, finite prediction requirement and unchanged
persistence. Negative finite predictions remain recorded without clipping.

The coordinator performs no fitting, calibration, tuning or automatic
winner selection. Candidate source/settings selection occurs on development
material; the declaration records that provenance as an attestation.
Synthetic generation, prior inspection and repeat runs remain known material.
This comparison establishes no human prediction or treatment claim.

## Configuration and freeze

The input schema is `opent1d.m3.comparison/1`. The configuration has exactly
these fields:

| Field | Required content |
| --- | --- |
| `schema` / `kind` | `opent1d.m3.comparison/1` and `synthetic` |
| `source` | Existing `id`, `reference` and `format: normalized-cgm/1` metadata |
| `prior_access` | Existing `reviewed: true`, `status: present` and nonempty disclosure `reference` |
| `people` | One nonempty ordered list of existing M3 researcher person descriptors: unique `id`, absolute input `file` and exact `sha256`, half-open `bounds_us`, and complete sorted unique `origins_us` |
| `candidates` | At least two ordered objects, each containing exactly `id` and absolute `declaration` file path |
| `timeout_seconds` | One finite positive per-person worker budget, applied equally to all candidates |

Candidate IDs obey the existing M3 ID syntax, are unique, reserve
`persistence` for the shared reference and match their predictor declarations. The candidate list fixes execution and contrast
orientation order. A shared source with different frozen settings is
permitted; identity declarations do not establish independent ancestry.
Do not shorten the registered origin schedule or remove a failed candidate.

Before the first observation read, load and validate every candidate's
declaration, source and settings with the existing intake. Retain their
exact bytes and hashes in parent-owned `frozen/<id>/` directories. Save an
effective declaration that points to these source/settings snapshots; only
those file paths may differ from the requested declaration. Each generated
child configuration retains the same source, prior-access disclosure,
people, bounds, input hashes and registered origins as the parent.

Persist `plan.json` before invoking any child study. It contains exactly
`schema`, `config`, `config_sha256`, `candidates` and `provenance`.
The config hash uses existing canonical M3 JSON encoding. Each candidate
plan entry contains its parsed requested `declaration`, the exact requested
`declaration_sha256`, and the path-rewritten `effective_declaration`.
Snapshot source/settings hashes must equal both declarations. Provenance
binds the new comparison Python source inventory and this protocol, root
lock and unchanged child source/lock/protocol inventory, Git revision and
dirty flag, Python and platform. Guides and later evidence prose are not
numerical source inventory.

The coordinator does not read original observation contents itself before
or during candidate metadata freeze. Unchanged child execution reads and
snapshots each person's original inputs after the parent plan is persisted.
Every child's input identity is checked against the same frozen parent
descriptor; missing or changed bytes remain retained input failures.
Parent reconstruction consumes child snapshots and never opens the original
input or predictor locations.

## Execution, interruptions and archive ownership

Execute candidates sequentially in the frozen order, using unchanged M3
single-candidate execution and its declared per-person worker budget.
A regular worker failure or deadline does not remove the candidate or stop
other candidates. All original per-candidate reports retain their own
planned denominators and primary eligibility.

A coordinator interruption stops subsequent candidates. Preserve already
saved child artifacts and represent every later candidate and all of its
people/origins as not attempted, even when no child archive exists.
Distinguish a global interrupt from a worker deadline: the latter remains
local to that attempt. Delegate active worker cleanup to the unchanged
supervisor; do not claim broader descendant guarantees than it verifies.

Parent execution states are `started`, `finished`, `failed`,
`interrupted` and `not_attempted`. A candidate's `finished` state means a
child archive was produced and verified; it does not mean every worker or
every scientific eligibility gate passed. Persist candidate states and
error types outside child directories. A started, unfinished attempt cannot
be promoted to a finished candidate. Unavailable child artifacts remain
visible; inconsistent artifacts that exist fail reconstruction rather than
being treated as absent successful work.

Use fresh output directories and refuse overwrite. Parent plan, states,
frozen sources, generated configs, manifest and report files stay outside
`children/<id>/`. Child archives retain their strict inventories. Validate
each present child with its unchanged reconstruction reader before consuming
its predictions. The parent inventory binds retained child bytes as well
as parent administrative inputs. Preserve exact failed trace prefixes;
unattempted origins do not disappear from any denominator.

## Common support and eligibility

The initial primary support is the **all-candidate intersection**, including
every candidate in the frozen roster and shared persistence. Pairwise-support
analyses are deferred. Original single-candidate comparisons remain available
with their own denominators; differing subsets cannot establish a ranking.

For each planned person, align rows by exact registered origin. At every
overlapping row, host features, exclusion reason, target status/value/bound
and persistence must agree across candidates. Only candidate predictions
may differ. Different source/input hashes, people, bounds, origin schedules,
host histories, targets or persistence are rejected.

Under the unchanged callback, every valid history requires a finite output
or the worker fails. There is no successful per-origin abstention. Completed
candidates on identical inputs therefore have identical score availability.
Unequal coverage legitimately comes from failed, interrupted or not-attempted
workers; manufactured successful omissions or differing host availability
are invalid.

A shared scored origin has valid host features, a measured target and
retained finite predictions for all frozen candidates plus persistence.
Valid failure prefixes may be intersected for diagnostics, but a person
contributes to the primary comparison only when:

- Every frozen candidate's worker for that person completed.
- At least 288 origins are jointly scored.
- The last shared scored origin minus the first is at least 1,440 minutes.

Both coverage floors are required on common support itself, not on each
candidate's original subset. Origin span is not summed observation time.
A person with a long failed prefix remains excluded. A missing later
candidate is not dropped to create a contributing cohort.

Retain every candidate/person/planned origin count, candidate execution
status and original scored count, common scored origins and span, losses
from common support, primary eligibility and every exclusion reason.
Any planned noncontributor makes the cohort incomplete. Empty support or
zero contributing people yields null aggregate metrics and explicit reasons.

## Fixed metrics and uncertainty

For each contributing person, calculate MAE, RMSE and bias for every
candidate and persistence on exactly the common origins. The primary
contrasts are every candidate minus persistence, followed by every distinct
candidate pair oriented by the frozen candidate order. A person's contrast
is the mean of origin-level absolute-error differences, left minus right.
Negative values describe lower error for the left method on that support.

Average person-level errors and contrasts equally, using the inherited
overflow/subnormal-safe mean and scaled RMSE arithmetic. Do not pool
timestamps or weight a person by their number of origins. Diagnostic
prefix summaries cannot enter these aggregates.

For each contrast, resample whole contributing people with replacement:
2,000 draws, seed 301, sorted participant-ID order, and the 50th and
1,950th one-based empirical order statistics without interpolation.
Fewer than two contributing people leaves the interval null. These are
descriptive intervals, not simultaneous superiority tests or clinical
accuracy criteria. No threshold, automatic ranking or winner is defined.

The report schema is `opent1d.m3.comparison/1`; its top-level fields are
`schema`, `kind`, `provenance`, `candidate_order`, `candidates`,
`common`, `human_evaluation` and `reconstruction_scope`.
Each `candidates` entry retains its coordinator state/error and unchanged
single-candidate report, or a missing-archive reason and full not-attempted
person/origin accounting. The `common` section records `support`,
`planned_people`, `contributing_people`, `complete_cohort`,
`people`, `equal_person_metrics`, `contrasts` and `null_reason`.
Per-person common records expose statuses, original/common scored counts,
planned count, origin list/span, losses, eligibility, reasons and diagnostic
error summaries. Each contrast exposes `left`, `right`,
`person_differences`, `mean_person_mae_difference` and
`participant_bootstrap_95`. Zero contributors use null numeric aggregates,
not zero error. JSON and readable Markdown carry the same assessment.

## Reconstruction and verification

Reconstruction verifies frozen requested/effective declarations, generated
child configs, full roster/order/budget, parent inventory/provenance and
every present child's original source-bound reader. Then it checks shared
host identities, complete/partial statuses, common eligibility and all
derived arithmetic before rebuilding reports in a fresh directory.

It uses the standard library, saved child observations/traces and frozen
metadata; it neither imports candidates, refits models nor reads original
input files. Arbitrary candidate outputs remain execution evidence:
reconstruction checks their analysis, not an independent reproduction of
the supplied algorithm. Hashes establish saved consistency, not signatures.

Acceptance must demonstrate two existing predictor structures and exact
fresh-process repeats; independent hand calculations for signs and equal
person weighting; 288-window and 24-hour boundary conjunction; one-person
null uncertainty; long failed-prefix exclusion; empty and incomplete
common cohorts; frozen candidate retention; identity/semantic mismatch
rejection; and byte-identical report reconstruction after original source
inputs/predictors are unavailable. Repository checks verify software only.
Independent usability and M2/P1/M3–M5 external evidence gates remain open.
