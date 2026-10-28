# 0074 — Integrate the private installer without widening public distribution

Date: 28 October 2026

Status: accepted for this private integration; release and publication deferred.

## Context

The Windows installer and public-source preparation were developed independently
from the shared main history. Main's common-laboratory direction remains valid.
The installer adds bundled runtime verification and a manual native build route;
source preparation restricts automatic native setup in a public snapshot. A
merge must retain both behaviors without treating an internal installer as an
approved public runtime distribution.

## Decision

Integrate main, the installer branch and preparation history on a new local
branch/worktree. Preserve numerical protocols, native locks, recorded failures,
private originals, explicit file-redaction identities and the new-public-root
export procedure. Keep the original development repository private; do not push,
run hosted CI/CD, tag or publish a release as part of this work.

Retain both the packaged runtime source inventory and publication-policy files
in new setup-plan source identities. In private source/installed candidates,
existing bundled runtime verification remains available and does not invoke a
host installer. In public snapshots, apply the native setup policy before any
installation/output, including when installed-package metadata is present.

Refuse Windows payload staging/building from a public source snapshot before
source copying, runtime download or output creation. The manual Windows workflow
is private-repository-only. An internal build from this private integration may
still exercise all implemented GUI routes, but it does not clear their runtime
or parameter-table distribution rights or known dependency advisories.

Retain decision 0070 for the common-laboratory plan. Assign 0073 to the installer's
branch-local former 0070 and update current navigation. The original installer
commits, old package source inventories and their historical paths/hashes remain
unchanged in the private archive. This numbering repair does not relabel J as a
build of the integrated source.

## Consequences

The initial public-source exercise remains the two synthetic standard-library
MMTT tasks. A public bundled installer requires an explicit distribution decision,
complete asset/notices and security review, the applicable Windows lifecycle and
workflow evidence, and independent acceptance for the claims made. Preserve
old locks/readers rather than silently upgrading scientific identities.

The [integration record](../research/installer-publication-integration.md) owns
actual local checks and remaining limits. Old Windows J evidence remains bound
to its original build; host tests and synthetic artifacts do not establish a new
Windows build, full VM acceptance, independent use or scientific validity.
