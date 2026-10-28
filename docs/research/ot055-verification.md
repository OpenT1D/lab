# OT-055 synthetic sampling verification and handoff

Date: 18 October 2026. Scope: bounded internal software verification. The
[sampling guide](../mmtt-sampling.md) is canonical; the separate
[empirical preparation](mmtt-sampling-empirical-plan.md) retains the unresolved
human-data, kinetics, margin, precision and oversight requirements.

## Implementation and source boundary

Task 2 reuses OT-054's source-pinned fixed-kinetic estimator, initializer,
keyed measurement perturbations, native plan/runner and native reader. It
removes raw observations before numerical parsing and independently freezes
each reduced child. Only the required-time admission list differs between
schedule settings; no full-fit state, nuisance parameter or omitted analyte
value enters a reduced fit. Decision 0069 records this shared boundary.

The six planning files were integrated once in `3ec9e07`. OT-053's 15 dossier
digests were verified against `cd10cb0`/`4f38f01`. All 14 OT-054 core digests
were checked against `23e1bc1`, integrated as `59d9d5b`. The later handoff/GUI
commits `a8a85fe`, `f4feb22`, `accb434`, `3e13a73` and `099f01a` were integrated
as `59d8d1d`, `53f5245`, `4f232ce`, `a1b2db0` and `3ce4e7b`. All 32 original
GUI identities were checked against `3e13a73` before Task 2 extension.

Backend commit `328a363` adds the small shared required-time admission extension,
without changing estimator arithmetic or uncertainty. It also adds raw masking,
sealed parent/child plans, failure-aware comparisons and reconstruction. GUI
administration uses a shared observation-task lifecycle and fixed registered
CLI commands. It contains no second estimator. The machine-readable
`experiments/mmtt_sampling/verification.json` binds the subsequent integration
code and checked file identities. Original predecessor verification records
describe their own snapshots, not the modified integration.

## Checks and local execution

- Forty-two focused sampling tests passed: four manufactured numerical vectors
  across full/subset schedules, exact units and AUC, negative-rate preservation,
  matched retained-time perturbations, raw and estimator-level omitted-value
  poisoning, missing requested times, development-only selection, archive
  relocation, forged-statistic/attempt rejection and actual SIGTERM handling.
- Five Task 2 GUI HTTP/process tests cover four complete/incomplete controls,
  byte-identical downloads and reconstruction, the explicit archive library,
  changed input/selection/task refusals, restart and owned cancellation. The
  invalid-full-analyte regression confirms valid reduced children still execute.
  Task 1's original HTTP/frontend regression checks also pass after factoring
  the shared lifecycle.
- `uv sync --locked` passed. The first integrated
  `uv run --locked python scripts/check.py` passed **1,366 tests, 13 existing
  skips**. The next integrated run passed **1,367 tests, 13 existing skips**,
  linters/navigation and strict Sphinx build, including the invalid-full GUI
  regression. A browser-discovered archive-view dispatch mismatch was then fixed
  in `55c5519`; five frontend tests (including 108 archive checks) and the actual
  incomplete library report pass. The final acceptance check on `55c5519` passed
  **1,367 tests, 13 existing skips** in 291.213 seconds,
  with all repository checks and the strict documentation build.
- A real local browser prepared, froze, ran and reconstructed all four supplied
  cases. The general archive library also verifies and displays an incomplete
  sampling report with the correct native schema. The information-loss report's 324 displayed metric cells matched native
  JSON. Three downloaded JSON reports matched their original archive bytes.
  The paired table retains all 45 planned comparisons and native conditional
  intervals. No human observations or researcher sessions were used.
- Browser cancellation of a 1,024-draw run retained 60 required variant pairs:
  45 known unattempted pairs and 15 unavailable atomic pairs, distinguishing
  unavailable work from zero or known unattempted work. Its sealed interrupted
  archive reconstructed successfully. The HTTP test separately interrupts during
  the native analysis phase and verifies shared operation exclusion and cleanup.
- Complete and incomplete casepack archives were relocated and reconstructed
  using Python `-B -E -s -S` from a separate trusted source export of `328a363`.
  Both JSON and Markdown matched byte for byte. The source inputs, original
  folder paths, simulation packages and archived Python execution were unnecessary.

The 13 existing skips require the separate C1 PyTorch runtime. Tests, browser
checks and documentation builds establish only their declared software behavior;
they do not establish model validity, human interval coverage or researcher value.

## Reproduce the software case packet

Use a fresh ignored results directory in the matching trusted checkout:

```bash
uv sync --locked
uv run --locked python scripts/prepare_mmtt_sampling_cases.py \
  --output results/ot055-casepack
```

The script executes the public CLI for development export/import, full input
export, study freeze, common-entry check/run and reconstruction for every case.
It requires the expected complete/incomplete exit codes and byte-equal JSON/MD,
then records original report/manifest hashes in `casepack.json`. Every case has
two development people, three declared evaluation people, two visits per person,
four schedules and three required variants. With the default 128 draws, the
planned denominators are 60 variant pairs, 120 visit points and 7,680 draw pairs.
These engineered evaluation identities are known controls, not blinded evidence.

| Case | Expected software observation | Complete variant pairs / planned | Failed visit points / planned |
| --- | --- | --- | --- |
| `constant` | Constant concentrations preserve each point total across all subsets; conditional intervals can still differ | 60 / 60 | 0 / 120 |
| `information-loss` | Full/five/four nominal paired change is +913.9611396248856 pmol; three times gives −302.9012517216406 pmol, with three evaluation direction reversals | 60 / 60 | 0 / 120 |
| `incomplete` | Low observations and a censored visit remain explicit; no favorable-draw-only interval or missing-equals-zero conclusion | 36 / 60 | 12 / 120 |
| `steep-response` | Negative-rate boundary failures stay visible alongside retained full/subset observations | 27 / 60 | 33 / 120 |

The local verified packet is `results/ot055-casepack-final`; its original hashes
are bound in the verification JSON. Do not commit synthetic output archives.
Additional automated checks cover a missing requested 60-minute value, an invalid
full reference with valid raw subsets, changed glucose exposure and an attempted
evaluation-based schedule choice. The same protocol's numerical-reference file
contains independent constant, low constant, linear-rise and linear-fall controls;
the globally linear controls alone cannot demonstrate preservation of a peak.

## OT-056 and empirical boundaries

An independent exercise can use the four cases to ask for correct endpoint units,
visit pairing, absolute/bias/precision interpretation, paired direction changes,
all failed denominators and the distinction between concentration AUC and amount.
Freeze the exercise and strong-comparator rubric before actual sessions. Do not
score known agent walkthroughs as independent users or infer clinical sample
size from the proposed product-user count.

No schedule is declared clinically equivalent or approved for fewer blood draws.
Human execution is refused by this synthetic contract. Authorized dense paired
observations, applicable kinetics and assay rules, participant-disjoint allocation,
domain-chosen margins and precision, a low-value rule and responsible oversight
remain prerequisites for a separate empirical protocol. A negative finding that
no reduced schedule meets its criteria remains valid. Biological applicability,
empirical acceptance, prospective sampling and independent comparative usability
remain open; they are not synthetic implementation acceptance claims.
