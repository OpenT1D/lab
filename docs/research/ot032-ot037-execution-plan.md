# OT-032–037 isolated execution plan

**Status:** authorized internal implementation plan, 3 October 2026, prepared
from main `d9991c115e795c2977177349805619df15981598`. Protocols precede new
numerical execution. The [roadmap](../../ROADMAP.md#functional-development-after-ot-031)
owns scope; [decision 0058](../decisions/0058-configurable-study-and-local-research-tools.md)
owns the architectural/scientific boundaries. Completion requires a separate
dated verification record, rather than this plan.

**Execution outcome:** implemented in the grouped branches; the
[verification record](ot032-ot037-verification.md) owns the actual internal check
scope, preserved development failures and remaining external/platform limits.

## Worktrees and ownership

All worktrees are attached managed checkouts under the local Codex worktrees
directory. Main stays at the published baseline during this goal. Root creates
branches, freezes the planning commit, integrates reviewed changes and records
checks. Agents do not modify the primary checkout or commit each other's files.

| Worktree / branch | Work grouped together | Owner and exclusive files |
| --- | --- | --- |
| `functional-lab-plan/OpenT1D` / `codex/functional-lab-plan` | Plan, protocol freeze, then combined integration and acceptance | Root: roadmap, decisions, navigation, common workflow entry, integration tests/CI, final evidence/status |
| `m4-configurable-study/OpenT1D` / `codex/m4-configurable-study` | OT-032 scientific contract, numerical execution, reports and reconstruction | Protocol/numerics agent: new `experiments/m4/initial_load/`, its tests and `docs/m4-configurable-study.md` |
| `local-campaigns/OpenT1D` / `codex/local-campaigns` | OT-033 frozen planning, retained attempts, resume and campaign reports | Campaign agent: new `experiments/campaigns/`, its tests and `docs/local-campaigns.md` |
| `researcher-tools/OpenT1D` / `codex/researcher-tools` | OT-034 archive catalogue and OT-037 declared runtime setup | Tools/verification agent: new `experiments/catalogue/`, `experiments/setup/`, their tests and canonical guides |

The study is scientifically independent of administration. Campaign execution
depends on its frozen intake/runner/reader contract. Catalogue and setup share
local task/runtime metadata and can be built together without changing model
equations. A fourth branch supplies a reviewable integration without using
main as the development checkout. At most four agents run concurrently.
Reviews go to the file owner; no concurrent writes to shared files.

## Freeze before implementation

Commit this plan, roadmap selections, decision and the initial **M4-STUDY/1**
prose/machine protocol before numerical implementation or observations. A retained
development probe failed its new coarse source-rate gate at 15 grams. The explicit
**M4-STUDY/2** revision halves only the coarse maximum step, preserves the failed
version and its receipt, and precedes definitive study execution. Both versions
keep the same equations, source parameters and acceptance thresholds; the
[protocol history](m4-configurable-study-protocol.md) records their identities.
The study supports
exactly the fixed 0, 15 and 30 gram initial-load choices, ordered subsets and
an ordered two-to-eight source roster. Historical 0/30 gram cases are parity
targets; the new midpoint was chosen before new results. No event timing or
profile variation is exposed. Existing numerical packages and locks remain
unchanged and importable by separate wrappers.

Planned study entry: `python -m experiments.m4.initial_load run --config PATH
--output FRESH`; `reconstruct --archive PATH --output FRESH [--allow-failed]`.
Register the task as `m4-study` after its native execution and reader exist.
Passive intake exposes normalized configuration/source/protocol/lock identities
to the campaign layer without importing supplied code. Exact configuration
schemas are versioned in each new package and reject unknown fields.

The initial campaign schema is `opent1d.local-campaign-config/1`: task
`m4-study`, ordered cells with unique ids and explicit configuration files,
one-to-eight repetitions and a finite per-study outer deadline. Bound the plan
to at most 32 cells and 128 total slots. Freeze standalone source/configuration
bytes and identities before dispatch. Cell-major/repeat order is fixed.
Each explicit run/resume session attempts remaining slots once, retains prior
attempts, and links the prior session's sealed identity. Reuse requires both
frozen identity consistency and successful authoritative reconstruction.
No report averages incompatible scientific conditions or hides failed slots.

Catalogue input is `opent1d.catalogue-request/1` with ordered archive entries,
registered tasks and local tags. Indexing reads metadata and full byte
inventories; verification invokes explicit standard-library readers into
fresh external directories and checks source archives before/after. Index,
verify and filtering are separate operations. Comparison eligibility requires
verified complete evidence and task-specific matching scientific conditions,
not merely equal directory shapes or successful JSON parsing.

Setup provides passive task-specific plan/check and explicit install commands.
Plans bind declared project/lock identities and use only existing locked root,
native and observer environments needed by the task. Installation uses
`uv sync --locked` and checks identities afterwards. No arbitrary archived
script, unlocked dependency, global package or automatic installation from
`run` is authorized by this interface.

## Parallel implementation and integration

1. Create the three child worktrees/branches from the frozen planning commit.
   Owners implement in disjoint namespaces and communicate precise interfaces.
2. Study owner implements scenario-specific references, controls, source runs,
   solver refinement, passive observation, complete archives and stdlib reader.
   Campaign owner builds frozen plans/lifecycle/failure accounting in parallel;
   tools owner builds catalogue/setup against the explicit registry.
3. Root reviews each increment and commits it on its branch. Integrate numerical
   contract first, then campaigns and tools; resolve shared-entry/navigation
   adaptations in the integration worktree only. Cross-review process cleanup,
   provenance, archive tampering, full denominators and comparison semantics.
4. Stop source edits and commit a clean candidate before definitive numerical
   acceptance. Runs keep the same protocol/source/lock identities; subsequent
   substantive changes require new runs with fresh output identities.

## Acceptance and retained evidence

Study: both existing sources on all three loads, scenario-specific reference
and control agreement, complete trajectories, inherited conservation/positivity
and solver gates, historical 0/30 gram parity, fresh-process repeats, deterministic
JSON/Markdown/figure reconstruction without numerical environments or callbacks,
invalid configuration, retained failed source and deadline/interruption cleanup.

Campaign: real native study dispatch and repeated slots, all planned denominator
and failure states, interruption followed by explicit resume, verified reuse,
retained retries, changed frozen input/archive rejection, failure reconstruction
and bounded process cleanup. Unit fixtures cannot replace native execution.

Catalogue: index actual retained archives, filter metadata, verify/reconstruct
with registered readers, distinguish failed/unverified entries, reject tampered
archives, accept exact-condition compatibility and reject differing loads,
rosters or protocols. Setup: missing runtime/check behavior, lock-bound plan,
explicit locked installation and task execution/reconstruction in the fresh
managed checkout; report tested platform/version and untested clean-system
limits accurately.

Run `uv sync --locked` and `uv run --locked python scripts/check.py`, plus
appropriate new native numerical tests. Review the final diff and confirm old
scientific sources/locks remain unchanged. Record commands, actual exits,
commits, inventory/report hashes, denominators, numerical outcomes and remaining
limitations. Local checks do not imply hosted CI, independent usability,
human/biological validity, treatment benefit or a public release.

OT-035 GUI and OT-036 new-model intake stay proposed/conditional. Existing
OT-026 observation fitting and OT-027 selected therapy mechanisms retain their
own suitable-data, rights and scientific review gates. No external message,
human-data evaluation, main merge, push or release is part of this goal.
