# OT-062 entry handoff and bundle-copy registration

PR #64 was critically reviewed again and merged as
`894b0534a6a2a4012cf8de0a7945ca2122383b17`, with the same tree as tested
`ca2cd8b11f2b61653bc356e373c2efafaf21554e`. The complete local check passed
2,186 tests with 32 expected skips; all sixteen required hosted jobs in run
41730725138 passed. Fresh reviews found no open issues: 21 entry negatives and
two positive controls, plus eight bundle cases and three single-guard omission
controls, retained the intended boundaries. These results verify the preceding
[entry/bundle increment](ot062-lt1-entry-review-bundle.md), not native acceptance.

[ADR 0104](../decisions/0104-lt1-entry-handoff-copy-registration.md) selects two
bounded components, now implemented. This successor's pull request records the
final exact revision and verification; its draft is retained until those checks pass.

## Selected handoff boundary

Exchange one bounded entry frame and one exact canonical acknowledgment over
separate, already opened endpoints. The caller owns their provenance and provides
exclusive ownership; this library cannot establish endpoint identity or native
confinement. Existing observation admission precedes endpoint intake. A refused
gate leaves caller endpoints untouched. After valid intake, this exchange owns
only its endpoints, listeners and timer.

Require complete frame/acknowledgment EOF and bind origin, exact frame and grant
hashes, attempt and nonce. Bound bytes/chunks before aggregation, handle
backpressure and retain bounded partial evidence on cancellation, timeout,
premature close or stream failure. The asynchronous handoff budget starts after
synchronous observation; it cannot preempt `collectCurrent` hashing. No native
import follows acknowledgment. A separate strict reader verifies byte/source
consistency while preserving false phase, endpoint-truth and native authority.

No CLI, process owner, automatic transport route or write to selected journal
paths is added. Actual dedicated descriptors, sandbox/profile permission, fixed
entry and instrumentation remain separately reviewed. All six native families
remain unrun; a successful invented exchange supplies no actual host result.

## Implemented entry exchange

[entry_handoff.mjs](../../experiments/lt1_diagnostic/entry_handoff.mjs) exports
`handoffInvented`, `handoffCurrent` and the pure `acknowledge` formatter.
Invented facts cannot choose observed origin. The current function uses unchanged
`collectCurrent` before touching endpoint/options intake. Invalid options,
nonfresh endpoints, a shared stream and process stdio are refused before ownership
transfer. Endpoints and their implementations must be trusted; the library does
not prove that an opaque caller stream is a pipe or confined to a peer.

The outgoing frame is ended separately from the incoming acknowledgment. An ACK
is at most 1,024 bytes and 64 chunks, with exact compact UTF-8 magic/JSON/LF/EOF
bytes binding kind, frame, observation grant, attempt and nonce. A complete ACK
without EOF is insufficient. Success requires frame-write completion and matching
ACK EOF. A monotonic check also refuses late events when the timer callback has
not yet run. The finite 1-30,000 ms budget covers asynchronous handoff only.

Results retain intended frame bytes and a bounded received ACK prefix in memory,
with separate write-attempted/write-finished/ACK-EOF fields. Failed writes may have
sent a prefix; there is no automatic retry. Completion/cancel/error/timeout removes
the exchange's listeners/timer and requests destruction of only its two owned
endpoints. Minimal passive error/close guards retain only their endpoint until a
terminal signal; a silent endpoint may retain these constant guards without a
poller or deadline timer. Destruction request is not independently verified
endpoint closure. A copy is passed to the sink so it cannot mutate retained
intended evidence. This does not prove the bytes actually received by a peer.
The library never invokes a worker after acknowledgment.

[handoff_readback.py](../../experiments/lt1_diagnostic/handoff_readback.py) checks
externally expected current Python/JS source identities and ACK bytes, then calls
the unchanged full entry-frame reader. Its transport frame is canonical compact
UTF-8; older supported entry-frame byte forms remain supported by the old reader.
Exact ACK reconstruction rejects duplicate, extra, torn, differently bound or
promoted records. Repeated historical reading is allowed. Byte consistency proves
neither actual transport execution nor endpoint identity, closure, handoff timing,
stdio, phase or live ownership; these flags and all native flags remain false.

## Selected copy-registration boundary

Reopen the exact published review bundle against external manifest, base register
and context identities. Validate exact policy/current/predecessor bytes before
filesystem intake. Explicitly allocate one new, unused copy ID per original
subject, conservatively representing that subject's derived data in the whole
bundle. Bind provenance to its manifest and unchanged origin/hold/context/source.

Keep the base register's old states; the stored recovery proposal is not silently
approved or adopted. Preserve old subject/copy objects, deadlines and historical
recovery horizon. New coverage flags remain false: recording these copies cannot
prove there are no other copies or update the actual restore horizon. Reassess
using the unchanged planner and recheck bundle/source identity before returning.
Unknown origins remain unknown and holds do not restart retention.

Return deterministic proposed register/provenance bytes for the same complete
inputs, including assessment time and source identity. Do not save or activate
them. Saving them elsewhere creates further private records requiring their own
accounting. Existing recovery scope, mapping and observations must be reconciled
for the added copies. No existing pilot, storage, backup, snapshot, key or payload
is selected for removal; effective erasure remains unproved and all operational
authorities stay closed.

## Implemented registration proposal

[bundle_registration.py](../../experiments/lt1_diagnostic/bundle_registration.py)
exposes `propose_registration`. Supplied register, policy, predecessor and a
separately hash-pinned allocation are checked before private bundle intake. The
allocation binds the full current registration-source identity, manifest, base,
policy, context, evidence kind and exactly one unused copy ID per subject. Bounds
on IDs/counts and successor register size precede filesystem access.

The unchanged bundle reader verifies the published closed namespace, exact stored
base/policy and replay. The successor is copied from that base, retaining every
old copy and state even when the saved unapproved recovery proposal says absent.
Only the explicit new aggregate copies and predecessor link are added. Known and
unknown origins, origin evidence, holds, policy, context and historical
`recoverable_until` remain exact; all three coverage booleans are false. The
unchanged retention planner must return exactly the inherited deadlines.

Each returned provenance record binds its subject/copy, complete bundle manifest,
private path/root/leaf, base, allocation, context, time and inherited values.
Source-identity hashes reference the allocation and immutable bundle intent;
the current full registration identity is returned once. Total provenance is
bounded to 4 MiB. Source and the complete bundle snapshot are checked again before
return. A changed inode with identical bytes is still refused.

No register or provenance is written, activated or approved. Keep these returned
private bytes outside the immutable bundle and account separately for any saved
copies. `new_bundle_copy_registration_required` remains true until a reviewed
register is actually adopted; `global_copy_coverage_verified` remains false.
Recording derived metadata does not establish actual payload copies, refreshed
backup/snapshot coverage or a removal permit. Actual host, complete ordinary
recovery scope and effective erasure remain unqualified.

## Verification boundary

Tests use tooling Node, invented in-memory channels and new disposable private
metadata bundles. They cover strict acknowledgment, backpressure/EOF/deadline,
cancel/error prefixes, cleanup errors, evidence-buffer ownership, source binding,
exact old-state/history preservation, allocation/size bounds and final namespace
revalidation. Independent technical and facts/privacy reviews and the final
clean-revision local/hosted results belong to this increment's PR record.
