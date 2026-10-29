# Contributing to OpenT1D

OpenT1D welcomes software, scientific and documentation contributions. You do not need to build a model to help: reproducing a result, identifying a questionable assumption or making a guide easier to follow can be equally valuable.

The project implements M0 native references, bounded M1/M2 experiments and researcher-owned P1/M3/M4/M5 method workflows. Their current bounded software is internally verified, including the [combined M3–M5 execution](docs/research/researcher-workflow-integration.md). Independent human M2 reproduction, intended-user acceptance and broader empirical/biological claims remain open. The [roadmap](ROADMAP.md) separates completed implementation from those evidence requirements.

The [internal verification protocol](docs/research/internal-verification-protocol.md) separates internal numerical checks from later independent review; external reproduction is not a prerequisite for development.

OpenT1D prioritizes research tools that let users connect existing models,
controllers and appropriately authorized data. The [tool-first decision](docs/decisions/0045-tool-first-research-platform.md)
and [roadmap](ROADMAP.md) define current priorities. An original controller or
physiological model is an optional, separately justified study. Public examples
use invented data; contributors must not submit private health records.

The [P1/0.1 researcher workflow](docs/p1-research-workflow.md) locally runs and
reconstructs a fixed synthetic M1 task. [P1/0.2](docs/p1-external-controller.md)
now accepts one local rate controller under a bounded contract. A source-pinned
upstream PID [worked example](docs/p1-upstream-pid-tutorial.md) verifies that
intake. The [P1/0.4 internal follow-up](docs/research/p1-internal-followup.md)
checks a second profile/seed pair and a distinct proportional source. A human
reviewer conditionally cleared one exact internal technical checkout;
independent intended-user execution remains open. No stable
general model API is claimed. The historical
[C1 research record](docs/research/c1-controller-protocol.md) includes negative
original-method findings and a technically verified G2P2C integration; the
[latter's readiness decision](docs/decisions/0044-c1-g2p2c-native-readiness.md)
does not qualify it as a fair efficacy comparator. Cure-oriented M4/M5 work
currently verifies attributed equations, synthetic couplings and data
requirements; it does not establish a treatment result. The completed internal
[work packages](docs/research/roadmap-history-2026-10-28.md#post-integration-internal-work-packages) add a common
local task entry and separately specified M3 predictor and M4 secretion-source
comparisons. The entry now registers ten routes, including `m4-compare`,
the separately versioned `m4-study` and its explicit
[maintained successor](docs/m4-maintained-study.md), `m4-study-secure`. The
[functional development packages](docs/research/roadmap-history-2026-10-28.md#functional-development-after-ot-031)
add configurable initial loads, immutable local campaigns, an archive catalogue
and explicit task-directed setup. The [OT-032–037 record](docs/research/ot032-ot037-verification.md)
binds their local execution, failure and reconstruction scope.
The [OT-029/030 record](docs/research/ot029-ot030-verification.md) and
[OT-031 record](docs/research/ot031-verification.md) bind their separate local
verification scopes. OT-031 native execution and simulator-free reconstruction
are internally verified; independent usability and biological evidence remain open.
The [observation-analysis CLI and GUI](docs/observation-analysis.md) add a
synthetic-only fixed-kinetic paired sensitivity task with an explicit shared
core reused by the implemented [OT-055 sampling task](docs/mmtt-sampling.md).
The [OT-057 record](docs/research/ot057-uiux-verification.md) binds the later
integrated interface fixes and internal browser checks. Preserve frozen units,
failure accounting and source identities; no human applicability follows from
synthetic checks. The comparative researcher pilot remains open.
Consult the roadmap
and linked evidence before extending any of these workflows.

## Find a useful contribution

| Contribution | A useful starting point |
| --- | --- |
| Documentation | Correct a confusing explanation, broken link or unsupported claim. |
| Research | Review a primary source and explain what it does and does not support. |
| Reproduction | Run a candidate simulator's documented example and record the exact environment and results. |
| Controller integration | Propose a bounded external-method task with source identity, causal inputs, action units, timing, rights and failure behavior. |
| Cure-oriented research | Review the [OT-024 dossier](docs/research/m4-evidence-dossier.md) and [M4 evidence gaps](ROADMAP.md); contribute independent numerical assessment, suitable measurements or domain review before proposing a therapy model. |
| Models and data | Assess a candidate with the [model guide](docs/research/models.md) or [data guide](docs/research/data.md). |
| Software | Work on the next unblocked [roadmap work package](ROADMAP.md#now-next-and-later). |

Small corrections can go straight to a pull request. For a new module, dependency, interface or substantial feature, first describe the research task and proposed approach in an issue or draft pull request. Include what can be reused and what needs to change. A short design discussion is sufficient unless the decision affects the shared architecture.

## Work locally

1. Fork the repository, or create a branch if you have write access.
2. Clone your fork and install the tooling using [the development guide](docs/development.md).
3. Make a focused change with an explanation that another contributor can assess.
4. Run `uv run --locked python scripts/check.py` from the repository root.
5. Open a pull request describing the problem, change, verification and remaining limitations.

The [public source installation and CI policy](docs/publication-security.md)
limits automatic public setup and native execution. The two synthetic MMTT tasks
are the initial public exercise. Historical native tutorials preserve research
commands; the root CI result does not execute those native campaigns. A native
change needs its separately reviewed environment and relevant numerical checks.

Use clear commit messages. There is no mandatory commit-message syntax, CLA or signed-off-by requirement. Keep unrelated cleanup separate when it makes review harder.

## Evidence expected with a change

Describe the research task a contribution helps with, what it reuses and what
others can reproduce or extend. Credit existing projects and consider an
upstream contribution when it serves the task. When comparing tools, state the
question, supported versions, equivalent inputs and outcomes, preparation and
maintenance effort, and limitations. Report favorable, similar, unfavorable and
inconclusive results with the same care. Scope any improvement claim to the
comparison actually performed.

For documentation, verify local links and check scientific claims against the cited primary source. Distinguish proposed behavior from implemented behavior. Public project documentation, including research reports, is written in English. Preserve historical findings and source references when translating existing reports.

For software, provide checks that address the behavior that matters. A defect fix should normally include a small reproduction. A numerical change should include a suitable reference, justified tolerance and explanation of any changed outputs. Formatting-only changes do not need invented tests.

For a model or adapter, include its origin, license, intended use, inputs and outputs, known limitations and a reproduction of a suitable reference. Start with the [model-card template](docs/templates/model-card.md). Review both the module and its coupling to other modules.

For an experiment, describe the question and analysis before inspecting the final evaluation results. Use the [protocol template](docs/templates/experiment-protocol.md) and follow the [validation guide](docs/research/validation.md). Preserve failures and exclusions in the report.

## Rights, data and attribution

Submit original contributions under the repository's [Apache-2.0 license](LICENSE), unless an explicitly documented third-party license applies. You must have permission to contribute the material, including permission from an employer or other rights holder where needed. You retain copyright in your work.

Preserve required upstream license and attribution notices. A paper describing a model does not by itself grant redistribution rights to its code or data. Record the exact upstream version and applicable terms before copying or distributing an asset; see [licensing](docs/licensing.md).

Use synthetic or explicitly redistributable examples. Do not put personal health records, access tokens or restricted datasets in issues, pull requests, logs or repository files. The [data guide](docs/research/data.md) describes how to contribute a reproducible data workflow without redistributing its inputs.

## AI-assisted contributions

AI assistance is welcome for implementation, analysis and writing. Review the generated work, verify references and run the relevant checks. Be able to explain the result and its limitations. Mention substantial AI assistance when it helps a reviewer understand how the work was produced or verified; no disclosure is needed for routine spelling or completion assistance.

Generated code is not evidence of model validity. Generated citations must be checked against the source. Do not upload restricted data to an external tool without the rights and authorization needed for that use. AI tools are not listed as authors or maintainers.

## Review and decisions

Maintainers review scope, correctness, clarity, evidence and ongoing maintenance cost. Scientific expertise is sought where a claim requires it; software review and scientific review are recorded separately. A module can be accepted as exploratory with explicit limits while further evidence is collected.

Changes to shared interfaces, scientific conventions or licensing need a short [decision record](docs/decisions/README.md). Routine fixes do not. Follow [governance](GOVERNANCE.md) for unresolved disagreements and [the code of conduct](CODE_OF_CONDUCT.md) in project discussions.

Update the [changelog](CHANGELOG.md) for user-visible behavior, scientific corrections or significant additions. Typographical fixes and internal maintenance normally do not need entries. Use [support](SUPPORT.md) for questions and [security reporting](SECURITY.md) for vulnerabilities.
