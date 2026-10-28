# 0060 — Maintained campaigns and the local experiment workspace

Date: 4 October 2026

Status: accepted for implementation; execution evidence is recorded separately.

## Context

Decision 0059 delivers one maintained M4 study through a local GUI. Historical
local campaigns select the original `m4-study` runtime. Existing CLI archives
also remain outside the GUI's own job journals. Researchers need maintained
repeated execution and access to previous evidence before campaign GUI control.

## Decision

Implement two internal goals in isolated branches. Goal 1 delivers a separately
versioned maintained campaign CLI and a read-only GUI archive library in
parallel. Goal 2 adds GUI campaign management after Goal 1 acceptance. The CLI
and fixed authoritative readers remain the scientific execution boundary.

Use `MAINTAINED-CAMPAIGN/1`, `opent1d.maintained-campaign-config/1`,
`opent1d.maintained-campaign/1` and `opent1d.maintained-campaign-report/1`
for the new `experiments.maintained_campaigns` namespace. Select only
`m4-study-secure`; retain existing matrix/repetition bounds, frozen inputs,
immutable attempts, sealed sessions and explicit identity-checked resume.
Historical campaign modules, protocols, numerical equations and locks remain
unchanged. The successor's source inventory is explicit and excludes GUI code.
There is no tuning, pooled scientific result or new physiological mechanism.

Allow the maintained native owner its existing twenty-second cleanup window.
The campaign parent allows thirty seconds outside its execution deadline.
The GUI campaign parent allows ninety seconds for nested cleanup, inventory,
reporting and session sealing, also outside its execution deadline. A hard kill
can leave forensic, unsealed evidence; it does not authorize automatic repair
or reuse. Preserve planned slots and all unsuccessful attempts.

The library accepts only explicitly configured canonical archive roots at
startup: the workspace plus repeated `--archive-root PATH` arguments. Expose
opaque root identities and relative paths. Freeze and revalidate root and
entry identities; reject symlinks, special files and path escapes. Keep original
archives read-only and place derived reports and administration in the GUI's
own workspace. Do not broaden source/configuration/output path permissions.
Use bounded owned subprocess workers for catalogue indexing and reconstruction;
Library HTTP methods do not perform full archive traversal or numerical execution.

Show passive catalogue metadata for eight existing scientific tasks. Full GUI
native verification and report/figure access initially select maintained M4
only. Historical compatible readers remain available through their explicit
CLI path; an archive never selects arbitrary Python or a module. Metadata,
recorded verification, current verification, numerical acceptance and report
completeness are separate. Library verification labels a worker-verified snapshot and explicitly marks source
freshness as not rechecked during passive browsing. Detected identity/report
changes, failed explicit rechecks and restarts withdraw live verification.

Preserve loopback binding, same-origin session checks, the workspace manager
lock, one active operation and observed process start identities. Reuse fixed
argv without a shell. Saved PIDs do not establish ownership after restart.
Source Python is trusted local researcher code; this service is not a sandbox.

## Acceptance and evidence

Freeze integrated scientific sources before definitive numerical assessment.
Run two declared synthetic configurations with two repetitions, interrupt the
second slot after the first succeeds, resume and retain the interrupted attempt.
Verify accepted reuse, a no-op resume, failed-source accounting, tamper refusal,
model-free reconstruction and original archive byte preservation. Exercise GUI
library success/failure, changed/restarted verification, downloads, bounded
nonregular inputs, cancellation, keyboard/mobile operation and stale selection.
Goal 2 additionally verifies GUI/CLI scientific parity and nested cleanup.

Use locked repository checks and task-specific numerical, process and browser
checks. Agent review is internal verification. Independent human GUI use,
biological validity and human-data assessment remain separate open items.
Exhausted Actions minutes leave hosted verification open; no billing or
repository protection change is part of this increment.

## Consequences

The increment adds experiment management around existing synthetic science.
The canonical roadmap and English guides own scope and commands. Publication
to main remains a separately requested step. The M3 GUI remains later work.
