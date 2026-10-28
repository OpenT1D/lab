# MMTT beginner packet verification — 22 October 2026

This record covers internal technical preparation on
`codex/windows-mmtt-test-package`, based on remote main
`9d418dc9cb0dbdcc0471b55dac6269e40802d1f0`, fetched before work began.
The clean packaged implementation is
`c96729618bca8a499886d38cb58318817ce12e6a`. Later evidence-only documentation
commits do not replace its source bundle. No merge, push or external transfer
was performed during packet verification. Subsequent Git integration does not
rebuild the packet or add Windows/human evidence. The
[session guide](../gui-test-session.md) owns preparation and
use; the [OT-057 record](ot057-uiux-verification.md) owns the earlier interface
fixes already included in this candidate.

## Concrete packet

The local transferable artifact is
`results/usability/20261022/OpenT1D-Windows-MMTT-c967296-nl.zip`, alongside its
unpacked directory and SHA-256 file in the implementation worktree. A verified
copy is now preserved in the primary checkout as described below. Packet ID: `packet-5ca549b1776b438e9d4e4e55e8a21554`.

- ZIP size: 69,315,062 bytes.
- ZIP SHA-256: `9907be4018ba64dd89a219c97493f1a54cfc7a47e4f4dae29199a92acd20d339`.
- Manifest: 919 protected payload files; clean source commit and bundle identity
  verified, with no participant observations or installed environments included.
- ZIP extraction into a fresh directory reproduced the entire payload inventory,
  including empty directories, and passed native packet verification.
- Both retained M4 references were copied from the preserved 17 October packet,
  without modifying their originals. The authoritative reader reproduced all six
  JSON/Markdown/SVG artifacts exactly before packaging, preserving their distinct
  complete and interrupted statuses.

`FirstSteps.html` explains Windows/Ubuntu/WSL 2, explicit installation/check/start,
network/prerequisite requirements and recovery. The two Dutch MMTT assignments
use the second paired example and first sampling example with their supplied
settings. Expected outcomes appear separately on the moderator page. Existing
GUI example names reveal their engineered purpose; assess report-based reasoning,
not label repetition. Separate M4 cards, forms, references and runners remain
available. The default generator still selects M4 unless `--session mmtt` is
specified. English canonical guides for both MMTT routes are included offline.

## Actual local checks

Host: macOS 26.5.2, arm64, Python 3.12.13. This was an existing developer laptop,
not a clean operating-system image. Git, curl and uv were already available.
The actual `Install.command` installed into a fresh receiving directory with
spaces in its path, wholly inside this worktree. The bundle checkout, root lock
and two native M4 environments installed successfully. `Check.command` returned
`ready: true`, `numerical_validation: false` and
`source_or_model_executed: false`. Installation did not execute models.

`Start.command` launched the receiving GUI on loopback and indexed the two M4
references. An isolated Chromium browser prepared, froze, ran, viewed,
reconstructed and downloaded both MMTT tasks through the existing interface:

| Task | Actual native result | Reconstruction and downloads |
| --- | --- | --- |
| Paired assumption-dependent control | Complete: 1 person, 2 visits, 3/3 required variant pairs; classification remains assumption-dependent | JSON/Markdown reproduced exactly; both downloads equal original bytes |
| Sampling information-loss control | Complete: 5 people, 4 schedules, 60/60 required variant pairs and 7,680/7,680 perturbation pairs; three-time direction reversal retained | Parent and four child JSON/Markdown reports reproduced exactly; parent downloads equal original bytes |

Ctrl+C stopped the server and closed its listening port. Starting the same
installed packet again succeeded. Both named results reappeared in Results with
**Previously checked; check again**, and both were explicitly reconstructed
again. The same twelve report artifacts remained byte-identical across both
reconstruction rounds. This establishes local saved-result recovery, not Windows
process ownership or scientific validity. No new M4 simulation was needed for
this refresh; its locked setup and retained complete/interrupted readers were
checked, and its scientific implementation was unchanged.

The standalone feedback page was exercised through a static loopback preview,
without the experiment backend. Browser automation refuses `file:` navigation;
direct file opening remains unverified. Actual browser checks covered empty
initial values, clearly marked internal QA entries, export/download, reload with
empty values, explicit restore, foreign-packet and malformed-JSON refusal without
replacement, and a separate retest with an identified parent and empty outcomes.
The original QA export remained unchanged. All QA files stay outside the packet
and do not count as human feedback. The 390-pixel form was visually inspected;
fixed session, moderator, M4 and both MMTT guide routes returned HTTP 200.
Favicon 404s and expected polling connection failures while the GUI was stopped
were observed; these are not successful task executions or participant findings.

## Repository checks and retained evidence

`uv sync --locked` passed. `uv run --locked python scripts/check.py` passed on
the implementation: **1,395 tests in 441.846 seconds, 13 existing skips**, plus
lint, formatting, metadata/navigation checks and the warning-as-error
documentation build. The focused suite passed 12 packet tests and 24 worksheet
contract checks. Generated Bash launchers and worksheet JavaScript passed syntax
checks. An initial Markdown blank-line lint error was corrected before the
successful complete check; the intermediate failure is not counted as a pass.

Ignored `results/usability/20261022/` retains the packet, ZIP, manifest output,
installation log, setup receipt, native reconstruction identities,
`preservation.json` and full repository-check log. `output/playwright/` retains
snapshots, screenshots, exact downloaded reports and explicitly marked QA form
exports. The compact [machine record](../../experiments/usability/mmtt-verification.json)
binds the artifact and check scope. Source changes are confined to packet/cards,
feedback presentation, tests and documentation; native estimators, units,
protocols, locks, runners and readers are unchanged.

## Preservation before integration

On 22 October, the maintainer authorized merging the branch into main and
pushing the changes while preserving the packet and verification evidence.
Before integration, all local verification material was copied to the primary
checkout's ignored directory:

`results/usability/20261022/windows-mmtt-c967296/`

`packet-and-verification/` contains the original ZIP, unpacked packet, checksum,
installation/setup logs, native evidence, receiving installation and extraction
check. `browser-evidence/` and `browser-session-evidence/` retain the browser
captures, downloaded reports and clearly marked internal QA feedback. These
private verification files are separate from the transferable packet and remain
outside Git. `preservation-receipt.json` binds all 23,801 copied entries with
file hashes, directory entries and preserved symbolic-link targets. Source and
copy inventories matched; the copied packet passed its native verifier and the
ZIP retained the SHA-256 above. Originals were retained. Git integration does
not change the packet's frozen `c967296` implementation identity.

## Remaining acceptance

No Windows host was available. Actual Windows PowerShell, WSL enablement/Ubuntu
initialization, first installation, localhost browser access, both task flows,
stop/cancellation/cleanup and direct standalone HTML opening need verification
on the tester's own machine. Existing Windows launcher source is unchanged;
its earlier syntax/stub evidence is not a new Windows-host test. Missing-uv
bootstrap was not exercised on this already provisioned laptop.

Human installation/comprehension observations, assistance, observed fixes and
human retests remain empty and open. This beginner session does not replace the
[OT-056 comparative researcher pilot](ot056-researcher-pilot.md), establish
empirical validity or support treatment claims. Actual handoff rights review
and dependency terms remain separate before external distribution; this task
produced a local transferable packet, without transferring or publishing it.
