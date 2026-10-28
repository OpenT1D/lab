# Reliable archive-library verification — OT-043

## Scope and candidate

This 5 October 2026 internal record covers the schema-aware catalogue correction
and fixed native M3 report readers in the general GUI archive library.
[Decision 0063](../decisions/0063-reliable-archive-library.md) fixes the boundaries;
the [library guide](../gui-archive-library.md) remains canonical.

Three implementation agents used separate catalogue, adapter and presentation
worktrees/branches; integration used `codex/archive-library-integration` from
`76fb99925d59e8252f8958b634365bd913bc80f3`. A fourth agent independently reviewed
the combined code. The implementation commits are `cdb67a3`, `5112c41` and
`e3f66f8`; integration additionally binds library journal task labels, withdraws
M4 snapshots after figure failures and preserves open M3 rosters on rechecks.
At the user's request on 5 October 2026, local main was fast-forwarded from the
baseline to the verified candidate `4e5cf48464af3fc479acdd7fd636718f90112914`,
without conflict or source changes. GitHub publication and hosted checks remain
open.

## Recorded claims and original evidence

The retained OT-041 M4 native study previously produced 34 catalogue path
warnings. Its reference seal declares paths relative to `reference/`, rather
than the archive root. The explicit supported-schema dispatch checks all 732
recorded claims: 463 study, 235 historical and 34 reference claims match. The
467 original files remain unchanged. There is no archive rewrite or guessed
path fallback.

Actual temporary-copy mutations retain changed/missing-file mismatches, invalid
unsafe claims and unsupported unknown schemas. Mixed statuses preserve each
manifest's diagnostics. These checks cover supported recorded claims; they do
not establish all-byte completeness, source authenticity or scientific validity.

The broader preservation receipt binds 623 pre-existing tracked native
experiment, model, root tooling/lock and M3/M4/M5 research-document files.
All seven retained original archive inventories, including 641 files and their
directories, match the before-operation inventory. Before main integration,
the primary checkout was clean at the baseline revision; the subsequent
fast-forward preserves those protected source and archive bytes. No predictor, simulator or human-data
analysis is executed by this increment's saved-evidence reconstruction.

## Actual native and GUI acceptance

The local loopback service indexes and verifies these retained native archives.
Every case also reconstructs through its fixed native CLI. The GUI JSON/Markdown
bytes equal both the CLI output and available original native reports; M4's SVG
is also byte-identical. Failed coverage retains a successfully verified native
analysis with explicitly incomplete results.

| Task | Retained case | Native completeness | Report parity |
| --- | --- | --- | --- |
| Maintained M4 | OT-041 native study | Complete | JSON, Markdown, SVG exact |
| M3 forecast | Full CLI forecast | Complete | JSON, Markdown exact |
| M3 forecast | Genuine predictor RuntimeError | Incomplete | JSON, Markdown exact |
| M3 comparison | Full CLI comparison | Complete | JSON, Markdown exact |
| M3 comparison | Failed candidate with retained complete child | Incomplete | JSON, Markdown exact |
| M3 forecast | Genuine cancelled sealed forecast | Incomplete | JSON, Markdown exact |

The cancelled forecast retains both planned participants: the first is
interrupted after 12/859 attempted origins; the second is `not_attempted` with
0/859 attempted. All 1718 planned origins remain in the denominator. The browser
shows native errors, null metrics and common support without recalculating or
ranking unmatched subsets. Actual browser registration, native verification and
JSON/Markdown downloads exercise the full comparison, failed forecast and
cancelled forecast.
Desktop and 390-pixel mobile captures retain the roster, separate statuses and
bounded downloads; the mobile page has no horizontal document overflow.
Participant details remain open across the periodic verification recheck.

Five full/failed retained M3 cases in the adapter receipt have unavailable
original preparation/predictor paths. The cancelled original retains its
preparation, so input unavailability is not claimed for that case. A separate
genuinely interrupted comparison regression removes all original reports and
preparation: the fixed model-free native reader retains its interrupted and
unattempted roster. When original M3 JSON is absent, passive metadata remains
unavailable while explicit sealed reconstruction can succeed into fresh output.
The actual missing-report copy never gains a report in its source directory.

## Boundaries, regression and review

Actual HTTP checks refuse an unsealed original, M3 SVG, unsafe relative paths,
changed derived snapshots and a source change after indexing. A failed recheck
withdraws the former snapshot and its downloads. One active operation blocks
concurrent mutation; actual index cancellation terminates cleanly without forced
cleanup or remaining owned processes. Request-bound M3 library task labels
survive restart; persisted verification becomes recorded evidence and no saved
PID gains ownership. The actual loopback-server restart retains all 31 saved job IDs, tasks and
terminal states, demotes live verification and permits explicit fresh native M3
verification. These restart boundaries also have actual HTTP regressions.

Existing M4 fields, trajectory figure and JSON/Markdown/SVG readers remain
available; all three actual browser downloads equal the original native bytes.
Browser registration also verifies an existing M3 durable package's saved bytes,
with reconstruction explicitly not requested by that registration. Existing durable-package integrity verification and reconstruction
succeed using the explicitly selected clean historical checkout at
`7e4ae004cde5c01a2b0f90b0d8c5afdefcd819f1`; package data never selects executable
saved code. The exact reader stays clean and at its recorded revision.

The independent combined review ran 87 focused tests and found no unresolved
blocking code issue. Its M4 figure-error finding was corrected and reproduced:
report and download controls withdraw with the failed artifact. Integration's
controlled frontend suite now covers 56 cases, including unchanged-roster
retention, task dispatch, asynchronous stale responses and malformed bounds.

`uv sync --locked` and `uv run --locked python scripts/check.py` pass on the
combined integration candidate: 1246 tests in 236.124 seconds, lint/formatting,
Markdown/YAML/CFF checks, explicit navigation and a warning-as-error Sphinx
build. The final documentation status update receives separate documentation
checks; scientific code is unchanged after the full run.

After the fast-forward, `uv sync --locked` and the full locked repository check
also pass from the primary main checkout: 1246 tests in 237.838 seconds
and the warning-as-error documentation build. `main-sync.log` and `main-check.log`
retain this separate integration result. The final integration-status prose
receives its own Markdown/navigation/build check before commit.

## Retained evidence and limitations

Raw receipts and native reconstruction outputs are retained outside disposable
worktrees in the primary checkout's ignored
`results/archive-library-verification/`. Key files are
`catalogue-claim-acceptance.json`, `actual-cli-gui-cases.json`,
`actual-boundaries.json`, `m3-adapter-retained.json`, `durable-regression.json`,
`preservation.json`, `actual-restart.json`, `browser-downloads.json`,
`actual-gui-durable-registration.json`, `review.json` and their actual test/CLI
logs. `full-check.log` retains the complete locked repository result. Browser captures
and downloaded native reports are retained in `output/playwright/ot043-*`.
Session tokens, credentials and private health records are not recorded.

This is internal macOS software verification. Independent intended-researcher
use, human evaluation, biological validity and hosted checks remain separate;
Actions minutes remain exhausted. Synthetic completeness does not measure
prediction quality in people. Larger native reports exceed the bounded GUI
presentation and remain inspectable with the native CLI. No new model, scientific
convention, dependency, release or empirical result is claimed.
