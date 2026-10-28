# C1/0.6 — Two-sided feedback kernel

**OT-019 development, 25 September 2026.**
[Decision 0034](../decisions/0034-c1-feedback-discrete-conventions.md)
fixes the discrete conventions for a new, unconfigured and
simulator-independent controller in
[`experiments/c1/feedback.py`](../../experiments/c1/feedback.py).
This is an arithmetic implementation and test record. No gains, patient
settings, native simulator outcome or superiority claim are selected here.
The [C1/0.5 audit](c1-method-revision.md) explains why the prior overlay
was retired as lead.

## Input and ownership

The caller supplies integer controller time `t` (minutes), released CGM
`G` (mg/dL), its integer source time, a Boolean fresh/held flag, and the
unchanged native basal-bolus **basal rate** `B` (U/h). The kernel returns a
bounded basal rate; a future adapter must preserve the native meal bolus
and explicitly convert the native basal unit at its boundary. There is no
patient object, simulator import, physiological insulin-on-board estimate,
or dataset in the kernel. A held value must exactly match the last fresh
value and source time. Future observations, nonfinite values, invalid base
rates and a nonincreasing controller clock are rejected before state changes.

The settings are required explicitly. They are a target and low cutoff
(mg/dL); proportional gain `Kp` (U/h per mg/dL); integral gain `Ki`
(U/h per (mg/dL·min)); optional rise gain `Kr` (U/h per (mg/dL/min));
maximum rise (mg/dL/min), fresh gap (min), absolute integral
(mg/dL·min), upward correction step (U/h per controller update), and final
basal rate (U/h). The step bound is per update, not per minute. All
settings are finite and nonnegative; the five limits are positive and the
low cutoff is below target. The class has no defaults or selected gains.

## Exact update order

State is previous command time, last fresh `(source time, G)`, integral
`I` (mg/dL·min) and previously **commanded** correction `C` (U/h).
`reset()` clears all four; the first call has elapsed time zero. At a
fresh observation:

1. `e = G − target`. The nonnegative rise is
   `R = clamp((G − Gprevious)/(t − tprevious), 0, Rmax)` if a previous
   fresh observation exists and its gap is at most `gapmax`; otherwise
   `R = 0`. A fall gives zero rise.
2. If `G ≤ low`, set `Ibase = min(Iprevious, 0)`; otherwise retain
   `Iprevious`. This clears positive integral memory on a fresh low, while
   retaining negative memory for downward correction. Set
   `Itrial = clamp(Ibase + e·Δt, −Imax, Imax)` only when elapsed time
   since the **previous command** satisfies `0 < Δt ≤ gapmax`. Otherwise
   `Itrial = Ibase`. A long unobserved gap is never integrated wholesale.
3. Calculate `Craw = Kp·e + Ki·Itrial + Kr·R`. If `G ≤ low`, replace
   `Craw` by `min(Craw, 0)`. Calculate `Traw = B + Craw`,
   `Trequest = clamp(Traw, 0, Tmax)` and
   `Crequest = Trequest − B`.
4. Upward slew limits the **correction relative to the native base**:
   `Tfinal = clamp(B + min(Crequest, Cprevious + Smax), 0, Tmax)`.
   Downward movement has no slew limit. The final rate bound and a change
   in native `B` take precedence over the correction step. Record the
   actual commanded correction as `Cnew = Tfinal − B`.
5. Conditional anti-windup: if `Itrial` changed and the error pushes
   against a binding upper total-rate clamp, lower total-rate clamp, or
   upward correction slew, keep `Ibase` instead. Recompute steps 3–4
   once with that integral. A sign-opposing error may unwind integral
   even while an output bound is active. Record raw, requested and final
   rates, clamp/slew flags and whether the integral was frozen.

For a held observation, output the native base `B` exactly, keep `I` and
last fresh sample, set `Cnew = 0`, and advance command time. This fallback
bypasses slew for changes in the native base. The next fresh call may
integrate only its own elapsed command interval; the rise term still needs
two sufficiently close **fresh** observations. Nonfinite intermediate
arithmetic raises before committing any state.

The matched engineering comparator is `without_rise(settings)`: a copy of
the same settings with **only** `Kr = 0`. It uses the same controller,
causal inputs, base action, reset and limits. It is not a qualified strong
published-method comparator.

## Verification and next gate

`tests/test_c1_feedback.py` uses invented arithmetic fixtures to check
two-sided action, zero-gain native-base identity, candidate/comparator
equivalence without rise, low gating, upper/lower/slew anti-windup,
opposing-error unwinding, held and long-gap behavior, reset and rejection
without state mutation. These are kernel checks, not simulated glucose
outcomes. The historical C1/0.2 and C1/0.4 results are unchanged.

The subsequent [C1/0.7 native development matrix](c1-feedback-development.md)
adds the adapter and a one-attempt matched budget on the 16 known
profile/seed/condition cells, retaining every attempt and failure. A
published comparator, Cambridge boundary and new evaluation freeze remain
separate gates. Neither this kernel nor a passing repository check supports
a clinical or human-benefit claim.
