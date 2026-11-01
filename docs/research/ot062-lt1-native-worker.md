# OT-062 LT1 native loader and worker successor

Date: 1 November 2026. Base: PR #52 squash merge
`70c0c994301a0976495c68ccee20a6a227c9a56d`. This follows the
[diagnostic harness](ot062-lt1-harness.md) and
[decision 0095](../decisions/0095-lt1-native-worker-admission.md).
No native setup, import, build or simulation has been performed. All setup and
execution gates remain closed.

## Implemented boundary

[native_loader.mjs](../../experiments/lt1_diagnostic/native_loader.mjs) implements
a positive verifier instead of interpreting candidate metadata as permission.
The fixed [production registry](../../experiments/lt1_diagnostic/native-admissions.json)
has separate empty setup-receipt and execution-grant lists. An unknown grant is
refused before parsing it or inspecting supplied staging paths. The worker reads
this registry from its own source location; no request or environment argument
selects a replacement. Changing the registry requires a reviewed source change.

A reviewed grant must bind all of the following:

- Exact private plan bytes and either direct or wrapped mode; the existing
  thirty-minute millisecond protocol and selected LT1 revision remain unchanged.
- Actual Node v22.23.4 Darwin arm64 executable bytes, exact named host and absolute
  staging root. A matching version string alone is insufficient.
- Complete staging file hashes, including hidden files, source/license, runtime,
  package lock, installed toolchain, TypeScript configuration and loader. Symlinks,
  special files, extra or missing files and changed bytes refuse. Staging must
  already be immutable under the separately reviewed host controls.
- Current worker JavaScript import closure, including the transitive historical
  recording helper. This does not enroll a new historical reader identity.
- Exact setup, host, rights and security receipt bytes; the setup receipt digest
  must independently appear in the trusted setup list. These are reviewed evidence
  inputs, not self-authenticating approvals.

[native_worker.mjs](../../experiments/lt1_diagnostic/native_worker.mjs) verifies
those identities before registering the staged ts-node loader and importing the
four fixed Simulator/Cambridge/IdealCGM/StaticInsulinPump entrypoints. It selects
the existing direct/wrapped construction and emits a versioned single-attempt
result retaining recorded primary and diagnostic failures. It neither fabricates
a trusted reader packet nor publishes output. The historical Node22.22.2 worker,
locks, tolerances, baselines and closed prototype `loadNative()` remain intact.

This worker is not yet an admitted launch route. The supervisor must prevent
preloads before startup; checking `execArgv` and environment inside a worker cannot
undo a preload. A child process and a receipt hash do not enforce filesystem or
network confinement. The existing `platform_process`, `Ownership`,
`shared_services.execution.supervise` and project store still need an explicit
route with immutable staging, clean environment, deadlines, durable per-callback
prefixes, all planned/failure slots and descendant/sentinel cleanup. None of those
gaps may be waived by adding a grant. The current stdout result can be lost if a
process is killed before export; native cancellation and process qualification
remain unrun. Source/runtime staging and setup machinery are not installed here.

## Passive runtime assessment

[runtime-review.json](../../experiments/lt1_diagnostic/runtime-review.json) is
reviewed metadata only. The archive came from the
[official Node distribution](https://nodejs.org/dist/v22.23.4/). Archive SHA256 is
`c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428`.
Passive in-memory inspection found 197 package manifests, 186 unique name/version
pairs. Querying those plus the twenty existing headless packages produced ten
affected archive pairs and 22 distinct GHSA matches. The twenty headless packages
had zero matches. That narrower result never cleared the complete Node payload.
The JSON retains each affected pair and advisory identifier for rechecking against
the [OSV API](https://google.github.io/osv.dev/api/). Version matches establish an
assessment obligation, not exploitability in this exact diagnostic.

Seven archive package roots lack a recognized root-local notice. This is an
inventory gap, not proof of missing licensing. Corepack's inlined dependency
closure is not established by enumerating package manifests. The proposed new
minimal staging profile selects only `bin/node` and the complete Node LICENSE,
with their exact byte lengths and hashes in the metadata. It excludes npm and
Corepack files without modifying the original archive. No runtime was extracted
or staged. Native embedded libraries remain part of the executable.

The separately inspected [npm 12.2.1 release](https://github.com/npm/cli/releases/tag/v12.2.1)
declares compatibility with Node22.23.4, but its 145 unique bundled package pairs
include four affected pairs and eight GHSAs. It is not admitted as a setup manager.
Registry SHA512 integrity matched; both registry ECDSA signatures verified under
the retrieved [official registry key](https://registry.npmjs.org/-/npm/v1/keys)
with system OpenSSL, and modified-message controls failed. This authenticates the
registry name/version/integrity binding under that key, not dependency safety.
No overrides, replacement pins or install commands were run.

Node OpenPGP authentication remains open. The retrieved key's calculated primary
fingerprint matches the [official release-key list](https://github.com/nodejs/release-keys):
`5BE8A3F6C8A5C01D106C0AD820B1A390B168D356`. That is not cryptographic verification
of the retained SHASUMS signature. No suitable existing OpenPGP verifier was found;
OpenSSL is not one. Source/header inspection supports individual embedded version
and backport observations, but does not close embedded-library advisories,
artifact-to-source/build provenance, signer/subkey validity or revocation policy.
Selecting a smaller payload does not remove those obligations.

## Rights and private evidence

The exact selected LT1 revision declares
[MIT](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/LICENSE.md),
and the inspected Cambridge, sensor and pump files retain MIT headers. The
diagnostic does not select upstream PID/MPC/reference/frontend code or a separate
patient/device table. Keep the full license and Hovorka/Andersen attribution
recorded in the [asset card](models/lt1-cambridge.md). This is a declared-license
basis for a precise restricted-local-use decision, not independent parameter
chain of title, a named operator/reviewer's approval or public redistribution
clearance. Native parameters, settings, states and raw reports stay in private
owner-only storage pending output/export classification.

The private passive evidence packet retains archive/member inventories, notices,
OSV responses/advisories, primary source snapshots, registry signature controls
and remaining gates. Its location belongs in the review handoff, not in the public
runtime manifest. No private native inputs or outputs are committed.

## Verification and next gate

The [Node controls](../../tests/lt1_native_loader.test.mjs), invoked by the root
[Python check](../../tests/test_lt1_native_loader.py), exercise an invented grant
and trust registry, positive fixed constructor loading, both scripted harness
paths and reset, unknown-grant early refusal, each receipt and identity mutation,
extra/missing staging files, symlinks, hidden names including `__proto__`, and
wrong constructor exports. The production CLI is tested only for refusal with
the empty registry. It performs no candidate import. Separate review found and
fixed the omitted transitive recorder hash and plain-object `__proto__` inventory
omission; controls now distinguish both regressions.

These are software fixture checks, not positive native worker execution or C15–C18
acceptance. Before setup, authenticate Node, resolve embedded/runtime/toolchain
security and notices, select a qualified setup mechanism and record the precise
restricted-use decision. Admit setup separately and verify its actual receipt.
Then complete the supervisor/store/host route and named-host observations before
any execution grant. Preserve every failed attempt and the independent native
parity/reset/timing/causality/failure criteria in the canonical harness guide.
