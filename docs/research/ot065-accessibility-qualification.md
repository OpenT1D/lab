# OT-065 — Concept v1 accessibility qualification

## Scope and decision

This record separates the existing automated accessibility checks from actual
screen-reader use of the internal Concept v1 Mac application. It covers the two
synthetic MMTT tasks, Study execution, selected results and prospective
comparisons. It does not qualify the full laboratory, another operating system,
a public distribution or independent intended-user acceptance.

The [selected Concept increment](../../ROADMAP.md#selected-concept-v1-implementation-slice-ot-065)
requires keyboard/focus, narrow/zoomed layouts and non-color status. Actual
screen-reader qualification remains a separate requirement in
[OT-065](../../ROADMAP.md#planned-core-and-product-work-packages) and the
[product requirements](../product-laboratory.md#workbench-delivery-and-long-term-use).
The [installed GUI guide](../installed-gui.md#concept-v1-desktop-application)
owns the application procedure; [decision 0114](../decisions/0114-concept-v1-desktop-workspace.md)
owns its native window and process boundary. This record adds no numerical,
scientific-input, reader or shared-service change.

## Candidate and retained evidence

The selected relocated app is the clean PR 85 candidate built from
`bb3c7fee4d3792c3f58aed9e218410f57fc4ae22`. Its Git tree is
`e90c7ef5f3c51b2f6e6a2ed0039d058735b7c84b`, identical to main
`194805ba5647e4eee7388798440b698ea898a647`. The app contains Electron 45.3.2,
CPython 3.12.16 and the two-task installed SDK descriptor 4. The ZIP SHA-256 is
`4c3732f6d267b6a0ca5602aa8b4ae4b024d4170650e5cf270e00be429ab0a8a3`.
The current host reports macOS 26.5.2, build 25F84, arm64. The declared macOS 13
minimum is not a tested minimum-host result.

Local evidence remains outside version control. These are internal receipts,
not publicly downloadable release artifacts:

| Evidence | Local location and observation |
| --- | --- |
| Selected artifact | `/private/tmp/opent1d-ot065-relocated/build-result.json` and its `OpenT1D.app` |
| Fresh artifact readback | `/private/tmp/opent1d-ot065-accessibility-artifact-readback.json`: all 1,804 regular files and 14 symbolic links match the selected receipt; no mismatch |
| Existing packaged-window results | `results/concept-desktop-tests/results.json` in the earlier `f245` worktree: 11 passed, no skipped, unexpected or flaky cases; started 15 November 2026 at 18:50:59 UTC, duration 253.206 seconds |
| Isolated screen-reader fixtures | `/private/tmp/opent1d-ot065-accessibility-session-20261115/fixtures.json` and its separate `workspace` |
| Exact-app startup probe | `/private/tmp/opent1d-ot065-voiceover-20261115/launch.json`: selected relocated app path and separate workspace; Electron reported accessibility support off before VoiceOver activation. This duplicate owned instance was closed before the coordinator continued the session. |

The existing packaged suite's saved identity attachments bind its checks to the
same clean candidate source. Its results are reused for the unchanged tree;
the full native suite was not repeated merely to create this record. The fresh
readback checks the delivered files and link targets against the receipt; it
does not independently authenticate upstream archives or test installation on a
clean host. A sandboxed attempt could not launch Electron. The explicitly
approved native launch succeeded; this distinction is retained in the handoff.

## Criterion and evidence matrix

| Criterion | Evidence already present | Remaining qualification |
| --- | --- | --- |
| Keyboard access and focus return | `tests/browser/concept-v1.spec.mjs` checks save shortcuts and narrow explorer Escape/focus return. `tests/desktop/mac.spec.mjs` checks review-dialog return, Check readiness to Run focus, Results and Study heading focus, and narrow explorer return in the real packaged renderer. | Actual VoiceOver navigation and native-menu interaction; the existing cases do not exhaust every keyboard sequence. |
| Zoom and narrow layout | Both packaged MMTT task cases set the actual Electron zoom factor to 2 in an 800-pixel content window, observe a CSS viewport below 650 pixels and require no document-wide overflow in Results and Study. Separate browser result checks use 390 pixels with 200-percent root text and exercise table/control navigation. | No claim about every host display, assistive zoom setting or combined user preference. Scrollable native tables retain their own region. |
| Status without color | Execution and attempt text names action, plan, execution status, evidence completeness and complete/planned slots. Result/comparison text retains incomplete, failed and unattempted cases. The packaged suite exercises those states and exports their native reports. | Actual screen-reader discovery and live announcements; a text-state check is not a complete visual-contrast or color-vision assessment. |
| Control names and structure | The supplied source uses associated labels, named dialogs, headings, status/alert roles, current-page state and named scrollable tables with captions and column headers. Existing browser and packaged checks address selected accessible names and focus destinations. | The actual macOS accessibility tree can check exposure; it cannot establish what VoiceOver says or how its cursor moves. |
| Correction and preserved work | Existing Concept browser cases retain unapplied input, failed saves and conflicts; packaged cases retain saved work across normal quit and owner/renderer loss. | VoiceOver must find the error, correction action and retained edit without assistance. |
| Scientific content access | Native result tables and exact Markdown/JSON/CSV exports accompany figures. Packaged MMTT and comparison cases verify exported bytes and retained identities. | VoiceOver table navigation, header/value association, units, limitations and export-dialog use. A figure's alternate text alone is insufficient. |
| Screen-reader operation | VoiceOver and VoiceOver Utility are installed on this Mac. An actual app accessibility-tree inspection is feasible. | A genuine VoiceOver session with recorded commands and its own observed output. Installation, ARIA, browser assertions and an ordinary app accessibility tree do not satisfy this row. |
| Independent intended-user use | Candidate-bound exercise preparation exists separately. | Actual intended-user and recipient sessions remain unrun under OT-072; an agent's technical session cannot close them. |

The historical [thin-GUI record](ot065-072-shared-gui.md) and
[editable-workbench record](editable-workbench.md) retain their own earlier
browser and accessibility limits. They are not retroactively promoted to an
actual-screen-reader result by the new app's existence.

## Isolated fixture preparation

Use only invented example data. The prepared workspace is separate from the
existing default workspace and from any researcher project. Its installed
controller lease was closed before app launch. Fixture preparation used the
selected app's bundled interpreter and installed controller, not a source-tree
replacement for either component. The retained local preparation recipe is
`/private/tmp/opent1d-ot065-accessibility-fixtures.py`.

The fixture roster is chosen before screen-reader observations:

| Project | Prepared state and purpose |
| --- | --- |
| `VO paired ready` | Supplied complete paired example, 32 perturbation draws, saved/reviewed/frozen. No attempt exists initially. Its two-member `VO prospective volumes` comparison freezes nominal and volume-120, an explicit baseline and the question before execution. This supplies readiness, execution and unattempted comparison states. |
| `VO sampling incomplete` | Supplied incomplete sampling example, 32 draws, saved/reviewed/frozen and actually executed through the installed controller. Its retained outcome has incomplete evidence and failed slots. This supplies real incomplete native tables and complete planned support. |

To recreate these states without the local recipe, start an empty explicit
workspace, create each project from its named supplied template, set draws to
32 in Assumptions, apply/save, review and freeze. In the paired project, freeze
the two-member comparison before running it. In sampling, use the incomplete
template and run once. Retain the receipt's actual IDs rather than predicting
new attempt identities. Preparation runs are not participant observations.

Launch the selected app directly with an absolute workspace path:

```sh
/private/tmp/opent1d-ot065-relocated/OpenT1D.app/Contents/MacOS/OpenT1D \
  --workspace /private/tmp/opent1d-ot065-accessibility-session-20261115/workspace
```

The shell hashes an explicit workspace path into a separate temporary Chromium
profile before acquiring its single-instance lock. This permits the isolated
candidate beside an older default-workspace instance. Select the process whose
app path and workspace match the launch receipt; the bundle identifier alone
can select the older app. The existing user's `Testing` project is not a
screen-reader fixture and must remain untouched.

## VoiceOver session protocol

Record date, operator, exact candidate receipt/source, host, fixture IDs,
VoiceOver language and the initial on/off and caption-panel state before any
session action. Record the actual command, resulting screen/focus or VoiceOver
cursor, output verbatim where practical, assistance and pass/fail/inconclusive
for each case. Keep unexpected results and abandoned paths. Do not replace an
unobserved announcement with the text expected from source code.

Apple documents Command-F5 as the VoiceOver toggle. If the welcome dialog
appears, Return continues; do not select the option that suppresses future
welcome dialogs. The default VoiceOver modifier, written `VO` below, is
Control-Option or Caps Lock. Function-key behavior can require Fn. Use the
host's actual supported key mapping and record it.
See [Apple's activation guide](https://support.apple.com/guide/voiceover/turn-voiceover-on-or-off-vo2682/mac)
and [keyboard navigation guide](https://support.apple.com/guide/voiceover/control-your-mac-with-keyboard-commands-vo2681/mac).

A usable observation channel must come from VoiceOver itself. If audio is heard,
record that explicitly. If audio is unavailable, Apple's caption panel displays
what VoiceOver is speaking and can provide actual phrase evidence through a
screenshot or accessibility inspection of that panel. Record this as caption
output, not audio listening. Apple documents `VO-Fn-Command-F10` for toggling
only the caption panel; preserve and restore its original state. Do not change
speech, voice, verbosity, tracking, Quick Nav, braille or scripting preferences
merely to make the check easier. See
[Apple's caption-panel guide](https://support.apple.com/guide/voiceover/use-the-braille-and-caption-panel-unac078/mac).

The installed VoiceOver scripting dictionary also exposes read-only last-phrase
and cursor text, but that route is optional and was not used for this protocol.
It may need separate scripting/automation access. An app's ordinary
accessibility tree, a DOM snapshot, `aria-live` attributes or Electron's
accessibility-support flag alone cannot substitute for VoiceOver output.

| Case | Action and acceptance chosen before observation |
| --- | --- |
| VO-01 — Launcher | With the selected candidate foreground, turn VoiceOver on if initially off. Use VO-Left/Right to find Recent projects, both fixture names and New project. The names and roles identify the controls; activating the paired fixture opens that project. Record the first actual VoiceOver phrase before continuing. |
| VO-02 — Study and dialogs | Navigate the Study heading, Research question and Approach. Open Observations or Assumptions with VO-Space; use VO-Shift-Down/Up if interaction with a group is required. Field names, current values and the dialog title must be available. Escape/Cancel returns to an identifiable invoking control and preserves the saved inputs. |
| VO-03 — Correction | In a disposable new study or unfrozen derived revision, enter invalid synthetic content, apply/review and record the resulting error. VoiceOver must announce the error or allow it to be found from the active context, identify a correction route and retain the attempted edit. Correct it and review again. Keep the frozen fixtures unchanged. |
| VO-04 — Review and readiness | Open Review study, read the synthetic-only/no-analysis-yet explanation and close it. Check readiness for the paired frozen plan. VoiceOver must identify the dialog, selected plan, ready status and available Run action. Distinguish a reviewed draft, frozen plan and completed attempt. |
| VO-05 — Execution and result transition | Run the paired plan once through VoiceOver. Record actual action/status output and the settled attempt; do not require a fabricated percentage. Navigation or polling must not continually restart speech or steal the user's cursor. Open results and identify the new heading and selected attempt. A run too brief to observe a live announcement leaves that part inconclusive. |
| VO-06 — Verification and table | Activate Verify saved report. Read completeness, selected plan/attempt context, one native table's caption, headers, units and values, and a limitation. Use VoiceOver navigation to establish the header/value relationship; merely finding the text in an app tree is insufficient. |
| VO-07 — Incomplete evidence | Open `VO sampling incomplete`, select its retained attempt and verify. VoiceOver must expose incomplete evidence, failures and planned support without relying on color. Expand a schedule report and navigate its table or exact export. Record any indistinguishable disclosure/control names. |
| VO-08 — Comparison | Open `VO prospective volumes`. Read the frozen question, baseline, member roster and first-attempt policy. After the paired run, one shared first attempt can serve both variants; neither retry nor later execution may silently replace the selected first-attempt meaning. Read the native comparison table through VoiceOver. |
| VO-09 — Native commands and export | Open the native File menu by keyboard and identify Save/Open Project without activating an unrelated project. Export one verified report into the disposable session directory through the native save dialog. Record the actual dialog navigation and preserved report identity. |
| VO-10 — Reopen and restore | Save/close the test-owned candidate normally, reopen the explicit workspace and find the saved question, plan and attempt without a new execution. Restore the original VoiceOver and caption-panel states. Retain the workspace and transcript for review; do not stop or modify the older app. |

A case passes only when its required behavior and VoiceOver output are observed
on the selected candidate. Record a failure for a reproducible inaccessible
control, lost context, missing necessary announcement/content or misleading
status. Record an environmental failure separately from an application defect.
A blocked activation, absent caption/audio observation, unsupported input
command or too-short event is inconclusive for the affected case. A partial
session qualifies only the cases and states actually exercised. It does not
supply WCAG conformance, another assistive technology, another host or OT-072
acceptance.

## Current qualification boundary

The fixture preparation, artifact readback and initial exact-app launch are
completed internal technical work. At the preparation boundary, no genuine
VoiceOver phrase or navigation result has yet been recorded in this document.
The screen-reader criterion therefore remains open until the session outcome
is appended with its actual evidence and case dispositions. The existing
keyboard, zoom, reflow, non-color status and native-export checks retain their
bounded passing scope.
