# Source publication preparation — 25 October 2026

This record prepares a public source repository separately from a first software
release. The audited base is `3787cc076d8a4850da5e91563c8fa8852a0a3393` on
`main`. Preparation is on `codex/public-release-preparation` in a separate local
worktree. No repository visibility change, public hosting, release, external
handoff or independent-user acceptance is established by this record.
The latest source-only rights/security disposition below supersedes the open
rights/contact/triage items of the earlier local candidate. That candidate is
retained as historical verification, not silently relabeled as the new export.
The exact new root and its checks are recorded in the separately delivered
commit-bound verification receipt after export.
The [maintainer guide](../maintenance.md) owns the publication checklist and
proposed first-release exercise; the [roadmap](../../ROADMAP.md) owns delivery
order and scientific acceptance.

## Source review 28 October 2026

The current preparation combines private main, the OT-058 installer source and
publication safeguards. The [integration record](installer-publication-integration.md)
keeps the original source identities and Windows limitations. Later local review
corrected mixed-language test-session labels, the language metadata of one
historical Dutch report and stale roadmap status. Five Dutch research reports
and optional Dutch session cards are intentional; the general guides and
experiment interface are English.

The independent source export passed 1,560 tests with 32 existing skips, both
complete synthetic MMTT examples and 12 byte-identical report reconstructions.
The content audit found only the maintainer-authorized public identity/contact,
upstream attribution and artificial test identities. Six notice hashes and all
14 redacted-source hashes were checked. File and Git-history secret scans found
no credentials. Exact receiving identities and logs are retained with private
verification receipts; every export has its own `publication-snapshot.json`.
Older ZIPs and commit identities below remain historical artifacts.

The primary certifi advisory was rechecked on 28 October after its 26 October
update: the first patched version is now reported as 2026.10.18, rather than the
2026.10.19 recorded in the dated review below. The current
[security inventory](../../publication-security.json) retains both observations;
root 2026.10.23 remains beyond the affected range.

`OpenT1D/lab` is still empty and the original repository remains private.
Actions was observed enabled on the destination with zero runs. The requested
publication has no CI/CD: disable Actions before a future authorized first push,
then apply the [manual branch controls](../publication-security.md#ci-and-branch-controls)
without requiring an unexecuted status check. No source, tag, installer or release
was published by this review. Metadata about an empty destination is dated
pre-publication evidence; refresh it when publication actually occurs.

## Selected public destination

On 25 October 2026 the maintainer selected a new public `OpenT1D/lab` repository,
while retaining `OpenT1D/OpenT1D` privately without renaming it. Read-only preflight
confirmed that `lab` did not exist and the development repository remained
private; the authenticated account has administration rights. Current support,
citation, documentation-source and clone links now select `lab`. Historical
commit/PR/Actions evidence links keep the private archive identity and its narrow
external-link exception. Publication and server-control results are recorded
against their actual new commit rather than inferred from this selection.

## Lab preparation-only status

The maintainer selected `OpenT1D/lab`, then explicitly clarified that the source
must remain unpublished while the first version is prepared. The public
repository was created empty and labeled `OpenT1D research software. First
version in preparation; source publication pending.` Its five topics match the
research/source scope. No source push, release or version tag was performed.
Read-only verification found zero branches, commits, tags and releases; the
original `OpenT1D/OpenT1D` repository remains private at its unchanged main SHA.

The following settings were configured **only on the new destination** and read
back through GitHub's API: read-only workflow tokens, workflow PR approval
disabled, selected Actions limited to the four exact revisions already used by
the workflows, SHA pinning required, approval for all external fork contributors,
dependency alerts, private vulnerability reporting, secret scanning and push
protection. No organization-wide or private-archive setting was changed.
Main-branch protection and hosted source CI await an authorized first push;
there is no branch or workflow source to verify yet. Issue/license/citation-panel
rendering and account notification delivery remain open. No fake vulnerability
report or test email was sent.

The current source-preparation commit is
`b7cd479efac9c52e2437ed2a9d7d7dac94157f8b`; its new **local** single-commit root is
`0cec667fdde744e878be0ce26d79664f7a377e29`. This export includes the documentation
consistency fixes and selected public URLs. Guide packets now select the public
repository for snapshot commits and the private repository for private commits;
one regression test covers both targets and preserved local guide links.

On that exact local root, `uv sync --locked` and the complete repository checks
passed: **1,407 tests in 421.760 seconds, 13 existing skips**, lint, citation,
navigation and the clean warning-as-error Sphinx build. Both MMTT examples passed
15 commands and reproduced all 12 report files byte-for-byte. Actual native
installer attempts were refused before output/environment creation. A simulated
private/manual CI request still cannot enable native jobs in the snapshot.
No native environment was installed. Workflow `actionlint` passed without
ShellCheck integration; 285 generated HTML pages had no missing targets/fragments
in 87,146 local hyperlink instances. External URLs were not fully rechecked;
public source-file URLs are intentionally unavailable while the repo is empty.

The new-root Gitleaks review found the same 21 file digests and one categorical
key, with no credential finding and no added allowlist. The receiving Git-bundle
clone has only the prepared root and cannot resolve the private source revision.
The source ZIP/bundle, checksums, verification receipt and explicit **do not
publish** instructions are packaged locally in
`OpenT1D-lab-preparation-0cec667fdde7.zip`, SHA-256
`5b1626480e9c3f327edf121e2226d84d3eae5bc8d74d44fa8a44161f6821fc45`.
They supersede the earlier review candidate while remaining unpublished.
Detailed logs/settings receipts remain outside the shareable package.

This evidence-only note records events after the export; it does not rewrite its
manifest or silently rebuild the checked candidate. A first software release,
clean-OS and independent-user acceptance, native maintenance and scientific
validity are not established. Preserve the explicit publication deferral until a
later maintainer instruction changes it.

## Source and history checks

The Git inventory contains 1,173 tracked files at the base. A full local-ref
inventory (`git rev-list --objects --all`) covered 513 reachable commits,
including local branches beyond main. No paths under `data/private/`, `data/raw/`,
`results/`, `.venv/` or `node_modules/` and no credential filenames were found
in that reachable-object path inventory. The data/archive-extension search found
one historical `tests/fixtures/m5-report-only.zip` fixture. Its 17 members contain
source/report/manifest files and an explicit synthetic declaration. Path checks
are a screening tool, not proof that arbitrary JSON or prose contains no private
information. Existing commit-author identities remain part of Git history.

[Gitleaks](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1) **8.30.1**,
using its default rules, scanned all reachable Git history with full redaction,
`--ignore-gitleaks-allow` and `--log-opts='--all --full-history'`.
The official Darwin arm64 archive matched the published SHA-256
`b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5`.
The scanner reported 475 scanned commits and about 24.29 MB of patch content;
its count differs from the complete reachable-commit inventory because Git's
patch traversal does not emit every merge as a separate patch.

All **ten generic-key findings were reviewed**. Nine are 64-character hexadecimal
file-digest entries in scientific execution/verification inventories, including
paths containing `secretion`; one is a categorical `key` string selecting
`gained_in_from_below_70` or `gained_in_from_above_180` in
`experiments/c1/feedback_diagnose.py`. None is a credential. No broad path/rule
exclusion, history rewrite or credential deletion was introduced. The committed candidate source tree was also exported without local environments
or ignored outputs and scanned independently, including archive traversal. Its
ten findings are the same nine digest entries and categorical key, all checked
against the actual source lines. A fresh scan must assess new findings rather
than treating this classification as an allowlist for future content.

Available Actions history was checked before publication: **122 runs** were
inventoried; logs for **118 runs / 852 files** were downloaded to temporary local
storage. Four run-log downloads returned HTTP 404 and are not claimed as inspected. A fully redacted Gitleaks directory scan, including archive traversal,
found **zero secret findings** in about 19.24 MB of available logs. The repository
artifact API returned **zero currently retained artifacts**. Deleted, expired,
inaccessible artifacts/logs and copies outside this repository are outside this
check. Secret scanning does not identify every health record, copyright issue or
confidential statement; the final export is scanned again under its own identity.

## Assets and rights

This preparation concerns a source checkout: original code, adapters, guides,
protocols, metadata, lockfiles and synthetic controls. It does not assemble a
third-party runtime or distribute the ignored local `results/` stores. The
maintainer has explicitly confirmed authority to publish original OpenT1D
material under Apache-2.0, including any employer/client rights. The
[rights inventory](../../publication-rights.json) records that confirmation,
verified upstream notices and exclusions for this source offering.

| Included or referenced material | Observed boundary and remaining decision |
| --- | --- |
| Original OpenT1D code/docs/configuration | Maintainer authority explicitly confirmed for Apache-2.0 publication; preserve contributor copyright and separate upstream terms. |
| Paired/sampling analysis core | Original standard-library algebra with cited source methods; its module explicitly records that no GPL implementation is imported/copied. Synthetic examples are engineering controls. Human-data rights are separate. |
| simglucose and GlucoSim | Pinned upstream source declares MIT; exact notices retained. Two complete native table rows discovered in historical receipt JSONs are now withheld and mapped to privately retained originals. Table-level provenance remains unresolved and those rows are excluded. |
| LT1 Cambridge | Pinned source MIT license verified and retained as LICENSES/LT1.txt. Setup downloads source separately into ignored Node tooling; no bundled runtime clearance. |
| Optional C1 references | Pinned G2P2C/OpenAPS MIT notices verified and retained. Their separately fetched engines/weights are outside the source offering; technical readiness does not establish efficacy/comparator acceptance. |
| Other Python/Node dependencies | Nine uv locks and the committed Node lockfiles identify separate environments. A source lockfile is not a runtime-license inventory or authorization to redistribute every dependency asset. |
| Literature/source metadata and equation implementations | Bibliographic metadata and concise original source summaries retain citations/locators. No full article text, paper figures or clinical dataset is included. The optional GPL isr.deconv source is separately fetched, not copied into the original estimator. |
| Original generated research SVGs | Sixteen figures contain DejaVu Sans glyph outlines; exact Bitstream/DejaVu notice from Matplotlib 3.9.4 is included in LICENSES/DejaVu.txt. |
| Generated reports, checkpoints and private observations | Ignored local outputs are outside this proposed source offering. Review any future public archive byte-for-byte under its own rights and privacy conditions. |

The [P1 rights decision](p1-product-acceptance-review.md) applies only to its
identified internal bundle and recipient. It does not clear this public source,
new recipients, generated studies or a prebuilt runtime. The source-only decision is now separately recorded in
[decision 0072](../decisions/0072-source-publication-rights-and-runtime-scope.md),
using the maintainer's confirmation and the actual exclusions/notices. It does
not clear a prebuilt runtime, restricted observations or a later study archive.

## Dependency and hosted-CI findings

The live Dependabot API returned **230 open alerts** at the base: 29 critical,
119 high, 70 medium and 12 low. Counts include repeated advisories across
manifests and overlapping package-name casing; they are not 230 distinct
vulnerabilities. Packages named are certifi, setuptools, Pillow/pillow, filelock
and urllib3. Pagination was followed for the complete open-alert list.

Two alerts concern root tooling and are addressed by the candidate lock:

| Advisory | Root lock before | Candidate lock | Scope |
| --- | --- | --- | --- |
| [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) | certifi 2026.7.22 | certifi 2026.10.23 | Updated beyond the reported first patched version, 2026.10.19. |
| [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w) | setuptools 84.0.0 | setuptools 84.2.1 | Updated beyond the reported first patched version, 84.1.0. |

Only those two root package entries changed. The other eight uv locks, numerical
implementations and protocols are unchanged. The **228 other base alerts remain
open in preserved historical/native environments**. The complete review groups
them into 50 distinct advisories in
[publication-security.json](../../publication-security.json). All six affected
projects are excluded from public automatic installation. The public snapshot
installer refuses them before installing even the first project, and CI gates
native steps/jobs to explicit private-archive dispatches. The
[security guide](../publication-security.md) explains attack surfaces,
remaining manual-use risk and the requirements for patched successors. This
mitigates exposure; it does not dismiss alerts or declare historical runtimes
safe. Updating a numerical lock still requires a compatible successor and
repeated numerical verification. The proposed first-release
tasks use the standard library and patched root tooling, not those native locks.
GitHub alert closure is not claimed before a merged default-branch rescan.

The [main workflow run](https://github.com/OpenT1D/OpenT1D/actions/runs/40181470506)
shows failure because jobs did not start: GitHub's annotations report an account
billing/spending-limit restriction. A macOS capacity annotation also appears on
one native job. No successful current-main hosted run is established. Resolving
account billing is a maintainer action; changing repository visibility merely
to bypass that problem is not part of this preparation.

## Repository settings and publication actions

Read-only API observations on 25 October:

| Setting | Observed result | Next action |
| --- | --- | --- |
| Visibility/default branch | Private; main at the audited base | Decide publication only after the exact source/content/rights review. |
| About metadata | Empty description/topics/homepage | Suggested description: `Open, modular research tools for reproducible type 1 diabetes experiments.` Topics: `type-1-diabetes`, `research-software`, `simulation`, `reproducible-research`, `python`. Add a homepage only after a real hosted URL is checked. |
| Issues/Discussions | Issues enabled; Discussions disabled | Keep the existing issue forms and check their rendering when publishing. |
| Workflow tokens | Read-only defaults; PR approval disabled | Preserve the least-privilege defaults. |
| Allowed Actions | All; server-side SHA pinning not required | Existing workflows pin their action revisions; review third-party contribution approval when public. |
| Branch protection/rulesets | API HTTP 403: unavailable on the current private plan | Inspect again after the chosen plan/visibility supports it, apply the checked-in policy and verify enforcement. No rule is claimed active. |
| Fork-contributor approval | API HTTP 422 for a private repository | Configure and verify before accepting public fork workflow execution. |
| Private vulnerability reporting | API HTTP 404 | Enable and test on the chosen destination when supported; email ownership and receipt confirmed by maintainer. |
| Dependency alerts | Enabled; open findings inventoried | Root fixes prepared; all 50 distinct advisories inventoried and affected historical automatic routes excluded. Recheck actual public default branch alerts. |

The maintainer supplied a confidential reporting email and authorized its use
in [SECURITY.md](../../SECURITY.md) and the
[code of conduct](../../CODE_OF_CONDUCT.md). Both policies publish that same contact.
The maintainer explicitly confirmed mailbox ownership and message receipt on
25 October 2026. No assistant test message was sent.
Account-level notification delivery, issue/citation-panel rendering, public secret protection,
Pages hosting and enforcement of branch rules remain unverified. The private
repository exclusion in `docs/conf.py` must be removed when public URLs become
accessible, followed by an external-link check. It is retained while private.

## New rights and security verification

The latest candidate adds six targeted security/rights checks plus an installer
integration regression. They cover all affected/unknown project refusals,
missing/corrupt policy rejection, absence of installer calls/output on refusal,
read-only inspection, CI public/private/manual scope, public branch policy,
root versions against all reviewed advisory ranges, notice/source-map hashes and
withheld table rows. The focused 23-test publication/setup/workflow suite passed.
The complete preparation-branch check also passed: **1,406 tests in 510.728
seconds, 13 existing skips**, lint/citation/navigation checks and the clean
Sphinx warning-as-error build. `uv sync --locked` and workflow `actionlint`
passed (the latter without ShellCheck integration). The final exported root
receives its own full repository and MMTT checks; its receipt identifies the exact
result rather than extending an old pass.

No native model implementation, numerical protocol or separate numerical lock
was changed. Shared setup now binds its new policy/helper files in new plans;
old setup plans must be regenerated after this implementation change. Historical
scientific archives retain their original identity requirements.

## Final source-only candidate

The rights/security preparation commit is
`cd45c19a41a4c422ad7565a68fbe183077190c24`. Its independent public root is
`de3d111f856cdd5b73054a1be7ed84e81a748ec6`: 1,193 exported source files plus
`publication-snapshot.json`, one commit, no remotes/tags and no private development
commit objects. The actual standalone bundle was cloned into a fresh receiving
checkout and verified to have the same single root; the private preparation
revision cannot be resolved there. The original GitHub repository was rechecked
and remains private.

On this exact public root, fresh `uv sync --locked` and the full repository check
passed: **1,406 tests in 416.891 seconds, 13 existing skips**, lint, citation,
navigation and the clean Sphinx warning-as-error build. `actionlint` passed on
both workflows without ShellCheck integration. Both complete MMTT examples passed
15 commands and reproduced all 12 report JSON/Markdown files byte-for-byte.
No native numerical environment was installed.

Actual public-root CLI installation attempts for both `m4-study` and
`m4-study-secure` returned the policy refusal before creating installation
outputs or native environments. Even a simulated private/manual CI request in
that snapshot returns `native_enabled=false`. The historical locks and their
228 remaining base alert entries are preserved, not patched or dismissed.

The new-root Gitleaks scan again reported 22 findings: 21 inspected file-digest
entries and the known categorical key, with no credential finding. No allowlist
was added. Tracked files contain no actual personal computer prefix or old
personal commit email, and the JSON content scan found no complete native
parameter row. All 14 privately retained originals match their source-map hashes.
These are bounded technical/content checks, not proof of every possible rights
issue or independent scientific/user acceptance.

The review ZIP, source ZIP, standalone one-commit bundle, checksums, public
verification receipt and next steps are retained under the primary checkout's
ignored `results/publication/20261025/`, with the delivery directory
`public-source-delivery-cleared-de3d111f856c/`. The review wrapper is
`OpenT1D-publication-review-cleared-de3d111f856c.zip`, SHA-256
`024d2e275529ad340b80aa2b87c17c8abc6869b2a789cc4f6a0de8c3b0c81373`.
Detailed logs and original files remain outside the shareable delivery.

This candidate supersedes the earlier `4e9e941d09d2` offering. It is left
unchanged after verification; this later private evidence note does not rebuild
it or change its identity. The source-only rights/security preparation is
complete for the declared exclusions and two-task scope. Actual destination
selection/publication, current-head hosted CI and server-control activation
remain pending. No release version, release date, DOI, native maintenance claim
or independent acceptance is created.

## Documentation consistency follow-up

A subsequent documentation review corrected the maintainer guide's obsolete
branch-protection command and earlier numerical CI job counts. It now selects
the public-source policy and keeps the historical 16-job inventory separate.
The development/contribution/support and direct native guides expose the current
installation boundary before setup commands. The optional BC-003 reference check
is explicitly separate from the standard-library MMTT exercise. The history
record links its later rights/runtime decision without rewriting old evidence.

These are documentation-only updates on the preparation branch. The previously
delivered `de3d111f856c` snapshot remains immutable and does not silently acquire
this follow-up. Its 1,406-test result remains attached to that exact exported
root, not to a newly named artifact. A later export must identify its own source
revision and verification. Historical research reports, Dutch texts, frozen
protocols, numerical code/locks and recorded results are unchanged by this review.

## Earlier local candidate without private Git history

The [public-source guide](../public-source.md) and
[decision 0071](../decisions/0071-public-source-history.md) define an independent
local source export. Twelve historical files had 173 personal computer-prefix
occurrences on 167 lines. Those prefixes are now location placeholders; original
bytes were preserved privately before editing. The public
[source map](../../publication-source-map.json) records original/redacted hashes.
Scientific results and historical hash fields were retained rather than rebased
to the redacted bytes. Old development Git IDs/links remain archive references;
the export does not provide their commits or all matching historical readers.

The source builder creates a new single-commit repository using the maintainer
account's verified GitHub noreply identity, without copying Git metadata or
ignored local files. It refuses dirty source, existing output, personal author
email and submodule contents without a separate review. The actual candidate was exported from private preparation commit
`671f51bafec90e3519ff9bd0b9b519b2076f656c` and has new root
`4e9e941d09d2c1056ea6c6197b3d85ce0b0598bf`. Its tracked source has no personal
computer prefixes or personal author email, and both author/committer use the
verified GitHub noreply identity. The original private commits cannot be resolved
in its object database. A receiving clone of the actual bundle also has one
commit and cannot resolve the private source revision.

On this **new root**, `uv sync --locked` and the full repository check passed:
**1,399 tests in 402.879 seconds, 13 existing skips**, plus lint, citation,
navigation and the clean Sphinx warning-as-error build. Both complete MMTT
examples passed 15 commands and reproduced all 12 original/reconstructed report
files byte-for-byte. Gitleaks scanned the one-commit candidate history; its 22
findings were reviewed as 21 file-hash entries and one categorical key, with no
credential finding. These are technical checks of this exact candidate, not
independent human acceptance or a complete rights/content clearance.

The source ZIP, standalone one-commit Git bundle, SHA-256 files and shareable
verification receipt are retained outside the worktree under the primary
checkout's ignored `results/publication/20261025/`, in
`public-source-delivery-4e9e941d09d2/`. Detailed logs remain in the separate private
`public-root-evidence-4e9e941d09d2/` directory and are not included in the source
export. The public candidate is left unmodified after these checks; later
private evidence notes do not silently rebuild or relabel it. The original private
repository is not rewritten, renamed, deleted or made public.

## Earlier preparation-branch verification

The candidate refreshes the README, support/security/citation status, the
licensing boundary and the maintainer's proposed two-task release exercise.
A fresh root environment installed successfully using `uv sync --locked` with
the two patched tooling dependencies. A local single-branch clone of functional
candidate `126234a551947cce5ffca721b9e116c8e29e0630` into a new directory whose
name contains a space then installed its own new root environment. Both complete
canonical MMTT CLI examples passed: 15 setup/example/import/freeze/check/run/
reconstruction commands, with **12 byte-identical original/rebuilt Markdown and
JSON reports**, including all sampling child reports. This used macOS arm64,
Python 3.12.13 and uv 0.11.16 on an existing developer laptop. No native simulator,
third-party estimator or restricted observations were installed for these tasks.
This is a fresh-environment technical check, not a clean-OS or human-user test.

The local ignored `results/publication/20261025/` retains the receiving checkout
identity, exact commands/exit codes, report hashes, source inventory, all 61
installed root-tooling distributions' license metadata and redacted scan/settings
inventories. These are local evidence, not a published archive or complete
bundled-runtime license clearance.

`uv run --locked python scripts/check.py` passed: **1,395 tests in 381.709
seconds, 13 existing skips**, plus Python/Markdown/YAML checks, citation metadata,
explicit documentation navigation and the clean Sphinx warning-as-error build.
The existing suite includes real local GUI transport, report and process-lifecycle
checks; it is not an independent browser usability session or a new execution of
all separate native scientific campaigns. The final evidence-only documentation
update is checked again for Markdown and a clean documentation build. No
numerical behavior or separate experiment lock changed.

Earlier commit-bound source ZIPs, checksums and receipts are retained locally for
review; the current candidate supersedes them for publication. The receiving studies, audit evidence and final source ZIP are also
preserved under the primary checkout's ignored
`results/publication/20261025/public-release-preparation/`, outside this disposable
worktree. The final receipt records the exact source commit, source archive and
file hashes. This local preservation does not publish or authorize the archive.
Independent human installation/use and actual publication
remain open. The bounded source-only rights decision is recorded above. No version, release date, DOI or scientific result is assigned.
