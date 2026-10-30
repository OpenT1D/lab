# Installed MMTT sampling integration

## Selected scope before implementation

Base: `120178d1a0aca75b0222f9e37b09424389dd1d4d`, merged roadmap PR 37.
Implement step 2 of the [selected window](../../ROADMAP.md#selected-development-window-first-integrated-laboratory)
under [decision 0085](../decisions/0085-installed-mmtt-sampling.md).
The integration owner implements SDK/shared services and workbench on
`codex/installed-mmtt-sampling`, with separate read-only technical review.
One owner runs the final full check. Agent review is not independent user or
scientific acceptance.

Reuse the native [sampling task](../mmtt-sampling.md) without changing its
scientific files, protocols, units, frozen controls or tolerances. Support all
four supplied synthetic cases through the existing installed Python/CLI and
loopback workbench. Arbitrary GUI intake and editable studies remain subsequent
work. Preserve current MMTT sensitivity and historical/native M4 boundaries.

## Acceptance and counterexamples fixed before outputs

1. Build and noneditably install the SDK in a fresh POSIX CPython 3.12 environment;
   from an unrelated directory, export inputs, validate, freeze, inspect, run,
   retry, reconstruct and relocate sampling through CLI and Python.
2. Compare complete native and adapted parent/child report bytes for the same
   frozen scientific plan. Retain the engineered information-loss reversal and
   constant-input control; do not refreeze expected scientific outcomes.
3. Reject evaluation-containing development evidence, changed development cells,
   changed design/allocation, missing resources and changed source identity.
   Refusal must not publish a freeze or launch an estimator.
4. Preserve incomplete and cancelled attempts, all planned schedules/people/
   assumptions/draws, explicit retry and `allow_failed` semantics. Observe owned
   cleanup and preserve an unrelated process; a forced stop may remain forensic.
5. Refuse resealed missing/swapped child reports, dropped draws and parent/child
   contradictions. Opening/importing never executes archived Python. Rebuild all
   available parent/child reports after original input/project paths are absent.
6. Use the installed GUI and SDK on one project with identical plan/attempt IDs.
   Prepare/freeze/run/verify sampling, inspect its development/evaluation report,
   access unchanged child reports and reopen the relocated project after restart.
   Reject unknown/traversal paths and withdraw tampered nested report copies.
7. Run relevant native sampling reference/workflow, shared service, SDK, GUI and
   frontend checks; inspect an actual installed browser flow. Preserve source
   inventories and legacy controls. One owner runs `uv sync --locked` and
   `uv run --locked python scripts/check.py` on the final integrated revision.

## Implemented boundary

The SDK descriptor is version 3, with strict historical v1/v2 task rosters.
The separate sampling adapter captures original raw files and development bytes,
delegates scientific freezing/masking to the native task and retains trusted
source, runtime-file, ancestry and protocol identities. No scientific source,
baseline, tolerance or OT-059 fixture changes are part of this increment.
The approximately 300-line task adapter leaves the generic store and event schema
unchanged. Existing service dispatch, installed facade, wheel closure and GUI need
bounded registration/report changes; no second estimator or route manager exists.

Passive intake checks parent/schedule/child associations and completed draw
ledgers. Explicit reconstruction performs native arithmetic verification, using
trusted installed sources rather than archived callbacks. The outcome hashes
the parent and every available native child report. The GUI reads those same
copies as inert text, with explicit authenticated child read/download actions.
Tampering with any nested copy withdraws the displayed verification when a
request refuses or polling receives an invalid pointer. Project evidence stays
authoritative; a verified convenience copy is not continuous project monitoring.

## Development evidence

These checks used local Apple Silicon macOS, the locked CPython 3.12 root
environment and noneditable SDK environments. The development tests build the
actual wheel with the explicitly allowed dirty-fixture option. Their source
identity therefore remains distinct from the final clean candidate.

```bash
uv run --locked python -m unittest \
  tests.test_installed_sampling tests.test_sampling_services \
  tests.test_sampling_capabilities tests.test_installed_gui \
  tests.test_installed_gui_frontend tests.test_mmtt_sampling_masking \
  tests.test_mmtt_sampling_estimator tests.test_mmtt_sampling_comparison \
  tests.test_mmtt_sampling_workflow -v
npm --prefix tests/browser test
```

| Check | Observed result and scope |
| --- | --- |
| Targeted Python tests | 43 passed in 92.580 seconds. Includes all four installed controls, CLI/native byte parity for all ten reports, Python cancellation/retry, original-path removal, restarted GUI, shared plan/attempt IDs and native sampling regressions. |
| Installed control plans | Supplied inputs are first checked to retain 128 draws; the four-case CLI regression then explicitly selects 32 draws, preserving 60 slots and 1,920 draw pairs per plan. Service parity retains 128 draws and 7,680 pairs; information-loss retains three engineered evaluation direction reversals. |
| Refusal cases | Evaluation-containing development input; changed cells reimported with a valid new seal; changed original design; resealed missing child, dropped variate and swapped child. Refusal preserves the project head. Fixed-path HTTP, unknown/traversal requests and changed nested copies are checked. |
| Actual installed browser | All five Chromium application tests passed in 53.5 seconds with Node 24.22.1 and pinned Playwright 1.64.1. The added installed case retains 128 draws, reads/downloads a native child, relocates/restarts without the original project and checks tampering withdrawal. The other four checkout flows also pass. No backend responses are substituted. |
| Frontend and visual inspection | The actual JavaScript passes 12 controlled DOM cases. Desktop 1,280-pixel and narrow 390-pixel browser screenshots were inspected; narrow layout has no document-wide horizontal overflow. Native Markdown tables remain scrollable and downloads preserve authoritative bytes. This is not accessibility qualification. |
| Separate read-only review | A separate agent reviewed intake, ancestry, capabilities, process evidence and GUI withdrawal. It reproduced a P2: refused child requests left old verified content visible. The correction withdraws parent/children on read/download refusal or invalid-state polling. Its regression fails on a disposable source copy with that fix removed and passes on the actual source. Review also corrected exported CLI example paths. No unresolved finding remained in that development pass; final committed review is retained separately. |

Initial unprivileged HTTP tests encountered six sandbox socket-bind refusals;
the same targeted family passed with loopback permission. Early browser harness
runs exposed a linked temporary-directory ancestor, an ambiguous project-copy
selector and an incorrectly joined request URL. Correcting those harness defects
led to the successful five-test run. The initial dependency install used system
Node 22 and warned about its engine; actual browser checks used Node 24.22.1.
These failed setup/harness runs supply no product acceptance.

## Final revision and retained receipts

The integration owner runs the final clean-candidate probe and one full root
check after integrating review fixes. Retained files under ignored
`results/installed-mmtt-sampling/` identify the actual revision, dirty state,
wheel bytes, installed descriptor, host, exit statuses and reports:

- `targeted.log`, `browser.log`, `browser-results.json` and `review-dom.json`;
- `withdrawal-negative-control.json`, the intentionally failing counterexample;
- `qualify.py`, `candidate/receipt.json` and the retained candidate wheel;
- `qualification.json`, with four default-128-draw native comparisons and
  moved-reader hashes after original input/project paths are absent;
- `full-check.log` and `final-check.json`, with final source and command outcomes.

The final handoff supplies those receipts' verdicts; this source record does not
substitute a planned check for its result. Reproduce the standard final stages:

```bash
uv sync --locked
uv run --locked python scripts/check.py
```

The full root check includes legacy SDK/shared services, GUI/packet controls and
documentation. Hosted status is read separately from local results; a local pass
does not establish hosted CI. No new native M4 execution or attachment is
qualified by this sampling increment. Existing M4 source/criteria remain intact;
the changed application descriptor requires a fresh application-bound attachment
and relevant native qualification before claiming current-artifact M4 success.
Other OS/application combinations, changed-reader compatibility, editable studies,
human-data applicability, independent usability and biological validity remain
open. The original formative packet is unchanged; no human session is recorded.
