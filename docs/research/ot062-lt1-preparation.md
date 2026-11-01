# OT-062 LT1 first implementation packet

Date: 1 November 2026. Base: fetched `origin/main`
`a2e5058ec833e016033195843b623f6bce92762c`, clean before editing in an isolated
worktree. Status: implemented **preparatory** kernel, fixture reader and passive
artifact review. No native installation, build, import or simulation performed.
No native adapter, setup permission, host execution admission, two-engine result
or biological claim follows. The [earlier proposal](ot062-runtime-rights.md)
remains historical evidence with all authorizations false.

## Selected question, identities and capability

Ask whether audit-1 consumes only causally released glucose once per native
control tick while preserving the Cambridge loop. Reuse C01–C14c arithmetic
controls and retain C15–C18 as native acceptance cases. Select fixed Cambridge
parameters with `Gpeq=124.91784824923789`, IdealCGM and StaticInsulinPump from LT1
2.1.0, commit `9a6092065bd821f88691cd8d03b0550acd665573`. No clinical cohort,
frontend, oref0, image assets, commercial device tables or new parameter fitting
are selected. Keep Hovorka/Andersen ancestry and the
[asset card](models/lt1-cambridge.md) limitations.

The proposed candidate is
`lt1-cambridge-audit1-node22.23.4-darwin-arm64-preparation-1`.
[candidate-review.json](../../experiments/adapter_audit/lt1-candidate-review.json)
binds the passive Node/npm artifact observations; every authorization is false.
The historical LT1 lock stays at SHA-256
`44ad7ba062a7d67032d91fcc9e0fa2aa3910b3856dce76bee5ba32093c1a150e`.
No historical worker's Node 22.22.2 check is changed or bypassed.

Choose a new engine-specific `lt1-cambridge-audit1/1` capability as recorded in
[decision 0093](../decisions/0093-lt1-sampled-preparation.md). The kernel is
implemented, but the capability is not registered for SDK, GUI or native dispatch.
It supports sampled basal U/h, causal released glucose, one fixed parameterization
and seed 101. It refuses bolus, same-cadence cross-engine inference, human profile
matching, checkpoint resume, arbitrary controller execution and broader cohorts.
The current twenty-minute invented fixture remains twenty minutes; it is not
relabeled as the proposed thirty-minute native diagnostic.

## Runtime, headless build and security assessment

The [official release index](https://nodejs.org/dist/index.json) retrieved on this
date identifies 22.23.4 as the latest 22.x entry. The
[22.23.4 release](https://nodejs.org/en/blog/release/v22.23.4) identifies a security
release; the [October security bulletin](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
describes Node and bundled-library fixes. This selects a candidate, not a general
statement that no vulnerabilities remain. Historical 22.22.2 receives no new risk
exception. The broader Node 24 public-tooling choice is a different identity.

Passively downloaded `node-v22.23.4-darwin-arm64.tar.gz`: 49,996,369 bytes,
SHA-256 `c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428`,
matching official SHASUMS over HTTPS. The archive has 5,866 members and 189 files
whose basename is LICENSE/NOTICE/COPYRIGHT or a selected license extension.
No member was extracted to an executable environment; no binary was run. The
signed checksum file was retained, but its signature was **not verified** against
a trusted release key. HTTPS hash agreement is not authenticated release
verification. This remains a concrete pre-setup gate.

All twenty tarballs referenced by the unchanged headless npm lock were downloaded
passively, verified against their SHA-512 integrity and inventoried for notice
paths/hashes without extraction or lifecycle execution. Each has notice files.
The new JSON records their actual byte SHA-256 and lengths. This improves on the
earlier registry-only match; it is not a complete notice-compliance review.
A fresh twenty-version OSV batch returned no matches. Its response hash is bound.
This scan excludes Node/V8 and bundled libraries, upstream Git code, OS/compiler
and unqueried nested components. Complete their current advisory disposition
before setup. Node's payload contains npm and its dependencies; absence from the
headless import path does not make that payload disappear from the inventory.

Keep the selected headless path: separate private staging with TypeScript 5.7.3,
ts-node 10.9.2 and @types/node 22.10.7 and the existing twenty-package resolution.
Do not install the full upstream package graph or execute `postinstall:
patch-package`. A future separately identified manifest/lock must declare the
new exact Node version and retain the dependency entries; this packet does not
generate it or run npm. Proposed setup uses script-disabled `npm ci` with no audit
or funding network phase, followed by reviewed explicit loader configuration.
Pin the npm executable and loader/compiler options in that setup receipt.
The inherited import traversal is static evidence, not proof of a complete
runtime trace. Review the exact successor closure, full clean upstream source
inventory and build outputs before native execution. Root Python remains tooling.

## Restricted local use and outputs

Pinned `LICENSE.md` SHA-256 is
`5b786cd1552015d73f9a6e294c4a78fbee89801c998345cfe226e36d624962eb`, matching
[the retained notice](../../LICENSES/LT1.txt). Cambridge, IdealCGM and
StaticInsulinPump carry MIT headers. Their selected constants/device defaults
are in source; inspected files import no separate patient or device table.
This provides a concrete declared-license basis to consider local use of these
exact code/default assets while preserving headers, the full MIT notice and
model references. It does not independently verify the original parameter chain
of title or confer an approval. The MIT declaration permits software use subject
to retaining its notice; no new rights grant or upstream contact was obtained.

The selected diagnostic does not need native PID/MPC or ReferenceScenario at
runtime. Those remain separately attributed historical-reference inputs if their
own checks are later admitted. Do not silently import that example just to obtain
a controller configuration, or substitute its different patient/equilibrium.
Do not copy article figures/tables or the source snapshot's withheld native rows.

The reviewable restricted-use decision is: exact Cambridge/IdealCGM/static pump
code and source defaults, synthetic events, one private macOS arm64 development
host, no device control, no parameter/cohort export. It remains **pending**, with
the basis and limits above available for a maintainer decision. Resolve any
separately supplied asset before adding it. Interpreter, npm and twenty-package
notices must accompany any later local copy as required by their actual terms;
Node's [full license inventory](https://raw.githubusercontent.com/nodejs/node/v22.23.4/LICENSE)
and archived npm notice paths are evidence inputs, not blanket bundle clearance.

Native states, full parameter settings, raw diagnostic/native records and reports
must remain in owner-only private storage outside Git. Output copyright, underlying
asset provenance and possible embedded parameters are separate from code licensing.
Only invented fixtures and specifically reviewed metadata/sanitized summaries are
public in this packet. Public native bundle, table and full-report redistribution
remain unapproved. A private detail record must identify the local-use decision's
operator/reviewer, scope, unresolved provenance and export classification before
execution admission. Do not invent an approving person.

## Smallest harness and trusted reader

The passive source review checked Simulator, Cambridge, IdealCGM, static pump,
controller types and solver entrypoints against the pinned source. Native reset
orders solver, sensor, controller, actuator, patient and offsets component seeds
by +1…+4. Each callback advances patient, sensor, controller, actuator, recorder.
The controller is called on every callback, including minute 30; event boundaries
can shorten the default one-minute callback step. Native pump update quantizes
rate at 0.05 U/h and consumes random draws even with zero configured noise.

[lt1_sampled.mjs](../../experiments/adapter_audit/lt1_sampled.mjs) implements only
the sampled state machine. It receives a copied released observation and elapsed
minute; it sees no patient state or actual-event table. It holds command on
off-grid callbacks, rejects duplicate/missed/reversed updates, retains original
measurement and availability times and refuses changed stale samples. The release
queue must choose the newest available measured sample before calling it. That
queue and actual native construction are still to be implemented/reviewed.

The direct harness must independently construct Simulator/Cambridge/IdealCGM/pump
and a separately inspected audit-1 reference controller. The wrapped harness uses
the new sampled kernel with an independently tested raw-generation/release queue.
Both preserve native reset, solver and all pump callbacks. Existing M2
`build(direct=true)` selects PID/MPC and cannot be this policy's oracle. Calling
the same adapter twice is not a direct/native control. Obtain native basal from
equilibrium without changing initial state to make the controller fit; refuse
out-of-range/nonfinite basal. Bind all input bytes, seeds, source/lock, interpreter,
compiler/loader, harness/kernel/reader, parameter and initial-state identities.
Time-varying profiles need further review: native equilibrium uses local midnight;
this fixed-parameter choice makes no general timezone-independence claim.

The future native reader needs distinct sections for native callbacks, raw sample
generation, releases, sampled transitions and complete delivery intervals. Accept
finite strictly increasing actual callback times, including fractional boundaries;
validate six sampled transitions at 0…25 for a complete thirty-minute attempt.
Close an interval only when the following native endpoint is present. Integrate
modeled `iir * duration_minutes / 60`; preserve command independently and exclude
the terminal action and unobserved tail. Preserve primary failure if diagnostics
also fail; length alone never establishes success. Historical M2's integer-index
reader remains unchanged and cannot admit this grid.

[lt1_packet.py](../../experiments/adapter_audit/lt1_packet.py) implements a narrower
trusted **fixture-only** reader now. It reuses the existing regular-file bounded
intake, strict JSON and Decimal audit oracle. It refuses native kind and arbitrary
archived-source fields, binds actual fixture bytes and retains three declared
slots, a zero-prefix failed first attempt, its explicit retry and an unattempted
slot. The fixed plan is compiled into this reader; it is not a general project
ledger or native evidence format. Relocating its single JSON file needs no native
runtime. It checks internal retry lineage, not authenticity of past attempts.
Separate review demonstrated that removing the failed attempt and consistently
resetting its retry's ordinal/parent is accepted as a different invented history.
That accepted counterexample is tested explicitly; byte hashes identify the file
read but cannot authenticate an untrusted producer's history. Native intake needs
an externally trusted attempt inventory/seal and the existing immutable store.
Existing project `store.py`, `execution.begin/finish/reconstruct` and
`execution.supervise` remain the intended future owners of immutable slot/attempt
events, execution and reconstruction, rather than a second ledger implementation.
No current route/descriptor/allowlist or reader-transition registry is extended.

## Acceptance and counterexamples

| Boundary | Accepted control | Distinguishing counterexample |
| --- | --- | --- |
| Sampled clock | Original four-tick Decimal transcript; six ticks over thirty minutes; off-grid 2.5/3.5/4 callbacks hold exactly | Duplicate, reversed, missed tick; extra sample on off-grid callback; terminal update |
| State/availability | Reset to 120, fresh lagged update, stale basal, delayed minute-10 source at minute 15 | Early release, old sample displacing new source, changed stale value, boolean time, hidden meal/state field |
| Arithmetic | Original 1.2/1.2/1.2/1.8 commands; non-target initial value; strict negative lower-clamp and upper-clamp controls | Current sample used before command; missing clamp; reset uses initial glucose |
| Fixture reader | Full and empty-failure prefixes, explicit retry, unattempted slot, relocated no-site reconstruction | Missing parent with unchanged retry lineage, retry without terminal parent, boolean ordinal, truncated completion, changed identity, duplicate JSON keys, symlink; consistently rewritten history remains accepted without external trust |
| Future C15/C16 | Direct/wrapped exact native scientific fields; native resets twice/fresh process; unchanged raw sample generation; actual 40 g/20 g announcement case from prior packet | Shared wrong replay against historical baseline; future-meal 80 g pre-event leak; shifted sample timestamp; held pump callbacks; fractional event rounded |
| Future C17/C18 | Retain all attempted/unattempted cases, completed prefix and primary error; bounded cancellation/deadline and sentinel survives | Padded tail, dropped failure, diagnostic error hiding native error, unrelated process killed, survivor after cleanup |

The kernel's new binary/Decimal arithmetic criterion and unchanged native exact
parity requirement are specified in decision 0093. The old Decimal fixtures,
baselines and tolerances are preserved. Native C15–C18 and inherited historical
reference checks remain unrun; a thirty-minute diagnostic cannot replace them.
Retain unavailable historical comparisons explicitly when the old runtime cannot
be admitted. Repeated/out-of-order RHS probes stay in the existing M4 suite;
sampled callbacks are not pure RHS functions.

## Private evidence, gates and exit criteria

Passive archives/responses and notice inventories are retained privately outside
Git under `/private/tmp/ot062-lt1-review-20261101`; pinned source review files under
`/private/tmp/ot062-lt1-source-review`. Directories use owner-only permissions.
These temporary paths are local retention locations, not permanent archives.
Before deleting them, transfer to approved private evidence storage and verify
hashes. No native parameter payload or result was created by this assessment.

| Gate | Concrete next evidence | State |
| --- | --- | --- |
| Pre-setup runtime/security | Authenticate checksum signature; disposition full Node/npm/vendor closure; identify exact new manifest/lock/loader and setup plan | Open; byte hashes verified, no setup admitted |
| Restricted local use | Record named reviewer/operator decision for precisely selected source/default/device/output assets and retained notices | Open; source-declaration basis documented |
| Harness/reader review | Implement independent direct/reference harness, release queue, fractional-grid native reader and source inventory; review C15–C18 before setup | Open; kernel and invented reader controls implemented |
| Separate setup | Explicit authorization for frozen artifact acquisition/staging, then actual script-disabled setup receipt, executable/hash/options and payload inventory | Unrequested/unrun |
| Host execution | Verified setup receipt plus one named macOS arm64 host, file/network confinement, private output path, per-attempt deadline/cleanup and explicit case authorization | Unrequested/unrun |
| Native acceptance | Historical applicable checks, all C15–C18 attempts/failures, direct parity and relocated simulator-free native reconstruction | Unrun |

Future host review should reuse `platform_process` and shared `Ownership`/
`execution.supervise` for the coordinator and descendants. A child process or Node
permission flag alone is not network confinement. Select and test an actual host
file/network enforcement mechanism, cancellation before initialization and while
blocked, outer deadline/escalation, descendant cleanup and an unrelated sentinel.
No such host mechanism is implemented or qualified by this packet.

This preparatory increment exits when source/artifact observations are bound,
kernel/fixture-reader controls and separate technical diff review pass, and the
author's final root check is recorded on the final tree. It does not wait for
native execution that the open gates prohibit. The concrete next increment is
the versioned direct/reference and wrapped construction plus fractional native
reader/release queue, reviewed with the remaining runtime/rights decisions before
requesting setup. A simglucose successor, second controller/question, fit/freeze/
evaluate and broader OT-066 work follow the roadmap order.

## Verification scope

The implementation owner runs `uv sync --locked`, targeted
`test_lt1_preparation.py` and unchanged `test_adapter_audit.py`, the existing M4
pure-RHS controls, and one final `uv run --locked python scripts/check.py`.
The Node kernel suite uses the existing host tooling Node; it does not execute
the downloaded 22.23.4 candidate. Exact revision/dirty state, actual outcomes,
separate review findings and private log locations belong in the PR handoff.
Local root checks are not hosted CI, native parity or independent human evidence.
