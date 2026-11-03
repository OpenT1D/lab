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
bounded components. Implementation and final exact-revision verification are
pending in this successor's draft pull request.

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
