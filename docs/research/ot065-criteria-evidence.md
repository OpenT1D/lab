# OT-065 — Selected workbench criteria and evidence

## Decision and scope

Audit date: 15 November 2026. **OT-065 remains open: actual screen-reader
qualification is not yet established.** The implemented selected workflow is
the two synthetic MMTT tasks on the internal Apple Silicon Mac Concept v1
application, with the same installed Python/CLI project services. The
[roadmap](../../ROADMAP.md#selected-concept-v1-implementation-slice-ot-065)
selects implementation scope; the full
[OT-065 acceptance row](../../ROADMAP.md#planned-core-and-product-work-packages)
and [product requirements](../product-laboratory.md#workbench-delivery-and-long-term-use)
retain the accessibility and onboarding requirements. This audit does not
silently remove a criterion to close the package.

The work started from clean current main
`194805ba5647e4eee7388798440b698ea898a647`, the PR 85 merge. Its tree,
`e90c7ef5f3c51b2f6e6a2ed0039d058735b7c84b`, equals the tested clean head
`bb3c7fee4d3792c3f58aed9e218410f57fc4ae22`. That equality permits the existing
exact-artifact results to support the unchanged product implementation. It
does not turn a later documentation revision into a newly built app or a new
screen-reader result.

## Criterion-to-evidence matrix

The four dispositions are **proved** (implemented with appropriate bounded
evidence), **underverified** (implemented but required evidence remains),
**missing** (an absent deliverable) and **separate** (explicitly outside the
selected OT-065 increment). An onboarding presentation gap found in this audit
is addressed below. No additional missing implementation was identified in the
selected workflow; that finding does not imply exhaustive defect detection.

| Applicable criterion | Disposition and evidence | Limit or required next step |
| --- | --- | --- |
| Same scientific plan and core validation through GUI, CLI and Python | **Proved.** [Installed SDK](../installed-sdk.md), [editable workbench](editable-workbench.md) and actual installed parity checks retain plan/parent/attempt identities and native readers. Fresh Python/CLI exercises in this audit cover both tasks outside the checkout. | No stable general model API or universal engine contract follows. |
| Project, draft, freeze and compatible inputs | **Proved.** Saved immutable concept revisions, exact-revision validation, explicit freeze, parent-linked variants and task-specific input rosters use existing services. PR 85 desktop cases cover both approaches; earlier workbench cases cover original byte preservation, invalid correction and conflicts. | Assets are the selected synthetic MMTT inputs and settings, not arbitrary interchangeable physiology modules. |
| Useful errors and recovery | **Proved within the recorded cases.** Invalid/refused work retains edits; forensic/failed/incomplete attempts remain distinct. Actual native tests cover failure/retry. The additional recovery probe checks explicit stopped-executor consent, passive opening and preserved partial evidence. | The unfinished fixture was deliberately constructed with the existing helper. This is not an observed spontaneous crash-recovery claim or checkpoint resume. |
| Real progress, cancel and retained attempts | **Proved.** Real SDK phase/elapsed time, owned cancellation, retry and native quit/owner-loss cleanup are covered by packaged cases with process-start identities and a separate preserved sentinel. | No estimated percentage, hostile-code sandbox or other-host lifecycle claim. |
| Question-led comparison and native report/table export | **Proved.** Prospective question, baseline and roster precede execution. Paired desktop comparison and separate sampling comparison retain first attempts and unavailable support. JSON/Markdown/CSV and sampling child exports match native bytes. | Comparison direction and full denominators remain task-specific; no universal ranking or additional scientific estimand. |
| Screen/interaction specification, component guide and annotated states | **Proved as design preparation.** The existing Figma specification, three-screen examples, 14 annotated states, compact guide and internal walkthrough were found and read; see the design map below. | Static design review supplies neither executed product behavior nor user acceptance. Current Concept choices supersede the earlier presentation details. |
| Keyboard, zoom, narrow layout and status beyond color | **Proved within selected checks.** Packaged cases include actual Electron zoom factor 2 at an 800-pixel content width, no page overflow, focus transitions and explorer Escape. Browser cases cover narrow text reflow, controls and dialogs. Status and completeness use text. | These selected checks are not complete WCAG, contrast or assistive-technology qualification. |
| Actual screen-reader operation | **Underverified.** The [accessibility record and ten-case protocol](ot065-accessibility-qualification.md) identify the exact app, prepared fixtures, actual activation attempt and missing observation channel. | Genuine VoiceOver phrases/navigation, table header/value relationships and necessary status/error announcements must be observed. Ordinary AX/ARIA or a running VoiceOver process cannot close this row. |
| Reopen preserves work | **Proved.** Native save/quit/reopen, authoritative history hydration, retained attempts and prospective comparison restart checks pass on the candidate. Source/browser cases preserve failed/unapplied edits and conflicts. | SDK project copying alone does not copy GUI workspace concept histories; keep the stated storage boundary. |
| Analyst tutorial | **Proved as supplied and technically reviewed guidance.** The [two-task tutorial](../installed-gui.md#first-analyst-exercise) connects the existing creation, freeze/run, result, comparison, variant and reopen procedures with expected checkpoints. Labels and ordering were separately checked against the implementation. | A fresh independent analyst has not completed it; that is OT-072. |
| Programmer adapter/notebook route | **Proved within the selected offline scope.** [Python/CLI](../installed-sdk.md#python-exercise-outside-the-checkout) and the [notebook entry](../installed-sdk.md#existing-same-estimator-notebooks) reuse the existing SDK and both same-estimator notebooks. Fresh installed operations and notebook comparison passed. No new adapter is needed for this task family. | Notebooks run in the pinned checkout and do not create SDK ledgers. Installed plans are explicitly opened/derived in Concept; no Jupyter UI or external contributor claim. |
| Intended-user/recipient acceptance, human-data and biological evidence | **Separate.** OT-072 and the scientific task protocols retain these questions. | Agent review and synthetic software checks do not supply them. |
| Clean-host distribution, Developer ID/notarisation, Windows, new engines or M5 execution | **Separate.** OT-073/058 and separately selected implementation packages own those outcomes; Windows and M5 execution are not selected here. | Existing broad product ambitions remain. No platform, release or multi-engine promise is newly closed by this audit. |

## Existing design evidence and supersession

The read-only audit found the following in the existing
[Figma file](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm):

| Artifact | Existing content and evidence role |
| --- | --- |
| [Canonical screen/interaction spec, node 9:205](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=9-205) | 191 lines, scientific identity/state rules, primary action conditions, task-specific interpretation, comparison/error rules and traceability. Section 10 records the 14 November internal walkthrough and corrected counterexamples. |
| [Screens/prototype, node 5:12](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=5-12) | My research, Research and Results, S01–S20 task-specific desktop examples, three narrow compositions and an explicit static-prototype explanation. |
| [State catalogue, node 8:2](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=8-2) | E01–E14: empty projects/results, loading, validation, conflicts, execution failure, stopping, incomplete/unfinished evidence, reader refusal, comparison refusal/unavailable cases, unresolved conclusions and unavailable storage/server. These are annotated synthetic designs, not fabricated incidents. |
| [Compact guide, node 9:2](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=9-2) | Typography, colors, spacing, action/field/status/table components, focus and narrow/zoom targets. Earlier light/teal proposals remain historical design evidence. |
| [Concept v1, page 20:7](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=20-7) | Accepted compact launcher 20:26 and dark Study 20:94; [continuation 49:35](https://www.figma.com/design/OXMicPqyaLtz26ZzO56qfm?node-id=49-35) selects the execution section, Results tab, prospective comparison and explicit GUI recovery. |

The Concept continuation and [operational guide](../installed-gui.md#concept-v1-study-workbench)
govern current control labels and placement. In particular, the older E09
CLI-only recovery instruction is superseded for Concept by the explicit
stopped-executor checkbox and recovery action. The current dark layered
surfaces, limited blue primary actions, observation/assumption accents and
compact layout do not require reproducing the earlier light-theme proposal.
No design, retained candidate or frozen participant exercise was rewritten in
this audit. A separate read-only agent also read the specification and confirmed
this interpretation; it remains technical review, not intended-user evidence.

## Retained execution evidence

The earlier `f245` worktree retains
`results/ot065-concept-workflow/verification.json`, its full check log and
`results/concept-desktop-tests/results.json`. These local files are not public
release downloads. The PR 85 full local check on clean `bb3c7fe` passed:
2,498 tests, 32 skips, no failures/errors; the unit stage took 4,342.206 seconds.
Thirteen skips require the locked C1 PyTorch environment; nineteen require
actual Windows host/installer/kernel behavior. The log's nested deliberate
`CONTROL ASSERTION` failure is a test-runner self-test whose outer case passed.
The [hosted PR 85 run](https://github.com/OpenT1D/lab/actions/runs/43749425281)
also passed its required software checks. Skipped native/scientific jobs add no
numerical evidence.

The exact relocated ZIP candidate has 11 passing desktop cases, zero skips,
unexpected or flaky cases, in 253.206 seconds. Its archive SHA-256 is
`4c3732f6d267b6a0ca5602aa8b4ae4b024d4170650e5cf270e00be429ab0a8a3`.
The separate sampling comparison retained all 30 comparison cases and 60
native slots; the explicit-recovery probe retained forensic partial bytes and
the original plan across retry. Their local receipts are respectively
`/private/tmp/opent1d-ot065-sampling-comparison-evidence/probe-result.json` and
`/private/tmp/opent1d-ot065-native-recovery-evidence/native-recovery-result.json`.
The new accessibility audit read back all 1,804 regular files and 14 links
against the selected app receipt without mismatch.

Adverse historical checks remain recorded: an initial download fixture lacked
Playwright download admission; a callback fixture used the wrong argument; and
a real reopen race required the PR 85 hydration guard. A 20-person/1,024-draw
probe completed computation but exceeded the unchanged 16 MiB reader bound and
was preserved as forensic failure. The successful smaller lifecycle fixture
does not erase that limitation. No reader bound or tolerance was relaxed.

## Onboarding verification and current handoff

The onboarding change adds connected instructions to the existing canonical
GUI and SDK guides. Existing analyst task guides, Python/CLI entry points and
both fixed notebooks were discovered first and retained. Public examples remain
invented; no scientific implementation, source/reader identity, frozen plan,
reference or tolerance changed.

Fresh wheel build/install and Python/CLI execution used a new environment and
working directory outside the checkout, on macOS arm64. The clean base wheel
SHA-256 is `2260f347ceddf8c5b4efba82557922eb1519e2c8772b31917243f4861d15702d`.
The evidence under `/private/tmp/opent1d-ot065-onboarding-evidence/` includes
`receipt.json` and its committed handoff binding. It covers paired execution,
retry, reconstruction and copied-project reopen; complete sampling with 60/60
slots; a derived plan, prospective comparison and exact saved-tip JSON/CSV
replay; and both existing notebooks. Paired reports match byte for byte.
Sampling Markdown and child reports match; its parent JSON matches as parsed
objects after excluding only the top-level native `execution` journal in
memory; the direct-estimator notebook does not create that native journal.
The saved original is
untouched. Across both tasks, eleven report files are byte-equal; the remaining
parent JSON comparison retains `execution_status` and every scientific field.
No values are rounded and no tolerance is used. This fresh notebook check does
not separately compare attempt journals or frozen-plan files.

The additional CLI sampling probe first guessed an example file path and was
correctly refused, then passed using the paths actually returned by example
creation. That probe error is retained; it is not a failed documented paired
command. A denied default uv-cache access was resolved using the explicit
admitted cache. Neither event was concealed or repaired by changing contracts.

The final handoff must identify the integrated revision, clean/dirty state,
separate diff review, local style/navigation/strict-doc outcomes and the exact
required CI run. This is a documentation-only change: required CI supplies the
full current-revision suite under the [verification policy](../development.md#documentation-only-changes).
The earlier full run is unchanged-implementation evidence, not the full CI
receipt for these new documents. Screen-reader observations remain subject to
the explicit accessibility record; this package cannot be marked complete
while that binding row is underverified.
