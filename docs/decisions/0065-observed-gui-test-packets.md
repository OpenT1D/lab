# 0065 — Bound GUI test packets and a conditional Windows/WSL entry

Date: 11 October 2026

Status: accepted for the scoped OT-045–049 technical preparation.

## Context

A first tester will use their own Windows computer. The current GUI and M4
workers depend on Unix file locks, signals and owned process groups. Installing
Windows Python does not preserve those lifecycle guarantees. The existing local
study packet also requires manual setup, archive registration and JSON editing.

## Decision

Add a separate `experiments.usability` entry around the unchanged GUI, setup
tools and authoritative M4 reader. Freeze a clean source checkout in a Git
bundle, retain complete and genuinely interrupted synthetic archives, reconstruct
both before packaging, and bind their bytes, reports and reader revision in a
manifest. Never execute an archive's saved Python. The manifest detects changed
bytes; it is not a signature or an independent rights decision.

Provide one session entry page, participant goals and a separate moderator page.
Keep public guides canonical and English; a generated private Dutch packet can
use the same task identities. A bounded browser worksheet exports/restores local
JSON observations without a feedback API, cloud upload or scientific-archive
mutation. Unobserved fields stay empty. Explicit retest creation retains the
parent session/packet identity and starts with empty outcomes.

Reuse the current GUI server and its loopback, origin, locking and cleanup rules.
The session entry registers only the packet's two explicit read-only reference
archives and indexes their metadata. Saved-analysis verification remains an
explicit GUI action. Installation and scientific execution remain separate.

Prepare a Windows entry through initialized Ubuntu on WSL 2, preserving Linux
process ownership and a Linux-filesystem checkout. Windows launch files use a
process-local PowerShell execution policy only; they do not alter the machine's
policy, install WSL, change distributions or open a LAN listener. WSL enablement,
restart and first-user initialization use Microsoft's documented prerequisite
steps. The start action does not install dependencies. The explicit install
action reuses locked projects; a missing uv is installed into a private tool
directory from the versioned upstream installer.

## Acceptance and limits

Verify packet integrity and refusal of linked/changed/incomplete material,
native reconstruction, fresh receiving-checkout setup, registered references,
HTTP/browser form behavior, malformed import refusal and session cleanup.
Record exactly which host and launcher paths were exercised. macOS checks,
PowerShell syntax checks or mocked WSL calls do not verify a real Windows host.
Windows/WSL readiness remains open until an actual machine runs its checks.

OT-048 and the human part of OT-049 require actual observations. Technical
preparation does not populate them or close P1, M2 or scientific acceptance.
Identify and review the actual handoff's sources, rights and dependency terms
before transfer; no participant contact details or observations are committed.
