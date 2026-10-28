# 0073 — Native Windows installer with private runtimes

Date: 22 October 2026

Status: selected for OT-058 implementation; Windows execution and independent
user acceptance remain separate verification steps.

The installer branch originally used local decision number 0070. Integration on
28 October 2026 assigns 0073 to avoid colliding with the common-laboratory
planning decision already on main. Historical installer commits and package
inventories retain the original path/bytes and their recorded identities.

## Context

OT-058 requires one graphical Windows installation and a launch shortcut,
without user-managed GitHub, WSL, Python or terminal setup. The first installer
must expose all existing GUI routes. The native simulation and observation
runtimes have different locked NumPy/SciPy versions. Source snapshots, exact
runtime identities and fresh `-m` and `-S` interpreter invocations are part of
existing reconstruction contracts. The GUI and scientific runners previously
relied on Unix file locks, process groups, signals and interpreter paths.

## Decision

Build a per-user Windows 11 x64 installer with NSIS. Bundle three isolated
CPython 3.12.15 installations from the hash-pinned python-build-standalone
20261021 release: root tooling, secure native simulation and the M4 observation
runtime. Resolve dependencies from the existing locks without changing their
scientific versions. Use compatible locked Windows wheels, building only the
four pure-Python sources with pinned build backends. Include licenses and
corresponding source material. Installation is offline and needs no system
Python, Git, administrator access or restart.

Preserve ordinary Python interpreter semantics and real source files. A fixed
source-only `.pth` makes the installed application importable during normal
startup; controlled working directories preserve stdlib-only `-S` readers.
Launch with environment and user-site isolation. Do not use `._pth`: its
`import site` behavior would change the existing `-S` reconstruction boundary.
Keep the loopback browser interface, all existing GUI capabilities and M5's
existing report-only boundary. This does not advertise every CLI experiment.

Record immutable source and runtime inventories in the package manifest.
Installed readiness verifies these components offline; repair directs the user
back to the installer. Checkout setup retains its existing explicit `uv` route.
Runtime admission reuses the existing safe directory-handle inventory so each
file is hashed through a checked traversal without repeatedly reopening every
absolute ancestor. Windows ancestor handles prevent directory replacement;
file identity and mutation checks, exact file sets, complete hashes and locked
metadata checks remain mandatory on every admission. No result is cached across
checks. The inventory retains its existing 900-second internal budget. Source
identities include the inventory dependency. This refinement follows the actual
candidate-C Windows readiness failures recorded in the verification dossier.
Maintained M4 worker imports do not eagerly discover transitive source ancestry.
Explicit provenance checks start from the original inherited source roots and
perform one complete walk, examining each candidate once within that walk.
Each later check performs fresh discovery; added, removed or changed local
imports remain observable. Capturing the original roots function prevents the
process-local successor adapter from recursing through its replaced public
entrypoint. This changes preparation work, without changing scientific code,
source inclusion or the historical coordinator and worker deadlines.
Within one regular-file open, evaluate link policy and pathname identity from
one fresh pathname snapshot, then take the checked descriptor snapshot last.
Windows inventory readers reuse that same-open descriptor snapshot instead of
immediately querying it again. Keep the post-read descriptor check and a fresh
final reopen with descriptor ChangeTime, together with hashes, directory pins
and all operation boundaries. No file metadata is reused across opens or checks.
Reuse only the lazy process-local Win32 DLL/function/type bindings. Every open
still creates its own file or directory handle and attribute buffer, and every
admission recomputes file metadata and hashes. The binding cache retains no file
state, success result or handle. Concurrent cold calls may initialize separate
binding tuples; thread-local ctypes error values and handle ownership remain
independent. This avoids repeated binding construction without weakening the
filesystem checks.

Installed M3/M4 workflow commands separate passive preparation, complete
installation integrity and native execution. The pre-installer M4 readiness
ceiling covered metadata work; adding a 753 MB full inventory made that old
30-second envelope unsuitable. A fresh owned worker now audits each required
runtime with its existing 900-second inventory and 30-second metadata ceiling.
Passive preparation retains 120 seconds for M3 and 30 seconds for M4. Native
execution and reconstruction keep their original independent allowances; unused
audit time cannot extend them. The outer coordinator publishes the sum of these
ceilings plus bounded startup and cleanup. Checkout commands retain their
original path and allowances.

One live owner latches cancellation across every transition. Audit results are
fresh, typed, tied to the current source/manifest and usable only once within
that owner. There is no saved admission receipt, skipped audit or cached file
result. Each child has at most 30 seconds of cleanup; the intermediate M3 owner
allows 40 seconds and the GUI allows 60 seconds for these packaged operations,
including shutdown. A cancelled packaged M3 run retains its archive without
starting another audit/reader; a later explicit saved-analysis check can verify
it. Display-only phase records say when configuration, included components or
analysis are being checked; they never grant readiness or change deadlines.
The phase owner/worker and workflow dispatch sources enter existing M3/M4 source
inventories through a lightweight filename list, without importing a new
coordinator into predictor processes.

Separate writable analyses and durable archives from application versions.
Retain old versions and runtimes with saved-reader shortcuts across update and
removal. Installed durable reconstruction uses a matching, independently
retained installed reader with verified source/runtime identity; an archive's
bundled source is never automatically trusted. Checkout readers still require
the original clean Git verification.
Resolve the GUI's selected installed revision as metadata, matching checkout
`git rev-parse`; this lookup grants no trust. Both durable operations verify
the selected source and runtime in their core before use and again before
publication. Interpreter selection returns the path from its own complete
identity check without immediately repeating the same runtime scan. Export
retains its separate source-copy check. No identity result is reused across
these boundaries or across operations.

Use Windows Job Objects to own workers and descendants. A trusted bootstrap
waits for Job assignment before executing an analysis, then receives cooperative
interruption over a private control pipe. Bounded cleanup terminates any
remaining owned descendants. Redirected Windows workers use `DETACHED_PROCESS`
to avoid an unnecessary console host; Job admission and cleanup stay unchanged.
Bind `PeekNamedPipe` before START admission and before creating the control
watcher. The gate and watcher are sequential consumers of the same private pipe;
read only available bytes and wait briefly when it is empty. This avoids leaving
a blocking stdin read pending during NumPy DLL initialization, a pattern also
reported in [NumPy issue 24290](https://github.com/numpy/numpy/issues/24290).
Do not assume `PeekNamedPipe` is universally nonblocking: Microsoft documents
[blocking with synchronous handles in multithreaded applications](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe).
Keep START, bounded command framing, CANCEL, EOF and Job cleanup semantics;
unexpected pipe errors interrupt work instead of silently losing cancellation.
Keep the locked numerical runtimes and existing worker deadlines.
Preserve POSIX process ownership. Windows regular file access rejects reparse
points and compares mutation timestamps through file handles, avoiding CPython
3.12's different path/handle meanings for `st_ctime`. Workspace locks are live
OS locks.
Publish Windows status and GUI administration files through a shared
`SetFileInformationByHandle` / `FileRenameInfoEx` primitive with replacement and
POSIX semantics. Existing readers keep the previous file; subsequent readers
open the complete new file. Validate ordinary files, retain ownership of the
pending handle and pin directory ancestors. Admission phase records retain their
additional identity and bounded-content checks. Failures remain failures;
publication does not retry, copy over an open destination or extend any clock.
GUI administration uses a fresh unique pending name so an earlier crash's
unowned temporary file neither blocks persistence nor gets overwritten. Native
text writers retain their fixed pending names because interrupted archive
validators explicitly recognize them; native attempts use fresh output folders.
Preserve native text encoding/newlines and the existing Unix publication path.
Record the shared helper in the affected explicit source inventories; historical
archives retain their original readers. This follows the separately preserved
F phase failure and G comparison-state failure and their fresh-file Windows
reproductions, not a change to scientific behavior.
Installer/launcher admission shares a mutex. Incoming maintenance code requests
authenticated shutdown even when the old runtime needs repair; saved PIDs do
not grant termination authority. Read historical Windows paths as Windows paths
when reconstructing on another host. Use extended-length Windows data/archive
roots so deep campaign paths do not require a registry change. Canonical report
text uses UTF-8 with LF on both platforms.

## Alternatives and consequences

- PyInstaller replaces `sys.executable` with its bootloader. Preserving the
  current worker, source and stdlib-reader contracts would require additional
  adaptation; portable CPython directly supplies them.
- A CPython embeddable package with `._pth` was prototyped for the two MMTT
  workflows. The full GUI needs separate locked scientific runtimes and genuine
  `-S` behavior, so that prototype is not the delivery architecture.
- Managed WSL adds distribution, virtualization and restart dependencies. It
  remains an interim technical route, not the selected product entrypoint.
- Browser-only or hosted execution would change the analysis and data boundary.
- NSIS can compile on macOS/Linux, but compilation does not test the Windows
  kernel, installation, process cleanup or independent use. Three runtimes and
  retained readers increase disk usage; this candidate does not delete old
  readers automatically.

Verify every existing GUI execution/reader route, exact reconstruction,
cancellation, resume, restart, repair/update/removal and installation without
development tools. Keep local rehearsals, Windows execution and human acceptance
distinct. This changes delivery and portability, not scientific conventions.

## Sources

- [python-build-standalone distribution archives](https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html)
- [Pinned portable CPython release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021)
- [CPython command-line isolation and site options](https://docs.python.org/3.12/using/cmdline.html)
- [CPython Windows isolated path configuration](https://docs.python.org/3.12/using/windows.html#finding-modules)
- [PyInstaller executable semantics](https://pyinstaller.org/en/stable/runtime-information.html#using-sys-executable-and-sys-argv-0)
- [NSIS compiler platforms](https://nsis.sourceforge.io/Docs/Chapter2.html)
- [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Windows file and reparse-point access](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)

- [Windows rename information and filename buffer](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)
- [Windows replacement flags and existing handles](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information)
