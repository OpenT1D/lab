# 0062 — Expose existing synthetic M3 workflows in the local GUI

Date: 4 October 2026

Status: accepted; implemented and internally verified locally in the separate
[acceptance record](../research/m3-gui-verification.md).

## Context

OT-030 supplies frozen-predictor comparison on common synthetic support.
OT-035/040 supply owned GUI operations; OT-041 retains maintained M4 archives.
The M3 CLI already owns the causal forecast and coverage conventions. The GUI
currently has no M3 configuration, execution or durable-reader route.

## Decision

Implement OT-042 as a GUI adapter for `m3-forecast` and `m3-compare`, without
changing historical scientific sources, protocols, frozen models or locks.
Reuse the fixed CLI for fixture creation, metadata checks and execution, and
the fixed native standard-library readers for saved analysis. Keep a single
active operation across M3, M4, campaigns, library and durable administration.
Use owned processes, bounded deadlines and observed-identity cleanup. A restart
records interrupted jobs but never adopts saved PIDs or resumes a predictor.

The interface selects an allowed root and relative configuration, then uses
opaque input/candidate/configuration/run IDs. Intake rejects unsafe paths and
human declarations. Explicit preparation copies original synthetic configuration,
declarations, source, settings and observation bytes into an owned freeze;
retain original configuration and record byte access and path/roster adaptations.
This preparatory access is separate from native access history. Native metadata
checks still do not inspect observation content or execute a predictor. A run
requires matching current frozen identities and successful readiness evidence.

Show native JSON/Markdown with complete planned denominators and unsuccessful
cases; do not pool candidate support or calculate new numerical criteria in the
browser. Execution state, native-reader success and complete cohort are separate.
Cancellation may leave an unsealed forecast without a reconstructible report.
A sealed partial comparison can retain an unsealed child as native diagnostics.

Add explicit durable task mappings: forecast uses `experiments.m3.researcher
report --study`; comparison uses `experiments.m3.comparison reconstruct --study`.
They do not receive the M4 `--allow-failed` flag. The existing package /1 retains
its structure and strict trusted-reader identity. M3 completeness comes from
native `evaluation.complete_cohort` or `common.complete_cohort`. Any present
original top-level report must match fresh authoritative evidence at export.
Missing reports are permitted only when the native sealed reader succeeds;
never synthesize them into original archives. Existing M4 tasks remain supported.

Raw interrupted retention is a distinct operation and schema. Copy all available
owned archive files/directories to a fresh opaque child of the explicit startup
external store, with an inventory and provenance receipt. Enforce the existing
bounded filesystem protections, source stability and no-overwrite publication.
It makes no verified-package, scientific validity or reconstructibility claim,
and has no executable import, resume or archived-PID authority.

## Acceptance and limits

The roadmap owns the required CLI, browser, relocation, failure, tamper,
process and M4 regression checks. Retain raw acceptance evidence outside
implementation worktrees. Agent verification remains internal. Independent
human usability, authorized empirical evaluation, hosted checks and main/GitHub
publication are separate. Revisit wider tasks, human input or storage backends
only with a separately specified consumer and evidence contract.
