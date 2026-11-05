# 0093 — Separate the LT1 sampled diagnostic from native admission

Date: 1 November 2026. Status: selected for preparation only.

## Question and decision

Can the audit-1 lagged proportional basal controller consume only released
observations exactly once per native five-minute tick, while LT1 retains its
solver, reset, sensor and actuator lifecycle? This is a causal execution question,
not an efficacy estimand. Select a separately named LT1 diagnostic boundary,
`lt1-cambridge-audit1/1`, before a separately reviewed simglucose successor.
No historical M1/P1/M2 controller allowlist, reader or runtime guard changes.

Implement the dependency-free sampled kernel now and qualify it using invented
audit transcripts. A future native controller delegates at minutes 0,5,…25 of
the proposed thirty-minute development run. Other native callbacks hold its
command. The terminal callback consumes no sample and creates no new command.
Raw samples are generated before filtering; a trusted release queue outside
the kernel chooses the newest measured sample available as of the tick.
Older released samples cannot displace a newer consumed sample. Reject duplicate,
reversed or missed sampled ticks and hidden extra controller inputs. Sampled
memory never enters continuous RHS callbacks. Retain repeated/out-of-order pure
RHS probes separately; they cannot prove arbitrary supplied code pure.

Use target 120 mg/dL, gain 0.01 U/h per mg/dL, cap 3 U/h and reset memory 120.
On a fresh observation compute from prior memory, then update it. On stale input
command the frozen basal without updating memory. Basal must be finite in [0,3]
and separately bound to native equilibrium settings; the fixture's 1.2 is invented.
Only U/h `iir` is supported. No bolus amount or U/min value may enter LT1 as iir.
Future simglucose maps the same rate to U/min by dividing by 60; its native
cadence and observation compartment remain distinct.

Preserve every native pump callback, including its random draws and quantization.
Integrate modeled delivery over completed native intervals using actual elapsed
minutes/60, independently of command. A five-minute controller clock does not
make the native callback/delivery grid five-minute or integer. A new native
fractional-grid reader must be implemented and qualified separately; the existing
M2 reader remains authoritative for its original grid.

## Scope and evidence

The new fixture ledger reader consumes bounded regular JSON through existing
intake helpers, refuses native-kind evidence, binds the trusted audit fixture
bytes, keeps declared slots, first attempts, explicit retries and unfinished
prefixes. It executes no archived code. It is a preparatory reader control,
not an OT-064 native reader migration or installed SDK capability. Do not register
this candidate in the task registry or broaden descriptor 6.
Its lineage checks cannot authenticate history: a consistently rewritten standalone
fixture can remove a failure and relabel the retry as first. A recorded accepted
counterexample preserves that limitation; the native route needs the existing
immutable project store and an externally trusted evidence inventory.

The unchanged Decimal audit oracle remains exact. New JavaScript kernel arithmetic
checks allow at most `2 * Number.EPSILON * max(1, abs(expected))` U/h for the
selected bounded fixture values: one multiply and one add in the policy. The
first targeted run exposed `1.7999999999999998` versus decimal 1.8; retain that
binary output without rounding. This new arithmetic criterion does not replace
native parity: direct and wrapped serialized scientific fields must match
exactly on the same admitted runtime. Existing baselines/tolerances remain frozen.

Runtime/security, restricted-use rights and direct/wrapped harness/reader review
precede separately authorized setup. A verified setup receipt then precedes
named-host execution admission. The passive candidate inventory grants none of
these permissions. [The implementation packet](../research/ot062-lt1-preparation.md)
owns acceptance, private evidence and the concrete next package.
