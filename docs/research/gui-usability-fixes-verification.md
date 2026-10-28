# Internal GUI usability fixes — OT-050

The maintainer requested eight fixes from an internal agent walkthrough of
main `6cbc8c90f3a7ca7754da834c2f17d8b54e4104c7`. Work uses the separate
`codex/gui-usability-fixes` branch and managed worktree. This is internal
software verification on macOS 26.5.2 arm64, Python 3.12.13 and uv 0.11.16,
using the Codex in-app browser. It is not an independent human session,
Windows/WSL installation test or evidence of model validity.

The initial implementation is `f96d8a535ce907d79391cd33a91956d13e02b85d`.
`fd6aae60ac72bb7aacf406e07048770893ba5e2e` corrects only an existing polling
test harness to include the real native-status helper. The final implementation,
`83440ccb74e565114e403116ae1a95022577afa2`, additionally scrolls explicitly
selected archive details into view, after a narrow-window retest showed that
focus alone could leave the heading near the viewport's bottom edge.

## Findings and retest

| Finding | Change and observed local result |
| --- | --- |
| F01 | Private participant cards provide a terms glossary in Dutch or English. The Dutch card was opened and its glossary expanded; Source ID and Python code versus matching JSON declaration agree with the GUI explanation. Guide use remains assistance to record. |
| F02 | A real M4 run showed operation state and increasing elapsed computer time in the activity panel and across views. The 240-minute window is explicitly simulated model time. Per-model/condition progress is explicitly unavailable; no percentage or ETA is manufactured. Completion time remained 9m 22s. |
| F03 | The interrupted reference was indexed and explicitly reconstructed. The GUI retains native `interrupted`, incomplete/failed numerical acceptance, verified reconstruction and 0/2 sources, 0/6 cases, 0/1 pair separately. The complete reference retains native `completed` and full acceptance. |
| F04 | During the actual study, the disabled archive saved-analysis action showed the single-operation reason beside it. Its View operation shortcut returned to the running M4 task. After completion the action became available. |
| F05 | Explicit selection focused the archive heading and scrolled to its details. At 390 × 844 the final fix showed the heading inside the viewport, with document/body widths of 390 pixels. Passive polling retained the focused heading; the browser adjusted absolute scroll position when the global operation strip appeared. This was a desktop viewport test, not a real phone or screen-reader assessment. |
| F06 | `INVALID MODEL` produced the specific Source ID format error, reopened Options and focused the invalid input. Restoring `dalla_man` cleared the invalid state and a fresh setup check became Ready. |
| F07 | After archive reconstruction, Start → Insulin secretion showed an idle M4 panel with a correct Results reference. The incorrect “library snapshot below” message was absent. |
| F08 | A real Dutch worksheet export was downloaded, followed by reload and explicit file restore. Its earlier role/outcome values returned and the message stated that no new observations were added. English wording was changed consistently; the live restore exercise used Dutch. |

Private original notes, intermediate retests and browser screenshots remain
outside version control. They include the unsuccessful narrow-window focus-only
attempt. Browser automation stalled substantially at the export/file-chooser
boundary; eventual restored values were verified. Those tool delays are not
reported as application execution performance or human difficulties.

## Native execution and artifact integrity

Explicit locked setup installed the root tooling and both separate native M4
environments. The receipt reports readiness and no model execution during
installation. The new standard study
`job-d63356583c3542c6beb8e8bf3b19b8ed` completed in 562.360859 seconds,
accepting 2/2 sources, all 6/6 source/condition cases and 1/1 pair. The existing
numerical gates and scientific runners were reused without changes. Its
explicit saved-analysis check reconstructed the three native report artifacts.

A separate initialized run, `job-c16179bd2f414fcaa449661cd153d88c`, was
actually cancelled through the GUI. Its retained native report is interrupted,
with zero accepted outcomes and all planned denominators. The earlier completed
study remains available. The manager reports no remaining owned process and no
forced cleanup for the cancelled operation.

The Dutch and English packets bind the initial clean implementation and
reconstruct both retained complete/interrupted references during preparation.
The original archive bytes remain authoritative. Additive native-status metadata
changes presentation; catalogue acceptance and scientific condition digests keep
their existing meaning. Download routes continue to expose native artifacts.

## Repository verification and remaining gates

The root environment was installed with `uv sync --locked`. The corrected
candidate `fd6aae60ac72bb7aacf406e07048770893ba5e2e` passed
`uv run --locked python scripts/check.py`: 1,282 tests in 246.492 seconds,
13 existing C1 runtime skips, lint/format checks and the documentation build
with warnings treated as errors. The first full attempt failed because the
controlled polling harness omitted the new real helper; that failure and its
correction were retained. Focused regressions cover elapsed timestamps,
terminal/invalid timing, busy actions, validation recovery, workflow-scoped
messages, explicit focus/scroll and additive interruption metadata. They are
presentation/boundary checks, not numerical-validity evidence.

Final implementation `83440ccb74e565114e403116ae1a95022577afa2` passed the
same full locked command: 1,282 tests in 246.041 seconds, 13 existing skips and
the warning-as-error documentation build. The new verification page and ToC
also passed their explicit Markdown/YAML checks. Actual file comparisons
matched all nine JSON/Markdown/SVG artifacts: the new study's reconstruction
and both library reference reconstructions. Comparing the first study after
cancellation with its earlier reconstruction also confirms its report bytes
were retained. Private receipts preserve hashes and operation identities.
Status/evidence-only commits do not change the tested GUI, worksheet or
scientific runners.

Actual Windows/WSL host installation and lifecycle acceptance, external handoff
review, OT-048 participant observations and OT-049 human fixes/retests remain
open. The [session guide](../gui-test-session.md) owns preparation and the
[researcher exercise](../gui-researcher-exercise.md) owns human task criteria.

## Main integration, 14 October 2026

[PR #37](https://github.com/OpenT1D/OpenT1D/pull/37) merged into GitHub main at
`7df6594bf4d54238027fbd8418f9de879c03b1de`; local main was fast-forwarded to
the same commit. Its tree matches publication candidate
`6398359cff5484906cbaad70675754ce75df11be`, preserving the tested code.
The maintainer explicitly requested integration while skipping CI/CD. The
merge commit includes `[skip ci]`, which suppresses the configured automatic
`push`/`pull_request` workflows; no push run was recorded for this merge SHA.
Workflow configuration remains unchanged. The preceding hosted PR repository
job had no executed steps: its annotation reported an account payment/spending
restriction. No hosted pass is claimed. The integration-status documentation
follow-up also uses the requested skip marker and is checked locally.
