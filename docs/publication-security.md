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
plus the standard-library paired boundary check. The suite includes the synthetic
MMTT routes. Native jobs and root steps that install native projects are gated.
A manual `historical_native` dispatch can enable them **only** in a private
repository without the public snapshot marker. Its default is false. The input
cannot enable historical native jobs in a public repository or exported snapshot.
A skipped native job is not numerical verification.

The requested first source publication has **no hosted CI/CD**. Before its first
push, disable GitHub Actions on `OpenT1D/lab` and verify that setting. Retain the
local checks and exact source receipts; do not describe them as hosted results.
After main exists, enable pull-request and conversation requirements, administrator
enforcement, and force-push/deletion protection **without a required CI status**.
The JSON policy below is reserved for a later explicit CI activation; requiring
its unexecuted check while Actions is disabled would prevent ordinary changes.

Use [.github/public-source-branch-protection.json](../.github/public-source-branch-protection.json)
for the public source default branch. It requires the actual **Repository
checks** result, pull requests and conversation resolution, including for
administrators, and forbids force pushes/deletion. It does not invent a second
reviewer. The older `main-branch-protection.json` retains the complete historical
16-job policy for deliberate private native verification; it is not the policy
for this bounded public offering.

The public destination's repository-level security settings are now configured:
read-only workflow tokens, PR approval by workflows disabled, exactly four
allowed Action revisions with mandatory SHA pinning, approval for all external
contributors, dependency alerts, private reporting, secret scanning and push
protection. Their API states were read back on 25 October 2026.

On 28 October 2026 the maintainer authorized publication of the reviewed source
without CI/CD. Actions is disabled. The initial main branch uses
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
It is an inactive example, not a recognized `dependabot.yml` or `dependabot.yaml`.
Repository Actions stays disabled. The passive dependency graph, vulnerability
alerts, secret scanning and private reporting remain separate security features;
the graph may run platform metadata processing when supported manifests change.
No hosted repository CI, release automation or installer build is enabled.

## Activate on the selected public destination

The selected new destination is [OpenT1D/lab](https://github.com/OpenT1D/lab).
Keep `OpenT1D/OpenT1D` private. After the independent root is published to `lab`,
perform and verify these platform steps there:

For the initial publication without CI/CD, apply the disabled-Actions and manual
branch-control variant above. Do not run the workflows mentioned below. Steps 2,
4 and 6 describe later hosted-CI activation and require a separate decision.

1. Set the description to `Open, modular research tools for reproducible type 1
   diabetes experiments.` Add `type-1-diabetes`, `research-software`, `simulation`,
   `reproducible-research` and `python` topics. Add a homepage only after checking
   an actual hosted site.
2. In **Settings → Actions → General**, use read-only workflow permissions,
   disable pull-request approval by workflows, and require approval for all
   external contributors. Retain commit-pinned Actions and no checkout credentials.
3. In **Settings → Advanced Security**, enable dependency alerts, available secret
   scanning/push protection and private vulnerability reporting. Verify the private
   reporting entry point; the maintainer-confirmed email remains the fallback.
4. Apply the public source branch policy after **Repository checks** has run on
   the new default branch. The REST endpoint is
   `PUT /repos/{owner}/{repo}/branches/main/protection`, with the checked-in public
   JSON as its body. Inspect the resulting rules and verify an administrator
   cannot force-push/delete or bypass a required failed check. Do not apply the
   historical 16-job policy by accident.
5. Confirm the issue forms, pull-request template, license and citation panels.
   Check account notification delivery separately. Review alerts on the actual
   default branch; preserved historical alerts are not automatically closed by
   excluding their installation routes.
6. Retain the narrow link-check exclusion for the separate private development
   archive. Public `OpenT1D/lab` URLs must not be excluded. Run the manual
   external-link workflow and inspect its report after the default branch exists.

No platform setting is described as active until its actual response and
behavior have been verified. Publishing source does not create a supported
software release, independent-user acceptance or clinical/scientific evidence.
