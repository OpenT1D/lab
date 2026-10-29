# Internal Apple Silicon MMTT candidate

This unsigned internal application offers the two synthetic MMTT tasks:
[paired meal-test sensitivity](observation-analysis.md) and
[reduced measurement schedules](mmtt-sampling.md). It contains its own pinned
CPython 3.12.16 interpreter and reuses the existing standard-library calculations
and report readers. Git, uv, host Python and terminal setup are not product
prerequisites. Other native models, campaigns and archive-library routes are
outside this candidate's capabilities.

This is development software for Apple Silicon, not a supported product release.
There is no Developer ID signature or notarisation. The declared macOS 11.0
binary target is a build constraint; minimum-OS, clean-host, downloaded-copy
Gatekeeper and independent intended-user qualification remain separate. A local
launch does not establish acceptance on another Mac.

## Run a supplied synthetic example

Open the reviewed `OpenT1D.app` in Finder. The native launcher starts the included
interpreter and opens the local interface. Choose **Explore paired meal tests**
or **Explore fewer measurement times**, prepare a supplied example, freeze its
plan and run the analysis. Inspect the reported coverage and assumptions, then
download the saved report. The task guides own the exact interpretation and
complete CLI alternatives.

Reopen the saved entry and check its report reconstruction. These examples use
invented observations and demonstrate software behavior under declared
assumptions; they are not human-data or biological validation.

Quit with **Exit OpenT1D** in the browser or **Quit OpenT1D** in the application
menu. A second opening reuses the same workspace. Another candidate version
must wait for the first to exit.

## Saved work and candidate identity

The default workspace is `~/Library/Application Support/OpenT1D/MMTT`, outside
the application. Moving or deleting the application does not delete that
workspace. The internal relocation/removal/replacement probe uses copies of
one exact candidate; it does not qualify arbitrary future upgrades or readers.

Each build supplies `build-result.json` with its source revision, build ID and
complete file-hash inventory. The bundled manifest records the source closure,
runtime archive hashes, compiler/SDK, architecture, binary deployment targets
and third-party notices. Keep that receipt with the candidate being tested.
No version tag, release version or public binary download is assigned by this
internal build procedure.

## Build and verify an internal candidate

The [maintainer build and probe reference](../packaging/mac/README.txt) owns the
commands, fresh-directory requirements and isolated test workspace. Building
needs an Apple Silicon Mac, Apple's Command Line Tools, locked root tooling and
`zstd` on the build PATH (`zstd --version` must succeed). macOS system tar uses
that executable to read the pinned `.tar.zst` upstream metadata. It is a build
prerequisite only; the application user needs none of these host tools.
The runtime and provider inputs are pinned by hash in
[`packaging/mac/runtime-lock.json`](../packaging/mac/runtime-lock.json).
[Decision 0075](decisions/0075-mac-mmtt-runtime-capabilities.md) owns the runtime
and capability contract; the Windows v1 package contract remains separate.

Qualify the exact committed source: compare two build inventories, run the real
application/browser probe with fresh synthetic data, and execute the unchanged
numerical references with the included interpreter. The probe covers both task
chains, invalid input, cancellation with partial evidence, reconstruction,
relocation and preserved saved bytes. Success also requires authenticated
shutdown, confirmed LaunchServices wait completion and finished diagnostic
cleanup before a success receipt is published. LaunchServices observer status
is not the Cocoa application's OS exit status. A failed or incomplete probe is
not a successful candidate handoff.
