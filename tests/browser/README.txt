Browser development checks (checkout/installed synthetic MMTT and built documentation)

Run from the repository root with Node 24 and the locked Python 3.12 root
environment. No native simulation environment is installed by this suite.

  uv sync --locked
  export PLAYWRIGHT_BROWSERS_PATH="${TMPDIR:-/tmp}/opent1d-playwright-browsers"
  npm --prefix tests/browser ci --ignore-scripts --no-audit --no-fund
  npm --prefix tests/browser run install:browser
  npm --prefix tests/browser test

Linux browser dependencies, when required by the host:

  npm --prefix tests/browser run install:browser -- --with-deps

OPENT1D_BROWSER_PYTHON can select an existing root interpreter; otherwise the
suite uses .venv/bin/python (Windows: .venv/Scripts/python.exe). The test launcher
uses the real Service, HTTP transport, frontend and command workers with a
unique temporary workspace per test. It restarts that server to reopen saved
reports. There is no substituted backend or intercepted application response.

One Chromium worker, no retries, 90 seconds per test and a five-minute global
budget bound the MMTT suite. The success paths use 32 explicitly selected synthetic
uncertainty draws. Cancellation uses 1024 and waits for the saved analysis-phase
marker before clicking Cancel; it never changes the calculation or server.

The additional installed-sampling test builds a source/data wheel, installs it
noneditably in a disposable CPython 3.12 environment and launches its actual GUI
from an unrelated directory. It retains the supplied 128 draws, reads/downloads
native child reports, checks desktop/narrow views, relocates/restarts without the
original project path and proves nested-tampering withdrawal. It uses no native
simulator, substituted response or checkout GUI. Its build receipt and screenshots
are retained with the other Chromium diagnostics. Development runs allow a dirty
source fixture; formal candidate receipts still require a clean source build.

Three installed workbench flows reuse installed-fixtures.mjs and cover own
synthetic files, exact CSV BOM/CRLF retention, invalid-input correction, autosave
focus, restart, immutable parent derivation, cross-tab conflict/restore, large
raw integer seeds, explicit sampling development separation, keyboard labels
and narrow/200-percent-text reflow. Their analysis plan explicitly uses32 draws;
the supplied installed-sampling control above still uses128. Eight application
flows share the same five-minute budget. These are bounded software/accessibility
observations, not formal screen-reader or independent usability qualification.

Reports, server logs and success screenshots are under output/playwright/.
Failures retain traces, screenshots and a copy of the synthetic workspace.
Temporary workspaces are removed after each test. The browser cache is only the
explicit PLAYWRIGHT_BROWSERS_PATH; do not point it at private research data.

The separate documentation suite reuses the same pinned tools. Build and stage
the HTML under the published project path before running it:

  uv run --locked python scripts/check.py --stage docs
  uv run --locked python scripts/stage_documentation.py _build/html _build/documentation-preview/lab
  npm --prefix tests/browser run install:browser -- chromium firefox webkit
  npm --prefix tests/browser run test:docs

Remove a previous _build/documentation-preview before restaging. The destination
must be fresh. The runner owns a loopback HTTP server on port 8766. It audits all
generated HTML pages, initial redirect icons, image/Mermaid rendering, declared
assets and downloads, and checks all staged non-HTML bytes. It also exercises
search and dark mode and proves rejection with synthetic fault pages. Mermaid's
pinned jsDelivr module requires network access; load failures fail the check.

The search check lets the entry page finish before submitting the query, then
waits for the finished heading and completed summary requests before opening a
result. The strict monitor remains active across those waits and the navigation.
Delayed-response fixtures verify that real HTTP, request,
console and JavaScript errors remain fatal; the test does not discard errors.

Documentation runs all three Playwright engines with four workers, no retries,
45 seconds per test and a fifteen-minute local total budget. Select one engine:

  npm --prefix tests/browser run test:docs -- --project firefox --global-timeout=300000

CI runs one required matrix job per engine with a five-minute documentation
budget, fail-fast disabled and distinct browser-<engine>-... diagnostic artifacts.
All three must pass the public gate. Only Chromium runs the MMTT application
flows. The installer defaults to Chromium; explicit names select engines. Linux
hosts can include --with-deps before the names.

Per-page JSON receipts record the actual engine/version. Results and failure
screenshots/traces are under output/playwright/documentation, preserving the
MMTT diagnostics. CI retains both suites' diagnostics including failures.

The redirect audit accepts only Firefox's exact NS_BINDING_ABORTED for an
obsolete main-frame favicon during a matching immediate same-origin meta refresh.
Both documents must declare the same icon. A later natural browser image request
must have completed with HTTP 200 before probes, its actual response bytes must
decode, and the explicit asset probe must succeed. Raw failures and classified
recoveries remain recorded. Other request, asset and decode failures stay fatal;
there is no page retry. Native Firefox-only fixtures are intentionally skipped
in Chromium/WebKit; the complete page audit still runs in every engine.

Playwright 1.64.1 is pinned in package.json and package-lock.json. Version/source:
https://github.com/microsoft/playwright/releases/tag/v1.64.1
https://playwright.dev/docs/test-use-options

These are browser/software regressions, not numerical acceptance, scientific
validity, independent usability, OS qualification or release evidence. Workflow
activation and additional operating-system/installed-browser coverage are separate work.
