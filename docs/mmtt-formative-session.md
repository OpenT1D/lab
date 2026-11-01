# First installed MMTT formative session

This is the operational supplement to the [internal MMTT candidate's formative
packet](internal-mmtt-candidate.md#prepared-formative-exercise-and-open-gates),
for OT-065/072. It fixes a manageable first session using its existing five task
families. The [installed workbench guide](installed-gui.md) owns operation;
[paired analysis](observation-analysis.md) and [sampling](mmtt-sampling.md) own
scientific meaning. The older [checkout session](gui-test-session.md), original
MMTT/M4 `prepare-study-packet` and [OT-056 comparative pilot](research/ot056-researcher-pilot.md)
retain their different artifacts and protocols.

**Question:** Can an intended analyst use the installed workbench to inspect a
synthetic paired meal test, compare a declared assumption and measurement
schedule, recognize incomplete evidence, recover a failed attempt and preserve a
reconstructible project? Select an actual computational/domain analyst familiar
with tables, units and uncertainty who did not build this candidate. Programming
is optional. Record relevant experience privately; a beginner session is useful
feedback but cannot establish intended-analyst acceptance. A separate actual
recipient is required for an independent handoff observation.

This page is **facilitator material and contains answers**. Supply only the
[participant card](templates/mmtt-session-participant.md), a working copy of the
packet's recovery project and its actual diagnostic receipt, and the frozen
operational guide. Keep the original task card as facilitator preparation only.
Keep answer keys,
references and observation records in a separate private location/account. Public
documentation can be discovered; directory separation is not access control.
Record prior exposure and any use of an answer-bearing guide. Do not call this a
blinded study. No session, consent, recipient or acceptance has been observed.

## Select and freeze the existing artifact

Use the retained two-task candidate B for the first session, rather than
rebuilding main. Its existing qualification selected Apple Silicon macOS,
CPython 3.12.13, descriptor 4 and the two standard-library MMTT tasks. It ships
neither an interpreter nor physiological runtimes. Installation on a new host
needs its own preflight; this is not a standalone Mac application or release.

| Retained identity | SHA-256 or source revision |
| --- | --- |
| B clean source | `ffa4e107b597050e457fbeca4a5962f42e596f11` |
| B wheel | `256ee9aba41e9e16ac88877ae9c2cd9fb19900e5fee9dbb7b069a1fe25f287f6` |
| B descriptor | `478cd53c3aca4eba7c74ff32c3f2115179fd279f925082c110d4885e0ade50fb` |
| Original `formative-packet/packet.json` | `d9c8b31770411de3ee8cb31dbc66e8a861f62830398a36ce186d89feb9623304` |

The maintainer retains the wheel, `receipt.json` and
`qualification/formative-packet/` under the private reader-candidate evidence.
Do not commit those directories or infer availability from a public source link.
Before arranging a session, the facilitator must actually locate them. If any
identity or required file differs, stop preparation and retain the discrepancy;
do not relabel a rebuilt artifact with this evidence.

Copy the blank [session record](templates/mmtt-session-record.md) outside the
sealed packet. Freeze its preparation fields: candidate/packet hashes, host and
interpreter, this supplement's revision/hash, operational guide, task card,
order, help policy, time limits, references and reviewer. Leave all human fields
empty. This supplement scopes the original packet's broad tasks to the choices
below; retain the original `Tasks.md` unchanged as preparation evidence, and use
the supplement's participant card as the sole session prompt.

## Technical start checklist

- [ ] Verify the original manifest hash above, every relative file/hash in its
  `files` mapping (109 files), plus `packet.json` itself, and no missing, extra
  or linked files. Verify the
  wheel against its receipt and the hash above. Hashes check consistency; obtain
  artifacts from the trusted maintainer, not from an untrusted replacement.
- [ ] Use a fresh canonical absolute session directory outside installations and
  existing projects. On macOS use `/private/tmp`, not its `/tmp` symlink. Keep the
  retained packet read-only. Make a working copy of its complete participant
  `recovery-project`; do not run against the retained original or a partial copy.
  Also supply its actual `events/00000004/evidence/receipt.json` as an offline
  text file, preserving its hash and original path in the preparation record.
  The GUI exposes failure status but no diagnostic-receipt viewer. This receipt
  is task evidence; supply no interpretation of its cause.
- [ ] Decide before observing whether installation is assessed or prepared.
  Prepare it for the first formative session. If observed separately, retain
  setup errors/help/times as installation evidence; do not absorb them into task
  timings. Missing CPython/uv/network access blocks setup until actually resolved.

Example facilitator installation, using the retained wheel at the substituted
absolute location and a fresh environment:

```sh
uv venv --python 3.12.13 /private/tmp/mmtt-session-environment
uv pip install --offline --no-deps --link-mode=copy \
  --python /private/tmp/mmtt-session-environment/bin/python \
  /absolute/private/candidate-b/opent1d_lab-0.0.0.dev0-py3-none-any.whl
/private/tmp/mmtt-session-environment/bin/opent1d-lab installation
/private/tmp/mmtt-session-environment/bin/opent1d-lab gui \
  --workspace /private/tmp/mmtt-session-workspace
```

- [ ] Retain `installation` output; check source, descriptor and exactly
  `mmtt-sensitivity`, `mmtt-sampling`. Open the printed loopback address. Confirm
  project creation, both task selectors, concept derivation, comparisons,
  verification/download and **Copy complete project** on a disposable rehearsal.
  Native/connected controls must be absent. Do not install native dependencies.
- [ ] Rehearse T1–T5 below with this installation, fresh inputs and a recovery
  copy. Check computed rows against the actual reference reports, not just GUI
  status. Use a separate fresh working recovery copy for the participant.
- [ ] Prepare a second installation of the **same B wheel** in a fresh environment
  and workspace for T5. Rehearse opening a full copy and reconstructing the exact
  saved tip with the old server stopped and original project unavailable. Keep
  originals for rollback. This is same-artifact relocation, not an upgrade test.
- [ ] Confirm writable export storage and that a downloaded JSON/Markdown/CSV
  report opens offline. Give the participant the loopback start address and exact
  working recovery-folder path; give the recipient the copied project path,
  comparison ID, saved ledger tip, report hashes and application identity only.
  No answer key or coaching accompanies the handoff.

Stop with Ctrl+C in the launch terminal after active work has stopped. Closing a
browser tab leaves the server running. A restart requires a fresh verification;
old displayed verification is not live evidence. Never resolve a connection
problem by exposing the service beyond loopback.

## Fixed order and facilitator checks

Reserve 60 minutes after prepared setup: introduction 5, T1 5, T2 12, T3 15,
T4 8, T5 10, debrief 5. These are planned elapsed caps, not measured performance.
Pause for an agreed break; preserve unfinished tasks at the cap. If compute or
support exceeds the slot, split the session and retain the block/timeout before
using saved reports for a separately labeled interpretation-only continuation.
Do not mark the original execution task successful because a reference was supplied.

1. **T1 — inputs.** Use **Invented paired visit** (paired `complete`). Inspect observations,
   visit order and assumptions; save/freeze the base plan **without running it**.
   Require the analyst's explanation of input identity and the estimand. Keep
   the initial response before showing an operational hint.
2. **T2 — changed assumption.** Derive an editable child from T1. Change only the
   `nominal` variant's volume from 4.585 to 5.502 L and its rationale; keep all
   required variants, observations, order, kinetics, seed and draws. Save,
   validate and freeze the child with its parent link. Freeze a two-member
   comparison of base `nominal` versus child `nominal`, with base as baseline,
   **before either runs**. Fix its question as whether the direction and magnitude
   of follow-up-minus-baseline secretion change depend on the volume assumption.
   Run both and reconstruct/download the comparison.
   Keep JSON/Markdown/CSV, exact saved ledger tip and first explanation. An
   accidental early run requires fresh derived plans and a new comparison;
   retain the mistake, assistance and extra effort.
3. **T3 — measurement schedules.** Use **Invented information loss**
   (`information-loss`), retaining the supplied
   settings and sealed development inputs. Freeze `nominal/full` versus
   `nominal/three-times` in one unattempted sampling plan before running it.
   Explain the full native schedule report as well as the selected comparison.
   Repeat with **Incomplete measurements** (`incomplete`) in a separate plan/comparison.
   Preserve all cases and allocation groups. Record whether the analyst notices
   low-C-peptide interval incompleteness as well as unavailable points.
4. **T4 — recovery.** Open the working copy of the actual failed recovery project.
   Inspect its attempt/forensic evidence, record the diagnosis and proposed
   remedy, then create an explicit retry with the failed attempt as `retry_of`.
   Its original microsecond deadline produced a terminal forensic failure, not
   a native report. A normal-timeout retry should complete. Do not demand an
   impossible report from forensic-only evidence. Keep the first failure and
   the retry/report identities. The supplied recovery project has no comparison;
   it is distinct from the facilitator's failed-comparison reference.
   Correct initial reasoning can state that the status alone does not establish
   a cause; use the supplied actual receipt to assess the subsequent diagnosis.
5. **T5 — handoff.** Save T2's report tip and hashes; copy the **complete** project.
   Stop the old server. Have the distinct recipient open the copy using the
   separately prepared B installation/workspace, reconstruct T2 at its saved tip
   and compare the report bytes/hashes. No rerun is needed. The analyst may do a
   self-reopen if no recipient is available, but recipient/independence fields
   stay empty and independent handoff remains unassessed. GUI copying includes
   concepts; CLI project relocation carries the authoritative ledger, not GUI
   workspace concepts. Record that distinction if the CLI fallback is used.

## Separate reference key and scoring

Use the intact packet's `facilitator/<role>/report.json` and `report.md`. The
following are synthetic technical checks, not participant findings. Do not put
this table or reference reports in participant materials.

| Role / location | Expected evidence for this fixed session |
| --- | --- |
| `paired`, both members' rows | T2 base before/after/change: 5722.08 / 8583.12 / 2861.04 pmol. Child: 6866.496 / 10299.744 / 3433.248 pmol; member-minus-base change contrast +572.208 pmol. Magnitude increases 20%; direction remains increase under both conditional change intervals. The original key selects `volume-120` within one plan; this session's derived `nominal` reproduces those rows, while adding a real parent/child edit. |
| `sampling`, `paired_change` rows | Five synthetic pairs: two development, three evaluation. `full`: +913.961139625 pmol; `three-times`: −302.901251722 pmol; contrast −1216.862391347 pmol. Conditional directions reverse. Full times 0/15/30/60/90/120; reduced 0/60/120 min. Comparison retains 30/30 available point rows. |
| `missing`, all rows | 26/30 available comparison point rows: 18 complete, 8 incomplete with points, 4 unavailable. Low-C-peptide point values remain available with absent intervals. The censored follow-up and paired change are unavailable in both members. The full native sampling result retains 60 slots across four schedules and three variants, with 36 complete and 24 failed; comparison rows have a different denominator. |
| `failed` / `cancelled` | Respectively 0/6 and 0/30 available comparison point rows; first failed/interrupted attempts remain selected after later retries. These are retained adverse controls, not successful analyses. |
| participant `recovery-project` | Its separate first attempt is failed/forensic/incomplete with three unavailable slots; retry remains linked and cannot erase that first outcome. |

For these fixed point checks use absolute tolerance 0.000001 pmol (including
rounding in this table); inspect the actual JSON for intervals and full support.
Do not widen scientific tolerances or rescale user-chosen cases to fit this key.
Exact saved-report handoff requires byte/hash equality, not a numeric tolerance.
MMTT estimates whole-body total endogenous secretion **including basal**, in
pmol over observed 0–120 min; paired change is follow-up minus baseline. C-peptide
concentration and AUC differ from secretion. Uncertainty is conditional engineering
perturbation, not assay validation, population uncertainty or biological truth.
Schedule selection uses development evidence only; passing subsets cannot replace
the planned roster. A comparison adds no new interval for differences.

Record task disposition and correctness separately, using the blank record:

- **Correct:** required artifacts/support and the analyst's own explanation match
  the task key, units, window, direction, uncertainty and limits. A visible
  `completed` status or repeated example label alone is insufficient.
- **Critical error:** wrong quantity/unit/window/direction; missing treated as
  zero or dropped; evaluation used for schedule selection; first failure erased
  or retry substituted; downloaded report called a full project; reconstruction
  called rerunning; software success called biological/clinical validation.
  Preserve the first statement and consequence, even if later corrected.
- **Blocked:** a technical prerequisite, refusal, execution or reader failure
  prevents a required action. Record cause/evidence before assistance or fallback.
  **Timeout**, **withdrawn**, **partial** and **not assessed** remain distinct.
- **Supported:** substantive navigation help, scientific hints, CLI assistance
  or takeover occurred. Record exact content/source/time and whether completion
  followed. A supported correct answer is not independent completion. Log ordinary
  guide use too; it does not become unassisted recall.

Read the card neutrally. Wait for a help request or two minutes without progress,
then record the first answer/state and ask whether help is wanted. Escalate from
the frozen guide to an operational hint, then a content hint or takeover. Log
each level before proceeding. Stop harmful interpretation from driving further
claims, while retaining the initial error. Accessibility accommodations are
recorded separately from substantive help. No contact or recording is authorized
by this document; arrange actual participation/recording permission separately.

## Support, preservation and interpretation

For a terminal failure, keep its ledger/receipt and retry explicitly. An unfinished
attempt requires confirmation that its executor stopped before the documented
CLI `recover --execution-stopped`; never guess from saved PIDs. For a refused
reader or changed bytes, preserve originals and diagnostics; restore an intact
copy or the correct retained application. Do not edit seals or broaden reader
compatibility. A prospective comparison's first failure stays selected: a new
question needs fresh plans and a new prospective comparison.

Private support handoff includes artifact/host identities, task/plan/attempt IDs,
exact error, minimal synthetic reproduction and attempted remedies. Keep names,
contacts, credentials and personal data out of logs/issues. Record any new glue
code, core/GUI edits and maintainer time; needing a product edit blocks that
candidate's task until a separately identified retest. Do not update during the
session or overwrite the first record.

Use one interval log: participant active work (including reading/help), compute
wall time, breaks and total task elapsed time separately. Compute can overlap
active work; do not sum them to obtain elapsed time. Record unattended compute
explicitly, and facilitator/maintainer effort separately. Missing is empty/null,
not zero. Preserve first submissions, failed work, corrections and retests as
distinct files outside the sealed packet; hash submitted reports and confirm
exports before closing. Keep participation/consent/contact records separately
protected. Review the first submission independently of coaching where possible;
record reviewer conflicts and unresolved disagreements.

The fixed report structure is: frozen scope/readiness; actual participation and
deviations; task-by-task first answers/artifacts/disposition/help/timing;
correctness and critical errors with adjudication; recovery and recipient
reconstruction; favorable, unfavorable, incomplete and missing observations;
prioritized fixes and retest scope; remaining evidence gates. Until actual
observations exist, leave the results and decision blank. Use formative findings
to improve tasks, not to estimate time savings. A later comparison needs the
separate OT-056 protocol or a prospectively frozen task-specific OT-072 design,
competent baseline, matched cases, order/help controls and total effort accounting.
No platform-wide percentage or pilot acceptance follows from this first session.

## Optional later native session

Keep M4/connected tasks in their [existing separate integrated packet](internal-integrated-candidate.md).
The exact native-qualified original is source
`94805ed12bc972acd3707313ad0a718b5753cf14`, wheel SHA-256
`41118432e1e900b66709d1671b38ce1dbbc26263a87207f3a4512cf41eccf7be`.
Merged PR #45 is `5dbdd24703480c7504fce3db6e6867ff33b3ca3e`;
the later `aa1a62f` exit-qualification fix and its supplemental checks do not
requalify another wheel for native numerical work. A new installation needs a
fresh application/interpreter-bound reviewed runtime attachment. The native
preflight, rights/privacy boundary, actual-host references and session duration
must be ready before selecting that separate exercise. Full native reports and
parameter records stay private. A rebuilt wheel, different interpreter or M3
extension inherits no native qualification. No M3 task is selected here.
