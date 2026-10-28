# Prepare and run a local GUI test session

This is the technical entry for OT-045–049 and the MMTT beginner packet. The
[researcher exercise](gui-researcher-exercise.md) owns observation criteria;
the [GUI guide](local-gui.md) owns M4 operation. The
[paired analysis](observation-analysis.md) and [sampling](mmtt-sampling.md)
guides own the two MMTT routes. A beginner's session
can reveal usability problems without satisfying intended-researcher acceptance.

The [22 October packet verification](research/mmtt-beginner-packet-verification.md)
identifies the concrete Dutch MMTT ZIP and actual macOS checks; Windows/WSL and
human testing remain open.

## Prepare one bound packet

Use a clean, committed implementation checkout with the root locked environment:

```sh
uv sync --locked
uv run --locked python -m experiments.usability prepare \
  --complete /path/to/complete-m4 \
  --interrupted /path/to/interrupted-m4 \
  --output results/usability/session-packet \
  --language nl --target windows-wsl --session mmtt
```

`--session mmtt` selects two short participant assignments: explain whether a
paired secretion-change conclusion depends on assumptions, then explain what
changes when measurements within the same meal-test window are omitted. The
second paired example and first sampling example use existing synthetic inputs,
default settings, native runners and readers. The card asks for report-based
explanations, reopening, checking and saving; it supplies no expected answer or
click sequence. Expectations are confined to the moderator page. Existing GUI
example names do reveal their engineered purpose; repeating a label alone is not
evidence of comprehension.

`--session m4` (the default) retains the original M4 session. Every packet also
contains separate `M4-Participant.html`, `M4-Moderator.html` and
`M4-Observations.html` cards and both native M4 references. Use those cards for
the two supplied M4 models and three initial loads, preferably in a separate
session. The forms reject a different task set rather than mix M4 and MMTT
outcomes; restore or create a retest using the matching form.

`--language en` retains English session cards; Dutch is for a private generated
session packet. Supply real retained archives. Preparation copies them, uses the
current authoritative standard-library reader, checks original JSON/Markdown/SVG
bytes and verifies the declared complete/interrupted statuses. Missing, linked,
changed or incompatible material is refused. Original archives remain unchanged.
No model is imported, trained or simulated by preparation or reconstruction.

The participant card includes a terms glossary in its selected language for
the English GUI labels, including **Source ID**, Python model and its matching
JSON declaration. It explains vocabulary without prescribing a click route.
Record when the tester uses the glossary, just as with other guide assistance.
Restoring an observation export restores its earlier values; it adds no new
observations. A separate retest action creates empty outcomes.

The packet contains `FirstSteps.html`, offline `Participant.html`,
`Moderator.html` and `Observations.html`, version-bound source and native
reference bytes, launch files, session assets and offline copies of the five
canonical English guides (session, GUI, M4 exercise and both MMTT routes). Review that actual source bundle's rights,
attribution and dependency terms before transfer. No installed dependencies or
participant observations are bundled. Keep the complete directory together;
the manifest checks integrity but does not authenticate a sender.

## Refresh a packet after software changes

A packet and its installed checkout stay bound to their recorded revision;
pulling a newer main elsewhere does not upgrade them. To test the integrated
OT-057 MMTT interface fixes, prepare a fresh packet from an identified clean,
committed main revision, verify its manifest and setup receipt, and retain the
older packet and observations separately. The
[OT-057 record](research/ot057-uiux-verification.md) does not establish a newly
built Windows packet or Windows execution.

The MMTT packet extends the OT-045–049 preparation; it does not replace M4.
For comparative researcher acceptance, use the separate
[OT-056 protocol](research/ot056-researcher-pilot.md) and its forms; beginner
observations do not count as comparative pilot results.

## Receive on Windows through WSL

These are the prepared Windows/WSL instructions for a version-bound source
packet. Windows/WSL packet execution retains its own verification scope. For the
separately tested native Windows 11 x64 candidate and its bundled runtimes, follow
the [Windows installation guide](windows-installation.md). The packet's
`Install.cmd`, `Check.cmd` and `Start.cmd` files below use WSL.

Extract the entire ZIP into one directory and open `FirstSteps.html` before
installation. The documented command requires Windows 11 or Windows 10 version
2004 (build 19041) or later. Installation needs internet access and WSL setup may
require administrator rights; an existing initialized Ubuntu must use WSL 2.
For a compatible host,
Microsoft documents opening PowerShell as administrator, running
`wsl --install -d Ubuntu`, restarting and initializing an Ubuntu user. Existing
Ubuntu must use WSL 2. Follow [Microsoft's installation guide](https://learn.microsoft.com/en-us/windows/wsl/install)
when these prerequisites are absent; the launcher does not change them.

In Ubuntu, install Git and curl if missing:

```sh
sudo apt-get update && sudo apt-get install git curl ca-certificates
```

Then use the packet's three Windows files:

1. `Install.cmd` explicitly installs the source checkout and locked root/M4
   environments. A missing uv uses the versioned installer in a private tool
   directory without editing shell profiles. First installation needs network
   access; preserve errors and ask for help if required.
2. `Check.cmd` checks packet/checkout identity and required locked environments
   without importing supplied models or running an experiment. It saves a setup
   receipt; inspect `ready` in that receipt.
3. `Start.cmd` opens the local session in the Windows browser and keeps the WSL
   service in its terminal. References appear under **Added archives** with
   `session-reference` tags; use **Check saved analysis** explicitly to inspect
   them. Starting does not install or simulate.

The scripts select Ubuntu explicitly and store the installed checkout and packet
inside its Linux filesystem under `~/.local/share/opent1d/`. This follows
[Microsoft's filesystem guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems).
Windows browsers can reach WSL services through localhost according to
[Microsoft's networking guide](https://learn.microsoft.com/en-us/windows/wsl/networking);
the service stays bound to `127.0.0.1`. No firewall, port-forwarding or LAN access
change is performed. A browser connection failure is a blocked setup task,
not permission to expose the service on the network.

## Receive on macOS or Linux

Provide Git and curl, then use `Install.command`, `Check.command` and
`Start.command`. On Linux invoke these files with `bash`. Installation creates a
separate version-bound checkout; an existing packet's checkout is not overwritten
or upgraded. To verify in a disposable local directory, set the task-specific
`OPENT1D_INSTALL_ROOT` before launch. The default is `~/.local/share/opent1d/`.
See [uv's installer options](https://docs.astral.sh/uv/reference/installer/) for
the private unmanaged tool installation behavior.

For an already identified receiving checkout and copied packet:

```sh
.venv/bin/python -m experiments.usability verify --packet results/usability/packet
.venv/bin/python -m experiments.usability check --packet results/usability/packet
.venv/bin/python -m experiments.usability start --packet results/usability/packet
```

## Observe, export and retest

Agree and record whether installation is assessed or prepared beforehand.
Plan 45–60 minutes, retaining additional setup/execution time separately. Give
the participant goals rather than a click sequence; keep expected outcomes on
the moderator page. Record assistance and the participant's own explanation.
Use a separate fresh run for cancellation, retaining the completed study.

Open `Observations.html` directly if installation or startup is blocked; it needs
no local server and can retain the setup observations through explicit export.
The MMTT form separates installation, startup and the two assignments. Each
records outcome, result comprehension, assistance, observed problems and related
report identity. A visible comments field retains remaining questions and
unassessed work. Record partial execution/reopening/interpretation outcomes in
the explanation and problem fields rather than marking the whole task successful.
The observation form holds values in browser memory only. It makes no feedback
API request and uses no cloud or automatic browser storage. **Export observations**
requests a local JSON download; confirm it exists before closing. **Restore**
accepts a bounded export from the same packet. A malformed or foreign record
does not replace current observations. **Create a retest** explicitly selects
an earlier export, binds its parent identity and creates empty outcomes for the
current packet; the original file is never edited. Record the actual fix revision
and affected tasks. Keep downloaded observations private, outside the sealed packet and scientific
archives and version control, without participant names or contact details.

Leave unobserved fields empty. A blocked execution task stays blocked when a
saved report is supplied for later interpretation. Resolve blocking and
misinterpretation findings first, then repeat those tasks with a human tester.
The original P1 exercise and proposed broader researcher round remain separate.

## Stop and recover

Keep the launch terminal open. Cancel an active operation in the GUI, then use
Ctrl+C in the terminal to stop the server through its existing owned-worker
cleanup. Closing a browser tab does not cancel an experiment. A restart does not
adopt saved process IDs or live verification; recheck saved analysis explicitly.
An uncatchable terminal/host failure cannot guarantee cleanup.

For a missing prerequisite, follow `FirstSteps.html`. For an interrupted install,
rerun the explicit install action without deleting original evidence. Changed
packet/checkout bytes require the correct intact packet or a newly frozen
candidate. A second GUI server is refused rather than replacing the first.
