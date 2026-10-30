# 0084 — Thin installed project GUI and formative preparation

Date: 2026-10-29. Status: accepted for bounded internal implementation.

## Context

The shared-core queue's fourth increment consumes the installed MMTT and native
M4 project services. Their verified plans, attempts and readers already supply
the selected technical boundary. A browser interface must preserve that ledger
and scientific authority while preparing an observable intended-user exercise.

## Decision

Add a small loopback GUI to the dependency-free installed SDK. Its controller
calls the public SDK API for examples, validation, freezes, execution, explicit
runtime attachment, reconstruction and complete project relocation. Expose
read-only frozen-plan detail and parent metadata through that same API. GUI
handles, job state and report pointers are convenience state; the SDK project
remains authoritative. The existing checkout GUI and all 196 native source and
condition files retain their identities.

Bind to `127.0.0.1`, use an unpredictable session token with exact Host/Origin
validation, bounded JSON and fixed routes. Inventory all GUI assets in the
installed artifact. Never serve arbitrary paths, render archived HTML or choose
code/runtime from a project. View/download only fixed report files from an
explicit successful SDK reconstruction, with byte hashes checked on access.

Allow one active SDK action per GUI workspace. Execute it in a tracked
non-daemon thread. Run cancellation uses the existing SDK Event. Server shutdown
rejects new work, cancels the active run and waits for owned cleanup; other
project actions drain before exit so a metadata transaction is not killed.
Browser-tab closure does not stop a run. An unobserved process crash remains
unfinished evidence and never grants saved PID authority or automatic recovery.

Prepare version-bound neutral task cards, a facilitator key and blank observation
records for the shared-project exercise. Keep participant answers separate from
the key. Technical rehearsals populate no human observations. No participant,
independent user acceptance or performance advantage is inferred. The historical
GUI exercise and OT-056 comparisons retain their own scope.

## Consequences and checks

Keep the numerical functions, protocols, locks, criteria and reports unchanged.
A new artifact needs a newly created attachment for execution, while identical
trusted reader bytes reopen old projects without an attachment. Verify an actual
installed GUI outside a checkout, shared GUI/CLI plan and attempt identities,
MMTT and M4 results, cancellation/shutdown, restart, relocation and exact report
bytes. Challenge HTTP framing/authentication, unsafe paths, concurrent requests,
tampered reports and changed attachments. The integration owner alone runs the
final full repository check. Other native hosts, distribution rights, independent
usability and biological evidence remain separately gated.
