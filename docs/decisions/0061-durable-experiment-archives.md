# 0061 — Preserve maintained M4 experiments outside disposable worktrees

Date: 4 October 2026

Status: accepted for implementation; verification is recorded separately.

## Context

OT-038–040 deliver maintained campaigns and a local experiment workspace.
The main integration record reports that ignored native archives, receipts and
logs are unavailable at their original worktree paths. Git retains code and
historical recorded identities, but does not retain those ignored bytes. A GUI
report download and a library pointer do not preserve a complete experiment.
This increment cannot recover the unavailable historical artifacts.

## Decision

Implement OT-041: durable export, integrity verification and restore for
`m4-study-secure` and `maintained-campaign` only. Use the separate
`experiments.durable_archives` namespace and directory package
`opent1d.durable-archive/1`. Preserve all original native files, empty
directories, unsuccessful attempts and session history byte for byte. Retain
historical absolute paths as provenance; do not rewrite them during relocation.
Historical numerical sources, protocols and locks remain unchanged.

A package contains `manifest.json`, `archive/`, `reader/` and `evidence/`.
The manifest inventories every other file and directory, with sizes and SHA-256
identities. `reader/` preserves the full tracked bytes of one explicitly
trusted clean Git checkout at its full revision. Verify working bytes against
Git objects, including files hidden by index flags. These snapshots remain
data: neither packaging nor reconstruction dispatches code from the package.
The package is bounded to 50,000 files, 100,000 entries, 256 MiB per file,
2 GiB total and an 8 MiB manifest. Hash and copy streams without accumulating
the complete package in memory. Reject unsafe ancestor paths, links, special
files, noncanonical paths and case/normalization aliases.

Export first runs the fixed authoritative reader with failed/incomplete
coverage permitted. Record successful reconstruction separately from numerical
completeness, and preserve its receipt and outputs outside the native inventory.
Require unchanged source and reader inventories around export. Use fresh
owned staging and publish without replacing an existing destination. Restore
copies the complete integrity-verified package to a fresh destination, without
model execution, installation, repair, resume or adoption of saved PIDs.

`verify` establishes package byte consistency only. Explicit reconstruction
requires a caller-trusted clean checkout at the recorded full revision, with
its full tracked bytes matching the preserved reader inventory. Execute only
the two fixed reader commands with `-B -E -s -S`, no inherited Python selectors,
owned bounded processes and a reader deadline of 120 seconds by default.
The caller may select 1–1800 seconds; package operations are bounded to
900 seconds; the effective reader deadline is capped by its remaining budget.
Owned cleanup can follow the deadline. A manifest or archived source never selects a module, interpreter,
Git operation or executable. Hashes alone do not authenticate an experiment. Export/restore destinations
remain outside the reader checkout. Fresh reconstruction output may use its
Git-ignored `results/` subtree, while package/native/tracked-file overlap stays
forbidden and the full tracked checkout is rechecked before and after.

The GUI adds an optional explicit startup `--archive-store PATH`: an existing
canonical directory outside this checkout. It may create only fresh opaque
package children there. Treat the store as an explicit read-only library root
for subsequent browsing; preserve existing archives and packages. Export,
registration, integrity recheck and reconstruction use the shared one-active
operation lock and owned workers. Registration uses an allowed root ID and
relative directory; no browser-supplied checkout, executable or absolute path.
The GUI reconstructs only with its currently trusted clean checkout. A reader
identity mismatch directs the researcher to the explicit compatible-checkout
CLI route; it does not fetch, install or select archived code automatically.

## Alternatives

Keeping archives only in ignored worktree directories repeats the observed
retention gap. Report-only downloads omit inputs and attempt history. A general
compressed archive/import framework is unnecessary for these two consumers;
a bounded directory package avoids compression and extractor semantics.
Automatic archived-reader execution would turn preserved data into executable
trust and is rejected. Broader task support needs a separate bounded decision.

## Acceptance

Export a native maintained study and campaign, retain a failed or interrupted
attempt, and reconstruct restored evidence from a second clean checkout after
the original archive path is unavailable. Compare complete native file and
directory inventories, report content and planned/accepted denominators.
Refuse tampered, missing, additional, unsafe or incompatible package members,
changed readers and overlapping/existing destinations. Exercise GUI export,
registration, recheck, failure labels and current-reader mismatch in a browser.
Preserve raw acceptance artifacts outside the implementation worktree.

## Consequences and revisit conditions

This increment improves retained software evidence; it does not add physiology,
human observations, independent usability or clinical validity. The selected
next implementation is OT-041. M3 GUI support is the subsequent proposed feature,
and the prepared independent researcher exercises remain separate external
acceptance work. Broader compatibility or storage backends require demonstrated
consumer need. Hosted CI remains open while Actions minutes are exhausted;
main publication remains a separately requested step.
