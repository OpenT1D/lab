# Documentation publication

The repository documentation uses one strict Sphinx build for local inspection,
pull-request downloads and the main-branch GitHub Pages site. The CI workflow
defines publication; live deployment and environment settings require separate
platform readbacks. A local build is not a deployment receipt.

## Build and preview

Run `uv sync --locked` and `uv run --locked python scripts/check.py` for the
complete repository check. For a documentation-only iteration, use
`uv run --locked python scripts/check.py --stage docs`. The build replaces
`_build/html`, treats warnings as errors and retains the configured project
subpath handling, search, assets and source downloads.

`uv run --locked python scripts/stage_documentation.py _build/html _build/site`
creates a new publication tree. Its destination must not exist. It copies visible
regular files byte for byte, including `_static` and `_downloads`; it excludes
every path with a dot-prefixed component. It rejects symlinks, multiply linked
files and special files anywhere in the source, including hidden paths, before
creating output. Entry pages and the search index are mandatory. This is a check
of controlled build output, not a filesystem sandbox against a hostile local
process changing files concurrently.

On a successful pull-request root check, download the `docs-pr-...` artifact from
that run. Extract it and serve the directory over local HTTP to inspect navigation,
search and downloads. The HTML artifact expires after one day. Pull requests
cannot publish Pages and receive no Pages or identity-token write permission.
All PR HTML is untrusted contributor content; inspect it in that context.

## Publish reviewed main

Only a `push` to `refs/heads/main` in `OpenT1D/lab` uploads a Pages artifact. The
artifact name includes its run ID and attempt. The deployment job waits for the
same run's complete `Repository checks` gate: root checks, the three-host smoke
matrix and Linux Chromium flows must all succeed. A failed, cancelled or skipped
family prevents deployment. The deployment job is not a dependency of that gate.

Pull requests also require the read-only [dependency review](publication-security.md).
On main pushes, that PR-only job is explicitly skipped; the aggregate validates
that event-specific result while requiring the root, matrix and browser results
to succeed.

The deploy condition uses `always() && !cancelled()` to evaluate those guards after
the event-specific ancestor skip while honoring manual workflow cancellation,
including cancellation after aggregate success. It still requires that success
and the exact trusted main push. GitHub otherwise applies an implicit status check, and skipped
jobs can skip later jobs in the [dependency chain](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds).
The [28 October main run](https://github.com/OpenT1D/lab/actions/runs/40784585671)
uploaded its checked Pages artifact and passed the aggregate, but skipped
publication after the PR-only dependency job was skipped. Corrected main
deployment requires a subsequent successful hosted publication receipt.
GitHub [re-evaluates job conditions on cancellation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-cancellation);
`always()` alone would keep a matching deployment job running.

Only the deployment job grants `pages: write` and `id-token: write`, and it does
not check out or execute repository code. The `github-pages` environment must have
an exact `main` branch deployment policy and Pages must use the workflow build
type. Both are platform settings to verify, not properties established by this
document. Active main runs and deployments are not cancelled; superseded pending
runs may be replaced. Superseded PR runs may also be cancelled while active.
Concurrency does not guarantee dispatch order. Manual dispatch runs checks but
does not publish the site.

The Pages upload composite Action contains a pinned `upload-artifact` dependency.
[action-dependencies.json](../.github/action-dependencies.json) records that exact
edge. The selected-Action policy includes direct and transitive revisions,
without publisher wildcards. The upload Action's tar step dereferences links, so
the explicit staging check is required before both artifact routes. See the
[pinned composite source](https://github.com/actions/upload-pages-artifact/blob/fc324d3547104276b827a68afc52ff2a11cc49c9/action.yml).

The Pages artifact expires after one day; compact synthetic check diagnostics
expire after five days. Expiration of build artifacts does not remove the
deployed site. Failed checks retain their diagnostics and leave the previously
deployed site in place. To repair a bad publication, review and merge a corrective
PR through the same checks; do not publish arbitrary local HTML or reuse an
artifact from a different run.

## Acceptance evidence

Before declaring publication operational, inspect an actual PR HTML artifact,
confirm the deploy job is skipped on that PR, then verify successful integrated
main checks and deployment. Read back the environment branch rule and Pages
build type. Check the returned site URL, the `/lab/` entry redirect, a documentation
page, search, an asset and a byte-exact notebook download using the deployed site.
Only then set the repository homepage to the verified URL. Publication does not
establish usability, biological validity or a packaged software release.
