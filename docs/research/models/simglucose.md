# simglucose model and asset card

Status: native scenario reproduced locally and in Linux CI; evidence is tracked in the [reproduction record](../m0-reproduction.md). M1 now provides a separate [thin adapter and development demonstration](../../m1-tutorial.md); neither workflow establishes clinical validation. [M2](../m2-reproduction.md) reuses the unchanged M1 loop in a separate process and evaluates the prespecified unused adult profiles, reporting native failures and conditional comparisons separately from Cambridge.

## Identity and intended use

Jinyu Xie's simglucose, revision `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, package version 0.2.11. The [source assessment](../m0-assessment.md) links pinned implementation and license evidence. Physiology is the simglucose implementation of the UVA/Padova 2008 lineage. Neither another implementation's regulatory status nor its scientific evidence transfers automatically.

The M0 reference selects the upstream tutorial's adolescent profile and basal-bolus scenario. It establishes software behavior for that fixture. The proposed adult controller comparison remains separate. The source offers ten profiles each for children, adolescents and adults; these are parameterized virtual profiles, not a sampled clinical cohort.

## Inputs, outputs and lifecycle

Native physiology advances at one-minute intervals using SciPy dopri5. Dexcom sets the outer observation/action interval to three minutes. Both basal and bolus actions are U/min; the pump clips and quantizes them before delivery. Integrate delivered rates over intervals to recover U.

Custom-scenario numeric times are hours, with event quantities in grams. `CHO` records interval-averaged meal-event inputs, not a consumed-carbohydrate trace. The controller receives the preceding interval's actual meals and profile-specific questionnaire and physiology information. No claim of realistic announcement-only information is made.

`BG` is initially subcutaneous glucose and subsequently a three-minute mean of that signal; `CGM` is separately simulated. Neither is plasma glucose. Action rows describe the following interval; the final action cells are structurally missing. The native runner ignores terminal flags and runs to the horizon. The recorder reports threshold events independently and checks finite results. Native reset and fresh-process execution are tested separately.

## Assets, rights and distribution

The repository declares MIT for code. Preserve Jinyu Xie's notice; direct installation from the pinned upstream is used rather than vendoring source or tables. Each run inventories installed Python and CSV file hashes.

| Asset | Role | Provenance and rights limit |
| --- | --- | --- |
| `vpatient_params.csv` | Physiological constants and initial conditions | Bundled under the repository declaration; no independently verified table-level chain of title |
| `Quest.csv` | Carbohydrate and correction factors and profile information | Separate controller asset; do not treat as measured clinical data |
| `sensor_params.csv` | Sensor cadence and noise configuration | Preserve exact preset and source; no claim of current commercial-device validation |
| `pump_params.csv` | Delivery limits and quantization | Preserve exact preset; modeled delivery is not measured tissue absorption |
| Upstream tutorial | Scenario and default-controller reference | Selected segment, fixed date and unique output paths are recorded harness changes |

Parameter provenance uncertainty is retained. No redistribution of upstream parameter tables is introduced. Original OpenT1D harness code retains the repository license; runtime dependencies retain their licenses.

## Execution, evidence and limits

The isolated lock fixes Python 3.12, NumPy 1.26.4, SciPy 1.13.1, pandas 2.2.3 and the complete dependency graph. setuptools is held below removal of the upstream `pkg_resources` dependency; build tooling is constrained separately. These are tested compatibility choices, not a statement that newer stacks cannot work. Warnings are retained.

The [reproduction guide](../m0-reproduction.md) supplies commands, measured summaries and acceptance. Solver settings, configuration, source hashes, package versions, output hashes and failures are recorded per run. No independent researcher or published figure has been reproduced. Cross-platform numerical differences must be reported rather than hidden behind an arbitrary tolerance. The initial maintainer owns this research harness; no supported simulator release is promised.

## M3 suitability boundary

The [M3 data assessment](../m3-data-feasibility.md) excludes this engine from its CGM-only human forecasting application: verified physiological profiles/state initialization and a defensible observation mapping are absent. M0/M1/M2/IV-001 synthetic evidence remains unchanged. No real person is matched to a virtual profile or parameterization.
