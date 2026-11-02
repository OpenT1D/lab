# OT-062 LT1 runtime follow-up and host fixture qualification

Date: 1 November 2026. Base: PR #53 squash merge
`d244c4932ca97f0e71b4911555acbb1038b63f7b`. This follows the
[worker successor](ot062-lt1-native-worker.md). The
[review metadata](../../experiments/lt1_diagnostic/qualification-review.json)
records bounded new evidence. It supplies no setup, native execution or
redistribution authorization. The production admission lists remain empty.

## Runtime and build assessment

The Node v22.23.4 annotated tag identifies source commit
`27f213124280b4db4cd1e3dd42f6f8afd01ceff7`. This is a resolved source pointer,
not an authenticated signature or independent binary reproduction. Pinned source
identifies cjs-module-lexer 2.2.0; its one npm name/version OSV query returned no
matches, closing that version-inventory gap only. The
[official build policy](https://github.com/nodejs/node/blob/v22.23.4/BUILDING.md)
declares macOS 13 arm64/Xcode 16 builds with minimum macOS 11. Exact compiler/SDK
patch identity, an actual build receipt and artifact-to-source reproducibility
remain unestablished. The previous archive/member hashes and affected npm
payload assessment are preserved in the worker guide.

| zlib issue | Bounded disposition |
| --- | --- |
| CVE-2026-22184 | [Merged Node assessment 435](https://github.com/nodejs/nodejs-dependency-vuln-assessments/pull/435) identifies the affected contrib/untgz tool, excluded from Node. This is an upstream non-applicability rationale, not a patched zlib-version claim. |
| CVE-2026-27171 | [Merged Node assessment 439](https://github.com/nodejs/nodejs-dependency-vuln-assessments/pull/439) says supported Node APIs use crc32 and do not expose/call the affected CRC-combine functions. Native addons calling zlib directly remain outside that rationale. |
| CVE-2026-85091 | Open. Both pinned `deps/zlib/gzwrite.c` and `deps/v8/third_party/zlib/gzwrite.c` lack the failure-path `avail_in`/`next_in` resets in the [upstream correction](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148), addressing that CVE, also reported in [issue 1310](https://github.com/madler/zlib/issues/1310). V8's build target includes its copy. This proves source presence and an absent correction; supported API reachability, actual linked behavior and exploitability are not established. |

The two pinned gzwrite copies have the same SHA256:
`469b1e58932ea11bdda2a153f6655f7b3c13254240fae157181b49ed1bc93b47`.
A Node 24 inquiry does not qualify the selected Node 22 artifact. Resolve this
case through an applicable upstream assessment, reviewed source/build reachability
analysis or a separately identified maintained fixed candidate. Do not waive an
issue because a broad tracker is closed, or declare every old version exploitable
without accounting for patches/API scope. Full vendor/native-library/OS review
remains incomplete.

An expanded bounded search found no existing OpenPGP verifier in the inspected
system, Homebrew, GitHub Desktop, Utilities and local-bin locations. This does not
prove no verifier exists anywhere. No verifier was installed or implemented.
The [official release-key workflow](https://github.com/nodejs/release-keys)
provides full/active keyrings and GPG instructions. A later established verifier
must authenticate the retained SHASUMS signature under an authorized valid
signer/subkey and reviewed revocation policy, then check the exact archive line.
Fingerprint matching and npm registry ECDSA verification remain separate evidence.
Node OpenPGP authentication is still open.

The subsequent [authentication/integration record](ot062-lt1-auth-integration.md)
authenticates the exact retained signature/archive with a separately reviewed
established utility. That later result closes the signature question only; it
does not clear the runtime/security, rights, setup or execution gates recorded here.

## Rights and setup mechanism

The selected [LT1 MIT notice](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/LICENSE.md)
requires copyright and permission notices in copies or substantial portions of
the software. Preserve the full license/disclaimer and selected source headers.
Cambridge cites Hovorka 2004 and Andersen 2014, but does not individually map all
17 source-defined defaults to primary origins. IdealCGM has one source-defined
sampling default; StaticInsulinPump has nine generic delivery/error defaults.
The selected modules load no separate manufacturer/patient table. Exact default
inventories remain private; no new numeric table is published here.

These observations establish the declared-license basis and remaining ancestry
questions, not independent chain of title or an operator/reviewer's decision.
Scholarly attribution and MIT notice retention are distinct obligations. Keeping
full native settings, initial states, raw trajectories and reports private until
export classification is project policy; MIT itself does not impose a universal
restriction on numeric outputs. A proposed public summary still needs review for
copied source/default tables, notices and any additional assets. Operator/reviewer
decision fields remain null. No local-use or redistribution clearance is invented.

A concrete alternative to the affected npm payload is now specified: a separately
identified frozen, data-only Python stager for the exact twenty headless tarballs
and Node binary/full-license selection. The lock has twenty flat targets without
nested version conflicts. Basic passive member inspection found only regular
files/directories and no obvious traversal/link members. Nineteen archives use
`package/`; `@types/node` uses `node/`. No archive was extracted and no lifecycle
script or resolver was run.

This stager is a proposal, not implemented or admitted software. Before setup,
review its own implementation/tool identity, whole-archive preflight, resource
bounds, normalized path/case collisions, link/special-file rejection, exact target
mapping, script refusal, private atomic staging, notices, per-file hashes and
failure/cleanup receipts. Qualify it with malicious invented archives without
loading candidate code. Actual staging and native loader compatibility still
require separately authorized setup. Do not replace historical locks or guards.

## Explicit host fixture probe

[host_probe.py](../../experiments/lt1_diagnostic/host_probe.py) is an explicit
Darwin arm64 probe with a fixed
[standard-library fixture](../../experiments/lt1_diagnostic/host_fixture.py).
It accepts a fresh private output directory, never a command, model, runtime
candidate, policy file or plugin. It reuses `shared_services.execution.supervise`,
`platform_process` and `Ownership`; there is no new process manager or native
dispatch route. The receipt binds the actual Python executable, sandbox binary,
OS identity, exact profile text and 148-file static local implementation closure,
including the borrowed supervisor/ownership code and package ancestor initializers.
Initializer imports are closed recursively; changing initializer bytes withdraws
qualification. The original 141-file inventory omitted normally executed package
initializers. A fresh PR review reproduced that gap on disposable source copies;
the corrected inventory and host run replace that incomplete identity evidence. It checks source hashes again
before the final receipt; a missing/invalid changed source withdraws qualification
while retaining failure evidence. This inventory is not arbitrary dynamic-import
proof or an immutable native installation.

The generated profile denies by default, allows the fixture's Python runtime,
declared system read/map paths, one fixture source, input reads and one case's
output writes. It grants no network rule. It imports the host's Apple
`dyld-support.sb`, whose hash is retained. That file explicitly identifies its
rules as private system interfaces subject to change. Broad system metadata,
mach-lookup and listed bootstrap access remain part of this fixture profile;
this is not proof against arbitrary hostile code or all IPC exfiltration paths.
It is not a ready native Node sandbox profile. The Python runtime is read-only
to the child but is not staged or qualified as the future native environment.

The supervisor supplies only fixed `LANG`, `LC_ALL` and `PATH` values. The child
runs `-I -S -B`, and the fixture verifies isolation/no-site and the environment
key/value boundary. CoreFoundation adds `__CF_USER_TEXT_ENCODING` on this host;
that observed encoding key is explicitly allowed, with names recorded and no
environment values exported. This proves the fixture launch behavior only;
native Node preload, dynamic library and module-resolution paths remain separate.

Before confinement, the parent opens a loopback listener and successfully
connects to it. Each parent/descendant then must observe EPERM/EACCES for socket
connection, outside-file content read and outside-file write. Connection refusal
or a missing target is insufficient. Allowed invented input reads and output
writes must succeed. Outside sentinels remain unchanged.

The planned denominator is fixed at four cases before any child starts:

| Case | Required retained observation |
| --- | --- |
| Complete | Zero exit, explicit exact completed marker, three fsynced invented rows and observed empty owned tree |
| Primary failure | Exit 23 remains failed, prefix retained, child observed by live start identity and cleaned |
| Deadline | WorkerDeadline remains failed; inherited child confinement, owned cleanup and stopped heartbeat sentinel |
| Intentional cancellation | Cancelled remains interrupted; inherited child confinement, prefix and cleanup retained |

All cases require the unrelated owned control process to remain alive until
explicit final cleanup. External signals never satisfy an intentional cancel
case: they fail qualification and leave later planned cases unrun. Unknown
cleanup state, missing child observations, changing heartbeat, malformed evidence,
wrong completion/exit/status, a false denial flag or ECONNREFUSED cannot pass.
The final private receipt retains every slot and per-case logs/process receipts.
These are diagnostic receipts; no project-store seal or native reader packet is
manufactured.

Run only for the explicit fixture investigation, using a new private path:

```sh
uv run --locked python -m experiments.lt1_diagnostic.host_probe --output /absolute/private/new-fixture-run
```

The output's parent must already exist and be canonical. The probe refuses an
unsupported host or existing output, creates the new root owner-only, and does
not run automatically in public CI. On the development Mac, the Codex filesystem
sandbox prevented nested `sandbox_apply`; the actual OS probe therefore ran
through the separately reviewed host tool invocation. That tool permission is
not a setup or native execution admission.

## Observed results and remaining gates

On one private named Darwin arm64/macOS 26.5.2 host with existing CPython 3.12.13,
all four final fixture cases passed. Each retained exactly three invented rows;
the failure/deadline/cancel cases also observed inherited child denials, child
ownership/cleanup and stopped sentinels. The unrelated process survived each
case and was explicitly reaped. No LT1 source, Node candidate, TypeScript loader
or physiological model was imported or run.

The development record retains the first dyld startup failure, two diagnostic
environment-check failures, intermediate successful runs and the final qualified run.
Review reproduced two false passes: external SIGTERM during the final cancel
case and completion without a marker. Both are fixed with focused regression
controls, along with failure retention when final source inspection raises.
The [root tests](../../tests/test_lt1_host_probe.py) exercise those pure validators,
identity, evidence and profile construction; they do not automatically launch the
OS sandbox. Root suite/hosted checks remain separate from this actual-host record.

Remaining before native execution: complete runtime/authentication/security and
restricted-use decisions; qualify the proposed setup implementation; separately
authorize setup and verify its receipt; establish immutable native staging and a
clean native launch; review a native file/network/IPC profile; bind this to the
existing supervisor and immutable all-attempt project ledger; qualify durable
native callback prefixes, cancellation/deadline/descendant behavior and C15–C18 on
the admitted exact runtime/host. None of those gates is closed by a scripted
Python fixture. No production grant, task registry, SDK/GUI route, publication
allowlist, historical lock, reader identity, baseline or tolerance is changed.
