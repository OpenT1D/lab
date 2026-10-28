# C1/1.4 — M1 comparator route decision and causal boundary

**OT-019, 26 September 2026.** This is a simulator-free source-feasibility
decision. It closes the **unmodified** OpenAPS `oref0` route on the current M1
interface and selects the published G2P2C method for the next feasibility
gate. It does not supply a trained policy, run a native comparison or qualify
a strong M1 comparator.

## Why unmodified `oref0` is a no-go here

The [C1/1.3 boundary](c1-oref0-adapter-boundary.md) can reproduce source IOB
from explicit synthetic pump receipts, but M1 supplies a controller with
released CGM and announcements, not confirmed delivery. Its previous
`Action` is a U/min command. The [executable preflight](../../experiments/c1/comparator_route_preflight.py)
rejects treating that command as an `oref0` pump receipt. A five-minute
reference decision at minute 5 can change a temp basal inside M1's constant
three-minute interval [3, 6); the projection rejects that split. Moving
decisions, changing M1's clock or inferring delivery would define a different
method or interface and would need its own decision and tests. The historical
upstream example mismatch from [C1/1.1–1.2](c1-oref0-example-history.md)
also remains recorded. This verdict does not say `oref0` is ineffective; it
says its unchanged reference loop is not an equivalent M1 comparator now.

## Replacement source and bounded adapter

G2P2C is a [published glucose-control method](https://www.utupub.fi/server/api/core/bitstreams/9a4f6dc1-b4ef-40e8-8776-ad0cc2a08ea6/content)
with [MIT-licensed source](https://github.com/RL4H/G2P2C/tree/37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70).
The selected source is commit `37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70`.
Its selected two-feature state contains 12 historical CGM/insulin-command
pairs without meal or time-of-day features. With expert bolus disabled, its
exponential pump transform produces a continuous U/min rate. These features
fit M1's action type and causal controller inputs more closely than the
current `oref0` route. The [boundary code](../../experiments/c1/g2p2c_boundary.py)
accepts only fresh M1 `Observation` values and the immediately previous
basal-only `Action`, enforces a three-minute sequence and reset, and applies
the source's normalization and exponential rate transform. It refuses a
private completed `Row`, future command, stale CGM, bolus rate or out-of-range
value. Command history here means **requested** insulin, as in the source
worker's state update; it is not confirmed delivery.

The source worker is **not** an M1 adapter: its calibration/reset and rollout
read simulator `info`, including meal fields unavailable to an M1 controller.
The preflight inspects that boundary and replays the pinned pure normalization
and pump-action functions against the local mapping. The local state is a
shape and value preparation contract, not verified policy inference: source
tensor conversion, initialization/calibration parity, any learned weights and
episode handling remain unverified.

The source defaults to GuardianRT at **five minutes**, whereas the same
source includes a three-minute Dexcom sensor matching M1's step. No trained
checkpoint is tracked in the pinned repository. A published five-minute
policy cannot simply be asserted to work at three minutes. A separate
source-faithful training or verified transfer, with exact checkpoint hash,
configuration, profile split, training environment, rights and compute
budget, is required. The source actor samples and clamps its action, so
policy RNG and inference mode must also be frozen. Condition D's stale CGM
needs a declared causal fallback before any complete C1 comparison. We have
not trained, selected or scored a G2P2C policy.

The [offline-RL glucose-control source](https://github.com/hemerson1/offline-glucose)
was also screened: its state processing includes actual meal-on-board, which
does not fit the C1 missing-announcement contract without adaptation, and a
ready checkpoint was not verified. The native Cambridge MPC remains a
separate physiological-engine reference, not a direct M1 replacement.

## Reproduce and next gate

Use clean external checkouts of pinned `oref0` commit
[`88cf032a`](https://github.com/openaps/oref0/tree/88cf032aa74ff25f69464a7d9cd601ee3940c0b3)
with the [locked dependencies](../../experiments/c1/oref0-package-lock.json),
and pinned G2P2C commit `37f7b7e1`. The source files and M1 callback are
fingerprinted in the local JSON. From the repository root:

```sh
uv sync --locked
uv run --locked python -m unittest tests.test_c1_g2p2c_boundary -v
uv run --locked python -m experiments.c1.comparator_route_preflight \
  --oref0-source /path/to/external/oref0 \
  --g2p2c-source /path/to/external/G2P2C \
  --output results/c1-comparator-route-preflight.json
```

The ignored report and a byte-identical fresh-process repeat are indexed in
the [C1 evidence index](../../experiments/c1/evidence-index.json). No patient
data, new M1 case or new evaluation matrix enters this package. [Decision
0039](../decisions/0039-c1-comparator-route.md) records the selection.

The next gate is a reproducible causal policy route: select and freeze the
three-minute training/transfer protocol and matched development budget,
obtain or train a source-traceable checkpoint, verify policy-state and action
parity, define stale-CGM and native-stop handling, then review equal
information and held-out overlap. Only a separately declared C1 development
round may use the resulting comparator; the exact evaluation freeze and
two-family assessment remain later decisions. **No strong M1 comparator is
qualified by C1/1.4.**
