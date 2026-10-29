<a id="iv-001--numerieke-verificatie-en-gevoeligheid"></a>

# IV-001 — Numerical verification and sensitivity

Translated from Dutch on 29 October 2026. Historical findings, language-policy
statements and audit results below describe the original report, not a new review.

<a id="status-en-afbakening"></a>

## Status and scope

The local numerical campaign was executed according to [IV-001](internal-verification-protocol.md), separately from OT-001/OT-014. The [canonical guide](../internal-verification.md) describes installation, execution and reconstruction. This report supports internal software and numerical verification; independent human reproduction and biological validation are not claimed. The selected mutation campaign and two full robustness matrices were also executed.

The pilot ran on clean commit `b35232e`; the full local matrix on clean commit `adf7cbc`. The saved manifests contain full revisions, source hashes and lock hashes. The full matrix was then repeated on clean commit `903f72d`: all eighty traces are exactly equal. Review subsequently corrected process status for failed campaigns, campaign cancellation and checks for missing runtime settings. These corrections change no numerical calculation; targeted fault injections check them. The final PR check executes the full matrix again on Linux.

<a id="vooraf-vastgelegde-grenzen"></a>

## Prespecified limits

The pilot used only adult#001/101/basal-bolus and Cambridge/PID: two configurations, three solver settings and separate feedback/replay, giving twelve complete runs. The native tolerances are simglucose dopri5 `rtol=1e-6`, `atol=1e-12` and Cambridge SolverRK1_2 relative error target `0.001`. Both are refined by factors of 10 and 100; the native outer cadence stays the same. MPC retains its own Euler prediction solver.

The largest native-to-finest pilot deviation was 0.00003310 mg/dL for simglucose and 0.08648801 mg/dL for Cambridge/PID. Mean absolute deviations were 0.000001575 and 0.01534833 mg/dL, respectively. The maximum exposure shift was one Cambridge interval: 0.06944445 percentage points. Modelled insulin delivery remained equal.

Before the full matrix, the limits were recorded in `experiments/verification/criteria.json` and a separate freeze artifact with pilot input hashes, source hashes and the full schedule:

| Signal | Technical limit | Interpretation |
| --- | --- | --- |
| Maximum absolute glucose deviation | 0.1 mg/dL | One tenth of a mg/dL as a numerical reporting scale |
| Duration-weighted mean absolute deviation | 0.02 mg/dL | Detection of sustained small drift |
| Maximum absolute exposure shift | 0.25 percentage points | 3.6 minutes; approximately one simglucose interval |
| Absolute difference in daily insulin total | 0.01 U | Small change through quantised feedback; replay additionally requires exact delivery |

These are development criteria, not clinical accuracy limits. They were not adjusted after inspection of the full matrix. Historical baselines remain unchanged.

<a id="volledige-lokale-matrix"></a>

## Full local matrix

Ten development configurations, each with six numerical runs and two additional initialisation histories, yield eighty planned runs. Of these, 71 are complete and nine stopped natively. All 64 simglucose runs and sixteen Cambridge runs remain in the inventory; there is no cohort or compartment pooling.

| Comparisons | Within limit | Sensitive | Insufficient complete coverage |
| --- | --- | --- | --- |
| Solver refinement, sixty pairs | 48 | 6 | 6 |
| Initialisation, twenty pairs | 0 | 17 | 3 |

The six sensitive numerical pairs belong to Cambridge/MPC. With fixed nominal insulin control, the maximum deviation for native versus factor 10 is approximately 0.9213 mg/dL; factor 10 versus 100 gives 0.0501 mg/dL. The mean absolute deviation falls from 0.5756 to 0.0379 mg/dL. Further refinement therefore reduces the difference, but the mean deviation remains above the prespecified limit. Native versus factor 100 gives a maximum of 0.9618 mg/dL, a mean of 0.6135 mg/dL and an exposure difference of 0.2083 percentage points. Meals and modelled delivery remain exactly equal over the shared trace, including initialisation. This is sensitivity to the native solver, not a change to the physiological equations.

With active MPC feedback, the maximum native-to-finest deviation is 0.8379 mg/dL, with a mean of 0.2571 mg/dL; the difference in insulin delivery is 0.01667 U. Feedback differences are not strictly monotonic: quantisation and the controller response change the control actions. The solver used internally by MPC was not refined. The factor-100 feedback and replay runs were repeated exactly in new processes. None of these results proves accuracy against an analytical or biological truth.

<a id="initialisatie-en-stops"></a>

## Initialisation and stops

The eight variants of adult#001/102/PID stop at minute 1077 from native reset. With zero hours of initialisation, this provides 1077 observed scoring minutes; with 24 or 48 hours of initialisation, the scoring day is not reached. No zero insulin total is reported for an unobserved scoring day.

In addition, adult#001/101/PID stops with 48 hours of initialisation at minute 2946, hence after 66 scoring minutes, at 9.92254116 mg/dL. Direct execution with the original native patient, sensor, pump and PID confirms glucose, sensor values and delivery exactly up to the native `done` flag. The first diagnostic attempt used SimObj, which ignores that flag and continues calculating; that output and the resulting incorrect length assumption in the diagnostics are also retained. The OpenT1D stopping policy was not changed.

All seventeen comparisons with complete scoring days are sensitive to prior history under these strict technical limits. Even 24 versus 48 hours is not generally stable. The differences encompass physiology, accumulated controller state and sensor history; they do not justify claiming that one initialisation duration is biologically correct.

<a id="verificatie-en-bewaring"></a>

## Verification and preservation

The new nominal workers were compared with the existing M1/M2 execution for basal-bolus, the known simglucose PID stop, LT1-PID and LT1-MPC. Full trace equality, repetition in new processes and nominal fixed-input replay were checked. Native M0/M1/M2 reset and historical checks remain in CI. The new checks also cover timeout, cancellation, failed initialisation, changed input bytes and an actually complete bundle that is truncated and reinventoried specifically to test false completion.

Report reconstruction works in a Python process with `-S`, without simulator imports. The full local matrix was reconstructed byte-for-byte with this on the analysis version used. Source revision, configurations, effective settings, warnings, errors, probe scripts and complete/partial output are retained outside Git; the original numerical inventory in `experiments/verification/evidence-index.json` identifies six checked local bundles, including the interrupted first PR #18 CI, the successful final PR/main CI, both full local matrices and the final native verification. The final native verification on `5807aae` also passes for missing runtime provenance, campaign cancellation and six deliberately failing workers alongside six complete control runs. The repository check contains 63 tests and a successful documentation build. Local archiving is not an external backup.

The conclusion is bounded: nominal integration is preserved exactly; some calculations are solver-sensitive and initialisation-dependent. Additional self-tests do not remove these limitations. Human data and an independent operator remain separate evidence steps.

<a id="geselecteerde-foutherkenning"></a>

## Selected fault detection

On clean commit `47c6980`, seven preselected source mutations were executed in separate temporary copies. All seven unmodified controls pass; all seven mutations are detected by the intended assertion. Each mutation test ends with exit code 1 because of that assertion, not an import error, syntax error or timeout. The original working file remains byte-identical. Patches, source hashes, test commands, environment details and diagnostics are retained.

| Injected fault | Check that detects the fault |
| --- | --- |
| Integrating U/h as U/min: factor 60 | Independent duration-weighted amount fixture: 3.5 U instead of 210 U |
| Delivering an announcement multiple times | A second request at the same time yields zero grams |
| Advancing an announcement by three minutes | Zero at minute 417, 45 g at 420, zero at 423 |
| Skipping native sensor generation during masking | The component stream must continue during masking |
| Passing unfiltered future information | The controller receives only the permitted announcement |
| Accepting a missing final point as complete | A previously valid complete fixture is truncated and reinventoried |
| Ignoring changed input bytes | Whitespace changes the bytes despite the same JSON value |

The previously existing targeted announcement test allowed the time shift through: it checked totals and one-time delivery. The new test checks exact interval assignment. This is a demonstrated gap in that selected test, not a claim that all historical regressions would miss the fault.

The preparation probe also found a bounded M2 provenance gap: an arbitrary nonempty object could replace the recorded package details after the bundle was consistently reinventoried. The reader now compares these details exactly with the saved lockfile, including the distinction between JSON booleans and numbers. The new regression test starts with a valid complete synthetic format fixture; it is not a new physiological reference. Numerical functions, native engines, controller settings and historical baselines do not change.

The score is solely seven out of seven selected faults. No overall mutation coverage, independent human review or biological validity is inferred. The Linux numerical PR #19 run additionally confirms the same 71 complete runs, nine stops and classification counts as the local campaign.

The fault campaign was checked with 66 repository tests, a successful documentation build and a successful native M2 reproduction including repetition in new processes and report reconstruction. At PR #20, the maintained inventory additionally contained the final PR #19 CI, the retained discovery probes and the local fault campaign: nine bundles in total at that point.

<a id="bevroren-robuustheidsmatrix"></a>

## Frozen robustness matrix

The first full matrix was executed on `c1edb9a`, the second on `4be1a79`. Both freezes record all 170 cases, source and lock hashes, parameter definitions and native parameter values actually read before execution. No tuning was performed. Each of the ten development configurations gets seventeen separate variants; the previously inspected OT-014 evaluation is not reused. Execution remains bounded to the two existing native families and their original controllers.

| Outcome | Both full local matrices |
| --- | --- |
| Planned runs | 170 |
| Successfully completed | 151 |
| Natively stopped | 19 |
| Worker errors or unexecuted cases | 0 |
| Planned controller pairs | 85 |
| Complete successful controller pairs | 66 |

All 170 traces, sensor audits and terminal statuses are exactly equal between both matrices. A separate verification on `4be1a79` compares all ten baselines exactly with the original numerical workflow and repeats 36 selected cases in new processes: all seventeen variants for adult#001/101/basal-bolus and Cambridge/PID, plus two Cambridge/MPC variants. Those traces and sensor audits are also exactly equal. The full report is reconstructed byte-for-byte in a Python process without simulator imports.

Seventeen stops belong to adult#001/102/PID. Without initialisation, 1077 scoring minutes are available; for the other variants the full scoring day is missing and the insulin total metric remains undefined. Adult#001/101/PID additionally stops after 66 scoring minutes with 48 hours of initialisation, and with the larger meals exactly at the end time of 2880 minutes, with glucose 9.555803939319874 mg/dL. For that last new stop, an independently constructed native env/controller loop confirms exactly the same glucose, CGM, delivery and stop. The trace contains 960 intervals, but the run is not successful. It is therefore not used as a fully successful controller pair despite 1440 available scoring minutes. This is internal software verification, not independent human reproduction.

The ranking depends on the condition and outcome measure. For the three complete simglucose pairs, the PID minus basal-bolus difference in mean glucose changes from positive at baseline to negative without scoring-day announcements. The sign for time in range reverses in two of those three pairs. For Cambridge, MPC minus PID for time above 180 mg/dL changes from +3.4722 percentage points at baseline to -0.7639 percentage points at one and a half times the meal amount. The corresponding differences in time in range are +37.3611 and +40.6944 percentage points; this is therefore not a general reversal of an overall controller score. Lower mean glucose is not automatically interpreted as better.

The report gives differences and descriptive ranges per model/condition, with all individual pairs and missing comparisons. The Cambridge singleton is not a cohort; the two simglucose seeds do not yield a population confidence interval. Parameter variants are not additional patients. The previously demonstrated numerical sensitivity of Cambridge/MPC remains a limitation; this campaign proves neither numerical accuracy of every perturbation nor biological robustness. There is no pooled ranking or general robustness designation.

The selected parameters are simglucose `kabs` and `kd` and Cambridge `SIT` and `tmaxG`, each individually at 0.9 and 1.1 times the native value. The native source definitions and units are retained. simglucose retains its tabulated initial state; Cambridge recalculates the native equilibrium. A preparation probe showed that Cambridge returns a mutable parameter object: original values are therefore copied before modification. Controller settings and the MPC predictor remain unchanged.

<a id="correcties-en-begrenzing-van-de-eindcontrole"></a>

## Corrections and limits of the final check

The robustness reader checks all native sensor calls before masking, including the two simglucose reset measurements at minute zero. An unterminated final audit line in an interrupted run is counted separately and remains identified by the input byte hash; such a line in a run reported as successful is rejected. Missing sensor calls, an extra parameter change, missing freeze provenance and false study completion are checked with retained counterexamples. The first reset measurement also gets a strict numerical time check: a boolean must not serve as zero.

Actual cancellation of the robustness campaign preserves one interrupted case and 169 unexecuted cases. The deadline check likewise retains an interrupted result. On main after PR #20, one existing M1 test intermittently hit its 0.3-second deadline during provenance collection, before the first checkpoint. The first CI attempt is retained; a targeted rerun of only the repository job on the same commit passed. The test now distinguishes that valid early timeout from a timeout guaranteed to be triggered after the checkpoint. The latter, SIGTERM, SIGINT and SIGKILL must preserve the three written minutes exactly. The production timeout was not extended.

All internal IV-001 steps are therefore executable and supported by numerical and software evidence. Independent human M2 reproduction remains an open later acceptance point. No patient data were used, no access requests submitted and no release or clinical validity claimed.

The extended inventory contains sixteen checked archives, including both robustness matrices, the full local verification, discovered faults and correction probes, and earlier PR/main CI including the failed timing test. The closing repository check comprises 70 tests and a successful documentation build. Final CI bundles created after a PR commit are additionally retained outside Git; no earlier bundle was overwritten.

The first full PR #21 CI on `097026a` passed all seven jobs and likewise confirmed 151 successful runs and nineteen native stops on Linux. Subsequent local reconstruction of the downloaded Linux artifacts produced exactly equal JSON data but different bytes because of the operating-system-dependent order of `inputs_sha256`. The reader now sorts these keys canonically. A targeted check reverses the full file enumeration and requires identical report serialisation. The original Linux output and discrepancy probe remain retained; no numerical value or historical baseline was changed.
