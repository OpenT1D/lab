# 0001 — Project foundation

Status: accepted for the repository foundation. Date: 2026-09-12.

## Context

OpenT1D aims to become an open modular virtual laboratory connecting metabolic and biological T1D research. The initial repository contained a research report and roadmap. It needs a coherent public-facing structure before implementation begins.

The [repository research](../onderzoek/repositorybasis.md) compares established projects and standards. The [scientific research](../onderzoek/projectopzet.md) covers candidate models, data and evidence.

## Decision

Build shared infrastructure and useful reference modules. Reuse upstream work when suitable and allow whole-engine integration as well as justified component composition. Prove the first complete experiment and early interchange across model families before declaring general interfaces.

Use English for public guides and preserve the research reports. The original decision retained them in Dutch; they were translated into English on 29 October 2026 without updating the historical findings. The root README introduces the project; the roadmap is the canonical implementation plan. Organize deeper material by project design, research practice, contribution and maintenance.

License original project material under Apache-2.0 and retain separate terms for third-party assets. Require attributable, reproducible contributions without adding a CLA or signed-off-by workflow at this stage.

Use GitHub-readable Markdown as the canonical source. Build the same files into a local Sphinx site using MyST, Furo and an external table of contents. Keep development dependencies in a uv lockfile. CI verifies content structure, citation metadata and a strict documentation build.

Use lightweight founder governance with explicit responsibility and no invented committees. Add real confidential reporting channels before opening public contributions. Treat GitHub settings and public hosting as separate activation steps.

## Alternatives

GitHub-only documentation would have fewer tools but no built-in search or strict cross-reference build. A separate website source would duplicate the documents. The selected approach supports both reading modes from the same files and leaves room for scientific API documentation later.

MIT or BSD would also permit broad reuse. Apache-2.0 continues the original research recommendation and provides explicit contributor patent terms. Documentation-only Creative Commons licensing is deferred to avoid an unnecessary split for original material; it can be reconsidered for a specific publication or community need.

A full package skeleton, universal plugin API and deployment architecture are deferred until a working integration gives them concrete requirements.

## Consequences and review

The foundation has a real build and upkeep cost, controlled by a single locked toolchain and shared local/CI commands. Scientific claims require their own evidence; passing repository checks is not a scientific endorsement.

Revisit this record when the first adapter establishes packaging requirements, a new maintainer changes governance needs, or distribution requirements reveal a concrete licensing issue. Engine selection, biological coupling contracts and public API stability remain later decisions.
