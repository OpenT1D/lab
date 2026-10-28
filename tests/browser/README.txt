Browser development checks (synthetic MMTT only)

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
budget bound the suite. The success paths use 32 explicitly selected synthetic
uncertainty draws. Cancellation uses 1024 and waits for the saved analysis-phase
marker before clicking Cancel; it never changes the calculation or server.

Reports, server logs and success screenshots are under output/playwright/.
Failures retain traces, screenshots and a copy of the synthetic workspace.
Temporary workspaces are removed after each test. The browser cache is only the
explicit PLAYWRIGHT_BROWSERS_PATH; do not point it at private research data.

Playwright 1.64.1 is pinned in package.json and package-lock.json. Version/source:
https://github.com/microsoft/playwright/releases/tag/v1.64.1
https://playwright.dev/docs/test-use-options

These are browser/software regressions, not numerical acceptance, scientific
validity, independent usability, OS qualification or release evidence. Workflow
activation and additional browser/platform coverage are separate work.
