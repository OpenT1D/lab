# OT-032/033/034/037 local implementation verification

**Status:** bounded implementation and internal verification completed,
3 October 2026. This record separates numerical study evidence from campaign
administration, catalogue reconstruction and environment readiness. The
[roadmap](../../ROADMAP.md#functional-development-after-ot-031),
[decision 0058](../decisions/0058-configurable-study-and-local-research-tools.md)
and [execution plan](ot032-ot037-execution-plan.md) own scope. Main remains at
baseline `d9991c115e795c2977177349805619df15981598`; no merge, push or release
is part of this goal.

The [machine receipt](../../experiments/integration/ot032-ot037-verification.json)
binds actual commands, exits, source/report/manifest hashes and preserved
development failures. Large numerical archives and research inputs remain
outside version control. The retained local evidence root is
`/private/tmp/opent1d-functional-lab-acceptance-20261003`.

## Grouped branches and implementation

| Managed worktree / branch | Implemented work |
| --- | --- |
| `m4-configurable-study/OpenT1D` / `codex/m4-configurable-study` | OT-032 native study, reports, reader and numerical tests |
| `local-campaigns/OpenT1D` / `codex/local-campaigns` | OT-033 frozen campaign lifecycle, process cleanup and separate prepared CI job |
| `researcher-tools/OpenT1D` / `codex/researcher-tools` | OT-034 catalogue and OT-037 declared locked setup |
| `functional-lab-plan/OpenT1D` / `codex/functional-lab-plan` | Protocol/plan freeze, shared seventh route, reviewed integration and evidence |

Three agents implemented disjoint packages and cross-reviewed provenance,
failure accounting, numerical conditions and process ownership. Root committed
and merged each reviewed increment in the integration worktree. Historical
numerical modules and root/native/observer locks remain unchanged.

Native acceptance used clean revision
`160c4e0bf34042ec66a30630878fc09d311a50a0`. Catalogue acceptance used
`a25ecf62a1b24ab7de5e1185c5c36d2dab8f5f6c`. Later tools-only commits do not
belong to the study's 86-file inventory or campaign's 98-file inventory;
those frozen source hashes were independently checked unchanged. Each archive
retains its actual checkout provenance.

## Configurable M4 study

The seventh common-entry task, `m4-study`, supports an ordered subset of the
predeclared 0/15/30 gram initial solid gastric loads and two-to-eight declared
one-state secretion sources. It preserves adult#001, existing basal/SC
conventions, 240 minutes and 961 output points. CHO remains zero during the run;
there is no meal-event timing API, new physiology, fitting or winner selection.
See the [canonical guide](../m4-configurable-study.md) and
[M4-STUDY/2](m4-configurable-study-protocol.md).

The full primary matrix passed **2/2 sources, 6/6 source/load cells and 1/1
source pair**. Both native and observer primary/repeat processes completed.
Independent inspection confirmed 86 numerical/observer check values within
frozen limits, six identical shared-control cases and nine independently
recomputed pair metric bundles. All fresh-process repeat difference lists
were empty. Selected observed maxima are:

| Criterion | Maximum | Frozen limit |
| --- | ---: | ---: |
| Source solver error, pmol/(kg min) | 6.65275422795375e-6 | 1e-5 |
| Glucose solver error, mg/dL | 1.0918897161160474e-6 | 0.01 |
| Insulin solver error, pmol/L | 3.513786232154104e-5 | 0.01 |
| Glucose mass error, mg/kg | 1.6677215767145524e-7 | 1e-5 |
| C-peptide oracle concentration error, pmol/L | 2.5867009975877235e-10 | 1e-5 |

The independent historical check passed **88/88 parsed cases, 3,118,394 numeric
values and maximum difference 0.0** for unchanged tight/reference settings at
0/30 grams: 32 causal child files, 24 observer cases, 24 common-reference cases,
four padded native cases and four native-class diagnostics. Source/declaration
bytes match. Historical raw JSON differs in key ordering, observer schema and
eight `gain` representations (`1.0` versus `1`); historical file-byte equality
is not claimed. The changed coarse setting has its own numerical gates.

The nonfinite source failed first; both subsequent valid sources still completed.
The archive retains all three sources, nine cells and three planned pairs;
two sources, six cells and one pair are accepted while the whole study stays
failed. In the separate 15-second whole-source deadline case, a callback recorded
its PID and ignored SIGTERM. The native owner used SIGKILL, reaped the worker and
confirmed its group absent after 25.0879 seconds including the bounded ten-second
cleanup grace. Both other deliberately insufficient-budget failures remain
visible. No source in that case is accepted.

The primary, nonfinite and deadline archives all reconstruct with
`.venv/bin/python -B -S -m experiments.workflows reconstruct m4-study`;
failed archives use `--allow-failed`. All nine JSON/Markdown/SVG outputs are
byte-identical to their corresponding new archives and retain their statuses.
Three meaningful native numerical tests passed. The 21 focused study tests
include strict stage/command ledgers, launch failures and relocation regressions.

## Frozen local campaigns

The [campaign guide](../local-campaigns.md) describes the initial `m4-study`
campaign contract. Actual acceptance used two cells (fasting and 15 grams),
two repetitions, a 1,800-second outer study budget and unchanged native
600-second stage/3,600-second whole-source budgets. Every child generated and
verified its own historical reference and scenario-specific controls.

After the first slot completed, SIGTERM was sent only to the campaign
coordinator while the second native source worker was active. Cleanup cascaded
through the native owner; no scoped processes remained. The sealed first
session retained one accepted slot, one interrupted slot and two unattempted
slots. Failed reconstruction without opt-in refused before creating output;
`--allow-failed` reconstructed exact JSON/Markdown.

Explicit resume skipped the first accepted slot and attempted only the other
three. The final campaign passed **4/4 slots and 8/8 source/load cases**, with
**five retained attempts**, including the interrupted attempt and linked retry.
Three immutable sessions scheduled **4, 3 and 0** attempts. No-op resume retained
accepted archive identities; all prior manifests/reports stayed unchanged.
Final stdlib reconstruction matched JSON/Markdown exactly. Resuming copied
campaigns with changed frozen input or accepted output refused before a fourth
session. All 98 frozen implementation/protocol/lock hashes still matched.

The actual initial run exited 1, resume and no-op resume exited 0, and both
tamper resumes exited 2. Thirteen focused tests additionally cover lifecycle
and real resistant-process cleanup. The campaign supervisor's bounded
20-second cleanup margin exceeds the native owner's ten seconds.

## Catalogue and setup

The [catalogue](../experiment-catalogue.md) indexed and authoritatively
reconstructed **11/11 archives across all seven registered routes**: ten complete
experiments and the explicitly incomplete failed-source study. All original
full inventories remained unchanged. Task/protocol/model/status/tag filters
worked. Actual identical-condition fasting repeats were eligible after fresh
native-reader revalidation; different loads, different tasks, unverified entries
and failed experiments were ineligible with explicit reasons.

The compatibility signature binds saved Python/platform, numerical runtimes,
native scientific identity/parameters, source/condition snapshots, declarations
and exact M4 shared curves. Installation locations remain provenance. Diagnostic
logs stay in full inventories and do not become scientific conditions. Legacy
M4-secretion/M5 archives lacking saved platform evidence remain readable and
reconstructable, with explicit incomplete repeat coverage and ineligible reasons.

Actual copied-archive tamper tests rejected changed bytes after indexing, a
rewritten M5 metric/hash claim, and a forged verified/complete receipt with a
rewritten invalid M3 trace. The last comparison reran the native reader. Indexing
alone establishes metadata reading, not verified or complete evidence.

[Task-directed setup](../task-setup.md) correctly reported ready root tooling
and missing native/observer environments in the managed integration checkout.
Explicit installation used existing `uv sync --locked` projects. Independent
full offline lock checks then matched all three environments: CPython 3.12.13;
native simglucose 0.2.11/NumPy 1.26.4/SciPy 1.13.1; observer NumPy 2.2.6/SciPy
1.15.3. Locks, Python selectors and uv identities stayed unchanged. Current
version-3 setup plan/check receipts bind the final tools; no reinstall was needed.
Reconstruction-only setup correctly requires root alone. Readiness is not model
validity or numerical acceptance.

## Preserved development findings

- M4-STUDY/1's predeclared 15-gram development probe failed the new coarse
  source-rate gate (`1.350865261140477e-5 > 1e-5`). M4-STUDY/2 halves only
  coarse maximum step from 0.5 to 0.25 minutes. The failed protocol/probe,
  unchanged thresholds and explicit revision history remain preserved.
- Native runs at `64adc1692e51aa9b34c92a0eea5595bcd9c80c29` failed before
  callbacks because full native identities included old installation paths.
  The repair excludes only the values of two retained location fields; all
  other identity fields, parameters and runtimes remain exact. Current worker
  full identities and fresh-process repeats remain bound. Failed archives and
  the early interrupted development campaign remain unmodified.
- A first parity review rejected eight integer/float `gain` encodings despite
  zero numeric difference. Its receipt remains alongside the successful exact
  finite-number comparison; booleans remain distinct.
- Catalogue review added exact saved runtime/native condition coverage. Its
  first actual repeat comparison then exposed diagnostic log paths in a source
  selector. The failed receipt remains; the corrected selector and regression
  precede the successful fresh catalogue acceptance.

## Repository checks and limits

The final machine receipt records the actual result of `uv sync --locked` and
`uv run --locked python scripts/check.py`: Ruff, format, Markdown, YAML, citation
metadata, navigation, repository tests and strict documentation build. The
separate prepared CI job covers setup, numerical study, campaign reuse and
catalogue verification; the prepared protection policy lists 14 matching jobs.
No hosted run or server-side policy change is claimed.

This is internal verification on macOS 26.5.2 arm64. Other clean systems, Windows,
cross-hardware bitwise identity and independent researcher usability remain
unverified. Known synthetic fixtures are not blind scientific evaluation.
Callback purity and rights are declarations; artifact readers verify saved
evidence without independently reproducing arbitrary supplied algorithms.
Biological validity, authorized human-data evaluation, treatment benefit, a
general model API and a public release remain open. OT-035 GUI and OT-036 new
model types remain outside this completed implementation goal.
