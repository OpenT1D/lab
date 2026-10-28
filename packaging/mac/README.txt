Unsigned internal Apple Silicon MMTT candidate

Build on an Apple Silicon Mac with Apple's Command Line Tools from a clean
committed checkout. Root uv is build tooling only. Network is needed once for
the three hash-pinned upstream archives; a verified cache can then be reused.

  uv sync --locked
  uv run --locked python scripts/build_mac_app.py \
    --output /private/tmp/opent1d-mac-build-UNIQUE \
    --cache /private/tmp/opent1d-mac-runtime-cache

Output must be a fresh directory outside the checkout; existing output is
refused. build-result.json records the exact application bytes, commit and
build ID. Repeating with the same commit, runtime cache and compiler should
produce the same file inventory. This is a directory candidate, not a signed
installer, DMG, public release or clean-host qualification.

Open OpenT1D.app in Finder. The application contains its own real interpreter;
Git, uv, host Python and a terminal PATH are not product prerequisites. Only the
two synthetic MMTT tasks are admitted. Saved analyses and examples are under
~/Library/Application Support/OpenT1D/MMTT. Quit with Exit OpenT1D in the browser
or Quit OpenT1D in the application menu. A second opening reuses the same local
workspace; another application version must wait for the first to exit.

For an isolated maintainer probe, LaunchServices can pass an explicit workspace:
  open -n /private/tmp/opent1d-mac-build-UNIQUE/OpenT1D.app --args \
    --data-dir /private/tmp/opent1d-mac-probe-UNIQUE \
    --state-file /private/tmp/opent1d-mac-probe-state-UNIQUE.json --no-browser

Do not point a probe at user data. Keep old applications for their supported
readers. Moving, replacing or deleting this application does not remove the
separate workspace. No Developer ID or notarisation is used. macOS may reject
an unsigned downloaded copy; a local launch does not establish Gatekeeper
acceptance on another Mac. See decision 0075 for the runtime/capability boundary.

Focused checks:
  uv run --locked python -m unittest tests.test_mac_contract tests.test_mac_packaging
  uv run --locked ruff check experiments/desktop experiments/gui \
    scripts/build_mac_app.py packaging/mac/bootstrap.py tests/test_mac_*.py
