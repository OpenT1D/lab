# OT-062 LT1 diagnostic harness and fractional reader

Date: 1 November 2026. Base: `90e249bbb79a0bfba32927969c2549d9e74b081a`,
the squash merge of critically reviewed PR #51. This increment implements the
source/fixture scope selected in [decision 0094](../decisions/0094-lt1-diagnostic-harness-reader.md).
It does not perform a native import, installation, build or simulation. The
[runtime/rights gates](ot062-lt1-preparation.md#private-evidence-gates-and-exit-criteria)
remain open; the original [admission proposal](ot062-runtime-rights.md) remains
descriptive evidence with all authorizations false.

## Question and selected construction

Can the audit-1 lagged rate controller consume released glucose exactly once per
five-minute tick while preserving every Cambridge native callback, reset, sensor
generation and pump update? This remains a causal execution question, not an
efficacy study. Select the same LT1 2.1.0 source revision
`9a6092065bd821f88691cd8d03b0550acd665573`, fixed `Gpeq=124.91784824923789`,
IdealCGM and StaticInsulinPump. Preserve the native SolverRK1_2, default one-minute
outer step, seed 101 and component offsets. Source declarations and unresolved
parameter ancestry remain as recorded in the [LT1 asset card](models/lt1-cambridge.md).

[protocol.mjs](../../experiments/lt1_diagnostic/protocol.mjs) validates the bounded
thirty-minute UTC plan and records the new trace. The
[wrapped construction](../../experiments/lt1_diagnostic/wrapped.mjs) assembles
Simulator/Cambridge/IdealCGM/pump through injected constructors and the existing
sampled kernel. The [direct reference](../../experiments/lt1_diagnostic/direct.mjs)
independently constructs those modules and independently implements release
selection, lagged updates, announcement accounting and controller memory. It
imports neither the wrapped queue nor the sampled kernel. Both share plan
validation and recording, so matching paths alone cannot exclude a shared bug.
The separate Python reader and hand-calculated controls supply additional oracles.
No M2 PID/MPC direct path is substituted for audit-1.

Both constructors query `Cambridge.computeIIR` at the frozen equilibrium glucose
and start time. The derived finite U/h basal must equal the frozen plan and fit
[0,3]; otherwise construction refuses. They never alter initial state to fit a
controller. This read uses fixed parameters; it makes no general claim about
time-varying profiles or native local-midnight initialization. Native Simulator
retains ownership of reset and integration. No new physiological solver or pump
model is implemented.

These injected constructors are trusted test code, not a sandbox or an arbitrary
plugin interface. The production `loadNative()` function always refuses before
loading source; caller-supplied flags/receipts cannot open it. It is deliberately
not a positive admission verifier. A future reviewed loader/worker must bind the
complete source/runtime/setup/host packet before native use. This increment adds
no task registry entry, SDK descriptor, GUI dispatch, installer or process owner.

## Clock, release and delivery contracts

Plans and traces use whole elapsed milliseconds from `2024-07-20T00:00:00Z`.
The diagnostic supports at most one actual meal and one separately specified
announcement. Durations below 60000 ms are refused because upstream setMeals clamps
them. A duration must also round-trip exactly through the native minute argument.
The selected 150000 ms start and 90000 ms duration preserve the 2.5/1.5-minute case.
No event is silently rounded to an integer-minute grid.

The recording sensor invokes native generation before applying a delay or mask.
It delegates native next-update requests. The wrapped queue retains measurement
and availability time separately, chooses the newest measured released sample
and returns a copy. Read queries do not consume samples or change policy state;
late older samples cannot displace newer observations. Each controller callback
checks that generation has reached exactly that callback time. Only the released
CGM value crosses to the policy; native actual-event and patient-state objects
are not controller inputs. Announcements are copied from the frozen declared
records, delivered once, and ignored by the diagnostic rate calculation.

Policy updates occur at 0,5,…25 minutes. Every other native callback holds command;
the terminal callback at 30 records raw generation/pump output without a new policy
transition. The next requested stop is strictly later than current time even at 30,
avoiding a repeated terminal callback. Native pump updates still occur at every
callback, with its own quantization and random draws. Command U/h and modeled
delivery U/h remain different fields. Stateful sampled updates never enter a
continuous RHS. Historical M4 purity probes and all M1/P1/M2 contracts stay intact.

## Trusted reader and retained failures

[reader.py](../../experiments/lt1_diagnostic/reader.py) consumes bounded regular
plan/packet files through the existing intake helper and strict JSON decoder.
It binds actual plan bytes, the selected upstream/runtime candidate and current
Python static import ancestry plus the fixed JavaScript/data source roster.
This is an implementation inventory, not proof of an actual native runtime or
a complete dynamic import trace. The expected packet hash must come from an
external trusted inventory/project store. Computing it from an untrusted producer's
file does not authenticate that producer's history. No archived code is imported.

The reader validates the selected native callback grid, finite Cambridge state
fields, raw IdealCGM sampling, as-of observations, freshness, lagged memory/command
order, announcements and actual meal intake. It integrates the previous modeled
rate only when a following valid endpoint exists, using duration_ms/3600000 hours.
The result is an exact numerator/denominator in U from recorded decimal rates.
An empty or single-row prefix has undefined delivery, reported as null. It never
pads a missing tail or treats a terminal rate as an additional interval.

Failure/interruption/unfinished status remains authoritative even with every row
present. Primary and diagnostic-export errors have separate fields. The in-memory
session recorder retains separate reset/run sessions and valid prefixes; a failed
row or last observed raw generation stays in an explicitly unscored diagnostic
tail. Export receives a copy, so it cannot rewrite the primary result. That
recorder is not a durable ledger or a process supervisor.
Separate review reproduced stale last-generation diagnostics when a subsequent
run failed in solver reset before sensor reset. Each new recording session now
clears that recorder-owned observation before invoking Simulator, without an
extra native reset. A repeat-then-initialization-failure control keeps the prior
session intact and requires an empty current prefix and diagnostic tail.
A separate serialization-fault control found that a diagnostic tail containing a
circular object could overwrite the original validation error. Diagnostic capture
now records that secondary failure independently and rethrows the original cause;
an additional export failure is retained rather than replacing either cause.

`compare()` checks modes/identities and exact scientific row values/status from
the same byte buffers each reader consumed, with no tolerance or rounding. It
reports both outcomes and never grants native acceptance. Input labels are only
`invented` or `native-unadmitted`; even a structurally valid declared-native record
returns native acceptance and execution authorization false. A checksum or a
declared origin is not a verified setup receipt, rights decision or host admission.

## Preselected controls and evidence limits

The [scripted interface fixture](../../tests/lt1_diagnostic_fixture.mjs) contains
no physiological equations. Its invented states, glucose and pump rates are not
native outputs, parameter tables or a virtual patient. The
[Node controls](../../tests/lt1_diagnostic.test.mjs) and
[Python reader tests](../../tests/test_lt1_diagnostic.py) cover the following cases.

| Control | Independent result or distinguishing refusal |
| --- | --- |
| Direct/wrapped construction and repeated native-shaped reset | Same scripted rows; 32 outer callbacks, 6 sampled transitions; every sensor/pump callback retained; distinct session arrays |
| Fractional event | First times 0,60000,120000,150000,210000,240000,300000 ms; no integer-minute coercion |
| Delay/mask | At 15 min raw 150 remains recorded while the policy consumes raw 60 measured at 10 min and released at 15 min; the 20 g announcement is delivered once |
| Policy/amount | The known first four commands are 1.2,1.2,1.2,1.7999999999999998 U/h without rounding; independently scripted delivery integrates to 25/48 U |
| Prefix/failure | Two completed intervals give 3/100 U; zero/one-row delivery is null; simultaneous primary/export errors remain distinct; full failed/unfinished records stay noncompleted |
| Counterexamples | Early/relabelled observation, wrong freshness/order, duplicate/omitted callbacks, hidden fields, wrong grid, terminal transition, malformed/truncated JSON and changed plan/source/packet hashes refuse |
| Shared wrong paths | Giving both paths the same current-sample command still fails the independent reader; changing a state in one otherwise valid trace fails exact pair comparison |
| Engine-free inspection | Moved packet/plan bytes reconstruct with Python `-S`; ambient Decimal precision/rounding does not change the exact rational amount |

These are fixture and source-construction checks. They do not run LT1, verify its
numerical solution/device behavior, establish arbitrary code purity or close
native C15–C18. Historical reference criteria remain independent and frozen.
Actual admitted direct/native replay, reset, sensor/RNG consumption and process
observations are still unrun. A matching pair of invented traces is not native
parity or biological evidence.

## Remaining admission and integration work

The subsequent [native worker successor](ot062-lt1-native-worker.md) implements a
separate positive verifier and fixed-entry loader with an empty production grant
registry. It preserves this guide's historical closed entry and reader identity;
its native branch, setup and host process integration remain unqualified.

Before setup: authenticate the selected Node checksum/signature, complete the
bundled/runtime/build security disposition, record the restricted-use decision
and notices, then review the exact positive native loader/worker, source inventory
and full C15–C18 packet. Separately authorized setup must produce a verified
receipt before named-host execution admission. No gate is changed by this merge
or by a reader accepting declared data. Native inputs, settings, raw states and
reports must stay in owner-only private storage with separately reviewed export.

Later native execution must use the existing `platform_process`, `Ownership` and
shared `execution.supervise` facilities, with host file/network confinement,
deadlines and descendant/sentinel checks. The existing project store remains
responsible for all planned slots, attempts, explicit retries and trusted seals;
this reader handles one attempt and does not migrate that ledger. Actual native
process cancellation, full project relocation and SDK/GUI migration remain open.

The author owns the one final full repository check on the final source, following
the [development handoff](../development.md#task-and-review-handoff). The PR handoff
records exact clean/dirty state, separate technical review, actual targeted/full
check outcomes and private evidence location. Local receipts remain distinct
from hosted CI. No new dependency, historical lock, baseline, tolerance, reader
transition registry or publication allowlist is changed.
