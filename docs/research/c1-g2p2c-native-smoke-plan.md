# C1/1.10 — Frozen M1 G2P2C integration smoke

**OT-019, 26 September 2026.** This is a pre-execution software gate for
trained G2P2C actors. The committed
[plan](../../experiments/c1/g2p2c-native-smoke.json) selects one already
known M1 seed-101 condition-D case for each adult#001 and adult#002. It
authorizes no efficacy metric, controller comparison, tuning or evaluation
matrix. The [runner](../../experiments/c1/g2p2c_native_smoke.py) must wait
for each profile's successful [C1/1.8 training attempt](c1-g2p2c-training-freeze.md)
and checkpoint intake.

## Fixed interface and acceptance

Each actor is loaded from its frozen profile training directory through the
[checkpoint preflight](../../experiments/c1/g2p2c_trained_preflight.py).
That preflight checks the full-run status, contiguous 196-rollout summary,
training args, source/engine locks, checkpoint byte hash and actor tensor
values. It also rechecks source-training versus intake actor constructor,
initial tensors and weights-only round-trip, then checks exact forward parity
between the directly imported source actor and intake actor with the final
trained weights on 16 invented states. It replays 741
invented three-minute observations, including ten
masked intervals, with a controller reset. The native smoke then supplies
only M1's released `Observation` and announcement to that actor. M1 owns
its original patient, scenario, sensor, pump, clock and terminal rule.

Both planned cases must complete all 960 three-minute intervals, produce
exactly ten profile-basal commands during the masked window and keep every
basal command finite and within the selected source action range. Native
termination, an incomplete trace, wrong fallback or invalid action is a
failed integration gate and remains in the record. This is a readiness
criterion for the callback, not a glucose-control quality threshold.
The runner preserves a partial trace and failure details; it refuses an
existing output directory. A fixed `--repeat` path can test fresh-process
identity without replacing the first attempt. The initial native snapshot
and full interval trace are saved. After the native run, the actor resets
and replays every saved command from the released M1 observation fields,
announcements and its own causal history without importing the simulator.
Any replay difference fails the integration gate.
A simulator-free injected-failure test checks that an interrupted runner
retains its initial snapshot, partial trace and failure record, and refuses
to overwrite that attempt.
The `--verify` command independently checks the saved plan, source and
checkpoint preflights, initial snapshot, complete trace, native status and
report fields, then replays actor commands without running simglucose.

After both trained checkpoints pass intake, from the locked C1 training
environment and a clean external G2P2C checkout:

```sh
uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_native_smoke \
  --source /path/to/external/G2P2C --profile adult#001

uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_native_smoke \
  --source /path/to/external/G2P2C --profile adult#002

uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_native_smoke \
  --source /path/to/external/G2P2C --profile adult#001 --verify
```

Run the same two profile commands with `--repeat` to create independent
process attempts, then verify each repeat with `--repeat --verify`. The
[readiness audit](../../experiments/c1/g2p2c_reference_readiness.py) requires
both profiles to pass their integration gates and their primary/repeat
reports to be identical:

```sh
uv run --locked --project experiments/c1/g2p2c_training_source python \
  -m experiments.c1.g2p2c_reference_readiness \
  --source /path/to/external/G2P2C \
  --output results/c1-g2p2c-reference-readiness.json
```

Missing, failed or differing attempts stay visible and fail technical
readiness. A successful audit verifies the selected callback and locked
native setting on these two known cases only. It does not qualify a fair
comparator, establish glucose-control quality or authorize a new matrix.

The outputs belong in the ignored `results/c1-g2p2c-native-smoke-*`
directories. The freeze and execution state are recorded in the
[C1 evidence index](../../experiments/c1/evidence-index.json). Even if both pass,
comparator eligibility still needs a
separately frozen, matched known-case development roster with native
reference coverage and failure accounting. This plan does not reopen M1,
M2, or the earlier C1 matrices.

## Adult#001 execution

The first frozen case completed all 960 intervals to minute 2,880. Its ten
masked-CGM commands equal the declared profile basal, all actions are bounded,
and simulator-free replay reproduced every command. Independent saved-artifact
verification passed. A new-process repeat produced byte-identical initial
snapshot, trace and report; the report SHA-256 is
`0306b099f42335847e57b5fc3d06c6793aa9fc96fd47ca742da95bf0e313aecd`.
The primary and repeat remain in separate ignored result directories, with
their hashes in the [evidence index](../../experiments/c1/evidence-index.json).
This known synthetic case is integration evidence only; no efficacy metric or
fair comparator claim follows.
The command sequence above said to wait until **both** trained checkpoints
passed intake. Adult#001 was run after its own intake while adult#002 was still
training. This ordering deviation is retained here: it changed no case,
checkpoint, action rule or acceptance check, but the two-profile execution
cannot be described as following that scheduling instruction exactly.

## Adult#002 and combined readiness

Adult#002 also completed all 960 intervals to minute 2,880, with ten exact
profile-basal fallback commands, bounded actions and complete simulator-free
command replay. The saved-artifact verifier passed for both the original and
new-process repeat. Their initial snapshot, trace and report are byte-identical;
the report SHA-256 is
`3add087d26b7f35781cbbc72bea55470209b7deff4627ae5271e10def903c66f`.

The [combined readiness audit](../../experiments/c1/g2p2c_reference_readiness.py)
verified both profiles and both repeats. Two fresh processes wrote identical
audit reports with SHA-256
`daf2b5803f74f8b5864c25c9b056dc1004e24420b3d37fceb86f17724f1757da`.
An earlier interim audit failed closed while adult#002 outputs were absent.
The final report sets `technical_m1_boundary_pass` to true and
`eligible_m1_comparator` to false. It verifies this narrow two-case native
software boundary only. A separately frozen matched development roster,
native reference coverage, equal-information review and failure accounting
remain prerequisites for comparator eligibility; the adult#001 ordering
deviation is retained in that review. [Decision 0044](../decisions/0044-c1-g2p2c-native-readiness.md)
records the technical go and comparator no-go boundary.
