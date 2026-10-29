<a id="onderzoek-naar-de-repositorybasis-van-opent1d"></a>

# Research into the OpenT1D repository foundation

Translated from Dutch on 29 October 2026. Historical findings, language-policy
statements and audit results below describe the original report, not a new review.

<a id="1-advies"></a>

## 1. Recommendation

From the start, OpenT1D needs a coherent public project foundation: an understandable entry point, a usable contribution procedure, clear responsibilities and an auditable trail of scientific assumptions. The appropriate result is a repository where a new researcher can quickly assess what the project intends to build, what already works and how their own contribution can be assessed.

The recommended setup combines a concise README with detailed documentation, a current roadmap, scientific contribution formats and automated documentation checks. The intended outcome remains a modular virtual laboratory with both infrastructure and building blocks. The first concrete research task makes that ambition actionable; the repository must not reduce the project to just a benchmark or wrapper.

Completeness here means covering important responsibilities and making the described workflow executable. An empty directory for every future subsystem, a badge without evidence or a committee without members does not improve the foundation. Even a perfectly organised repository does not prove that a physiological model is correct.

<a id="2-onderzoekskader"></a>

## 2. Research scope

The reference date is 12 September 2026. The comparison uses official repositories and documentation from established open-source projects, supplemented by primary documentation from GitHub and the standards used. The selection includes broad scientific libraries and projects resembling a modular simulation platform. It is neither a ranking by stars nor a full audit of the software examined.

The research assesses six aspects: first introduction, joining as a contributor, scientific auditability, maintenance, responsibilities and suitability for a project that does not yet have a runtime. Observed practices and recommendations for OpenT1D are separated below. Documents on a moving main branch may change after the reference date.

The technical and biological quality of T1D model candidates is covered in the separate [project research](projectopzet.md). This report concerns the setup needed to assess and maintain such quality later. Popular projects provide useful examples; their size or reputation is no reason to adopt their entire process.

<a id="3-vergelijking-met-bestaande-projecten"></a>

## 3. Comparison with existing projects

| Project | Observed practice | Application to OpenT1D |
| --- | --- | --- |
| PyBaMM | Combines a simulation framework, models and parameters with experiments; the README provides an executable starting point and links to examples, documentation and model-specific citations. | Present infrastructure and modules together. Add a real first simulation tutorial when it exists; retain citations for the modules actually used. |
| SciPy | Distinguishes contribution types and documents decision-making and governance roles. | Value research, documentation and reproduction alongside code. Record current responsibility without simulating a mature governance structure. |
| scikit-learn | Requires reproducible problem reports, rights to contributions and supported proposals; has explicit rules for automated contributions. | Make each contribution understandable and auditable. Allow AI use with responsibility for quality, sources and verification. |
| Mesa | Connects contributions to documentation, tests and formatting; larger extensions require substantive discussion. | Allow small improvements directly and discuss shared interfaces or new modules early. Use the same checks locally and in CI. |
| PhysiCell | Organises the introduction around concrete example projects, build commands and scientific references. | Later make a reproducible experiment the primary entry point. Clearly separate documentation tooling now from future simulation commands. |
| BioSimulators test suite | Connects explicit simulator conventions to example archives and execution checks. | A compatibility claim needs executable evidence cases. Distinguish standards conformance from biological validity. |

The project observations come from their own READMEs, contribution guides and project documentation.[^1][^2][^3][^4][^5][^6][^7]

<a id="31-wat-vooral-bruikbaar-is"></a>

### 3.1 Particularly useful practices

PyBaMM is a strong substantive analogy: a domain-specific platform can provide both shared infrastructure and a collection of models. The model and its application are visibly central. The practical lesson for OpenT1D is to organise the README around the research experience the platform intends to offer, with an honest status statement while that experience is still being built.[^1]

SciPy shows that contributions extend beyond new algorithms. A clear division of responsibilities makes collaboration predictable. For OpenT1D, a named initial maintainer with a public decision process is sufficient; a large steering group only fits when the corresponding people and responsibilities exist.[^2][^3]

The scientific examples also reveal a boundary. BioSimulators checks address specified execution conventions and example experiments. This supports the need for compatibility checks, but does not itself support a claim that a model reliably predicts a particular patient or treatment.[^7]

<a id="32-wat-niet-letterlijk-wordt-overgenomen"></a>

### 3.2 Practices not adopted literally

The contribution procedure of a large established project may assume extensive specialist knowledge and review capacity. OpenT1D starts with a short process and specifies the evidence needed for each contribution. The stricter AI restrictions of scikit-learn are not copied; OpenT1D's chosen policy welcomes AI assistance while keeping the submitter responsible for the content.[^4]

An existing branching strategy, website infrastructure or release calendar is not adopted automatically either. Those choices serve the maturity of the example project. OpenT1D first needs one main branch, an auditable change route and a working documentation process.

<a id="4-informatiearchitectuur"></a>

## 4. Information architecture

The README has one task: help a new visitor understand what OpenT1D is and where to take the next step. It contains the ambition, current status, first research task, main navigation, contribution entry point, licence and citation. Detailed architecture, model conditions and maintenance instructions belong in linked documents.

The documentation gets separate entry points for project design, research, contributions and maintenance. Within that structure, the Diátaxis distinction between tutorials, task-oriented guides, reference and explanation is useful. These four document types answer different reader questions; they do not immediately require four mostly empty directory trees.[^8]

Explanations and contribution guides can already be written for OpenT1D. A simulation tutorial and API reference follow with the first working implementation. The existing model and protocol templates are documentation formats and are explicitly not presented as technical interfaces.

The public guides will be in English. The existing Dutch research reports will be retained and made accessible from the documentation. There will be one current roadmap. Research reports provide supporting arguments and refer to that roadmap for the current work order, so changes do not need to be maintained manually in three places.

| Content | Canonical location | Maintenance trigger |
| --- | --- | --- |
| Purpose, current status and entry point | `README.md` | Any change in available capabilities |
| Long-term direction and design principles | `docs/vision.md` | Change in project direction |
| Milestones and work packages | `ROADMAP.md` | Achieved outcome or changed dependency |
| Architectural boundaries | `docs/architecture.md` | First integrations and interface decisions |
| Model, data and evidence conventions | `docs/research/` | New application or relevant methodological lesson |
| Participation and responsibility | Root community documents | Changed workflow, contact or role |
| Operational setup | `docs/maintenance.md` | Activation of GitHub features and releases |
| Research sources | `docs/onderzoek/` | New or changed decisive information |

<a id="5-benodigde-repositorybestanden"></a>

## 5. Required repository files

GitHub supports recognisable community files such as CONTRIBUTING, CODE_OF_CONDUCT, SECURITY and SUPPORT. These can direct visitors to the right information. Their placement and presence are useful, but a file does not activate a working process or contact channel.[^9]

<a id="51-vanaf-de-foundation"></a>

### 5.1 From the foundation

| File or component | Why it is needed | Concrete content |
| --- | --- | --- |
| README | Understandable first introduction | Ambition, status, first task and links |
| CONTRIBUTING | Predictable contribution procedure | Local setup, review, evidence and rights |
| LICENSE and NOTICE | Rights and attribution | Apache-2.0 for original material; preservation of upstream terms |
| CITATION.cff | Discoverable research citation | Verified existing author information, no invented release or DOI |
| GOVERNANCE | Responsibility and decision-making | One named maintainer and short decision records |
| CODE_OF_CONDUCT | Behavioural expectations and response | Practical original text with explicit contact status |
| SECURITY and SUPPORT | Correct route for questions and problems | Distinguish vulnerabilities, scientific errors and project questions |
| CHANGELOG | Visible meaningful changes | Only Unreleased while there is no release |
| Issue and PR templates | Useful problem and contribution information | Question, origin, reproduction and limitations |
| CODEOWNERS | Designated review responsibility | The existing maintainer account |
| Editor and Git configuration | Consistent text files | UTF-8, LF, limited ignore rules |
| Tooling and CI | Repeatable quality checks | Lockfile, one local/CI command and strict documentation build |

A Code of Conduct without a usable reporting route is operationally incomplete. The address must therefore not be invented. Setting up and checking a confidential contact remains an explicit prerequisite for public community onboarding. The same applies to private vulnerability reporting availability: GitHub treats that as a separate setting.[^10]

The first issue forms collect a problem and its evidence, a proposal with acceptance criteria or a project question. The GitHub format supports required fields, but the setup asks only for information useful to that type of report. Blank issues remain available for exceptions.[^11]

<a id="52-pas-toevoegen-bij-een-concrete-aanleiding"></a>

### 5.2 Add only when there is a concrete reason

A FUNDING file comes when a real funding route exists. A DOI, publication badge and release version follow actual publication. Automatic package publishing, release attestations and a distribution inventory belong with a real package. An API reference belongs with an existing API.

An extensive author database, multiple translation systems, a plugin registry, general example data and a formal advisory board are not requirements now. They get a place only when the corresponding content, people or user need exists. This keeps the current foundation complete for its task and maintainable.

<a id="6-wetenschappelijke-afspraken"></a>

## 6. Scientific conventions

A generic open-source template is insufficient for OpenT1D. A contribution may be correct as software yet biologically coupled incorrectly. The foundation therefore needs explicit conventions for model ancestry, process ownership, units, time, observable information and limits of use.

The model-card format asks for the original publication, code version, parameters, licences, population, mechanisms and limitations. It also asks who models a process such as absorption or secretion. This prevents a technically compatible coupling from silently including the same physiology twice.

The protocol format records the question, scenario, intervention, tuning, outcome measures and analysis method. It includes space for failures, exclusions, independent evaluation material and deviations from the original plan. A result must later be reconstructible from saved output without manual corrections to a figure or table.

Status is not compressed into one quality badge. A module can be implemented and reproduce an upstream example while still lacking relevant external validation. These properties must remain visible separately. The sources and arguments are discussed in more detail in the [scientific project research](projectopzet.md#8-validation-as-core-functionality).

The first publication need not present a new optimal control algorithm. A meaningful comparison or a correctly documented dependence on model choice can already contribute to research. The broader laboratory then grows by applying the same evidence and reproducibility infrastructure to new biological questions.

<a id="7-licentie-citatie-en-data"></a>

## 7. Licensing, citation and data

Apache-2.0 is used for new OpenT1D material, consistent with the earlier project design. The official licence contains explicit provisions for contributions, patent licences, distribution and notices. The licence is included unchanged; project-specific explanation belongs in the separate licensing guide.[^12]

This choice makes no claim to other researchers' rights. An implementation, parameter collection, dataset and figure may have different terms. Coupling a GPL component must be assessed for the combination actually used and distributed; a separate process is not an automatic solution.[^13]

CITATION.cff is suitable for machine-readable citation data and is recognised by GitHub. It contains only existing metadata. Until there is a release or archive record, a user must identify the commit used. The CFF validator checks structure, not the historical accuracy of authorship or a scientific claim.[^14][^15]

FAIR software recommendations emphasise a public version-controlled repository, licence, citation and quality checks, among other things. These are useful design goals for OpenT1D. A private repository with prepared documents does not thereby have full public FAIR status; publication and actual accessibility remain separate steps.[^16]

Data must remain subject to their terms of use. Public examples can be synthetic or explicitly redistributable. Access to controlled data can be supported through reproducible instructions and converters. A `.gitignore` is only an aid against accidental addition, not access control or a way to retract information already published.

<a id="8-tooling-en-automatische-controle"></a>

## 8. Tooling and automated checks

The chosen documentation setup uses Sphinx, MyST, Furo and an external table of contents. MyST processes Markdown and can flag unresolved document references. The external table of contents enables one navigation structure without rewriting the same root documents under `docs/`.[^17][^18]

A uv development group and lockfile manage documentation and checking tools. No OpenT1D simulation package is defined yet. This follows uv's distinction between project dependencies and building or installing a project itself.[^19]

The local and CI routes are identical: Python tooling checks, Markdown checks, YAML checks, CFF validation and a full HTML build that fails on warnings. Sphinx provides a build mode treating warnings as errors. A separate linkcheck build can additionally check external references.[^20]

External links are not fetched as a requirement for every pull request. Publishers may block robots and websites may be temporarily unavailable. Results need assessment: rejection by a publisher does not prove that a source has disappeared. Internal document references must pass directly. An exception for the current private repository is temporary and must be reassessed at publication.

The workflow uses read-only repository permissions, full commit hashes for Actions, a time limit and cancellation of superseded runs. This follows GitHub's documentation on least privilege and pinning external Actions. An ordinary documentation check needs no write token, secrets or privileged pull-request trigger.[^21]

Dependabot is configured for Actions and uv. Updates remain reviewable changes. The documentation describes supported ecosystems and settings; a numerical dependency update will later also need assessment for changed scientific outcomes.[^22]

<a id="9-governance-en-onderhoud"></a>

## 9. Governance and maintenance

The current founder-maintainer is named. Decision-making is public in the project history once published: ordinary changes in a pull request, consequential conventions in short decision records. This is enough to retrieve decisions without tying development to a meeting schedule.

CODEOWNERS designates a responsible account. GitHub requires appropriate repository access for a code owner, and actual required approval is configured through branch protection or rulesets. The file alone therefore does not protect the main branch.[^23]

With one maintainer, the repository must not expect a mandatory second approver who does not exist. The proposed setting requires passing checks and a reviewable change trail; independent review is added when a second maintainer is available. Scientific claims requiring domain assessment meanwhile remain bounded by the evidence available.

Releases will later receive semantic software versions and a meaningful changelog. The chosen version convention says nothing about the magnitude of a changed scientific outcome. A correction to parameters or a metric definition must also be visible when the API stays the same.[^24][^25]

Scientific corrections require a separate procedure: describe the original claim, error, affected versions, expected impact and new outcome. Retain the old result with a correction reference. Reproducibility loses its meaning if old artifacts are silently overwritten afterwards.

<a id="10-invoering-en-acceptatie"></a>

## 10. Implementation and acceptance

The first step is the local foundation: coherent documents, existing metadata, a valid licence, templates and checking tools. The second step is activation on GitHub: first commit and push, hosted CI, suitable branch rules, working reporting channels and possibly documentation hosting. That second step must not be presented as complete merely because YAML files exist.

During preparation, the actual repository is private, without a first commit. Issues are enabled and Discussions are not. This initial situation explains why public clone and documentation links become usable only after access or publication. It is recorded in the [maintainer guide](../maintenance.md).

For local acceptance, the documentation build, relevant style checks, YAML structure and CFF validation must pass. Navigation and generated pages must also be inspected. A broken reference must demonstrably make the check fail. CI settings and issue forms can be assessed locally, but their final GitHub behaviour is confirmed only after activation.

After this foundation, M0 starts with a real protocol and upstream reproduction. New management tooling is added when it removes a concrete obstacle. The repository is designed to allow rapid development while keeping clear which outcomes have been demonstrated and which still require research.

<a id="bronnen"></a>

## Sources

All sources were accessed on 12 September 2026. Project documentation without a publication date refers to the version visible on that date. The references support the observed practices; the OpenT1D choices are the recommendations justified above.

[^1]: PyBaMM contributors. [PyBaMM repository and README](https://github.com/pybamm-team/PyBaMM). Project documentation, moving main branch.
[^2]: SciPy community. [Contribute to SciPy](https://scipy.org/contribute/). Project documentation.
[^3]: SciPy community. [SciPy Project Governance](https://docs.scipy.org/doc/scipy/dev/governance.html). Official developer documentation.
[^4]: scikit-learn developers. [Contributing](https://scikit-learn.org/stable/developers/contributing.html). Official contribution guide, including automated-contributions policy.
[^5]: Mesa contributors. [CONTRIBUTING.md](https://github.com/mesa/mesa/blob/main/CONTRIBUTING.md). Project documentation, moving main branch.
[^6]: PhysiCell contributors. [PhysiCell README](https://github.com/MathCancer/PhysiCell/blob/master/README.md). Project documentation with example projects and scientific reference.
[^7]: BioSimulators Team. [BioSimulators test suite documentation](https://docs.biosimulators.org/Biosimulators_test_suite/). Official description of conventions and example archives.
[^8]: Daniele Procida. [Diátaxis](https://diataxis.fr/). Official description of four documentation types.
[^9]: GitHub. [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file). Official product documentation.
[^10]: GitHub. [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). Official product documentation.
[^11]: GitHub. [Syntax for GitHub's form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema). Official product documentation.
[^12]: Apache Software Foundation. [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html). January 2004, official licence text.
[^13]: Free Software Foundation. [GNU GPL FAQ: mere aggregation](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation). Official explanation.
[^14]: Citation File Format contributors. [Citation File Format](https://citation-file-format.github.io/). Official format site and integration explanation.
[^15]: Citation File Format contributors. [cffconvert](https://github.com/citation-file-format/cffconvert). Official validator repository.
[^16]: Netherlands eScience Center and DANS. [FAIR software recommendations](https://fair-software.eu/). Official recommendations.
[^17]: Executable Books contributors. [MyST Parser: cross-references](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html). Official parser documentation.
[^18]: Executable Book Project. [Sphinx External ToC: configuration and structure](https://sphinx-external-toc.readthedocs.io/en/latest/user_guide/sphinx.html). Official extension documentation.
[^19]: Astral. [uv: configuring projects](https://docs.astral.sh/uv/concepts/projects/config/). Official documentation on project configuration and packaging.
[^20]: Sphinx developers. [sphinx-build](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). Official build documentation.
[^21]: GitHub. [Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions). Official security documentation.
[^22]: GitHub. [Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference). Official configuration reference.
[^23]: GitHub. [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Official product documentation.
[^24]: Tom Preston-Werner and contributors. [Semantic Versioning 2.0.0](https://semver.org/). Official specification.
[^25]: Keep a Changelog contributors. [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Guidelines and convention.
