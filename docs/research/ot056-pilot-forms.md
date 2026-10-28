# OT-056 blank pilot forms

Use with the [pilot protocol](ot056-researcher-pilot.md). All observation cells
below are intentionally empty. Copy forms into the authorized private workspace;
do not commit researcher identities, recordings or health records. Generated
CSV headers come from `scripts/ot056_pilot.py init`; allocation rows are planned
slots only. A missing observation is never a zero, success or inferred answer.

## Freeze and readiness record

| Field | Evidence/reference |
| --- | --- |
| Protocol version, freeze date, owner and archived plan SHA-256 | |
| OT-053 disposition and approved endpoint/units/normalization/kinetics scope | |
| Controlled OT-054 and OT-055 commits, reproduced checks and supported routes | |
| Case manifest, source bytes/hashes, synthetic or authorized-human scope | |
| Three matched cases per task, difficulty review and retained failure content | |
| Independent answer key, numerical tolerances, reviewer and adjudicator | |
| Actual-tool version, competent scripts and permitted use/handoff | |
| Notebook method/source/runtime identity and expert review | |
| Demonstrated imports, endpoint parity, full and incomplete exports/reopening | |
| Primary strongest comparator for each task and pre-session selection rationale | |
| Six actual researchers, two teams, experience and participation references | |
| Random slot assignment, seed, task/block order and break plan | |
| Equal onboarding, practice, information, accessibility and help/AI policy | |
| Active timeout, timing procedure and rubric/analysis amendments | |
| First and repeated-study scope, environment/reset policy and cost accounting | |
| Authorized recording, storage, access and public-summary scope | |
| Unresolved prerequisites and disposition | |

Keep actual identities and consent/contact information in a separate protected
record. `roster.csv` uses only R01–R06, non-identifying team codes, experience
evidence and participation evidence. Codes are assigned only to actual people.
The reviewer must be independent of implementation and coaching; record
conflicts, blinding limits and adjudication arrangements in the freeze.

## Neutral task cards

Supply the same scientific requirements for every arm, with the allocated case.
Replace bracketed fields only from the verified case manifest, before freezing.

**Task 1:** "Using [case], assess whether the estimated visit-to-visit change in
total endogenous insulin secretion over measured 0–120 minutes is consistent
across [frozen variants]. Submit a complete report with estimates, paired change,
conditional uncertainty, all planned attempts and failures, glucose/test context,
separate C-peptide AUC, provenance and a justified conclusion. Preserve the
report and show how its saved analysis can be reconstructed."

**Task 2:** "Using [case] and the same endpoint and analysis method, assess the
information lost under [frozen subsets of observed times]. Refit after removal
without using removed measurements or learned parameters. Submit the full and
reduced estimates, absolute differences, bias, precision, paired conclusions,
low-C-peptide behavior, all failures, provenance and a justified conclusion.
Preserve the report and reconstruction evidence. Explain what the comparison
does and does not justify about future sampling."

Provide the frozen scientific specification and ordinary tool documentation,
not the expected numerical answers. The task card does not prescribe clicks.

## Session observation sheet

| Field | Actual observation |
| --- | --- |
| Slot, team/experience reference, task, tool, period and allocated case | |
| Session date, moderator, protocol/hash and case/runtime/report identities | |
| Platform, environment state, training/practice and prior-tool experience | |
| Prompt/start, submission/end, breaks and active-time total | |
| Compute start/end, elapsed time and overlap with active work | |
| Interval: start/end, person, category, task, tool, study and reason | |
| Help request/source/content/duration and accessibility accommodation | |
| Complete, timeout, blocked or withdrawn; failure explanation | |
| First report path/SHA-256, raw artifacts, exports and reconstruction evidence | |
| Researcher's own conclusion and explanation of limitations | |
| Missed problems, unnecessary warnings, errors and observed consequence | |
| Deviations, interruptions and missing/unassessed information | |
| Separate corrected submission or retest identity, if any | |

`sessions.csv` has one primary row per allocated slot/task/tool, with status,
active/elapsed/compute seconds, substantive assistance count, first report
SHA-256 and retained evidence reference. Complete reports require a positive
measured active time and lowercase 64-character SHA-256. A failure without a
report uses an empty hash. Missing sessions remain absent; do not invent rows.
Use the interval sheet to substantiate the numerical totals.

## Independent review and adjudication

| Field | Independent assessment |
| --- | --- |
| Reviewer, independence/conflicts, blinding limits and review date | |
| Slot/task/tool, case/answer-key/protocol identity and report SHA-256 | |
| Identity/units/window/direction criterion and evidence | |
| Complete planned coverage, censoring, boundaries and failures | |
| Task-specific estimates/uncertainty/conclusion criteria, with tolerances | |
| Glucose context, AUC distinction and interpretation limitations | |
| Export/provenance/reconstruction criterion | |
| Correct and complete: yes/no, reason and supporting locations | |
| Critical error classes/counts, consequences and comparator contrast | |
| Minor issues, missed problems and unnecessary warnings | |
| Disagreement, adjudicator verdict, reason and preserved original assessment | |

`reviews.csv` binds the same submitted report hash, a `yes`/`no` correctness
verdict, critical error count and review evidence reference. Review unfinished
attempts as well, including errors already expressed. Never rate an unfinished
or critically incorrect report as correct and complete. A review does not erase
substantive help recorded in the session. The machine counts errors; reviewers
must inspect new error classes and consequences themselves.

## First and repeated-study effort sheet

| Field | Actual measurement |
| --- | --- |
| Tool, study (`first`/`repeat`), scope, team and observed date | |
| Category, person/role, interval start/end, person seconds and elapsed seconds | |
| Installation and environment preparation, including failed attempts | |
| Expert scripts/notebook/OpenT1D preparation and format conversion | |
| Integration with existing data/report systems | |
| Analysis, interpretation, report assembly and reconstruction | |
| Maintenance/fixes/updates, actual reuse and repeat-specific changes | |
| Compute/resource/license costs, currency/date and actual payer | |
| Overlapping work, critical-path duration and prevention of double counting | |
| Evidence reference; measured zero or missing/not assessed explanation | |

`effort.csv` allows multiple nonoverlapping person-work entries in each
tool/study/category. Categories are `installation`, `preparation`, `integration`,
`analysis` and `maintenance`. Assign each work interval once. Sum primary-session
active time into `analysis` only once; record separate repeated-study work.
Include documented measured zero where applicable, not a guessed zero for
unobserved work. The script requires coverage of all categories for each tool
and both studies; it cannot verify the intervals or unseen work by itself.

## Product decision record

| Field | Evidence and decision |
| --- | --- |
| Owner, independent reviewer, date, frozen plan and input/output hashes | |
| All six paired records for both tasks and both comparators | |
| Independently correct reports out of six; timeouts/help/withdrawals | |
| Median paired-subset time reduction, individual differences and range | |
| All-six failure-penalized time sensitivity, separately labeled | |
| Critical error counts, classes, paired consequences and reviewer assessment | |
| Actual first/repeat total effort, breakdowns, variation and costs | |
| Experience/order/case effects, deviations, dissent and unassessed scope | |
| Continue, narrow, rework/stop or insufficient evidence; explicit rationale | |
| Follow-up scope and remaining software/usability/empirical gates | |

Leave this record blank until actual reviewed sessions exist. A successful
script run or synthetic rehearsal does not supply its observations or decision.
