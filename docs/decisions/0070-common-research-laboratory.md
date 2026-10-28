# 0070 — Deliver a common research laboratory across bounded tasks

Date: 25 October 2026

Status: accepted for product direction and future work allocation. The common
core, general API and delivery increments remain to be implemented and verified.

## Context

[Decision 0045](0045-tool-first-research-platform.md) makes research tools for
researcher-owned models and authorized data the primary deliverable. Existing
routes provide useful native integrations, isolated runtimes, task contracts,
execution, retained failures and reconstructible reports. The shared synthetic
MMTT core demonstrates reuse for two related tasks. These assets do not yet
form a stable general laboratory interface.

The product direction is a connected, modular T1D laboratory. A single polished
analysis route is insufficient evidence of platform reuse; adding separate
runners and screens for every question would preserve the same integration
burden. The [product-direction research](../onderzoek/productrichting.md)
assesses the evidence, alternatives and remaining uncertainty.

## Decision

Develop one common project, experiment-plan, capability, execution and
result/evidence layer across scientifically task-specific contracts. Serve
GUI, CLI and programmatic use from the same scientific plans and results.
Extract suitable existing infrastructure and migrate bounded routes through
it, preserving their native behavior, historical protocols and compatible
readers. Do not start a second parallel implementation of every workflow.

Support both whole-engine integration and smaller component replacement where
a defensible scientific boundary exists. Preserve native equations, solvers,
runtimes and process ownership. Units, compartments, routes, time conventions,
causal information and supported populations remain explicit; one common
lifecycle does not make incompatible physiology interchangeable.

Test reuse with a second method, engine or research question and then a third
task or domain. Assess the added adapter work, core/GUI changes, maintenance,
correct complete reports and independent use. A simulation/controller task
and an observation-analysis task can exercise different scientific contracts
through the same laboratory. These are product acceptance jobs, not evidence
that a universal API or cross-engine comparison is already implemented.

Retain the [OT-058 Windows product outcome](../../ROADMAP.md#planned-windows-installer-ot-058):
one graphical installer and a launch shortcut, without separately administered
Git, WSL/Ubuntu, Python, environments or terminal setup by the user. The choice
between native runtimes and any application-managed compatibility mechanism
requires a subsequent architecture assessment; wrapping today's WSL
instructions in a launcher does not satisfy that outcome.

Keep internal software verification, native reproduction, independent usability,
source-specific empirical evidence and clinical benefit separate. Internal
platform work may proceed within its declared scope while external evidence
remains open. An original controller, physiological mechanism, dataset-hosting
service or treatment model is not a prerequisite for platform success.

## Alternatives and consequences

A single-task product would not test the intended cross-task laboratory.
A universal equation language or fixed public API chosen before concrete
adapters would conceal scientific differences or force unnecessary upstream
rewrites. A rewrite from scratch would discard verified routes and create
avoidable migration risk. None is selected.

The [product requirements](../product-laboratory.md) define the intended
capabilities; the [roadmap](../../ROADMAP.md#common-laboratory-delivery-plan)
owns sequencing, dependencies and acceptance. This decision extends 0045
without replacing historical contracts or changing existing numerical results.
Detailed schemas, API signatures, runtime packaging and migrations need their
own bounded implementation decisions and checks.

Evaluate standards, external workflow executors, HPC/cloud and further biological
modules when a concrete research job establishes their need, source rights,
scientific assessment and maintenance ownership. No standard compliance,
platform support, independent review or empirical applicability is granted by
this decision. Revisit the direction if repeated tasks cannot reuse the shared
infrastructure or independent researchers find no benefit over competent
existing tools and scripts.
