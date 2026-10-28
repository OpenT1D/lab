# 0024 — Assess hepatic assumptions with a separate matched comparison

Status: accepted on 22 September 2026 for the requested next OT-026 internal assessment. Start from `c6cb206` in the existing isolated worktree. BC-008 and upstream physiology remain unchanged.

The [source assessment and protocol](../research/m4-hepatic-assessment.md) select the Dalla Man 2007 hepatic extraction and portal EGP relations for a conditional 2×2 comparison. Coefficients imported from the normal column are hypothesis anchors, not estimates for residual T1D or graft recipients. The original evidence does not establish that a smoothly declining extraction fraction is a general causal law.

Preserve BC-008 basal plasma glucose, insulin, SC delivery and all inventories. Use the paper's equilibrium constraints to reanchor extraction and EGP intercepts, explicitly separating this engineering adaptation from the published healthy model. Measure literal drop-in baseline mismatch separately. Otherwise a changed initial equilibrium could masquerade as a dynamic mechanism effect. Do not substitute a completely different population's full model to attribute two individual mechanisms.

A new local wrapper replaces only hepatic loss and EGP, including the loss ledger and same-stage glucose derivative seen by the source. Freeze cases, equations, limits and contrasts before execution in BC-009/1. Reject unsupported HE domains without clipping. Compare disabled behavior directly with unchanged BC-008; verify conservation, solver sensitivity and fresh-process repetition. Biological adequacy remains a separate question requiring appropriate flux/kinetic observations and domain review.
