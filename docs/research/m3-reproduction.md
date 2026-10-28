# M3 software preparation and acceptance

The [M3/1 protocol](m3-protocol.md) specifies a conditional six-person OhioT1DM CGM-only forecast assessment, using existing Ridge and persistence. [Feasibility](m3-data-feasibility.md) records current public sources and unresolved rights. The [canonical tutorial](../m3-tutorial.md) owns commands. Human observations have not been acquired, fitted or evaluated.

## Initial repository review

The maintained main checkout was clean at `d37264d51db24869f2bbffc342b87ccbedc26501`; fetched origin agreed. Its [main CI](https://github.com/OpenT1D/OpenT1D/actions/runs/35211787239) passed. Original protocols, locks, native sources, historical numerical baselines and M0/M1/M2/IV-001 evidence were inspected before implementation. Independent human M2 reproduction remains open and is not a preparation blocker.

The retained native failures, incomplete controller pairs, Cambridge solver sensitivity and initialization effects remain material limits. M3 does not solve them by assigning real people virtual profiles. Existing M0/M1/M2/IV-001 artifact semantics remain unchanged. The new statistical prediction question does not establish either physiological engine's human accuracy or identify a biological change for B1.

Archive verification covered the tracked M0/M1/M2/verification indices and supplemental local inventories. Distinct indexed directories within those stores were 11, 9, 14 and 21 respectively; overlapping indices were not added together. The separate PR-22 archive also passed direct verification. This is local integrity checking, not independent reproduction or offsite backup.

The audit also found malformed JSON in the inactive prepared branch-protection file. The software change repairs its check list and tests alignment with all workflow jobs. No remote branch-protection setting, visibility or publication is changed. The simglucose runtime/build constraints and setuptools advisory remain intact.

## Acceptance by roadmap criterion

| M3 requirement | Executable preparation | Human evidence still required |
| --- | --- | --- |
| Reproducible data workflow and rights | Source selection, conservative XML boundary, normalized registry, source/conversion hashes, private storage and authorization gates | Eligible recipient, current agreement, permitted processing/retention/publication, actual archive and dictionary |
| Units, clocks, compartments, missingness and overlap | Strict CGM categories, exact causal positions, no interpolation, command/delivery separation, irregular rate integration, identity checks | Verify native flags, clocks, availability, complete source identities and usable periods |
| Freeze appropriate splits and preprocessing | Provider training/test distinction, temporal development/validation purge, development-only scaler/Ridge, separate learned-model freeze | Verified release-specific bounds and responsible custodian attestation before human execution |
| External observations and simple predictor | Existing estimator, persistence and conditional native intake; physiological uses explicitly excluded | Execute held-out human forecasts; no such measurement exists yet |
| Reserve material, uncertainty and coverage | Reserved-cohort policy, whole-person bootstrap, per-origin strata, all planned/failed/unattempted cases | Actual person linkage, coverage, uncertainty and untouched suitable B1 material |
| Reconstruct permitted artifacts and synthetic tutorial | Saved forecasts, causal audit, targets, coefficient/config/protocol identities and simulator-free report reader | Actual permission to retain derived human artifacts; independent authorized reproduction |

The first five criteria remain open as human-data acceptance even where their software mechanics work. The synthetic reconstruction/example criterion can be completed independently. No CI result or invented signal closes the external-evaluation criterion.

## Verification scope

The software tests cover independent quantity examples; numeric type and JSON-overflow rejection; source/time/identity validation; missing, censored and off-grid observations; causal availability; split purging; development-only fitting; reset/isolation; native estimator equivalence; input tampering; missing provenance; false completion; partial records; cancellation/deadline retention; and reconstruction from saved artifacts. The full existing seven native/repository CI jobs remain required alongside the added M3 job.

Preparation failures include sandbox cache/network access, an initial use of the system Python lacking `hashlib.file_digest`, initialization before provenance recording, deadline exception ordering, and one-ULP arithmetic assertions. Captured logs remain archived; early cache/network attempts preceding file-backed logging are documented here rather than claimed as fully captured logs. Corrected checks use the repository's locked interpreter, record initialization before diagnostics, preserve original failure identity and distinguish floating rounding from scientific tolerances. No historical baseline or IV-001 threshold changed.

Execution is AI-assisted development/self-review. No independent person, patient-data access, clinical validation, public release or stable API is claimed. Definitive clean-commit synthetic results and exact-head/main CI identities are recorded after verification, in the evidence index and supplementary local inventories.

## Clean synthetic execution

The first definitive software run used clean commit `31b70fa80c3033cad06b90c063f978b8c486b92b`, after protocol commit `a5e6cbb14f9304885955072b9e462e1ac82d633a` was frozen and [PR 23](https://github.com/OpenT1D/OpenT1D/pull/23) was merged. Its [exact-head CI](https://github.com/OpenT1D/OpenT1D/actions/runs/35460790000) passed all seven original jobs. The local locked repository checks passed 95 tests and the documentation build; four isolated native M3 tests passed. The separate audit also ran the 11 M0 Python, 12 M1 native, 10 LT1 and 13 M2 native tests and the IV-001 reference/lifecycle verification.

All six invented participants completed, with 1,728 planned origins, 1,380 forecasts (79.86% coverage) and 1,260 scored paired targets (72.92%). The saved exclusions include warmup, absent/off-grid/unavailable history, censored/invalid targets, clock segments and split boundaries. Low/high origin strata are empty in this example, and reported as such. Each participant supplies only 210 scored targets: the shorter fixture intentionally does **not** meet the human protocol's 288-window floor.

| Synthetic output | Value in mg/dL |
| --- | ---: |
| Equal-person Ridge MAE | 4.189 |
| Equal-person persistence MAE | 3.189 |
| Primary paired MAE difference | +1.000 |
| Descriptive whole-person bootstrap interval | +0.873 to +1.138 |

These numbers describe self-authored signals only. They neither rank models for humans nor support clinical accuracy. The worse Ridge result was retained without changing alpha, splits, features or thresholds. Full precision, rank diagnostics, per-person/condition results and all exclusions are in the archived artifacts.

The verification repeated fitting and evaluation in fresh processes with identical coefficients, forecasts, errors and coverage; reconstructed the saved report byte-for-byte with `python -S`; rejected unmarked evaluation reuse while retaining its complete unattempted schedule; and retained a real SIGTERM checkpoint and deadline interruption. The error-path tests additionally cover failure during provenance initialization, import and fit finalization, and failure of secondary diagnostics.

Final review also added rejection of development targets whose recorded availability falls beyond the development block, zero censor bounds in saved traces, and conversion receipts missing a matching native participant/local alias, consumed-intake hash or producing code provenance. These close information/category boundary gaps without changing protocol settings or the reported synthetic scores. The expanded repository suite passes 96 tests. The prior synthetic evaluation is known material; both old evidence and the subsequent clean verification are retained. No human evaluation was inspected.

The [tracked evidence index](https://github.com/OpenT1D/OpenT1D/blob/main/experiments/m3/evidence-index.json) binds the initial audit/PR-23 evidence and clean local execution to SHA-256 inventories in the maintained checkout's `results/m3-archive`. Later PR/main CI artifacts are preserved in the same store with a supplementary local index; they cannot be included in their own producing commit. Preserve both inventories and do not add overlapping entries twice. No patient-level artifacts are present in this public-synthetic store.
