# BC-003: forward C-peptide kinetics and a synthetic observation experiment

Protocol BC-003/1, specified on 20 September 2026 before implementation or outcome inspection. The [machine specification](../../experiments/m4/c_peptide/protocol.json) freezes profiles, inputs, solver settings, sampling and criteria. Work continues from `751e701` in the isolated `codex/beta-cell-reference` worktree; later original-worktree edits are not imported.

## Question, model and permitted conclusions

Given a declared C-peptide appearance rate, can the two-compartment model described by Polonsky et al. ([1986, DOI 10.1172/JCI112308](https://doi.org/10.1172/JCI112308)) predict concentration with independently checked numerics? Under explicitly noiseless synthetic observations and a known input, which parameter combinations are distinguishable? This is a forward observation reference for OT-025 and preparation for the remaining OT-026 measurement gate.

The primary specification is the process scheme on p. 99, the unnumbered bolus equation on p. 100 and Table I on p. 103. Both the equation and table were visually inspected. The [model card](models/polonsky1986-cpeptide.md) records source conventions and applicability. No patient records, cohort reconstruction, clinical parameter estimates or therapy effect are part of this protocol. A human-data estimator or general C-peptide deconvolution algorithm is not implemented.

## Inputs, states and process ownership

Time is elapsed minutes. Input is C-peptide appearance in pmol/(kg min). States are central and peripheral amounts in pmol/kg, cumulative eliminated amount, and cumulative input since time zero. Plasma concentration is central amount divided by central distribution volume in L/kg, giving pmol/L. The source's 65.5 mL/kg becomes 0.0655 L/kg; pmol/mL concentration becomes pmol/L by multiplication by 1000.

K1 transfers central to peripheral, K2 transfers back and K3 removes from central, all in min^-1. Thus `dQ1/dt = -(K1+K3) Q1 + K2 Q2 + q`, `dQ2/dt = K1 Q1 - K2 Q2`. Elimination is `K3 Q1`. Do not import the insulin subsystem's hepatic loss or SC absorption. The source uses C(t) for amount in its scheme and concentration in its dose/volume expression; this implementation names those separately.

Use unchanged finite forcing/interpolation from BC-002. Every input segment is integrated separately, with no extrapolation and no smoothing of jumps. A bolus is an explicit initial central amount, not an artificially high rate in one time bin. Initial ledgers are zero. Conservation is `Q1 + Q2 + eliminated = initial inventory + delivered_since_start`.

The two fixed profiles are the printed normal and T1D group means. They are **nominal parameter sets**, not individual fits or averages of predicted patient curves. No kinetic parameter is estimated during the forward runs. The independent synthetic recovery experiment below is separate.

## Frozen cases and initialization

For each profile execute a synthetic 100 pmol/kg central bolus over 180 min, the published constant-infusion schedule (3 then 30 pmol/(kg min), 120 min each), a synthetic basal-plus-pulse case over 240 min, and zero input. The source's actual 50 nmol bolus cannot be mapped to its per-kg parameters without individual body weights; this experiment makes no Figure 1 cohort reproduction claim. The infusion schedule is reproducible, but its replay with mean parameters does not reproduce Figure 2's measured or mean fitted curves.

Zero and step cases start with zero incremental amounts. Bolus starts with 100 pmol/kg in central and zero in peripheral. The synthetic basal case explicitly assumes 1.5 pmol/(kg min) and starts at `Q1 = q/K3`, `Q2 = (K1/K2) Q1`; the rate becomes 10.5 from 10 to 30 min before returning to baseline. This demonstrates total versus incremental concentration with a fully declared synthetic basal convention. It does not infer basal release for BC-001 or a person.

## Numerical reference and acceptance

Compare tight RK45 and reference DOP853 with an independently implemented analytical bolus kernel from p. 100 and its exact convolution for piecewise-constant forcing. Record the coarser RK45 result without using it as the reference. Keep numerical dynamics and analytical reference separate. Also check an independent one-compartment limit (K1 = 0), constant equilibrium, exact zero, repeated execution, invalid configurations and incomplete solver output.

At the specified 0.5-minute reporting grid require concentration disagreement at most 1e-5 pmol/L, mass/input error at most 1e-7 pmol/kg, and amounts no lower than -1e-9 pmol/kg. Equilibrium discrepancy must be at most 1e-8 pmol/kg, unit conversions at most 1e-12 relative and repeat discrepancy exactly zero. These are numerical criteria for these inputs and sampled times, not continuous-time or biological error bounds. The simple comparator is a central one-compartment model with the same volume and irreversible central loss; report its transient difference, without asserting either model's predictive accuracy in people.

## Synthetic sensitivity and identifiability

Use the nominal T1D profile and an independently generated 100 pmol/kg bolus curve at the paper's 30 sampling times from 2 to 180 min. Fit only K1, K2, K3 and Vp, keeping dose known. Optimize positive log parameters from two frozen starting points and require relative parameter recovery within 1e-4 and concentration residual within 1e-6 pmol/L. This is an implementation demonstration on noise-free synthetic data, not external validation.

Compute concentration sensitivities to log parameters with two finite-difference steps, require relative matrix agreement within 1e-5, and report singular values/rank using the frozen 1e-8 relative threshold. Compare the full schedule with early-only and three-point schedules. Short-window numerical conditioning is descriptive; no sample schedule is declared clinically sufficient.

Then allow both input amplitude and distribution volume to scale by the same factor, 0.5 or 2. The resulting bolus concentrations must agree within 1e-8 pmol/L. Report the joint five-parameter sensitivity rank and an exact amplitude/volume ambiguity. At equilibrium, concentration depends on q/(K3 Vp), and not separately on the exchange rates. These explicit ambiguities limit what spontaneous secretion and C-peptide alone can establish. No arbitrary secretion profile is fitted to a human or synthetic curve.

## Artifacts, data needs and review

Archive protocol, model and reused-input sources, environment specification/lock, exact forcing and initial states, all profile/case traces, analytical and simpler-model concentrations, numerical checks, sensitivities and recovery records. Preserve failed attempts and errors. Reconstruct JSON using only saved artifacts and the standard library; reconstruct figures without rerunning dynamics. Distinguish published equations/parameters/stimulus from synthetic generated observations in every report.

The [measurement specification](m4-cpeptide-measurements.md) defines paired glucose/C-peptide sampling, stimulus and treatment records, assay/renal information, independent evaluation and access conditions. Available catalogue descriptions are not permission or evidence that the required measurements exist. Review by a secretion/kinetics expert, assay specialist, clinician and statistician remains open. Do not contact anyone or request restricted data in this experiment.
