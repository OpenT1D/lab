# OT-062 tooling-host probe and retained removal evidence

PR #67 was critically reviewed again and merged as
`df0781fcd35cd282f11d710c4dce4b1820a63d4c`, with the same tree as tested
`a9c4534f08914b39d70ccbe1a4de56c2f0d7574a`. Its full local check passed 2,265
tests with 32 expected skips; all sixteen required jobs in hosted run 41830086534
passed on attempt 1. Fresh reviews found no open findings: eleven additional
transport/descriptor cases, six reconciliation cases and meaningful guard omissions
challenged ownership, source/history pins and conservative incomplete behavior.
Those results belong to the preceding [owned-transport/reconciliation increment](ot062-lt1-owned-transport-reconciliation.md).

[ADR 0107](../decisions/0107-lt1-tooling-host-removal-evidence.md) selects an actual
engine-free tooling-host consumer and durable removal-evidence storage. The
successor PR records exact implementation, host observations and final checks.

## Explicit tooling-host scope

The fixed host probe uses ordinary already installed tooling Node through the
existing owned transport, under a fixed deny-default Darwin arm64 OS profile.
It does not stage or start the selected Node/LT1 candidate or import a model.
Fixed inherited descriptors 3/4 carry the frame/ACK separately from logs. Matched
unconfined positive controls use only fresh invented targets and a loopback server.
Parent and child must observe actual permission denials for outside read/write,
loopback connection and fixed no-op nonallowlisted exec, while allowed input reads
and scratch writes succeed. Missing targets or connection refusal cannot pass.

Completion/cancellation must retain actual owned process/start evidence, stopped
child activity and survival of an unrelated control until explicit cleanup. Source,
tooling executable and profile identities are captured privately before/after.
Runtime initialization fields remain observations; the production native observer
allowance is unchanged. Broad system bootstrap and mach-lookup remain limitations;
this does not prove immutable bootstrap, arbitrary IPC or hostile-owner isolation.

Run only explicitly on the supported host, using a fresh path under an existing
canonical owner-only parent outside the checkout:

```sh
uv run --locked python -m experiments.lt1_diagnostic.host_entry_probe --output /absolute/private/new-host-entry-probe
```

Root/hosted checks cover bounded validators and invented cases, never invoke the
OS sandbox automatically. Tooling-host observations cannot satisfy the six actual
native-family denominator or C15–C18. Selected-runtime rights/security/setup and
native execution remain separately gated; all four production lists stay empty.

An explicit local observation on the supported host passed both completion and
cancellation with the fixed profile, without widening it. In each case both the
parent and child recorded all four permission denials and successful allowed
operations; matched unconfined operations succeeded. The inherited handoff/ACK
completed, owned process/start lineage was retained, child activity stopped, and
the unrelated control survived until its explicit cleanup and reap. Private source
and tooling/host mechanism identities matched at final readback. This is one local
tooling-host observation, not hosted OS-profile evidence or selected-runtime
qualification; exact source and final repository/hosted results accompany the PR.

## Retained removal-evidence packet

The fresh fixture producer retains the original manifest and intent before its
own separately injected synthetic removal. The parent uses the actual shared-owner
receipt bytes in the unchanged reconciliation reader. No invented completion
receipt substitutes for that process outcome. Interrupted removal stays incomplete.

The packet writer validates exact externally pinned reconciliation inputs before
filesystem intake. It writes a durable intent before copied inputs, uses fixed flat
bounded members, publishes exclusively and reopens by external manifest/register/
context/source identities. Failed/cancelled prefixes remain available; a complete
pending map cannot masquerade as the published leaf. Replay recomputes the exact
stored proposal and rechecks source and live namespaces under quiet ownership.
The intent binds the publication parent and physical root identity; copying or
relocating a packet cannot reuse its allocated copy IDs. Readback preserves the
stored `assessment_as_of` with `assessment_refreshed: false`; it does not silently
refresh the retention assessment.

The first intent assigns unused aggregate packet-copy IDs for every original
subject and preserves origins/holds. Postpublication provenance and additional-copy
accounting stay outside the immutable packet to avoid a final-manifest hash cycle.
This separate unsaved accounting proposal starts from the supplied registration's
old states, retaining conservative `present` copies. Stored reconciliation proposals
are unapproved metadata; no automatic composition, activation or absence approval
follows. Saving returned metadata creates further copies requiring accounting.

A later critical review found that a valid near-limit registration could produce
an oversized additional-copy register only after packet publication. The writer
now computes that exact successor byte bound with fixed-width evidence hashes
before reconciliation replay or private filesystem intake. Known unrepresentable
successors refuse without creating a pending or published packet; genuinely
interrupted or uncertain operations still retain their available evidence.

These are private snapshot/software observations. No removal timestamp, retention
deadline compliance, complete live/quarantine/snapshot/backup coverage, ordinary
restore exclusion or effective erasure is established. Unknown original clocks
stay unknown. No existing private pilot, backup, snapshot or key is read or removed.
Added source/examples contain no actual personal names, host/account/storage values
or private record hashes. Ordinary configured Git/GitHub attribution remains public.

## Remaining qualification

The selected-runtime bootstrap, modules/addons, entry/profile integration and
confinement still require their exact admitted setup and independent execution
decision. All six actual native-family cases and C15–C18 remain unrun. The next
host decision must bind that candidate's real executable, bootstrap and imports,
rather than transfer this tooling fixture's result. Keep the production launcher,
profile, worker and authorities unchanged until those decisions exist.

For effective deletion, review complete original-copy and ordinary restore
coverage and the unknown private retention origin before any removal decision.
This increment retains actual owned **fixture** removal receipts and conservative
separate proposals; it does not settle backup/snapshot/key coverage, approve a
register, establish a removal time, or remove an existing private payload.
