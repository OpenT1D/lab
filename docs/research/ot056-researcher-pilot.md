# OT-056 comparative researcher pilot

**Status, 18 October 2026:** internal technical acceptance is complete within
the synthetic OT-053 boundary. Controlled OT-054/055 CLI/GUI handoffs are adopted;
both same-estimator notebooks and the 22-case native chain pass, including
retained failures and reconstruction without the original output directory.
The final locked check passes **1,390 tests with 13 existing skips** and the
strict documentation build. No researcher, independent reviewer or licensed
comparator access is confirmed. The human pilot, product decision and full
OT-056 goal remain open.
The [original OT-056 acceptance plan](roadmap-history-2026-10-28.md#planned-mixed-meal-analysis-tasks) records this pilot's proposed criteria.
The earlier [GUI exercise](../gui-researcher-exercise.md) has a different task
and cannot supply observations for this pilot.

The subsequent [OT-057 interface follow-up](ot057-uiux-verification.md) was
integrated into main on 19 October, with remote identity verified on 22 October.
Its internal macOS retests and 1,393-test repository check extend the software
evidence; they supply no human pilot observations and do not close this goal.
The 1,390-test result above remains the historical OT-056 acceptance result.

## Scope in the current laboratory plan

**Clarification, 29 October 2026.** This remains a proposed comparative study.
Its 30% time-reduction target, five-pair rules and matching evaluator are
retained for that study; no measured productivity advantage is claimed. The
[current delivery plan](../../ROADMAP.md#common-laboratory-delivery-plan) and
[product requirements](../product-laboratory.md#product-value-measurement)
assess useful laboratory contributions through correctness, usability,
interoperability and maintainability. The pilot's comparative progression rules
are not general delivery thresholds for those integrations.

Before conducting an amended pilot, declare its protocol and evaluator revision,
justify the task-specific criteria and preserve the original analysis. Do not
change thresholds after seeing observations or relabel an old result under new
criteria. The dated pilot proposal and technical evidence below remain intact.

## Technical completion and human acceptance

The maintainer requested technical completion first, with the human pilot kept
separately open. Technical acceptance now covers controlled OT-054/055
execution commits, runnable synthetic case packages, independent numerical
answers, both same-estimator notebooks, full import-to-task-report execution,
retained failures, reconstruction and relocation verification.
Independent sessions, comparator-expert qualification, licensed vendor-tool
exports and the product continuation decision remain separate external evidence.
The technical open-estimator comparison does not establish AOMM/SAAM II parity
or superiority.

The controlled OT-053 dossier `cd10cb0` and handoff `4f38f01` are now adopted.
All fifteen dossier-file hashes were checked against the original source commit
before use. [Decision 0067](../decisions/0067-mmtt-feasibility-boundary.md)
permits only invented fixed-kinetic preparation: whole-body total endogenous
secretion including basal in pmol over observed 0–120 minutes, follow-up minus
baseline, equilibrium initialization and no automatic weight/BSA/glucose
normalization. Negative estimates remain visible. Human kinetics and empirical
uncertainty are not established.

The shared importer through `f17172c` and schedule preparation through
`342ea0a` were adopted from their controlled commits, excluding the duplicate
planning patch and duplicate importer copies. Local cherry-picks preserve
original commit references. The input-only preflight below remains useful
separately from the completed task-execution chain.

The technical input preflight is executable:

```sh
uv run --locked python -m experiments.ot056_pilot preflight \
  --output results/ot056-new-preflight
uv run --locked python -m experiments.ot056_pilot verify-preflight \
  --archive results/ot056-new-preflight
```

Choose a fresh directory. It creates six structurally matched task/case
packages, each with five invented participants, two visits and 60 rows, plus
three explicit bad-unit/missing-endpoint/duplicate-time controls. Shared import
preserves all nine outcomes; the six valid packages also produce development-only
imports and actual frozen schedule-selection receipts. Case reconstruction uses
the trusted generator and shared readers; corrected archive checksums alone
cannot legitimize altered coverage or human findings. Relocated verification
checks that development inputs are exactly projected from their original case.
Human difficulty equivalence is not assessed.

The main A/B/C packages now combine the controlled OT-054 increase and
assumption-dependent trajectories with the OT-055 sharp-peak, low-signal and
censored controls. Their extra minute-15 observations are invented on the
declared piecewise-linear control path; no missing human measurement is filled.
Each scale must produce one consistent, one assumption-dependent and three
insufficiently determined Task 1 conclusions under the frozen engineering
settings. The real estimator checks these answers. Glucose stimulus differences
remain visible as context. These synthetic software fixtures do not establish
human task-difficulty equivalence or empirical held-out performance.
The case receipt also fixes the expected model interpretations after each
reduction: the evaluation control is assumption-dependent with five times,
unresolved with four and consistent with three. A cleaner-looking reduced
conclusion is not itself evidence of better inference. These expectations are
checked against isolated shared-core calls and reproduced by the native Task 2
chain, including all required failures and planned denominators.

OT-055's independently derived vectors in `5ff2206` were then adopted after
checking all eleven recorded source hashes. The reference-input conversion
commands produce actual shared-schema inputs and source-bound expected
answers without invoking an inverse estimator:

```sh
uv run --locked python -S -m experiments.ot056_pilot references \
  --output results/ot056-new-references
uv run --locked python -S -m experiments.ot056_pilot verify-references \
  --archive results/ot056-new-references
```

The four manufactured reference profiles include constant, low, rising and
falling concentrations. Two declared visit pairs have nonzero analytically
known changes; the other two repeat the same manufactured curve across visits.
The falling profile retains its negative terminal-rate control. These are
software references, not clinical sampling-equivalence or biological truth.
Expected answers are regenerated from the controlled vector source; resealing
changed answers does not make them authoritative.

The OT-055 backend `328a363`, GUI `8bfbbb3`, library correction `55c5519` and
final handoff `8744391` are adopted. All 55 final source identities were checked
against the origin commit and this checkout. Its 42 backend tests pass here,
including actual common-entry/catalogue execution and interruption. Decision
[0069](../decisions/0069-mmtt-sampling-reuse.md) adds required-time admission to
the shared settings and evaluator; the estimator, kinetics and error procedure
remain the same. Original OT-054 source hashes describe the earlier checkpoint;
the two admission files now follow the controlled OT-055 extension.
No human observation file is populated by these commands.

### Combined native rehearsal

```sh
uv run --locked python -S -m experiments.ot056_pilot rehearse \
  --output results/ot056-new-two-task
uv run --locked python -S -m experiments.ot056_pilot verify \
  --archive results/ot056-new-two-task --output results/ot056-new-two-task-check
```

The complete native rehearsal contains eleven Task 1 and eleven Task 2 cases.
Task 2 adds the matched A/B/C packages, invalid units, missing endpoints and
duplicate times, four analytical profiles at every schedule, a controlled
direction reversal, two omitted-value traps and a missing interior measurement.
It checks all planned people, visits, variants and paired perturbation counts.
Independent analytical totals and paired changes use the declared `1e-7` pmol
software tolerance; C-peptide AUC and negative-rate acceptance remain separate.

The fixed [Task 2 notebook](../../experiments/ot056_pilot/same-estimator-sampling.ipynb)
freezes the identical development evidence, raw inputs and settings. Shared raw
projection precedes every independent native plan and direct `evaluate` call.
Both routes retain identical child reports, attempts and plan bytes, and
identical comparison Markdown. For comparison JSON, only the CLI's top-level
native process journal is excluded: the notebook does not fabricate a native
process journal. Every scientific field and nested result must match exactly.
The full original CLI report and journal remain archived and reconstruct exactly.

Invalid and extreme minute-15 evaluation cells cannot change any reduced
report or attempt. The invalid full reference remains unavailable, never zero.
A missing minute-90 measurement blocks the affected full/five-time visit before
estimation or perturbation; the other visit stays visible, and four/three-time
analyses retain their known result. Development-only selection evidence remains
untouched in these traps. Duplicate times retain all planned unattempted work.

The combined verification test removes the original output directory before
reconstruction, repeats both native tasks in fresh processes, and refuses
resealed canonical-input, coverage and invented-human/product claims. It never
executes archived Python or notebooks. Both completed GUI handoffs are adopted;
the final locked repository check, including the Task 2 library correction,
passes. Human qualification and comparative sessions remain open.

### Controlled Task 1 execution

OT-054 core `23e1bc1` and handoff `a8a85fe` are adopted after checking all
fourteen implementation hashes and the protocol hash against the source commit.
The complete bounded Task 1 GUI is now adopted through controlled final record
`099f01a`, including implementation `accb434` and navigation fixes `3e13a73`.
At adoption, all 32 GUI and 14 core source hashes matched the handoff; seven adopted
GUI/HTTP/frontend tests pass in this integration checkout. Its producer's
[verification record](ot054-verification.md) separately records the actual
four-case browser exercise. Independent human usability remains open.
The fixed repository
[notebook](../../experiments/ot056_pilot/same-estimator.ipynb) freezes the same
source bytes and settings and calls the shared `evaluate` / `report_from_attempts`
calculation directly. It does not call the CLI or implement another estimator.
An experienced human analyst has not yet qualified it for timed sessions.

```sh
uv run --locked python -m experiments.ot056_pilot rehearse-task1 \
  --output results/ot056-new-task1
uv run --locked python -m experiments.ot056_pilot verify-task1 \
  --archive results/ot056-new-task1 --output results/ot056-new-task1-check
```

This actual CLI/notebook rehearsal covers eleven named cases: the three Task 1
variants, three input-fault controls, the four controlled upstream interpretation
examples, and the four-person analytical reference bundle. The compared input
snapshots and frozen plan bytes must match. Reports, Markdown and every saved
attempt match byte for byte. The complete roster remains visible for censored,
duplicate and missing-endpoint failures; unknown units are refused by both routes.
Correct insufficient or assumption-dependent conclusions remain correct outcomes.

The reference bundle checks known whole-body totals, follow-up-minus-baseline
changes, separate C-peptide AUC and the unclipped negative terminal-rate result
within explicit software tolerances. Its declared small error SD is an
engineering control, not assay precision. Native reconstruction and verification
after relocating the archive and removing its original output directory pass.
Changing a named case's input snapshot, a controlled example's canonical input
or a comparison's coverage count is refused even after resealing. Verification
regenerates the named controls and derives counts from trusted reconstruction.
Four full-chain tests cover these properties.

The [machine-readable verification record](../../experiments/ot056_pilot/verification.json)
binds final integrated code `1e2b9ab`, controlled source receipts, the retained
22-case archive and actual check-log hashes. The final locked check passes
**1,390 tests with 13 existing skips**, followed by the strict documentation
build. The separate empirical and human/product gates remain open. The record
sets `technical_complete: true` and `full_goal_complete: false`.

The source-model numerical check was independently repeated here using the
existing locked BC-003 runtime:

```sh
uv sync --locked --project experiments/m4/beta_cell/runtime
experiments/m4/beta_cell/runtime/.venv/bin/python \
  -m unittest experiments.observation_analysis.test_numerical -v
```

It passes against the separate analytical and ODE forward paths, reproducing the
declared refinement behavior and retained coarse-grid boundary failure. This is
software agreement under synthetic assumptions. It supplies no human validity,
usability, vendor-tool qualification or product-value result.

## Question and evidence boundary

Can intended researchers produce correct, complete reports for both tasks with
less active time and acceptable total effort than strong existing workflows?

- Task 1: assess whether paired secretion-change conclusions remain consistent
  across frozen, defensible assumptions.
- Task 2: assess information loss after removing measured time points before
  refitting with the same method, assumptions and uncertainty procedure.

Both use estimated total endogenous insulin secretion over the same measured
0–120 minutes and its visit-2 minus visit-1 change. Freeze physical units,
normalization, initialization, basal handling and uncertainty from the accepted
OT-053/054 protocol. C-peptide AUC is a separate reference. Preserve glucose
exposure, test conditions, all attempts, failures and indeterminate conclusions.
A different glucose stimulus can change secretion without functional recovery;
neither task establishes a treatment effect. A full-curve estimate is a reference
analysis, not biological truth. Do not infer no change from nonsignificance.

Synthetic cases can assess software use and interpretation of synthetic evidence
once verified implementations exist. They cannot close empirical T1D evaluation.
Human researchers using synthetic cases still provide human usability evidence;
agents operating those cases provide technical evidence only. Six tool users
are distinct from the number of clinical observation records in an empirical study.

## Prerequisites and dependency handoff

Record an immutable commit, check record and source/rights scope for each
dependency. Read the controlled commits, reproduce relevant checks in this
worktree and adopt the existing implementations rather than writing another
estimator. Do not transfer uncommitted files from another chat. A narrow/stop
OT-053 disposition may require narrowing or stopping this pilot as well.

| Input | Required before session freeze | Current evidence |
| --- | --- | --- |
| OT-053 | Proceed/narrow/stop dossier, estimator applicability, units/conventions and strong baseline assessment | Controlled narrow dossier `cd10cb0` and handoff `4f38f01` adopted; synthetic fixed-kinetic scope only |
| OT-054 | Controlled Task 1 commit, numerical/failure/reconstruction checks and usable local route | Core `23e1bc1` / handoff `a8a85fe` and completed GUI through `099f01a` adopted; native/notebook and adopted GUI/HTTP/frontend tests verified |
| OT-055 | Controlled shared-core Task 2 commit, leakage checks, schedule comparisons and usable local route | Backend `328a363`, GUI/library correction and final handoff `8744391` adopted; all 55 current source hashes checked; full/subset CLI/notebook and GUI/report-reader regressions pass |
| Cases | Matched A/B/C packages per task, hashes, expected reports, tolerances and independent answer-key review | Six matched synthetic packages and 22 native technical cases have expected reports, tolerances and reconstruction; independent human difficulty/answer-key qualification remains open |
| Researchers | Six actual intended users across at least two teams, experience and participation records | None confirmed |
| Comparator expert | Experienced user configures and checks the actual workflow and notebook | None confirmed |
| Reviewer | Domain reviewer independent of implementation and session coaching; conflicts recorded | None confirmed |
| Rights/access | Actual data/handoff scope, comparator licenses, working exports and supported platform | Synthetic scope/source established; human data, actual comparator access/exports and pilot platform unverified |

Controlled source commits, executable commands, contracts and reader identities
are recorded above. Shared planning commits and empty pilot forms supply no
execution or human evidence. Recheck the frozen source identities before a
human session; do not replace them with an unreviewed worktree state.

No outreach, recruitment, license purchase or data-access application is
authorized by this protocol. Contact details, private observations and identities
remain outside version control. Record only non-identifying slots and local
evidence references in the packet; publication requires its own authorized scope.

## Strong comparators and fair preparation

Use three arms: `opent1d`, `current` (the researcher's actual workflow with
competent scripts) and `notebook` (a well-prepared notebook with the same open
estimator as OpenT1D). An experienced comparator user must help prepare both
alternatives. Include reasonable batch automation, diagnostics, uncertainty,
report assembly and reconstruction; comparing with avoidable manual work is
not informative. Record preparer time for every arm, including OpenT1D.

The vendor's [AOMM page](https://www.nanomath.us/aomm), checked 18 October 2026,
describes MMTT analysis, batch processing, secretion indices and precision
outputs. Its page has differing version labels; verify the installed build.
The [SAAM II page](https://www.nanomath.us/saamii) describes model construction
and estimation on Windows. These are candidate comparators, not proof of access,
export compatibility or endpoint equivalence. This pilot assumes no vendor API.

Before qualifying an actual comparator, its experienced user must demonstrate:

1. Authorized installed access on the pilot platform, exact version, license and
   permitted recording/export scope; never store license keys in the packet.
2. Import of the same source cases with actual sample times, units, censored and
   missing values and linked visits preserved, including detectable bad input.
3. A documented route to the physical 0–120-minute endpoint, frozen variants,
   uncertainty, paired change and retained failures, with required script glue.
4. Actual export and reopening of a report, including incomplete evidence;
   retain file hashes and a demonstration record. Manual exports are acceptable
   if supported; count the work. Do not infer machine-readable export support.
5. For Task 2, actual deletion before interpolation/fitting, no removed-point
   parameter leakage and the same fixed window and prespecified subsets.

If AOMM cannot express the selected estimator or variants, document the semantic
difference and use a competent applicable SAAM II/script workflow where feasible.
Do not compare similarly named responsivity indices as the primary endpoint.
A different model can be an additional workflow comparison only after the
reviewer approves endpoint comparability; the same-method notebook is still
required to distinguish workflow value from numerical-method differences.

Select the strongest applicable primary comparator **for each task before
participant sessions** using expert demonstration of correctness, achievable
workflow and preparation burden. Record the rationale, applicability and
remaining limitations. Report both comparator results; do not switch the primary
after observing favorable times. If the actual-tool arm is inaccessible, finish
the notebook preparation but keep the full comparative claim open.

## Matched cases, allocation and support

The generated allocation has six unfilled slots R01–R06, two tasks and three
tools: 36 planned task/tool attempts. All six tool permutations appear once per
task; Task 2 reverses each slot's tool order. Each tool receives each case label
twice per task. Slots are not recruited researchers. Randomly assign consenting
researchers to slots, balancing team and prior-tool experience where feasible;
record the assignment method and seed before opening any session results.
Do not change the generated schedule silently; a change requires a new protocol.

Prepare three matched case variants per task to reduce direct answer recall.
They must match participant/visit counts, sample burden, numerical difficulty,
failure/low-C-peptide content, uncertainty and expected interpretation effort.
For every case retain source bytes, synthetic/authorized-human status, hashes,
allocation, protocol, expected outputs, tolerances and provenance. Use the
controlled executable cases and software answer checks above as technical
preparation. An independent reviewer must qualify their scientific interpretation
and difficulty before the human session freeze. Technical rehearsal and expert
difficulty matching use separate nonparticipant material.

Each case must require detection and reporting of a known limitation or failed
attempt as well as a paired result. A correct indeterminate conclusion or
"no reduced schedule qualifies" can pass. All arms receive the same observation
bytes, information, scientific conventions, assumption/schedule options and
report requirements. Compatible format conversion is preparatory work and must
be timed. No arm receives hidden fitted values or removed measurements.

Provide equivalent written onboarding, practice material, documentation and
available support for each arm; record real prior experience separately.
Use neutral task prompts from the [blank forms](ot056-pilot-forms.md).
Do not coach a particular interface path. Record every substantive help request,
source and duration. Supplied documentation is permitted independent work;
moderator instructions, teammate help or interpretation advice count as assistance.
Freeze policy on AI assistance equally across arms; proposed primary sessions
exclude interactive AI help. Accessibility accommodations are supplied equally
and documented before assessment.

The allocation splits Task 1-first and Task 2-first 3/3 across slots; split
sessions into practical blocks with breaks. Freeze block order, onboarding and
practice limits before sessions. Keep tasks/cases isolated; don't reveal answer
keys or review verdicts between tools. Report carryover, experience and period
patterns; this small design cannot remove all learning effects.

## Timing, failures and correctness rubric

The proposed limit is **3,600 active seconds per task/tool attempt**, identical
across tools. This is a product-study timeout, not a clinical threshold.
Confirm it in the freeze after a separate technical/expert rehearsal. Start at
the neutral task prompt and stop at submission of a claimed complete report.
Include reading, coding, debugging, interpretation and report preparation.
Pause active time only for breaks or unattended computation; retain interval
start/end/reason records. Record installation, wall-clock elapsed time, compute
time and substantive assistance separately. Compute can overlap active work;
do not sum overlapping clocks into a supposed elapsed duration.

Keep the first submitted report and bind independent review to its SHA-256.
An independent domain reviewer applies the frozen case-specific answer key and
tolerances, blinded to tool where practical by normalizing report presentation
without discarding provenance. A moderator's successful execution is not review.
Retain disagreements and adjudication; freeze who adjudicates before sessions.
Later corrected reports and retests remain separate observations and do not
replace the primary first submission.

| Mandatory rubric item | Correct, complete evidence |
| --- | --- |
| Identity and units | Correct participants, linked visits, method/plan/source identity, physical units, normalization, 0–120-minute window and direction of change |
| Coverage | All planned cases, attempts, exclusions, failures, censoring and boundaries visible; missing is not zero |
| Task 1 | Required variants, conditional uncertainty, between-variant differences and justified consistent/assumption-dependent/insufficient conclusion |
| Task 2 | Frozen actual-time subsets, removal before fitting without leakage, absolute differences/bias/precision, paired conclusions and low-C-peptide/failure accounting |
| Interpretation | Glucose/test context, separate C-peptide AUC, full-curve reference limits; no nonsignificance-as-no-change or synthetic-to-human/treatment claim |
| Reproducibility | Native report/artifact, actual export, reconstruction evidence and enough provenance to recover the result |

Every mandatory item must pass, within independently approved numerical
tolerances. Correct and complete is binary; aesthetic polish cannot offset a
missing scientific requirement. A correct explanation that the case cannot
support an estimate can pass if the frozen answer key expects that outcome.

Critical errors include wrong units/visits/window, unnoticed removed-information
leakage, dropping failures/denominators, asserting a reliable conclusion from
indeterminate evidence, or claiming biological/treatment benefit unsupported by
the inputs. Record error class, consequence, count and reviewer rationale even
for unfinished attempts. Record missed problems, unnecessary warnings and minor
issues separately. A critical error makes that report incorrect.

Statuses are `complete`, `timeout`, `blocked` and `withdrawn`. Review correctness
separately: a submitted report may be incorrect. Independent success requires
a complete, correct report within the active limit and zero substantive help.
Do not exclude timeouts, withdrawals or installation blocks from the denominator
of six. Missing sessions remain missing and prevent a complete assessment.

## Analysis and decision rules to freeze

For each task and each comparator, show all six paired records: status,
correctness, assistance, active/compute/elapsed time, critical errors and
report/evidence identities. Show individual paired differences, median and
range; stratify descriptively by team, experience and period without claiming
powered subgroup effects. No significance test establishes market value here.

Proposed quantitative progression rules are:

1. At least five of six independently correct OpenT1D reports for **each task**.
2. At least 30% lower median active time for each task against its frozen
   strongest comparator. Use the same independently successful pairs in both
   medians: `1 - median(OpenT1D time) / median(comparator time)`. Require at least
   five successful pairs and five correct comparator reports, so an unusable
   baseline cannot create an advantage. A zero denominator is indeterminate.
3. Repeat the time comparison over all six planned slots, scoring any
   unsuccessful attempt at the frozen active limit. Require the same 30% gain
   in this failure-penalized sensitivity analysis. These scores are not observed
   time to correctness; display them separately from observed clocks.
4. No additional critical interpretation errors relative to the comparator.
   Compare counts and error classes and inspect the paired records. The script
   checks aggregate counts only; the independent reviewer must assess novel
   error classes and consequences before any continuation decision.

The five-pair and failure-penalty rules are proposed conservative operational
details for the roadmap targets. Freeze or amend them with reasons **before**
human observations; changing them later is exploratory and preserves the
original analysis. Changed allocation or quantitative criteria require updating
the script and protocol schema together. Show every comparator, including any stronger result that
disagrees with the prespecified primary.

Measure person time for installation, comparator/OpenT1D preparation, integration,
analysis/reporting and maintenance separately for an actual first study and an
actual repeated study of the same frozen scope. Include expert script/notebook
construction, format conversion, report reconstruction, fixes, version updates
and reuse-specific work. Record who worked and what was reused in private
interval sheets. Enter measured zero only when no work was actually required;
unknown is missing. Do not substitute projected amortization for observation.
Show totals, category breakdowns and differences, with variation across users
and teams. Record compute/resource/license costs and who bears them even when
not part of active researcher time. Session analysis time is included once in
the `analysis` effort category, not added to those totals a second time.

The script sums logged person seconds and operation elapsed seconds. Summed
operation durations are not end-to-end wall time when work overlaps; derive
critical-path elapsed time from the interval sheet. Repeated-study analysis
intervals require separate observed repetition; the 36 primary cells alone do
not measure repeated-study effort. Label any optional cost projections separately.

After independent adjudication, a human product decision records:

- **Continue** within the tested scope if both tasks meet frozen criteria,
  error-class review is acceptable and total first/repeated effort supports a
  useful improvement. Explain remaining costs and tradeoffs explicitly.
- **Narrow** if value is supported for only one task, role or context; preserve
  failures and state which broader criteria were not met.
- **Rework or stop** if correct reports or a meaningful advantage are absent,
  or the strong baseline provides similar quality with comparable total effort.
- **Insufficient evidence** if required people, cases, reviews or access are
  missing. This is the current disposition; it is not a completed pilot verdict.

Document author, independent reviewer, protocol/hash, paired evidence,
deviations, total effort, dissent and next scope. Passing CI or numerical checks
does not supply a human product decision. This small formative pilot supports
a bounded product choice, not a population-wide market or clinical effect claim.

## Local preparation software

From the repository root, create a new ignored private packet:

```sh
uv sync --locked
uv run --locked python scripts/ot056_pilot.py init results/ot056-pilot-draft
uv run --locked python scripts/ot056_pilot.py summarize results/ot056-pilot-draft
```

`init` refuses to overwrite any directory. It creates a draft plan, the fixed
placeholder allocation and header-only roster/session/review/effort CSV files.
No participant record is generated. A draft summary is valid bookkeeping output
with `status: not_evaluable`, empty observations and `product_decision: null`.

Complete the [freeze and observation forms](ot056-pilot-forms.md) privately,
bind case/answer-key and source commits and archive a hash snapshot before the
first session. Fill the plan's evidence references, primary comparators and
timeout from that freeze. Only actual human evidence permits the declaration
`evidence_kind: human_sessions`; internal rehearsals use `technical_rehearsal`.
Set `status: frozen` only after the independent prerequisite review. Record the
pre-session plan hash in session records and keep the archived bytes to detect
post hoc edits. Any changed protocol gets a separate packet and amendment.

The summary rejects duplicate/unknown attempts, changed allocation, wrong cases,
unbound reviews, inconsistent correctness, invalid times and nonfinite values.
It preserves all six slots in each comparison. Missing coverage, prerequisites,
teams, reviews or first/repeat effort keeps the assessment not evaluable.
Output hashes bind the six input files; save the JSON outside the packet or
under a different name. `quantitative_gates_met` stays null while prerequisites
are missing. Even a fully populated packet returns
`requires_independent_product_decision` and never fills `product_decision`.

This is a local bookkeeping check, not an authentication system: references and
declarations require human verification, as do timing intervals, reviewer
independence, rubric compliance and error classes. It runs no estimator, reads
no health records and grants no rights or session approval.

## Internal verification and remaining acceptance

The bookkeeping tests use invented temporary fixtures. They verify allocation
balance, hand-calculated paired timing, retained missing/timeout/helped/incorrect
attempts, evidence binding, nonfinite rejection, malformed readiness, target
boundaries and overwrite protection. Blank pilot forms are never populated by
the synthetic technical rehearsal.

The final integrated code `1e2b9ab` passes `uv sync --locked` and
`uv run --locked python scripts/check.py`: **1,390 tests, 13 existing skips**,
repository linters/navigation checks and the strict documentation build. The
skips require the separate C1 PyTorch runtime. The separately locked unchanged
estimator reference also passed; its limited scope is described above.

The retained archive `results/ot056-final-fc602` contains all 22 native/notebook
case comparisons. Its original output path was removed before fresh-process
verification. Verification was repeated after both final handoffs were installed.
The archive manifest SHA-256 is
`2a82eadb89a0df9dc5e71dc95189ece0622fc5d200419d269c88a32ab13b5771`.
The machine-readable record binds controlled sources, the complete source
projection, actual command outcomes and retained check-log hashes. The
[OT-054](ot054-verification.md) and [OT-055](ot055-verification.md) records bind
the producer browser exercises; the final combined checkout reruns their
HTTP/frontend/process regressions. No independent human usability is inferred.

Remaining human acceptance requires actual intended researchers across at least
two teams, an independent domain reviewer, expert qualification of the cases
and both comparator workflows, authorized installed comparator access with
working export/reopening, and frozen session/analysis criteria. Then collect
actual first-report correctness, first/repeated-study effort, timing and
assistance, retain adjudication and make a reasoned product decision. The
technical implementation is complete; the full researcher-pilot goal remains
open. No outreach or human finding is supplied by this software verification.
