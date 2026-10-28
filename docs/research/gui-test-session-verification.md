# GUI test-session preparation verification — OT-045–049

This 11 October 2026 record covers technical preparation on the isolated
`codex/gui-usability` branch. The checked implementation is
`bd96d50cce473a3746fc1fc193f43dd556361c45`; subsequent status/evidence prose does
not change that implementation. The [session guide](../gui-test-session.md)
owns use and recovery; [decision 0065](../decisions/0065-observed-gui-test-packets.md)
owns the boundaries. These are internal checks, not participant observations.

## Packet and receiving installation

The Dutch private packet `packet-07668656af934f058718d11842819974` binds its
clean source bundle, 908 protected files and both actual retained M4 references.
The current standard-library reader reconstructed JSON, Markdown and SVG bytes
exactly for the complete and interrupted archives before packaging. Original
inputs were preserved. Complete reference coverage is 2/2 sources, 6/6
source/condition cases and 1/1 pair; the interrupted reference retains all
planned denominators with zero accepted sources/cases/pairs.

A fresh macOS receiving checkout was cloned from this source bundle through
`Install.command`. Existing Git, curl and uv were prerequisites; this was not a
clean operating-system image. Root tooling and both required native environments
were installed with the existing locks. The setup receipt reports `ready: true`,
`numerical_validation: false` and `source_or_model_executed: false`.
`Start.command` started the original GUI and indexed only the two explicit
read-only reference archives. Explicit native verification through the received
HTTP service reproduced all six download artifacts byte for byte. Their
complete/interrupted statuses and full denominators remained distinct.

The receiving GUI then checked and executed a new standard M4 study. It accepted
2/2 sources, all 6/6 source/condition cases and 1/1 pair. Explicit saved-analysis
reconstruction reproduced all three new native artifacts byte for byte. A
separate fresh run was actually cancelled: its sealed report remained
interrupted, with 0/6 accepted cases and the full planned denominator. Its
failed-archive reconstruction completed without labeling it accepted; the first
complete study was preserved. The live GUI reported no remaining owned processes.
After Ctrl+C stopped the received server, its kernel manager lock could be
reacquired. These lifecycle checks are macOS evidence, not Windows evidence.

## Browser, retention and request boundaries

An actual isolated Chromium browser exercised the Dutch worksheet: empty initial
outcomes, a clearly marked internal test value, export/download, reload, explicit
restore, malformed and foreign-packet import refusal without replacing current
observations, and explicit retest creation with a parent identity and empty new
outcomes. The actual downloaded JSON confirms those properties. No filled QA
record is included in the packet or counted as a participant result.

The standalone document was checked through a local static HTTP preview because
the browser automation tool refuses `file:` navigation. Direct opening on a
Windows browser remains unverified. The embedded packet metadata required no
scientific backend or feedback API. The 390-pixel form layout was visually
inspected. The actual received GUI exposed both references under Added archives
and displayed the verified complete report. Missing favicon requests returned
404; no worksheet JavaScript error was observed.

Actual requests to session routes refused a foreign Host and Origin with 403.
Changing a served participant asset produced 409; restoring the original bytes
restored access. The copied canonical guide, moderator page and standalone
worksheet were reachable through their fixed routes. No arbitrary file route,
feedback mutation API or LAN listener was introduced.

## Windows preparation and verification limits

The Windows launcher passed PowerShell syntax checking and eight controlled
cases on PowerShell 7.6.6 for macOS: missing WSL, uninitialized Ubuntu, WSL 1,
path conversion failure, execution failure, check, localhost browser opening and
refusal to open a foreign URL. WSL responses were stubbed; these checks do not
verify Windows PowerShell 5.1, a Windows host, a real WSL distribution, localhost
forwarding, prerequisite installation or console/process cleanup on Windows.
The temporary official PowerShell asset's published SHA-256 was checked before
use; no global PowerShell installation was made.

The intended tester uses their own Windows computer. Its Windows version,
WSL availability, actual installation/run/cancellation and usability observations
remain to be recorded. The launcher leaves WSL enablement, restart and Ubuntu
user creation to the documented explicit prerequisite steps. Handoff rights
review, the first real session, observed fixes and human retests remain open.

## Repository and source preservation

`uv sync --locked` passed. The complete clean implementation run of
`uv run --locked python scripts/check.py` passed: 1,280 tests in 220.221 seconds,
with 13 existing C1 runtime skips, plus lint/formatting, Markdown/YAML/CFF,
navigation and warning-as-error documentation build. Ten focused packet tests,
19 controlled checks of the actual worksheet code, Bash syntax, ShellCheck and
PowerShell syntax passed separately.

All 487 pre-existing files selected from scientific modules, GUI, setup,
workflows and root locks match the base main implementation; the new session
entry is separate. No model equation, parameter, scientific protocol, clock,
unit or numerical criterion was changed. Repository passes do not establish
independent usability or scientific validity.

## Retained evidence

Ignored local `results/usability/` retains the sealed packet, native HTTP
download/boundary receipts and protected-source check. Receiving checkouts and
setup receipts are disposable execution evidence; preserve the standalone
packet outside the implementation worktree before cleanup. Browser snapshots,
downloads and screenshots are ignored QA material. The compact
[machine record](../../experiments/usability/verification.json) identifies the
exact evidence scope; no contact details or human observations are committed.

The packet and a 68,826,290-byte ZIP were preserved byte-exactly under the
primary checkout's ignored `results/usability/20261011/` store. ZIP extraction
payload hashes match the original packet, including empty directories; filled
QA worksheet exports are excluded. `preservation.json` binds the actual ZIP
SHA-256 and source revision. No external transfer has occurred. The retained
packet deliberately binds the checked implementation above; this evidence-only
follow-up does not silently replace its frozen source bundle.
