# Editable installed workbench

## Selection before implementation

Base: `cc79c42bdce729030b0749fa8d9ed4e126f07a1c`, merged sampling PR 38.
Implement [roadmap step 3](../../ROADMAP.md#selected-development-window-first-integrated-laboratory)
under [decision 0086](../decisions/0086-editable-workbench-drafts.md), on
`codex/editable-study-workbench`. One integration owner writes and runs the final
full repository check; a separate read-only agent reviews the diff.

Before final verification, integrate main through `5d4afe5` (documentation search
completion checks). Preserve both additive changelog entries; no sampling or
workbench numerical implementation is changed by that integration.

## Acceptance and counterexamples

1. Import researcher-chosen declared synthetic metadata/CSV, edit shared
   assumptions and sampling schedules through the installed workbench, retaining
   explicit development evidence and native validation. Selected M4 configuration
   editing retains its fixed source/runtime boundary.
2. Save incomplete/invalid concepts, restart or reload, inspect saved revisions
   and restore a prior revision as a new revision. Reject stale cross-tab saves,
   corrupt blobs/heads and unsupported file/task names; retain original evidence.
   Uncommitted writes must not silently replace the last committed revision.
3. Any changed scientific inputs or parent clear validation. Freeze refuses
   stale/unvalidated state, revalidates exact saved bytes and creates an immutable
   SDK plan. Untouched uploads retain exact UTF-8 BOM/CRLF bytes.
4. Derive from an existing frozen plan with original inputs and a recorded parent.
   New settings produce a new plan; original plans, attempts and reports remain
   byte-identical. GUI and Python/CLI expose the same plan and report identities.
5. Preserve missing/censored visits and all planned slots, explicit incomplete
   verification, cancellation/shutdown, fixed authenticated downloads, runtime
   selection and full-project relocation. Copy GUI concepts explicitly; do not
   claim CLI relocation transfers workspace convenience state.
6. Exercise actual noneditable SDK and browser flows, keyboard/focus, narrow/zoom
   layout, correction and conflict paths. Use immutable native scientific files
   and relevant numerical/workflow regressions. Run `uv sync --locked` and one
   final `uv run --locked python scripts/check.py` on the integrated revision.

## Evidence

### Implemented boundary

The installed SDK adds passive `inspect_inputs`, explicit `prepare_development`
and original-input `Project.export_inputs` methods with CLI counterparts. They
reuse native capture, import, schedule-time and observation readers. No numerical
file, protocol, ancestry file, frozen reference, tolerance or OT-059 fixture changes.
The M4 route retains its existing selected sources and explicit attachment policy;
this increment checks metadata/derivation and refusal, not new native M4 execution.

GUI concepts have immutable UTF-8 blobs/revisions, an atomically published head,
explicit saved-revision recovery and optimistic revision checks. Invalid raw text
remains correctable. Validation binds content, parent, revision and application;
freeze revalidates through the SDK and preserves a new immutable parent-linked
plan. GUI project copying retains concept history with validation cleared.
Workspace concepts remain distinct from SDK project evidence and CLI relocation.

Authenticated state polling omits source files and large validation bodies.
Terminal job detail expands the exact immutable revision on demand, rather than
retaining repeated raw file copies in every job. Both polling and late results
preserve explicit choices and newer local edits. File reads have per-field
sequence guards. Untouched BOM/CRLF and large raw integer seeds retain exact bytes;
the frozen-plan display also preserves native integer text without browser rounding.

### Development checks and review

Local checks use Apple Silicon macOS, the locked root CPython 3.12 environment,
actual noneditable SDK environments and Node 24.22.1/Playwright 1.64.1 for Chromium.
Development wheels explicitly admit dirty fixtures; clean final evidence is
identified separately in retained receipts. The integration owner ran:

```bash
uv run --locked python -m unittest \
  tests.test_workbench_drafts tests.test_installed_gui \
  tests.test_installed_gui_frontend tests.test_workbench_installed \
  tests.test_installed_sampling.InstalledSampling.test_gui_sampling_child_reports_restart_and_relocation \
  tests.test_installed_sdk.InstalledSDK.test_thin_gui_shares_ledger_parent_ids_and_two_file_mmtt_reader \
  tests.test_ci_baseline -v
npm --prefix tests/browser test
```

- The targeted Python family passed all 36 cases in 122.805 seconds. It includes
  actual installed own intake, invalid correction/restart, exact BOM/CRLF hashes,
  derived plans preserving originals, complete/incomplete support, direct native
  sampling report parity, copied concept histories, selected M4 configuration
  export and unselected-source refusal. No native setup is performed.
- All eight Chromium application flows passed in 120.293 seconds, without
  intercepted responses. Three new installed flows exercise own uploads,
  autosave focus, correction, restart, conflict/fork/restore, raw large seeds,
  parent derivation, development separation and schedule editing. Existing
  lifecycle/download/relocation/cancellation flows retain their own scope.
- Controlled DOM cases cover late validation/save/upload results, explicit
  picker selection, parent-preserving conflict copies, exact seeds, unsafe UTF-8
  refusal, invalid structured values and existing readiness/report regressions.
  The final wrapper has 22 cases, including exact frozen-plan integer display
  and explicit unsaved status after a refused autosave.
- Actual screenshots were inspected at desktop/narrow widths and 200-percent
  text size; keyboard tab focus and accessible names are checked in Chromium.
  These are bounded observations, not actual screen-reader or complete WCAG
  qualification, installation usability or independent intended-user evidence.

A separate read-only agent reproduced six defects during development: oversized
diagnostics made a concept unreadable; late validation replaced edits; conflict
copies lost the parent; polling reset the picker; older file reads replaced newer
choices; and a shadowed loop variable replaced display names with filenames.
All were corrected with regression coverage. Its independent repeats confirmed
bounded diagnostics, retained edits/recovery, preserved selection, latest-upload
ordering, parent retention and the unchanged scientific/OT-059 inventory.
The final committed review is retained with the handoff.

A subsequent critical review independently reproduced two further defects.
Revalidating a frozen concept cleared its frozen-plan anchor, so a later edit
could lose its immediate parent. Validation now retains that anchor on both
success and refusal; editing still creates an unfrozen child. A delayed saved
concept open/reload could replace edits entered after the request. A separate
edit counter now rejects that late replacement, including file selections whose
asynchronous read has not finished. Recovery bytes and newer controls remain
intact. Controller and actual installed HTTP checks cover revalidation/derivation;
the controlled DOM wrapper now has 24 cases. Both new DOM regressions fail on
the previous JavaScript for the expected replacement/state assertions and pass
after correction. An actual installed Chromium case delays an authentic SDK
response to verify the reload race without substituting its content.

The late-validation regression also fails on a disposable JavaScript copy with
that fix removed, for the expected lost-edit assertion. A 320,108-byte CSV with
20,000 invalid rows previously generated a 2,129,502-byte diagnostic result;
the bounded result retains all error counts and the correctable raw input.
Oversized annotations now refuse before head publication. The initial sampling
test incorrectly expected censored input to be invalid at import; correcting
that expectation preserves native semantics. Early browser harness failures
were ambiguous selectors or reading a plan ID before freeze finished. They
supply no acceptance until corrected runs pass.

### Cold hosted budget and final receipts

Actual uncached hosted Root checks before this increment took 19 minutes
38 seconds on source `12770dc` and 19 minutes 19 seconds on `40c064e`, under a
twenty-minute limit. The second run spent 18 minutes 59 seconds in the repository
check/build step. This increment adds an actual installed-workbench test class
and root regressions, so only that job's limit becomes 25 minutes. Caching stays
off; tools, job roster, public gate, native guards and scientific criteria remain
unchanged. The matching CI policy test passes. A local duration is not the hosted
benchmark; the retained job metadata supplies the baseline.

The integration owner runs one final full repository check on the clean integrated
revision, a clean wheel rehearsal and the final browser family. Actual revision,
dirty state, environment, wheel hash, outcomes and skips are retained under ignored
`results/editable-workbench/`, including:

- `targeted.log`, browser logs/results and `review-dom.json`;
- `validation-negative-control.json` and development failure logs;
- `hosted-root-baseline.json`, final review and CI snapshots;
- `qualify.py`, retained `candidate/receipt.json` and wheel, qualification results
  and synthetic project snapshots;
- `full-check.log` and `final-check.json` for the final command outcomes.

The handoff states those receipts' actual verdicts. This source record does not
replace a pending final check with a result. The standard commands remain:

```bash
uv sync --locked
uv run --locked python scripts/check.py
```

Local and hosted evidence remain distinct. Other-host/release qualification,
current-artifact native M4 execution, changed-reader compatibility, cross-plan
comparisons, independent users and biological validity are separate open gates.
The original formative packet and packaged application allowlists are unchanged.
