# 0071 — Separate public source history from private development evidence

Date: 25 October 2026

Status: accepted for local preparation; external publication remains pending.
Extended by [0072](0072-source-publication-rights-and-runtime-scope.md), which
records the subsequent source-only rights confirmation, withheld table fragments
and public installation/CI policy. The original decision below retains its scope.

## Context

The private development history contains personal commit metadata and local
computer paths. GitHub visibility applies to the repository rather than selected
old commits. Scientific records also bind historical source hashes, so a blanket
rewrite must not present redacted evidence as unchanged original execution bytes.

## Decision

Prepare an independent local Git root from the reviewed tracked source tree,
with a GitHub noreply author/committer and no copied objects, refs, remotes or
configuration from the private history. Preserve that original history privately.
Do not publish through a private-history merge, clone/mirror push or visibility
change of the development repository.

Redact personal computer prefixes in twelve historical source/receipt/plan
records and publish an explicit original-to-redacted file-hash map. Preserve
originals privately, retain recorded scientific hashes and results, and identify
the changed records as redacted copies. Keep numerical code, parameters, units,
protocols and locks unchanged by this privacy preparation. The `.source.txt`
probes acquire new identities; old archives may need their matching private
trusted readers. New source freezes identify the actual new bytes.

## Consequences

The [public-source guide](../public-source.md) owns preparation and compatibility
limits. The candidate must pass its own checks; old development results do not
become checks of its new root. Public readers cannot retrieve old private commits
merely because a historical ID remains in a scientific record. Published
attribution and the chosen reporting address remain visible intentionally.
External rights, content review, repository controls and independent-use decisions
remain open. A local prepared snapshot does not create a public release.
