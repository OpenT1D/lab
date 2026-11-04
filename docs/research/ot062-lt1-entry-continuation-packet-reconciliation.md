# OT-062 entry continuation and packet-copy reconciliation

PR #69 received a fresh two-agent critical review and was merged as
`c3bc37f4910a34f53b5cbdf67f23354f9bc5ca8b`, with exactly the tested tree of
`799e19d08db200ddfd7133f992ccdfca20fd8929`. Its retained full local check passed
2,307 tests with the same 32 expected skips. All sixteen required jobs in
[hosted run 41890832016](https://github.com/OpenT1D/lab/actions/runs/41890832016),
attempt 1, passed. Fresh review ran fourteen core boundary controls and five
process controls without open findings. An earlier CodeQL test-string finding
was independently verified as a contextual false positive and resolved without
changing source or CodeQL configuration. These results qualify the preceding
[candidate-host/packet-cleanup increment](ot062-lt1-candidate-host-packet-cleanup.md),
not this successor or actual native execution.

[ADR 0109](../decisions/0109-lt1-entry-continuation-packet-reconciliation.md)
selects two additive consumers implemented in this successor. Its
[PR #70](https://github.com/OpenT1D/lab/pull/70) owns final integrated source,
current local/hosted checks and the remaining verification gaps.

## Versioned entry continuation

`native_entry.prepare` returns a new source/profile-bound continuation
specification without launching a runtime. The separate
`native_entry.mjs.continueNativeEntry` library requires exact canonical setup/execution
memberships before private-path or descriptor intake. Bind its full new source
closure independently of the existing observation producer. Complete the
inherited FD3/4 frame/ACK exchange before the fixed integration-worker continuation;
accept no caller-selected command, runtime or native delegate.

Construct fixed process arguments and public source/profile identities first,
then engine/integration/setup bytes, then observation bytes and finally the new
entry contract. Raw grants travel through a trusted-code API. The observation
and process arguments do not contain the new entry-contract hash, avoiding a
self-referential digest requirement.

The grant-bound code projection excludes only the three canonical mutable
authority JSON files. The full current audit identity still includes them and
travels separately as trusted context, derived after any separately reviewed
local membership update. This increment performs no such update. Exact
canonical memberships and the complete current audit are checked independently.
All transitive code remains bound; this separation neither changes authority
files nor lets an empty or unrelated registry authorize execution.

Both validators use the same versioned public source-key manifest. Its canonical
path roster includes itself, and its content hash is part of the code binding.
Python compares its computed closure with that roster. Neither validator may
accept an omitted transitive dependency merely because a supplied grant, host
record and expected-context map were all rewritten to omit it.

Raw grants are copied and readmitted before options or packet intake.
Owned packet buffers must match all observation hashes and exact engine,
integration and setup memberships before argument/context intake. The async
exchange uses owned input snapshots; changed inputs/source or cancellation before
continuation cannot dispatch the worker. The full current audit and canonical
authority snapshot remain separate from the grant-bound code projection.

Ordinary tooling Node and a fixed invented continuation exercise actual owned
channels, acknowledgment ordering, failures and cancellation. Invented origin is
never promoted to observed native evidence. No new native launcher, CLI, task
dispatch or store route is selected. Existing launchers, workers, profiles and
readers remain unchanged. Old host receipts do not qualify the new entry/profile.
The new `opent1d.lt1-native-entry-host/1` namespace is required.
`continuation_count` records invocation of the fixed function, not native attempt
completion. It supplies no journal/model success or new-process assertion.
Actual native bootstrap, module, addon, process, file/network and host-mechanism
families and C15–C18 remain unrun. The existing broad-rule, IPC, expected-byte-exec
and resource-limit questions remain open.
Snapshots and final rechecks assume quiet trusted control of source and inputs;
they are not atomic protection against a hostile same-user writer.

## Exact packet-copy readback

`packet_reconciliation.propose_packet_reconciliation` binds externally pinned
retained packet/intent, cleanup request/context,
accounting/provenance, journal and actual owned process receipt. Do not reopen the
removed packet, replay original live reconciliation or accept a supplied reader
report as proof. Use the unchanged strict removal reader and recheck source and
live readback before returning.

Only complete whole-packet readback may propose absence for the explicitly
allocated packet-copy IDs. Incomplete removal preserves the supplied accounting
bytes exactly. Every other copy, original origin/hold, policy, history and recovery
coverage remains. Keep historical packet and actual removal contexts distinct;
neither replaces the other's scope. The proposal's assessment reference may not
precede the retained input reference, but neither reference proves absence time.
Preflight the exact proposed successor bytes before live intake. An oversized
hypothetical complete successor cannot invalidate safe incomplete readback;
actual complete readback must refuse an oversized proposal without writing it.
Returned register and provenance remain unsaved and unapproved. Saving them
creates additional private copies requiring separate accounting.

Namespace absence is not an absence onset, original retention-timing result,
ordinary restore exclusion or physical erasure. Unknown origins, holds and
unreviewed copy/restore coverage remain blockers. Fresh invented complete and
interrupted fixtures do not establish effective erasure of an existing private
pilot, backup, snapshot, container or key.

## Gates and verification boundary

All four production authority lists remain empty. Exact runtime/security and
rights decisions, setup and verified setup receipts, bounded native execution,
case-specific host qualification and complete private recovery/removal review
remain separate. No actual selected runtime or private-pilot operation is selected.
Source and reports contain no actual personal, host/account/storage values or
private record hashes; ordinary configured Git/GitHub attribution retains its
existing visibility. The successor PR owns final-source checks and remaining gaps.
