# OT-062 LT1 host boundaries and exact-file removal fixtures

This follows the [private controls](ot062-lt1-private-controls.md). PR #59 was
reviewed again with 384 additional combinations and boundary/guard controls, then
merged as `28d098deb673e09472d7ddf15652da980d36b2c5`. Its tree equals tested
`b545cd7c6767a387018ce5af0c44aa64179dd5ce`; the retained full check ran 1,993 tests
with 32 expected skips and hosted run 41519164950 passed its required roster.
Those receipts do not qualify this successor automatically.

[ADR 0099](../decisions/0099-lt1-quarantine-and-host-fixtures.md) and the
[bounded result summary](../../experiments/lt1_diagnostic/host-removal-review.json)
define this increment. Actual human identities, host/account/storage details,
private contexts and personal/policy record hashes remain private. Ordinary GitHub
account and configured commit-author metadata remain public. No actual native
packet, private audit evidence, backup, snapshot or encryption key was removed.

## Separate removal authority and implementation

[removal.py](../../experiments/lt1_diagnostic/removal.py) implements a bounded
internal API, with no general deletion CLI or automatic expiry job. Its fixed
[authority](../../experiments/lt1_diagnostic/removal-admissions.json) starts empty.
Unknown request bytes refuse before JSON/caller-path intake or evidence creation.
A retention result, receipt field or caller-supplied registry is not authority.
The trusted fixture injection seam admits only the explicitly constructed test
requests during qualification; arbitrary Python under the same UID is outside
this application boundary.

An admitted request binds source/Python and host/account observations, exact reviewed
context bytes, existing canonical private target/evidence roots, a fresh attempt,
and a closed file map with device/inode/UID/mode/size/time/hash observations.
Context hashes bind bytes; semantic rights, process, retention and recovery
decisions still require actual review before admission. The public kind label
does not establish that a packet is safe or invented.
The host tuple contains platform, machine, hostname and UID. Permitted local use
is recorded in the separate private context; these fields do not establish
boot/login/session continuity or native host qualification.

The first backend supports one flat directory, at most 128 files, 16 MiB per file
and 32 MiB aggregate. Requests/contexts are bounded to 1 MiB, journals to 2 MiB.
Names are a restricted 64-character ASCII subset; file modes are 0400/0600 and
directories 0700. Target/evidence roots must be separate, nonnested, current-user
owned and on the same filesystem. Links, FIFOs, special files, unlisted entries,
changed bytes/identities and unsafe directory bindings refuse. Mode/UID checks
do not qualify inherited ACL or a complete hostile-owner storage policy.

All inputs are opened and verified before evidence creation or removal. Original
descriptors remain open. Each entry moves via the existing exclusive-rename
primitive into a new quarantine, where its identity/bytes are checked again before
unlink. A substituted entry is retained on mismatch. There is no blind rollback,
recursive removal, attempt adoption or automatic retry. The reviewed root and
empty quarantine/evidence directories remain available for inspection.

POSIX unlink does not accept an expected inode/hash. Even after quarantine there
is a final check-to-unlink window for a hostile same-user writer. Exclusive quiet
ownership and separately reviewed process/storage controls are prerequisites;
neither FD-relative operations nor read-only modes prove a hostile-owner sandbox.

## Evidence and reconstruction

A new owner-only evidence attempt holds `events.jsonl` and quarantine. Prepared,
quarantined and removed events are fsynced with affected directories. Failures
retain their primary cause and available prefix. A broken journal is not followed
by an attempted success record. An outer stop can leave a valid file in quarantine
or an absent file whose removal event was not fully written; recorded removals
are only a lower bound in incomplete evidence.

The reader binds externally retained request/journal bytes, current source and
reviewed target inode. It checks private evidence names/mode and reobserves journal
and namespaces after its last source inspection. A complete result also needs
every expected removal event, current empty target/quarantine, no terminal or
outer error, exact integer zero exit, no external signals and observed empty owned
cleanup. Reported absence without that process/evidence chain stays incomplete.
Partial inspection reports names and the event prefix, not verified payload bytes
or a scientific report. The retained qualification independently checks surviving
invented bytes. Opening evidence executes no archived code and resumes no operation.

Every returned result has `effective_erasure_verified: false`, setup/native flags
false and no new authority. Completion means the bounded fixture namespace was
observed absent under the declared process/source conditions. It does not account
for filesystem recovery, backups, snapshots or unknown copies. A quarantined object
keeps its original retention subject/clock; update the exact private copy map under
the existing [retention convention](../decisions/0098-private-retention-planning.md).

## Versioned host boundary fixture

[host_boundary_probe.py](../../experiments/lt1_diagnostic/host_boundary_probe.py)
uses the existing supervisor, process observer, legacy profile construction and
validator. Its fixed [fixture](../../experiments/lt1_diagnostic/host_boundary_fixture.py)
contains no engine and accepts no user command or policy. The earlier host probe,
fixture and historical identities remain unchanged. The new profile narrows
`/System` read/map rules to `/System/Library`; explicit dyld-support imports,
other bootstrap paths and broad mach-lookup remain known limitations.

The denominator is fixed before launch: complete and intentional cancel. Both
parent and actually observed child must satisfy nine EPERM/EACCES denials:
outside read/write, loopback connection, staging write/unlink/chmod, fixed no-op
nonallowlisted shell, scratch-symlink outside read and `/System/Volumes/Data`
alias outside read. Input reads and scratch writes must succeed, with isolated
startup and the declared environment. Each denial also needs a successful
unconfined control. Aliases must exist and name the same real object; ENOENT or
connection refusal cannot pass. Staging is owner-writable in the unconfined case,
so ordinary POSIX mode denial is not substituted for sandbox evidence.

The executable test inherits descriptors. Review reproduced a false denial when
opening DEVNULL failed before exec; a guard regression distinguishes the attempted
exec from that earlier I/O failure without launching a process in unit tests.
Both cases require child start identity, stopped heartbeat, empty final ownership
and survival of an unrelated control process until explicit cleanup. Cancellation
uses an inherited TERM-ignoring child to exercise owned escalation. External
interruption, incomplete evidence and contradictory process errors cannot pass.

Run this explicit internal fixture only with a new path under an existing private
0700 parent; root CI never launches the OS sandbox:

```sh
uv run --locked python -m experiments.lt1_diagnostic.host_boundary_probe --output /absolute/private/new-boundary-run
```

It refuses unsupported hosts, existing output and noncanonical source copies.
Nested sandbox application required the host tool permission on the development
Mac; that permission is separate from runtime/setup/native admission.

## Observed qualification and limits

On the declared private Darwin arm64 host, both host cases passed, with nine
denials in each of two groups per case and all unconfined controls. The 149-file
static implementation/initializer inventory matched before/after. Current Python,
sandbox, imported profile and shell identities were recorded privately. These are
observations under the stated host/tool assumptions, not an immutable or fully
reproduced bootstrap/OS. Broad mach-lookup does not qualify arbitrary hostile IPC.

Four separately retained Python removal cases passed on fresh invented data:

| Case | Independent observed state after owned process cleanup |
| --- | --- |
| Complete | Zero exit, two recorded removals, target/quarantine empty; reader completes |
| Deadline after prepared record | No moves/unlinks; both original files retained; reader incomplete |
| Deadline after first removal | First file absent with recorded removal; second exact file retained; reader incomplete |
| Cancel after quarantine | No unlink; first exact file retained in quarantine and second at target; reader incomplete |

All four retained empty owned-process sets, preserved an independently started
unrelated process and reaped it explicitly afterward. The 50-file helper source
inventory and fixture-script identity match the final qualification. Development
receipts and counterexamples are retained separately from that final evidence.

Review corrected stale reader observations and inconsistent terminal/outer
completion, plus the pre-exec DEVNULL false denial and host completion schema.
Meaningful missing-guard controls distinguish the errors. Pure tests and the
explicit host/removal records remain separate from full root/hosted checks.

The existing [manual removal procedure](ot062-lt1-private-controls.md#manual-removal-and-verification)
still owns actual private cleanup. Its origin/copy/snapshot/backup coverage and
effective-erasure mechanism remain unqualified. No container, key destruction,
backup setting or actual native launch was introduced. Runtime/rights, immutable
native source/startup, native file/network/IPC/module/addon/process behavior and
C15–C18 remain open. All four production authority lists are empty. Historical
locks/guards, scientific readers/baselines/tolerances and public task/SDK/GUI/CI
scope remain unchanged.

The [native/recovery preparation](ot062-lt1-native-recovery.md) follows this record
with a read-only launch contract, explicit private host observations and separate
scoped logical-recovery/timing assessment. It does not promote these Python
fixtures to actual native or recovery qualification.
