# C1/1.3 — OpenAPS history and temp-basal adapter boundary

**OT-019, 26 September 2026.** This simulator-free package follows the
[locked `oref0` source baseline](c1-oref0-example-history.md). It tests
source-native IOB on synthetic, explicit pump receipts and implements a
three-minute projection of temporary basal commands. It does not connect an
OpenAPS controller to M1 or run a native glucose outcome case.

## Causal data ownership

The [C1 information contract](c1-controller-protocol.md) gives a controller
its own previous **actions**, released observations and announcements, and
frozen configuration. M1's completed `Row` separately includes modeled
delivered insulin and private glucose/meal fields. The current controller
callback receives neither the row nor a pump-confirmed delivery receipt.
Consequently an M1 `Action` is not a pump-history event, and its `bolus_u_min`
is a **rate**, not an instantaneous bolus amount. Converting it to a delivered
`oref0` bolus would assume both accepted delivery and an injection time that
the existing interface does not establish.

The [adapter boundary](../../experiments/c1/oref0_adapter.py) keeps
`PriorCommand` distinct from `PumpBolusReceipt` and `PumpTempReceipt`.
Only explicit, completed pump receipts serialize to the source's newest-first
history format; a command, future bolus, unfinished temp, duplicate event or
generic M1 row is rejected. The receipt format is a source-replay **test
input**, not a new causal controller feed. A future route would need a
separately reviewed pump-confirmation interface, with no native private state
leakage and a defined response to delivery disagreement or missing records.

The [source preflight](../../experiments/c1/oref0_adapter_preflight.py) uses
the unchanged `oref0` `lib/iob` implementation at commit
[`88cf032a`](https://github.com/openaps/oref0/tree/88cf032aa74ff25f69464a7d9cd601ee3940c0b3),
the C1 npm lock, and its **example profile** (1 U/hour scheduled basal).
The replay assigns the synthetic `START` wall clock UTC solely to make
source timestamps zoned; an M1 operational timezone mapping is not selected.
At 60 minutes, a synthetic confirmed 2 U/hour temp over minutes 0–30 and a
1 U bolus at minute 30 yield source IOB 1.355 U: 0.425 U basal component and
0.93 U bolus component. Blank, temp-only and bolus-only controls produce
0, 0.425 and 0.93 U. This verifies the serialization and source response
under the pinned runtime. These invented records and example profile are
not M1 patient data, measured insulin, a clinical estimate or a comparator
result. Profile mapping, source glucose and COB construction from causal M1
inputs remain open.

## Time and action projection

The source may issue an absolute U/hour temp for a duration, emit no new
temp command (keep the active one), or cancel it with zero duration and rate.
`TempBasalProjection` preserves those distinctions. It divides U/hour by
60 for M1's U/min command, resumes the scheduled basal at expiry, rejects
split three-minute steps and clears state on reset. The covered 30-minute
temp begun at minute 0 occupies ten M1 intervals exactly; a later no-op
does not restart its clock.

Five-minute source decisions and three-minute M1 steps coincide only every
15 minutes. A changed source temp at minute 5 bisects M1 interval [3, 6),
so a single constant U/min command cannot preserve that event. The test
raises on this split. Running source decisions every three minutes, delaying
them to minute 6, or holding them to minute 15 would each alter timing. This
package selects none of those variants. Upstream CGM deltas are also based
on a different cadence; their causal resampling is still open.

## Reproduce and next gate

Use a clean external checkout of the pinned source with the committed
[C1 npm lock](../../experiments/c1/oref0-package-lock.json) installed, then
run from OpenT1D:

```sh
uv sync --locked
uv run --locked python -m unittest tests.test_c1_oref0_adapter -v
uv run --locked python -m experiments.c1.oref0_adapter_preflight \
  --source /path/to/external/oref0 \
  --output results/c1-oref0-adapter-preflight.json
```

The local result and byte-identical fresh-process repeat are outside Git;
their hashes are in the [C1 evidence index](../../experiments/c1/evidence-index.json).
The package makes the **no-go** concrete: M1 has no causal confirmed-delivery
feed, the 5/3-minute source decision grid conflicts, and the example profile
is not an M1 profile. [Decision 0038](../decisions/0038-c1-oref0-adapter-boundary.md)
records these conventions. The next implementation gate is a reviewed choice
of information/timing interface and failure behavior, then a separate causal
glucose/announcement/profile mapping and source output checks. Any
timing-altered version must be named as an adapted method. No native C1
matrix, strong-comparator eligibility or treatment claim follows here.
