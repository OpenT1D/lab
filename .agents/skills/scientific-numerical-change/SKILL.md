---
name: scientific-numerical-change
description: Implement or review OpenT1D model, adapter, solver, metric or scientific-analysis changes that can alter numerical meaning or outputs. Use the affected task's protocol and reference checks; prose-only edits do not need this workflow.
---

# Scientific and numerical changes

Read [AGENTS.md](../../../AGENTS.md), [CONTRIBUTING.md](../../../CONTRIBUTING.md)
and the applicable [roadmap item](../../../ROADMAP.md). Use the component and
test map in the [development guide](../../../docs/development.md) to find the
affected task's canonical guide, protocol and evidence record. The
[validation guide](../../../docs/research/validation.md) defines the claims that
each kind of evidence supports.

Before editing, identify the question, current behavior, bounded change and
acceptance cases. Record the contracts that the change must preserve: model and
parameter ancestry, source and lock identities, compartments and units,
amount/rate/point/interval meaning, initialization, event order, clocks, causal
availability and biological process ownership. Preserve development/evaluation
separation and the planned denominator, including failures and partial runs.
Use a short [decision record](../../../docs/decisions/README.md) when changing a
shared interface or scientific convention; routine fixes do not require one.

Choose checks for the changed behavior before inspecting new evaluation output:

- For an adapter, compare direct upstream and adapted execution under controlled
  inputs; preserve native reset, solver and lifecycle behavior.
- For equations, coupling or numerical settings, select an appropriate reference,
  balance/invariant or refinement check and justify its tolerance. Check the
  coupled boundary as well as the changed component.
- For metrics or analysis, use independently calculable fixtures with the actual
  signal, time and missing/partial-data semantics. Verify reconstruction and
  affected reader compatibility when stored results are involved.

Follow the task guide rather than copying commands between environments.
The [M1](../../../docs/m1-tutorial.md), [M2](../../../docs/m2-tutorial.md) and
[internal verification](../../../docs/internal-verification.md) guides own their
native checks. The root environment is tooling and orchestration; native
physiology uses separately locked environments. Read the
[public snapshot policy](../../../docs/publication-security.md) before setup:
historical native commands do not authorize public installation or bypassing
the snapshot gate. If the required environment is unavailable or excluded,
continue applicable fixture and reconstruction work and report the native check
as unrun, with its reason.

Investigate unexpected output changes. Do not relax tolerances, regenerate a
historical baseline or refreeze expected output merely to obtain a passing run.
An intentional scientific change needs an explicit rationale, new identity and
an account of affected prior results; retain the original evidence. Use new
output directories and keep complete and failed evidence outside Git. Keep
private health records, restricted inputs and credentials out of commits and
logs.

Hand off the exact revision and dirty state, changed scientific contracts,
commands/environments actually used, reference and tolerance rationale, observed
output differences, failures, unrun checks and remaining limits. Distinguish
software/numerical verification, a reproduced reference, independent human use
and empirical or biological validity. Another agent's review supplies technical
review, not independent scientific validation.
