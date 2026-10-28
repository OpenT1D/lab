# 0025 — Observe pancreatic feedback secretion with C-peptide

Status: accepted on 22 September 2026 for the requested next OT-026 step, starting from `9393fb1` in the existing isolated worktree.

The [BC-010 protocol](../research/m4-feedback-observation-protocol.md) composes verified feedback output and the unchanged forward C-peptide reference. It uses pancreatic appearance Spo in its existing molar per-kg units. Equimolar processing and central appearance are declared working approximations; this is neither an anatomical transit model nor a demonstrated graft boundary. Insulin portal transit, hepatic extraction and pharmaceutical delivery stay out of C-peptide kinetics.

Use a passive observation branch driven by a completed, verified BC-009 archive. The runner can create that archive or consume an explicitly supplied checked archive. Copy its full hashed evidence into the new attempt. Independent locks preserve the native and C-peptide runtimes. This gives exact preservation of upstream glucose/insulin and avoids numerical feedback from an observation state. A monolithic reimplementation is unnecessary for this one-way dependency.

Specify the interpolant and initial inventories before execution. Distinguish kinetic solver error, source solver error and coarsening error, and compare delivered amount with the parent pancreatic ledger. Show the erroneous post-portal inlet as a fault comparator. A branch-level appearance/volume ambiguity remains a conditional mathematical example, not a claim about identifiability of the entire coupled model. Revisit the boundary with population-specific kinetics, processing, assay information and domain review before human interpretation.
