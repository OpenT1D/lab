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

## Browser regression checks

The required Linux browser matrix runs Chromium, Firefox and WebKit. Each job independently builds and stages documentation
from the same checked-out source using the commands above. It serves that tree
under `/lab/`, matching the published project path. It checks every generated
HTML page, including the entry redirect and search. This verifies the source
and staging procedure; it does not consume the root job's uploaded artifact or
establish that GitHub Pages has deployed it.

With the locked browser tooling installed as described in the
[development guide](development.md), run:

```sh
npm --prefix tests/browser run install:browser -- chromium firefox webkit
uv run --locked python scripts/check.py --stage docs
uv run --locked python scripts/stage_documentation.py _build/html _build/documentation-preview/lab
npm --prefix tests/browser run test:docs
```

The staging destination must not already exist. Remove an earlier
`_build/documentation-preview` before restaging. The test runner owns its loopback
HTTP server on port 8766 and refuses to reuse another server.

Listeners are attached before navigation so errors during the entry redirect
are retained. HTTP errors, failed requests, console errors and JavaScript
exceptions fail the check. Images must decode and Mermaid must render to SVG.
Declared assets and downloads are requested explicitly, including the favicon
in the entry HTML before its redirect. Each captured HTML document must declare
an icon, so removing the entry's icon link also fails. Every staged non-HTML file is checked
over HTTP against its original bytes. Search must finish and open a result;
the diagram must render again after a theme change. Synthetic fault pages test
that missing assets and browser errors are actually rejected.

Firefox can cancel the entry page's favicon request while following its immediate
meta refresh. That exact `NS_BINDING_ABORTED` is accepted only for a main-frame
image declared as the favicon in both documents. The same-origin source and
final document must both load successfully, and the final document must naturally
request and completely load the same icon with HTTP 200 before any test probes.
Its explicit asset check must also return 200, and the bytes of that completed
browser response must decode as an image. A later successful GET cannot substitute
for failed or corrupt browser data.

The original failed request and its narrowly classified recovery remain in the
JSON receipt. Other cancellations, HTTP errors, missing declarations, incomplete
loads and decoding failures still fail. The suite does not retry or reload a
page to obtain recovery evidence. Native Firefox redirect regressions are
Firefox-specific; those fixtures are intentionally skipped in the other engine
projects. Every generated documentation page is still checked in all three.

Each CI engine uses four workers, no retries and a five-minute documentation
budget. The matrix uses `fail-fast: false`, so one failing engine does not cancel
the others' diagnostics. All three results must succeed for the required gate.
The four MMTT application flows run only in the Chromium job. Local `test:docs`
runs all three engines within a fifteen-minute total budget; select one with
`npm --prefix tests/browser run test:docs -- --project firefox --global-timeout=300000`.
The installer keeps Chromium as its default; explicit browser names select the
requested engines. On Linux, add `--with-deps` before those names when needed.

The pinned Mermaid module still requires jsDelivr access; a failed CDN load
fails the browser check. Logs, per-page JSON receipts and failure screenshots
and traces are retained in separate `browser-<engine>-...` artifacts for five
days. Per-page receipts record the actual engine name and version. The browser
matrix remains a dependency of `Repository checks`, so a failure also prevents
main publication. These checks cover Playwright's engine builds on Ubuntu 24.04;
live-site acceptance, other operating systems and installed browser/release
qualification remain separate.

## Publish reviewed main

Only a `push` to `refs/heads/main` in `OpenT1D/lab` uploads a Pages artifact. The
artifact name includes its run ID and attempt. The deployment job waits for the
same run's complete `Repository checks` gate: root checks, the three-host smoke
matrix, Chromium MMTT flows and all three documentation engines must succeed. A failed, cancelled or skipped
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
publication was subsequently observed in the
[corrected main run](https://github.com/OpenT1D/lab/actions/runs/40789265528)
on `1714f06`; the deploy job actually ran and succeeded. The later integrated
receipt is recorded below.
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

On 29 October 2026, the [integrated-main run](https://github.com/OpenT1D/lab/actions/runs/40792457095)
checked clean source `45fd3aa4866f74862717e8a51c77b867f2b0a42f`. Root checks ran
1,700 tests with 33 expected skips; all three host smokes, four Chromium flows
and the aggregate succeeded. The PR-only dependency job was skipped as intended.
The successful `Publish documentation` job consumed
`github-pages-40792457095-1` from that same run and attempt, and deployment
`7400643365` reported success for the exact main revision.

The live [site](https://opent1d.github.io/lab/) passed a separate Chromium check:
the missing-slash redirect and documentation entry, navigation to the Mac guide,
finished search, assets and byte-exact Mac build-reference/runtime-lock and MMTT
notebook downloads. All 43 observed project responses succeeded with no page
errors or failed requests. These are dated acceptance observations; subsequent
changes require their own run and deployment receipts.
