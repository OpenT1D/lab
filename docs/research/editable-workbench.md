# Editable installed workbench

## Selection before implementation

Base: `cc79c42bdce729030b0749fa8d9ed4e126f07a1c`, merged sampling PR 38.
Implement [roadmap step 3](../../ROADMAP.md#selected-development-window-first-integrated-laboratory)
under [decision 0086](../decisions/0086-editable-workbench-drafts.md), on
`codex/editable-study-workbench`. One integration owner writes and runs the final
full repository check; a separate read-only agent reviews the diff.

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

Implementation and actual verification are pending. Retain receipts under ignored
`results/editable-workbench/`. Report actual failures, source/dirty state, commands,
outcomes, skips and final review. Local checks are distinct from hosted results;
agent/browser rehearsals supply no intended-user or biological acceptance.
