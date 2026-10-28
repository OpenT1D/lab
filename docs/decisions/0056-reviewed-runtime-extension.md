# 0056 — Preserve historical baselines through one reviewed runtime extension

Status: accepted for internal verification on 2 October 2026.

## Context

Commit `d6e97db6ae9f0885a15f8ad1b8ea3a488956e98c` added pinned GlucoSim
`6422a91d533125a8feb4f2e8737aecd67fec95c9` to the native Python environment.
The lock hash changed while existing dependency entries remained identical.
The M0, M1 and M2 jobs of [CI run 37014981209](https://github.com/OpenT1D/OpenT1D/actions/runs/37014981209)
rejected the historical runtime context after retaining their native outputs.

## Decision

Keep both original baseline files and all original output collections unchanged.
Archive the preceding lock bytes and declare the exact addition in a separate
review record. Before accepting the extended runtime, verify both lock hashes,
prove the complete semantic lock difference, bind the original baseline bytes
and require the complete reviewed package inventory. Continue all original
configuration, ancestry, solver and exact trajectory comparisons.

M0 observes distribution metadata before importing Gym. Its legacy
`pkg_resources` import can expose setuptools vendored distributions later in
the process. Record both complete observed inventories explicitly; reject
mixtures, missing locked packages, version changes and undeclared additions.
M1 requires its original post-import inventory plus the one added package.
M2 continues to use the same M1 collection checker.

Return separate runtime-extension evidence with review and checker hashes.
Preserve each observed manifest, original collection name and original origin.
The extension does not qualify GlucoSim as a reproduced reference or change a
scientific tolerance. See the [evidence and reproduction route](../research/runtime-baseline-extension.md).

## Alternatives and consequences

Blindly replacing the old lock hash would hide the runtime change. Removing
context checks or generating new expected trajectories from the failed run
would weaken historical verification. An explicit extension permits the
existing environment while retaining the earlier evidence and failure modes.

Unknown locks and dependency changes require a new investigation. Revisit this
record if native outputs cease to match, the existing dependency graph changes,
or another platform needs a new historical output collection. Internal agent
review and CI do not close independent human or biological acceptance gates.
