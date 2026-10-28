# OT-031 internal verification

**Status, 3 October 2026:** OT-031 is implemented and internally verified.
The two-source native comparison, outer launcher repeat, preserved failures,
source deadlines, simulator-free reconstruction and locked repository checks
pass the bounded [OT-031 acceptance](roadmap-history-2026-10-28.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources).
The [execution receipt](../../experiments/m4/comparison/execution.json)
binds achieved commands, revisions, source/runtime inventories and hashes.

## Frozen implementation and preserved scope

The [M4-COMPARISON/1 protocol](m4-source-comparison-protocol.md), machine
protocol and [decision 0057](../decisions/0057-m4-source-comparison.md) were
committed at `1fab1e0feabc3f099fb43121fed5eaa1759c8804` before implementation
and new comparison execution. The [execution plan](ot031-execution-plan.md)
records scope and the read-only dependency triage.

The primary run froze clean implementation revision
`945cd033184a7be88fad077ea971b71369988294` on branch
`codex/m4-source-comparison`. It recorded 62 source snapshots. The diff from
planning baseline `4ab905f` contains new comparison code, tests and documents,
without edits to existing numerical packages, source declarations or
numerical project/lock files. The unchanged single-source executor and
native readers provide each complete child archive.

The task fixes fasting and an initial 30 g gastric solid load, a 240-minute
horizon, all 961 saved times at 0.25-minute spacing, the inherited native
profile/initial state, fixed SC schedule, basal/portal ownership and passive
C-peptide inlet. It compares supplied responses under these synthetic
conditions; it does not alter secretion physiology or fit a source.

## Observed primary execution

The native command exited zero and saved
`results/m4-comparison/ot031-primary`:

```console
.venv/bin/python -B -S -m experiments.m4.comparison run \
  --config experiments/m4/comparison/example.json \
  --output results/m4-comparison/ot031-primary
```

The coordinator created one verified BC-008 reference before executing the
ordered Dalla Man and ultradian roster. All 20 reference numerical gates
passed. The reference manifest SHA-256 is
`ff55074dd31d43dec73c1e2ceca25682ebbcb1b93a72db2a645de0aacf8746ad`.
Every child retained that same reference identity.

| Source | Causal primary/repeat cases | Observation primary/repeat cases | Complete source accepted |
| --- | --- | --- | --- |
| Dalla Man adapter | 8/8 completed in each process | 6/6 completed in each process | Yes |
| Ultradian f1 component | 8/8 completed in each process | 6/6 completed in each process | Yes |

Both inherited causal assessments passed, and all 13 observation gates
passed for each complete child. Both children retained zero changed repeat
artifacts. Recorded numerical processes used Python 3.12.13; glucose/insulin
used NumPy 1.26.4 and SciPy 1.13.1, while C-peptide used NumPy 2.2.6 and
SciPy 1.15.3 in its separate locked environment.

| Observer check, maximum across both sources and all tracks | Discrepancy | Frozen limit |
| --- | ---: | ---: |
| Independent oracle concentration | 2.586701e-10 pmol/L | 1e-5 pmol/L |
| Two-solver concentration | 2.585074e-10 pmol/L | 1e-5 pmol/L |
| Finest archived-source coarsening | 0.02985166 pmol/L | 0.05 pmol/L |
| Parent-dose relative difference | 1.627785e-7 | 1e-4 |
| Fresh-process artifact differences | 0 | 0 |

The complete report accepts both sources and all four source/scenario
entries, with one supported pair. Their four saved common BC-008 and host
constant-basal glucose/insulin/C-peptide trajectory objects match exactly.
The Dalla Man candidate has exactly zero contrast against BC-008 for all
three signals at the saved times. The ultradian component has a nonzero
gastric-load contrast. Fasting pairwise differences are small floating-point
residuals rather than a selected or rounded-to-zero outcome.

The following meal-scenario descriptions use frozen roster order,
**Dalla Man minus ultradian**, over every saved time:

| Signal | Signed AUC difference | Signed time-mean difference | Maximum absolute separation |
| --- | ---: | ---: | ---: |
| Glucose | -2709.646 mg min/dL | -11.29019 mg/dL | 20.30728 mg/dL |
| Plasma insulin | 7788.144 pmol min/L | 32.45060 pmol/L | 68.42970 pmol/L |
| Central C-peptide | 65973.79 pmol min/L | 274.8908 pmol/L | 429.4269 pmol/L |

These are modeled trajectory separations, without an accuracy endpoint or
biological ranking. The Dalla Man adapter preserves its 2007 equation
ancestry. The ultradian source preserves its attributed stateless sigmoid,
explicit synthetic basal normalization and host pancreatic route; it is
not the complete ultradian physiology.

## Direct reconstruction and independent agent review

The following standard-library command exited zero without importing
numerical runtimes or executing either supplied source:

```console
.venv/bin/python -B -S -m experiments.m4.comparison reconstruct \
  --archive results/m4-comparison/ot031-primary \
  --output results/m4-comparison/ot031-primary-reconstructed
```

All three reconstructed report files match the primary bytes exactly:

| Artifact | SHA-256 |
| --- | --- |
| `report.json` | `68fbbab66ed3a5ea693e83ac882391a42c75f128ffa58e6db3b28988cc2e406a` |
| `report.md` | `4137825e4750419c00ec114ccbddd996ca7628a958b7cee2aca718b12ba2b01a` |
| `figure.svg` | `b326cfb22ca48a2db44209e1c3e3cb02bf014dacc1f58a2dd17cef065b4fe1ae` |

A separate AI agent performed read-only contract/code and artifact review.
It reconstructed the complete primary archive under `python -B -S`,
inspected raw worker attempts/runtime metadata and independently recomputed
all six scenario/signal pairwise summaries from saved candidate values.
All arithmetic and exact common-control comparisons agreed with the report.
Review findings concerning configuration mutation, reconstruction outputs,
saved-report tamper and early preparation failures were corrected before
the committed primary execution. No blocking primary-evidence finding
remains. This is additional agent review, not independent human execution
or scientific domain review.

No outer coordinator console log file was retained for the primary run or
direct reconstruction. Their achieved commands and exit status are recorded
in the receipt; the supervised reference/source logs remain sealed inside
the native archive.

## Outer repeat, retained failures and checks

The common-entry run and reconstruction exited zero at entry revision
`b3cfaeee989f0ec33ae3bf5e58c3c33004ef7d46`, reusing the same verified reference.
Its freeze records a dirty checkout from concurrent documentation/status and
receipt drafts. The complete comparison/numerical source inventory matched
the clean primary. All 56 causal/observer numerical case files matched byte
for byte, as did the direct pairs, common controls and child scenario
summaries. All three reconstructed report files matched the repeat exactly.
JSON and Markdown retain their different Git provenance; the repeat SVG is
identical to the primary. The receipt preserves both revisions and hashes.

A separate three-source roster ran an invalid negative-rate source first.
It failed in the causal stage; both subsequent valid sources completed. The
report retained all six planned source/scenario entries, accepted four and
kept only the Dalla Man/ultradian pair eligible. Both pairs involving the
invalid source have null metrics. Its 12 planned observer entries remain
unattempted. Overall verification remains failed; neither the native reader
nor common-entry reconstruction hides that failure. Both reconstruction
routes exited zero with `--allow-failed` and reproduced all three files
exactly. The common entry recorded `report_completeness: failed` separately
from successful reader exit.

A separate 30-second whole-source deadline reached the blocking callback,
then terminated its worker. The recorded PID 44953 was absent on follow-up,
and the scoped process check found no retained deadline workers. The same
budget also expired for the subsequent ultradian workflow. Both failures,
all four planned source/scenario entries and null pairwise support remain
visible; zero entries are accepted. Standard-library failed reconstruction
again reproduced all three report files. This probes retention and cleanup,
not successful ultradian acceptance under the short budget.

Meaningful automated tests cover global interruption, later unattempted
sources, cancellation during reference verification, the final completion
boundary, interrupted-but-completed child rejection and separate-session
worker termination/reaping. No separate full native interruption campaign
was executed. Read-only review found no blocking implementation issue.

| Check | Observed result |
| --- | --- |
| Focused comparison core | 24 tests passed |
| Existing and new common-entry checks | 19 tests passed, including four new route tests |
| Inherited isolated observation numerical suite | 5 tests passed |
| `uv sync --locked` | Exit zero |
| `uv run --locked python scripts/check.py` | 906 tests, lint/format, Markdown, YAML, CFF, navigation and Sphinx build passed |
| SVG visual inspection | Six panels, axes/units, legend and source-status text legible |
| Hosted CI | Not executed for this increment |

The full check ran from the entry revision with documentation/evidence
drafts in the working tree. Its preserved log SHA-256 is
`cdcc9f6a9ef254f13fbffffbc540b28bb65c1725bccabcbbbaabd6ce187c7de8`.
The failed/deadline operational receipt SHA-256 is
`8e2bc7e361e3115e7f6983bed0a8b4d4c69af009e142a50fc4505f55b0401763`.
Final evidence/status prose follows that full run; its focused documentation
validation is recorded separately rather than relabeling the earlier check.

## Limits

This is internal synthetic software verification. No human observations,
empirical calibration, biological superiority, clinical predictive quality,
insulin requirement, cell mass or treatment benefit is established.
Independent usability and M4's empirical/biological acceptance remain open.
Archived source-grid checks do not establish convergence below 0.25 minutes.
Hash consistency cannot prove arbitrary callback purity, rights or validity.
Unrelated historical M0–M2 and C1 numerical campaigns were not repeated.
