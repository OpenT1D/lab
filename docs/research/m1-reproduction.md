# M1 implementation and evidence

**Historical scope:** this page records the original milestone and its then-pending work. The separate [M2 evidence record](m2-reproduction.md) tracks the later Cambridge integration and OT-014 evaluation; earlier outputs and acceptance claims remain unchanged.

M1 implements the bounded development workflow from [OT-001](first-experiment.md). The [canonical tutorial](../m1-tutorial.md) owns installation, execution and reconstruction commands. This record distinguishes working software from evidence beyond the implementation.

## Acceptance mapping

| Criterion | Concrete check |
| --- | --- |
| Explicit model, scenario, observation, action, clock and unit boundaries | Immutable contracts, invalid examples and decision 0003; `tests/test_m1_contracts.py` |
| Native physiology and solver preserved | Thin adapter calls the pinned engine; direct native tutorial, adapter and reset histories match exactly and match independently retained M0 output digests |
| Controllers and permitted information | Native formula comparison, allowlisted kwargs, once-only announcements, held-observation age and no native info dictionary passed to the controller |
| Sampling, horizon, true meals and delivered insulin | 960 completed intervals in complete development cases; interval semantics, meal totals and independent rate/amount fixtures |
| Reset and random state | Full 48-hour reset replay for both controllers, changed-seed test, equal native sensor-generation counts through dropout and fresh-process replay |
| Versioned metrics and exclusions | Independently calculable threshold, weighted variance, missingness, partial coverage and seed-then-profile aggregation fixtures |
| Provenance and retained failures | Input/lock/protocol copies, source hashes, effective settings, warnings/logs, native diagnostics and manifest inventory |
| Missing files, nonfinite values, interruption and overwriting | Missing-input, changed-file, invalid-signal and initialization tests; SIGINT/SIGTERM/deadline/SIGKILL subprocess tests; overwrite rejection |
| Report reconstruction without simulation | Standard-library artifact/report path; fresh-process `python -S` reconstruction compared byte for byte |
| Usable demonstration and clean installation | 32 scheduled development runs from an isolated locked environment; dedicated Linux CI workflow and canonical tutorial |

The implementation is delivered in sequential PRs [#9](https://github.com/OpenT1D/OpenT1D/pull/9) (contracts/metrics), [#10](https://github.com/OpenT1D/OpenT1D/pull/10) (adapter/controllers/conditions), [#11](https://github.com/OpenT1D/OpenT1D/pull/11) (artifacts, reconstruction and tutorial). The [Linux implementation run](https://github.com/OpenT1D/OpenT1D/actions/runs/34747531609) passed all four jobs for PR head `1aba0116630925ced31970dfc587ae937a73a37a`: 25 repository tests, 11 M0 Python tests, 10 M1 native tests, 10 LT1 tests, both historical reference workflows, the development feasibility probe and the 32-case M1 demonstration. Its native artifacts record the Actions merge checkout used by that run. Subsequent workflow checkouts explicitly select the exact PR head SHA. The [final PR #11 run](https://github.com/OpenT1D/OpenT1D/actions/runs/34747741677) passed for `ec89c53faff961c5ae1d12c937347431957e85b0`, and the [merged main run](https://github.com/OpenT1D/OpenT1D/actions/runs/34747887919) passed for `fafcd5830113a5cc62c2712a6140b89c7065ed05`. Both complete evidence bundles were preserved before the critical review.

## Observed development behavior

The initial local demonstration recorded 28 complete runs and four native terminal runs. All four terminal cases are `adult#001`, seed 102, PID, at minute 1077; their configurations differ only in scored-day conditions that have not yet begun. A separate native execution and the adapter agree exactly through the stop. The other complete runs have 960 intervals. Native sensor generation continues during condition D; complete sensor coverage is 97.91666666666667% for D's scored day and 100% in A–C. The available duration is 1410 versus 1440 scheduled minutes for D. These are software-observation facts, not clinical exposure estimates.

All terminated cases and excluded pairs remain visible. Primary statistics are undefined when no scored interval exists. Delivered insulin is the modeled native delivery over observed scored intervals, with its observed duration, not prescribed insulin or a filled estimate for an unfinished day. The initial 24-hour period is preserved; no convergence or efficacy claim follows.

The original M0 adolescent reference is a separate fixture. Its exact historical output checks remain unchanged, as do both recorded Linux digests and the LT1 Cambridge reference. M1 adds no tolerance or automatic baseline enrollment. A PID-integral test initially used a different summation order; comparing the actual native sequential addition order removed the last-digit test discrepancy without modifying the controller.

## Evidence scope still open

No evaluation profiles 003–010 have been executed or used for tuning. The 32-case demonstration uses only development profiles and seeds 101–102, without changing the fixed native gains. The complete held-out protocol study is not claimed. Independent researcher execution, separately published numerical-reference agreement, application-specific scientific review, a stronger comparator and external validation remain open. Patient-data access and native-release verification remain pending; no access request has been submitted.

The existing simglucose runtime `setuptools/pkg_resources` limitation remains explicit. There is no general host, second adapter, published package, release, public evidence archive or offsite backup. Local archived evidence establishes integrity and retention, not independent reproduction or biological validity.

## Preserved reproduction evidence

The Mac installation used a new virtual environment and an empty uv package/build cache. Its clean worktree recorded implementation commit `1aba0116630925ced31970dfc587ae937a73a37a`. Both controllers and the terminated PID case replayed exactly in fresh processes. The saved report rebuilt byte for byte with `python -S`, without installed third-party packages. The clean native adolescent reproduction matched the existing Mac historical CSV digest `e4eeaaf4e67d4bfe155413799d5258a417919b4d249361171ab514ece325fb85`.

Retrieved Linux artifacts have matching locked packages, native source hashes, adapter source hashes and effective settings. Their three fresh-process replays and simulator-free reconstruction are exact within Linux. Rebuilding the Linux report on the Mac also produced identical report bytes. Across all 32 Mac/Linux traces, maximum absolute differences were `1.9468870959826745e-11` mg/dL in interval glucose, `1.949729266925715e-11` mg/dL in raw/controller CGM, `3.3584246494910985e-14` U/min in basal commands and `3.497202527569243e-13` U/min in bolus commands. Times, flags, observation ages, true/announced meals and modeled delivered insulin are identical. These are diagnostics, not a pass tolerance or an isolated arithmetic explanation. No baseline or controller setting changed.

The [tracked M1 inventory](../../experiments/m1/evidence-index.json) records verified archive and inventory hashes for the Mac evidence, Linux artifacts/CI log and numerical platform diagnostic. Immutable bundles live outside Git in `results/m1-archive` in the maintained main checkout. They include failed/development attempts as well as the clean reproduction. Verify the maintained store from the repository root:

```sh
uv run --locked python experiments/m0/archive.py --destination results/m1-archive --index experiments/m1/evidence-index.json
```

Use the existing [archive procedure](m0-reproduction.md#local-evidence-archive) for additional selected public synthetic evidence. New clones do not automatically obtain this local store. Preserve both bundle and inventory on transfer, and keep a separate backup before deleting the maintained checkout. No offsite backup or public release is claimed.

## Critical review corrections

The review reproduced gaps in the initial M1 implementation: missing provenance could pass reconstruction; a failed trace could escape its inventory; unsealed trace changes were not identified by report input hashes; a JSON exponent could overflow to infinity; and study completion could contradict individual statuses. The corrected reader validates required metadata and warning records, the supported protocol hash, complete sealed inventories, file stability and exact consumed-input hashes. It retains recoverable partial attempts. The report now exposes study status, observed scored minutes and stop time, displays an unobserved insulin day as undefined, and avoids declaring no sign reversal from fewer than two included profiles. A native diagnostic-export failure cannot mask the simulation error, and nonfinite PID state is rejected even when the returned action is finite. Report schema is now `opent1d.report/2`; numerical metric version, native formulas and M0 baselines are unchanged.

Fresh replay alone could reproduce a consistently wrong M1 trajectory. The added [M1 historical baseline](../../experiments/m1/baseline.json) derives exclusively from verified bundles retained before this review: the original clean Mac demonstration, initial Linux PR #11 demonstration, and final exact-head Linux PR #11 demonstration. The prior merged main collection independently matches the initial Linux collection. The check compares configuration, packages, source fingerprint, lock, protocol, effective settings, row counts and statuses, then requires one entire collection of exact initial/trace digests. It rejects arbitrary mixtures and unknown output without applying a tolerance. Native diagnostic CSV is additionally compared during fresh replay. This is a historical regression reference, not independent scientific validation.

A full scalar comparison of the two previously retained Linux variants found identical interval glucose, delivery, timing, meals, flags and statuses. Differences were confined to initial/raw/controller CGM and commands: maxima `2.842170943040401e-14` mg/dL for initial CGM, `1.1368683772161603e-13` mg/dL for interval raw/controller CGM, `1.1796119636642288e-16` U/min for basal commands and `1.3322676295501878e-15` U/min for bolus commands. Package versions, native source fingerprint and effective settings agree. These measurements explain the scope of the two historical patterns, not their exact arithmetic cause; that cause remains unresolved. No new review-run output was used to construct either reference. Future manifests also record `NPY_DISABLE_CPU_FEATURES` alongside CPU feature flags to aid diagnosis.

The final local review implementation `00bce3bf9d0b10d205a7b6477655df058ab686b1` ran all 32 cases from a clean worktree: 28 completed and four retained native terminations. Every initial/trace digest matched the original Mac collection, and every per-run metric matched the original saved report exactly. Three fresh-process replays and `python -S` report reconstruction passed. Repository checks passed with 40 tests; the native suite passed with 12 tests. The tracked inventory preserves both local review demonstrations and verification/check logs, plus the prior Linux final-head/main bundles and historical diagnostic. All eleven existing M0 archives were reverified unchanged. Linux CI on the final corrective PR commit remains a required merge gate.
