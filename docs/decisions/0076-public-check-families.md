# 0076 — Shared public check families and one required result

Date: 28 October 2026

Status: accepted; hosted platform acceptance remains separate.

## Context

The public exercise consists of two standard-library synthetic MMTT tasks.
Root checks combine static checks, contracts, controlled DOM tests and Sphinx.
Historical numerical jobs require explicit private-archive dispatch. Adding
platform and real-browser checks must preserve that boundary and the stable
required status instead of making skipped dependencies appear successful.

## Decision

Keep one local repository command with the existing complete order. Expose
`style`, `tests` and `docs` stages for focused work; style includes metadata and
navigation. Retain one broad Linux root job, its `repository-checks` ID, outputs
and historical native steps; display it as `Root checks`.

Use the same explicit public smoke runner locally and on Linux x64, macOS arm64
and Windows x64. It selects real-host cases before running them and fails on
missing cases, empty suites and any skip. Reuse existing CLI/file/process cases
and add HTTP flows with a separate workspace and explicit interpreter. Windows
uses its Job/control-pipe cases; POSIX signal tests do not stand in for them.

Run the four synthetic browser flows in one Linux Chromium job. Keep browser
workers at one and retries at zero. Broader browser/OS coverage needs its own
evidence, including server shutdown behavior.

Only the final public job has the visible name `Repository checks`. It always
evaluates the explicit root, OS-smoke and browser dependencies and accepts only
`success` from every family. Failure, cancellation, skip, missing or additional
family results fail closed. Native jobs are not dependencies of this gate.

Keep the fifteen native job IDs, literal private/manual guards, native root
steps, historical locks and the exact Action allowlist. The historical sixteen
status policy remains the fifteen native names plus the stable public gate;
public policy requires only that gate. Policy tests classify both rosters
explicitly. Retain compact synthetic diagnostics for five days.

## Alternatives and consequences

Separate required statuses would couple branch protection to matrix names and
make later changes harder. Splitting the root suite into many jobs or a full
OS/Python matrix would add unmeasured setup and portability work. Keep those
choices open until hosted duration and failure evidence justify them.

This decision creates a verification contract, not platform qualification,
scientific validity, a release or an activated service. Exact PR/main hosted
results and protected-branch behavior remain acceptance requirements. Revisit
the selection when supported tasks/platforms change or measured runtime warrants
a smaller root job or further families.
