# OT-062 LT1 authentication, rights dossier and durable attempt integration

Date: 2 November 2026. Base: PR #54 squash merge
`c3efbc70c2d50161a686a8985a7b56bdd3e05255`. This follows the
[runtime/host fixture assessment](ot062-lt1-host-qualification.md) and
[decision 0096](../decisions/0096-lt1-durable-attempt-integration.md).
The production setup and execution lists remain empty. No candidate Node binary,
native TypeScript loader or LT1 model was executed or installed.

## Exact release signature authenticated

[runtime-authentication.json](../../experiments/lt1_diagnostic/runtime-authentication.json)
records successful cryptographic verification of the cleartext-signed Node
v22.23.4 SHASUMS. The signing/primary fingerprint is
`5BE8A3F6C8A5C01D106C0AD820B1A390B168D356`, listed in both the
[official release keys](https://github.com/nodejs/release-keys) and the
[pinned Node README](https://github.com/nodejs/node/blob/v22.23.4/README.md).
The signature was created at `2026-10-21T10:33:12Z`. The authenticated target line
matches the exact Darwin arm64 archive SHA256:
`c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428`.
The actual retained archive bytes independently hash to that value.

No existing GnuPG verifier had been found. A separate established public-data
utility was therefore reviewed: [OpenPGP.js 6.3.2](https://github.com/openpgpjs/openpgpjs/releases/tag/v6.3.2),
using its full self-contained Node bundle. Its npm archive SRI matched, both
registry ECDSA signatures verified with system OpenSSL under the retained registry
key, and modified registry-message controls failed. Exact package/source/bundle
identities, eight embedded dependency archives/notices and nine dated OSV
no-match responses remain in the private tool dossier. Official signature-spoofing
advisory ranges exclude this version. This is a bounded tool assessment, not a
general vulnerability guarantee or independently reproduced library build.

The utility used the pre-existing host Node v22.22.2, identified by byte hash,
under a reviewed deny-default macOS profile. The candidate being authenticated
was only read as data. No npm install, lifecycle script, encryption/private-key
operation or candidate import occurred. The profile allows exact public inputs,
the frozen utility, required `/System/Library`/dyld/Cryptex and library bootstrap
paths, and private receipt output. It grants no network, mach-lookup or fork
operation. Existing host tooling and bootstrap paths remain a conditional trust
base; this does not clear that host Node for native simulation.

Limits supplied by the launcher were a 128 MB V8 **old-space** cap, ten CPU
seconds, one MiB output-file limit, 64 descriptors and a fifteen-second owned
deadline. The V8 setting is not a hard total-memory/RSS bound. The existing shared
supervisor observed zero exit and an empty remaining owned tree; all 161 frozen
utility/input/source manifest entries still matched after execution. No secret,
patient input or native report was supplied to the tool.

The version-pinned wrapper used the library's established API with strict defaults:

- Parse the cleartext wrapper with `readCleartextMessage`, not the detached API.
- Require the exact full primary fingerprint, one SHA256 signature and a reviewed
  release signing window. Call `verifyPrimaryKey(now)`,
  `isRevoked(null, null, now)` and current/signing-time `getSigningKey` checks.
- Call `verify(..., expectSigned: true)` and explicitly await the single
  `signatures[0].verified` promise. Never accept signature presence alone or relax
  hash/key defaults, backdate a failure or enable reformatted-key bypasses.
- Compare all authenticated text with retained SHASUMS text, normalizing only
  CRLF to LF and at most one final LF. Require exactly one exact target filename
  and checksum line, then hash the archive independently.

Four controls were rejected: changed signed payload; changed signature armor or
packet; a different valid official primary key at the identity-policy boundary;
and that parsed/current-valid alternative key at the library verification phase.
The latter reaches signature verification, rather than merely failing a fingerprint
assertion. The signature-mutation control is labeled conservatively because a
mutation can be rejected during armor/packet parsing; the changed payload directly
exercises authenticated-data failure. No custom OpenPGP/cryptographic verifier was
implemented.

The actual verification time was `2026-11-01T22:56:44.923Z`.
Current and signing-time validity passed, and no revocation was present in the
fresh official key bytes. That is not global discovery of every possible
revocation. An independent technical reviewer checked the retained result,
manifest, input/archive hashes and negative-control outcomes without rerunning
the tool. It is technical review, not independent human reproduction.

This closes the exact signature/checksum authentication question from the prior
assessment. Embedded-library/CVE reachability, source/build/OS security and the
unresolved zlib correction remain open. Authenticity does not establish safety,
scientific validity, rights, setup authorization or execution authorization.

## Concrete rights dossier, decision still pending

[rights-dossier.json](../../experiments/lt1_diagnostic/rights-dossier.json)
separates the exact LT1 source/default classes, proposed Node binary/full-license
payload, twenty frozen headless archives and private verification utility. It
records declared licenses, retained notices, ancestry limits, intended restricted
local purpose and public-distribution exclusions. No numeric default table or
native output is added to this repository.

Decision owner, reviewer, date, approved users/host, storage/output scope and
approval remain null. These must be completed by the actual decision makers for
the exact selected use and assets. Scholarly attribution, MIT notice obligations,
parameter chain of title, combined distribution obligations and project output
policy remain distinct. In particular, keeping full native settings/states/raw
reports private pending export review is project policy, not a universal MIT
restriction on numeric outputs. The separate LGPL verification utility and its
notices/source remain private; no library is vendored or bundled into this app.
The dossier is evidence and a decision worksheet, not a permission document.
No loader grants authority from its approval/status fields.

## Durable single-attempt worker

[integration_worker.mjs](../../experiments/lt1_diagnostic/integration_worker.mjs)
is a separate entry; the original worker and reader are unchanged. The
[integration verifier](../../experiments/lt1_diagnostic/integration_gate.mjs)
requires both the existing engine-grant digest and an integration-envelope digest
in the fixed reviewed registry, plus the existing separately admitted setup
receipt. An empty production registry refuses before any supplied path is
inspected. Otherwise, an unknown envelope hash refuses after bounded envelope
intake, before engine staging/output is inspected or candidate source is loaded.
No registry entry is added here.

The new envelope binds an attempt identifier, private output root, live owner PID,
separate integration host-receipt bytes, current integration JavaScript closure
and frozen reader identity. Before journal creation/import, the worker reads every
declared reader source file canonically and compares its bytes, plan, revision and
selected runtime identity. The complete Python import roster must come from
`journal_reader.identity()` and envelope review; the Node worker does not infer
Python imports. No caller-supplied registry, approval flag or archived code path
can replace that review. The production native branch remains unrun.

[attempt_journal.mjs](../../experiments/lt1_diagnostic/attempt_journal.mjs)
requires an existing canonical owner-only empty output directory and creates
`events.jsonl` exclusively. It fsyncs the header before native import/init and
each row after the existing validator returns successfully. It never reads extra
sensor/controller values, changes simulated time or replaces the native solver,
reset, pump or callback schedule. A callback checks the still-matching parent PID.
This is a callback stop check, not immediate solver cancellation or proof of
supervisor/descendant confinement.

Journal append failure stops the run; an invalid/unwritten row cannot silently
advance the committed row count. The existing callback setter is restored.
Native initialization errors get a failed terminal record with an empty prefix
when journal export remains available. A terminal export error is reported
separately from an existing primary error; poisoned/torn output remains incomplete.
Actual native import/initialization and export-fault qualification still require
the admitted environment. No file is overwritten or reused for a retry.

## Engine-free reconstruction and process authority

[journal_reader.py](../../experiments/lt1_diagnostic/journal_reader.py) consumes
bounded regular journal/plan/process-receipt bytes and externally supplied expected
journal/receipt hashes. Those hashes must come from a trusted same-attempt
inventory/store; calculating them from an untrusted producer's own files only
checks integrity and does not authenticate process history. Original output and
owner metadata must agree with the supplied process argv/observations. Relocation
does not cause archived paths or code to be opened.

The reader recomputes its current initializer-aware source identity and delegates
scientific row/plan/causality checks and exact fractional integration to the original
trusted reader. It never imports a candidate engine or archived code. Only complete
newline-terminated records are scored; a torn final record is retained as an
uncommitted byte count. Invalid committed records, repeated ordinals, data after a
finish, stale code/plan, mismatched receipt/output/owner or unknown cleanup refuse.
An empty or single-row prefix has null delivered amount; no endpoint is padded.

A worker footer cannot override failed/interrupted process status, nonzero exit
or observed external signals. Even a full valid 32-row footer remains noncompleted
when the process was interrupted. Primary/native, diagnostic and process causes
remain separate. Missing footer with zero process exit is failed, not completed.
The only origin labels are `invented` and `native-unadmitted`; native acceptance
and execution authorization always remain false.

The [Node controls](../../tests/lt1_integration_gate.test.mjs),
[fixed child fixture](../../tests/lt1_journal_fixture.mjs) and
[Python process/reader tests](../../tests/test_lt1_journal.py) cover dual authority,
setup separation, current worker/reader bytes, private exclusive files, closed
production refusal, static JavaScript import roster, row-export failure,
direct/wrapped 32-row equality, relocation, native-shaped failure, owner-loss
injection, actual scripted deadline/cancellation, torn tails, receipt/status
counterexamples and scientific corruption. The invented full amount remains
25/48 U; three-row prefixes retain 3/100 U. These are unchanged hand-calculated
fixture oracles, not native numerical results or two-engine acceptance.

## Remaining native integration gates

There is still no admitted task/SDK/GUI dispatch or project-store route. Before any
production entries: finish runtime/security and rights decisions; qualify and
separately authorize the proposed frozen setup; verify its actual receipt; freeze
immutable native source/runtime/reader identities and a clean native launch;
qualify the native file/network/IPC profile and owned supervisor; connect the
existing all-attempt ledger with all planned failures and explicit retries; verify
durable native prefixes, initialization, callback timing/RNG, cancellation/deadline,
descendant cleanup and native C15–C18. Historical locks, guards, readers, baselines,
tolerances, publication allowlists and the maintained two-task scope stay intact.
