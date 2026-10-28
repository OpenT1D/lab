# 0047 — Bind researcher secretion intake to the BC-007 synthetic task

**Status:** Accepted for bounded M4 implementation, 27 September 2026.

## Context

BC-007 freezes a Pedersen–Cobelli secretion reference, a declining synthetic
glucose challenge, and two distinct kinetic outputs. Its source and scientific
criteria are pinned. M4 still lacks a way to run a researcher's own secretion
model through those outputs. The platform direction in
[0045](0045-tool-first-research-platform.md) prioritizes researcher-owned
methods.

## Decision

Add a separate workflow accepting one trusted local Python file with a
full-grid `secretion(times_min, glucose_mmol_l)` function. Its declaration
records model identity, source hash, rights basis, dependencies and exact
`pmol/(kg min)` output unit. Require one finite, nonnegative sample per frozen
BC-007 time/glucose point and impose a stated engineering rate limit. Use the
same piecewise-linear forcing for insulin and C-peptide. Preserve BC-007's
source conversion and baseline convention by using its verified archive as
the reference and its paired boundary as the candidate's kinetic context.
Keep incremental and synthetic-basal cases separate.

Archive the complete reference, candidate source, declaration, model output,
runtime identity, kinetic trajectories and check results. Validate through
the existing two solvers and independent kinetic oracle. Reconstruct the
comparison from artifacts without executing the candidate model or solvers.
Leave BC-007 code, protocol and historical results unchanged.

## Alternatives

- Generalize BC-007 in place: this would alter its frozen historical task.
- Accept a secreted-rate CSV: that would allow traces but not exercise a
  researcher-owned dynamic model on the fixed glucose challenge.
- Define a universal model plugin: no user exercise yet warrants that scope.

## Consequences and revisit condition

This is one prescribed synthetic challenge, not glucose-feedback coupling,
package sandboxing, human model validation or a therapy claim. The researcher
remains responsible for source rights, complete dependency records and any
scientific interpretation. Revisit the interface after actual user attempts
identify concrete incompatibilities.
