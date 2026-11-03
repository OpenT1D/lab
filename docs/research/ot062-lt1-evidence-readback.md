# OT-062 correlated attempt and recovery readback

PR #62 was critically reviewed on `41b4f68c03e768c11b856fc7de80831740b30571`
and merged as `af75fdabaf5295cbe77443d5dfd382dab9f235d0`, with an identical tree.
The retained full check passed 2,112 tests with 32 expected skips; all sixteen
required jobs in hosted run 41702982547 passed. Fresh review added thirty pure
start/log/owner controls and seventeen recovery/binding checks with no open
finding. These results verify the [preceding increment](ot062-lt1-prestart-recovery-probe.md).

[ADR 0102](../decisions/0102-lt1-attempt-and-recovery-readback.md) selects two bounded
read-only consumers. The two consumers are implemented in this successor. Focused fixture checks and
final exact-revision verification are recorded in its pull request. No native
runtime, storage query or actual removal is selected.

## Selected scope

Correlate exact attempt journal/process/plan files with existing engine/integration
packet bytes and the same owner, source and host-mechanism identities. Reuse the
engine-free journal reader. Preserve partial prefixes and primary process errors.
Keep all six native case families unrun until case-specific native instrumentation
exists; a normal completed attempt cannot prove confinement or universal IPC safety.

Convert a retained recovery observation into a proposed successor copy register,
compatible logical observations and retained per-copy provenance. Preserve original
clocks, holds, policy, predecessor and every copy. Unknown readbacks remain unknown.
Retain raw intervals, age conservatively from their start and never infer an exact
absence instant. Successful system queries never establish channel coverage.

## Implemented contracts

[native_readback.py](../../experiments/lt1_diagnostic/native_readback.py) exposes
`inspect_attempt`. Its externally pinned capsule and eight packet blobs bind the
three exact private journal/plan/process-receipt files. The wrapper checks the
fixed argv and root roles, owner/context, one connected acyclic owned process
tree with a single spawned entry, engine/integration grants and each
setup/host/rights/security receipt. It checks current worker/reader/launcher source
identity, selected executable inventory identity and reviewed mechanism/profile
bindings, then calls the unchanged `journal_reader.inspect`. It reads the exact
expected bytes again afterward. Relocated files retain their original attempt
and command identities. File readback requires a canonical owned private parent,
private ordinary single-link files and reviewed quiet ownership.

The result preserves the existing reader's rows, committed prefix, uncommitted-tail
count, worker finish state, effective process status and primary error. A zero
outer exit without a worker finish is a failed reconstruction. Cleanup errors,
observed signals contradicting completion, swapped grants/owners/roots or changed
source/bytes refuse. No opaque supplied reader report is accepted. Missing
pre-start journals cannot become completed attempts. The wrapper reads repository
source identities and only the three selected evidence files; it does not read the
staging payload, invoke the collector, run a worker or inspect execution grants
for admission. Externally pinned metadata does not independently prove OS truth.

All six `native_preflight.NATIVE_CASES` remain `not_run` with an explicit missing
instrumentation reason, even for a consistent completed attempt. The ordinary
journal has no case-specific native bootstrap/module/addon, process, file/network
or host-mechanism instrumentation. It cannot establish confinement, hostile IPC
safety, C15-C18 or general native-host acceptance.

[recovery_readback.py](../../experiments/lt1_diagnostic/recovery_readback.py) exposes
`propose`. All inputs are bounded byte blobs with externally expected identities;
no supplied path is opened. A reviewed mapping binds probe, collector/tool/Data
identities and existing subject/copy/channel/path selections. Only registered
live/quarantine copies can be selected. Snapshot/backup copies stay in the full
register and appear as unobserved, rather than disappearing from a denominator.

The returned `register_raw`, `observations_raw` and per-copy `provenance_raw` must
be retained privately by the caller before using their identities. Nothing is
saved automatically. The successor points to the exact current register, after
validating its own predecessor where required. It preserves every subject/copy,
original origin and evidence, hold, policy and coverage field. Only supported
present/absence states update mapped copy evidence. Known states require canonical
lexical paths and cannot contain error or partial-read metadata. Unknown readbacks leave the
registered state/evidence unchanged and remain unknown observations.

Per-copy provenance keeps the exact logical readback and both raw UTC endpoints,
plus input/context identities. For the unchanged v1 logical assessor,
`observed_at` is explicitly the whole-second floor of the interval start, a
conservative freshness anchor rather than an exact sample instant. Entire
intervals must lie within capture and be nonfuture relative to external `as_of`.
A stale lower bound cannot be rounded forward. `absent_since` is always null:
observed absence supplies neither an absence onset nor proof of timely erasure.
Unknown origins and deadline-straddling intervals stay uncertain. All four channel
coverage observations are incomplete regardless of query success; scope approval
is preserved as an external input, never inferred.

Tests use invented packets, fresh private fixture files and existing scripted
constructor rows. No LT1 engine or new OS qualification is executed. Counterexamples
exercise exact source/grant/owner/root/file binding, process failure/deadline/cancel
and partial journals, plus provenance, lineage, mapping, intervals, stale evidence,
unknown origin/hold and coverage. Agent review and fixture success do not establish
independent human reproduction or actual native/recovery qualification.

## Gates

Existing authorities remain empty. Actual setup/native execution, native
instrumentation/C15-C18, approved ordinary recovery scope, complete copy/restore
coverage, original timing and separately admitted removal remain open. Real private
payloads, host identifiers and raw receipts remain outside version control.
