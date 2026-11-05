# OT-062 entry observations and private review bundles

PR #63 was critically reviewed again and merged as
`07eb0a97c22747acb94a8ce44422794106dc5cc5`, with the same tree as corrected
`081481c86264f133f35904059e76a0be0ace4110`. Review found and fixed impossible
owned-process ancestry and contradictory known readbacks before merge. The renewed
full check passed 2,149 tests with 32 expected skips; all sixteen required jobs in
hosted run 41720121918 passed. Six ownership guard controls, an independent
125-graph matrix and thirteen recovery old/new counterexamples support the fixes.
These results verify the [preceding readback increment](ot062-lt1-evidence-readback.md).

[ADR 0103](../decisions/0103-lt1-entry-observation-review-bundle.md) selects two
bounded components, now implemented. This successor's pull request records the
final exact revision and verification. No actual native execution or private removal is selected.

## Selected entry-observation scope

Prepare a fixed producer library and one strict frame reader. The producer has
no CLI or launch route; its observation gate does not precede an already running
Node or establish a pre-model phase. Pure supplied facts remain invented. The
reader correlates a separate externally pinned parent entry PID/start/executable
observation with owner, attempt, nonce, profile and exact grants. Returned frame
bytes need later reviewed transport: the journal output must still be empty and
the current sandbox profile allows no new evidence-root writes. All six native
families remain unrun; real fixed-entry wiring and qualification remain open.

## Implemented entry protocol

[entry_observation.mjs](../../experiments/lt1_diagnostic/entry_observation.mjs)
exports `encodeInvented` and `collectCurrent`. The former always emits invented
origin. The latter requires exact observation/engine/integration hashes in the
existing execution list and the exact setup-receipt hash in the existing setup
list before packet intake or binary-fact acquisition. It checks packet-byte,
owner/attempt/profile/runtime and source bindings. Production lists remain empty;
no actual native observation was collected.

The observer records its already running process PID/PPID, executable path/hash,
version/platform/architecture, argv/execArgv, exact clean environment and producer
identity. It reports stdio unobserved. Executable/source hashing is streamed and
bounded, with descriptor/namespace readback. No supplied path is opened for
payload intake, no worker is started, and no frame is written into either native
output root. The gate controls observation, not earlier Node startup. Fixed entry,
transport, bounded observation hold and pre-model instrumentation remain separate.

[entry_readback.py](../../experiments/lt1_diagnostic/entry_readback.py) exposes
`encode_grant` for compact UTF-8 observation-grant bytes and `inspect_frame` for
one externally pinned frame, packet, parent observation and outer receipt. The
new grant rejects duplicate/noncanonical byte forms; existing packet grants are
not reserialized. Frame time is canonical millisecond UTC with calendar validation.
The bounded magic/JSON/LF/EOF frame rejects torn, duplicate or extra records.

The reader requires matching nonce, attempt, grants, profile, argv/environment,
current producer/reader identities and selected executable. The parent record's
owner is distinct from its observed entry: exact integer PIDs, the same externally
observed entry start and executable, and the retained receipt's single rooted
acyclic process tree must agree. No Node uptime substitutes for an OS start token.
It reads canonical public source identities, but no private path or OS process
collector. External expected identities establish consistency, not independent
truth or liveness. Repeated historical readback is supported; a nonce/attempt
mismatch is refused without inventing a global anti-replay authority.

The result's `entry_binding_consistent` does not establish pre-model phase, stdio,
live owner or terminal attempt completion. Those flags and all native-host,
acceptance/setup/execution/removal flags remain false. All six native families
remain `not_run`, even for consistent observed-kind input. The existing full
attempt reader and actual admitted host instrumentation remain separate.

## Selected private bundle scope

Save exact bounded recovery inputs, proposals and per-copy provenance under a
new private flat manifest. Preserve original clocks, holds and predecessor; keep
unknown origins unknown. An intent precedes copied inputs. Exclusive publication
and readback preserve failure prefixes and uncertain durability. Reopening checks
external manifest/current-register/context identities, original replay and a
separate nondecreasing current assessment. No active register or private pilot is
replaced automatically.

Only the entire own closed bundle may supply a proposed exact removal request.
Store request/context/journal elsewhere and capture signatures after the last
publication/readback step. No partial request for an existing evidence directory
is inferred from a point observation. Actual removal admission, complete ordinary
restore coverage and effective erasure remain open.

## Implemented durable bundle

[review_bundle.py](../../experiments/lt1_diagnostic/review_bundle.py) supplies
`save_review_bundle`, `inspect_bundle` and `prepare_removal_request`. Save replays
`recovery_readback.propose` from bounded supplied bytes before filesystem intake.
Only a fresh canonical private directory outside the checkout is accepted, with
0700 directories and 0600 ordinary single-link members. Fixed flat filenames,
manifest identities, inherited subject origins/holds and provenance remain within
the existing removal file-count/byte bounds.

An intent is fsynced before input/proposal copies. The manifest is last, then
expected-byte readback, source recheck, exclusive rename and parent fsync complete
publication. Cancellation/failure retains the pending prefix; a rename followed
by uncertain fsync/readback retains the published map with an uncertain result.
No automatic cleanup, overwrite retry, active-register pointer or admission update
occurs. A complete pending map cannot masquerade as the intended published leaf.
Readback establishes byte/namespace/replay consistency, not independently proved
fsync durability or hostile-owner isolation.

The reader requires external expected manifest/current-register/context hashes.
It reconstructs original stored inputs and proposal at the stored `as_of`, then
computes a separate current assessment at an external nondecreasing `as_of`.
Current assessment never replaces stored bytes. Known original clocks and holds
remain exact; unknown stays unknown. Saving creates additional private copies:
`new_bundle_copy_registration_required` stays true and
`global_copy_coverage_verified` stays false. The historic input register's coverage
does not become a global claim about the saved bundle.

Removal preparation snapshots the entire own closed bundle after publication and
readback, including manifest and intent. It returns unadmitted request bytes with
exact root/file/source/context identities using the existing removal schema.
Request/context/journal must remain outside the target; adding anything to the
bundle invalidates its closed inventory. The actual empty removal authority
refuses the prepared invented request while retaining every member. No actual
private pilot, backup, snapshot, key or payload was removed.

Tests use only invented frames, source-bound fake process facts and fresh private
file fixtures. Targeted cases cover canonical UTF-8/time, replay/identity and frame
boundaries, plus proposal replay, clocks/holds, namespace races, interruption,
publication uncertainty and closed-authority request refusal. These are software
checks; actual native fixed-entry execution, phase/confinement/C15-C18, approved
ordinary recovery scope and complete copy/restore/effective-removal evidence stay
open. Full results belong to this increment's exact-revision PR record.
