# OT-062 simglucose audit-1 consumer and bootstrap fixtures

## Status and boundary

The new `experiments/simglucose_audit/` component implements the sampled audit-1
consumer, a fixed invented-engine bootstrap and an independent engine-free
reader. It uses only the Python standard library. It is software preparation
for the [adapter audit](ot062-adapter-audit.md) and
[runtime/rights proposal](ot062-runtime-rights.md), not a native simglucose
adapter, direct/wrapped parity result or host qualification.

All setup, execution, removal and export gates remain unchanged. Native execution
is postponed. `bootstrap.run_native` always refuses before decoding input,
following a supplied path, importing selected dependencies or constructing an
engine. There is no factory, plugin, callback, module-name or resource-path input
to the fixture bootstrap. Existing M1/P1/M2 allowlists are unchanged.

The fixed `source-contract.json` records public metadata from the previously
reviewed manifest proposals: simglucose revision
`a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, 17 selected Python modules including
seven package initializers, three whole-file CSV requirements and the scientific
consumer/bootstrap proposal. It contains no CSV contents, private evidence paths,
role records or operational grants. Source metadata and published notices do not
establish rights to use the parameter/device assets. Quest remains excluded from
the consumer; absence from a future built artifact is still unproved.

## Executable fixture contract

The built-in fixture has eleven explicitly invented CGM values and ten modeled
delivery rates. Delivery is scripted independently of the commanded rate; the
fixture does not simulate glucose, meals, pump quantization or sensor noise.
The fixture basal is 1.2 U/h, not a calculated native basal.

| Boundary | Implemented behavior |
| --- | --- |
| Clock | Ten three-minute intervals, commands at 0 through 27 minutes, eleven observation points through minute 30. The terminal point issues no command. |
| Release queue | Delay the minute-9 observation until minute 15; mask minutes 12 and 15 after generation. Select the newest measured eligible observation, never an older released replacement. Keep raw observations separately. |
| Controller | Memory starts at 120 mg/dL. On a fresh sample compute `clip(b + 0.01 * (previous - 120), 0, 3)` U/h before updating memory. Held observations command basal and leave memory unchanged. |
| Action boundary | Call the scripted engine with commanded U/h divided by 60 as basal U/min and zero bolus U/min. Record the actual received arguments separately from the consumer's command journal. |
| Delivery | Sum only returned interval delivery rates times three minutes, as exact rational values of the serialized rates. A pending failed command has no delivered amount. No intervals means unknown amount, not zero delivery. |
| Announcements | Deliver one invented announcement ID at minute 15, except in the fasting variant. The controller ignores it. This does not implement native meal ingestion. |
| Lifecycle | Fresh state per bootstrap, explicit reset/step/close counts, scripted observation consumption and cursor, distinct initial-history and reset-return channels. Counts describe this interface, not native RNG consumption. |
| Failure | Preserve reset failures, interrupted/failed prefixes, pending commands, early terminal replies, terminal diagnostic tails and separate primary/cleanup errors. A cleanup failure cannot remain completed. |

The four identified variants are `filtered`, `unfiltered`, `future80` and
`fasting`. The `future80` label carries the proposed native negative-control
identity; it does not create an 80 g meal or a native trajectory. Fixture checks
establish information-prefix invariance with supplied data only. Actual native
40/80 g meals, the eating queue and the distinct 20 g announcement remain part
of the separately gated native case plan.

`reference.py` independently enumerates eligible samples and reconstructs every
row, actual action argument, scripted count, status and amount. It does not call
the consumer, release queue or scripted engine. Controller arithmetic uses exact
rational intermediates with a binary64 rounding step after each declared
operation, independently reproducing the consumer's ordered Python operations.
For example, the fixture command after prior memory 180 is
`1.7999999999999998`, not an exactly represented 1.8. No tolerance is widened.
The earlier Decimal fixtures, native references, frozen baselines and lockfiles
are unchanged; this new executable fixture does not revise their criteria.

## Bootstrap and reader

`run_fixture(raw)` accepts bounded JSON bytes of the exact invented fixture
schema. Duplicate keys, nonfinite numbers, numeric booleans, unsupported fields
and native/factory inputs are refused before constructing the scripted engine.
It records the configuration byte hash and hashes of the fixed local package,
reference and source contract. The parent `experiments` namespace must have its
expected path and no initializer. Source identity is rechecked after execution.

`inspect_fixture(report_raw, expected_report_sha256, config_raw,
expected_config_sha256)` requires externally supplied byte pins and the current
trusted local source identity. It reconstructs the complete expected fixture
report and rejects extra fields, forged completion, changed source/authority,
wrong unit arguments, observation consumption and partial-prefix contradictions,
even when a changed report is rehashed. It imports no engine or supplied code.
Its summary always identifies invented evidence and denies native acceptance.
These cooperative source/byte checks are not protection against a hostile Python
process and provide no owned-process, confinement or genuine native outer evidence.

`inspect_proposals` accepts the three historical manifest byte buffers and an
externally pinned bundle index. It checks the acyclic asset/bootstrap/consumer
hash bindings, exact selected code and resource metadata, excluded assets,
notices, scientific semantics and closed proposal authorities. Source-file labels
are opaque strings and are never opened. The result stays **blocked**: the old
proposal's implementation flag is historical and supplies no native admission.
Retention fields are checked as inherited proposal metadata, not as a live
expiry decision or permission to retain, extend or delete anything.

## Engine-free use and verification

With the already prepared root tooling environment, from the repository root:

```sh
uv run --locked --no-sync --offline python -B -m experiments.simglucose_audit fixture
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_audit tests.test_adapter_audit
```

The first command writes only invented fixture JSON to stdout. It does not save
or export private evidence. The fixed `native` CLI mode exits with refusal; no
native launch command is implemented. The new fixture module tests causal release,
units, independent arithmetic, modeled amount, reset/repeat behavior, failures,
actual scripted arguments/consumption, input and source drift, reader forgery,
proposal drift and dependency-import traps. The existing adapter-audit tests
remain part of the bounded regression check.

This increment's verification uses existing locked tools without synchronization
or installation, targeted Python tests and repository style/documentation checks.
The full root suite includes Node/process/host experiments and is not evidence
from this postponed native task. Report its unrun scope explicitly. Local fixture
checks and agent review are neither hosted CI nor independent human reproduction,
native numerical parity, biological validation or effective-erasure evidence.

## Passive source and runtime-lock review

`runtime_sources.py` adds a reusable standard-library inspector for the exact
seventeen source buffers and the two predecessor native/build lock byte buffers.
All source sizes/SHA-256 values and both lock hashes must match the fixed public
source contract **before parsing**. Empty package initializers are valid members.
The caller supplies bytes, never a source, package, cache or artifact path to open.
No selected source is imported or executed; no dependency is resolved, installed,
built, fetched or pruned. A source/lock mismatch refuses the entire inspection.

| Evidence now checked | Boundary that remains open |
| --- | --- |
| All 17 Python buffers and seven package initializers match the manifest. Conservative traversal from the six fixed entry modules reaches that inventory. | This is selected source syntax, not a full Python/native runtime or effects closure. |
| Thirteen distinct external import targets remain listed, including guarded and demonstration imports. The package initializer's Gym registration and the three literal resource calls remain visible. | Gym/package registration effects, EntryPoint loading, actual rllab absence and external package source/initializers are not observed. |
| Lexical contexts preserve if/try/except, class/function bodies, decorators and defaults. Top-level Matplotlib imports remain visible alongside the patient's demonstration import. | Context does not solve Python execution order, arbitrary aliases, reflection or dynamic imports. `animate=False` cannot justify discarding these import requirements. |
| Every predecessor native/build package row is retained: 34 native plus eight build packages, each lock with one separate virtual project. Dependency markers remain data; artifact records and complete package records receive metadata hashes. | No wheel/platform/ABI is selected and no artifact bytes, vendor code, interpreter, OS library or build result is qualified. GlucoSim, Gymnasium and pathos remain in declared lock scope even when the selected source route does not import them. |
| The three whole-file resource requirements and their missing hashes/use decisions remain in the report. Quest is outside this consumer's literal resource calls. | No CSV is read; consumer exclusion does not establish Quest exclusion from a built package, title to assets or permission to use them. |

`analyze_python` and `analyze_lock` are syntax helpers, not general-purpose Python
or dependency resolvers. The lock helper conservatively refuses ambiguous names,
dangling or contradictory dependency identities and unsupported package fields,
including optional-dependency structures it does not interpret. The bound
inspector only admits the exact two predecessor byte identities as metadata;
it neither edits those locks nor creates a new OT-062 lock. Recorded predecessor
package versions do not imply a current security or vulnerability assessment.

`inspect_runtime_sources(source_buffers, native_lock_raw, build_lock_raw)` emits
an explicitly **blocked** metadata report with all operational authorities false
and native postponement true. Its nine blocker categories preserve the required
interpreter/runtime/import/build/artifact, asset/right, bootstrap/parity and
setup/host/execution work. `inspect_runtime_report` requires an external report
byte pin and recomputes the exact report from the same bound input buffers using
trusted local inspection code. It rejects rehashed changes, omissions or authority
promotion. This is deterministic cold metadata reconstruction, not an independent
native oracle or protection against a hostile process.

The local implementation checks the original retained source text and locked
metadata passively; public tests use invented code and TOML and never import the
engine. The package's source identity now also includes `runtime_sources.py`, so
earlier fixture receipts keep their earlier implementation identity. No frozen
numerical baseline or scientific tolerance changes. To run the bounded combined
Python checks with existing tooling:

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_runtime_sources tests.test_simglucose_audit tests.test_adapter_audit
```

## External bootstrap sources and runtime/rights proposal — 9 November 2026

A separate passive review now binds 38 registry archives from the two unchanged
predecessor locks: 32 native registry roles and eight build roles with two shared
package/version pairs. The two native VCS roles remain outside this new artifact
intake. All 38 downloads match their locked SHA-256 and size, totalling 77,139,911
bytes. These are source-inspection candidates, not an installed or admitted
runtime. Gym and multiprocess are sdists; no new build result is available.

The review retains archive inventories, selected Python/notice text, primary and
vendored metadata and a concrete private runtime/rights proposal. It identifies
79 notice members, twelve setuptools vendor-metadata records and 55 declared
License-File references bound to notice members. This is not exhaustive native,
font, build, asset or legal title clearance. The 229 native-library inventory
rows are metadata, not a count of independently authenticated unique libraries.
The archive reader bounds exact hash-pinned inputs and selected output; it does
not claim generic hostile ZIP/PAX/GNU/decompression-bomb protection. No package
code, native member or `.pth` text is executed and no archive member paths are
materialized. No simglucose/GlucoSim parameter, Quest or device payload is acquired.

| Exact source finding | Consequence for a future bootstrap |
| --- | --- |
| Gym 0.9.4 parent calls dependency checks importing NumPy, requests and six, and imports distutils, core, envs, scoreboard/upload and wrappers. | Its parent is broader than registration. An imported upload callable is not evidence that an upload occurs; network/upload use remains forbidden. |
| Gym registration imports `EntryPoint`; its `load(name)` performs parse/load, reached by `EnvSpec.make`. Registering builds `EnvSpec` without itself resolving the target. | An import-only compatibility symbol is a bounded proposal. `parse`, `load` and `gym.make` stay closed; native compatibility remains unmeasured. |
| `_distutils_hack` can import the setuptools parent and `_distutils`, inspect the working directory, change finder/module state; setuptools extends `sys.path`, removes `backports` and applies monkey patches. | The hook is not a neutral, fully reversible context. Do not import the existing M4 compatibility module wholesale or run it in the controller/reader. |
| Matplotlib pyplot imports font management; a matching cache can return early, but cache miss/error/mismatch constructs a manager. That path can use timer threads, system font discovery, `fc-list`/`system_profiler`, native font loading and cache locks/writes. | Agg/private `MPLCONFIGDIR` is not confinement. Qualify real host denies and the allowed bundled data/cache needs; no such execution occurred in this review. |

Gym's [exact PyPI sdist](https://pypi.org/project/gym/0.9.4/) contains no detected
notice and its PKG-INFO license is UNKNOWN. A separately recovered
[historical upstream notice](https://github.com/openai/gym/blob/b5576dc23a5fcad0733042ab2ad440200ebb6209/LICENSE.md)
contains MIT code terms and distinct MuJoCo model attribution. Comparing that
Git tree with the sdist matches 134 of 136 Python members; `gym/__init__.py` and
`gym/version.py` differ. This is partial provenance, not exact publisher/build
authentication, independent title verification or a blanket whole-archive MIT
asset decision. Setuptools' own license likewise does not replace its vendored
notices, which include LGPLv3 and other distinct terms.

The source analysis covers 1,109 core/initializer AST records; 525 layout/grammar
gaps remain, chiefly multiprocess version subtrees. It does not close all external
import/effect paths. A new [OSV batch observation](https://google.github.io/osv.dev/post-v1-querybatch/)
for 51 public artifact/vendor package-version labels and two Git commits returned
53 empty results without pagination. This is a dated query result, not safety,
rights, native/OS/interpreter or unlabelled-vendor assurance.

The concrete technical direction remains a **proposal**: a standalone bootstrap
in a fresh owned worker per attempt, exact three-resource binding and an
import-only `EntryPoint` whose parse/load refuse. Preserve the upstream numerical
sources. Qualify explicit denies for unnecessary network, subprocess and system
font/config access with only the reviewed bundled resources and private cache
allowed. Worker exit is the lifecycle boundary for import mutations; do not
claim shim rollback. An incompatible import/denial/parity stays failed or
incomplete. Expanded permissions, a source refactor or a cache shortcut require a
new reviewed identity and never follow automatically.

The private human/machine package fixes the exact artifact/notice roster,
source findings, nine blocker categories and later decision order. It remains
ineligible for admission and not ready for approval: no new interpreter/project/
lock is selected, Gym/asset/native/build rights remain incomplete, and no actual
setup, host or execution receipt exists. A later rights decision does not accept
runtime risk or open setup; setup does not lift native postponement. Existing
LT1 rights/M4 admissions do not transfer. All gates and native postponement remain.

## Parallel runtime/rights and worker increment — 9 November 2026

Three bounded tracks were completed in parallel and integrated with a separate
root diff/counterexample review. None installs a runtime, reads an asset payload
or changes an operational admission. Historical private proposals and their
as-of source identities remain unchanged.

The LT1 track rechecked the official Node release index, latest-22 checksums and
November announcement at 19:36:23–25 UTC. The observed latest 22 release remains
22.23.4; no successor was observed. This is availability metadata, not new archive,
signature, binary or build authentication. Its separate ts-node source review
traces compiler loading through `attemptRequireWithV8CompileCache` into
`v8-compile-cache-lib` 3.0.1. Conditional installation can read cached BLOB/MAP
data, replace a compile hook and attempt lock/cache writes at uninstall. No cache
was visited or selected runtime code executed. An optional future `DISABLE_V8_COMPILE_CACHE`
choice is a new environment/source/profile/reader identity to review, not a
current change or proof that every Node cache is disabled. Copied ts-node
internals, embedded/vendor/build provenance and actual loader-thread behavior
remain separate from the forthcoming Node fixes.

The rights track explains both Gym byte differences exactly: the sdist removes
one contiguous historical logging-configuration block and changes version
0.9.3 to 0.9.4. The official repository serves the exact 0.9.4 version blob,
`a482f45003fdced4924e9406f5cfc2d860f33ee6`; no matching release commit for both
sdist differences was established. Historical 134/136 correspondence is retained;
understanding the edits does not authenticate the publisher/build.

The three resource blob identifiers/sizes match the visible original simglucose
root-commit tree metadata. The MIT notice was added later in that repository.
Current pinned MIT terms remain a concrete possible basis for a bounded published-
notice reliance decision; later addition does not mean the current revision has
no license grant. Original table ancestry/title is not independently established.
Payload SHA-256 values remain null, no whole CSV is read and no rights decision
or built-artifact exclusion follows from metadata continuity. No independent
title proof is imposed as an automatic requirement for every future reliance
decision; the actual provenance limitations must be explicitly assessed.

### Fixed engine-free worker

`worker_fixture.py` now runs one fresh, fixed standard-library Python child via
the unchanged shared process owner. Strict invented JSON intake precedes source
reads/spawn. There is no caller-selected command, module, callback, engine or
path. The fixed child uses `-I -S -B`, a trusted source root and bounded request/
ready/result/finished framing. Package/worker identity, exact request bytes and
the three process-owner source files are bound separately. The package source
inventory now includes the worker; earlier receipts retain their earlier identity.

Input backpressure and output reading run in joined I/O threads under one
five-second protocol deadline, with startup time charged to that same budget.
Afterward, live owned stop has a separate one-second wait; both joins share one
additional one-second window. These are cooperative fixture controls, not a
guarantee that arbitrary kernel/spawn calls or hostile processes are preemptible.
An already reaped fixed child is not signalled again. An unexpected remaining
group after exit is incomplete cleanup, without adoption or new signal authority.

Complete, cancel, deadline, before-read backpressure and finish-then-block cases
retain the actually returned fixture/pending prefix. A complete scientific
journal and finished frame do not replace process exit. Primary fixture errors,
diagnostic errors and transport/cleanup errors remain distinct. The cold reader
recomputes the independent fixture oracle and checks byte/source/owner/protocol/
status consistency without running the child or consumer. Serialized transport
facts are cooperative fixture reports, not authenticated outer/durable-journal
evidence or independent reconstruction of actual process history.

Network, subprocess and system-font denial modes only emit invented refusal
events; they never attempt those operations. Host-precondition states are also
invented. Even an all-`invented-pass` requirement set remains blocked, with no
host/native qualification or authority. Native `bootstrap.run_native` continues
to refuse unconditionally before input/source/path intake or construction.

The integrated Python test set now includes the worker module:

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_worker_fixture tests.test_simglucose_runtime_sources tests.test_simglucose_audit tests.test_adapter_audit
```

The Node successor, exact native interpreter/lock/artifacts, whole-resource
intake/use decision, standalone native bootstrap and real host/process/native
qualification remain open. The 32 planned LT1 attempts remain unrun; this
engine-free worker adds no native attempt or two-engine acceptance. Setup,
execution, export, removal and retention decisions remain separate.

## Review candidate: durable fixture journal and bounded compatibility

A further three-track increment freezes one source candidate and separate private
D-RUNTIME, D-INTAKE and D-RELIANCE decision descriptors. These remain proposals;
none changes an admission registry. The prior observations above retain their
original revision and as-of limits.

`worker_journal.run_journal_fixture(request_raw, destination)` first validates the
strict invented request, then creates an exclusive private directory without
symlink traversal. The direct caller supplies a trusted absolute output path;
JSON cannot select paths, commands, modules or engines. A concrete internal sink
records the request, package/owner identities, actual parent/child PID observations,
raw frames before parsing, and ordered lifecycle events. Exclusive files and a
hash-chained, fsynced event stream preserve available prefixes. No saved PID is
used for control or adoption. Process ownership still uses the unchanged shared
helper and the fixed standard-library child, never a native engine.

Only completed scientific reconstruction, actual exit zero, observed owned
cleanup, both joined I/O threads and successful journal finalization can issue a
successful producer manifest pin. Completion publication uses an exclusive hard
link from a fsynced staging file; both names are retained. A marker pathname alone
is insufficient: a subsequent fsync/close failure can leave it visible without
an issued success pin. Sink failures stay diagnostic and cannot replace an
existing worker primary error or skip its owned stop and joins. Available raw
frames and worker failure/pending prefixes remain evidence, never success.

`read_journal(destination)` only loads bounded fixed-roster regular files without
following symlinks. `inspect_journal` requires the caller-held manifest pin from
the successful producer return, plus the request pin, and independently checks
bytes, source, event order, lifecycle consistency and the existing scientific
oracle. Computing a fresh pin from an untrusted marker is not that external trust
context. `inspect_journal_prefix` checks a separately pinned crash prefix and
always returns incomplete, including a torn trailing record or stray marker.
Readers never spawn a child or import selected runtime dependencies. These are
cooperative controller observations, not authenticated OS history, hostile-process
confinement, actual native host qualification or scientific validity.

`compat_fixture.py` supplies exactly three fixed invented byte buffers with the
resource labels and an importable `EntryPoint` symbol. It accepts no actual asset
paths or alternative payloads. `parse` and `load` refuse unconditionally before
using arguments. No `pkg_resources`, `_distutils_hack`, Gym registration or module
registry mutation is performed. This fixture checks the limited proposed API;
it establishes no production package compatibility.

The private runtime proposal selects CPython 3.12.16/PBS 20261026 Darwin arm64
**published source/build metadata**, a separate proposed OT-062 project, and the
unchanged 34 native/eight build predecessor roles. Actual executable, new locks,
artifact/build/ABI/security/notices and setup/host receipts remain absent. The
LT1 cache-disable environment is likewise a separately versioned successor
proposal; no active ENV or historical source identity changes.

D-INTAKE specifies one later passive acquisition of exactly three pinned whole
CSV objects, 18,161 accepted bytes and a total 18,164-byte read cap including
rejection sentinels. No body was read and no payload SHA-256 is invented. Its
terms were reviewable; that earlier candidate did not yet implement or qualify
the actual HTTP collector.
D-RELIANCE separates current source/notice reliance questions from later exact
whole-file/runtime/artifact-notice bindings. Complete material-use approval is
not yet ready. Neither descriptor transfers LT1/M4 permissions, accepts runtime
risk, opens setup/execution/export/removal, resets retention or lifts native
postponement. Private decision/evidence locations and personal identities stay
outside this public guide and Git.

Bounded integrated checks use the existing root tooling only:

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_worker_journal tests.test_simglucose_compat_fixture tests.test_simglucose_worker_fixture tests.test_simglucose_runtime_sources tests.test_simglucose_audit tests.test_adapter_audit
```

This command includes invented journal filesystem/process fixtures, not asset
inspection, installation or native execution. Retain their private evidence under
the applicable limits; these tests perform no removal action. Full root, Node,
actual host/native and hosted checks remain separate and unclaimed here.

## Bounded passive three-resource collector

The next increment prepares the separately authorized three-CSV intake. It
implements a bounded collector and qualifies its contract with **invented
fixtures only**. It acquires no actual resource, installs nothing and changes no
existing setup, execution, removal or export gate. Native execution remains
postponed; the 32 LT1 native attempts remain unrun.

The source fixes the three public URLs/revision, sizes, Git-object identifiers,
notice identity and limits. A future operational plan binds the exact current
source, private output and inherited limits; a separately held approval byte
identity must bind that plan and allow passive intake alone. These are trusted
private controller inputs, not self-issued authority supplied by a result.
No real approval is created by fixture construction. The ordinary entry refuses
without evaluating arguments; the approved low-level route must validate its
complete plan/approval/origin context before opening a destination or network.

The HTTP route uses fixed standard-library TLS/HTTP logic with certificate and
hostname verification. It sends only the fixed GET/Host/path and required headers;
there is no proxy, authentication, cookie, redirect, retry, range, mirror or
compression/text decoding route. Response headers and body reads are bounded;
unsupported transfer framing and ambiguous length/coding reject before acceptance.
Raw reads preserve the rejection sentinel instead of allowing Content-Length to
hide extra bytes. An exact-sized body must match its known Git object before its
first payload SHA-256 is accepted. These checks are byte-level acquisition, not
CSV parsing, research use, original title or publisher authentication.

The three accepted bodies total 18,161 bytes. Reads permit at most 18,164 body
bytes, including one rejection sentinel per target, and stop the action on the
first failure. Per-request 30-second and whole-intake 90-second budgets include
startup and transport; owned supervision and finalization checks are separately
qualified with stalled invented operations. The 90-second window cannot issue late success. After a controlled failure,
a separate two-second owned recovery may preserve already published opaque
prefixes and failure metadata, with bounded owned stop/I/O joins. Every operation
must remain before the same earliest approval/retention deadline; production
intake requires at least 100 seconds of headroom before touching the output.
The limits do not assert that every kernel call or process cleanup is preemptible
on an unqualified host. Real DNS,
TLS peer/trust and GitHub response behavior are not observed by these fixtures.

Output is fresh, private, exclusive and nofollow. The pinned notice is preserved
before body acquisition. Each target has at most one opaque body pathname;
partial/rejected bytes remain evidence and never become accepted solely because
of their name. Their stored-file SHA-256 may record forensic integrity; the
accepted payload SHA-256 is set only after exact size and Git-object agreement. Complete versus failed/incomplete metadata remains explicit.
No automatic removal, overwrite, resume or retry follows a crash or rejection.
Recovery runs only after confirmed owned cleanup; a live/unjoined predecessor
prevents another filesystem phase.
The retained intake root is bounded to 84,752 bytes: body/sentinel bounds plus
1,052 notice bytes and at most 65,536 receipt bytes. Successful finalization and
a caller-held producer receipt pin are required for completed cold reconstruction.

The cold reader reconstructs lengths, object/hash identities, file closure,
source/plan/approval/origin bindings and closed non-intake authorities from
bounded bytes. Fixture reports remain identified as invented and grant no real
intake or native authority. Filesystem/process interruption and durability claims
are limited to the observed controls; abrupt controller loss can lose unpublished
or not-yet-stored bytes and leaves incomplete evidence.

With the existing locked root tooling, the added bounded checks are:

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_intake_collector tests.test_simglucose_worker_journal tests.test_simglucose_compat_fixture tests.test_simglucose_worker_fixture tests.test_simglucose_runtime_sources tests.test_simglucose_audit tests.test_adapter_audit
```

These tests retain invented evidence outside Git and perform no target removal.
The byte caps describe application-consumed HTTP bodies, with separately bounded
HTTP headers; they do not bound all TLS/OS buffering, protocol overhead or DNS
traffic. Conservative internal framing limits can reject a transfer and never
trigger a broader retry.

The private approval package fixes the exact proposed destination, source/plan/
qualification pins, single-action scope and retention conditions. New technical
facts remain under the inherited maximum 30 days and absolute 6 December 2026
cap, with earlier limits winning and no old origin reset. It creates no new
personal identity/role record. Actual acquisition still requires the separate
explicit approval; runtime/material use, setup, host/native qualification,
export and removal remain separate.

## Review candidate: proposed host controls and cold reconstruction

`host_qualification_fixture.py` renders a logical Darwin arm64 host-control
proposal from externally held candidate bytes and two trusted, disjoint absolute
POSIX role roots. It supplies exact proposed argv, eight replacement environment
keys, eight output paths and twelve matched controls: an allowed reference and a
denied profile case for file, network, IPC, process, loader and addon effects.
No path selected by candidate JSON is opened. The proposed executable and probe
paths are roles only; the actual probe entrypoint and OS policy are not
implemented. Private Matplotlib configuration and `Agg` do not establish
confinement. Proposed deadlines and byte limits are not qualified enforcement.

The request schema binds the profile, current core and local host-fixture source
identity, and existing process-owner sources without changing prior intake
identities. Actual executable, setup, OS/ABI, probe, witness, owner/boot/context,
rights/risk and qualification-grant identities remain missing. Candidate metadata
is an opaque identity, never admission. `run_host_qualification()` refuses before
using arguments, source or paths.

The invented-only producer and independent cold reader cover nine fixed cases:
completion, cancellation before start and after two controls, deadline, primary
error, combined primary/cleanup error, cleanup error, denial mismatch and crash.
The reader reconstructs source/input/owner bindings, control order and results,
pending prefixes, explicit cancel/deadline/error observations and cleanup/join
accounting. Rehashed authority promotions, malformed order, false cleanup and
trailing bytes after a terminal result are refused. Incomplete prefixes remain
incomplete. Invented owner tokens are never authority over saved PIDs; no host,
socket, process, loader or addon probe is launched by these fixtures.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_host_qualification_fixture
```

Private project proposals preserve 34 native and eight build roles, the two VCS
revisions and prior notice metadata in two inert pyprojects, constraints and four
outer build recipes. They provide no new lock, environment, backend-hook
qualification or output receipt. Offline/no-index flags do not confine builds.
Lock resolution may retrieve complete snapshots/assets and execute backend or
package metadata code; it requires its own exact scope and any applicable lift
of the execution postponement. A passively reviewed runtime's published checksum
or attestation statement does not establish locally verified archive bytes,
cryptographic authentication, executable identity or host compatibility.

## Review candidate: opaque runtime intake preparation

`pbs_intake.py` separates a future, explicitly approved opaque-copy action from
archive interpretation. Its ordinary `run_intake()` entry refuses before using
arguments. The explicit `collect_approved()` boundary requires externally held
plan, approval, origin, rights-basis, source, process-owner and physical-root
pins. Invented approval construction cannot admit a production action. A private
exclusive consumption marker precedes allocation/network work; a partial output
or renamed output never supplies automatic retry authority.

The fixed proposal is one CPython 3.12.16/PBS 20261026 Darwin arm64 object. It
permits at most two GETs and one strictly checked publisher redirect, bounded raw
HTTP headers and exactly the published size/digest, with one rejection sentinel
byte. It has no proxy/auth/cookie/range/mirror/retry/decompression route. Invented
raw responses exercise the same framing parser; actual DNS, TLS, CDN responses
and production-duration operation remain unobserved. HTTPS endpoint validation
does not establish artifact signature authentication.

The producer hashes only bytes acknowledged by successful writes, then requires
fsync, physical namespace checks, current source/approval/origin checks and clean
owned process/reader/writer closure before success. There is **no retained-body
readback**. Receipt validation reconstructs metadata; it cannot claim a fresh
hash of persisted bytes. Failure retains the single already-written disk prefix
and, when safe and timely, bounded metadata with unknown digest. In-flight
controller/pipe/TLS/kernel buffers may be lost. Recovery requires confirmed owned
stop; it never deletes, repairs permissions, retries or creates a second body.
Request and whole-action deadlines include reserved cleanup/recovery time but
are not hard guarantees against uninterruptible kernel work.

The origin context's four rows describe new observation/proposal facts only.
They neither reset referenced material origins nor declare unknown older
materials timely. Earlier inherited retention limits and every other gate
remain in force. The private copy proposal has its own limited publisher-
metadata reliance and explicit embedded-license/membership uncertainty; the
accepted three-CSV assessment supplies no runtime-archive permission.

`pbs_archive.py` separately qualifies a strict invented gzip/ustar subset with
smaller fixture budgets. It rejects malformed framing/checksums, unsupported
extensions and sparse/device types, path/Unicode/case collisions, unsafe links,
trailing streams and decompression/member/inventory bounds. The cold reader
reconstructs reports from caller-owned invented bytes. It extracts nothing,
returns no notice/member text and keeps actual grammar/authentication/use claims
false. Its invented marker is not proof of provenance against a malicious
caller. `inspect_archive()` refuses before input, path or source access. These
fixtures do not qualify the real PBS grammar or the larger proposed real-reader
limits.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_pbs_intake tests.test_simglucose_pbs_archive
```

These checks use invented bytes and controlled root-tooling Python children;
they do not install, build, download, run a selected native runtime or read a
real asset/archive payload. Actual signature/certificate/identity/signing-time/
log validation requires separately reviewed verifier and trust-root identities.
The proposed opaque intake grants none of that inspection. A concrete private
approval must bind the exact tested source, target, destination, bounds,
one-action conditions, copy basis and earliest retention deadline.

## Review candidate: conditional phase-B authentication and inspection

The separately approved opaque PBS intake has a private receipt for the expected
size and producer-observed acknowledged-write SHA, with fsync/stat and no body
readback. That historical observation supplies neither fresh stored-body
integrity nor cryptographic authentication, member-inspection or reuse authority.
The original archive remains outside these preparation tests.

`pbs_auth.py` checks fixed invented context, policy and two-statement semantics,
including the different provenance/release subject names. Its nine hypothetical
controls cover signature, chain, identity, signing time, log, trust freshness,
rotation, source and self-hosted-builder disposition. A positive fixture still
reports actual cryptographic verification, authentication admission and execution
readiness as false. Rehashed booleans or receipts cannot populate missing real
verifier/trust policy fields. The cold reader reconstructs the control metadata;
`verify_archive()` refuses before argument, source, path or tool use.

`pbs_inspection.py` creates a fresh private file from caller-owned invented bytes
and holds one descriptor across two read passes and EOF probes. Only after the
first opaque digest/count and eligible invented authentication controls may it
rewind that descriptor, perform the second read and project bounded headers.
Before/after observations bind the descriptor, filename and private directory;
source, owner, mode, link count, expiry and changed-content failures preserve
incomplete accounting. Cold reconstruction checks stage reachability: a denied
or pending authentication cannot acquire a partial second-pass observation.
Physical token history is reported as fixture observations, not authenticated
OS history.

Fixture staging writes the supplied invented buffer once and checks its RAM
identity in addition to the two descriptor reads. The unchanged marker-strict
`pbs_archive` parser drains and internally hashes invented member bytes; the
phase-B projection returns no member hashes, member/notice text or extracted
files. Opaque decompression/draining consumes bytes, including any notice/asset
bytes; absence of text selection does not mean zero payload access. The smaller
fixture ceilings and logical checkpoints do not qualify a production reader's
larger proposed limits, watchdog, storage or actual archive grammar.
`inspect_archive()` remains unconditionally closed before any real input use.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_pbs_auth tests.test_simglucose_pbs_inspection
```

The conditional real proposal requires one first opaque stored-byte digest pass
and one authenticated same-descriptor inspection pass, with explicit compressed
read/EOF and decompressed drain limits. Unknown grammar must fail closed; prior
inspection of the original archive is not a prerequisite for qualifying that
supported grammar with invented fixtures. Notice-text and static member
selectors remain empty. New material-read scope, independent trust/bootstrap,
verifier/source/dependency/identity/time/log policy, bounded production I/O and
an exact new approval are all still required.

An installed GitHub CLI candidate was first assessed through package metadata
and local official manpages. A separate passive fingerprint binds the existing
binary's identity without executing it; this proves no source/build/dependency
correspondence or cryptographic qualification. The documented verifier takes an artifact path;
its possible hash/reopen operations cannot silently be called digest-only or
metadata-only within the two-pass budget. A qualified compatible adapter or a
separately reviewed different read strategy is needed. No verifier command was
executed, and no cache/keychain material or archive body was read in this work.
No concrete independent trust snapshot is currently held. This is a reviewable
conditional package, **not a ready operational approval request**. The opaque
copy, CSV, LT1 and other historical permissions do not transfer to phase B.

## Review candidate: verifier source discovery and full-ceiling reader

The next preparation candidate separates three tasks: a bounded source-discovery
collector, a generic reader qualified only with internally generated data, and
an independent rights/trust review. It supplies a concrete proposal for acquiring
three text candidates from the GitHub CLI 2.92.0 tag (`go.mod`, `go.sum` and
`LICENSE`). Their existence, bytes and hashes have not been verified. A mutable
tag and three successful responses would establish neither a coherent Git tree,
correspondence with the installed binary, nor a trusted root or verified build.
The formula's source-archive digest does not authenticate individual raw members.

`verifier_preparation.py` keeps its ordinary entry closed. A separately approved
fixed collector allows at most three GETs, no redirects or retries, with stored
caps of 64/512/64 KiB and one unstored rejection byte per response. It includes
one same-descriptor readback for each completed file, strict UTF-8/non-NUL quality
checks (Content-Type is ignored) and bounded static metadata; it never evaluates Go, resolves dependencies
or classifies the notice as a rights clearance. Rejected or interrupted prefixes
remain bounded private observations. Recovery uses stat metadata; a cold receipt
reader never reopens source bodies. An external held plan, source/owner identities,
rights/origin evidence and one-shot approval are required; fixture construction
cannot authorize the real action. No capture occurs in this preparation.

The private proposal limits network bodies to 655,363 bytes and completed-file
readbacks to 655,363 bytes, with a combined ceiling of 1,310,726 bytes. Stored
objects plus two metadata records total at most 786,432 bytes; the parent marker
and outer observation raise that to 802,944 bytes, excluding the separate approval
record. Each request includes stop/join in 30 seconds; collection includes storage,
readback and recovery in 120 seconds, with a nominal 130-second outer driver and
140-second initial expiry headroom. These are owned watchdog controls, without
an absolute guarantee against an uninterruptible kernel operation, SIGKILL,
coordinator failure or loss of queued bytes. There is no automatic retry or cleanup.

`pbs_production_inspection.py` adds a separate streaming gzip/POSIX ustar core.
Fixed internally generated scenarios exercise the proposed 25,172,086-byte
compressed limit, 512 MiB expanded limit, 20,000 members, 256 MiB per member,
4,096-byte path/depth-32 upper guards and 8 MiB inventory. The supported ustar
fields can represent at most 256 path bytes; these guards do not add a long-path
extension. The owned root-Python worker holds
one invented input descriptor for the digest and inspection passes, drains opaque
member bytes, validates gzip framing/CRC and bounds report I/O. Unsupported
extensions, unsafe paths/links, excess bytes and incomplete process closure refuse.
Its cold reader checks reachable stages and report identity; invented authentication
controls provide no actual cryptographic trust. No member contents, member hashes,
notice text or extracted files are returned. These tests qualify the supported
synthetic grammar and enforcement; compatibility with the unread real PBS archive
remains unknown. The real `inspect_archive()` front door remains closed.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_verifier_preparation tests.test_simglucose_pbs_production_inspection
```

The preparation approval covers only the proposed three-text discovery and its
single completed-file readback. Actual GitHub CLI execution, source/build closure,
independent trust bootstrap, signature/identity/time/log policy, a compatible
artifact-read strategy and real phase-B admission remain separate open work.
No tool probe, trust-root admission, original PBS read, installation, build,
export, deletion or native execution is authorized by this candidate. Existing
gates and native postponement remain unchanged. Private new-fact evidence is
bounded by 30 days and the earlier 28 November 2026 18:32:01 UTC ceiling, with
earlier limits taking precedence; old or unknown origins are not reset.

## Metadata-only assessment after source discovery

A separately approved private source discovery subsequently completed for all
three fixed candidates, with matching acknowledged-write and single-readback
hash observations. The receipt, static summary, outer observation and consumed
one-shot marker support that historical action. The grant has expired; its
expiry does not invalidate retained metadata within the earlier retention
window, and supplies no repeat capture or additional body-read permission.
Earlier preparation documents retain their original unapproved proposal states;
a new assessment records the later consent and outcome alongside them.

The metadata-only follow-up reads those existing records and existing runtime,
attestation and qualification metadata. It does not reopen or hash the captured
`go.mod`, `go.sum` or `LICENSE`, the installed verifier binary, the opaque PBS
archive or other asset/notice bodies. Reported source digests are producer
observations reconstructed from metadata, not new stored-body measurements.

The module summary retains 64 labels from 180 lexical dependency candidates and
explicitly reports truncation. The Go/toolchain labels and a Sigstore dependency
label are observations, not a complete dependency closure, a qualified API, a
build-to-binary link or verifier acceptance. `go.sum` and `LICENSE` have only
size/hash/UTF-8/line-count observations; no checksum semantics or licence terms
were reviewed. The accepted private discovery reliance does not imply general
source reuse, redistribution, runtime-risk acceptance or actual asset use.

The authentication assessment separates the qualified synthetic streaming core
from the missing real cryptographic and operational route. It still needs an
independently trusted root snapshot and bootstrap/freshness policy, exact
verifier implementation/build/dependency qualification, certificate issuer and
identity policy, signing-time/log/rotation policy and explicit self-hosted-builder
disposition. A path-based verifier can hash or reopen an artifact: its reads
cannot silently fit the proposed two-pass held-descriptor budget. A qualified
mature digest-input route or an explicitly revised and qualified read strategy
must resolve that conflict before an execution-approval request is ready.

The new private package preserves consumed/expired grants and original retention
origins, and records outstanding decisions without minting approvals or replacing
old seals. No download, installation, build, verifier/native activation, archive
inspection, export or deletion occurs. The earliest known private retention cap
remains 28 November 2026 18:32:01 UTC, with earlier limits taking precedence.
Complete historical copy/restore coverage, effective erasure and native acceptance
are not established by this metadata assessment.

## Bounded retained-source and notice review candidate

`retained_source_review.py` separates two prospective substeps under one narrowly
scoped future decision. Preparation and tests use invented files only. The
ordinary entry refuses before input use; exact actual input paths, byte counts,
hashes, physical tokens, output roots and permission records stay private.
Previously consumed discovery grants cannot authorize this new material access.
Operational admission belongs to the exact pinned private driver. It requires an
absent output name, including refusal of dangling symlinks, both at preflight and
immediately before A. Direct privileged helpers alone do not supply that complete
namespace admission. Private ownership is trusted; atomic protection against a
hostile actor with the same UID is not claimed.

Substep A holds bounded private regular source inputs and consumes one forward
pass per selected module and notice file, with size/hash/UTF-8/non-NUL and physical
name/descriptor/context checks. It does not seek, retry, resolve Go dependencies
or execute source. Static module output accounts for every supported lexical
label within its bounds; unknown or malformed syntax is explicit and cannot
claim complete context. Complete lexical labels do not establish Go semantics,
actual dependency contents, a usable verifier API or build/binary correspondence.

Only after both source identities and quality checks pass may A write one private
report containing structured module context and the full literal notice. This is
an explicit new notice-bearing copy. A's returned receipt contains metadata only;
it never displays the notice. A late storage/fsync/context failure may leave an
authorized bounded partial or full report prefix; failure metadata stays free
of notice text, and an incomplete producer cannot admit B. There is no automatic
repair, deletion, additional source pass or success claim from that prefix.

Substep B consumes that derived report once using separately held producer and
report pins, a second one-shot marker and current source/permission/context checks.
It never reopens the original material files. The result is one bounded private
notice-bearing review/delivery attempt, not a cold metadata read. A validated
notice may be partially delivered if cancellation, expiry or output failure
interrupts the private view; there is no automatic retry. Read/review preparation
receipts do not prove downstream display or global copy/restore coverage.

A future private proposal binds the two exact retained identities to at most
10,212 source application bytes including rejection probes, followed by at most
131,073 derived-report bytes: 141,285 input bytes total. The report cap is 128 KiB,
the A metadata receipt cap is 64 KiB, and the private B result envelope cap is
192 KiB. Two parent markers and two bounded outer observations give a 229,632-byte
persistent action-output ceiling, excluding its separate approval record. The
source worker has 60 seconds including owned stop/join and storage; report review
has 10 seconds. Outer 70/15-second metadata boundaries are nominal/cooperative,
without a hard kernel/crash guarantee. Each substep checks its own current expiry
and headroom; successful A does not reserve permission for a delayed B.

The future limited read/copy/private-view reliance must expressly cover notice
exposure through the private controller/tool result. Allocated local outputs
retain the earlier 28 November 2026 18:32:01 UTC ceiling; this does not guarantee
platform transcript deletion or close unknown session-copy/restore coverage.
No actual licence interpretation, new source read, runtime risk acceptance,
verifier/root admission, installation, build, export, removal or native execution
occurs in this preparation. All existing gates and native postponement remain.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_retained_source_review
```

## Bounded selected-tool startup and help candidate

`gh_verifier_probe.py` prepares one selected binary identity pass followed by
at most two controller-dispatched commands in fixed order: `--version` and
`attestation verify --help`. There is no artifact argument or cryptographic
verification. The ordinary entry remains closed; only a new exact private
decision, source snapshot, current installation identity, fixed profile and
qualified driver can admit a future attempt. Actual GH has not been run by this
qualification. Completed earlier source/report review is represented only by
existing receipts and derived observations; neither original source bodies nor
the notice-bearing report are reopened. Complete supported lexical context and
the observed MIT notice do not prove dependency contents, notice applicability,
all embedded rights or source/build/binary correspondence.

Controller fixtures use internally minted fresh invented files and root-Python
stand-ins. They cannot promote rehashed caller data into a fixture capability or
select a real tool. Separate matched OS controls use the same profile generator
with invented targets and explicit counterprofiles. The actual profile defaults
to denial, imports a pinned nontransitive Apple dyld support policy, permits the
selected executable and reads/maps within `/System/Library` and `/usr/lib`, and
allows `/dev/null` I/O. The Apple policy also supplies its reviewed Cryptex,
ancestor read/test access and loader operations. General sysctl reads, process forks,
other executable paths, network, user files and writes are not admitted.
This uses an OS private interface; policy drift requires requalification.

Matched mechanism controls require execution outside the tool sandbox on this
host. A future real attempt needs that exact reviewed route; approval review or
OS refusal stops it without fallback. This is a tooling probe, with its own
limited runtime and rights risks, and does not authorize model execution.

The private proposal fixes the binary byte count, historical expected digest and
physical identity. One fresh forward hash pass accepts exactly that count, with
one extra rejection byte at most. This cap excludes executable loading/mapping,
system and Cryptex reads, and the selected program's permitted self-reads. Those
have path, process and time bounds rather than aggregate byte/syscall bounds.
Two dispatched commands do not bound total self-reexec syscalls or prove that
untrusted code preserves its internal argv. Held descriptors and repeated name,
parent and token checks assume a trusted installation owner, permitted package
manager writers and administrators; they do not give atomic executable-byte
custody against a hostile actor with those privileges.

Each command has a ten-second budget including cleanup, within a sixty-second
owned worker budget covering hashing, process I/O, storage, stop and join. The
outer seventy-second boundary is nominal/cooperative: blocking outer metadata
I/O, crashes and kernel termination have no independent watchdog guarantee.
Per command, each pipe stores at most 8,192 bytes with one extra application
rejection byte. Across both commands that is 32,768 stored raw bytes and 32,772
application-read bytes. Emitted or kernel-buffered bytes are not that read cap.

A new private output root contains only a bounded raw-output report, a metadata
receipt and `.environment` with four empty home/config/cache/tmp leaves, six
directories including the root. HOME/config/cache/tmp are fixed and empty; the selected process receives a
scrubbed environment and cannot write there. The report is an explicit new
private material copy, at most 65,536 bytes; the receipt is at most 32,768 bytes.
One parent marker and one outer observation give a 114,816-byte action-output
ceiling, with a separate 32,768-byte approval record. No raw report readback or
raw tool-result view is included. Returned metadata cannot supply authentication
or runtime admission. Failure can leave bounded partial evidence; there is no
retry, repair, deletion or automatic retention extension.

All current operational gates and native postponement remain unchanged. Any
future probe retains the existing earliest local retention ceiling and requires
current checks, enough remaining time and one fresh exact approval. Even a
successful version/help probe leaves verifier source/build qualification,
certificate/log/root policy, bounded artifact access and actual cryptographic
verification open.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_gh_verifier_probe
```

## Bounded selected-tool error review candidate

A later, separately approved startup attempt matched the selected binary's
expected identity, then stopped at `--version` with exit code 2. It produced no
stdout and 506 bytes of stderr. The controller did not dispatch the help command
and did not retry. Metadata checks preserved the existing gates and native
postponement. This is a failed startup qualification, with no cryptographic
result or inferred diagnosis. The raw error remains unread.

`gh_error_review.py` prepares one new read/review attempt, using only invented
reports during qualification. Its ordinary facade refuses before argument/path
access; minted fixture provenance cannot select actual input files. A future
private decision binds the complete source report identity, physical source and
output parents, exact producer metadata, reader/owner identities, origins and
limited material-read/view basis. Previously consumed startup/source/notice
grants cannot authorize this report read or a new tool invocation.

The selected error is base64 inside a 2,316-byte JSON report. The proposed source
pass therefore permits at most 2,317 application bytes including one rejection
sentinel, rather than claiming a 506-byte file read. Size, whole-report SHA-256,
strict duplicate-free JSON, exact report/probe metadata and canonical base64
must pass before delivery. Only the selected 506-byte stderr buffer is admitted;
stdout must be empty and extra rows or material are rejected. There is no seek,
retry, second file hash pass or original-container view.

The one proposed private result view uses deterministic, reversible ASCII byte
escaping. The parent independently reconstructs the selected bytes and verifies
their count and digest before delivery. This displays unknown technical material,
not trusted instructions, executable code or permission to follow embedded paths
or URLs. The view is an explicit new private copy through the controller/tool
result, with unknown conversation/transcript/restore custody. Local retention
limits do not guarantee platform purge or complete global copy coverage.

No new local material file is proposed; the private conversation view may remain
outside those local files. The new private output root may
contain only a bounded metadata receipt; a consumed marker and bounded outer
observation record the attempt. Actual source paths, digests, physical
tokens, output roots and permission records stay private. Exact fixed-driver
admission rejects any existing output entry, including dangling links, before
and immediately before the action. The marker is consumed before the source
open. A failed validation/storage/view may leave bounded authorized evidence or
partial delivery; neither permits a retry or proves downstream display.

The escaped selected stream has at most 2,024 characters; the complete private
view/metadata envelope including its newline is capped at 16,384 bytes. The
metadata receipt cap is also 16,384 bytes. A 128-byte marker and 16,384-byte outer
observation give a 32,896-byte persistent action ceiling, with a separate
32,768-byte approval record. The owned worker has ten seconds including read,
validation, IPC, storage, stop and join. The outer twenty-second boundary is
nominal/cooperative without an independent blocked-metadata-I/O or pre-handle
process-launch watchdog. No source material can open before the fixed wire is
sent; this is no hard kernel or realtime guarantee.
Thirty seconds of permission headroom and twelve seconds before the worker are
required. Source application-byte bounds do not include own code/metadata or
internal IPC reads. Local allocated evidence keeps the existing earliest
retention boundary without resetting original report/material origins.

Owned root-Python fixtures test reading, validation, IPC, deadlines, cleanup and
delivery failure. They do not run GH, admit a different sandbox policy, diagnose
the actual error or qualify cryptography. All setup, execution, asset, export and
removal gates and native postponement remain. A later successful view still
requires a separate technical decision before any new GH attempt.

```sh
uv run --locked --no-sync --offline python -B -m unittest tests.test_simglucose_gh_error_review
```

## Narrow system-query successor candidate

A separately authorized single container pass and private error view later
identified a Go-runtime initialization failure to determine the system page
size, before the allocation heap initialized. That observation is retained only
as derived diagnosis and receipts in this preparation; the error/report bodies
are not reopened. It establishes neither the exact failed OS call nor a complete
set of access requirements for the installed GH binary.

The smallest proposed policy delta is one literal read-only system-query name,
`hw.pagesize`. The selected trusted SDK header records a historical table
association with `[6,7]`. A bounded lookup on the current kernel instead maps the
name to `[6,115]`. These are different observations, not evidence that the two
MIBs are interchangeable or that either is the embedded Go call path.
The successor binds an exact singleton list in its current OS-policy identity
and generated profile. It admits no global sysctl read, prefix/regex/wildcard
matcher, write operation, process metadata or caller-supplied exception. Other
profile operations and allowed system/Cryptex/file roots keep their previously
declared scope. Repeated queries of the one allowed name have no syscall-count
quota; owned command/whole/output and expiry limits apply.

Matched current-host mechanism fixtures use trusted root Python and fresh
invented targets. Page-size queries are exercised through both the named and
current numeric `[6,115]` forms. The SDK legacy `[6,7]` request remains denied
and its failed control is retained. The old no-query profile is the denial control. A different known
safe hardware query must fail under the candidate and succeed under an exact
counterprofile, so missing names or failed bootstrap cannot count as denials.
The targeted query fixture preloads trusted Python/ctypes and applies identical
SBPL afterward through private, deprecated, undocumented `sandbox_init` raw-profile
flags. The SDK does not present that mode as a supported public API. Empirical
current-host effects qualify this query mechanism only. The actual GH launcher
would apply the profile before exec through `sandbox-exec`; separate nonquery
controls exercise that route. This bootstrap difference proves no GH startup.
No real process arguments, environment, accounts or other private user metadata
are queried. Existing file/write/network/fork/other-executable controls test that
the narrow exception does not supply those permissions. The fixture-only Python
installation read/map rule is omitted from the actual selected-tool profile.

This can qualify the smallest currently supported candidate exception. It does
not demonstrate that GH invokes that call, that the rule is necessary or
sufficient for GH, or that no later initialization access will fail. Exact
source/build/dependency, rights, cryptographic verifier, trust-root and artifact
read questions remain separate. Any further failure stops without retries or
automatic policy expansion.

A new exact private decision would admit one fresh selected-binary identity
pass and at most two fixed version/help dispatches under this successor. Existing
probe and error-view grants are consumed. There is no artifact parameter, new
error/report view, archive access, download, installation, build, export or
removal authority. The hash application-byte cap excludes executable loading,
self-reads and allowed system/Cryptex I/O; two controller dispatches do not bound
internal self-reexecs. Trusted installation/owner/admin assumptions and unknown
embedded rights persist. Raw output is a bounded new private report copy with
no readback/view in the probe grant.

The existing measured ten-second command and sixty-second whole budgets include
owned cleanup. The whole timer begins before gate/start checks and never resets
after handle acquisition. The outer seventy seconds and pre-handle process
acquisition are cooperative, without an independent blocked-I/O/launch watchdog
or hard kernel/realtime guarantee. State allocation precedes owned process
acquisition and successful handles immediately enter cleanup protection. Current
OS-mechanism qualification may require the same specifically reviewed route
outside the tool sandbox; refusal stops without fallback. No GH or other native
engine is executed during preparation. All existing gates and native
postponement remain; LT1 stays at 0/32.

## Remaining native work

Before any separately approved native implementation/setup, resolve the exact
patched interpreter/runtime and complete import/build closure, including eager
Matplotlib imports, Gym parent registration, optional rllab absence, entry-point
loading and resource access. The three required CSV SHA-256 values are now bound
through a separately approved intake receipt, and the published MIT notice was
accepted only as a limited rights assessment basis. This supplies no new read,
parse, copy or actual-use permission; this preparation does not reread payloads.
Actual asset use, complete rights/runtime risk and new artifact membership remain
open. Verify full notices and future artifact
membership rather than promoting Git metadata or the LT1 rights decision.

Freeze an actual native direct/wrapped consumer and bootstrap, compatible new
reader and independent entrypoints. Preserve native construction/reset sensor
consumption, default initial state, one-minute solver/three-minute outer clock,
eating queue, pump behavior and sensor noise. Record native basal with ordered
`u2ss * BW / 6000` U/min, then `60 * value` U/h; refuse an incompatible basal,
and do not assume the U/h-to-U/min round trip preserves every bit. Complete the
separate risk/rights, setup receipt, host/process and execution admissions before
running the proposed cases. The LT1 native attempt denominator is not extended
by these invented simglucose fixtures. OT-062 remains open.
