# Native M5 archive-library verification — OT-044

## Scope and implementation

This 6 October 2026 internal record covers fixed native synthetic M5 analysis
verification, original JSON/Markdown downloads and complete accounting in the
general GUI archive library. [Decision 0064](../decisions/0064-native-m5-archive-library.md)
was written before code; the [library guide](../gui-archive-library.md) remains
canonical. Implementation uses `codex/ot044-m5-archive-library`, based on local
main `ca3bc66` and the reviewed planning commit `cd7bce4`.

The native M5 CLI, scientific source bytes, protocols and locks are unchanged.
The adapter invokes the existing in-place reader, then copies only report bytes
bound to the frozen inventory into owned GUI output. Manager publication checks
that inventory against the frozen request, report digests against the inventory,
and supplier declarations against verified catalogue metadata. Snapshot reads
check the original receipt and both report artifacts. Neither source authenticity
nor training/rights truth is inferred from these integrity checks.

## Actual native and HTTP cases

Four self-authored native cases use the existing real M5 runner and fresh
workers. The interrupted case receives SIGTERM after entering its sleeping
candidate; its sealed archive retains the active interruption and six remaining
unattempted eligible participants. Original bundle directories are removed after
preparation. A candidate-import marker remains absent throughout reconstruction.
Separate native guards reject fitting or worker launches; all four reports still
match their original bytes and saved values.

| Native case | Paired / eligible evaluation | Execution accounting | Native verification |
| --- | --- | --- | --- |
| Complete | 7 / 7 | Complete | Verified complete comparison |
| Controlled failure and repeat disagreement | 5 / 7 | Complete | Verified incomplete comparison |
| Every attempt fails | 0 / 7 | Complete | Verified incomplete comparison; null paired metrics |
| Real SIGTERM interruption | 0 / 7 | Incomplete | Verified incomplete comparison; remaining attempts unattempted |

Actual loopback HTTP indexing and owned native-verification jobs preserve all
32 people and the original source inventories. JSON/Markdown downloads equal
original native bytes; SVG and model-declaration artifact requests are refused.
Four separate missing-report, unsealed, tampered-report and extra-file copies
fail verification and cannot download a verified report. Passive recorded
completion does not override these failures.

After restarting the server on the final code, all four M5 and six retained
M3/M4 entries initially retain only `recorded_verification`. Explicit native
rechecks restore live verification and retain exact original bytes. The six
regression cases include complete M4, complete/failed M3 forecasts and
comparisons, and a sealed cancelled forecast. Native CLI/API artifacts agree,
including the M4 SVG; original archives are unchanged. The existing durable M3
package passes integrity and fresh reconstruction with its explicitly selected
clean historical reader at `7e4ae004cde5c01a2b0f90b0d8c5afdefcd819f1`.

## Actual browser evidence

Playwright drives actual registration, metadata refresh, native verification and
JSON/Markdown downloads for each M5 case. All 32 roster rows and seven evaluation
prediction rows remain in every view. Full eligible baseline and paired support
are shown separately; zero support retains null metrics and complete execution
never becomes a successful comparison. Declaration text is self-attested and
hash-bound; M5 exposes no SVG. Eight browser downloads match original bytes.

Actual unchanged report rechecks preserve an open roster detail and keyboard
focus in all four cases. M4 figure and M3 forecast selection still work. A
480-pixel viewport preserves all rows without document-level horizontal overflow.
Desktop/mobile screenshots were inspected. There are no JavaScript page errors
in these final browser cases. A separate verified test snapshot is deliberately
changed: the real browser hides the report, clears displayed declarations and
disables both downloads while the original native archive stays intact.

## Review and focused checks

Two implementation agents own backend and frontend respectively and perform
combined cross-review. Frontend review independently reproduces two integrity
findings: a coherently changed declaration receipt and a post-copy target
substitution. Both are corrected and covered by regression tests. Additional
backend review binds coherent target/receipt changes to the frozen source
inventory and checks both artifacts on every M5 snapshot read. Four independent
boundary regressions pass; neither agent reports an unresolved blocking finding.
These are internal technical reviews, not independent researcher acceptance.

The final focused M5 backend/actual HTTP run passes 18 tests in 12.866 seconds,
including cancellation, deadline cleanup and shared operation ownership. The
prior combined M5/M3 run passes 32 tests in 31.132 seconds before the final
narrow M5 strengthening; full repository execution below covers the final state.
Five focused frontend tests pass, including 105 controlled Node cases covering
native dispatch, accounting, malformed input, stale responses and downloads.
Focused lint, Markdown and diff-whitespace checks pass.

**Full repository check:** `uv sync --locked` and
`uv run --locked python scripts/check.py` pass on feature candidate
`fe1e1f8e21f3084ba197d965ca95739dad96707c`. The suite contains 1264 tests and completes in
229.117 seconds with 13 existing C1 tests skipped because their separately
locked PyTorch runtime is absent; no M5 or Node frontend check is skipped.
Lint/formatting, Markdown/YAML/CFF, explicit navigation and the warning-as-error
Sphinx build pass. The documentation-only acceptance follow-up receives separate
Markdown/navigation/build checks; implementation bytes remain those of this
fully checked candidate.

## Main integration and cleanup

At the user's request on 6 October 2026, primary local main was fast-forwarded
from `ca3bc665321bba2d7a3d7cf7107d52b63d861851` to
`537680a7e630cf52c478ebd4e0275bfabb47184b` without conflict or implementation changes.
`uv sync --locked` and `uv run --locked python scripts/check.py` pass again from
the primary checkout: 1264 tests in 295.039 seconds, with the same 13
existing C1 PyTorch-runtime skips, plus the warning-as-error documentation build.
`main-sync.log` and `main-check.log` retain this separate result. The final
integration-status prose and evidence index receive separate documentation checks.

Before cleanup, 575 cached GUI files (4,514,637 bytes) were copied byte-exactly
into primary `results/ot044-verification/gui-workspace-snapshot/`; the empty
manager lock is excluded. This is forensic cached evidence, not a GUI workspace
restore, trusted saved reader or process-ownership grant. Its preservation
receipt binds every copied byte, including intentionally failed/tampered cases.

The managed implementation worktree is archived with recoverable Git state;
the merged `codex/ot044-m5-archive-library` branch is removed. Afterwards, all
four original native M5 archives still reconstruct using the primary main reader,
with unchanged JSON/Markdown digests and no candidate import. All 14 original
receipt digests, the 575 cached files and 345 protected source/lock files agree.
`gui-workspace-preservation.json` and `post-cleanup-verification.json` retain
these checks. GitHub publication and hosted verification remain open.

## Retained evidence and limits

Raw proof is retained outside disposable worktrees in the primary checkout's
ignored `results/ot044-verification/` store. Key receipts are
`native-original-inventories.json`, `native-cli-parity.json`,
`native-fit-worker-guards.json`, `actual-http-m5-cases.json`,
`actual-http-regressions.json`, `actual-http-refusals.json`,
`final-http-rechecks.json`, `durable-regression.json`, `browser-acceptance.json`,
`browser-snapshot-withdrawal.log`, `preservation.json`, `full-sync.log` and
`full-check.log`. The tracked `experiments/gui/m5_library_verification.json`
binds the exact checked candidate and receipt digests. Executed preparation/acceptance scripts
are retained there too. Browser screenshots and downloads live in primary
`output/playwright/ot044-*`; session tokens are not saved in the evidence.

The final preservation receipt confirms all 345 protected native M3/M4/M5
and locked-environment files, all four M5 originals and six existing M3/M4
original archives remain unchanged. This is internal macOS software
verification on invented tasks. Independent use, human prognosis, biological
validity, treatment effect, public release and hosted verification remain open.
M5 execution/export controls and new durable-package support are not added.
