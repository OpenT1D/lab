<a id="kritische-review-van-de-opent1d-repositorybasis"></a>

# Critical review of the OpenT1D repository foundation

Translated from Dutch on 29 October 2026. Historical findings, language-policy
statements and audit results below describe the original report, not a new review.

This report preserves findings about baseline commit `b6bb60486a6bdf158f9954073ca70c9c5bfa31bb`. Improvements were taken up after the review; the [maintainer guide](../maintenance.md#current-setup) describes the current operational status and remaining activation points. The original judgement below is not a new check of those subsequent changes.

<a id="1-oordeel"></a>

## 1. Judgement

**The repository foundation is suitable for starting M0 and continuing development on the current private main branch. It is not yet ready for full public onboarding, and the built documentation site has a concrete accessibility defect.** The research direction, contribution conventions and existing technical checks form a coherent foundation. No confirmed P0 or P1 was found that makes the current private `main` unusable or irresponsible.

The main substantive strength is that OpenT1D connects a large scientific goal to auditable intermediate results. The distinction between its own infrastructure, external models and targeted original modules is clear. The documents do not assign general validation status to software that merely installs or can execute a simulation. For this project, that matters more than a long list of community files or badges.

Four points require targeted follow-up. A confidential reporting channel is missing, branch rules are not enforced, dependency alerts are disabled and Dutch reports receive English language metadata. The first two were already described as open activation points; the current GitHub status confirms them. Disabled vulnerability alerts have now been explicitly established through the API. The incorrect language marking is a newly reproduced output defect.

| Finding | Severity | Private main | Public contributions | Built documentation site / first release |
| --- | --- | --- | --- | --- |
| B1 — No working confidential reporting route | P1 for public onboarding | No current blocker | Resolve first | Security route needed for a public software release |
| B2 — Checks and change route are not enforced | P2 | Known operational limitation | First implement the project's own publication conventions | Release process must use a demonstrably checked source version |
| B3 — Dependency alerts are disabled | P2 | Improvement to ongoing maintenance | Activate and check coverage | Include vulnerability assessment before software distribution |
| B4 — Dutch reports have English language metadata | P2 | No current blocker | No blocker for Markdown alone on GitHub | Resolve before public distribution of the HTML site |

P0 means an immediate serious problem; P1 blocks responsible use or the specified publication step; P2 is a meaningful quality or maintenance problem. P3 is used below only for optional strengthening of checks. The priorities assess impact at this stage, rather than being an automatically derived Scorecard score.

<a id="2-reikwijdte-en-bewijs"></a>

## 2. Scope and evidence

The assessed foundation is commit `b6bb60486a6bdf158f9954073ca70c9c5bfa31bb`, both locally and on GitHub `main` on 12 September 2026. The working directory was initially clean. All 50 tracked files were included: project documents, research reports, templates, licence and citation material, Python tooling, tests, lockfile and GitHub configuration. This new report and its navigation entry are outside the assessed baseline.

Technical verification includes a fresh clone without shared Git objects, a new `.venv` and an empty uv package cache. Installation fetched the dependencies again. The existing uv 0.11.16 and Python 3.12.13 on macOS ARM64 were used; the Python installation itself was not rebuilt from an empty machine. Additional negative probes used separate temporary copies and an existing tooling environment. This is a different type of evidence from the clean installation.

GitHub settings and existing hosted runs were read again. The successful [run on the current main commit](https://github.com/OpenT1D/OpenT1D/actions/runs/34717812888) and the [pull-request run before the merge](https://github.com/OpenT1D/OpenT1D/actions/runs/34717784427) confirm execution on Ubuntu 24.04. No new remote workflow was started for this review, and no setting, issue, pull request or branch was changed.

The comparison uses current official project documentation and primary guidelines. It assesses concrete practices, not the overall quality of the example projects. Moving documentation branches may change after the reference date. Scientific source checking targets decisive claims; it is not a full audit of all 41 scientific footnotes, underlying equations or clinical datasets.

<a id="3-wat-sterk-is"></a>

## 3. Strengths

<a id="31-een-duidelijke-ingang-en-één-uitvoeringsplan"></a>

### 3.1 A clear entry point and one execution plan

[README.md](../../README.md) makes the current status immediately visible. The installation commands build documentation and are described accordingly. A visitor is not offered a fictional simulator API, validated virtual patient or future release as an existing capability.

[ROADMAP.md](../../ROADMAP.md) is the leading plan. M0 requires a concrete protocol, checks of upstream ancestry and rights, and a reproducible reference. M1 provides a full experiment chain; M2 checks replaceability with another physiological family. Later biological and data-oriented paths have their own dependencies. The absence of a simulator is therefore an explicit project phase, not a missing foundation file.

The publication checklist also distinguishes preparation in files from activation on GitHub. This prevents CODEOWNERS, a security policy or a workflow file from being confused with required review, a reachable reporting channel or an actually successful run, respectively.

<a id="32-modulariteit-met-betekenisvolle-grenzen"></a>

### 3.2 Modularity with meaningful boundaries

The [architecture](../architecture.md) supports both whole engines and finer composition. Existing researchers do not first need to rewrite their model in a new equation language. At the same time, units, compartments, routes, time conventions and process ownership are explicit integration conditions.

This principle recurs in the model guide, model card and biological roadmap. For example, it prevents a module and an engine from silently both calculating the same absorption. The documents do not prescribe a universal interface before the first integrations demonstrate which conventions are actually needed.

<a id="33-wetenschappelijk-bewijs-blijft-afzonderlijk-zichtbaar"></a>

### 3.3 Scientific evidence remains separately visible

The [validation guide](../research/validation.md) distinguishes correct implementation, preservation of upstream behaviour, application-specific empirical evaluation and independent reproduction. The roadmap keeps technical progress and missing evidence separate. An exploratory module can therefore be useful without receiving an unsupported treatment claim.

Data assessment starts in M0. The [data guide](../research/data.md) addresses missing values, participant overlap, time semantics, actual delivery versus commands and access rights, among other things. Model and protocol templates ask for source versions, limitations, failures and evaluation separation. This is an appropriate substantive foundation for later reproducible research.

<a id="34-een-uitvoerbare-bijdrageprocedure"></a>

### 3.4 A usable contribution procedure

[CONTRIBUTING.md](../../CONTRIBUTING.md) offers concrete entry points for code, documentation, source assessment and reproduction. Required evidence differs by contribution type. Small corrections may go directly to a pull request; shared interfaces and new modules require an early substantive proposal. There is no general requirement to write a new decision record for every change.

Governance names a real responsible person, conflicts of interest and the limitations of one maintainer. AI assistance is permitted with responsibility for understanding, origin and verification. This supports rapid development without elevating automatically generated content to scientific evidence.

<a id="35-bestaande-technische-maatregelen-doen-werkelijk-iets"></a>

### 3.5 Existing technical measures actually work

The same repository check is used locally and in CI. The lockfile contains 62 package records from PyPI; the distribution archives listed there have SHA-256 hashes. The two Actions are pinned to full commit hashes. Workflows have read permissions, a time limit, cancellation of superseded runs and no privileged pull-request trigger.

Existing regression tests guard concrete faults. Disabling restricted page discovery makes the local-notes test fail. Disabling HTML-output cleanup makes the retired-pages-and-downloads test fail. The earlier fixes have therefore been checked again and are not listed again as open defects.

<a id="4-vergelijking-met-toonaangevende-projecten"></a>

## 4. Comparison with leading projects

| Project and checked practice | Problem addressed | Meaning for OpenT1D |
| --- | --- | --- |
| PyBaMM uses a specified development environment, strict documentation checks and credit for models and methods used.[^1] | An experiment must be executable and retain its scientific origins. | Retain locked tooling and the strict build. Later connect upstream citation to actual model manifests and executed experiments. Add example tests once real simulation examples exist. |
| SciPy also names documentation, review and reproduction as contributions and makes decision authority visible.[^2][^3] | New contributors need an entry point and to know how decisions are made or contested. | The different contribution forms and founder governance fit. A steering council is useful only when real members and responsibilities exist. |
| scikit-learn requires understandable, carefully assessed contributions and treats careless AI proposals as a burden on reviewers.[^4] | A submitter must be able to assess and maintain the proposed change. | Retain responsibility and verification; the more restrictive AI workflow need not be copied. OpenT1D may set its own explicit policy. |
| Mesa requires early discussion of problem and design, plus examples and tests for useful new features.[^5] | Avoid building much code before usefulness and integration are clear. | Retain a short upstream probe in M0 and focused design decisions. Do not introduce universal extra approval rounds for small changes. |
| PhysiCell provides concrete example projects with build and execution commands and scientific references.[^6] | Users learn the system through experiments that actually work. | Deliver a comparable first-use experience with M1. The current tooling quickstart is honest; a simulation tutorial without a simulator would not be. |
| BioSimulators connects execution conventions to testable example archives.[^7] | An interoperability claim must be auditable. | Adopt the principle of a reference per supported adapter. Implement COMBINE/OMEX or SED-ML only when a concrete supported task requires it. Technical conformance remains distinct from biological validity. |

This comparison supports the existing direction. The largest remaining improvement lies in completing and checking operational conventions, rather than copying more documents. A large project's contribution procedure is an example of a solution for its circumstances, not a universal prescription for OpenT1D.

For example, SciPy's current AI policy requires explicit disclosure and limits autonomous submissions.[^8] This is a project-specific policy. OpenSSF's Code-Review check also explicitly distinguishes independent human review from AI or bot review, while recognising the limitations of a project with one active contributor.[^9] This review does not establish that OpenT1D already has an independent human review practice.

<a id="5-relevante-standaarden-en-richtlijnen"></a>

## 5. Relevant standards and guidelines

| Framework | Status | Assessment and judgement |
| --- | --- | --- |
| GitHub community files and form schema | Product conventions and schemas | Recognisable files and three substantively appropriate issue forms are present. Schema rules differ from YAML formatting. Actual private form rendering remains to be checked separately.[^10][^11] |
| GitHub Actions secure use | Security guideline | Minimal token permissions, full SHA pinning and absence of privileged PR execution fit. Branch enforcement is separate.[^12] |
| CODEOWNERS and branch rules | Product conditions and settings | The named account has administrator rights and GitHub reports no CODEOWNERS errors. According to the branch API, `main` is not protected. See B2.[^13] |
| OpenSSF Scorecard | Heuristic checks | Useful dimensions include CI, review, branch protection, update policy, token permissions and vulnerabilities. No full Scorecard was run or overall score assigned.[^9] |
| OpenSSF Best Practices | Criteria for a voluntary badge programme | Licence, project description, contribution procedure and tests fit the foundation. Public accessibility, maintenance history and other criteria are not thereby established. Do not claim a badge.[^14] |
| FAIR software | Recommendations | Repository, licence, registration, citation and quality checks are useful goals. The current private repository does not have full public FAIR status. Arrange registration and archiving for an actually usable artifact.[^15] |
| SPDX and REUSE | Metadata conventions; REUSE is a voluntary specification | `Apache-2.0` is a clear identifier. Per-file rights metadata becomes more useful with mixed assets. Without a REUSE claim, lacking REUSE configuration is not a violation of that specification.[^16][^17] |
| Apache-2.0 | The chosen licence terms | Root licence and attribution policy are present. The guide treats rights to code, data and parameters separately. This is not a compatibility judgement on engines not yet integrated.[^18] |
| Citation File Format | Metadata format | The CFF validator passes. There are no fictional release details or DOIs. Copyright, permission and GitHub rendering do not follow from passing schema validation.[^19] |
| Diátaxis | Documentation method | Documentation is organised around reader questions. There is no requirement to create four empty directory trees or a nonexistent API reference.[^20] |
| WCAG 2.2, language marking | Formal accessibility criterion when assessing conformance | Dutch HTML content receives English language metadata. See B4. This is not a full WCAG audit or a statement about legal obligations.[^21][^22] |
| uv and Sphinx | Tool behaviour and configuration | The documented Python 3.12 route works from a new environment. A Sphinx build checks document references, but is not a general GitHub-schema or raw-HTML validator.[^23][^24] |

None of these frameworks requires OpenT1D to add a fictional release, package API, DOI, advisory board or complete biological standards implementation now. Nor does a community-health percentage prove that the science, contact channels or maintenance practice are sound.

<a id="6-bevindingen"></a>

## 6. Findings

<a id="b1--p1-bij-publieke-onboarding-vertrouwelijke-meldroute-ontbreekt"></a>

### B1 — P1 for public onboarding: confidential reporting route missing

**Location:** `SECURITY.md:7–9`, `CODE_OF_CONDUCT.md:20` and `docs/maintenance.md:20–21` in the reviewed commit.

**Evidence:** both policies explicitly state that no confidential channel is configured. The current private-vulnerability-reporting endpoint returned HTTP 404. That status alone does not prove a cause; combined with the explicit policies, it does show that no working route is confirmed. A conditional reference to a possible GitHub button is not yet a reachable channel. GitHub treats private vulnerability reporting as a feature to activate separately.[^25]

**Impact:** an external contributor cannot report a vulnerability or confidential conduct incident through a specified operational project route. The text is honest, but the missing implementation remains relevant when the community opens. This is an existing, explicitly known publication prerequisite, not a newly discovered exploit.

**Proposal:** include a contact route designated and managed by the owner. Security and conduct reports may share an entry point if handling is clear. Where appropriate, activate the GitHub feature when available. Do not invent an address, recipient or independent ombuds role.

**Acceptance:** the policies name a real reachable route and responsible person; an authorised test report privately reaches the intended recipient; limitations for a report about the sole maintainer remain visible. Sending such a test message requires separate permission and was not done in this review.

<a id="b2--p2-controles-en-wijzigingsroute-worden-niet-afgedwongen"></a>

### B2 — P2: checks and change route are not enforced

**Location:** GitHub settings for `main`; related conventions in `docs/maintenance.md:24–25`; `.github/workflows/checks.yml:3–27` and `.github/CODEOWNERS:2`.

**Evidence:** `GET /repos/OpenT1D/OpenT1D/branches/main` reported `protected: false`. Both the ruleset endpoint and branch-protection endpoint returned HTTP 403 with a message that a plan change or public visibility is needed. At the same time, hosted checks pass and GitHub recognises the code owner. There is therefore a working check, but no enforced connection between that check and every change to `main`.

**Impact:** a previous successful run does not prevent a later change being placed without a successful check or history being overwritten. For the current private founder phase, this is a known operational limitation. For public collaboration, the repository must actually configure its own described change route. CODEOWNERS alone is not protection.[^13]

**Proposal:** with the appropriate plan or visibility choice, configure the `Repository checks` status, pull-request route and protection against force-push/deletion. Explicitly record any maintainer bypass. Until then, use the agreed PR and checking procedure for changes and do not claim that GitHub enforces it.

**Acceptance:** settings and a controlled probe confirm that an ordinary change must achieve the required status and that force-push/deletion are restricted. A second human approver becomes mandatory only when actually available. The current limitation is no reason to make the repository public unasked during a review.

<a id="b3--p2-kwetsbaarheidsmeldingen-voor-dependencies-staan-uit"></a>

### B3 — P2: dependency vulnerability alerts are disabled

**Location:** current GitHub security settings; `.github/dependabot.yml:3–18`; open maintenance point `docs/maintenance.md:29`.

**Evidence:** the vulnerability-alerts endpoint returned HTTP 404 with an explicit message that alerts are disabled. The Dependabot-alerts endpoint confirmed this with HTTP 403. The YAML configuration schedules monthly version updates. GitHub distinguishes that feature from alerts about known vulnerabilities and from security updates.[^26][^27]

**Impact:** this feature does not provide ongoing project alerts for newly known dependency problems. A monthly update PR and a lockfile do not solve this independently. An isolated scan with pip-audit 2.10.1 found no known vulnerabilities in the 61 installed Python packages on the reference date, with no skipped packages. This is a snapshot, not evidence that monitoring is unnecessary.[^28]

**Proposal:** activate dependency alerts and check whether the dependency graph actually recognises the Python dependencies used. Assign follow-up and check notification preferences. If graph coverage is insufficient, choose a small periodic audit of dependencies actually used. Retain monthly version updates alongside this; automatic merges are unnecessary.

**Acceptance:** the alerts endpoint confirms activation, relevant dependencies are visible and someone is responsible for follow-up. Any missing ecosystem coverage is explicitly addressed. The audit or alerts have a checked route, without deliberately introducing a vulnerable package into the main branch.

This is a maintenance gap, not a demonstrated vulnerable dependency in the current version. The Python scan does not automatically cover Actions, the Python interpreter or the Mermaid library loaded from a CDN.

<a id="b4--p2-nederlandse-rapporten-worden-als-engels-gemarkeerd"></a>

### B4 — P2: Dutch reports are marked as English

**Location:** `docs/conf.py:7–35` and generated versions of the project-design and repository-foundation reports (original Dutch paths in the reviewed baseline).

**Evidence:** both HTML pages contain `lang="en"` on the `html` element and no `lang="nl"` on the Dutch article or another suitable content container. This was established again after the clean build. The document language therefore inherits English. Current tests do not check this property.

**Impact:** screen readers and other language-dependent tools receive the wrong pronunciation language for thousands of Dutch words. A document can look visually correct while being read aloud incorrectly. WCAG 2.2 SC 3.1.1 requires a programmatically determinable main language; SC 3.1.2 addresses different languages within content.[^21][^22]

**Proposal:** introduce per-document language metadata and apply it in actual template output. Predominantly Dutch pages receive `html lang="nl"`, English guides remain `en` and English interface elements receive `lang="en"`. Adding a frontmatter field without an effect on HTML is insufficient.

**Acceptance:** inspection of generated HTML shows the correct effective language for both existing reports and this new report; English pages retain their language. Add a regression check and inspect at least one report using language inspection or a screen reader. Because this review contains only reporting changes, the defect remains open for the HTML version of this report too.

The defect does not block further private development. It must be resolved before publicly sharing the built site. Making only the Markdown files public on GitHub is a separate publication step with different rendering.

<a id="7-verificatie-en-grenzen-van-de-controles"></a>

## 7. Verification and limits of the checks

<a id="71-werkelijk-uitgevoerde-controles"></a>

### 7.1 Checks actually executed

| Check | Outcome | Evidence limit |
| --- | --- | --- |
| Fresh clone, new `.venv`, empty package cache; `uv sync --locked` | Passed; dependencies fetched again | Used existing uv and Python installation; not a completely new machine |
| `uv run --locked python scripts/check.py` | Passed: Ruff, Markdown, YAML, CFF, navigation, seven tests, strict HTML build | No simulation or biological tests |
| Generated internal links and anchors | 1,464 references across 28 HTML pages, no error | Baseline before adding this report; not a full accessibility assessment |
| Existing GitHub Actions runs | Passed on the reviewed main commit and specified PR | Historical actual hosted runs verified again; no new remote run started for the review |
| `actionlint` 1.7.12 on both workflows | Passed | Separately available through Homebrew; not part of the specified repository check |
| pip-audit 2.10.1 on the clean Python environment | 61 packages, zero known vulnerabilities, zero skipped | PyPI advisory data on the reference date, installed Python packages only |
| Lockfile inventory | 62 package records, PyPI sources, distribution hashes present | Some platform-dependent packages are not installed locally; hashes do not prove absence of malicious code |
| CODEOWNERS API and account rights | No parse errors; named account has administrator rights | This file's existence does not require independent review |
| Language metadata of Dutch HTML reports | Defect reproduced: English language marking only | B4; visual layout and pronunciation are separate properties |

The uv warning about missing `requires-python` in this tooling-only configuration is visible. The specified Python 3.12 route works. `uv add --group dev PACKAGE` was also checked in a temporary copy with an available dependency. There is no evidence that a fictional installable OpenT1D package must now be added for this.[^23]

<a id="72-negatieve-proeven"></a>

### 7.2 Negative probes

Each change below was made in a separate temporary copy. Only synthetic content was used. The main repository and its existing tests were not changed.

| Probe | Actual response | Assessment |
| --- | --- | --- |
| Disable restricted Sphinx page discovery | Local-notes test fails | Existing protection against unintended page discovery is demonstrably guarded |
| Disable cleanup of old HTML output | Retired-pages/downloads test fails | Earlier fix has a relevant regression test |
| Add an explicit download link to a synthetic file in `data/private/` | Check passes; file is included as a download | Exactly documented boundary in `docs/development.md:42`; a page allowlist is not a sandbox for explicit assets |
| Add a raw HTML link to a missing file | Check passes; incorrect link appears in output | MyST does not fully check HTML links |
| Add a broken Markdown link in the PR template | Check passes | GitHub-only Markdown gets style checks, but no Sphinx reference checks |
| Change `runs-on` to `runs-onn` | Repository check passes; actionlint fails | YAML formatting checks are not Actions schema validation |
| Change issue-form type `textarea` to `textinput` | Repository check passes | YAML formatting checks do not prove form-schema conformance |

These probes show checking boundaries, not that current workflows, forms or existing references are defective. Current workflows actually pass actionlint and hosted execution. The existing explicit-asset warning must be retained; a deliberately linked test file is not evidence of a hidden leak in automatic page discovery.

The last four probes justify optional P3 strengthening: include actionlint reproducibly, add a limited form-schema check and check GitHub-only/raw-HTML links. Their acceptance criterion is rejection of the described synthetic fault while valid existing files pass. New tooling must use the same local and CI route, with limited maintenance burden.[^11][^29]

<a id="73-externe-links"></a>

### 7.3 External links

The separate Sphinx linkcheck ended with exit code 1. Of 87 external URL records, 70 were reported working, two as redirects and four deliberately skipped because of private repository access. Eleven requests were rejected: ten with HTTP 403 at PMC, NEJM and Sage, and one with HTTP 429 at GitHub/PhysiCell. No HTTP 404 was reported in this run. There were also ten local fragment records that this builder did not check; these fall under the separately successful internal HTML link check.

A 403 or 429 is insufficient to classify a scientific source as missing. Source checking examined relevant publication claims through original abstracts or author versions where possible. Not every rejected page was thereby fully verified. Keeping external availability outside the required PR check is appropriate; do not add broad permanent exceptions to make the report artificially green.

<a id="74-overige-github-status"></a>

### 7.4 Other GitHub status

The repository is private, `main` is the default branch, Issues are enabled and Discussions disabled. The About description is empty and there are no topics. This is a small discoverability point before public opening, not a defect in project content. The licence is recognised as Apache-2.0.

Actions are enabled and default workflow permissions are read-only. Current workflows pin their Actions, while account-wide SHA enforcement is disabled. That difference is not a defect in the current two files. Secret-protection status could not be established reliably from returned metadata; a missing value was not interpreted as disabled or passed.

Issue-form rendering, the citation panel and external-contribution approval were not fully confirmed through a logged-in browser. The maintainer checklist already lists the first two. Official form-schema documentation also limits submission blocking through `validations.required` to public repositories; different behaviour in a private repository is therefore not automatically a form defect.[^11]

<a id="8-inhoudelijke-en-wetenschappelijke-broncontrole"></a>

## 8. Substantive and scientific source checking

The checked core claims support the described phasing. A repository label or publication abstract is evidence only for the corresponding description, not for the numerical quality of a future adapter.

| Topic | Finding from primary source checking | Consequence |
| --- | --- | --- |
| simglucose | UVA/Padova 2008, 30 virtual profiles and access to additional patient states are described in the original repository.[^30] | Ancestry and limits on controller information are appropriately explicit |
| GluCoEnv | The repository refers to simglucose/UVA2008 and PyTorch execution.[^31] | A second implementation of this basis is not a second independent physiological family |
| LT1 | `Cambridge.ts` names Hovorka-related sources; the paper describes headless execution and modular architecture.[^32][^33] | A candidate for a different family and an adapter probe are supported; executability within OpenT1D remains to be proved |
| APS TestBed | The original article describes two simulators and fault injection.[^34] | The roadmap appropriately investigates whether existing infrastructure already covers part of the need |
| ReplayBG | The original evaluation uses 100 virtual people and two cases with real data.[^35] | The limited claim in the research foundation is appropriate; a Python port or new application does not automatically inherit this evidence |
| MetaboNet | Table 1 reports 3,135/1,895 subjects and 1,228.2/867.4 patient-years for total/public; §2.2 describes overlap and remaining multiple identifiers.[^36] | Source figures are correct, but are not an internal audit of unique participants or data content |
| MetaboNet-Bench | The appendix states restrictions to noncommercial research and education for the bundle.[^37] | The texts appropriately leave actual download and component terms decisive |
| Application-specific model evidence | FDA guidance describes risk-informed credibility; the calibration protocol addresses identifiability and uncertainty.[^38][^39] | OpenT1D uses this as a design framework and claims no automatic regulatory conformance |
| Biological model boundaries | The OGTT methodology study is not general T1D/graft validation; PhysioLab concerns the NOD mouse.[^40][^41] | The repository does not transfer evidence between populations and species without support |
| Therapy questions | TN10 examines risk before diagnosis, PROTECT recent diagnosis; the zimislecel publication reports 10 of 12 full-dose participants insulin-independent at one year, with immunosuppression and interim analyses.[^42][^43][^44] | The texts distinguish stage, endpoint and treatment conditions and promise no universal cure |

The distinction between older UVA/Padova generations and the extension to day-long simulation was also checked in the version-specific literature.[^45] None of these checks installed a simulator or examined patient records. Currently missing tolerance values, controller settings and final population selection belong to M0; adding arbitrary values would make the foundation less reliable.

Three substantive refinements are useful design choices, but not confirmed defects. If desired, make one external user question more explicit in M0, so that technical added value can also be tested against a real need. If desired, state directly with the MetaboNet counts that the reported subject count is not an independently deduplicated count of unique people; the existing overlap warning already covers this risk. Add a completed claim-evidence card when the first real upstream reproduction provides content for it.

<a id="9-geprioriteerd-verbeterplan"></a>

## 9. Prioritised improvement plan

| Order | Action | Complete when | Dependency |
| --- | --- | --- | --- |
| Next maintenance improvement | B3: arrange dependency alerts and coverage | Activation, relevant dependency graph and responsible person demonstrably present; any coverage gaps addressed | Authorised GitHub setting; no new model code needed |
| Before external public contributions | B1: complete confidential reporting channel | Policies refer to a working route and authorised receipt test passes | Owner supplies channel and recipient |
| Before external public contributions | B2: enforce change route where available | Required check, PR route, protection and any bypass demonstrably configured | Appropriate plan or deliberate publication step |
| Before public HTML site | B4: fix language metadata | Dutch and English content have appropriate effective language; regression test passes | Small documentation configuration/template change |
| At public opening | Execute remaining existing checklist | About, topics, private reporting where available, forms, citation panel and external-contribution permissions checked | Chosen publication and notification policy |
| Optional, with further tooling changes | P3: better guard schemas and other links | The four specified synthetic faults are rejected with useful explanations | Limited reproducible tooling extension |
| Then continue substantive work | Execute M0 according to the existing roadmap | Protocol, source revisions, asset rights, upstream reference and data fit concrete | Actual model research, no extra foundation bureaucracy |

For a first software or research release, existing milestone criteria remain applicable: a reproducible example, versions and permitted assets, relevant numerical checks, claim boundaries and an appropriate correction procedure. Packaging, distribution inventory, archiving and any attestations must follow the actual release. Their absence at the current documentation stage is not classified as a defect.

<a id="10-reproductie-en-beperkingen"></a>

## 10. Reproduction and limitations

The core check can be repeated from a fresh clone using the commands below. For comparison with this report, use the specified baseline commit and a separate empty cache; the site's size changes when this report is added.

```sh
uv sync --locked
uv run --locked python scripts/check.py
uv run --locked sphinx-build -E -a -b linkcheck -c docs . _build/linkcheck
```

The language finding can be inspected without an additional Python library:

```sh
uv run --locked python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class Languages(HTMLParser):
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "lang" in values:
            print(tag, values["lang"])

for name in ("projectopzet", "repositorybasis"):
    print(name)
    page = Path(f"_build/html/docs/onderzoek/{name}.html")
    Languages().feed(page.read_text(encoding="utf-8"))
PY
```

On the baseline, the output for both documents is only `html en`. The negative probes can be repeated separately with the changes from §7.2; never apply them to a source version being published. Checking returned HTTP statuses requires appropriate repository access. Reporting retains no credentials, patient data or test messages.

This research proves neither complete absence of vulnerabilities, full WCAG conformance, legal suitability of future model distributions nor biological validity. The supplementary audit tools are not part of the repository lockfile. Windows was not executed separately; Linux is supported by existing hosted runs, not a new local Linux installation. Scientific checks mainly concerned original abstracts, relevant text passages and project documentation; supplements, full data licences and all possible errata were not assessed exhaustively.

During the review, only this originally Dutch report and its table-of-contents reference were added. Improvements are implemented afterwards and do not change the evidence about the specified baseline.

<a id="bronnen"></a>

## Sources

All web sources were accessed on 12 September 2026. Project documentation and GitHub guidelines refer to the version accessed on that date. Repository findings refer to the recorded baseline commit; operational GitHub observations are dated snapshots. Publication years below belong to the original studies.

[^1]: PyBaMM contributors. [Contributing to PyBaMM](https://github.com/pybamm-team/PyBaMM/blob/main/CONTRIBUTING.md). Official contribution guide; tooling, documentation, examples and citations.
[^2]: SciPy community. [Contribute to SciPy](https://scipy.org/contribute/). Official contribution entry point.
[^3]: SciPy community. [SciPy Project Governance](https://docs.scipy.org/doc/scipy/dev/governance.html). Roles and decision-making.
[^4]: scikit-learn developers. [Contributing](https://scikit-learn.org/stable/developers/contributing.html). Contribution quality, rights and automated contributions.
[^5]: Mesa contributors. [Contributing to Mesa](https://github.com/mesa/mesa/blob/main/CONTRIBUTING.md). Problem discussion, design, examples and tests.
[^6]: PhysiCell contributors. [PhysiCell README](https://github.com/MathCancer/PhysiCell/blob/master/README.md). Example projects and scientific references; automated linkcheck returned HTTP 429 once.
[^7]: BioSimulators Team. [BioSimulators test suite](https://docs.biosimulators.org/Biosimulators_test_suite/). Simulator conventions and example archives.
[^8]: SciPy community. [AI Policy](https://docs.scipy.org/doc/scipy/dev/conduct/ai_policy.html). Project-specific policy, not a general standard for OpenT1D.
[^9]: OpenSSF Scorecard contributors. [Scorecard Checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md). Includes Code-Review, Branch-Protection, CI-Tests and Vulnerabilities; no Scorecard run or overall score for this review.
[^10]: GitHub. [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file). Supported community files.
[^11]: GitHub. [Syntax for GitHub's form schema](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-githubs-form-schema). Element types, validation and public-repository restriction for required fields.
[^12]: GitHub. [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use). Token permissions, pinning and handling untrusted input.
[^13]: GitHub. [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Required access and separate branch rules.
[^14]: OpenSSF. [Best Practices Badge: passing criteria](https://www.bestpractices.dev/en/criteria/0). Voluntary programme conditions.
[^15]: Netherlands eScience Center and DANS. [FAIR software recommendations](https://fair-software.eu/). Five recommendations for research software.
[^16]: SPDX Project. [Handling license information](https://spdx.dev/learn/handling-license-info/). Licence identifiers and per-file information.
[^17]: Free Software Foundation Europe. [REUSE Specification 3.3](https://reuse.software/spec-3.3/). Conditions for the voluntary REUSE approach.
[^18]: Apache Software Foundation. [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html). January 2004; official licence text.
[^19]: Citation File Format contributors. [Citation File Format](https://citation-file-format.github.io/). Metadata format and integrations.
[^20]: Daniele Procida. [Diátaxis](https://diataxis.fr/). Documentation method.
[^21]: W3C. [Understanding WCAG 2.2 SC 3.1.1: Language of Page](https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html). Language determination and assistive tools; the page refers to the formal criterion.
[^22]: W3C. [Understanding WCAG 2.2 SC 3.1.2: Language of Parts](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html). Language changes within content.
[^23]: Astral. [Configuring projects](https://docs.astral.sh/uv/concepts/projects/config/). Project configuration and distinction from packaging.
[^24]: Sphinx developers. [sphinx-build](https://www.sphinx-doc.org/en/master/man/sphinx-build.html). Build behaviour and warnings.
[^25]: GitHub. [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). Separate activation of the reporting feature.
[^26]: GitHub. [Dependabot alerts](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-alerts). Detection, activation, notifications and limitations.
[^27]: GitHub. [Dependabot version updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates). Distinction between version updates and security functionality.
[^28]: Python Packaging Authority. [pip-audit](https://github.com/pypa/pip-audit). Known vulnerabilities through advisory services; version 2.10.1 in this review, without automatic fixes.
[^29]: rhysd and contributors. [actionlint](https://github.com/rhysd/actionlint). Static validation of GitHub Actions; local version 1.7.12.
[^30]: Jinyu Xie and contributors. [simglucose](https://github.com/jxx123/simglucose). Original repository and documentation.
[^31]: GluCoEnv developers. [GluCoEnv](https://github.com/RL4H/GluCoEnv). Repository; physiological origins and execution.
[^32]: LoopInsighT1 contributors. [Cambridge.ts](https://github.com/hpeuscher/loopinsight1/blob/master/src/core/models/Cambridge.ts). Model implementation with original references.
[^33]: Peuscher et al. [A Modular Open-Source Framework for In-Browser Diabetes Simulation](https://backend.orbit.dtu.dk/ws/files/383717203/1-s2.0-S2405896324021827-main.pdf). IFAC-PapersOnLine, 2024; especially §2.2.
[^34]: Zhou et al. [Design and Validation of an Open-Source Closed-Loop Testbed for Artificial Pancreas Systems](https://arxiv.org/abs/2208.06479). CHASE, 2022; author version.
[^35]: Cappon et al. [ReplayBG: A Digital Twin-Based Methodology](https://pubmed.ncbi.nlm.nih.gov/37368794/). IEEE Transactions on Biomedical Engineering, 2023; original abstract.
[^36]: Wolff et al. [MetaboNet: The Largest Publicly Available Consolidated Dataset for Type 1 Diabetes Management](https://arxiv.org/html/2601.11505v1). 2026; table 1 and §2.2 of the author version.
[^37]: Jeffries et al. [MetaboNet-Bench](https://arxiv.org/html/2606.18640v1). Preprint, June 2026; appendix on data terms.
[^38]: U.S. Food and Drug Administration. [Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-credibility-computational-modeling-and-simulation-medical-device-submissions). Final guidance, November 2023.
[^39]: Villaverde et al. [A protocol for dynamic model calibration](https://pmc.ncbi.nlm.nih.gov/articles/PMC8769694/). Briefings in Bioinformatics, 2022; online 2021.
[^40]: Breda et al. [Oral glucose tolerance test minimal model indexes of beta-cell function and insulin sensitivity](https://pubmed.ncbi.nlm.nih.gov/11147781/). Diabetes, 2001; original methodology study.
[^41]: Shoda et al. [The Type 1 Diabetes PhysioLab Platform](https://pubmed.ncbi.nlm.nih.gov/20491795/). Clinical & Experimental Immunology, 2010; NOD mouse model.
[^42]: Herold et al. [An Anti-CD3 Antibody, Teplizumab, in Relatives at Risk for Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/31180194/). NEJM, 2019. Population and endpoint checked; a future reproduction must also use the corrected publication and supplements.
[^43]: Ramos et al. [Teplizumab and β-Cell Function in Newly Diagnosed Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/37861217/). NEJM, 2023; PROTECT.
[^44]: Reichman et al. [Stem Cell-Derived, Fully Differentiated Islets for Type 1 Diabetes](https://pubmed.ncbi.nlm.nih.gov/40544428/). NEJM, 2025; original abstract and indexed passages.
[^45]: Visentin et al. [The UVA/Padova Type 1 Diabetes Simulator Goes From Single Meal to Single Day](https://pubmed.ncbi.nlm.nih.gov/29451021/). Journal of Diabetes Science and Technology, 2018.
