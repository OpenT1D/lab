# Private installer and publication integration — 28 October 2026

This record concerns `codex/installer-publication-integration` in a separate local
worktree. The maintainer requested local integration and checks only: source
publication remains deferred, with no push, hosted CI/CD, tag, PR or release.
The original main checkout and source branches are not reset or rewritten.

## Inputs and merge resolution

| Input | Exact revision |
| --- | --- |
| Current private remote main at fetch | `3787cc076d8a4850da5e91563c8fa8852a0a3393` |
| OT-058 installer branch | `0fbffbcf3e30d31389efb336406d8c88580f8281` |
| Publication preparation | `c0c2d542e1c86d537409368d83b4fa01902ecd61` |

The installer forked before main's two common-laboratory planning commits.
Integration retains the product requirements, research report (now translated into English), architecture
and OT-059–074 plan while importing the native installer and its bounded Windows
verification. README/roadmap/changelog and navigation conflicts retain both the
implemented internal candidate and the separately planned common core.

Main's decision 0070 remains the laboratory plan; the installer decision is now
[0073](../decisions/0073-native-windows-installer.md), with its former branch-local
number documented. [0074](../decisions/0074-private-installer-publication-integration.md)
records the integration policy. Historical J source revisions, payload hashes,
protocols, native locks, failed attempts and prior acceptance scopes are retained.
Original parameter-row/path copies remain private under the existing source map.

## Cross-route behavior

New setup plans bind both the Windows runtime inventory implementation and the
publication guard/policy. Private packaged runtime inspection still verifies its
manifest and private interpreter without falling back to host installation.
Public snapshot setup refuses excluded native projects before output or installer
calls; a bundled-manifest claim cannot bypass that policy.

The new Windows builder API and CLI refuse public snapshot staging/builds before
source inventory/copying, download, runtime extraction or output creation. Its
manual workflow additionally requires a private repository. This preserves the
source-only offering instead of silently introducing a second public native
installation route. No workflow is executed by local parser/lint checks.

## Verification

The tested integration candidate is `f02d41b45391352e76c7ac4b8fffc76d76b76eb4`. All three
input revisions are ancestors of that candidate. `uv sync --locked` and the full
`uv run --locked python scripts/check.py` passed: **1,560 tests in 392.811
seconds, 32 existing platform/optional-runtime skips**, plus lint, citation,
navigation and a clean Sphinx warning-as-error build. The 48 focused checks passed
first, including three new cross-route regressions. Local `actionlint` passed for
all three workflow files without ShellCheck integration; no workflow executed.

Both complete canonical synthetic MMTT CLI workflows passed 15 commands with
calculation processes using `-B -S`. All 12 JSON/Markdown reports reconstructed
byte-for-byte. No native environment was installed. The generated site contains
290 HTML pages with zero missing targets/fragments in 90,219 local link
instances. External URLs were not rechecked against the intentionally empty
public destination.

A separate local source-only export has one new root and no remotes; none of the
three private input commits is resolvable in its object database. Its actual CLI
refuses Windows staging before output/download and refuses both historical M4
native installation requests before output/installation. This test export stays
local and is not a release or newly approved public offering.

The identity comparison retained **33 frozen protocol JSON files, 10 native/Node
lockfiles and 457 other experiment Python modules byte-for-byte** from the
installer head. Only merged setup/publication behavior and current packet source
links differ among existing experiment Python modules. Five main planning/design
documents are exact, and root `uv.lock` matches publication preparation. All 14
redacted file hashes and privately preserved original hashes match the source
map. Historical scientific hash fields were not rewritten.

Checksum-verified Gitleaks 8.30.1 scanned the tracked export and nested archives
with full redaction. Its 22 findings were individually checked as 21 file digests
and one categorical key; **zero credential findings** and no new allowlist.
The export also contains no actual maintainer computer prefix or old personal
commit email. These checks do not prove every kind of confidential prose or
third-party distribution right cleared.

The private verification receipt, command logs, source/lock identities and exact
report hashes are retained under the main checkout's ignored
`results/integration/20261028/installer-publication-f02d41b45391/`. After the local
checks, read-only GitHub verification confirmed private main still at the input
revision, zero hosted integration runs and an empty `OpenT1D/lab`. No push, PR,
tag or release was made. The later evidence-only documentation update is checked
separately and does not silently relabel the tested candidate or export.

## Remaining boundaries

This task does not close the J dossier's M4/campaign reference-worker deadline
failures, complete Windows maintenance/lifecycle coverage, independent human use,
signing, SmartScreen reputation or VM/TPM restore validation. No fresh Windows VM
run or actual integrated NSIS executable is established by host tests or a
synthetic payload fixture. A newly built executable needs its own hash-bound
verification; the earlier J installer must not be renamed as this integration.

Root tooling retains the preparation branch's certifi/setuptools fixes. Native
locks and Windows build inputs still have separately recorded older dependencies;
this merge does not patch them or dismiss their advisories. The existing
[source-only rights inventory](../../publication-rights.json) does not clear a
bundled installer, its upstream parameter tables or all transitive native assets.
Notices and corresponding sources in the private installer are inputs to that
separate distribution review, not proof that it is complete.

`OpenT1D/lab` was confirmed empty at the start. Hosted source CI and main-branch
protection still await future publication authorization. Existing review ZIPs
remain immutable and describe their earlier source-only candidates; none is an
installer artifact or a substitute for this integration's verification.
