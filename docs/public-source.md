# Prepare a public source history

OpenT1D's source-publication candidate is prepared separately from its private
Git development archive. This guide owns that boundary; the
[maintainer checklist](maintenance.md) owns publication and release decisions.
The maintainer selected [OpenT1D/lab](https://github.com/OpenT1D/lab) as the new
public repository on 25 October 2026. The separate `OpenT1D/OpenT1D` development
repository remains private. The command below prepares an export locally;
repository creation, push and verified server controls are recorded separately.

## Current publication decision

The maintainer explicitly requested **preparation only** on 25 October 2026.
`OpenT1D/lab` exists as an empty public destination with preparation metadata and
security settings. No source branch, commit, version tag or release has been
published there. Keep the prepared source local until the maintainer explicitly
authorizes publication after the remaining first-version work.

The current local review scope is described in the
[28 October review](research/publication-preparation.md#source-review-28-october-2026).
Each export records its exact source and file hashes in `publication-snapshot.json`;
its independent Git root and verification receipt identify the receiving copy.
Do not push a private development branch or infer source-publication permission
from the existence of the empty destination.

The later [private installer integration](research/installer-publication-integration.md)
preserves this deferral and source-only boundary. Its native Windows builder
is available for private internal candidates, but is blocked in a public source
snapshot pending a separate distribution decision. Earlier ZIPs remain frozen
and do not silently acquire installer changes or a new verification claim.

## What the candidate contains

The export contains only the reviewed commit's tracked files. It starts a new
Git repository with one root commit, the maintainer's public name and GitHub
`noreply` email. It has no remote, tags, old commits, pull-request refs, Git
alternates or copied development configuration. Ignored results, environments,
private data and Actions logs are outside the export.

The original development repository and its history remain private. Do not push
its branches/tags into the public repository, merge that history into the new
root or use a mirror push. Future public work must descend from the public root.
A file named `publication-snapshot.json` records the source revision and hashes
of the exported files, without copying that source revision's Git object. Its
publication flag describes export-time state; later publication does not rewrite
that initial manifest or its verified commit.

## Personal information and historical evidence

The chosen project name, author attribution, GitHub account and confidential
reporting address remain intentional public information. Personal computer paths
in twelve historical records were replaced with `WORKTREES/`, `REPOSITORY` or
`USER_HOME`. These are location placeholders, not executable paths or commands.

[publication-source-map.json](../publication-source-map.json) records each
changed file's private-original and redacted hashes and the replacement counts.
Two additional historical receipts withhold complete upstream native parameter
rows whose separate table provenance remains unresolved. Their fragment hashes
remain; no replacement values are supplied. The source map now covers fourteen
files: twelve path-redacted records and two parameter-redacted receipts.
Original bytes are retained in the private archive. The displayed records are
redacted historical copies: they are not new executions or byte-identical
original receipts. Numerical results, units, numerical source, frozen protocols and
historical hash fields were not rewritten to make them appear to match the
redacted files. The two archived `.source.txt` probe files also have new file
identities; they are historical source records, not current model code.

Old development commit IDs and GitHub commit/PR/Actions links in research records
identify the private archive. They are not commits in the new public history and
may be inaccessible to public readers. Upstream model/method source references
retain their original identities and attribution. Do not relabel old checks as
runs on the new public root. Reconstruction that requires original historical
source bytes needs the matching trusted private reader/archive; this snapshot
alone does not establish access to every old experiment. New executions freeze
the source bytes actually used.

The initial candidate scope remains the two synthetic standard-library MMTT
workflows. Independent user acceptance, broader historical-reader compatibility,
and broader release acceptance retain their own gates. The maintainer confirmed
original-material authority and mailbox receipt; the
[licensing inventory](licensing.md) records the source-only clearance. The
[security policy](publication-security.md) records all current advisory
dispositions and enforces the bounded automatic-installation/CI scope.

## Prepare locally

Commit and review the private preparation branch first. Choose a new directory
outside that checkout and the maintainer's verified GitHub noreply address:

```sh
uv run --locked python scripts/prepare_public_snapshot.py \
  --output /tmp/opent1d-public-source-candidate \
  --author-name 'Matthias van der Galiën' \
  --author-email '156520680+matthias-van-der-galien@users.noreply.github.com'
```

The builder refuses uncommitted/untracked changes, an existing output directory,
a personal commit email and an unreviewed submodule export. It does not delete or
rewrite the private repository. It uses a tracked-file export rather than a Git
clone, then creates and checks the new history. Inspect failures in the receiving
directory; the tool never overwrites an existing candidate.

Before approving publication:

1. Check `git rev-list --all --count` returns `1`, `git remote -v` is empty and
   the commit author/committer use the selected noreply address. Confirm the
   original private commit cannot be opened with `git cat-file` in this repo.
2. Inspect the source-map entries and repeat secret, personal-path and email
   checks on the exported files and their new history. Automated scanning does
   not clear rights or identify every kind of confidential prose.
3. Run `uv sync --locked` and `uv run --locked python scripts/check.py` in the
   candidate. Execute both canonical MMTT examples and reconstruct their reports.
   Identify these results separately from the historical development checks.
4. Follow the [platform activation steps](publication-security.md#activate-on-the-selected-public-destination). Verify the selected `OpenT1D/lab` destination, links, About metadata,
   reporting contact, security settings and branch controls. A future destination
   URL or website is not assumed to exist by this local preparation.

Git user configuration is local and is not inherited by clones. Set the chosen
`user.name` and GitHub noreply `user.email` in each maintainer checkout before
committing to the public history.

Only after review should the single public branch be connected to the chosen
repository. No public push, old-repository rename/deletion, history rewrite or
visibility change is authorized by this local preparation tool.
