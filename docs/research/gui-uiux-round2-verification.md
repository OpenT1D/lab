# Second internal GUI UI/UX verification

This record covers OT-051, the five follow-up findings from the internal review
of main `84f7b992e04d0d802ce34813bf5b09f17adcca53`. Implementation and verification
use the separate `codex/uiux-round2-fixes` worktree on macOS arm64. These are
agent-operated software checks, not participant observations or scientific
validation. Original observations and new screenshots, accessibility states
and receipts stay private under ignored `results/usability/` directories.

## Scope and observed behavior

| Finding | Implementation and local verification |
| --- | --- |
| UX2-01 | Bounded M4 editable inputs are saved per browser tab and workspace. Reload restored a changed model identity and deselected condition. Reset restored supplied examples. After a successful native setup check, reload restored inputs but required a fresh check. Browser storage never restores readiness, frozen configuration identity or process ownership. Controlled checks additionally cover denied storage, malformed/oversized input, workspace separation and reset. |
| UX2-02 | M3 example preparation and setup checking have action-specific completion messages in both the global operation strip and M3 panel. They explicitly state that no predictor has run. Execution and reconstruction retain their separate report scope. |
| UX2-03 | A real interrupted reference was registered, made unavailable by restarting without its allowed root, hidden, recovered after reload through Show hidden references and restored. Verification remained disabled until the root was explicitly enabled again. Reconnection clears the obsolete availability error. Explicit native reconstruction retained interrupted status and 0/2 accepted sources, 0/6 cases and 0/1 pairs. All 885 files across the original reference archives retained their SHA-256 byte identities. Same-origin admission, strict boolean input, global operation ownership and the 128-reference bound remain enforced. |
| UX2-04 | A newly completed M3 comparison appeared with date/time above an older, deliberately cancelled M4 execution. Both remained accessible after restart. Results use latest recorded activity across workflow types, including saved-analysis checks. Missing legacy timestamps are explicit. Controlled checks cover mixed workflows, reordering, retained identity and keyboard focus. |
| UX2-05 | The fresh synthetic M3 comparison completed with 2/2 contributors. Its metric table showed MAE 0.3509 and contrast -2.699 mg/dL; the original JSON view retained 0.35089467990270173 and -2.6987002753982092 respectively. Absent metrics are unavailable. No native calculation, acceptance threshold or reader changed. |

## Verification status

All five tasks were retested through the local browser on 17 October 2026.
Results, M4 draft recovery and M3 metrics were also inspected at 390 × 844;
the document width remained 390 pixels and the relevant controls and tables
remained readable. The viewport override was reset afterward.

`uv sync --locked` and `uv run --locked python scripts/check.py` passed locally:
1,288 tests, with 13 existing C1 skips; lint, formatting, documentation
navigation and the warnings-as-errors Sphinx build passed. Meaningful
regressions also cover draft storage failure/untrusted inputs, status scope,
display-only rounding, exact native JSON, pointer recovery and admission.
Implementation commit `245be67adc230d38824f6ebc761ef5de3ded6105` was integrated
into main on 17 October 2026 with the maintainer-requested `[skip ci]` marker.
Scientific and GUI implementation files match the locally tested candidate;
only the roadmap and this integration record were updated during the merge.
Hosted CI was intentionally skipped. No hosted CI pass is claimed.

The new M4 execution was deliberately cancelled to exercise result retention;
this follow-up did not repeat a complete M4 numerical run. Instead it used the
existing interrupted reference's trusted reconstruction for the archive route.
Controlled failure-path checks supplement the browser exercises; denied browser
storage was simulated in the frontend harness rather than by changing the
user's browser settings.

Windows/WSL verification, authorized packet transfer, observed human sessions
(OT-048) and human retests (OT-049) remain open. A browser-tab draft is neither
a portable experiment archive nor a promise of recovery after closing the tab.
Reference hiding does not free a registration slot or preserve archive bytes;
independently retained experiment packages remain the durable-storage route.
