# Maintainer guide

This guide distinguishes repository files from settings and services that require separate activation. It is also the release checklist for the initial maintainer.

## Current setup

As checked through the GitHub API on **25 October 2026**, `OpenT1D/OpenT1D`
is private, Issues are enabled and Discussions are disabled. Its description,
topics and homepage are empty. The default branch is `main` at `3787cc0`.
These are dated observations, not permanent settings.

Actions are enabled with read-only default token permissions and cannot approve
pull-request reviews. The private plan still returns HTTP 403 for branch
protection and rulesets. Fork-contributor approval returns HTTP 422 because the
repository is private; private vulnerability reporting returns HTTP 404. These
responses do not prove that public-repository controls have been activated.

The latest main workflow did not start its jobs because of an account
billing/spending-limit restriction, according to its check annotations. This is
not a successful hosted verification. The dependency graph/alerts endpoint is
enabled; there are **230 open alerts** at the audited base, including 29 critical
alerts across pinned environments. The
[publication preparation record](research/publication-preparation.md) records
scope, technical scans, targeted root-tooling fixes and remaining actions.
Older foundation CI passes do not replace a passing run on a release candidate.

## Private development and public source

The maintainer selected `OpenT1D/lab` for the independent public source on
25 October 2026. `OpenT1D/OpenT1D` stays private with its existing history and
remote configuration. The observations above refer to that private archive;
activation and current-head CI on the selected destination are verified separately.

On 28 October 2026, the maintainer authorized the reviewed source publication.
`OpenT1D/lab` starts from the independently reviewed root
`60a756b3707827c7e7cc76a65f817f21d52cae40`, followed by a documentation-only status
commit. It is development research source, with no version tag, release,
installer or bundled runtime. The private development archive is not pushed.

GitHub Actions is disabled. The initial main branch uses the
[manual branch policy](../.github/public-source-manual-branch-protection.json):
pull requests, conversation resolution and administrator enforcement, no force
pushes/deletion, and no required CI status. No hosted pass is claimed. Private
vulnerability reporting, dependency alerts and available secret scanning/push
protection remain separate repository controls. The dated preparation record
retains the earlier empty-destination observations and local verification.

Use the [public-source guide](public-source.md) to prepare a new local Git root
without the private development history. Preserve original evidence privately and
review the explicit path-redaction map. Run checks on that new candidate before
selecting or publishing to a GitHub destination.

## Before opening the project to public contributions

The requested initial source publication has no hosted CI/CD. Disable Actions
before pushing, then use the [manual branch-control variant](publication-security.md#ci-and-branch-controls)
with pull requests, conversation resolution, administrator enforcement and no
force pushes/deletion, but no required CI status. Hosted-CI checklist items below
remain deferred until explicit activation; they are not local-check failures or
prerequisites for publishing this development source snapshot.

- [x] Preserve the original private development archive and prepare an independent public source root. Select its actual public destination separately.
- [x] Record original-material authority, reviewed upstream/font notices and explicit source-only exclusions in [the rights inventory](../publication-rights.json). The two complete upstream parameter rows are withheld; originals remain private.
- [x] Triage all 50 distinct base advisories; patch root entries and enforce [public installation/CI scope](publication-security.md), preserving historical locks and their open alerts.
- [x] Verify the independent public root `de3d111f856c` and its receiving bundle clone, full checks, MMTT reports and fresh history scan. The [dated audit](research/publication-preparation.md#final-source-only-candidate) records this exact export and its four unavailable historical Actions-log downloads as explicit limits.
- [x] Set and verify preparation-status description and five research topics on the empty `OpenT1D/lab` destination; no homepage is advertised.
- [x] Record the maintainer-selected confidential contact in both security and conduct policies.
- [x] Maintainer confirmed ownership and message receipt at the chosen contact on 25 October 2026; no assistant test email was sent.
- [x] Enable private vulnerability reporting on `OpenT1D/lab` and verify the enabled API state. End-to-end report/notification delivery is not claimed; no fictitious report was sent.
- [ ] After explicit source-publication authorization, run `Repository checks` on the new public head and resulting default branch. The current destination is empty; native jobs remain excluded from the offering.
- [ ] Verify the current pull-request head; the [historical foundation pass](https://github.com/OpenT1D/OpenT1D/actions/runs/34717719104) is not current-head evidence.
- [ ] After a future authorized first source push creates main, activate [.github/public-source-branch-protection.json](../.github/public-source-branch-protection.json) for the public source scope (see [activation steps](publication-security.md#activate-on-the-selected-public-destination)): require the `Repository checks` status and prevent force pushes and deletion. Verify enforcement, including for administrators.
- [ ] Require pull requests for shared changes. Do not require an approving reviewer who does not exist; add required independent review when another maintainer can provide it.
- [x] Confirm `.github/CODEOWNERS` names an account with write access. CODEOWNERS alone does not enforce approval.
- [x] Confirm Actions permissions are read-only by default.
- [x] Require approval for all external contributors on `OpenT1D/lab`, verified through its fork-workflow approval API.
- [x] Verify that dependency alerts are enabled and inventory all open alerts (25 October audit); the reviewed mitigations and remaining historical alerts are recorded in [the public source policy](publication-security.md).
- [ ] Confirm the maintainer's Dependabot notification preferences and delivery; use the repository's Security tab for alert triage in the meantime.
- [x] Enable and read back secret scanning and push protection on the public destination. No source was pushed to test a real credential rejection.
- [ ] Verify issue forms, the pull-request template, license detection and the citation panel after the default branch exists.
- [ ] Run the external-link review on the public `OpenT1D/lab` URLs; retain the narrow exception only for the separate private `OpenT1D/OpenT1D` archive.
- [ ] Decide whether to publish the built documentation using GitHub Pages or another host. Verify its URL before adding a website link or badge.

Changing repository visibility, enabling hosting and sending community announcements are separate publication actions. This checklist does not perform them.

## Private installer integration

The [integration record](research/installer-publication-integration.md) binds the
combined private source, retained laboratory plan and publication safeguards.
The earlier source-only checkboxes do not accept a bundled Windows distribution.
Keep its native/build dependency, upstream-asset and table provenance review,
fresh executable identity/Windows checks, independent use and signing decisions
separate. Old J reports remain attached to J's original build. This task makes
no remote change and does not trigger a workflow or publication.

## Proposed first release scope

Prepare a **source-checkout development release** on macOS arm64 with Python
3.12 and uv, limited to the two synthetic standard-library meal-test tasks:
[paired sensitivity](observation-analysis.md) and
[reduced sampling](mmtt-sampling.md). This is a proposed scope for review,
not a published version or a claim that broader routes have been accepted.
Keep the existing per-task scientific contracts and roadmap acceptance gates.
Windows installers, bundled runtimes, patient data and clinical use are outside
this candidate; a Windows offering must satisfy OT-058's own host checks.

Before tagging that candidate:

1. Identify the exact commit, uv/Python/OS versions, supplied cases and permitted
   assets. Review any added assets and refresh the source-only rights/security inventories for that release.
   Publish the supported-task/OS boundary and known limitations.
2. Clone that commit into a fresh directory and run `uv sync --locked` into a
   new environment. Use the canonical guides for both complete CLI examples;
   retain original and reconstructed Markdown/JSON and compare their bytes.
   Record setup failures and actual source identities. A fresh environment on a
   developer laptop is not a clean-OS or independent-user test.
3. In the GUI, complete both tasks, fix a deliberately invalid configuration,
   check/download the saved report, restart and reopen it. Preserve the original
   failed attempt. Test an existing incomplete example and distinguish a finished
   execution, complete coverage and successful reconstruction. Use the existing
   [test-session packet](gui-test-session.md), with a newly frozen commit and
   scope; do not reuse an old packet's identity for new source.
4. Ask a researcher who did not develop the workflow to install, perform both
   tasks, interpret their synthetic limits and recover/reopen a report using
   only the supplied instructions. Record assistance and blocking problems.
   One successful session supports only this bounded first-use scope; comparative
   researcher value still needs the separate OT-056/072 evidence.
5. Recheck repository controls, required CI results, dependency advisories,
   notices, citation metadata and the changelog for the final commit. Assign a
   real development version/date only when preparing that actual release.

Acceptance requires successful installation and both report reconstructions,
no unresolved blocker to the declared tasks, a completed independent exercise
with any assistance disclosed, and explicit release/rights decisions. Keep
unperformed steps open. Do not infer scientific validity from these checks.

## Main-branch protection

For the public source offering, use the prepared
[public source policy](../.github/public-source-branch-protection.json). It requires
pull requests, the up-to-date `Repository checks` result from GitHub Actions and
resolved review conversations, blocks force pushes/deletion and applies to
administrators. It does not invent a second reviewer. The separate
`main-branch-protection.json` preserves the historical 16-job inventory; do not
apply it as the public source policy. Skipped native jobs are not verification.

The maintainer selected `OpenT1D/lab` as the new public destination. Inspect any
existing rules there and keep the original private archive separate. This [GitHub API operation](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection)
replaces branch-protection settings; review the body before running it:

```sh
PUBLIC_REPO='OpenT1D/lab'
gh repo view "$PUBLIC_REPO" --json nameWithOwner,visibility,defaultBranchRef
gh api --method PUT "repos/$PUBLIC_REPO/branches/main/protection" \
  --input .github/public-source-branch-protection.json
gh api "repos/$PUBLIC_REPO/branches/main/protection"
gh api "repos/$PUBLIC_REPO/branches/main" --jq '.protected'
```

Verify the actual required check, PR requirement and force-push/deletion
restrictions, including administrator enforcement. A checked-in JSON file does
not activate those controls. The [publication activation guide](publication-security.md#activate-on-the-selected-public-destination)
owns the remaining server settings. Hosted CI must pass on the selected public
head and resulting default branch; the private account restriction is not a pass.

## Issue triage

Start with the supplied bug/scientific-correctness, proposal and question forms. Keep blank issues enabled for reports that do not fit. A scientific error should be routed to the affected experiment or model, not dismissed because the code executes successfully.

Use a small label set when triage needs it: `bug`, `documentation`, `proposal`, `scientific-correctness`, `help wanted` and `good first issue`. Templates do not depend on labels already existing. Apply `good first issue` only when the task has a clear scope and a reproducible starting point.

Do not automatically close unresolved scientific issues as stale. Review old issues when they block active work or when new evidence becomes available.

## Continuous integration

The required workflow installs the locked development environment and runs the same command as contributors. It checks the navigation and tests that local notes stay out of the generated pages and search index. It uses read-only permissions, SHA-pinned actions, a timeout and cancellation of superseded runs. It does not need repository secrets or run pull-request code with privileged triggers.

Automatic Dependabot version updates are disabled. The inactive `.github/dependabot.example.yml` preserves the optional monthly GitHub Actions/root-tooling configuration for a later explicit activation. The separately frozen native environments are not configured for automatic monthly version updates. Updates are reviewed, not automatically merged. Vulnerability alerts are enabled separately; the maintainer reviews them in the repository's Security tab and checks the affected version and use before deciding whether to update, mitigate or dismiss with a reason. Recheck dependency-graph coverage when the lockfile or packaging changes. These alerts do not cover every risk in the interpreter, downloaded browser libraries or commit-pinned Actions. A dependency changing numerical behavior in a future model integration also needs scientific-impact review.

The external-link workflow is manually triggered and reports link-check results in its log. Publisher access restrictions can cause false alarms, so it is not a required merge check. Revisit temporary exceptions before public releases.

## Releases

There is no release schedule or published simulator package yet. M1 and M2 run from a checkout with isolated pinned environments; see the [M1](m1-tutorial.md) and [M2](m2-tutorial.md) tutorials. Use semantic versioning for the first public software API, with `0.x` indicating development and explicitly documented breaking changes. Do not treat that convention as permission to make silent changes to scientific results.

Model, parameter, protocol and metric versions must be identifiable independently of the package version. Even an API-compatible correction can change a result.

Before a software or research release:

- [ ] Check the release scope against its roadmap acceptance criteria.
- [ ] Run the relevant software, adapter, scientific and documentation checks.
- [ ] Reproduce the supported example from a clean environment.
- [ ] Review the changelog, known limitations, migration instructions and result-changing corrections.
- [ ] Verify licenses and notices for the actual distribution and example data.
- [ ] Check citation metadata and the manifest's upstream references.
- [ ] Archive permitted experiment inputs and outputs, including failures and exclusions.
- [ ] Update the version and release date only when preparing that actual release.
- [ ] Publish the intended artifact, then verify that it can be retrieved and used.
- [ ] Add a DOI only after a real archival record has been created.

Package publishing, signed artifacts, provenance attestations, SBOM generation and release automation should be introduced with the first distributable runtime package. No publishing credentials are needed for the documentation foundation.

## Scientific corrections

Identify the affected model, parameters, protocol, analysis and releases. Record the original claim, the defect or new evidence, its expected impact and the corrected result. Preserve the original artifact with a correction notice rather than silently rewriting it.

If the impact is not yet known, say so and mark the affected conclusion accordingly. Coordinate private handling first if the issue also exposes a vulnerability or protected data. Update the changelog and documentation, and prepare an advisory or other notice when appropriate.

## Keep the foundation current

Update status when a capability actually ships. Keep one canonical roadmap and link to it. Refresh source-dependent research decisions when the evidence or upstream software changes. Document ownership changes in governance and CODEOWNERS together.

Add operational machinery when it solves an observed need: separate support channels, formal release roles or a steering group should correspond to real people and processes. Avoid advertising service levels, partnerships, endorsements or badges that the project has not earned.

## M0 runtime compatibility

The historical simglucose runtime needs setuptools 80.9.0 for `pkg_resources`;
its separate build constraint is 84.0.0. Root tooling uses 84.2.1. Those are
separate identities: changing the root environment does not patch a native lock.
The old source-distribution advisory remains open, alongside the other findings
in the complete [dependency review](publication-security.md).
Do not build/publish source distributions or process untrusted inputs there.

The public snapshot excludes automatic installation of these historical native
projects. A patched successor needs explicit source/runtime identity, dependency
review and repeated numerical/process/reconstruction checks. Preserve the old
lock and evidence; do not silently replace them or describe an old `secure`
task name as current advisory clearance.

## M3 preparation checks and private evidence

The separate M3 estimator lock is outside the initial two-task public acceptance
scope. Its native job is retained for deliberate private-archive verification;
see [CI scope](publication-security.md#ci-and-branch-controls). It checks native
estimator equivalence, development-only fitting and synthetic report
reconstruction. Neither that job nor the other native jobs runs automatically
on public pull requests. No skipped job counts as executed evidence.

The maintained private checkout's ignored `results/m3-archive` stores synthetic
evidence and source-documentation audit results. The tracked M3 index and local
supplemental indices identify attempts. Human source files, individual
predictions, identity maps and source hashes require a separate restricted store
and agreement-specific retention; never upload them through public CI artifacts.
See the [M3 tutorial](m3-tutorial.md).

## M0 evidence and regression review

For a proposed native model change, require the applicable structural checks,
fresh-process/native-reset equality and recorded historical baseline under an
explicitly identified, reviewed environment. A green replay alone is
insufficient. Archive and explain numerical differences before changing a
baseline; see the [reproduction policy](research/m0-reproduction.md#review-corrections-and-historical-baseline-policy).
The public source CI pass does not perform that native acceptance.

The maintainer retains the ignored `results/m0-archive` store in the private
main checkout. `experiments/m0/evidence-index.json` records verified bundle and
inventory digests. Preserve permitted CI artifacts before expiry, verify bundles
with `experiments/m0/archive.py`, and index their metadata. Do not delete original
evidence with worktree cleanup. Include it in local-data backups; this is not a
published archive or an offsite backup. Public redacted copies may need the
matching private original reader/source described in [the export guide](public-source.md).

## M2 evidence and human reproduction

The [M2 evidence record](research/m2-reproduction.md) identifies the frozen
commit, observed results and outstanding human reproduction. Preserve the
ignored `results/m2-archive` alongside M0/M1 stores and verify the tracked M2
index with the same archive tool. Keep failed attempts separate; never overwrite
a study or silently enroll new historical digests.

Another person must follow the tutorial at the recorded commit and complete the
result template to close independent reproduction. Internal development may
continue under [decision 0005](decisions/0005-internal-verification-and-external-review.md).
A subprocess, AI session or CI run cannot close that human gate.

## Historical numerical CI inventory

The workflow retains 16 named jobs, 15 of them native campaigns gated behind an
explicit `historical_native` manual dispatch in a private repository without the
snapshot marker. The root job's native steps are gated too. The authoritative
job names/commands are in [checks.yml](../.github/workflows/checks.yml), and the
[current scope policy](publication-security.md#ci-and-branch-controls) defines
when they may execute. The old 7-, 8-, 13- and 14-job counts belong to earlier
increments and are not the current required public checks.

The preserved jobs cover native references, M1/M2 and internal verification,
M3, literature absorption, M4 feedback/configurable/maintained studies,
conditional parameter recovery, volume sensitivity, likelihood profiles and C1
checkpoint boundaries. Their protocols and dated research records own matrices,
failures, numerical criteria and observed hosted results. Job configuration and
timeouts do not establish execution. Assess risk and rights before a deliberate
private rerun; a future maintained public native route needs its own verified
patched successor and explicit supported scope.
