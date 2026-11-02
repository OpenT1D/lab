# OT-062 LT1 notice inventory and qualification preparation

This increment closes a bounded **passive archive preflight** prerequisite for the
proposed frozen setup. It does not perform setup or native qualification. The
[authentication and journal record](ot062-lt1-auth-integration.md) remains the
canonical account of the authenticated Node archive and invented journal checks;
the [original runtime/use proposal](ot062-runtime-rights.md) owns gates A–E and
the prospective C15–C18 criteria.

## Exact headless notice evidence

[headless-notices.json](../../experiments/lt1_diagnostic/headless-notices.json)
now records each of the twenty exact archives selected by the unchanged historical
headless lock: lock placement, version, registry URL/SHA512 integrity, archive
SHA256, package metadata SHA256, declared license and recognized notice-member
paths/lengths/hashes. Retained archive bytes independently match the lock's SRI.
There is no resolver, new dependency, lock update or package-manager invocation.

The package-level declarations are seventeen MIT, one BSD-3-Clause (`diff`), one
ISC (`make-error`) and one Apache-2.0 (`typescript`). These labels describe package
metadata, not every embedded asset. Twenty-two recognized notice files include
`ts-node/dist-raw/NODE-LICENSE.md` and TypeScript's full `ThirdPartyNoticeText.txt`.
The latter includes DefinitelyTyped/MIT, Unicode, W3C, WHATWG/CC-BY-4.0,
Web Background Synchronization and WebGL material, including the W3C Community
Final Specification Agreement. Retain the complete bytes; do not replace that
file with an Apache label or a shortened summary. TypeScript's
[upstream license](https://github.com/microsoft/TypeScript/blob/v5.7.3/LICENSE.txt)
and [third-party notices](https://github.com/microsoft/TypeScript/blob/v5.7.3/ThirdPartyNoticeText.txt)
are separate inputs to the review.

An explicit gap remains: `@cspotcode/source-map-support` includes
`browser-source-map-support.js`, a Browserify bundle with inlined modules whose
complete ancestry and notices have not been established by the recognized-file
roster. The passive package count does not imply that this inlined closure is
reviewed. Before setup, either establish and preserve its exact source/notices or
review a newly identified payload excluding unused content and qualify that new
payload. The separate selection proposal below makes that exclusion explicit;
it supplies no clearance for the original complete archive.

The [rights dossier](../../experiments/lt1_diagnostic/rights-dossier.json) keeps
personal role fields redacted; the owner and reviewer are recorded privately.
It still requires their actual decision, users and named host, storage/access,
retention, approved exports and parameter/default ancestry disposition. Complete
Node LICENSE, LT1 source notices, headless package notices and the separate
private verification utility remain distinct. The [Node license](https://github.com/nodejs/node/blob/v22.23.4/LICENSE)
contains multiple component terms; selecting only the binary does not discard
those notices. Scholarly citations are not a substitute for asset rights. No
native settings, default table, state, trajectory or report is published.

## Bounded in-memory preflight

[archive_preflight.py](../../experiments/lt1_diagnostic/archive_preflight.py)
reads only supplied byte strings. It compares the expected archive hash before
decompression. Expected entries must come from the reviewed inventory; a
producer-supplied expected digest only checks its own bytes. The preflight caps
compressed and expanded bytes, member count and individual
files, and rejects traversal/noncanonical paths, different roots, links, sparse
or special members, GNU/PAX extension records, duplicate paths and file/directory collisions.
Raw 512-byte headers are checked with the standard-library header decoder before
GNU/PAX records can disappear inside high-level tar iteration. Path/collision
checks use lexical POSIX names; case folding and Unicode filesystem aliases are
a separate future stager/host obligation. It checks exact package metadata bytes and name/version/license, then each
recognized notice's byte length and hash. It returns all regular member hashes
and explicit directory names. It does not call tar extraction, create files,
import archive code, launch a process, access the network or grant permission.

Limits are 32 MiB compressed, 64 MiB expanded, 2,048 members and 32 MiB per file.
The caller must bound acquisition before passing bytes; this is not a streaming
acquisition service or a hostile-input memory sandbox. Decompression and member
payloads are bounded but Python's total RSS is not hard limited here. The exact
retained twenty archives pass with 510 regular files and 27,232,179 payload bytes.
Their full byte inventories remain private. This is layout/identity evidence,
not TypeScript resolution compatibility, a complete license closure or runtime
safety. The returned authorization fields remain false.

The [invented archive controls](../../tests/test_lt1_archive_preflight.py) challenge
traversal, backslashes, links/specials, duplicate members, collisions in either
order, altered hashes/metadata/notices, missing notices, duplicate JSON keys,
compressed/expanded/member/file limits and truncated gzip. A separate control
binds the public twenty-entry inventory back to the historical lock without
fetching packages. Actual retained archives are assessed separately, not downloaded
or installed by root tests/hosted CI.

## Separately identified no-browser payload proposal

[headless-selection.json](../../experiments/lt1_diagnostic/headless-selection.json)
binds each original archive and its complete file map, then excludes one exact
53,583-byte `browser-source-map-support.js` member. The resulting 509-file,
27,178,596-byte proposal preserves all 22 recognized notice files, package
metadata and historical lock bytes. Original archives remain unchanged.
Source, selected and retained-notice maps have separate canonical JSON hashes;
target paths explicitly use `toolchain/node_modules/` placement.

[payload_selection.py](../../experiments/lt1_diagnostic/payload_selection.py)
checks the reviewed profile digest, notice-inventory bytes, complete package
roster, exact preflight file maps, exclusion bytes and unchanged notices. Its
inputs must come from genuine retained archive preflight evidence; matching
producer-supplied metadata hashes alone cannot authenticate archive consumption.
The pure function returns a proposed file map and closed authorization fields.
It creates no files, loads no engine and supplies no setup receipt.

Passive source inspection found the excluded name only in the bundle itself,
package metadata and README across the 510 supplied regular files. The package
main entry is `source-map-support.js`, with declared `@jridgewell/trace-mapping`
dependency. This motivates the proposed exclusion, but its generic `require`
hook prevents a claim that name searches prove every computed resolution path.
Actual loader compatibility, full remaining embedded-content rights and the
target filesystem's alias/collision behavior still require qualification.
No selected native environment has been constructed.

## Refined runtime disposition from source and binary data

[runtime-disposition.json](../../experiments/lt1_diagnostic/runtime-disposition.json)
records the new passive observations separately from the historical assessment.
The exact archive signature remains authenticated by the prior record; this
increment does not rerun the verifier or execute the candidate.

Both pinned `gzwrite.c` copies are byte-identical to
[upstream zlib v1.3.1](https://github.com/madler/zlib/blob/v1.3.1/gzwrite.c).
They predate the [nonblocking retry implementation](https://github.com/madler/zlib/commit/81cc0bebedd935daeb81b0b6e475d8786b51af3d)
and lack its `gz_vacate`/`state->again` path. Before the error is cleared, their
older write-error path treats negative writes as fatal and returns before the
subsequent move operation.
Therefore absence of the [later correction](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148)
alone was insufficient to classify the older path. A fresh review located the
[maintainer's 27 October adjudication](https://github.com/madler/zlib/issues/1292#issuecomment-6456517984):
the old corruption route after `gzclearerr()` is also covered by CVE-2026-85091.
Clearing the error revives stale external `next_in`/`avail_in`; fatal `Z_ERRNO`
alone therefore cannot support a non-applicability decision. The embedded older
C-library path is known affected; selected Node API/packet reachability remains
a separate question. The open Node [26](https://github.com/nodejs/nodejs-dependency-vuln-assessments/issues/467)
and [24](https://github.com/nodejs/nodejs-dependency-vuln-assessments/issues/492)
assessment issues do not supply Node 22 clearance.

Passive review of all 18,714 regular `src/lib/deps` members in the authenticated
source archive found no client of the reviewed writer/error/open API names
(`gzwrite`, `gzfwrite`, `gzprintf`, `gzvprintf`, `gzclearerr`, `gzopen`, `gzdopen`)
outside the zlib trees and their test. The Node binding uses deflate/inflate streams, without an identified
supported JavaScript gzFile entrypoint. These source observations do not prove
absence of dynamic/binary reachability. They support only a named risk decision
for one immutable trusted research packet, with actual extra-module/addon,
startup and host enforcement still to qualify. The current worker rejects every
`execArgv` option; permission/no-addon flags cannot be assumed without a reviewed
successor guard.

Independently checked Mach-O data from the authenticated binary contains external,
non-debug `_gzwrite`, `_gzprintf` and `_gzvprintf` symbols with addresses inside
`__TEXT,__text`. Consequently, assuming all gzip writer code was omitted or
discarded by the linker is unsupported. Symbol presence does not establish a
supported JavaScript call path, exploitability or exact build reproducibility.
No binary was written to disk or executed during inspection.

Embedded build metadata declares minimum macOS 11.0.0, SDK 15.0.0 and linker tool
3/version 1115.7.3. These are observations from the artifact, not a reproduced
compiler/SDK/build receipt or qualification of the actual host's libraries and
frameworks. Full security/build/OS, formal rights and native host decisions remain
open. No production admission or historical evidence record is rewritten.

## Concrete native qualification work, still unrun

The following packet identifies evidence still required for LT1. It is a coverage
and instrumentation review, not a runnable campaign or an execution request. A
later frozen all-attempt roster must identify each mode/reset/repeat/fault/stop
slot, exact input/source/runtime/reader bytes, operator/host and separate setup
and execution admissions before launch. Preserve unavailable and unattempted
slots and explicit retries; no success-only denominator is acceptable.

| Coverage | Concrete evidence and oracle | Current gap |
| --- | --- | --- |
| Historical reference | Applicable unchanged M0/M2 reference criteria and wrong-replay negative controls, with their original horizons/controllers/runtime identities | The new 30-minute sampled diagnostic cannot replace an unavailable or failing historical reference; no historical runtime admitted here |
| C15 native basal and reset | Independently record native equilibrium/basal provenance and units; direct/wrapped fasting runs, two resets in one process, then fresh-process repeats; exact serialized scientific equality | The fixture's 1.2 U/h is not an established native basal. Current worker runs one attempt and finish; a same-process reset qualifier needs its own reviewed source identity |
| C15 seed identity | Preserve seed 101; reject unsupported LT1 seed 102 before engine execution; identify each changed input separately | Do not widen the old seed guard or interpret a deterministic unchanged value as proof of identical input identity |
| C16 ordinary event and filtering | Actual 40 g meal at minute 15 for 15 minutes; separate 20 g announcement; minute-10 sample delayed to minute 15, minute-15 sample masked after generation; unfiltered native controls | Current invented template is the separate fractional-event case. Freeze this ordinary native plan independently; verify unchanged raw sampling/noise/RNG consumption |
| C16 future and fractional controls | Reidentify an 80 g future-meal case and require identical pre-event prefix; independently test minute-2.5 start/1.5-minute duration with exact source/release timestamps | Preserve both ordinary and fractional cases. The 32-row/25/48 U fixture is no native numeric oracle; derive native delivered amount from admitted rows without endpoint padding |
| C17 initialization and export faults | Invalid/nonfinite initial state, failure after two complete intervals, truncated output, combined native/export error and terminal diagnostic-only tail | Need fault injection tied to actual native/source boundaries; retain primary and diagnostic errors separately and never score an uncommitted journal record |
| C17 process stops | Cancellation before initialization and while blocked, deadline and forced termination, each with control and exact completed prefix | Actual Node startup/loader/native blocking must be observed; scripted Python/Node fixtures do not qualify this native behavior |
| C18 file/network/IPC and ownership | Named macOS arm64 host, actual Node/ts-node registration profile, clean launch environment, child/grandchild stop and unrelated sentinel start identity; coordinator crash/app-close cases | Existing Python host profile and separate signature utility profile cannot be reused as native qualification; module registration, threads/IPC/bootstrap access require review |
| C18 reconstruction | Copy complete, partial and failed attempts; remove original runtime/source/output availability; fresh trusted engine-free reader with externally trusted same-attempt artifact/process hashes | Native durable journals/store hashes not yet produced; exact report equality and appropriate failure/refusal status remain unrun |

The proposed diagnostic execution deadline is 300 seconds; cleanup has its
separate proposed 40-second acceptance bound, as in the original packet. Freeze
the observation/polling mechanism and retain its unobserved-orphan/escape limits.
Neither number is a physiological tolerance. Existing baseline values,
scientific tolerances, M2 guards, native workers/readers, publication allowlists
and task/SDK/GUI registrations remain unchanged.

Next setup implementation is still the separately reviewed data-only frozen
stager: exact path placement, no scripts/resolver/shims, fresh private root,
confined/atomic completion, notice preservation and retained failed evidence.
This preflight is only its read-only prerequisite. No runtime has been staged;
positive native TypeScript initialization, native process qualification and
C15–C18 remain unrun. Production setup/execution admission lists remain empty.
