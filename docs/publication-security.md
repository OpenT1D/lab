# Security boundary for source publication

The independent public snapshot offers the two synthetic MMTT tasks with the
patched root tooling. It includes historical research sources for inspection,
but does not offer a maintained installation of every recorded native engine.
The [public-source guide](public-source.md) owns export and history handling;
[SECURITY.md](../SECURITY.md) owns confidential reporting.

## Dependency review — 25 October 2026

The complete base alert inventory contains 230 alerts for **50 distinct
advisories**. Repeated manifests and package-name casing explain the difference.
[publication-security.json](../publication-security.json) records every advisory,
severity, affected range, first patched version, source URL and base manifest.
No alert was dismissed and no historical lock is declared patched.

On 28 October, the [primary certifi advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) was checked again after its
26 October update: its affected range now ends before **2026.10.18**, the first
patched version. The machine-readable inventory records that correction and
retains the originally recorded 2026.10.19 range as historical metadata.
Root certifi 2026.10.23 is beyond both boundaries; installation exclusions and
the historical runtime locks are unchanged.

| Package | Distinct advisories | Treatment in this source offering |
| --- | --- | --- |
| certifi | 1 | Root tooling uses 2026.10.23, beyond the current reported 2026.10.18 fix. Older historical entries are excluded from automatic public setup. |
| setuptools | 2 | Root tooling uses 84.2.1, beyond both reported fixes. Older historical entries are excluded. The legacy native pkg_resources requirement needs a separately verified successor. |
| Pillow | 41 | Five historical runtime locks contain 12.3.0. The reported fix is 13.0.0. These runtimes are excluded; no claim of harmless image processing is made. |
| filelock | 3 | Two C1 locks contain 4.0.3; the reported fix is 4.2.1. They are excluded. |
| urllib3 | 3 | The base simglucose lock contains 2.7.0; the reported fix is 2.8.0. That environment is excluded. |

The two root manifest entries are fixed locally. The other 228 base alerts remain
visible and apply to preserved historical environments. Their attack surfaces
include TLS trust/proxies, archive/build paths, lock-file handling and image/font
processing. Synthetic research use does not prove those vulnerabilities
unreachable. The standard-library MMTT calculations do not install those
numerical environments. This dated review is not a promise about future
advisories; refresh it before any subsequent release.

## Enforced automatic-installation boundary

A generated `publication-snapshot.json` identifies the independent public source.
Within that snapshot, the common CLI/GUI task-directed installer checks the
tracked policy **before any project installation or output creation**. It refuses
all projects outside the reviewed allowlist, including all six affected native
projects. A missing or invalid policy fails closed. Read-only setup inspection
and simulator-free reconstruction remain available.

The root project, the small NumPy-only C1 source environment and the separate M3
estimator have no matches in this dated advisory inventory and are listed in the
policy. That list does not expand the initial two-task acceptance scope.
Installation readiness does not establish scientific correctness.

This is an installer policy, not an operating-system sandbox. A trusted local
user can still run `uv sync --project ...` or remove source files manually.
Historical guides preserve those original commands as research records; they are
outside the maintained public installation route. Do not execute those frozen
environments on untrusted inputs or treat the old `secure` task name as a claim
that its dependencies have no current advisories. Use the private research
archive for deliberate historical reproduction under a separately assessed risk.

To re-enable a native public route, create an explicitly identified patched
successor, check its full dependency inventory, repeat the relevant numerical,
process and reconstruction checks, review upstream/table rights and update this
policy and supported scope. Preserve the original lock and evidence identity.
A new lock must not inherit an old numerical verification claim.

## Private Windows installer integration

The private OT-058 branch supplies an internal bundled installer, separately
from this source offering. Integration retains its verified-runtime inspection
and the public setup refusal, including when package metadata is present.
The Windows builder refuses a public source snapshot before output, download or
payload staging; the manual Windows workflow is private-repository-only.
Private internal builds remain possible and are not declared distributable by
that fact. See [the integration record](research/installer-publication-integration.md).

The source-only clearance does not cover the native/observer dependency locks,
Windows build-tool inputs, upstream parameter tables or transitive payload
assets as a public bundled product. In particular, the root tooling fixes do not
upgrade the separately pinned native runtimes or `dependency-inputs.json` build
backends. Review and identify a supported successor before widening distribution;
keep the recorded old environments and scientific evidence intact.

## CI and branch controls

When enabled, push and pull-request CI runs the root repository suite and documentation build,
the standard-library paired boundary check, three-host public task smokes and four
Linux Chromium flows. One required `Repository checks` result accepts only successful
root, platform and browser families, plus dependency review on pull requests.
Only the dependency job may be skipped on explicit `push` or `workflow_dispatch`
events. Native jobs and root steps that install native projects are gated.
A manual `historical_native` dispatch can enable them **only** in a private
repository without the public snapshot marker. Its default is false. Every
native job/step also requires literal private-repository, `workflow_dispatch`
and `historical_native` conditions in the workflow, alongside the scope helper's
output. A pull request that changes the helper to print `native_enabled=true`
cannot satisfy those independent public/private and event guards. The input
cannot enable historical native jobs in a public repository or exported snapshot.
A skipped native job is not numerical verification.

The initial source publication on 28 October 2026 had **no hosted CI/CD** and
disabled GitHub Actions on `OpenT1D/lab`. Its local checks and exact source receipts
are not hosted results. Initial main used pull-request and conversation
requirements, administrator enforcement and force-push/deletion protection
**without a required CI status**. Requiring an unexecuted check while Actions is
disabled would prevent ordinary changes. The activation procedure below prepares
the later operational change without claiming it has happened.

Use [.github/public-source-branch-protection.json](../.github/public-source-branch-protection.json)
for the public source default branch. It requires the actual **Repository
checks** result, pull requests and conversation resolution, including for
administrators, and forbids force pushes/deletion. It does not invent a second
reviewer. The older `main-branch-protection.json` retains the complete historical
16-job policy for deliberate private native verification; it is not the policy
for this bounded public offering.

The 25 October 2026 preparation recorded read-only workflow tokens, PR approval
by workflows disabled, four selected Action revisions, approval for all external
contributors, dependency alerts, private reporting, secret scanning and push
protection. These dated observations do not establish the current platform
settings. Current checked-in workflows pin their Action references; the prepared
allowlist below admits exactly the checked-in revisions. A separately enforced
platform SHA-pinning flag is not asserted here.

On 28 October 2026 the maintainer authorized publication of the reviewed source
without CI/CD. Actions was disabled. The initial main branch used
[the manual branch policy](../.github/public-source-manual-branch-protection.json),
with pull requests, conversation resolution, administrator enforcement and no
force pushes/deletion; it does not require an unexecuted CI status. The
CI-enabled JSON above remains reserved for a later explicit activation.
The separate private archive's earlier plan/account limitations remain dated
observations. Local verification is not a hosted CI result.

## Automatic dependency jobs during initial publication

The initial source push triggered three GitHub-managed Dependabot jobs despite
repository Actions being disabled: two finished before cancellation and one was
cancelled. Their [update run](https://github.com/OpenT1D/lab/actions/runs/40712032708),
[cancelled update](https://github.com/OpenT1D/lab/actions/runs/40712032550) and
[graph metadata run](https://github.com/OpenT1D/lab/actions/runs/40712032362) remain
visible as actual platform history. No repository test or installer workflow ran;
these service outcomes are not scientific or release verification.

Both generated update PRs were closed without merging. The configuration was
renamed to `.github/dependabot.example.yml` to disable automatic version updates.
At that point it was an inactive example, not a recognized `dependabot.yml` or
`dependabot.yaml`. Repository Actions remained disabled. The passive dependency graph, vulnerability
alerts, secret scanning and private reporting remain separate security features;
the graph may run platform metadata processing when supported manifests change.
Those dependency-service outcomes did not activate repository CI, release
automation or installer builds.

## Prepared dependency updates and PR review

The later recognized `.github/dependabot.yml` prepares monthly grouped updates
for root uv tooling and pinned Actions, capped at three open version-update PRs
per ecosystem. Its root uv scan explicitly excludes `experiments/**`,
`packaging/**` and `tests/**`. No historical numerical lock or bundled runtime is
automatically remediated by this configuration. Merging it to the default branch
enables update discovery; actual service runs and update PRs need their own
receipts. Update PRs still require review and the complete public gate.

The pinned Dependency Review v5 job has only `contents: read`, runs only on
`pull_request` and blocks newly introduced high/critical vulnerabilities in
runtime, development and unknown scopes. It disables PR comments, license checks,
warning-only mode and OpenSSF scorecard calls. It compares exact PR base/head
SHAs and installs no dependency project. It does not close existing advisories
or make historical environments supported.

V5's [snapshot retry timeout returns its current comparison](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/main.ts)
even when warnings remain. Therefore its successful result is followed by
`scripts/dependency_snapshot.py`. The guard polls the same
[dependency comparison API](https://docs.github.com/en/rest/dependency-graph/dependency-review)
for at most 120 seconds, checks warnings on every page, refuses redirects and
unsafe/incomplete pagination, and requires warning-free data to match the full
unfiltered dependency/advisory output from the official action. A partial action
result cannot become green merely because snapshots finish afterward. API,
parse, timeout and mismatch failures require investigation or a fresh run.

The stable public gate requires dependency-job success on PRs. It accepts only
that job's explicit skip for `push` and `workflow_dispatch`; all other public
families must succeed. Unknown/missing event information and skipped PR review
fail closed. Fork and Dependabot PRs retain read-only tokens and external approval
requirements. If GitHub cannot compare a fork's revisions or supply dependency
snapshots, that is a failed check to resolve, not permission to bypass it, add a
PAT or use a privileged PR trigger.

Before operational acceptance, observe a safe root `uv.lock` update in the
dependency graph and a disposable never-merge PR introducing a known high
advisory. Verify both the dependency job and aggregate fail, then remove the
probe and obtain green results. A requirements-file probe alone does not prove
uv-lock coverage. Local negative fixtures establish rejection logic only.
Snapshot completeness is bounded API evidence, not a guarantee that every
vulnerability is known or that software/scientific results are valid. Review
existing alerts separately; this increment supplies no automatic dismissals.

## CodeQL observation — 28 October 2026

The maintainer separately enabled GitHub-managed CodeQL default setup and read
back a configured weekly standard analysis for Python, JavaScript/TypeScript and
Actions. Its [initial hosted run](https://github.com/OpenT1D/lab/actions/runs/40757235369)
succeeded. The recorded main analyses contained fourteen initial Python signals
and no JavaScript or Actions signals; subsequent recorded PR analyses reported
zero new results. Those PR results do not establish a clean repository baseline.

A separate internal technical review found no demonstrated blocker for the two
maintained synthetic tasks. Signals included simulated physiological variables
misclassified as secrets, fixed invented fixtures and report fields, guarded
artifact/static routes and historical controller indices. The codeload URL
substring finding identified a small private-builder correctness follow-up;
the reviewed hash-pinned path did not demonstrate SSRF. This bounded triage does
not prove every alert false or qualify other workflows. All fourteen signals
were left open. The 228 historical dependency alerts were also left unchanged;
neither this triage nor the new PR delta check supplies automatic dismissals.

## Activate on the selected public destination

The selected new destination is [OpenT1D/lab](https://github.com/OpenT1D/lab).
Keep `OpenT1D/OpenT1D` private. The checked-in baseline retains the existing
fifteen historical native jobs and root steps, one required `Repository checks`
gate, read-only tokens and no checkout credentials. Public execution comprises
one broad root job, a Linux/macOS/Windows smoke matrix and a Linux browser job.
It explicitly selects Python 3.12, uv 0.11.16 and
Node 24.22.1 with dependency caching off. Historical native Node versions and
runtime locks remain separate. Public diagnostics contain synthetic-check logs,
per-command timing and selected source/event/runner/tool identities, retained for
five days. They supply evidence of the actual run, not scientific validation.

Activate only after review and local verification of the exact candidate. The
repository-level Actions switch and each workflow's state are separate controls.
Keep every checked-in workflow manually disabled while staging repository policy:

- [Action permissions](../.github/public-source-actions-permissions.json) is the
  prepared final body for `PUT /repos/OpenT1D/lab/actions/permissions`, including
  the requested `sha_pinning_required: true` setting. Verify its actual readback.
- [Selected revisions](../.github/public-source-selected-actions.json) is the body
  for `PUT /repos/OpenT1D/lab/actions/permissions/selected-actions`. It disables
  blanket GitHub-owned/verified-publisher allowances and lists exactly the
  checked-in Action revisions, including both historical and public Node actions.

These are prepared REST payloads, not settings receipts. Repository-level disabled
Actions can make the selected-actions API return HTTP 409; do not assume allowlist
staging/readback works in that state. Keep individual workflows disabled while
enabling repository-level access when required for those API operations. The
[official permissions API](https://docs.github.com/en/rest/actions/permissions)
describes the endpoints. Review inherited organization policy as well; do not
widen to wildcard or all-publisher access when a revision is missing.

Then perform and retain evidence for these platform steps:

1. List the actual workflows and put `checks.yml`, `links.yml` and
   `windows-installer.yml` into `disabled_manually` state. Read back every state
   before enabling repository-level Actions. A workflow source file or a native
   condition is not a receipt for this platform control.
2. Apply the reviewed repository Actions permissions with `allowed_actions:
   selected` and `sha_pinning_required: true`, enabling the repository if needed
   to use the selected-actions API. While all workflows remain manually disabled,
   apply and read back the exact checked-in allowlist. Verify read-only workflow
   tokens, PR approval by workflows disabled and approval for all external
   contributors. Read back the requested SHA-pinning setting as well.
3. Only after those controls match, enable the reviewed `checks.yml` workflow.
   Read back its enabled state and retain the reviewed source identity. Leave
   `links.yml` and `windows-installer.yml` manually disabled. The Windows workflow's
   separate private-only condition remains in place too.
4. In **Settings → Advanced Security**, verify dependency alerts, available secret
   scanning/push protection and private vulnerability reporting. Verify the private
   reporting entry point; the maintainer-confirmed email remains the fallback.
5. Obtain successful hosted **Repository checks** runs for the exact PR head and
   integrated main; inspect their event/source SHA receipts and explicit skips.
   Record cold-run setup/check times before changing runner sizes or timeouts.
   Only then apply the public source branch policy. The REST endpoint is
   `PUT /repos/{owner}/{repo}/branches/main/protection`, with the checked-in public
   JSON as its body. Inspect the resulting rules and verify an administrator
   cannot force-push/delete or bypass a required failed check. A manual dispatch
   alone does not replace the required PR/main event results. Do not apply the
   historical 16-job policy by accident.
6. Confirm the description/topics, issue forms, pull-request template, license
   and citation panels. Add a homepage only after checking an actual hosted site.
   Check account notification delivery separately. Review alerts on the actual
   default branch; preserved historical alerts are not automatically closed by
   excluding their installation routes.
7. Retain the narrow link-check exclusion for the separate private development
   archive. Public `OpenT1D/lab` URLs must not be excluded. Enabling/running the
   external-link workflow is a separate reviewed operation; retain its report
   when that operation is selected.

No platform setting is described as active until its actual response and
behavior have been verified. Publishing source does not create a supported
software release, independent-user acceptance or clinical/scientific evidence.
