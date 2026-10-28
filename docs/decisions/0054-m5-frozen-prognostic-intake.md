# 0054 — Bound M5 intake to a frozen prognostic model

**Status:** Accepted for bounded synthetic implementation, 2 October 2026.

## Context

The existing M5 synthetic comparison verifies a fixed analysis shape on 32
invented participants, using development-only reference and added-function
ridge models. The tool-first direction calls for a researcher to connect
their own method and inspect coverage, failures, provenance and paired
metrics. The human-source linkage, biological review and empirical freeze
remain open; extending synthetic tool use does not require closing them.

## Decision

Add a separate `M5-RESEARCHER/1` route with exactly three local files:
trusted `model.py`, frozen `state.json` and hash-bound `model.json` under
`m5-prognostic-model/1`. Declare model identity, rights basis, source/state
hashes, current Python major/minor with no external dependencies, and the
exact invented fixture and eligible development participants used for
training. Treat training and rights statements as self-attested provenance;
hashes are byte identity, not proof of those statements.

Expose `predict(record, state)` on `m5-landmark-input/1`: prior reported
insulin U/day, prior glycemic status mg/dL, landmark day after first infusion
and observed-function index. Do not pass aliases, split labels, outcomes or
future infusions. Retain the unchanged 32-person fixture, split, five
exclusions and repeat infusions. Provide no human loader.

Use two fresh standard-library workers per eligible held-out participant,
a default five-second budget each and finite numeric output in `[0, 1000]`
U/day. Process isolation is not a security sandbox; execute trusted code
only. Exact prediction and runtime-identity agreement is required for paired
scoring. Preserve every attempt and failure, including controlled
interruptions and remaining unattempted work. Compare with the unchanged development-only
standardized ridge reference, penalty 1 on slopes, including baseline MAE
over all seven eligible evaluation participants and both paired MAEs.
Incomplete coverage limits interpretation; zero pairs have null metrics.

Archive model/state/declaration bytes, protocol/implementation snapshots,
fixture, saved reference, projected requests, both attempts and reports.
Reconstruct from saved artifacts without importing candidate code or
refitting, checking the saved reference against development normal
equations. Hashes verify saved consistency, not authenticated execution
history. Keep the existing fixed M5 route unchanged.

## Verification and limits

Check numerical reference arithmetic, causal projection, repeat isolation,
failure/coverage accounting, tamper detection and model-free reconstruction,
then run locked repository checks. The
[protocol](../research/m5-researcher-protocol.md) owns the verification
record; the [guide](../m5-researcher-workflow.md) owns user execution.

This decision accepts an internal synthetic research workflow. It does not
establish rights clearance, independent usability, human prognostic quality,
treatment effectiveness or a source-specific empirical freeze. Those retain
their existing external evidence gates.
