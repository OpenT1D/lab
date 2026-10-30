# 0086 — Recoverable editable studies over the installed SDK

Date: 30 October 2026. Status: implemented; final integrated verification recorded separately.

## Decision

Implement roadmap step 3 over the installed project services. Admit bounded
user-supplied synthetic MMTT metadata/CSV/settings and sampling design plus an
explicit separate development package/CSV. Seal development inputs through the
existing trusted importer; preserve development-only roster checks before CSV
interpretation and never select schedules using evaluation output. The installed
M4 route accepts only its existing configuration and reviewed source pair.

Keep editable concepts in the GUI workspace, separately from the authoritative
SDK project. Use immutable content blobs and revision records with an atomic
head, optimistic revision checks and explicit recovery of prior saved revisions.
Preserve invalid text for correction. Uncommitted/orphan writes remain diagnostics;
they cannot silently replace the committed head. State polling carries summaries;
authenticated fixed routes load one bounded concept on demand.

Validation is convenience state bound to exact saved content, revision, parent
and current application. Scientific edits invalidate it. Freeze re-reads and
revalidates through the SDK, retaining its immutable parent and original bytes.
Export original frozen inputs through the SDK to derive an editable concept;
never read arbitrary project paths or overwrite a freeze. Preserve raw UTF-8
bytes for untouched files, including CSV BOM and line endings.

Expose structured assumption controls and raw source editors with explicit
save/validation/freeze states, autosave status, conflict recovery and keyboard
operation. General SDK methods own intake diagnostics, development sealing and
frozen-input export; the GUI owns no estimator or second experiment ledger.
GUI relocation copies concepts to the new workspace handle with validation
cleared. A CLI project copy carries authoritative freezes/attempts; workspace
concepts are not implied to be portable to another workspace.

## Preserved boundaries and acceptance

Do not modify native numerical files, protocols, frozen references, tolerance
criteria, OT-059 fixtures, runtime permission or the original formative packet.
Incomplete observations remain explicit diagnostics, not a reduced denominator
or a mandatory complete-study intake rule. No archived Python is executed.

The [task record](../research/editable-workbench.md) owns success/counterexample
cases, installed browser/SDK parity, separate review and final verification.
Root tooling stays separate from native runtimes. Independent use, accessibility
qualification, biological evidence and the next comparison increment stay open.
