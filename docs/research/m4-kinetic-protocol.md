# BC-002: a kinetic insulin inlet into pinned simglucose

BC-002/1, specified on 20 September 2026 before implementation. This is the next bounded OT-026 step from [BC-001](m4-results.md), not completion of M4. The [original machine protocol](../../experiments/m4/kinetic_inlet/protocol.json) is retained. The runnable default is [BC-002/2](../../experiments/m4/kinetic_inlet/refined-protocol.json), with the numerical refinement recorded below. Work continues in the existing isolated beta-cell branch from `615bed7`; later main-worktree changes are not imported.

## Question and scope

Can an explicit liver insulin inlet preserve pinned simglucose's insulin kinetics, units and mass accounting, while reproducing an independent linear-system solution? Can the saved BC-001 evoked-release trace be transferred with quantified communication error? Only insulin kinetics is integrated with nonzero input. No glucose-control outcome, pump adjustment, subject calibration or transplant benefit is evaluated.

The primary engineering inputs are already in pmol/(kg min): zero, constant, a finite pulse with non-grid boundaries at 5.3 and 15.7 min, and a finite ramp. This resolves the inlet's numerical scale without asserting an unknown endogenous basal rate. Added basal forcing and incremental insulin inventories are explicitly zero. Native basal pharmaceutical input is preserved only in the separate zero-extension whole-patient regression.

The secondary trace replay interprets BC-001 micrograms as nominal whole-body human-insulin mass, uses 5808 g/mol and the native virtual profile's 102.32 kg, and computes `q = SR * 1e6 / (5808 * BW)`. This is a dimensionally defined, **uncalibrated synthetic scenario**, not evidence that the published pool scale fits this T1D virtual profile. See the [boundary/source assessment](m4-kinetic-boundary.md). Capacity/gain zero, 0.5, 1 and 2 are amplitude scenarios. No basal rate is inferred from the pump or from BC-001 mobilization M0.

## Native ownership and initialization

Use the existing locked M0 simglucose environment and revision `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, profile `adult#001`. Verify installed source and parameter-table hashes before execution. Preserve the package and historical reference files unchanged.

The experimental wrapper calls the original 13-state derivative and adds liver input at index 9, or a separately named peripheral comparator at index 5, under the corresponding native nonnegative-state guard. Zero input must produce exactly the original derivative, including guarded negative-state probes. Only these stated additions may change a derivative. Full-state trajectories are run only for zero added secretion, with original native initial state, basal pump and no meals. Check native solver output, fresh instances and reset equivalence over 60 minutes.

For nonzero experiments integrate the **native insulin subsystem**, evaluating the original derivative with zero SC inventories and zero exogenous action; other state entries remain a fixed carrier and are not integrated or reported as physiology. State order is Ip, Il, cumulative hepatic loss, cumulative peripheral loss, cumulative delivered input. Initial values are all zero. Native exchange and removal remain the sole owners of m1, m2, m30 and m4; no additional hepatic extraction fraction or absorption is applied.

Mass accounting is `Ip + Il + hepatic_loss + peripheral_loss = cumulative_input`. Plasma insulin concentration is `Ip / Vi`, in pmol/L. These are incremental synthetic concentrations, not the person's total fasting concentration. The native fixed m30 and absence of a direct portal-insulin term in glucose production remain scientific limitations.

## Input, numerical oracle and communication

Use elapsed minutes, finite nonnegative inputs, and explicit piecewise-linear segments with independent left/right values so finite jumps are represented without smearing. Segment boundaries are split exactly; do not extrapolate past the supplied horizon. Output uses the 0.25-minute grid plus exact pulse boundaries. Reported maximum errors are sampled on that grid, not continuous-time bounds; subinterval peaks can be larger. An independently assembled augmented matrix exponential integrates the two-compartment kinetic matrix, removal ledgers and linear forcing on each segment. It must not call the native derivative.

Compare coarse and tight RK45 with DOP853 and the matrix-exponential oracle. Prespecified tight tolerances are 1e-7 pmol/kg for insulin states, 1e-6 pmol/L for concentration, 1e-8 pmol/kg for balance and −1e-9 for numerical positivity. Exact zero-extension and repeat criteria are zero discrepancy. Check independent scalar conversion anchors and invalid/incomplete solver behavior.

The archived BC-001 trace is validated before use. Its piecewise-linear secretion is the forcing definition, not a recovered continuous biological trajectory. Transfer interval-average constant rates at 2, 1, 0.5, 0.25 and 0.125 min. Every interval preserves the integrated amount of that declared source interpolant. Compare against continuous piecewise-linear transfer; require final amount error at most 1e-8 pmol/kg, finest concentration error at most 0.01 pmol/L and finest/coarsest error ratio at most 0.35. Do not represent this as refinement of unavailable underlying observations. BC-001's own solver refinement remains separately recorded.

Compare liver and peripheral delivery at identical secreted amount, plus zero and a constant-input baseline with the same total amount. The numerical concentration error must be below 1% of the maximum liver/peripheral contrast for a resolved route comparison. If it is not, report the contrast unresolved. None of these criteria demonstrates physiological correctness of the routes.

## Recorded numerical refinement

BC-002/1 failed its prespecified 0.01 pmol/L transfer-error limit for the peripheral route at 0.125 min: 0.01149510055 pmol/L. The failed attempt and original protocol are retained. After observing that result, BC-002/2 adds a 0.0625 min communication interval, retaining every earlier interval and **all original error thresholds**. The amendment was recorded before running that interval. This is an explicit development refinement, not an independent validation or a retrospective pass for BC-002/1. The runnable default uses BC-002/2; `--protocol experiments/m4/kinetic_inlet/protocol.json` reproduces the earlier rejected transfer setting.

Compare the larger of solver/oracle error and finest communication error with the route contrast. The [execution record](m4-kinetic-results.md) retains both protocol outcomes. The additional interval makes no change to secretion amplitude, basal conventions, kinetic coefficients or biological claims.

## Artifacts and evidence limits

Preserve the protocol, exact used BC-001 artifacts and hashes, native identity/parameters, lockfiles, source versions, input segments, per-case traces, verification, errors and reconstructible JSON/figures. Failed and incomplete cases remain visible; reports reject altered, missing or nonfinal artifacts. Existing output directories are never overwritten. Public report reconstruction needs no simulator or scientific library; figure reconstruction needs only the plotting environment and artifacts.

The result can establish a checked kinetic inlet and synthetic transfer behavior. It cannot resolve BC-001's paper/code initialization discrepancy, identify human secretion from observations or complete OT-026's biological/coupled acceptance. A later protocol still needs domain-reviewed basal/scale conventions, a secretion model applicable to its glucose regime, meaningful independent observations and explicit hepatic-action assumptions. No patient-data access, contact or therapy implementation is authorized by this experiment.
