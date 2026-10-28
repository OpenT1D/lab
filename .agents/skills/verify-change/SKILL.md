---
name: verify-change
description: Select and run evidence-based checks for a bounded OpenT1D change or review, then hand off the tested revision, results and gaps. Use for repository change verification, not release qualification or broad scientific validation.
---

# Verify a change

Start from the problem/reproduction, bounded diff, acceptance cases and
applicable [roadmap item](../../../ROADMAP.md). Read
[AGENTS.md](../../../AGENTS.md), [CONTRIBUTING.md](../../../CONTRIBUTING.md) and
the [development guide](../../../docs/development.md); its component/test map
and the affected task guide select the checks. Inspect the actual diff and
callers, not only the implementation handoff.

Record the source revision and working-tree state before checking. During
development, run targeted checks that can distinguish the required behavior
from a plausible regression. A defect reproduction should fail for the relevant
reason on the old behavior and pass after correction; an import failure or
timeout does not establish detection. Use disposable fixtures/source copies for
counterexamples and preserve the unmodified control. Do not turn an unrelated
known defect into extra scope without a selected fix.

Match the evidence to the changed boundary:

- Documentation and guidance: check local links, supported commands, navigation
  for new public guides and claims against the canonical source. Preserve the
  Dutch research reports.
- Contracts, storage and reports: check supported success, rejection and
  incomplete/failure behavior, input/source identity, byte consumption and
  reconstruction/reader compatibility where affected.
- Processes and runtime setup: exercise the affected ownership, cancellation,
  deadline and child-process behavior; preserve partial evidence and unrelated
  processes. Check source inventories when frozen setup or execution depends on
  implementation identity.
- Numerical behavior: follow the task's protocol and justified numerical checks,
  preserving ancestry, units, time conventions and historical tolerances. The
  [validation guide](../../../docs/research/validation.md) separates software
  checks from scientific claims.

Use `uv sync --locked` for root setup. The root Python environment contains
tooling, contracts and orchestration; it does not install native physiology.
Use the affected task's locked environment only when its native checks apply.
The [public snapshot policy](../../../docs/publication-security.md) keeps
historical native environments outside automatic public installation and CI;
do not remove or bypass that gate to complete verification. Report unavailable
or excluded checks and the resulting evidence gap. A root-suite pass or skipped
native job supplies no native numerical result.

Assign the final full repository check to one owner:

```sh
uv sync --locked
uv run --locked python scripts/check.py
```

Use the final integrated revision. A later relevant edit needs the affected
checks again and a new full-check receipt for the final revision; do not report
an earlier tree as checked. In concurrent work, use isolated worktrees for
writers and a separate technical reviewer for the diff and counterexamples.
Keep one owner for shared interfaces; do not duplicate the full suite across
agents. Agent review does not satisfy independent human reproduction.

The handoff states the exact revision and dirty state, changed behavior and
acceptance cases, commands, environments, exit outcomes, meaningful observations,
skips with reasons and remaining risks. Identify local versus hosted evidence
and link retained artifacts when available. Report failures and inconclusive
results. Do not silently refreeze baselines, invent results or claim model
validity, user acceptance, platform support or release readiness from checks
that did not establish them.
