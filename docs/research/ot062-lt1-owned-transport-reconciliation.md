# OT-062 owned entry transport and bundle-copy reconciliation

PR #66 was critically reviewed again and merged as
`7c6f9c20f8fae82a5cffa52b00f63745e3fc9502`, with the same tree as tested
`5719507dd9f865e8ccf461d8ecd4f06cec9defbd`. Its retained complete local check
passed 2,232 tests with 32 expected skips. All sixteen required jobs in hosted run
41817911552 passed on attempt 2. Attempt 1 retained fifteen successful required
jobs but lacked the aggregate job; the full retry changed no source or workflow.
Fresh agent reviews found no open findings, adding eleven bundle/reader cases,
eleven descriptor/error cases and meaningful guard-omission controls. These results
belong to the preceding [channel/bundle-cycle increment](ot062-lt1-channel-bundle-cycle.md).

[ADR 0106](../decisions/0106-lt1-owned-transport-reconciliation.md) selects direct
owned-process channel transport and an unsaved bundle-copy reconciliation proposal.
This increment's PR owns the final implementation and exact-revision verification.

## Owned descriptor transport

The resource adapter reuses the existing canonical supervisor code and process
owner with one task-local spawn binding. It adds no second ownership loop and
changes no shared source. The internal Python exec shim maps two inherited sockets
to descriptors 3/4, then execs a trusted entry under the same owned PID. DEVNULL
stdin, the three-key clean environment, close-fds policy and private ordinary log
remain explicit. Protocol bytes do not use stdout/stderr.
The passed exec environment is distinct from runtime initialization: the declared
macOS tooling Node adds a CoreFoundation encoding field after startup. Its raw
value stays private. The fixture observes this addition; it does not strip it,
extend the existing production observer's environment allowance or qualify the
selected native runtime, whose behavior remains unrun.

The spawn hook starts bounded channel work and returns promptly so the canonical
supervisor can enforce its process deadline. Parent intake retains a bounded frame
prefix, requires EOF, invokes trusted verification and sends one bounded ACK plus
EOF. Channel and process outcomes remain separate. A verifier is trusted local
code, never selected by packet text. Its synchronous work cannot be forcibly
preempted; bounded joining and an explicit unfinished result cannot claim callback
termination. Socket destruction requests do not independently prove peer identity
or complete native confinement.

Only the fixed invented tooling-Node fixture exercises this adapter here. The
existing native launcher and profile do not call it. There is no new selected
runtime route, automatic setup or grant list. Future native use needs separately
reviewed launch/entry/source/profile integration and exact existing admissions.
Do not substitute a nonempty registry for admission of exact request bytes. All
six actual native case families, bootstrap/phase/modules/addons and C15–C18 stay open.

## Conservative bundle-copy reconciliation

A deleted immutable bundle cannot be reopened to replay registration. Require
externally expected retained manifest/intent, base register, exact registration
successor, allocation and every copy's provenance instead. Validate their closed
byte/identity/delta/source bindings before filesystem intake. The removal request
must name that whole manifest/root/leaf and bind the same context. Use the unchanged
strict removal reader against exact journal and outer-process bytes, then recheck
source and live readback before returning.
These are snapshot observations under quiet exclusive ownership, not atomic
control over a hostile same-user writer or independent proof of supplied receipts.

Only a fully completed result may propose `absence-observed` for the explicitly
allocated new aggregate bundle copies. No older copy or object is changed.
Incomplete removal returns the supplied registration bytes unchanged and retains
their conservative `present` states. A complete successor links the registration
as predecessor; original origins, holds, deadlines, policy/context and historical
recovery horizon remain exact. No active register is saved or replaced.

The removal journal has no timestamp. These bytes do not establish `absent_since`,
timely compliance, ordinary restore coverage or physical erasure. Coverage and all
operational authorities remain false. Saving returned proposals or provenance
creates further private records requiring separate accounting. Unknown original
clocks remain unknown; the actual private pilot and restore scope remain open.

Tests use fresh invented metadata and ordinary tooling Node, never an admitted
LT1 runtime or an existing private pilot. All four production authority lists stay
empty. Added source/examples contain no actual personal names, host/account/storage
values or private record hashes. Ordinary configured Git/GitHub attribution remains public.
