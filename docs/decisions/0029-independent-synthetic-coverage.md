# 0029 — Independent synthetic profile coverage assessment

Status: accepted locally on 24 September 2026 before any new assessment draw or implementation. The [BC-014 protocol](../research/m4-coverage-protocol.md) fixes the question, seeds, denominators and failure rules.

BC-013 showed objective-profile geometry on two known development draws. Its nominal chi-square cutoff is not demonstrated finite-sample coverage. Assess **evoked gain only** on independent new draws with unchanged BC-013 inference and BC-012 physiology. Share each interior draw across free-volume GIC, fixed-volume GIC and GI so design differences are paired. Keep a separate exact-boundary gain scenario to expose nonregular behavior without asserting a 95% expectation there.

At the generating gain, nuisance-reoptimized Q minus unrestricted Q is enough to decide pointwise inclusion; recomputing complete profile curves for every draw would answer a larger and much more expensive question. Preserve the original three unrestricted and two conditional starts, raw negative DeltaQ, engineering bounds, analytic nuisance-volume projection and independent reference-solver checks. Count failures in the planned denominator and disclose them separately. Report Wilson intervals and Monte Carlo limits without making an observed percentage a biological or calibration pass criterion.

No model equation, parent protocol, threshold, source data, treatment mechanism or human-data route changes. The current output is a conditional synthetic assessment under one pinned patient and observation design. Population calibration, independent observations, domain review and any therapy interpretation remain separate OT-026/M5 work.
