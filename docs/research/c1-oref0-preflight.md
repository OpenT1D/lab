# C1/1.1 — Source-pinned OpenAPS `oref0` preflight

**OT-019, 26 September 2026.** This simulator-free source check implements
the first gate in the [C1/1.0 review](c1-method-comparator-review.md).
It does not add a controller to M1, score native cases, qualify a strong
reference, or assess treatment performance.

## Source, variant and reproduction

The candidate is [OpenAPS `oref0` at commit
`88cf032aa74ff25f69464a7d9cd601ee3940c0b3`](https://github.com/openaps/oref0/tree/88cf032aa74ff25f69464a7d9cd601ee3940c0b3),
package version 0.7.1. The checked source's `LICENSE.txt` and package
declaration say MIT. The preflight pins the commit and SHA-256 hashes of
the license, package, CLI, main basal algorithm and expected example. It
uses the unmodified `bin/oref0-determine-basal.js` path. The example command
passes `--microbolus`, but in a checkout without `autotune` the CLI disables
that flag, so the exercised variant is **temp-basal-only `oref0`**, without
SMB. `enableUAM` is true in the upstream example profile; this is a
source-example check, not a selected C1 configuration.

Run the audit from the OpenT1D root after checking out the exact upstream
commit into an **external temporary directory** and installing its npm
dependencies there:

```sh
git clone https://github.com/openaps/oref0.git /private/tmp/oref0-preflight
git -C /private/tmp/oref0-preflight checkout 88cf032aa74ff25f69464a7d9cd601ee3940c0b3
cd /private/tmp/oref0-preflight
npm install --ignore-scripts --no-audit --no-fund --package-lock=false
cd /path/to/OpenT1D
python3 -m experiments.c1.oref0_preflight --source /private/tmp/oref0-preflight --output results/c1-oref0-preflight.json
```

The checkout must remain clean and lack an `autotune` directory. The
machine-readable result records each upstream direct dependency's declared
range and observed installed version/license. The upstream repository has
no committed npm lockfile; this does **not** pin transitive packages or
complete a transitive license audit. The run used Node 22.22.2 and npm
10.9.7. The result is retained outside Git in
`results/c1-oref0-preflight.json`; its hash is in the C1 evidence index.
No upstream or private health data are copied into this repository.

## Executed checks and finding

The upstream `tests/determine-basal.test.js` suite passed **52/52** under
the installed dependencies. The unmodified example invocation, with its
fixed `--currentTime 1527924300000`, returned valid JSON but did **not**
match upstream `examples/suggested.json`:

| Field | Committed example | Current pinned CLI |
| --- | ---: | ---: |
| Temporary basal rate | 0 U/hour | 1 U/hour |
| Duration | 30 min | 30 min |
| `insulinReq` | −0.12 U | 0 U |

The prediction and explanatory fields also differ. Repeating the CLI in
an empty `autotune` directory enabled the SMB branch and still did not
match (0.9 U/hour and −0.04 U). This auxiliary probe is not the selected
variant or a parity pass. The full upstream `make test` run yielded 228
passing and 16 failing tests on this host; failures include Python/shell
checks and JavaScript runtime errors. The targeted basal suite passing
does not erase the example mismatch or make the whole upstream checkout
fully verified.

## C1 information and action mapping

| Upstream input/behavior | Permitted M1 origin or unresolved issue |
| --- | --- |
| Recent glucose readings and timestamps | May be retained from released `Observation` objects only; the upstream delta calculation normalizes to five-minute changes while M1 releases at three-minute intervals. Sensor noise is not exposed by the M1 contract. |
| IOB and activity array | Must be computed from the controller's own delivered basal/bolus history with a source-pinned insulin-action curve, including 24-hour warmup. The upstream example's precomputed IOB is only a fixture; feeding it to C1 would bypass causal reconstruction. |
| Current temp basal and last temp history | Must be derived from past commands and modeled delivery. M1 currently takes a fresh U/min command each three-minute step; it has no native persistent 30-minute pump temp-basal state. |
| Profile, limits, sensitivity and targets | Must be frozen, unit-mapped configuration. The upstream example's values are not patient or M1 profile parameters. |
| Meal and COB data | May use released announcements only. Condition B has no scored-day announcement; an upstream example with 20 g carbs is not a B-case fixture. No true meal stream is allowed. |
| `--currentTime` | May use the causal simulation clock in a research-only replay; the CLI itself describes this override as disabling safety checks. It cannot be treated as a device safety result. |
| Suggested temp basal | U/hour to U/min is division by 60, but duration, cancellation, unchanged-command and scheduled-basal resumption still need stateful fidelity across M1 steps. SMB bolus semantics are outside this selected variant. |

The [OpenAPS reference design](https://openaps.org/reference-design/)
describes five-minute CGM updates and persistent temporary basal commands.
The pinned source uses five-minute prediction blocks and 30-minute temp
decisions. Running it every three minutes, silently holding a command, or
replacing a temp basal with a one-step rate would change effective behavior.
The input mapping, reset/stale-CGM behavior, transitive dependency lock and
matched development budget remain open. None is inferred from the example.

## Decision and next gate

**No-go for M1 comparator eligibility at this revision.** Exact upstream
example parity fails, and the C1 causal/action mapping is unverified. The
next bounded task is to identify a source revision and example pair that
reproduce under a locked runtime, or establish a separate upstream-endorsed
fixture for this revision. Only then implement and verify a causal IOB,
three-minute command/temporary-basal, reset and stale-sensor adapter in a
simulator-free test. Any adaptation that changes five-minute or temp-basal
semantics needs a distinct method label and cannot inherit an OpenAPS
published outcome. Native C1 scoring and a superiority claim remain closed.

The [C1/1.2 follow-up](c1-oref0-example-history.md) checks the fixture's
origin and two releases, confirms the mismatch under a separately locked
current runtime, and records a local source fingerprint for subsequent
simulator-free adapter preparation. It does not turn this example into a
parity pass.
