# 0059 — Maintained runtimes and a local M4 GUI pilot

**Status:** accepted for internal implementation, 4 October 2026.

## Context

OT-032/033/034/037 provide configurable M4 studies, local campaigns, archive
indexing and explicit locked setup. OT-035 now selects this user problem:
a researcher should configure, execute, inspect and reconstruct one supported
synthetic initial-load study without manually composing JSON and several CLI
commands. Dependency alerts also identify affected HTTP and PyTorch runtimes.

Historical model, protocol, lock and result identities remain evidence.
Changing a frozen lock in place would invalidate its execution and archive
guards. Hash agreement and `weights_only=True` do not establish safe loading
with a vulnerable PyTorch version.

## Decision

Maintain root HTTP tooling with the smallest compatible locked change. Introduce
an explicitly identified maintained native execution runtime, preserving engine,
NumPy/SciPy, units, clocks, equations, numerical gates and historical protocols.
Freeze its successor execution identity before final numerical assessment.
Migrate both C1 PyTorch source projects coherently under a new runtime record,
checking actor construction, checkpoint intake, RNG ownership, causal actions
and bounded replay. Do not relabel historical training or method findings.

Preserve historical reconstruction through an explicit trusted reader checkout
and its full Git revision. A new `experiments.historical_readers` entry selects
only the seven existing scientific readers or the local campaign reader. It
uses current Python with `-B -E -s -S`, checks checkout cleanliness and archive
inventories, writes fresh output and retains supervised execution receipts.
It installs no historical dependencies and performs no Git mutation. An
archive never selects an arbitrary executable module.

The GUI is a loopback-only browser application for one M4 initial-load route,
with one active job. Its pilot accepts the existing two-to-eight declared
sources and selected 0/15/30 gram conditions, explicit existing budgets and
fresh output. The maintained runtime successor is selected explicitly.
Configuration becomes an immutable job input before execution. Existing
validators remain authoritative.

The GUI starts allowlisted CLI commands as subprocesses. It does not invoke
signal-installing supervisors from HTTP threads. Cancellation asks the native
owner to stop, waits for bounded cleanup and records incomplete evidence.
UI/job administration is outside scientific archive inventories. Recorded
process status, report completeness and native-reader verification are distinct.

Bind only to loopback, reject foreign Host/Origin requests and require a
per-session token for mutations. Use fixed argv without a shell, bounded
requests, explicit workspace paths and escaped text. Installation and model
execution require their own deliberate UI actions. Local Python sources remain
trusted code supplied by the researcher; the GUI is not a code sandbox.

## Verification and limits

Freeze CLI/GUI scientific parity, unchanged equations/core pins, native
refinement/repeat gates, archive reconstruction, failed-source accounting,
missing-runtime rejection, cancellation cleanup and browser operation before
acceptance runs. Preserve failures. Run the locked repository checks and
appropriate numerical and process/browser checks.

Internal delivery and intended-user acceptance are separate. Prepare a new
versioned GUI exercise for an independent researcher; do not substitute agent
testing or extend the historical P1 handoff permission to a new checkout.
No participant, execution date or empirical result is assigned. Hosted CI
remains conditional on the GitHub account restriction; local verification does
not establish hosted success, usability or biological validity.

## Implementation

The [execution plan](../research/ot035-maintenance-execution-plan.md) assigns
isolated worktrees, ownership and integration gates. Canonical English guides
and actual verification records follow implementation. Main is preserved
during this worktree goal; a release or main publication is a separate step.
