# OT-062 LT1 frozen setup packet and fixture qualification

This increment implements a bounded data-only stager and a separate setup-request
authority. It qualifies invented archive/byte fixtures, not an LT1 installation.
The [selected payload and risk record](ot062-lt1-qualification-packet.md) owns the
exact proposed assets and known zlib issue. The
[original runtime/use proposal](ot062-runtime-rights.md) still owns gates A–E.

## Decision and authority

[ADR 0097](../decisions/0097-lt1-setup-request-authority.md) separates authorization
to materialize one exact packet from later review of its actual setup receipt.
The new [request registry](../../experiments/lt1_diagnostic/setup-request-admissions.json)
starts empty. The existing native setup-receipt and execution lists remain empty.
Unknown request bytes refuse before JSON parsing, supplied path intake or output.
No worksheet field, fixture registry, claimed approval or archived code is loaded
as production authority.

The [public worksheet](../../experiments/lt1_diagnostic/setup-decision-worksheet.json)
is a redacted preparation example. The actual decision owner/reviewer identities
are recorded privately. Use/users/host, private storage/access/retention, exports,
parameter/default and remaining notice disposition, risk acceptance and approval
still require their actual decision. No names, private host/storage paths or
hash of the private personal worksheet are published. Public source and PRs,
including their ordinary GitHub account/commit metadata, remain public.

## Packet contract

[frozen_setup.py](../../experiments/lt1_diagnostic/frozen_setup.py) binds an exact
request schema to host/platform/architecture, canonical owner-only parent and new
attempt name, current stager/Python identity, input sizes/hashes, destination
sizes/hashes/modes and three review-receipt byte IDs. The actual rights/security/
harness decisions and authentic source/archive provenance must be reviewed before
admitting that request. The code compares their bytes; it cannot decide rights
or accept runtime risk on behalf of a person.

All supplied inputs are read and compared before output creation. Input snapshots
must be bounded ordinary single-link files; changed snapshots refuse. The in-memory
request maps admit at most 4,096 files, 128 MiB per file and 512 MiB aggregate input
and output bytes. Paths are at most 512 characters/16 components and the
payload has at most 128 directories including its root. Requests are at most 4 MiB. Acquisition must already be bounded;
these are data limits, not a hard process RSS/CPU sandbox.

[setup_payload.py](../../experiments/lt1_diagnostic/setup_payload.py) reuses the
existing bounded archive preflight and exact payload selector to prepare selected
package bytes in memory. It does not install an environment. Each real native
packet still needs reviewed Node binary/full-license, LT1 source/config and
complete package/loader/input provenance; no native packet or setup-request
admission is supplied by these fixtures. Functional TypeScript/native loading
remains unrun.

## Materialization and reconstruction

The POSIX backend creates a new 0700 attempt directory and retains descriptor
bindings for its payload tree. It uses no-follow, exclusive regular-file writes,
readback hashes, file/directory fsync and fixed 0400/0500 file modes. Payload
directories finish at 0500; the private evidence root remains owner-only.
Names use a bounded ASCII subset with case aliases, traversal, trailing dots and
file/parent collisions refused. No archive mode, link, device or script is adopted.
Windows is refused; native Darwin arm64 setup requires additional clean-startup
and separately qualified host evidence.

The full byte inventory is published through an exclusive atomic marker after
validation; pending records and failed prefixes are retained for inspection.
The reader checks externally retained request/manifest hashes, current source,
strict schema/limits/receipt identities, exact file bytes/modes/namespace and
absence of pending/failure/foreign entries. It opens no archived code. Review
caught and corrected false acceptance after directory rebinding and replacement
of a pending inventory, plus missing reader aggregate/schema checks.

`materialized.json` always reports `setup_admitted: false` and
`native_execution_authorized: false`. An atomic marker does not prove outer process
success, cancellation/deadline cleanup or a completed native setup. A failed
outer process cannot be promoted merely because a marker exists. A separate
supervised actual setup receipt must bind the request, output/source inventories
and process evidence, be independently verified, and only then be admitted by the
existing receipt authority. No automatic admission/update is implemented.

## Qualification scope

The [core tests](../../tests/test_lt1_frozen_setup.py) use fixed invented bytes:
complete output/readback, empty production refusal, changed input/source,
traversal/case alias/file-parent/mode refusals, existing-output preservation,
private-parent requirements, retained write/publish failures, namespace changes,
hardlinks/unexpected data, reader schema/bounds and both race regressions.
The [package tests](../../tests/test_lt1_setup_payload.py) prepare an invented
archive, omit its explicitly selected browser member, preserve its notice and
materialize/reconstruct the exact selected bytes without executing them.
The [owned child cases](../../tests/test_lt1_setup_process.py) exercise the
existing supervisor against a scripted Python stager stopped after a validated
prefix and during pending-inventory publication. These are setup fixtures, not
native C15–C18 or a general process-confinement qualification.

Source identity records the named implementation files, existing package
initializers, Python executable bytes and version. This does not cover the whole
bootstrap, import cache, standard library, dynamic libraries or OS state.
`-I/-S` alone is not that qualification. Mode/UID checks do not establish complete
ACL semantics or protect against an arbitrary hostile owner. The actual immutable
launch/source environment, source/config/module closure, denied network and
extra-module/addon enforcement require separate host/risk review. The current
Node worker rejects all `execArgv`; no permission/no-addon flag is implicitly
admitted by this setup component.

Actual native setup/receipt verification, native loader success and host execution
remain unrun. No historical lock, worker guard, scientific reader, baseline,
tolerance, publication allowlist or SDK/task/GUI dispatch changes.
