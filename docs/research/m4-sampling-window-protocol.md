# BC-015-P4 — Synthetic C-peptide sampling-window protocol

This prespecification compares a short C-peptide window with a hypothetical
late extension **within the unchanged BC-003 two-compartment model**. It asks
how much the chosen times help distinguish a synthetic pulse gain from central
C-peptide removal when the pulse's onset, duration and shape are known. It
does not interpret the actual CIT-07 participants or recommend blood draws.

The [machine protocol](../../experiments/m4/sampling_window/protocol.json)
fixes the design before this experiment is implemented. It reuses the
[Polonsky 1986 forward model](models/polonsky1986-cpeptide.md), its printed
T1D group-mean kinetic coefficients and independently derived analytical
constant-input convolution. Group means are nominal values, not a transplant
population distribution. The only input is an invented **incremental**
9 pmol/(kg min) C-peptide appearance pulse from 0 to 10 minutes after a
synthetic injection clock; no basal, glucose-driven secretion or insulin
model is estimated.

The [CIT-07 protocol v8, §9.1.2.8](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_Protocol_Version_8.0_20Aug12.pdf)
places glucose injection at -0.5 minutes on its test clock and lists
postchallenge C-peptide at 1, 2, 3, 4, 5, 7 and 10 minutes. These become
1.5–10.5 minutes **after the stated injection time**. The comparison arm adds
the protocol's later glucose/insulin blood-draw times through 180 minutes
*as if* C-peptide had also been obtained then. Those extra C-peptide values
are entirely synthetic; the core protocol does not document them. The
-10/-5/-1-minute C-peptide samples are recorded as source metadata but
excluded from fitting because this design assumes an exactly known zero
incremental baseline. Real basal estimation would add uncertainty.

The two fitted positive multipliers are pulse gain and K3 removal, each
bounded from 0.5 to 1.5 with truth 1. K1, K2, distribution volume and input
shape stay fixed. The reference ODE generates noiseless concentration in
pmol/L; the independent analytic convolution predicts it. A 30 pmol/L
Gaussian engineering error is added at every postchallenge time for 64
predeclared seeds, with the same draw reused in the nested early and extended
designs. Two starts are fitted per case, and failed fits or bound solutions
stay in the denominator. This error scale is not an observed assay property.

Before interpreting the comparison, the analytical and ODE curves must
agree within 0.0001 pmol/L; the log-sensitivity matrices at two step sizes
must differ by at most 0.001 relative; and noiseless fits from both starts
must recover each multiplier within 1%. The numerical runner must reject
incomplete results and reproduce exact saved numerical files on a fresh
repeat. No required superiority threshold is set for the extended window:
the point is to measure, not assume, its effect in this one favorable model.

Even a strong synthetic difference would not establish patient-level
identifiability. CIT-07 is an insulin-modified **IV glucose** protocol;
the separate coupled BC-008/BC-011 engine has a meal stimulus and must not be
silently replayed against it. Actual secretion input, assay limits, renal
kinetics, transplant route and participant linkage remain unverified. The
[public source screen](m4-alternative-observation-screen.md) and
[unsent review brief](m4-collaboration-brief.md) retain those gates.
