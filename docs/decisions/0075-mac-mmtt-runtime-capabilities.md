# 0075 — A bounded Mac MMTT runtime and application profile

Date: 28 October 2026

Status: accepted for an unsigned internal Apple Silicon candidate. Public
distribution, signing, notarisation, clean-host qualification and independent
user acceptance remain separate work.

## Context

The first Mac probe consumes only the two standard-library synthetic MMTT tasks.
Workers execute `sys.executable -m ...`, so a bootloader is not interchangeable
with a real CPython interpreter. The existing Windows-v1 package descriptor
requires installed distributions and private numerical runtimes. It must keep
its existing meaning.

## Decision

Add `opent1d.desktop-package/2` with an explicit capabilities-v2 declaration for
exactly `mmtt-sensitivity` and `mmtt-sampling`, Darwin ARM64 and a declared macOS
11.0 deployment target. Only this bounded contract allows an empty installed
distribution inventory. Its runtime selector identifies the pinned standalone
CPython archive rather than claiming the development dependencies are installed.
Continue to read and verify Windows-v1 descriptors under their original rules.

Use the official Astral python-build-standalone CPython 3.12.16 ARM64 release
archive from 20261026, verified against its published SHA-256. Retain upstream
build metadata, provider source and license texts. Inspect the delivered Mach-O
architecture, minimum-OS load commands and dylib dependencies. The deployment
target is a build declaration; it does not establish testing on every newer OS.

The builder stages regular runtime files, omits the exact upstream command-alias
links, and removes pip/ensurepip and regenerable bytecode. General archive,
source and runtime link/hardlink rejection remains strict. No host interpreter,
root development packages or historical native environments enter the runtime.
Record the source commit, selected source bytes, toolchain, upstream archives,
transformation and complete delivered payload identity.

A thin native Cocoa launcher starts that interpreter and surfaces startup
failures. No Developer ID, signing identity, paid service, notarisation or public
release is selected. Retain any linker/upstream ad-hoc code-signature metadata
as observed; it is not a trusted Developer ID signature.

The server admits only the two task APIs, their owned job inspection/cancellation
and authenticated desktop shutdown. The interface exposes the same two tasks;
hidden buttons alone are not capability enforcement. Other task controllers and
native example seeding are excluded from this application profile.

Keep writable work under `~/Library/Application Support/OpenT1D/MMTT`, or an
explicit separate test workspace. Replacing, moving or removing an application
must not modify that data. Verify old-result access for the exact supported
reader/source/runtime combination; preserve old applications when their readers
are needed. Do not promise arbitrary future reader compatibility.

## Alternatives and consequences

A frozen Python bootloader would require adapting the current worker protocol.
A full Windows-style dependency bundle would widen runtime and rights scope
without serving these two tasks. A capability-specific manifest preserves the
shared calculations and HTTP lifecycle while keeping those routes unavailable.

The candidate still needs actual launch, two-task execution/reconstruction,
interruption, double-launch, shutdown and data-preservation checks. An unsigned
local probe does not establish a trusted downloadable application or Gatekeeper
acceptance on a clean machine. A future release needs a separate reviewed
distribution and update/signing boundary.

## Sources

- [Pinned upstream release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261026)
- [Distribution archive metadata](https://gregoryszorc.com/docs/python-build-standalone/main/distributions.html)
- [Upstream runtime and licensing notes](https://docs.astral.sh/python-build-standalone/running/)
- [CPython isolation and module execution](https://docs.python.org/3.12/using/cmdline.html)
