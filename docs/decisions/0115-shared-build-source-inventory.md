# 0115 — Shared build source inventory

Date: 22 November 2026

Status: accepted.

## Context

The SDK, application builders, M4 runtime preparation and integrated candidate
qualification all bind build records to actual tracked source bytes. They
previously obtained this inventory from the Windows installer builder.

## Decision

Place the Git inventory in `scripts/build_source.py` and have each caller
use it directly. Preserve the file filters, limits, exact Git blob and SHA-256
checks, and the `revision`, `dirty` and `files` fields. Callers retain their own
clean-source policy, rechecks, staging, runtime admission and receipts.
Support direct script invocation and module import.

## Alternatives and consequences

Keeping the helper in the Windows builder would retain a platform-specific
dependency for all callers. Copying it into each builder would make checks and
receipt fields harder to keep aligned. The shared module keeps one source
identity contract. Revisit it if a build needs a different source format or
hash policy, with explicit verification of the affected receipts and callers.
