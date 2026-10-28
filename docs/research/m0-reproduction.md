# M0 native reproduction record

**Historical scope:** this page records the original milestone and its then-pending work. The separate [M2 evidence record](m2-reproduction.md) tracks the later Cambridge integration and OT-014 evaluation; earlier outputs and acceptance claims remain unchanged.

Status, 13 September 2026: simglucose's documented custom scenario runs locally with exact reset and fresh-process replay. The [first Linux reference run](https://github.com/OpenT1D/OpenT1D/actions/runs/34721218099) also passed with exact replay within Linux. LT1 native execution and Linux verification are recorded below. No controller comparison, clinical evaluation or independent researcher reproduction is claimed.

## simglucose commands

Run from the repository root. Choose new output directories for every attempt; existing directories are rejected. Downloaded dependencies, outputs and logs remain outside Git.

```sh
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose python -m unittest discover -s experiments/m0/simglucose -v
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/run.py --output results/m0/simglucose-1
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/run.py --output results/m0/simglucose-2
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/run.py --compare 'results/m0/simglucose-1/first/adolescent#001.csv' 'results/m0/simglucose-2/first/adolescent#001.csv'
```

Each invocation executes the native scenario and a native-reset replay. The configuration selects the original adolescent profile, Dexcom seed 1, Insulet and BBController defaults. Harness differences from the tutorial are selecting its custom segment, fixing the start to 2024-07-20 at midnight, disabling animation, separating output paths and observing native reset/step returns to checkpoint completed history. The native runner still owns the loop; the recording wrappers return each native value unchanged. No engine, controller or solver behavior is patched.

The [model card](models/simglucose.md) documents signal meanings and asset rights. The run manifest contains configuration, Python/platform and package versions, OpenT1D revision and dirty-state flag, harness/config/lock hashes, installed source and CSV hashes, solver settings, output summaries and completion status. Failed runs preserve traceback and the last fully completed native interval in the affected phase directory. SIGTERM, SIGINT and the default 300-second wall-clock deadline produce an `interrupted` manifest; `--timeout-seconds` changes that deadline. `first/recording.json` and `reset/recording.json` describe each phase. Development cases have their own directories. There is no shared partial file that can accidentally refer to a previous case. Threshold events are distinct from numerical execution failures.

## Observed local baseline

Two processes and their reset runs produced identical numerical histories on this Mac with Python 3.12.13. This is a newly recorded baseline for the pinned documented scenario, not agreement with a separately proven paper figure.

| Quantity | Observed value |
| --- | --- |
| State rows / action intervals | 481 / 480 |
| Horizon / outer interval | 1,440 min / 3 min |
| Total scenario carbohydrate | 220 g |
| Integrated modeled delivered insulin | 38.397325 U |
| Final logged subcutaneous glucose | 93.05999876753249 mg/dL |
| Logged glucose minimum / maximum | 93.05999876753249 / 159.13827424061583 mg/dL |
| Native threshold events | 0 |
| Native CSV SHA-256 | `e4eeaaf4e67d4bfe155413799d5258a417919b4d249361171ab514ece325fb85` |

No time-in-range claim is derived from thresholding interval means. A clinical interpretation of this short synthetic scenario is outside its purpose.

## Automated checks and evidence retention

The Linux CI job installs the separate locked environment, runs recorder tests and executes two processes with reset replay and a historical-baseline check. Artifacts preserve manifests, raw synthetic histories and logs even on failure, with 14-day retention. Download and archive required evidence before expiry; CI artifact retention is transport, not the research archive. The original Mac/Linux evidence has now been copied out of temporary directories into the maintained main checkout’s ignored `results/m0-archive` store, with verified bundles indexed in [evidence-index.json](../../experiments/m0/evidence-index.json). See the archive procedure below. The tracked report preserves summary results and source provenance without vendoring upstream inputs. A local archive is not an offsite backup or a public release.

Recorder tests use labeled synthetic traces to check cadence, amount integration, missing files, nonfinite values, structural endpoint cells, incorrect meals, overwrite rejection and failure/partial-output recording. Exact numeric equality is required within an environment. The retrieved Linux artifact has the same input configuration, lock, dependency versions, installed upstream source/asset hashes and solver settings as the Mac run. Both use dopri5 with upstream defaults rtol `1e-6` and atol `1e-12`. Cross-platform output is not bitwise identical: maximum absolute BG/CGM difference is `4.376943252282217e-12` mg/dL; CHO and insulin are identical. The difference is consistent with platform floating-point execution, but its precise operation-level cause has not been isolated. No tolerance was adjusted to declare equality. Linux CSV SHA-256 is `b1e8a16237aeb2574a0503484d6b530d02671bfb7380c5ad105efb9448e06ad9`.

Use `--compare <mac.csv> <linux.csv> --report-differences` to reproduce the per-column diagnostic report. This mode reports differences without applying a pass tolerance; the default comparison still fails on any numerical mismatch. These observed differences do not define a general future adapter tolerance.

Root checks remain `uv sync --locked` and `uv run --locked python scripts/check.py`. They lint the experiment harness but do not import its dependencies. The separate CI job and reference commands provide numerical execution checks.

## LT1 Cambridge commands

The isolated toolchain uses Node 22.22.2, TypeScript 5.7.3 and ts-node 10.9.2. These match the upstream compiler/loader versions selected for this probe. The imported Cambridge/MPC graph uses relative native modules and no external runtime package; the frontend and unselected oref0 controller are not installed. This is a headless reference probe, not an installation or test of the full LT1 application.

```sh
npm --prefix experiments/m0/lt1 ci --ignore-scripts --no-audit --no-fund
node experiments/m0/lt1/setup.mjs
npm --prefix experiments/m0/lt1 test
npm --prefix experiments/m0/lt1 run reference -- --output ../../../results/m0/lt1-1
npm --prefix experiments/m0/lt1 run reference -- --output ../../../results/m0/lt1-2
npm --prefix experiments/m0/lt1 run reference -- --compare ../../../results/m0/lt1-1/first/native.jsonl ../../../results/m0/lt1-2/first/native.jsonl
```

The source is fetched at its pinned revision into ignored `results/m0/lt1-upstream`. Existing source modifications, extra files (including ignored files) or a different revision are rejected. Native Cambridge, MPC, IdealCGM, StaticInsulinPump and the original IFAC reference configuration are imported without edits. Native callbacks save JSONL records incrementally; each record preserves state, input, output, sensor samples, controller output, announcements and diagnostics. Nonfinite numeric diagnostic values are tagged rather than silently converted to null. Nonfinite state/action/observation signals fail the recorder, retaining the partial trace.

The recorder invokes `runSimulation` twice on the same modules; that native method resets them and its solver. A second invocation of the command tests a new process. The native reference contains persistent announcement entries; a persistent entry is not a new meal event at every step. The reduced CSV contains the same time, plasma-glucose and delivered-infusion fields as the upstream helper. The manifest records effective parameters, source hashes, compiler lock, Node/platform and default native seeds. Source-only parameter inventories in run artifacts are not committed to Git.

## Observed Cambridge baseline

On this Mac, two processes and their native-reset runs were exactly equal, including the recorded controller diagnostics. The source and its compiler were unchanged during these runs. The [Linux Cambridge reference run](https://github.com/OpenT1D/OpenT1D/actions/runs/34721740861) also passed. Its full recorded native results are exactly equal to the Mac results, including controller diagnostics, with matching configuration, source hashes, lock and toolchain. The shared JSONL SHA-256 is `8427a2a0b0b8cc68aa82c40ef486373c017291157231e9f76720c4957e3f3641`. No cross-platform tolerance was used.

| Quantity | Observed value |
| --- | --- |
| State rows / elapsed horizon | 1,441 / 1,440 min |
| Outer step / IdealCGM samples | 1 min / every 5 min |
| Meal input | 40 g over 15 min at 08:00; announced at midnight |
| Integrated modeled delivered insulin | 11.875 U |
| Final plasma glucose | 109.97956300883534 mg/dL |
| Plasma glucose minimum / maximum | 100.47751422017063 / 124.91784824923832 mg/dL |

This is the native Cambridge/MPC scenario, not the simglucose meal protocol or an equivalent patient. Floating-point summation yields 39.99999999999999 g for the 40 g meal and 11.87499999999977 U for the reported total; the event rates are checked directly. The pump's reported delivered rate differs from its controller command because the native pump quantizes delivery. The final action row describes a potential next interval and is excluded from integration over the completed horizon.

The Node recorder tests cover synthetic rate integration, missing/truncated output, invalid timestamps or announcements, nonfinite serialization, retained partial failures, overwrite prevention and diagnostic comparison without a pass tolerance. Linux artifacts and CI console logs preserve evidence and loader warnings; native loader deprecation warnings do not establish a numerical defect. No separate published figure or independent researcher execution has been established.

## Consequences for integration and reuse

Both probes now have a small native execution surface; neither requires a new differential-equation implementation. simglucose supplies interval-averaged subcutaneous glucose with three-minute control, while this LT1 reference supplies plasma glucose and five-minute sensor/controller updates. The fixed native scenarios therefore test two execution paths, not controller rankings across matched populations.

The APS TestBed [source assessment](m0-assessment.md#reuse-versus-extension) remains relevant: controller comparison and faults already exist there. These probes show that the selected two engines can be exercised without adopting its older patched execution stack or source-rewriting fault injector. OpenT1D's demonstrated work so far adds a common evidence discipline, explicit signal semantics and retained failures. The accepted decision below explains why M1 will first use a thin simglucose adapter rather than extend LT1 as the host. A stable adapter API and common controller-information boundary still require M1 implementation; these recorders do not provide them. The updated decision includes a requirement-by-requirement LT1/APS comparison and accepts only the first Python adapter, not a permanent general host.

## Development feasibility and M0 closure

On 13 September 2026, the fixed native BB and upstream-example PID settings were exercised for 48 hours on **development profiles only**, using sensor seed 101. Both days' five meals were explicitly encoded. No evaluation profiles, announcement perturbations, tuning or controller-ranking analysis were run.

```sh
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/development.py --output results/m0/development
```

| Development profile | Native controller | Rows / completed | Logged glucose at 24 h / 48 h (mg/dL) | Native extreme stop flags |
| --- | --- | --- | --- | --- |
| adult#001 | Basal-bolus | 961 / yes | 90.99109106848485 / 104.54567004480688 | 0 |
| adult#001 | PID | 961 / yes | 191.72280566086172 / 46.354391271160885 | 0 |
| adult#002 | Basal-bolus | 961 / yes | 91.23891656595154 / 89.00768138773373 | 0 |
| adult#002 | PID | 961 / yes | 95.39134776200841 / 78.37171732333229 | 0 |

These are native interval-mean subcutaneous glucose values. They establish executable settings and expose initialization drift and weak reference behavior, not treatment performance. In particular, zero extreme flags does not mean no low glucose. The PID settings were not optimized after seeing these results, and a 24-hour initialization period is not claimed to reach a periodic steady state. The full traces, manifest, parameters, hashes and logs remain in the ignored result directory; the same bounded probe is included in CI. The [Linux development run](https://github.com/OpenT1D/OpenT1D/actions/runs/34722762371) completed all four cases with 961 rows each and zero native extreme flags. Retrieved traces use matching settings, lock and package versions. Across these four Mac/Linux pairs, the largest BG/CGM difference is `1.4637180356658064e-11` mg/dL; timestamps, CHO and delivered insulin are identical. This is a diagnostic comparison without a pass tolerance, not a claim of bitwise equality or an isolated explanation of the floating-point difference.

The [version 1.0 protocol](first-experiment.md) now specifies the first-engine population, timing, information, controller settings, metrics and failure conventions. [Decision 0002](../decisions/0002-m0-reference-first.md) accepts the software integration boundary. The [data card](m0-data-fit.md) completes the public-documentation feasibility assessment. Together these satisfy M0's selected synthetic research workflow; M1 must still implement and verify the adapter, information filters, metric calculations and report reconstruction before evaluating profiles 003–010.

Still open beyond this M0 scope: independent researcher reproduction, agreement with separately identified published numerical results, authorized human-data access and native-release verification, independent parameter-origin verification before redistribution, and application-specific scientific validation. No criterion is fulfilled merely by CI success. The known legacy dependency advisory is tracked in the [maintainer guide](../maintenance.md#m0-runtime-compatibility).

## Build-tool compatibility correction

The M0 closure work changed the isolated build constraint from setuptools 69.5.1 to 84.0.0 after the source-distribution advisory was reported. An empty-cache install rebuilt gym and simglucose successfully. Native simglucose output remained exactly equal to the earlier Mac baseline, including its CSV hash. Runtime setuptools stays at 80.9.0 because the unchanged upstream code imports `pkg_resources`; the patched repository-tooling environment no longer provides that API. This build-tool change does not remediate or conceal the legacy runtime package's advisory. No source distributions are produced or published from that runtime.

## Review corrections and historical baseline policy

The M0 self-review identified permissive LT1 signal checks, lost interrupted Python histories, stale development partial-output attribution and missing historical regression checks. The corrected tests cover each counterexample. LT1 now requires every pinned Cambridge state and controller signal with finite numeric values; empty sensor groups remain valid only between native five-minute sample instants. Invalid callback data are retained before rejection.

The Python recorder atomically replaces `progress.csv` after native reset and every fully completed step. Exceptions and catchable interruption copy that valid prefix to the phase's `partial.csv`. A hard kill cannot execute cleanup: the last atomically completed checkpoint remains, and `started` means unfinished, never success. A machine or storage failure may also lose buffered writes; local checkpoints are not a power-loss guarantee. Ignore `.tmp` files left by a killed write. A status file may lag its checkpoint by one write; inspect the CSV to determine its actual completed prefix. This is tested with SIGTERM, SIGINT, a deadline and SIGKILL. Filesystem loss and permanent process failure cannot be made recoverable by an in-process recorder alone.

Normal reference execution now compares against the tracked [Python baseline](../../experiments/m0/simglucose/baseline.json) and [LT1 baseline](../../experiments/m0/lt1/baseline.json), in addition to comparing fresh/reset runs. Checks include the exact output digest and the recorded runtime, lock, source and configuration context. Python baselines distinguish macOS arm64 and Linux x86_64; LT1 has recorded macOS arm64 and Linux x64 entries. Unknown environments and changed outputs fail rather than enrolling themselves as new baselines. The test suites include repeatable but deliberately wrong trajectories which pass replay equality and fail this historical check.

The baseline entries come from the already recorded M0 outputs, not from post-fix outputs. The newer Linux Python reference in PR #7 and the pre-fix main run has CSV SHA-256 `36b5a4e2fd1deec879504c5145bf035b1c22136d3627d809acf2ffc33d9b00ba`. Against the older PR #5 Linux CSV listed above, BG, CHO and insulin are exactly equal; the largest CGM difference is `2.842170943040401e-14` mg/dL and the largest risk-column difference is `3.375077994860476e-14`. Its source hashes are unchanged and it uses the updated build lock. The first [review-fix Linux run](https://github.com/OpenT1D/OpenT1D/actions/runs/34745493274) reproduced the older PR #5 digest exactly, with matching packages, lock, configuration, source hashes, solver, Python build and reported Linux platform relative to the newer reference. It failed because the first version of the baseline guard recognized only the newer digest. Both full historical digests are now named explicitly; each existed before these fixes and is archived. Each run must match one of those exact full outputs, and its fresh-process/reset comparisons must still be exactly equal. No numerical tolerance is used and new outputs are not automatically enrolled. The arithmetic cause of the last-digit CGM/risk difference remains unisolated. [NumPy dispatches numerical kernels based on CPU capabilities](https://numpy.org/doc/1.26/reference/simd/how-it-works.html); this is a plausible explanation, not a demonstrated diagnosis of these historical machines. New manifests therefore also record detected and disabled NumPy CPU features.

A baseline change requires retained old/new outputs, matching or explicitly changed input/environment provenance, a diagnostic numerical diff, an explanation of the change and review before replacing the digest. Do not update digests just because CI fails. Existing baselines establish recorded software behavior, not external scientific correctness. The current Mac probes remain bitwise equal after adding checkpoints and validation. LT1 console capture uses explicit Bash pipefail so a failed native command cannot be hidden by a successful log-writing process.

The [review regression CI run](https://github.com/OpenT1D/OpenT1D/actions/runs/34745762999) passed all 32 tests (11 repository/archive, 11 Python and 10 Node), both native historical-baseline checks with fresh-process/reset replay, and all four development cases. Retrieved manifests and outputs were checked before archiving the complete artifacts and CI log. Together with the local counterexample tests, this closes the listed recording and baseline findings; it does not establish independent scientific validation.

## Local evidence archive

The [tracked index](../../experiments/m0/evidence-index.json) identifies each retained bundle, its origin and archive/inventory hashes. Bundles live outside Git, under `results/m0-archive` in the maintained main checkout, not under a temporary worktree. This preserves the cited original evidence after CI expiry. New clones do not automatically acquire these local files; transferring a bundle must also transfer its inventory and match the tracked index. Back up this store with the project's normal local-data backup before deleting or moving the checkout.

Create a bundle only from an explicitly selected public synthetic run or downloaded M0 artifact directory. Keep source downloads, environments and private data out of it. Use a new destination for each bundle; existing destinations and symlink-containing sources are rejected. From the repository root:

```sh
uv run --locked python experiments/m0/archive.py --source results/m0/simglucose-1 \
  --destination results/m0-archive/NEW_UNIQUE_BUNDLE
uv run --locked python experiments/m0/archive.py \
  --destination results/m0-archive/NEW_UNIQUE_BUNDLE
```

The second command verifies the archive digest and every file against `archive.json` without extracting content. Verify the entire maintained store against the tracked index with `uv run --locked python experiments/m0/archive.py --destination results/m0-archive --index experiments/m0/evidence-index.json`. This also checks the inventory hashes, so replacing an archive and its local inventory cannot silently change the indexed evidence. Add new bundle metadata to the index only after verification. Archive integrity tests reject corruption and overwrite attempts. No release, shared cloud archive or offsite replication is claimed.
