# OT-029 and OT-030 multi-agent execution plan

**Status:** implemented and internally verified on the isolated worktree
branch, 2 October 2026. The [execution record](ot029-ot030-verification.md)
binds actual commits, native checks and remaining evidence limits.
Prepared on 2 October 2026 from local main `e77c9d7`, the completed OT-028
documentation update, [decision 0055](../decisions/0055-task-entry-and-m3-comparison.md)
and read-only reviews by three planning agents.

The [roadmap](../../ROADMAP.md#post-integration-internal-work-packages) owns
scope and acceptance. This record assigns implementation work and sequencing;
the existing task guides continue to own executable commands.

## Outcome and workspace

Deliver one local entry for the four supported researcher tasks (OT-029),
then a separately versioned comparison of multiple frozen M3 predictors on
one synthetic task (OT-030). Both must preserve existing numerical behavior,
source identities, failure archives and reconstruction.

Use the attached managed `researcher-tools-plan/OpenT1D` worktree on branch
`codex/researcher-tools-plan`, based on local main `e77c9d7`. The completed
OT-028 documentation and decision 0055 are carried into this branch. Root
owns Git operations. Agents work only in the assigned worktree and files;
they do not stage, commit, merge or modify the primary checkout.

At most four agents are active: the root integrator and three workers.
An additional agent is unnecessary for the first bounded implementation.

## Team and file ownership

| Role | Assignment | Exclusive write ownership |
| --- | --- | --- |
| Root / integrator | Freeze interfaces and protocol; integrate work, resolve cross-task choices, run acceptance and record evidence | Shared roadmap/status/decision/navigation/changelog files; final protocol approval; Git operations |
| Agent A / local entry | Implement task registry, metadata/runtime checks, explicit dispatch, reconstruction and report discovery | New `experiments/workflows/` package, `tests/test_workflow_entry*.py`, proposed `docs/local-workflow-entry.md` |
| Agent B / M3 comparison | Draft the new protocol and schemas; after review implement common-support analysis, coordinator and reconstruction | New `experiments/m3/comparison/` package, `tests/test_m3_comparison*.py`, proposed M3 comparison protocol and guide |
| Agent C / verification | Independently review A/B, prepare end-to-end acceptance and CI, audit provenance and failure accounting | New acceptance harness outside historical packages, its tests, `.github/workflows/checks.yml`; execution-evidence draft for root integration |

These package and guide paths are selected implementation targets, not
existing commands or implemented APIs. A owns the task registry even when B
adds comparison support. B owns comparison schemas and calculations. C owns
CI. Root alone edits shared documentation and final evidence/status. Reviewers
report corrections to the owner rather than editing the same file concurrently.

Leave historical P1, M3 researcher, M4 and M5 runner sources, their scientific
protocols and runtime locks unchanged. The existing M3 reader hashes every
Python file in its researcher package; even adding a file there changes its
inventory. New code and parent-level administration belong outside these
strict source/archive inventories.

## Phase 1 — freeze contracts before implementation

Root reviews A's entry contract and B's protocol/schema draft with C before
accepting the implementation contract. Commit the agreed protocol and schemas
before executing new assessment observations. Internal review is sufficient
for this software increment; it does not substitute for independent human use.

### OT-029 local entry contract

The planned checkout command is `python -m experiments.workflows`, with
`list`, `describe`, `check`, `run` and `reconstruct` operations. Register exactly
`p1-controller`, `m3-forecast`, `m4-secretion` and `m5-prognosis` initially.
Task-specific inputs remain explicit: P1 source/declaration, M3/M4 config and
M5 model bundle. Reject unsupported options; use structured subprocess
arguments and an explicit registry rather than shell or arbitrary-module dispatch.

`check` validates metadata, paths, source/settings/state identities and
present runtime requirements. It neither imports candidate code nor starts a
simulation or reads assessment observation contents. Clearly distinguish
unverified observation bytes from a validated execution. Existing P1 external
`preflight` runs a candidate smoke test and must not be reused as a passive
metadata check. Rights and training declarations remain researcher attestations.

Use the existing route-specific runners and report readers:

| Task | Execution runtime | Reconstruction capability |
| --- | --- | --- |
| P1 controller | Existing locked simglucose environment | Existing reader with root Python `-S`; fresh reconstruction directory |
| M3 forecast | Root environment; donor fitting/verification additionally uses the separate M3 runtime | Existing reader with root Python `-S`; fresh reconstruction directory |
| M4 secretion | Root orchestration plus the existing simglucose and beta-cell numerical environments | Existing reader with root Python `-S`; fresh directory and explicit failed-archive mode |
| M5 prognosis | Root standard-library worker environment | Existing reader verifies/rebuilds existing report bytes; it has no separate output-directory option |

Missing runtimes produce the appropriate `uv sync --locked` setup instruction.
Execution must not install or download an environment implicitly: verify
requirements first and scope the child uv environment with `UV_NO_SYNC=1`
and `UV_PYTHON_DOWNLOADS=never`, optionally `UV_OFFLINE=1`, including M4's
nested uv calls. No-sync alone does not disable Python downloads. Local
`uv run --help` confirms these settings; verify their inheritance and behavior
in acceptance. No package release or global CLI installation is required.

Preserve each route's timeout, interruption, process ownership, fresh-output
and archive rules. Show child exit status separately from scientific/report
completeness: a valid retained report can be incomplete even when the child
returns zero. Show report locations without inserting launcher files into
native archives. M5's report verification must not be replaced by file copying.

### OT-030 scientific and orchestration contract

B drafts a new versioned protocol before implementation. Its initial primary
comparison uses the **all-candidate intersection**, including every candidate
in the frozen roster and the shared persistence reference. Pairwise-support
analyses are deferred from this first increment; original per-candidate
persistence reports remain available with their own denominators.

Freeze at least two unique candidate identities, declaration/source/settings
hashes, synthetic observation identities, participant roster, bounds, planned
origins, prior-access disclosure, source/protocol/analysis identities, execution
order and finite worker budgets before observation access. Initially use the
same per-worker budget for every candidate and execute candidates sequentially
to avoid resource-contention differences. No fitting, tuning or winner selection
takes place in the coordinator. Known fixtures and repetitions stay known material.

Inherit six exact causal five-minute CGM values, 60-minute warm-up, exact
30-minute measured target, mg/dL, no interpolation/imputation, and the
existing participant-weighted error and bootstrap conventions. Common-support
eligibility requires all candidate workers for a person to complete, at least
288 shared scored origins, and at least 24 hours between the first and last
shared origin. This is origin span, not accumulated observation duration.

For every contributing person calculate each candidate's MAE and paired
difference from persistence on the same common origins; calculate direct
candidate-minus-candidate differences on that exact support. Average people
equally. If uncertainty is reported, preserve whole-person resampling:
2,000 draws, seed 301, inherited empirical percentile rules and null interval
with fewer than two contributing people. Freeze output fields and comparisons
before the first run.

Preserve every planned candidate/person/origin and failure prefix. Recompute
eligibility on common support itself, retaining all losses and full planned
denominators. Empty support yields null metrics with explicit reasons; failed
prefixes remain diagnostic even when numerically long enough. Never remove a
failed candidate from the roster to create a better comparison population.

Under the current M3 callback, a valid host history requires a finite prediction
or the worker fails. There is no successful per-origin abstention. Completed
candidates on identical host inputs therefore have identical scored-origin
availability. Unequal coverage is legitimately tested through failed,
interrupted or unattempted participant workers; different purported completed
histories, targets, persistence values or schedules must be rejected.

Persist a parent plan before invoking unchanged single-candidate studies.
Retain each child archive separately and validate it with the existing reader
before consuming its predictions. Parent protocol, inventory and report files
stay outside child archives. Parent reconstruction must verify child and
common-input identities and rebuild its JSON/Markdown report without original
observation paths, candidate execution or fitting. It does not independently
reproduce arbitrary supplied algorithms.

## Phase 2 — parallel preparation and OT-029 implementation

- A builds the local entry and focused tests from the frozen contract.
- B prepares reviewed protocol/schema details, hand-calculated numerical
  fixtures and isolated analysis while preserving existing M3 sources.
- C prepares the acceptance harness and clean-runner configured M4 check,
  and reviews metadata/execution separation and failure semantics.
- Root integrates their disjoint files, resolves interface questions and
  accepts OT-029 before registering the comparison task.

Freeze an agreed task description, runner invocation, input schema, runtime,
timeout meaning, status fields, report paths and reconstruction capability
for later `m3-compare` registration. A receives this contract from B; B does
not edit A's registry.

## Phase 3 — OT-030 implementation and integration

After root and C approve the protocol/support arithmetic, B implements the
separate coordinator, analysis and reconstruction. A registers `m3-compare`
only once the coordinator exists and meets its contract. C independently
reviews support, arithmetic, source inventories and semantic tamper handling.
Root updates navigation and acceptance scope without modifying historical
protocols or declaring synthetic performance to be human evidence.

## Phase 4 — clean-commit acceptance and completion

Stop agent writes, integrate reviewed changes and create a clean execution
commit before definitive native runs. Keep source/protocol/lock inventories
fixed throughout execution and reconstruction. A source change after a run
requires a new execution identity; do not alter archived provenance to make
it match. Each execution uses fresh output directories and preserves failures.

Acceptance covers:

1. **Entry semantics:** four tasks discovered/described; bad task options,
   invalid hashes/configs, missing runtimes and existing outputs rejected;
   an import-marker source demonstrates that `check` never executes it.
   Confirm nested uv dispatch performs no implicit sync/download and task
   completeness is not inferred solely from exit code.
2. **Real supported routes:** representative run/reconstruction through the
   entry for P1, M3, configured M4 and M5, including retained incomplete archives.
   Reuse existing source examples and numerical criteria. A fresh Linux CI
   runner executes the configured M4 path and reconstructs JSON/Markdown/SVG;
   mocks and the five isolated observer tests alone do not cover this route.
3. **Process/failure ownership:** route-specific timeout/interruption, retained
   prefixes and not-attempted cases, descendant cleanup and original archive
   status. Scope verification to behavior the new orchestration changes.
4. **M3 arithmetic:** independent hand calculations for signs and equal-person
   weighting; exact 288-window/24-hour boundaries; one contributing person
   with null interval; long failed prefix excluded; empty common support;
   full-cohort/partial-cohort labels and all-candidate roster retention.
5. **Identity and integrity:** observation/roster/bounds/origin/history/target/
   persistence/source mismatches rejected. A manufactured successful omission
   is invalid, rather than a new permitted abstention mode. Tampering must be
   checked semantically as well as through inventories.
6. **Repeat and reconstruction:** the two existing predictor structures repeat
   in fresh processes. Reconstruct child and parent reports after original
   input/predictor paths are unavailable, with report bytes matching. Preserve
   original M3 reconstruction and source inventories.
7. **Repository checks:** `uv sync --locked` and
   `uv run --locked python scripts/check.py`; focused/new numerical checks and
   planned CI jobs. Broaden testing only for new changes or unresolved failures.

Root records the actual clean commit, environments/locks, protocol/source
identities, commands, attempts, failures, report hashes and limitations.
Declare OT-029/030 complete only when their required behavior and checks pass;
report hosted CI separately from local verification. Update the roadmap,
canonical guides, navigation and changelog, then commit the evidence. Publish,
merge to main or create a PR only within the user's subsequent execution scope.

## Optional execution goal

When implementation is requested, use one goal with this objective:

> Complete OT-029 and OT-030 in the researcher-tools-plan worktree on its
> codex branch: freeze and review the interfaces/new synthetic M3 protocol,
> implement the bounded local entry and separate comparison coordinator with
> agents A/B/C, preserve historical sources and archives, pass the stated
> acceptance/repository checks, and record truthful execution evidence and
> completion status. Keep empirical studies and public release separate.

Execution was authorized on 2 October 2026 and the implementation goal was
started with the objective above. No token budget, schedule or automatic
publication is established. Independent M2 reproduction,
P1 intended-user acceptance and M3–M5 empirical/biological assessment remain
external evidence steps and do not block these internal software packages.
