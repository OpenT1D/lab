# 0082 — Install an identified source payload behind isolated processes

Date: 29 October 2026

Status: accepted for the internal OT-060 developer candidate.

## Context

Native tasks derive scientific source paths, protocols and selectors from their
module locations. Root tooling is not a simulation package. Simply installing
the `experiments` namespace would change those paths and retain checkout-only
Git, uv and `.venv` assumptions. Archived code cannot supply executable readers.

## Decision

Build a separate dependency-free wheel with a small facade and an explicit
original-layout source/data closure. Retain exact native bytes and a complete
installed payload descriptor. Do not rewrite legacy ROOT constants or forge an
existing desktop runtime manifest. The internal wheel version is a development
artifact identifier, not a published release or stable SDK promise.

Keep application provenance separate from native plan/reader identity. Retain the
complete verified application descriptor and its canonical hash with each new
installed freeze, and its small identity with each executing/importing attempt.
Reconstruction identifies the current application without replacing the original
records. The descriptor hash and wheel-byte hash are distinct identities;
stored labels and archived source do not grant execution authority.

Python API objects hold project paths, not expired store leases. Every operation
uses a fixed isolated installed worker, which acquires its own live project
lease. The POSIX virtual-environment CLI starts current CPython 3.12 by absolute
path with `-I -B -S`; it does not discover Python, uv, modules or readers through
PATH, cwd, PYTHONPATH or project/archive metadata. Normal Python API invocation
still trusts its host Python startup environment. Reuse live process ownership
for cancellation and cleanup; process isolation is not a hostile-code sandbox.
The broker owns a run-scoped cancellation event before dispatch can mutate a
project and through terminal sealing. Native worker handlers retain their own
lifecycle. For admitted execution, queued cancellation before worker launch seals an interrupted
forensic attempt without starting native work.

Add a narrow shared-services installed execution backend. MMTT uses the current
identified standard-library interpreter without uv or Git. M4 native execution
is an explicit unavailable capability under the current public runtime policy,
even if a caller plants a checkout environment. Passive native inputs and fixed
matching readers remain available. No native installation is performed.

## Consequences

The first upgrade matrix tests a facade-build change with identical scientific
reader bytes and rejects changed native readers. Preserve original freezes,
all attempts, raw variates, source snapshots and authoritative reports. A full
M4 installed migration still requires admitted native execution and complete
relocation evidence; other hosts, broader upgrades, distribution and independent
user/scientific acceptance remain separate gates. Checksums verify consistency,
not authenticity against rewriting an entire installation.
