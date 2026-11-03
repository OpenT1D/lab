# OT-062 owned pre-start controls and read-only recovery observations

PR #61 was critically reviewed again and merged as
`ee2faab9bed51064ca292d931bf3b366eee82a44`; its tree equals reviewed/tested
`86f2e95a582ba0c2fe4fd8b89d3e9f80d3075003`. The retained full check ran 2,066
tests with 32 expected skips. Hosted run 41602738665, attempt 2, passed all sixteen
required jobs. Dependency review was rerun after GitHub reported its successful,
finished first job as `in_progress`; both receipts remain retained. Fresh review
added 1,024 recovery combinations, twenty collector/preflight cases and three
meaningful guard controls with no open finding. Those checks verify the
[preparation increment](ot062-lt1-native-recovery.md), not this successor.

[ADR 0101](../decisions/0101-lt1-owned-prestart-and-recovery-probe.md) defines the
new operational boundaries. Actual names, host/account/session/storage values,
personal policy, private receipts and their identifying hashes remain private.
Ordinary Git/GitHub attribution remains public.
The [bounded result summary](../../experiments/lt1_diagnostic/prestart-recovery-review.json)
publishes only reviewed statuses and public source-inventory identities.

## Fixed native qualification entry

[native_launcher.py](../../experiments/lt1_diagnostic/native_launcher.py) supplies
one internal `launch_native` API. It accepts engine/integration bytes and four
roots, never a command, policy, registry or environment. Both exact grants must
already be in the source-local execution authority before supplied path intake,
host capture, evidence creation or spawn. A separately reviewed actual setup
receipt must also be in the existing setup list. All production lists remain
empty, so the production entry refuses before those operations.

After admission, the Python pre-start verifier checks the fixed runtime identity,
entire bounded staging map, selected Node executable hash, canonical worker source,
current journal/reader identity, fixed synthetic plan, packet/receipt bytes and
same-owner integration grant. It invokes the existing read-only materialization
inspector on the staging payload's parent, retaining its request/manifest binding.
It never runs `node --version`. The existing JS worker verifiers still execute
after startup; their source and behavior have not been changed.

Staging and packet roots are frozen private directories; output and evidence are
separate existing private directories. The worker output must be empty for
`AttemptJournal`, so the outer log is `launch.log` in the separate evidence root.
All roots must be canonical, mutually nonnested and outside the checkout, with
reviewed device/inode/UID/mode identities. Unlisted entries, aliases, changed bytes
or private packet-mode violations refuse. Staging retains the existing stager's
file/directory/depth/byte bounds. ACLs and hostile-owner storage are not qualified.

## Live owner and last checks

The versioned integration host receipt binds the current launcher/Python identity,
four roots, fixed sandbox and imported-profile bytes, profile hash, materialization
identities, deadline/grace and maximum context age. Its owner observation comes
from the same still-live main-thread process that will call the supervisor. An old
short-lived collector PID cannot become that owner. Runtime/rights/setup decisions
remain separately reviewed prerequisites; receipt hashes are byte bindings.

Prepare and review those exact receipt/grant bytes while that owner exists.
Following admission, reobserve boot/OS, UID, PID/start and POSIX-session fields
against the approved bytes without replacing timestamps, receipts or grant hashes.
A POSIX session remains distinct from login/audit-session continuity.

The [task-local adapter](../../experiments/lt1_diagnostic/native_supervisor.py)
uses the unchanged canonical shared supervisor code, defaults and ownership loop.
Each invocation copies its globals and replaces only the spawn binding with a
trusted guarded closure; shared module globals are untouched. The hook runs after
log opening, directly before the existing spawn. The native adapter sets the log
to 0600 and checks its descriptor/inode binding. It performs
the potentially slow owner capture before final source/packet/staging consumption,
then rechecks mechanism bytes, root/log/empty-output bindings and context expiry.
Cancellation before spawn returns interrupted with no worker; cancellation after
spawn uses the existing owner, deadline, escalation and cleanup. A failed last
guard leaves any available log and starts no worker.

The fixed command uses `sandbox-exec`, the reviewed profile, selected staging Node
and the canonical integration worker with staging/packet/output arguments. The
caller supplies no flags. Exactly LANG, LC_ALL and PATH are passed, stdin is
DEVNULL and inherited descriptors are closed. Existing shared callers retain their exact source and normal stdin behavior. The actual process fixture checks the passed spawn
arguments as well as EOF and noninheritance of a known inheritable descriptor.
Darwin Python may add `__CF_USER_TEXT_ENCODING` during startup; that observation is
kept separate from the exact three-key environment passed by the launcher.

The provisional native profile's explicit source-read rules name fixed worker/
authority files and the trusted reader source closure, including Python and lock/
candidate JSON, alongside staging/packet/output reads and output writes with the
selected executable. Its
read-metadata, dyld-support and broad mach-lookup rules remain known limits. It
has not been exercised with Node. The final POSIX check-to-exec race, whole dynamic
bootstrap/modules/addons/IPC, hard RSS and rlimits are not qualified. Complete,
primary-failure, deadline and cancel tests run only a fixed isolated Python parent
and child; they preserve an unrelated process and require empty owned cleanup.

The positive whole-native intake tests use invented staging, a mocked executable
identity/materialization/owner and a mocked native backend. They prove structural
binding and late refusal, not actual native loading. Specific controls cover
unknown authority, missing setup, foreign/background/stale owner, changed plan/
reader/packet/runtime/tool/log bytes, extra entries and expiry during acquisition.
All results keep native-host qualification, native acceptance and new authority
false. Existing exact execution grants may eventually permit bounded qualification
with native cases still unrun; no automatic gate requires already passing those
same cases, and no successful result inserts a new admission.

Four separately retained Python cases passed on the declared private host:
complete, primary exit 23, deadline and cancel. Each recorded the actual stdin/
close-fds/environment spawn contract, observed live parent/child start identities
and stopped heartbeat, preserved the unrelated sentinel and reaped it explicitly.
The 156-file static implementation/fixture map matched before/after and before
every spawn. The private runner preserves interruption/failure prefixes and
planned unrun slots; review corrected an interrupt handler that could otherwise
continue to a later fixture. No Node, sandbox or model was started for these cases.

## Read-only recovery probe

[recovery_probe.py](../../experiments/lt1_diagnostic/recovery_probe.py) exposes a
separate explicit `capture(targets=...)` API. It requires canonical Darwin arm64
source and performs only these fixed commands:

```text
/usr/sbin/diskutil apfs listSnapshots -plist /System/Volumes/Data
/usr/bin/tmutil listlocalsnapshots /System/Volumes/Data
/usr/bin/tmutil destinationinfo -X
```

The installed Apple manuals identify different scopes: APFS-volume snapshots,
local Time Machine snapshots and configured Time Machine destinations. The last
does not enumerate completed, offline, historical or third-party backups. No
`listbackups`, mount, `-m`, backup change, deletion/thinning, exclusion, root/FDA or
encryption operation is offered. The development host-tool permission runs the
reviewed queries as the same user; it is not root or native admission.

The collector binds its static source, tool hashes and observed Data device before
and after acquisition. Each command has a five-second timeout. Raw response
prefixes/base64 and their hashes stay private; invalid, failed, empty or truncated
responses remain unavailable. Query bounds are checked after acquisition, not a
hard memory/RSS sandbox. A valid empty destination array is an observed response,
never proof that no historical backup exists.

At most sixteen exact reviewed local files may be read back. There is no HOME or
directory walk. A target needs a canonical 0700 owned parent on the observed Data
device, a nofollow single-link ordinary file in mode 0400/0600, streamed hash and
descriptor/namespace stability. Each file is bounded to 16 MiB and all reads to
64 MiB, charging failed reads with at most one growth-detection byte per target.
Physical checkout/root ancestry also rejects case aliases; unknown checkout
identity refuses intake. Changed, unreadable, aliased or unsupported objects stay
unknown or refuse the reviewed target. Payloads are
not copied. Readbacks carry observation intervals, no original retention time,
`absent_since` or invented exact absence instant.

One explicit private capture observed all three command responses and the current
presence of the existing private decision record. Its 49-file static source map
was stable. All complete-copy/snapshot/backup coverage and all authority/erasure
flags remain false. Raw identifiers, file hashes and actual policy values are
not published. Existing private payload bytes and permissions were not altered;
no record, backup, snapshot, container or key was removed.

## Actual removal and remaining gates

Use these point observations to review the existing private copy register and
[manual removal procedure](ot062-lt1-private-controls.md#manual-removal-and-verification).
Explicitly account for logs, temp/cache, relocated/revised records, quarantine and
ordinary restore paths. Query success, exclusions or a currently empty list cannot
self-approve that scope or register all copies. Keep original clocks and predecessor
history; an unknown original time cannot be reset from file timestamps.

Actual native setup/startup/confinement and C15–C18 remain unrun. Actual recovery
scope approval, complete copy/restore coverage, original timing and a separately
admitted storage-appropriate removal operation remain open. The exact-removal
authority and setup/execution lists remain empty. Historical qualification records
keep their old source inventories; the task-local adapter requires new LT1 source
bindings for current receipts. No old reader, lock, baseline, tolerance, public
task/SDK/GUI route or automatic native-CI gate is refrozen or expanded.

The first implementation changed shared supervisor bytes and failed six historical
MMTT reader-transition tests in both local and hosted checks. Those failed receipts
remain retained. Restoring the shared source exactly and using the task-local
adapter preserves the qualified historical identities; the corrected revision is checked separately with fresh Python process evidence.
The associated pull request records the final exact revision and full-check results.
