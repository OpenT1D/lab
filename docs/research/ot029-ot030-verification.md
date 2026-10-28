# OT-029 and OT-030 internal verification

**Status:** implemented and internally verified on 2 October 2026, on branch
`codex/researcher-tools-plan`. This record closes the bounded local software
packages in the [roadmap](roadmap-history-2026-10-28.md#post-integration-internal-work-packages).
The [execution metadata](../../experiments/integration/ot029_ot030.json)
binds exact commands, source revisions, runtime locks and local report hashes.

## Implemented behavior

The [local entry](../local-workflow-entry.md) discovers five supported routes,
checks declarations and installed metadata, explicitly runs each task and
reconstructs its native archive. Passive checks neither import candidates nor
open M3 observation contents. Execution selects installed locked environments,
clears foreign selectors and prevents implicit sync or Python downloads.
Child exit status stays separate from report completeness. Signals are
forwarded to native owners; SIGHUP maps to SIGTERM for their cleanup.

The [M3 comparison](../m3-candidate-comparison.md) freezes all candidate
source/settings identities, one synthetic roster/origin schedule and equal
worker budgets before observation access. Its primary all-candidate support
requires completed workers, at least 288 shared scored origins and at least
24 hours of origin span. It weights people equally, retains failures and
returns null metrics with reasons when no one contributes. The separate
[M3-COMPARISON/1 protocol](m3-candidate-comparison-protocol.md) was committed at
`510094a2637d17d078a27df05b825803f12a37c3` before new assessment execution.

## Observed execution and source revisions

The four-route acceptance ran on clean
`994ad0bec6a58d31ec357acbe7402dab6cadaa26`. It recorded 21 commands, four
complete native runs, two explicit M3 failure/deadline probes and six native
reconstructions after removing its own supplied synthetic inputs.

| Route | Observed result |
| --- | --- |
| P1 | All four A–D conditions completed; native reports reconstructed with archived controller action replay. |
| M3 single predictor | Both planned people contributed. Failure and timeout probes each retained two people, zero contributors and 859 planned origins per person: 12 validated attempted rows plus 847 not attempted. |
| M4 configured source | Six observation cases completed in both primary and repeat. JSON, Markdown and SVG reconstructed byte for byte. The workflow generated its checked BC-008 prerequisite. |
| M5 | All 32 invented people retained; seven eligible held-out people had paired predictions. The native reader verified the existing report bytes without model execution or refitting. |

All six child archives remained byte for byte unchanged. The acceptance
receipt SHA-256 is
`5654b54241bf085da5d089df02710c17cc95e2a9e6864ca9936c1d148d16dff8`.

A separate implementation-review agent then added a narrow comparison-reader guard against
an interrupted coordinator attempt without global interruption. It also
clarified the harness's overly broad historical-campaign wording; no
four-route execution/check logic changed. The original receipt stays
unchanged and retains its actual source revision. Seventeen focused
comparison tests and eight harness tests passed after those corrections.

The final M3 comparison acceptance ran on clean
`a5e2c42d6be2d8afd3ce338c11a28875a24c6032`. It reused the unchanged, separately
verified synthetic development-only Ridge donor; its older native child
archive still reconstructed under the current unchanged researcher sources.
The trend and Ridge examples each matched 1,550 reference predictions.
Both planned people contributed 758 shared scored origins each. Fresh-process
traces and common analysis matched exactly. Adding a failing third candidate
retained the complete roster and produced null primary metrics, rather than
dropping that candidate. All three parent JSON/Markdown report pairs
reconstructed byte for byte after the original predictor/input paths were
removed; all child bytes remained unchanged.

## Checks and preservation

`uv sync --locked` and `uv run --locked python scripts/check.py` passed on
clean `994ad0bec6a58d31ec357acbe7402dab6cadaa26`: **866 tests**, Ruff,
Markdown, YAML, citation/navigation checks and the documentation build.
The same command then passed all 866 tests and built the final evidence/status
documents on source revision `a5e2c42d6be2d8afd3ce338c11a28875a24c6032`
with those documentation updates in the working tree. Both check logs are
bound in the execution metadata.

Focused checks cover independent arithmetic, equal-person weighting and
partial cohorts; count/span boundary conjunction; long failed prefixes and
empty support; frozen/source/config mismatches after rewritten inventories;
no successful origin abstention; local deadlines versus global cancellation;
real SIGTERM/SIGHUP cleanup; and final-child cancellation boundaries.

Every pre-existing experiment file from local main `e77c9d7`, all runtime
locks and historical researcher protocols remain unchanged. New entry,
comparison and acceptance packages live outside the historical source
inventories. The new comparison protocol bytes remain fixed since their
freeze. The primary local main checkout was not modified.

The existing locked beta-cell CI job now executes configured M4 through the
entry, reconstructs all three report formats and preserves its evidence.
**Hosted CI has not been run for this branch.** Local verification does not
establish a hosted runner result.

## Reproduce and interpret the checks

Install the root tooling and existing numerical projects explicitly:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
uv sync --locked --project experiments/m3/runtime
uv run --locked python scripts/check.py
.venv/bin/python -B -S -m experiments.workflow_acceptance \
  --output /tmp/opent1d-workflow-acceptance-new
```

The harness requires a clean checkout and a fresh output path. Follow the
[M3 comparison guide](../m3-candidate-comparison.md) for its declared fixture
and reconstruction commands. Its default Ridge settings are invented; the
native donor verification remains the separate existing M3 route. Exact
commands and the retained final comparison verification script are recorded
in the execution metadata. Local artifacts are under the recorded `/tmp`
paths and are not versioned; new runs have their own provenance and hashes.

Implementation and software review were AI-assisted. These are self-run
synthetic software checks. They do not complete independent
P1 usability, M2 human reproduction, M3 human predictive assessment, M4
biological assessment or M5 human prognosis/treatment evidence. Reconstruction
checks arbitrary M3/M5 candidate outputs and their analysis without
independently reproducing the supplied algorithm. Hashes establish saved
consistency, not authenticated execution or scientific validity. No unrelated
historical M0–M2 or C1 campaigns were repeated for this increment.
