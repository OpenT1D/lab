# Windows installation candidate

OT-058 supplies one offline installer and an OpenT1D shortcut for all current
GUI routes. It includes the required Python runtimes and dependencies. Users do
not obtain a GitHub checkout, install Git, WSL, Ubuntu or Python, manage
packages, or enter terminal commands.

This is an **internal installation candidate** for **Windows 11 on Intel/AMD
x64** with a default web browser. Windows ARM64, 32-bit Windows and Windows
Server are not installer targets. Earlier Repair/Reinstall, upgrade and separate
baseline outcomes retain their stated scopes in the
[verification record](research/ot058-installer-verification.md), including the
original failed upgrade and attempt 09's unresolved M3 result.

Recovery attempt 10 passed a licensed clean installation from a genuine Edge
download of the unchanged, unsigned J candidate. The first automatic browser
launch showed a healthy GUI. Shortcut reuse and normal exit passed. The native
Windows suite ran 124 tests with no failures/errors and six declared skips,
followed by an exact full payload audit. Agent-operated GUI verification completed
a fresh 32-draw Task 1 MMTT analysis and reconstruction with unchanged reports. A separate
sampling-information-loss API workflow also passed, with fresh readers. New
synthetic M3 forecast/comparison runs and saved readers passed. A separate
cancellation retained raw byte copies, with no complete-archive or native
reconstruction claim. Two M3 durable-package export/integrity/reader routes
passed across restart. Separate launcher/session controls passed, including
same-process reopen, access refusal, stale-session recovery and normal stops.
Further agent-operated GUI checks passed an M3 archive export, Task 1 external
archive registration/reader, reversible hiding and normal exit. Separate raw
retention preserved byte copies and complete receipts for two M3 cases; it
establishes neither archive integrity nor reconstruction.
The new campaign and M4 tests failed at their fixed
600-second reference-worker deadlines; candidate source evaluation was not
reached. Those failures remain open, with no model or deadline changes.

The earlier activation approval block was resolved by explicit user permission
and normal Windows activation. Controlled download metadata verified the exact
file hash and genuine ZoneId 3; public SmartScreen reputation remains untested.
Complete workflow/lifecycle coverage, full VM/TPM restore validation and
independent human acceptance remain open. No public signed release is claimed.

GUI, durable/API and launcher-control evidence retains its separate scope.
Eleven-case lifecycle preparation passed within its independently reviewed preparatory scope.
The first maintenance-test attempt failed before launch on its input path. The
second completed graphical installation, payload audit and data preservation,
but its report wrapper failed on an output-filename collision. The overall phase
remains failed. A separate report-only comparison and normal stop passed, with
the full comparison report independently verified. A separate controlled
Uninstall test subsequently cancelled an observed native analysis cleanly. Post-removal checks passed for both retained payloads, all
7,023 original data files and Windows registration/shortcut removal. Eleven fresh
retained-case readers passed with all 22 original report hashes unchanged,
normal exit and a final full payload audit. The original Uninstall05 failure,
earlier controller failures and failed Maintain02 remain preserved. Full
maintenance acceptance remains open. Installation checks
do not establish scientific validity or independent human acceptance.
A separate fresh I-to-J upgrade passed: exact J payload, original-case
preservation, one fresh J reader, 18 native checks without failures/errors/skips
and two normal stops. Its preservation check found 93 of 95 original files
byte-identical and exactly two precomputed verification-bookkeeping changes,
with no added files at that check; both original reports remained identical.
Earlier installation/admission/guard failures remain separate. This closes the
recorded upgrade test, not all workflow, maintenance or release acceptance.

## Integration and public-source boundary

This is the separately verified private J candidate, not a build of the later
combined source. [The integration record](research/installer-publication-integration.md)
retains its exact input revisions and new check scope. A future integrated
installer must be rebuilt and verified under a new identity; J's 18 upgrade
checks do not transfer automatically.

The public source snapshot still offers the two standard-library MMTT tasks.
It refuses bundled native Windows builds before download/staging. The private
checkout builder remains available for internal candidates, and the manual
Windows workflow is private-repository-only. This is a distribution-scope gate,
not a hostile-code sandbox. Known native/build dependency findings, upstream
parameter rights, signing and public distribution remain separate decisions;
see [publication security](publication-security.md). Source publication remains
explicitly deferred, and this integration starts no hosted workflow.

## Included workflows

The installer retains the current GUI's capabilities:

- Synthetic M3 glucose forecast and multiple-candidate comparison: example
  preparation, intake, configuration checks, execution and saved-analysis checks.
- Maintained M4 secretion studies: supplied source models, configuration,
  readiness, execution, reports/figures and reconstruction.
- Repeated maintained experiments: frozen campaigns, cancellation, remaining-slot
  checks, resume and reconstruction.
- Both synthetic MMTT questions: [secretion-change sensitivity](observation-analysis.md)
  and [sampling information loss](mmtt-sampling.md).
- Results library: supported native report readers, downloads and reversible
  hiding/restoration. M5 remains report-only in the GUI.
- Durable archive export, registration, integrity verification and reconstruction
  using a matching trusted reader; raw M3 forensic retention remains distinct
  from complete native evidence.

This scope preserves the existing GUI; it does not promise execution of every
CLI experiment. Examples are invented research inputs, not patient data or
clinical recommendations.

## Install, start and close

1. Obtain the maintainer-provided `OpenT1D-…-windows-x64.exe` and checksum.
   No public download location or release is established yet. Use a candidate
   whose origin the maintainer can verify. This unsigned candidate may prompt
   Windows reputation warnings; do not disable system protection to use it.
2. Open the installer and install for the current Windows user. All components
   are included: installation requires no network download, administrator access
   or system restart.
3. Open **OpenT1D** from the Start menu or desktop shortcut. The interface opens
   in the default browser. Choose a research question and its supplied example.
   Readiness checks verify the included components; no separate environment
   installation is needed. If components are missing or changed, close OpenT1D
   and run the installer again to repair them.
4. Use **Exit OpenT1D** to close the application. Closing only the browser tab
   leaves it running. Opening the shortcut again reuses that instance.

A browser being used for the first time may show its own setup before OpenT1D.
The observed Edge flow allowed account, data-import and personalization steps to
be skipped; no browser account or imported data was required.

During M3/M4 setup checks, **Checking installed components…** means OpenT1D is
verifying its included files. This can take time on slower computers. The
analysis starts after that check and retains its own time limit. You can cancel
either phase. After cancelling a forecast run, use its saved-analysis check to
verify any retained archive before treating its report as checked.

The interface listens on `127.0.0.1` with a random local port. Do not expose it
to other computers or permit inbound remote access. If startup reports another
version is running, exit that version first.

## Saved work, updates and removal

Application versions live under
`%LOCALAPPDATA%\Programs\OpenT1D\versions\<build-id>`. Writable plans, analyses,
reports and journals live in `%LOCALAPPDATA%\OpenT1D\workspace`; durable archive
storage is the separate `%LOCALAPPDATA%\OpenT1D\workspace-archives` folder.
Back up both data folders and the retained readers needed for reconstruction.
Supplied example models are copied into a content-identified workspace directory;
existing user edits are never silently overwritten.

Run a newer installer to update, or the same installer to repair its files.
Installation requests graceful shutdown and waits for owned work to stop. It
refuses to continue if shutdown cannot be established. The incoming runtime
performs this check even when the old runtime needs repair. Repair stages a
fresh complete version, retains the previous same-version directory, then
activates the replacement by rename. Unexpected old files do not survive inside
the repaired version. Retained repair directories can be removed deliberately
after verifying the repaired installation and backups.

Each source/runtime identity gets its own application directory. Updates retain
previous versions and runtimes, with shortcuts under **Start menu → OpenT1D →
Saved readers → build-id**. If an analysis requires an older reader, exit the
current application and open that reader. Do not replace its source files or
delete a version still required by saved analyses. Durable reconstruction
verifies a matching installed reader; exporting source with an archive does not
automatically make that source trusted executable code.

Windows application removal unregisters the main entry and removes its main
shortcuts. It **retains both data folders, version directories and saved-reader
shortcuts**. Removing retained folders is a separate deliberate action after
backing up the analyses and readers. Retained versions occupy disk space; this
candidate has no automatic reader cleanup or migration.

## Build and verify a candidate

These are maintainer steps. End users do not perform them.
[Decision 0073](decisions/0073-native-windows-installer.md) records the selection.

The builder requires clean committed source, a build Python interpreter and
NSIS 3.13. `packaging/windows/runtime-lock.json` pins portable CPython 3.12.15
x64 by SHA-256; `compiler-lock.json` pins NSIS. Three isolated runtimes preserve
the root, secure-native and observation locks. Locked compatible Windows wheels
and pinned pure-Python source builds are assembled without scientific version
resolution. The payload retains dependency licenses and source notices.

```console
uv sync --locked
uv run --locked python scripts/check.py
uv run --locked python scripts/build_windows_installer.py --output results/windows-package
```

Use `--makensis PATH` for a compiler outside `PATH` or `--runtime-archive PATH`
for an already downloaded, hash-matching portable Python archive. Building may
download locked runtime/dependency sources; installation does not. Only tracked
regular source files enter the application. Generated analyses, environments and
private inputs are excluded. `--allow-dirty` is for development experiments;
those outputs are not clean delivery artifacts.

The output includes the executable, its `.sha256`, `build-result.json`, staged
payload and `package-manifest.json`. The manifest records source revision,
source hashes, exact runtime projects/distributions and complete payload hashes.
The build identity binds actual payload bytes so a reused label cannot overwrite
a different reader. Packaging never marks Windows execution as verified.

On an actual Windows host, use the staged or installed private interpreter:

```console
PATH_TO_RUNTIME\python.exe -B PATH_TO_APP\scripts\windows_smoke.py --python PATH_TO_RUNTIME\python.exe --source PATH_TO_APP --output NEW_EVIDENCE_DIRECTORY
```

The harness records its actual platform, runtimes and outcomes in `evidence.json`.
Installed verification removes development tools from worker `PATH`, separates
source and writable data, and exercises GUI routes, original reports,
reconstruction and lifecycle behavior. Source-checkout rehearsals retain their
normal explicit developer setup and must be labeled separately. A partial
rehearsal is not complete package acceptance.

The manually dispatched `Windows installer candidate` workflow builds and
verifies a payload on a Windows hosted runner, including native process tests.
This does not establish graphical installation on a clean Windows 11 machine,
absence of preinstalled development tools, repair/removal or independent use.

## Remaining acceptance

- Complete every included execution/reader route on the current candidate.
  J's focused upgrade and maintenance work does not establish complete scientific
  workflow coverage. I's initial native failure, actual M4 run failure and earlier
  harness failures remain recorded; its clean installation/startup, shortcuts
  and unchanged warm native retry passed only their stated scopes.
- Complete remaining active-work maintenance acceptance. Separate
  controlled active-job cancellation, post-removal preservation/registration
  checks and eleven retained-case readers passed on J; the original failed
  Maintain02 and Uninstall05 phases remain failed. Earlier Repair, Reinstall and
  clean-installation checks retain their own scope in the dossier. The fresh
  I-to-J upgrade closes only its recorded case/preservation/reader/native scope.
- Observe an independent user install, complete the supplied MMTT examples,
  close, reopen and reconstruct. Record assistance, failures and retests
  separately from automated checks; assess the other GUI tasks within their
  existing intended-user scope.
- Decide signing and distribution before public release. No public version,
  release date or code-signing identity is assigned here.

These checks concern delivery and software behavior. They do not establish
model validity or close the separate empirical and intended-researcher gates.
