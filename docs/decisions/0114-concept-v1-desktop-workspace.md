# 0114 — Concept v1 Mac desktop workspace

Date: 15 November 2026

Status: accepted for a bounded internal Mac implementation. Host checks and
artifact identities remain separate from this selection.

## Context

Concept v1 implements the compact launcher and Study workspace on the installed
SDK. The selected product entry now requires its own application window. This
increment selects Mac Apple Silicon; Windows is deferred. Earlier packaged apps
launch a browser and retain their own build and qualification identities.

## Decision

Use an Electron shell around the existing HTML/CSS/JavaScript interface and
local Python controller. Pin the Electron archive by upstream SHA-256. Reuse the
existing standalone Mac CPython lock and the existing two-task SDK profile 4.
Ship those runtimes and the installed SDK closure. Users need no host Python,
Node, development tools or browser window. Loopback remains private transport
between owned application processes.

The shell owns one window, compact startup and larger project bounds, native
project-directory selection, application menus, single-instance activation,
save-before-quit and service shutdown. A private stdout readiness message carries
the local token; it is absent from URLs and logs. Closing the native owner's
stdin pipe requests service shutdown after an application crash. The watcher
uses raw descriptor reads so it cannot hold stdin's buffered lock at shutdown.
Renderer failure has native reload/quit handling without requiring a reply from
the failed renderer. A nonresponding renderer does not prevent explicit quitting
with saved work.

Keep renderer Node access disabled, sandbox/context isolation enabled, and
restrict navigation, new windows and privileged IPC to the owned main frame.
Use the SDK launcher's fresh bytecode-cache-prefix rule before importing the
facade. Keep the existing services, source/reader identities, data schema and
scientific code unchanged. The initial shell increment exposed the two-screen
editing slice. The separately selected MMTT workflow continuation exposes the
existing freeze/run/cancel/recover, attempt/result, prospective comparison and
verified-export services in that same window. It adds an execution section and
Results tab rather than another application or ledger. Recovery requires an
explicit stopped-executor assertion and retains the SDK's live-lease checks;
opening or refreshing a project never resumes an attempt. Numerical methods,
source/reader identities and existing comparison denominators are unchanged.

Use `backend/lib/python3.12/site-packages/opent1d_lab` so the SDK's existing
installation-root boundary names the complete private backend. Writable work
lives outside that backend under `~/Library/Application Support/OpenT1D/Concept-v1`.
An explicit `--workspace` supports retained work and isolated tests. Chromium
profiles for explicit workspaces live in the OS temporary directory, never inside
chosen projects. Moving/replacing the app leaves saved work intact. Copying an
SDK project folder alone does not transfer GUI concept histories.

## Alternatives and consequences

A separate Cocoa/WebKit interface would add another integration path. Electron
reuses the selected interface and provides an explicit desktop lifecycle, with a
larger bundle and a renderer runtime that needs maintained version pins.
Windows needs a separately selected service/host port; this change does not
remove POSIX service gates or alter historical readers to claim that support.

Deliver an internal `.app` and ZIP with source/runtime identities, complete
payload inventories, upstream notices and provider materials. Mac builds use
local ad-hoc signing after rebranding; this is not Developer ID signing,
notarisation or a public release. Minimum-OS, clean-host and intended-user
acceptance remain separate from the current-host checks.

## Sources

- [Electron process model](https://www.electronjs.org/docs/latest/tutorial/process-model)
- [Electron security](https://www.electronjs.org/docs/latest/tutorial/security)
- [Electron native dialogs](https://www.electronjs.org/docs/latest/api/dialog)
- [Electron packaging](https://www.electronjs.org/docs/latest/tutorial/application-distribution)
- [Pinned Electron release](https://github.com/electron/electron/releases/tag/v45.3.2)
