# OT-058 Windows installer: internal verification

Dates: 22–27 October 2026 (local dates; original UTC receipt timestamps retained).

This record covers the separate `codex/ot058-windows-installer` branch.
[Decision 0073](../decisions/0073-native-windows-installer.md) records the technical
selection; the [installation guide](../windows-installation.md) owns procedures.
The ordinary-user Windows 11 x64 VM provides **partial delivery verification**,
without GitHub Actions or an independent user session. Candidate J is the current
installer under test; it corrects the Windows directory-inventory failure found
in I's focused maintenance preparation.

| Candidate J check | Result | Actual method and scope |
| --- | --- | --- |
| Build and payload audit | Passed | Clean source `f47868a9b135`; exact 24,282-file payload independently audited on the host. |
| Locked host repository check | Passed | 1,545 tests, 32 skips and strict documentation checks; not Windows execution. |
| I-to-J graphical installation and browser launch | Observed | The Finish screen and automatic browser Start page were seen; this does not establish the complete upgrade test. |
| I-to-J upgrade test phase | Failed | Run `20261025T175809852-Upgrade` closed with controller exit one after the installed-payload audit exceeded its 1,800-second observation limit. The audit process was left running for inspection. |
| Late installed-payload audit and normal stop | Passed separately | All 24,282 files / 773,858,663 bytes matched after the original 1,800-second allowance; normal application stop then returned zero with no session present. The original Upgrade remains failed. |
| Separate CompleteUpgrade continuation | Passed | Fresh full audit within 1,800 seconds; all 366 original files byte-identical, no additions or bookkeeping changes; normal start/stop and retained I manifest/reader shortcut. No I reader execution. |
| Focused installed-J native tests | Passed | 18 directory/preservation tests, no failures, errors or skips; actual installed code with no private directory override. |
| Attempt 09 installed-J attestation and full native suite | Passed | Selected-file attestation passed separately; 124 installed Windows tests, six exact declared skips, no failures/errors and an exact full post-test payload audit. This does not close scientific workflow or lifecycle coverage. |
| Attempt 09 sampling-information-loss API workflow | Passed | Five invented people, four schedules, 60/60 variant pairs and 1,920/1,920 draw pairs at 32 draws; five jobs completed with exit zero, fresh readers and identical reports across restart. No browser workflow or human inference is claimed. |
| Attempt 09 sampling cancellation and interrupted readers | Passed | Cancellation after actual native analysis began; original job cancelled with exit one, no error, forced cleanup or survivors. Fresh readers retained interrupted-report hashes across restart. Checkpoint03 preserves metadata, original jobs and report hashes; the uncollected report bodies are currently unavailable after the test-environment interruption. |
| Attempt 09 M3 forecast | Unresolved | Run `20261026T132021027-M3Forecast` was launched and last observed running at 13:27:39 UTC. No terminal controller or workflow result was recovered after the environment interruption. |
| Recovery attempt 10 Windows baseline | Passed | Fresh ordinary Researcher/AMD64 Windows 11 build 26300; app/data/registrations absent, no registered Python or WSL runtime, disconnected adapter. This baseline predates the current installation attempt. |
| Recovery attempt 10 transport diagnostics | Observed and reviewed | Thirteen groups retain pre-readiness timeouts and expected nonzero/timeout/refusal diagnostics. Raw bytes, replay and ownership refusal were checked; the timed-out child's final exit remains unobserved. |
| Recovery attempt 10 normal shutdown and cold copy | Partial restore evidence | Normal Windows shutdown, QMP guest-shutdown and actual QEMU launcher zero; coupled capture zero and four-state integrity checks. A later bounded clone-boot check passed after offline transport-helper repair, followed by normal VM shutdown. Full VM/TPM restore validation and graceful TPM shutdown remain unproved. |
| Recovery licensed baseline and browser download | Bounded evidence | Fresh licensed baseline and cold-copy capture passed. Root observed Edge download/Keep; the controlled local server recorded the complete exact-J response. The first file-facts collector timed out; a separate native SHA-256 check later confirmed the actual Windows file. Later metadata verified genuine ZoneId 3 and NotSigned status. The subsequent clean installation and healthy first GUI startup passed; public reputation remains untested. |
| Attempt 10 M3 forecast/comparison | Passed, bounded synthetic API/readers | Both new cases, fresh reconstruction, original jobs and complete reports are preserved and independently reviewed. Attempt 09 M3 remains unresolved. |
| Attempt 10 M3 cancellation/raw retention | Passed within raw-copy scope | Actual native-started run cancelled1; forensic retention job completed0, declaring 50 files/1,371,995 bytes. Integrity/reconstruction false and completeness null; receipt body now host-preserved; all 50 member bodies are not claimed host-preserved. |
| Attempt 10 M5 report library | Passed, report-only | Index and two saved-report verifies completed0; normal stops and original metadata/job collection completed. Metadata/job originals and source assertions were independently reviewed; report bodies are not host-retrieved and no M5 model execution is claimed. |
| Attempt 10 Campaign / M4 | Failed | Fixed 600-second reference-worker deadlines interrupted partial numerical reference work; candidate source evaluation and later gates were not reached. No physical/model/deadline shortcut or cause inference. |
| Attempt 10 native library | Passed; originals collected | Three actual passed M3/sampling inputs, restart/readers and nine original jobs preserved and independently reviewed. No native model rerun. |
| Attempt 10 durable API/packages | Passed, bounded | Two M3 packages; ten jobs for export/registration/integrity/readers including restart, all completed0. Original-job union independently verified; collection failures remain separate. |
| Attempt 10 launcher/session controls | Passed, private workspace | Fourteen bounded checks, genuine stale-session recovery and two held native-zero normal stops. No session/token/credential values exported; active numerical maintenance remains untested. |
| Attempt 10 remaining GUI | Passed within recorded scope | View-only route checks plus actual M3 export, external Task 1 index/reader, visibility restore and held normal exit. Initial path refusal/copy-helper failure preserved; no new model runs or independent human session. |
| Attempt 10 dependent RawRetention | Passed, raw-copy scope | Two jobs, 43/85 files; both complete receipt bodies host-preserved, no member-body export. Integrity/reconstruction false, completeness null. |
| Attempt 10 lifecycle preparation | Passed, preparatory scope | Eleven frozen cases; metadata independently reviewed, not complete frozen-report body export. Later targeted removal/readers are recorded separately below; preparation alone is not acceptance. |
| Attempt 10 Maintain first attempt | Failed before installer launch | Helper refused `E:\candidate-j.exe` with `Unsafe root path`; no accepted analysis or installer marker. Original failure retained; no later attempt pass claimed. |
| Attempt 10 Maintain02 | Failed at report-wrapper save | Inner graphical installer0, launch refusal, full payload audit and original-data preservation passed. Output-filename collision prevented persisted report-check result; active numerical cancellation unproved. |
| Attempt 10 focused report reconciliation | Targeted checks/stop passed and reviewed | Separate GET-only eleven-case/22-report comparison and held normal stop passed. The full result body is preserved and independently verified; no installer/model rerun or change to failed Maintain02. |
| Attempt 10 Uninstall05 | Failed before Uninstall click | Native analysis was observed before launch, but the child-query observer timed out. A later observer crashed with an exact-identity Application Error event. Normal Cancel of the old window did not establish removal or active-job cancellation. |
| Attempt 10 controlled Uninstall03 | Passed, targeted active cancellation | Actual native analysis was running before operator Uninstall; held parent/child/server exited0 and analysis/job cancelled1 cleanly. Original failed Uninstall05 is unchanged. |
| Attempt 10 post-removal checks02 | Passed, separate component | Both retained full payloads verified; 7,023 original files byte-identical with 728 additions. Separate Windows metadata confirms registration/main-shortcut removal and retained reader shortcut; CIM-visible process scope only. |
| Attempt 10 focused retained readers03 | Passed and independently reviewed | Real retained shortcut; eleven fresh jobs completed0, eleven ordered outcomes and 22 hashes match frozen preparation. Normal held stop and final full payload audit passed; no fresh host copy of all 22 report bodies. |
| Attempt 11 fresh Baseline | Passed, application absence/idle | Independent boot facts and sealed baseline ancestry remain separate; no full dependency or VM/TPM restore retest claimed. |
| Attempt 11 InstallI / admission03 | Original phases remain failed | Graphical installation/automatic GUI were observed; original audit returned C000013A. Admission03's separate full I audit passed, but its wrapper failed from PowerShell case-insensitive variable shadowing. |
| Attempt 11 admission04 | Passed, separate component | Exact full I payload, real shortcut/basic desktop probe, three native-zero children, held server zero and idle checks. No installer/model rerun or upgrade acceptance. |
| Attempt 11 OriginalIGuard07 | Controller crashed; no phase result | Exact-identity Application Error 1000/C0000005; no observed native controller exit, phase/log/end/body or product/model dispatch. Cause remains unknown. |
| Attempt 11 owned I guard / fixture | Passed, bounded | Second owned guard passed a six-file inventory; fresh one-person 32-draw I case and reader passed with four jobs0 and two original reports. Earlier guard crash and five optional capture gaps remain separate. |
| Attempt 11 fresh I-to-J upgrade | Passed and independently reviewed | Exact J payload; 95 originals with 93 byte-identical, exactly two precomputed bookkeeping transitions and zero added at preservation check. Two original reports identical; fresh J reader, native18 without skips, normal stops/idle passed. No post-upgrade I-reader execution or full optional-log capture claim. |
| Recovery normal Windows activation | Passed after authorization | Explicit user authorization on 27 October resolved the earlier approval block. Normal activation and an ordinary-user license query passed; WinHTTP DIRECT, stopped proxy and disconnected NIC were verified. Application acceptance remains open. |
| Synthetic MMTT API case and first native reader | Passed | One 32-draw observations/increase case, complete synthetic cohort and unchanged reconstructed reports; four jobs completed with exit zero. All 366 existing files stayed byte-identical, with 89 added and no bookkeeping changes. |
| Repair | Passed | Full J payload restored; all 455 files byte-identical across maintenance with no additions or exceptions. A fresh native reader reconstructed the unchanged original reports. The two prebound normal-restart bookkeeping changes are recorded separately. |
| Reinstall | Passed | Full J payload verified; all 460 files byte-identical across maintenance, with no additions or exceptions. A fresh native reader reconstructed the unchanged original reports. Maintenance started with the application running; no active numerical-job maintenance claim. |
| Fresh J installation and example workflow | Passed | Separate clean ordinary-user offline baseline, exact full J payload, automatic server probe and shortcut reuse; one 32-draw MMTT API case and fresh reconstruction. An agent separately viewed the healthy Start page, results library and saved report; no independent human session or full GUI execution is claimed. |

Earlier I results remain distinct:

| Candidate I check | Result | Actual method and scope |
| --- | --- | --- |
| Application/dependency baseline | Passed | Ordinary Windows 11 x64 account; OpenT1D and its workspace absent, no registered Python, WSL feature disabled and no WSL distributions/packages. |
| Clean installation and startup | Passed | Offline graphical installation, default Finish browser launch and full installed payload audit. |
| Shortcuts | Passed | Start-menu/desktop reuse of the same process/session, maintenance stop and full payload audit; no model execution. |
| Initial installed native suite | Failed | 121 tests, one failure, two errors and six allowed skips; post-test payload audit not reached. |
| Explicit unchanged warm native retry | Passed | 121 tests, no failures/errors, the same six skips and full post-test payload audit; the initial failure remains unexplained. |
| M4 | Failed | The v10 API run failed after installation/readiness completed. The historical worker reached computation before interruption; cause analysis remains open. Earlier v8 observer and v9 pre-workflow guard failures remain preserved. |
| Campaign, M3, MMTT/cancellation | Pending | No closed I workflow result yet. |
| Library, durable archives and raw-retention UI | Pending | No closed I route result yet; M5 retains its report-only scope. |
| Focused maintenance preparation | Failed | The complete existing-workspace inventory stopped before fixture creation: a Windows directory size changed from 4096 to 0 across opening its pinned handle, with identical identity and timestamps. |
| Repair, Reinstall, Uninstall and saved readers | Pending | No I lifecycle result inferred from earlier candidates. |

The [candidate-I evidence](#candidate-i-clean-installation-and-native-retry-workflows-pending)
below distinguishes product results, helper failures and diagnostic-only passes.
Earlier C browser evidence and H's partial API/lifecycle passes remain in their
own sections. A/C native failures, both F Shortcuts failures, G's unpublished
comparison state and all H failures are preserved. API checks do not substitute
for a browser walkthrough; independent user acceptance, scientific validity and
public release remain open. The original macOS process-group EPERM remains
unexplained despite unchanged passing repeats.

## Implemented boundary

The offline NSIS candidate targets Windows 11 x64. It bundles three isolated
portable CPython 3.12.15 runtimes from python-build-standalone release 20261021,
with the existing root, secure-native and observation dependency locks. Its
scope is all current GUI routes: M3, maintained M4, campaigns, both MMTT analyses,
the report library and durable archives. M5 remains report-only in the GUI.

Native Windows support includes live locks, reparse-point checks, Job ownership,
gated worker startup and cooperative cancellation followed by bounded cleanup.
Installation and launch share a mutex. Incoming maintenance code can stop the
application when its old runtime needs repair. Immutable source/runtime
identities, separate data and retained reader shortcuts preserve reconstruction
dependencies. Installed readiness and durable trust use verified package
inventories; checkout verification retains its existing Git/uv contracts.

## Actual local evidence and its limits

The host is macOS 26.5.2 / Darwin 25.5.0, arm64. The root tooling environment was
prepared with `uv sync --locked` under Python 3.12.13. Native and observation
checkout environments were synchronized from their unchanged locks under exact
Python 3.12.15. Generated synthetic evidence stays under ignored `results/` or
task-local temporary directories; it contains no patient records.

The full Windows runtime assembly was statically inspected: root 62, native 34
and observation 12 distributions, with exact locked versions and both pinned
upstream Git revision identities. The Windows CPython archive SHA-256 is
`aac5d331fc3307343f95928fdbea4583f0d53973d08c7e1d081884fbd229a0e1`.
The corresponding macOS arm64 CPython archive used for local rehearsals has
SHA-256 `7b8d00b751db21cea87dc551a8f8165147c5fbc5251d5537d7e5497dde00a219`.
Mac runtime execution does not test the Windows binaries.

Focused tests cover package inventory/dirty-source boundaries, offline runtime
checks, source/data separation, installed durable trust, foreign archived paths,
scientific process supervision and live locks. Existing durable M3 fixture
coverage was extended to include the newly bound shared helpers. Actual Windows
Job, mutex and nested-predictor tests are explicitly skipped on this host and
included in the manual Windows workflow.

A full source rehearsal passed both M3 routes, then correctly refused an M4
historical reference because `experiments/desktop/runtime.py` changed while its
frozen computation was running. Cleanup completed. This is a failed rehearsal,
not an accepted full run; final checks must use stable source. Source rehearsals
retain developer `PATH` because checkout readiness explicitly requires uv.
Installed acceptance instead uses an empty worker `PATH` and cannot skip durable
archive verification.

The first stable full-GUI repository check passed: 1,440 tests in 417.879
seconds, with 17 explicit skips, followed by the strict documentation build.
Ruff, Markdown, YAML, citation metadata and navigation checks also passed. The
command was `uv run --locked python scripts/check.py`; its complete local log is
retained under `results/ot058-verification/full-gui/`. Subsequent review fixes
are included in the final complete check recorded below.

A separate real HTTP rehearsal passed both M3 routes, both MMTT analyses,
controlled MMTT cancellation and the report-only M5 route. It exercised library
registration, verification, original downloads and reversible hide/restore for
the five non-M4 readers. Forty-nine focused durable, M3 durable, installed-trust
and launcher tests passed. These were narrower preliminary results; the complete
immutable installed-payload rehearsal is recorded below.

The complete desktop navigation was also inspected in a real browser: all four
research questions, M4 readiness, campaigns, the configured archive store and
Exit were available; shutdown returned zero. The screenshot is retained in
`results/ot058-verification/full-gui/browser-start.png`.

The M5 Windows acceptance route uses an unchanged genuine synthetic saved
archive in `tests/fixtures/m5-report-only.zip`, with its generation and member
hashes in the adjacent JSON. Its 17 original files total 294,495 bytes; the ZIP
SHA-256 is `53052374b637adb799adfa4d040c338a0577d038c820baa10a128bcc60a9afeb`.
The harness only extracts verified bytes and invokes the current report reader;
it does not execute archived source or add M5 execution to the Windows GUI.

## First built candidate and its repository check

The original implementation candidate was committed as
`1a955012c43981980d77f3776336c3f5048cb614` on the separate branch. The worktree
was clean when the package was assembled. Later verification-record and manual
CI time-budget edits do not change the source revision recorded inside this
installer. The manual job now allows 120 minutes: three sequential native smoke
stages each retain their existing 30-minute limit, with time for building,
reader/lifecycle checks and evidence upload. The earlier 45-minute job budget
predated the full-GUI test scope.

That original candidate is
`OpenT1D-ot058-1a955012c439-702a1dd1c99f1cb4-windows-x64.exe`:

- Size: 201,602,772 bytes (192.3 MiB).
- SHA-256: `80a5980ec803d025b92a686844c1a9b81bab1fb8267a47c7bf4029070ac8b7e1`.
- Source: 1,203 tracked files, each checked against its committed Git blob;
  index flags and clean filters cannot conceal different packaged bytes.
- Payload: 24,270 files / 773,529,782 bytes, with every manifest hash verified,
  exact locked distributions and upstream commits, and no links or bytecode.
- Two NSIS 3.13 compilations of the same immutable payload on this macOS host
  produced identical executable bytes. This does not establish reproducibility
  across different hosts or a fresh dependency assembly.

The executable, checksum, `build-result.json`, `payload-audit.json`, complete
manifest, `reproducibility.json` and compiler logs are retained locally under
`results/ot058-delivery/`. This exact executable subsequently ran on Windows;
its failed first installation is recorded below. The source fix prepared after
that failure is not part of these executable bytes.

At that checkpoint, the required commands, `uv sync --locked` and
`uv run --locked python scripts/check.py`, passed on the clean implementation:
**1,453 tests in 469.309 seconds, with 18 explicit skips**, plus Ruff, formatting,
Markdown, YAML, citation metadata, navigation and the strict Sphinx build. The
complete log is `results/ot058-verification/full-gui/repository-check-delivery.log`,
SHA-256 `9b607250caa52dfd7d3f8a6fa3ac357af488cf3d32dd7a6e39abb7f1d988049c`.
An intermediate run had exposed an obsolete signal-injection test hook after
canonical report output changed to bytes; the hook was corrected and all four
SIGTERM finalization phases passed before this final complete check.

## Full installed-package rehearsal on macOS

The complete installed-payload harness passed against the same clean
`1a955012c43981980d77f3776336c3f5048cb614` application source, with three actual
macOS arm64 CPython 3.12.15 runtimes and their locked platform dependencies.
It ran outside the source directory, with an empty launcher/worker `PATH` and
separate program, workspace and durable-storage directories. It did not rely
on Git, uv or a system Python and did not skip durable reconstruction. This
tests the installed application architecture on macOS, not Windows binaries.

The actual HTTP route exercise passed:

- Both M3 preparation, check, execution and exact reconstruction routes.
- Maintained M4 execution with two supplied models and the fasting scenario:
  two accepted sources, two accepted source/scenario combinations and one
  accepted pair. Reconstructed JSON, Markdown and SVG bytes match the originals.
- A two-slot campaign with controlled cancellation after the first accepted
  slot, interrupted reconstruction, remaining-work check, resume and final
  reconstruction. The accepted first slot and interrupted attempt are unchanged.
- Both MMTT examples and their known synthetic outcomes, original downloads,
  reconstruction and a separately cancelled sampling analysis.
- All six native library readers, including M5's unchanged report-only fixture:
  registration, verification, original downloads, hiding and restoration.
- Four durable exports, registrations, integrity checks and reconstructions:
  both M3 routes, maintained M4 and the campaign. The matching installed reader
  is independently verified; archived source is not automatically trusted.
- Repeated launch, malformed-input refusal, clean authenticated Exit,
  reopening and re-verification of saved library/durable entries, and clean
  launcher `--stop` shutdown.

The retained job record contains **70 jobs: 68 completed and two intentionally
cancelled**, with no forced cleanup and no remaining owned processes. Both
application shutdowns returned zero. Evidence and synthetic artifacts are
retained in `results/ot058-verification/full-gui/installed-mac/`, including the
original source/runtime binding. The original `evidence.json` SHA-256 is
`ff726b1b73797f53a0ddd928abebdd21d04393340bfe1035536ce06114cff718`.
The post-run audit verified that all 20,789 macOS package files, totaling
872,068,763 bytes, were unchanged and contained no links or hardlinks. No
transient session credentials remained in the retained evidence. The synthetic
artifact ZIP passed its CRC check; its SHA-256 is
`4a29982f5a182ec266b17becb4506d5fd77d5ec794b29f7a6672b24453f1e958`.
The smoke record explicitly says `actual_windows_execution: false`,
`independent_clean_windows_installation: false` and `human_sessions: 0`.

## Earlier MMTT prototype

Before the full-GUI scope was confirmed, a narrower embeddable Python 3.14.9
prototype was built and exercised. Its evidence is retained under
`results/ot058-verification/` as historical prototype evidence only. It is not
the final runtime selection or evidence of all GUI capabilities.

Both MMTT analyses passed real desktop execution under local Python 3.12.13 and
exact 3.14.9: known synthetic outcomes, original report downloads, exact
reconstruction, repeat launch, restart, cooperative cancellation and shutdown.
Scientific report fields agreed after excluding declared provenance/journals.
The 3.14.9 interpreter was compiled locally from official source and lacked its
optional SSL extension; this only exercised standard-library code and localhost.
An actual browser rehearsal also completed both examples and the Exit action.

The first broad check, during active parallel editing, reported fixture and
source-provenance errors. Five durable M3 fixture cases passed after adding the
shared helper, and fresh focused M3 suites passed once their source was stable.
These intermediate results are not a successful final repository check.

## Actual Windows baseline and first installation failure

On 23 October, a local Windows 11 Enterprise Evaluation x64 VM completed the
ordinary-user `Baseline` phase. The guest reports **26H2 / 26300.9457**, PowerShell
5.1.26100.9444, Secure Boot enabled and TPM 2.0 status OK. QEMU 11.1.2 emulates x64
on the ARM64 Mac using multithreaded TCG, four virtual CPUs, 8 GiB RAM and
`-cpu max,vendor=GenuineIntel`. These elapsed times do not represent performance
on a native Windows PC. The Microsoft ISO's SHA-256 was checked against its
published hash before provisioning.

Earlier provisioning attempts failed before any OpenT1D installation: an
overlong unattended setup command was corrected, and three guest bugchecks were
independently traced to the kernel's RDPMC instruction, which the
[pinned QEMU TCG helper](https://raw.githubusercontent.com/qemu/qemu/v11.1.2/target/i386/tcg/misc_helper.c)
does not implement. After the controlled CPU-vendor change, normal
Microsoft activation, the baseline and a clean shutdown/reboot sequence passed.
This establishes those observed steps, not general emulator stability. Windows
hardware requirements and protections were not disabled.

Normal activation used `slmgr.vbs /ato` after a visible UAC approval with the
separate provisioning administrator. It returned zero and LicenseStatus 1,
without a supplied product key, clock backdating or rearm. Only this provisioning
step used restricted Microsoft activation/validation network access. WinHTTP
was restored to DIRECT, the temporary proxy stopped and the guest NIC
disconnected before the application baseline and installer attempt.

The actual Baseline phase passed at **06:54:07 UTC** as non-administrator
`Researcher`, with a 64-bit AMD64 process and OS. Its bounded checks found no
Git/Python/uv development command on PATH, registered Python installation,
enabled WSL feature/package/distribution, or existing OpenT1D installation or
workspace. Inbox WSL commands and WindowsApps Python aliases are not counted as
installed runtimes. The record reports `actual_windows_execution: true` and
`human_sessions: 0`; these are agent-operated checks, not independent user use.

Normal shutdown returned zero, QEMU exited without a forced stop, and a stopped
copy of the disk, UEFI variables and TPM state was preserved. The next boot's
event check confirmed orderly-shutdown events 1074/6006 followed by startup
event 6005, with no new bugcheck or unclean-shutdown event in the checked
interval. The later baseline restoration is recorded below.
The private supporting records are `confirmed-baseline-phase.json`,
`activation-confirmed.json` and `baseline-normal-shutdown.json`.

The original candidate then displayed its Welcome, license and extraction
pages while running offline as the same ordinary user. At **07:41:40 UTC**, it
displayed: "OpenT1D cannot inspect its installation folder. Check access to your
local application-data folder and retry." The installer had extracted its
temporary maintenance payload but did not complete installation. A subsequent
native inspection found the destination, application registration, uninstall
registration, desktop shortcut and application session absent. An empty
workspace directory existed; there were no experiment outputs.

Native `GetFileAttributesW` inspection returned error **3** for the missing
version/installation ancestors and error **2** for the missing `Programs`
directory; existing ancestors were ordinary directories. The inspection ran
successfully as the non-administrator user. This does not support the displayed
access-error explanation. A subsequent native NSIS 3.13 comparison reproduced
the defect: the original separate `GetLastError` plug-in call returned **80**
for every missing path, incorrectly rejecting it; immediate `?e` capture
returned the correct **2/3** and allowed those paths. The ordinary-user probe
completed with exit code zero and no timeout, across 36 comparisons including
repetitions and existing-directory controls. Stack sentinels and the register
canary remained intact in every comparison. This confirms the error-capture
defect; it is not a successful installation result.

The minimal source correction uses that documented `?e` option, preserving the
existing ancestor, directory and reparse checks. The observed clipped Welcome
heading also has a shorter title. Both changes are in corrected candidate A
recorded below.

The corrected full NSIS template and an extracted-function regression probe
compile with NSIS 3.13. Thirteen packaging tests pass on macOS; the three new
native tests are explicitly skipped there. They exercise existing/missing
directories, files, invalid names, junctions and caller-stack preservation.
The first test driver mishandled quoted command-line paths containing spaces;
its valid-path cases stopped before reaching the production function. That
failed test record is retained. A corrected driver transports paths through a
Unicode environment variable. It passed all **three native Windows tests in
12.221 seconds**, including existing and missing paths with spaces and Unicode,
file/invalid-name refusal, junction/descendant refusal and caller-stack checks.
The ordinary-user controller completed at 08:04:07 UTC with exit code zero.

**At that diagnostic checkpoint, successful installation was still pending.**
No application startup, GUI workflow, scientific execution or Windows maintenance
result is inferred from these focused tests, extraction progress or the baseline
pass. Candidate A's later completed installation is recorded below.
Supporting private evidence includes
`installer-details-13.png`, `inspect-install-paths-01`,
`capture-install-failure-01`, `nsis-path-comparison-01` and
`poll-nsis-regression-03`; raw credentials,
tokens and crash dumps are excluded.
The [NSIS System documentation](https://nsis.sourceforge.io/Docs/System/System.html)
defines immediate error capture.

The first harness reached its 3,600-second installer deadline at 08:06:03 UTC
while the error dialog was deliberately retained for native diagnostics. Its
terminal phase remains failed with that timeout recorded. The dialog was then
dismissed through the normal Abort/Cancel flow; this is not an extraction-time
performance result or a successful installation.

A separate ordinary-directory open/query/close probe passed using the original
Windows runtime. Review nevertheless identified a documented access-rights
mismatch: durable directory handles queried attributes while requesting only
`FILE_LIST_DIRECTORY`. The source now also requests `FILE_READ_ATTRIBUTES`
(`0x81` combined), retaining the same no-delete-sharing and reparse controls.
Three native tests cover query/close, rename protection and release, and
file/junction refusal without leaked handles. All three subsequently passed
against installed candidate A, as recorded below; the original probe did not
reproduce an access failure on this NTFS system. An attempted pre-build run of
the new tests could not start because normal NSIS cleanup had removed the old
temporary maintenance Python. That staging record is retained as **not run**,
not as a directory-test pass or a product failure. The Windows API contract is
specified in [Microsoft's query information reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryinformationfile).

The second local attempt uses a separately identified v2 acceptance harness
with an outer installer limit of **10,800 seconds**, replacing the first
harness's 3,600-second limit. The installer currently extracts the full payload
twice, first for trusted maintenance and then for installation; the larger
budget accommodates that work under CPU emulation. It does not extend any
application, scientific-worker or workflow deadline, and it does not relabel
the failed first attempt as successful.

## Corrected candidate A and second Windows attempt

Candidate A was built from clean source revision
`f661a63d2231726cc2fba6fc5ab0b288d9ad363c`, with build ID
`ot058-f661a63d2231-fe0740bbdf771023`. Its executable is
`OpenT1D-ot058-f661a63d2231-fe0740bbdf771023-windows-x64.exe`:

- Size: **201,611,215 bytes**.
- SHA-256: `cc7886da159e9e1f326e7af11bc968702712aa20aab35d287b88ba442633daed`.
- Source: **1,205** tracked files, verified against the exact committed Git blobs.
- Payload: **24,272 files / 773,551,531 bytes**, with every hash and the complete
  file set verified and no symbolic or hard links.
- All three runtime file inventories and dependency metadata remain unchanged
  from the first candidate: **62/34/12** root/native/observation distributions,
  with the same pinned upstream revisions.

The independent artifact audit verifies these bytes and identities; it does
not establish Windows installation or scientific acceptance. The executable,
`build-result.json`, `payload-audit.json` and manifest are retained under
`results/ot058-delivery-windows-fix-a/`.

The complete required repository check after both Windows fixes passed:
**1,459 tests in 406.971 seconds, with 24 explicit skips**, plus all lint,
formatting, metadata, navigation and strict documentation checks. Its log is
`results/ot058-verification/full-gui/repository-check-windows-fixes.log`, SHA-256
`2389885f04820137789af699a654dcce633c5b9f47c219d5be998a681876f27c`.
This macOS check does not substitute for native Windows execution of skipped
process, directory or lifecycle cases.

After normal shutdown, the failed first installation state was preserved as a
separate cold snapshot. The clean pre-installation baseline was restored using
all three coordinated components: disk, UEFI variables and TPM state. Their
restored hashes were verified and the preserved baseline remained unchanged;
the private `failed-install-attempt-01/restore-result.json` records completion
at **08:18:09 UTC**. The new v2 Baseline phase passed at **08:29:02 UTC** as
ordinary `Researcher`, with exit code zero and `human_sessions: 0`, recorded in
`confirmed-attempt02-baseline.json`.

The v2 helper preparation passed actual inbox PowerShell parsing for **23
scripts**, and candidate A's hash was verified in the guest. Its short Welcome
title and license page were visibly inspected without an application-installer
UAC prompt. The guest remained offline, using the restored baseline with no
developer tools or separate prerequisite setup. After both extraction stages,
the installer displayed **OpenT1D is installed**, with a visible desktop
shortcut and the default **Open OpenT1D** option checked.

The actual **Install phase passed** for
`ot058-f661a63d2231-fe0740bbdf771023`. It started at **08:30:57.782 UTC** and
finished at **10:12:01.709 UTC** on 23 October 2026. The controller finished at
**10:12:02.833 UTC**, exit code **0**, and was no longer running. The phase
verified the expected installed build/source identity, Windows app registration,
main/desktop/saved-reader shortcuts and installed payload audit. It ran as
ordinary `Researcher`, with a 64-bit AMD64 process and OS,
`actual_windows_execution: true` and `human_sessions: 0`. This establishes the
declared clean-install criterion internally; elapsed time includes CPU-emulated
extraction and verification and is not a native-PC performance benchmark.

The agent clicked **Finish** with the default launch option still checked.
Edge's ordinary first-use prompts were completed without an account or data
import; recurring import and optional personalization were disabled. OpenT1D's
**Start** page then displayed at a bare loopback URL. **More** navigation and
the MMTT analysis screen worked. These observations establish browser startup
and navigation. A later click on **Prepare example** for **Consistent increase
control** failed with **Entry owner exited with live descendants**, visible at
**10:22:03 UTC** in `attempt02-mmtt-prepare-01.png`. No calculation completed.
The private GUI observation record preserves that failed action separately from
the successful installation and automatic startup; neither result replaces the
other. The Finish page and first Start page were retained as screenshots,
separately from the terminal installation record.

The subsequent native suite completed with a failed result, recorded below.
All full Windows workflow and reader checks, repeat shortcut launch,
repair/update/removal and retained-reader acceptance remain pending. A
distinct-build update test remains pending. The failed first installation and
its focused diagnostics retain their original outcomes; the successful
candidate-A installation retest does not replace them.

## Candidate A native suite: failed result

The installed candidate-A CPython **3.12.15** runtime ran the native suite on
Windows x64: **23 tests in 36.447 seconds, one failure, four errors and one
explicit symlink-permission skip**. The skip reports that creating a Windows
symlink requires Developer Mode or permission; it is not a test pass.
All **three NSIS installer-path tests** and **three Windows directory tests**
passed, including directory-handle query/close, rename protection and release,
and file/junction refusal. The full suite nevertheless failed.

The four error reports arose during input freezing or declaration intake in
`read_regular`, before the intended scientific behavior could be tested.
The private cancellation case reported **analysis settings changed during
read**. Both nested-predictor subcases (`success` and `timeout`) and the
foreign-original-path archive case reported **declaration changed during read**.
The `timeout` subcase name does not establish an actual timeout: its input
intake failed first. These are file-identity/read-check errors, not successful
scientific or cancellation results. The subsequent diagnosis is recorded below.

The separate Job example test reached child exit code **0** and confirmed its
example output existed, then failed because cleanup returned `forced=True`
where the test required false. That assertion alone did not establish the cause;
subsequent native diagnostics did. The original failed suite remains part of the
evidence. The later separate-source native regression result is recorded below;
it does not change this installed candidate-A result.

This result does not undo the separately passed installation and automatic
browser startup. It leaves native acceptance and the broader numerical,
workflow and lifecycle gates open. The record is agent-operated and retains
`actual_windows_execution: true` with no independent human sessions.

## Confirmed native diagnoses and separate-source regression checks

The unchanged installed CPython 3.12.15 reproduced the intake rejection on a
fresh synthetic 20-byte file. Path snapshots were stable before and after the
read; descriptor snapshots were stable before, after and on reopening. Device,
inode, size and modification time agreed. The mismatch was `st_ctime_ns`: the
path snapshot represented creation time while the descriptor represented native
change time. No concurrent file mutation occurred in this diagnostic. This
matches the exact CPython implementation: [Windows path stat copies birth time
into its legacy change-time fields](https://github.com/python/cpython/blob/v3.12.15/Modules/posixmodule.c#L2008-L2018),
whereas [descriptor metadata reads native ChangeTime](https://github.com/python/cpython/blob/v3.12.15/Python/fileutils.c#L1026-L1045).
[Python documents the Windows timestamp transition](https://docs.python.org/3.12/library/os.html#os.stat_result.st_ctime).

The prepared source correction compares the original descriptor snapshots with
a freshly opened, validated descriptor for the final pathname check. It retains
identity and timestamp comparisons, byte limits, link refusal and the existing
hardlink policy. The analogous durable-file checks use the same helper. Eight
focused regressions cover unchanged reads, clock semantics, concurrent mutation
and replacement, limits, hardlinks and descriptor closure. The private
`native-stat-findings.md` binds the reproduction and upstream source inspection.

The first separate-source native preflight ran **eight tests in 0.631 seconds**
with **three errors, no assertion failures and no skips**. The unchanged-read,
mutation, hardlink/limit, clock-semantics and descriptor-closure cases passed.
All three errors occurred in two replacement-test methods: their ordinary
`os.replace` calls could not overwrite an already-open destination on Windows.
The intended replacement assertions were therefore not reached. The fixture now
renames the old path to a unique sibling before moving the replacement into the
vacated path; it does not skip or suppress either operation. Production fix
bytes were unchanged. The updated eight-case fixture passed locally with Ruff
and subsequently passed in the combined native retest below. This diagnostic
used a separate copied app with `dirty: true`, and verified its source and the installed A source/Python
identities afterward. It is not installed candidate-A or candidate-C acceptance.
The private `read-stat-preflight-01` record preserves the failure.

An earlier full repository check with the native workflow fixes passed
**1,469 tests in 424.297 seconds, with 25 explicit skips**, plus lint, formatting, metadata,
navigation and strict documentation checks. Its log is
`results/ot058-verification/full-gui/repository-check-native-workflow-fixes.log`,
SHA-256 `3b3b77f01959079cabd3a3051eded07b5ab4cfc7110c74a3df09148dad7472f7`.
That run used the earlier replacement fixture. The final complete host check
after the test corrections is recorded below.

The separate Job diagnostic identified the remaining process as `conhost.exe`,
created with `CREATE_NO_WINDOW`. It could remain alive after the Python worker
finished, so strict live-descendant cleanup correctly detected a process. It
was not the retained completed Python root: closing that root's handle did not
remove the remaining process. An alternating native comparison ran two original
and two detached launches. All four roots exited zero, produced the example and
had identical stdout hashes. Both original launches required forced cleanup;
neither detached launch did, using the same 15-second root deadline and zero
cleanup grace. Microsoft's [console creation contract](https://learn.microsoft.com/en-us/windows/console/creation-of-a-console)
and [process flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
distinguish detached processes from console applications without a visible window.

The prepared source change selects `DETACHED_PROCESS` for redirected owned
workers. It does not ignore console-host PIDs, weaken Job inventory, extend
scientific deadlines or relax real-descendant cleanup. Two regressions are added
to the existing primitives module. The private `findings.json` records the native
comparison and its exact evidence hashes. These focused diagnostic observations
establish the causes and candidate repair mechanisms. Installed candidate A
remains unchanged.

The first combined preflight ran **33 tests in 149.000 seconds**, with **one
failure, three fixture errors and one expected symlink-permission skip**. It
used the earlier replacement fixture, accounting for all three errors. The
remaining failure required a nested-child marker after a two-second worker
deadline. A separate native diagnostic confirmed that `TimeoutExpired` was
archived before the predictor reached that marker: the case was interrupted,
the retained root had exited, and no marker or live nested child was observed.
This did not establish a descendant-cleanup defect. The failed preflight and
its timeout diagnostic remain retained in `confirmed-combined-preflight-01.json` and
`confirmed-nested-timeout-diagnostic-01.json`.

The scientific regression now tests these two contracts separately. The
deadline case retains **two seconds** and requires the recorded plan limit,
interrupted state, `TimeoutExpired`, reaped root and closed ownership. The
successful nested-predictor case retains **15 seconds** and acknowledges the
predictor only after observing its child alive through a retained native handle
and confirming membership in the exact owned Job. That same handle must be
signaled after cleanup. No scientific deadline was extended, no PID-based
control was introduced and no timing-dependent skip was added.

The second combined preflight passed **34 tests in 174.221 seconds**, with
**zero failures, zero errors and one expected ordinary-user symlink-permission
skip**. It covered process ownership, installation locking, scientific
supervision, installer paths, directory handles and all eight file-snapshot
regressions. The controller was no longer running and returned **zero** at
**11:20:01.905048 UTC**. It verified the diagnostic source after execution and
reverified the unchanged installed candidate-A source and Python. The exact
record is `read-combined-preflight-02-final-20261023T111953Z-1e7d4d83/stdout.txt`.
This used candidate A's runtime with an isolated source copy declaring
`dirty: true`; it is **not installed candidate-A or candidate-C acceptance**.

The final required host check, `uv run --locked python scripts/check.py`,
passed **1,470 tests in 439.751 seconds, with 26 explicit macOS skips**, plus
lint, a format check of 645 files, metadata, navigation and strict Sphinx
checks. Its log is
`results/ot058-verification/full-gui/repository-check-native-workflow-final.log`,
SHA-256 `179290e2fe4a4d286136a8044f221458fc61171cc80caf5e9d18a8af5e3ce6a2`.
Neither this host check nor the separate-source Windows preflight substitutes
for retesting the corrected installed package.

## Candidate C and fresh Windows attempt

Candidate C was built from clean revision
`4c84773e6fd4c2f2d8f2792bfa7561c030b0b21c`, with build ID
`ot058-4c84773e6fd4-a80ac4dba2aa8c86`. It includes the native file-identity and
detached-process corrections and the updated regression tests. Its executable is
`OpenT1D-ot058-4c84773e6fd4-a80ac4dba2aa8c86-windows-x64.exe`:

- Size: **201,622,733 bytes**.
- SHA-256: `4b2c44fe103185ad8c1e694d1324109cf531884cb62b8badc2f2e0942d001ffb`.
- Package-manifest SHA-256:
  `8c105b0b089a808994c84bbae2905cbee7c0b20e493b8ca70e406c09a07cbfb0`.
- Source: **1,206 files**, with the exact tracked set and Git blob identities
  verified. Payload: **24,273 files / 773,589,845 bytes**, with every manifest
  hash and the complete file set verified and no symbolic or hard links.
- The **62/34/12** runtime distributions, runtime file hashes, dependency metadata
  and both pinned upstream revisions remain unchanged from the first candidate.

The executable, build result, manifest and independent audit are retained under
`results/ot058-delivery-windows-fix-c/`. The separate readonly `OT058FIXC` ISO
binds this exact executable and the new attempt-03 helpers; all **34 media
files** were verified after independent extraction. These are static artifact
checks, not Windows installation or reproducibility results. The curated host
checkpoint is
`results/ot058-verification/native-windows/attempt-02-checkpoint-v3/`;
it retains candidate A's failed native/MMTT outcomes and the successful
**dirty-source** 34-test preflight as separate evidence. Earlier candidate B
retains A's known faulty source and is not a corrected update successor.

After candidate A's actual GUI Exit, its evidence was exported before restoring
the baseline. The **559,332-byte** ZIP has SHA-256
`0d94b95f16bb2e27370d289503ef718c3e852c7ec9622f86dd04a971d6b57e29`.
The host validator checked the exact inventory and hashes of **164 evidence
members**, then extracted those files plus the export manifest. The bounded
credential/control exclusions and executable-content checks passed; no archive
code was executed. The private `attempt02-evidence-export.audit.json` records
this validation. This is a successful pre-restoration evidence export, not
post-uninstall verification or a claim of arbitrary secret detection.

Normal Windows shutdown returned zero and QEMU exited without a forced stop.
The completed attempt was preserved before restoring the baseline's disk,
UEFI variables and TPM state. All three restored components were hash-verified
and the preserved baseline remained unchanged; restoration completed at
**11:32:42 UTC**. The earlier attempt and its evidence were retained.

The fresh attempt-03 **Baseline passed at 11:39:54.987 UTC** as ordinary
`Researcher`, using a 64-bit AMD64 process and OS, with `human_sessions: 0`.
Its bounded checks again found no installed developer prerequisites, OpenT1D
installation or workspace. The controller exited **0** at **11:39:55.381 UTC**
and was stopped, as recorded in `confirmed-attempt03-baseline.json`. The guest
NIC remained disconnected for the application attempt. C's graphical Install
phase passed at **13:14:19.464 UTC**, with its controller stopped and exit zero
at **13:14:20.591 UTC**. The installed payload, registration and shortcuts passed
their bound checks. The default checked **Open OpenT1D** Finish option opened
Edge; its fresh browser setup was completed without an account, data import or
personalization. The actual OpenT1D Start page was observed.

The browser then completed **Consistent increase control** through Prepare
example, Validate and freeze plan, Run paired analysis and Check saved analysis.
The unchanged defaults used **128 uncertainty draws**, one synthetic pair,
two visits and all **3/3** required variant pairs. The recorded classification
was `consistent within investigated assumptions`. Reconstruction returned
`native_reader_verified` with unchanged report hashes:

- JSON: `55d4ac85150f5a21bd7ac82432f9ae6d6ceb248b9e369f2b0b4bc84b44785208`.
- Markdown: `26c9d43bb08073f5e47177bfca96598bfc09e743f390f958e6138a7c42c10f7d`.

Both jobs exited zero without forced cleanup, live root PID or remaining owned
processes. Clicking **Exit OpenT1D** and confirming its dialog removed the
session file, server and listener, verified at **13:57:19 UTC**. These are
actual agent-operated browser observations and synthetic software results,
not independent human or empirical acceptance.

C's installed Native phase failed: **34 tests in 325.421 seconds**, **one
failure, zero errors and one expected symlink-permission skip**. Only
`test_nested_predictor_stdin_and_live_descendant_are_owned` failed, because
its observer did not confirm live admission. That message alone does not
establish whether the 15-second bound elapsed or the worker exited early.
Its other ownership, deadline/archive, file-snapshot, installer-path and
directory tests passed. The controller stopped with exit **1** at
**13:28:19.333 UTC**. The original failed suite remains retained.

The subsequent Shortcuts phase confirmed that Start-menu and desktop launches
reused server PID **640**, but then failed the first M3 readiness operation.
Its controller stopped with exit **1** at **13:40:06.929 UTC**. The M3 log records
a **120-second** child check ending in `KeyboardInterrupt` inside repeated
ancestor `lstat` checks in `verify_packaged_project`; the job ended without
forced cleanup or surviving owned processes. No M3 calculation or successful
Shortcuts phase is claimed. Runtime audit optimization and a bounded diagnostic
of the unchanged nested test are separate follow-up work, recorded below.

The immutable selected checkpoint is
`results/ot058-verification/native-windows/attempt-03-checkpoint-01/`, manifest
SHA-256 `99459d40294eb005f00007dde662678d740f1b6e80a709922b2e47fa0f0fcc3b`,
cutoff **14:01:15 UTC**. It contains installation, browser, failure and shutdown
receipts plus selected screenshots, not a complete guest export. At that cutoff,
the normal MMTT case did not establish sampling or cancellation; the later partial
checks below add that evidence. M3/M4, campaigns, library, durable-reader and
lifecycle acceptance remain open.

**Candidate D** was built from documentation-only revision
`0b5e55662b6168771f9ab23dc3cfa7e57e800e5e`, build
`ot058-0b5e55662b61-441209e4e03e0910`. Its **201,623,731-byte** executable has
SHA-256 `4d301e48015d62ba66a8a9035f29a60baeddcef56ecf60d4136c4770454e0f4e`.
The independently audited artifact is under
`results/ot058-delivery-windows-fix-d/`. It preserves C's production/test/runtime
bytes and known outstanding failures. It has not been installed; no update,
feature version or public release is claimed.

## Nested ownership diagnostic and success-test correction

A separate instrumented run of C's unchanged nested test completed at
**14:11:10 UTC**; its controller stopped with exit **1** at **14:11:14 UTC**.
The test still failed. Its retained synthetic archive records `interrupted`,
execution-stage `TimeoutExpired`, and the original **15-second** plan. The
observer reached exactly 15 seconds without a descendant marker or acknowledgement;
the retained root then exited and its Job owner closed. The worker claim and
trace existed, but no worker-error or successful result existed. Before/after
source and interpreter audits matched C, and instrumentation reported no errors.
This identifies the observed deadline failure; it is an instrumented diagnostic,
not a successful repeat of the installed Native suite. Its receipt is
`confirmed-c-nested-diagnostic-01.json`, SHA-256
`a9fdf545983c2e6a30e0a872905308359051ef9c3285371fea9fc2d35712027e`.

The follow-up changes only the successful nested-ownership test to use
`run_study`'s existing **120-second default**, and asserts that the saved plan
records that same default. Its synthetic descendant now waits indefinitely,
so natural completion cannot falsely satisfy cleanup. The live retained handle,
Job membership, marker/acknowledgement, completed scientific result, root exit,
owner closure and signaled descendant-handle assertions remain required.
The separate two-second deadline test is byte-for-byte unchanged. No production
time limit is extended. The patch passed independent review, Ruff and the host
module's four portable tests; both native tests are skipped on macOS. Actual
Windows execution of the changed test remains pending.

## Runtime inventory follow-up

Candidate C's failed M3 check reached repeated absolute-ancestor metadata
lookups during its runtime audit. The development follow-up replaces that
per-file repetition with the existing safe `durable_archives.storage.inventory`
traversal. Windows directory handles pin ancestors; each invocation still
checks the complete file inventory, all file sizes/hashes, selectors, installed
distribution versions and upstream source metadata. Links, hardlinks, special
entries and changed file snapshots fail before the metadata subprocess. No
cross-invocation cache is introduced. The existing 30-second metadata and outer
GUI/scientific bounds remain unchanged; the reused inventory has its own
900-second bound. Setup and scientific source identities include the new
helper dependency; retained-reader fixtures include that same source closure.

An instrumented host-only comparison of C's root runtime counted **122,058**
resolver link checks before the change and **34** after it; the safe traversal's
own handle/descriptor checks still run. Host timing varies with system load and
does not establish a Windows speedup. The runtime's **7,151 files / 146,843,620
bytes** and both other runtime inventories matched their recorded hashes.
The host benchmark stubs the Windows metadata subprocess, which cannot execute
on macOS. It is algorithm and byte-inventory evidence only.

The affected host suite passed **78 tests in 64.151 seconds**, with three
Windows-directory tests explicitly skipped on macOS. After making the inventory
import local to admission, **33 focused tests** passed. Earlier failures from
an incomplete minimal reader fixture and unavailable sandbox process inspection
remain retained with the corrective rerun. The private host evidence is indexed
by `verification-summary.json`, SHA-256
`93081a237997550abdec570a61ff42b8d41a9a708dff5e6344a6847183b79035`.
The subsequent whole-repository run completed **1,477 tests in 520.194 seconds**,
with **one failure and 26 skips**: the existing historical-reader SIGTERM test
reported `failed` where it expected `interrupted`. Its log is retained as
`repository-check-runtime-inventory.log`; this is not a passing full check.
The unchanged failing method then passed 12 isolated repeats and its complete
nine-test module passed. The original temporary receipt was unavailable, so the
cause remains unproven. Only a bounded receipt summary was added to its failure
assertion; no behavior or deadline changed.

The complete stable rerun passed **1,477 tests in 508.601 seconds**, with
**26 explicit skips**, Ruff/formatting, repository metadata checks and the strict
Sphinx build. Its log is `repository-check-runtime-inventory-final.log`, SHA-256
`0cfb2485fa3b9441994c52e944ef1c60b93edd1488c5bc980844d8c95b1c854b`.
The separate private runtime prototype subsequently completed on actual Windows
at **14:52:24 UTC**; its controller exited zero at **14:52:25 UTC** and stopped.
It loaded only the reviewed runtime module under a private alias, explicitly
pointed every check at the unchanged installed C source, and used C's real
storage helpers and Windows interpreters. All three exact byte inventories and
metadata checks passed:

| Runtime | Files | Bytes | Admission seconds |
| --- | ---: | ---: | ---: |
| Root | 7,151 | 146,843,620 | 187.521 |
| Native | 9,953 | 346,744,218 | 187.752 |
| Observer | 5,932 | 260,087,984 | 105.316 |

The actual metadata subprocesses retained their 30-second bounds. Before/after
source, private interpreter, shared helpers and prototype checks matched. The
confirmation is `confirmed-runtime-admission-prototype-01.json`, SHA-256
`76e8370c7b2c68146282ab1144891fa68494dde8709e705b5af408ce03fdf949`.
These are single diagnostic observations under QEMU/TCG, not a general Windows
performance benchmark or a measured speedup against C. The root admission alone
exceeds the GUI M3 child check's 120-second bound, so this does **not** pass GUI
readiness or establish the correction is sufficient. Installed C and its failed
M3 phase remain unchanged. A further binding-only Windows API optimization is
being evaluated separately; no product deadline has been extended.

An earlier attempt to start the supplementary MMTT helper exited with Windows
access violation `c0000005` in `powershell.exe` at **14:25:20 UTC**, before its
controller or application processes were created. Bounded follow-up inspection
found no matching control/evidence directory or Python process. The Windows
event records an unknown fault module; the cause is unproven. Later staging and
runtime diagnostic calls passed. The failed invocation is retained separately
and is not counted as an OpenT1D workflow test.

A subsequent, separately controlled API-driven run against unchanged installed C
passed **MMTT sensitivity, sampling and controlled cancellation** in three isolated
workspaces. Each case reused its session on repeated launch, restarted, and
reconstructed the exact original JSON and Markdown report bytes. Normal jobs
completed; the cancelled sampling job retained its interrupted report. All jobs
reported no forced cleanup or remaining owned processes, and all six shutdowns
returned zero with no owned server left running. The controller stopped with
exit **0**, without timeout, at **15:08:42.373 UTC**. Before/after audits verified
C's exact **1,206-file source inventory** and private root executable; the full
dependency payload was not rehashed. No production deadline changed. The receipt
is `poll-c-partial-mmtt-03-20261023T151357Z-51d9ef4f/stdout.txt`, SHA-256
`7de7c249875638f0cbb87b17db863079b4e4dfc9c85248eed49617b82692253f`.
This is partial synthetic API evidence, separate from the earlier browser run;
it did not execute M3, M4, campaigns, library, durable-store, installer-lifecycle
or native-suite checks. C's failed Native and Shortcuts phases remain failed,
and neither FullSmoke nor all-route Windows acceptance is claimed.

The separate Win32 binding microprobe completed on actual Windows at
**15:28:38.228 UTC**, with controller exit **0**, no timeout and no remaining
controller. The exact baseline and proposed files were measured in balanced
order over two rounds. Fresh file reads, same-size/restored-mtime mutation
recognition, directory pinning and junction refusal passed for both variants.
Four simultaneous cold callers retained distinct live handles and buffers,
observed independent ctypes errors **6, 6, 80, 80**, and closed every owned handle.
All selected C interpreter/module and private-source identities matched before
and after; synthetic files were removed. The confirmation is
`confirmed-win32-bindings-02.json`, SHA-256
`703787fc0c2fa26c41cbca284d475dbc454045b6e465189d96c87378f8890d70`. This small synthetic probe does not
measure complete runtimes, GUI readiness or a general Windows speedup.

The first microprobe invocation stopped before its measurement because its
helper expected an explicitly empty `PATH`. Native inspection confirmed all
requested Python isolation flags and an **absent** `PATH`: PowerShell 5.1 removes
an environment variable assigned an empty string. A new, separately preserved
helper accepts absent or empty `PATH`; twelve host fixtures and independent
review preceded the successful native run. The original failure remains
recorded. No application deadline was changed for either invocation.

The exact binding-only production change and four focused regression cases are
now applied in the implementation worktree. The three targeted host modules
passed **33 tests**, with **9 actual-Windows-only skips**, and Ruff/style checks
passed. The combined private runtime measurement subsequently passed all three
complete byte inventories and actual metadata subprocesses. Its controller
stopped with exit **0**, without timeout, at **15:42:26.164 UTC**; exact installed
C source/interpreter and private-source identities matched before/after.

| Runtime | Admission seconds | Full inventory seconds | Actual metadata seconds |
| --- | ---: | ---: | ---: |
| Root | 148.412 | 141.189 | 6.532 |
| Native | 169.971 | 161.493 | 7.989 |
| Observer | 107.688 | 102.239 | 5.051 |

The real metadata limits remained **30 seconds**. These individual prototype
admissions exceed the old M3 root **120-second** check and M4's combined
**30-second** check allowance; no complete GUI readiness operation ran in this
helper. These are emulated observations with uncontrolled caches/scheduling,
not a native-PC benchmark or a general speedup claim. Confirmation:
`confirmed-runtime-admission-prototype-02.json`, SHA-256
`3451929195718ac6ef449d3a2516f4358b1549b388e830efd6f905ed25c96ad5`.
This is uninstalled development code, not a correction retroactively applied
to C. The original M4 metadata-oriented envelope predates the added complete
integrity check of **23,036 files / 753,675,822 bytes**. A separate bounded
installation-integrity phase is being evaluated; no deadline has yet changed.

The subsequent **actual installed-C whole M4 readiness check failed** at its
unchanged **30-second** command ceiling. It ran from the ordinary desktop API
with a newly frozen fasting configuration, observed **30.610 seconds**, and
stopped inside `hashlib.file_digest` while auditing installed files. The job
returned **3221225786**, retained readiness **false**, and left no owned
processes or forced cleanup. Authenticated desktop shutdown returned zero;
source/root-interpreter identities matched before and after. Its separate
controller stopped with exit **1**, without timeout, at **16:04:57.607 UTC**.
No installation or model run occurred. Confirmation:
`confirmed-c-m4-check-failed-01.json`, SHA-256
`37e62e9d1f97651eae7e87b4f66063c0a8e0b4ad01763c99daf975394dbb74c8`.
This independently confirms that complete installation integrity needs its own
bounded phase; it does not convert the original failed check into a pass.

A private 50-case regression invocation stopped **before any tests** because
its staging helper rejected the installed interpreter path. Its controller
stopped at **16:08:44.229 UTC**, exit **1**, with the child exited and no timeout.
No application or test failure is inferred from that helper failure. The
original frozen helper and its receipt remain preserved:
`confirmed-native50-staging-failed-01.json`, SHA-256
`344ba2d26cae625b9f784ceca03b21ff3eeaed38f248506ec03c85e0bc269694`.
A separately versioned preflight is being prepared; no native retest pass is
claimed yet.

The first unchanged-C setup diagnostic stopped before creating a plan, inside
selector-path inspection (`OSError`, `core.selectors` → `regular` → `is_link`).
It therefore **did not reproduce the suspected report-newline mismatch**.
Source/root-interpreter identities matched before and after; its controller
stopped at **16:15:48.493 UTC**, exit **1**, without timeout. Confirmation:
`confirmed-c-setup-plan-early-failed-01.json`, SHA-256
`5d7cddd974fd84c65c5f68993d65cb2677d46d0cea7bed6773e33efb167bb011`.

A separately preserved second diagnostic **created an actual installed-C setup
plan and attempted to load it**, reproducing the report mismatch: the written report had **915 bytes
with CRLF**, while the canonical UTF-8/LF renderer produced **902 bytes**. Loading
failed with `Setup plan report differs`; no installation or model run started.
It also measured both native/observer selector paths: extended paths containing
`..` failed with **errno 22 / WinError 123**, while ordinary paths and normalized
extended paths resolved successfully. Installed source/root-interpreter identities
matched before and after. Controller **3352** stopped with exit **1**, without
timeout, at **16:38:10.601 UTC**. Confirmation:
`confirmed-c-setup-plan-crlf-failed-02.json`, SHA-256
`8fa0ad3eaa8b25908d595db913e70fcb3a245e4078b4c7b9cc48e61e4abcf1a1`.
The first diagnostic's earlier failure remains recorded separately.

The receipt, exact support-15 media metadata and v2 helper manifest are retained
in the immutable selected checkpoint
`results/ot058-verification/native-windows/attempt-03-checkpoint-05/`, manifest
SHA-256 `b9e0989b78fabc47164dd7d48e2267772310b44a9146e107912b25bfb7763351`.
The reviewed selector normalization and canonical report writer are development
corrections; this failed unchanged-C diagnostic does not establish their native
acceptance.

The reviewed development follow-up now separates packaged integrity from native
operation clocks as specified in decision 0070. Complete runtime audits and
metadata checks remain fresh. One owner preserves cancellation across phases;
GUI shutdown allows that owner's bounded cleanup, and a cancelled packaged M3
run starts no new automatic audit/reader. The report writer now emits canonical
UTF-8/LF bytes. These are worktree corrections, not installed-C test passes.
The core/workflow/durable-reader selection passed **49 tests in 24.086 seconds**;
the GUI/M3/backend/setup selection passed **39 tests in 14.769 seconds**. The
latter includes real native archive creation, cancellation before automatic
reconstruction, retained unverified bytes and a later explicit reader. The
subsequent native preflight failed as recorded below.

## Candidate E build and failed native preflight

Candidate E was built from clean source
`c897c6ac0c1023e1f6ef16927bfab341cc99f2fa`, with build identity
`ot058-c897c6ac0c10-3af763bd1d1712cf`. The installer has **201,656,995 bytes**,
SHA-256 `4a053ed0d803508a037aca33b6777866e814d91ca4404eb963af5f833cc254d7`;
the package-manifest SHA-256 is
`94744a71cf3df0473ddaa8490a5eea15940bb177894e3836c6e513099a05273e`.
Its build and static payload audit are retained under
`results/ot058-delivery-windows-fix-e/`. **E has not been installed.**
The full macOS repository check passed **1,511 tests in 441.403 seconds**, with
**27 explicit skips**, before the clean commit; the checked source bytes matched
the committed build inputs. Log:
`results/ot058-verification/full-gui/repository-check-packaged-phases-03.log`,
SHA-256 `ae5e3f4a3fdf07bc7c348f7cb436a087590fb754176665dbd0afd5424f4d977b`.

The Windows preflight used an **isolated, explicitly modified source copy** and
installed C's private interpreter. It ran **84 tests in 257.594 seconds**, with
**one failure, no errors and four skips**. The failure was the preparation-phase
assertion in `WorkerPipeTests.test_private_cancel_seals_a_reconstructible_interrupted_analysis`;
its original observed phase was `None`, which does not identify the active
subphase. Separately, the helper rejected two symbolic-link permission skips
because their actual unittest subtest IDs differed from its expected parent ID.
The original failed receipt remains unchanged. Controller **1896** stopped with
exit **1**, without timeout, at **17:09:10.927 UTC**; the copied source and installed
C source/interpreter identities matched after execution. Confirmation:
`confirmed-native84-failed-01.json`, SHA-256
`ef5a2bd7417e36ea481a96be1bbdb93afdfae46f8c9fa239052e4f9672240fd4`.

A separately preserved repeat of the unchanged failing test ran **one test in
14.000 seconds**, with **one failure and no errors**. At the original **10-second**
preparation assertion, its retained worker was alive and the recorded phase was
`snapshot`. The test **never reached its CANCEL request**. Its original cleanup
then terminated the worker; the subsequently captured streams were empty.
Diagnostic instrumentation added no signal or kill. The exact snapshot copy/revalidation
subphase remains unknown, and this evidence does not establish a cancellation
bug. Controller **7544** stopped with exit **1**, without timeout, at
**17:29:33.623 UTC**; source and C's interpreter were unchanged. Confirmation:
`confirmed-native84-pipe-failed-01.json`, SHA-256
`805f91c72a748ee8a239ae2d98ee25bc4bb66a306b5a52f51c0838eeca159191`.
These are failed native diagnostics, not installed-E acceptance or successful
M3/M4 workflow/lifecycle checks. The reviewed follow-up changes only this test's
preparation observation from **10 to 30 seconds**, matching the existing smoke
observer. Its 1,024 draws, private CANCEL request, 10-second cleanup waits, SIGINT
and reconstruction assertions remain unchanged; no production clock changes.
The three existing host cases passed in **0.199 seconds**, with an independent
repeat passing in **0.230 seconds**, and Ruff passed. The installed candidate-F
retest below supersedes the pending status without changing these failed receipts.

## Candidate F: update and native pass, retained workflow failures

Candidate F was built from clean source
`e4ffb09276989f29199f4e8949f6a9ea45627f69`, with identity
`ot058-e4ffb0927698-dc2883c2560c8dc5`. Its installer has **201,658,649 bytes**,
SHA-256 `dcb9dd022a0df0ce250f665ddcb32320cc2a4b9c6681952fe035a75d7e523fe4`;
manifest SHA-256
`0470b7563b666c8b9dfe133ee1afb5e489e64346f95e040b27460d2b294634f3`.
The payload contains **24,279 files / 773,718,528 bytes**, with 1,212 source
files and the unchanged 62/34/12 distribution inventories. Build/static evidence:
`results/ot058-delivery-windows-fix-f/`. The full locked host check passed
**1,511 tests in 427.581 seconds**, with **27 explicit skips**, plus repository
and strict documentation checks (451.603 seconds total). Its log is
`results/ot058-verification/full-gui/repository-check-pipe-observation-01.log`,
SHA-256 `2870d5d524c5f40fc78adf2f0bdc1b292d77975982c2d875528fb1541a30c9a4`.

The ordinary-user graphical **C-to-F update passed**, with its controller stopped
at **19:21:05.067 UTC**. All 130 original saved files remained unchanged, the C
payload was retained, and its reader reconstructed the original MMTT reports
with identical bytes. F's default Finish launch and shortcut start/stop passed;
full payload audits and the frozen C acceptance history matched. This is an
update result, not a fresh-F baseline or maintenance during active numerical work.
Checkpoint04 manifest SHA-256:
`421ce3bb16557b392a88b8c8b356e2ff818c836331d0e0c8393dab958928c54e`.

F's complete installed **Native** phase then passed: **84 tests in 355.997 seconds,
no failures or errors, four exact allowed skip entries**. These comprise one
symbolic-link permission test, two permission-dependent subtests and one
POSIX-only signal/process-group case; they are not four separate skipped test
methods. The live cancellation/reconstruction test passed. Both full payload
audits matched and the controller stopped at **19:43:45.866 UTC**, exit 0.
Checkpoint05 manifest SHA-256:
`ad03b54a34eab418008c42772fadfbea28e840f25c5a7da4a3ec34f53f89c200`.

The first **Shortcuts** phase reused one server but failed at the first M3 fixture.
The outer 120-second deadline cancelled its owned worker without forced cleanup
or survivors; the nested traceback ended during namespace import, before model
execution. A concurrent read-only observer may have added load, but causality is
not established. The original failed phase and normal GUI shutdown are retained
in checkpoint06, manifest SHA-256
`53c813a3e58627c93f21edc5e9957bbc92455f43b7035196c78712f36407c02d`.
A separate, import-only diagnostic completed fresh GUI-worker and comparison
imports in **5.104 and 5.442 seconds**, with empty owned Jobs and unchanged selected
sources. These independent imports do not establish a nested workflow pass.
Checkpoint07 manifest SHA-256:
`1112b8ba075ed7e54cefccdae9f55e93c53581cc8f194eea00bbf4b619e2af11`.

One controlled **unchanged-F retry** preserved the first failure and all original
limits, with no additional PowerShell observer during startup. Both shortcuts
again reused one server. The trace proves that fixture preparation, intake,
repeat inspection and configuration creation advanced to the first forecast
readiness check. That check failed after **23.770 seconds**, with **WinError 5**
while replacing `m3-check-phase.json.pending` with `m3-check-phase.json`. This
was not a deadline failure: no interruption, forced cleanup or remaining owned
processes was recorded. The retry controller stopped at **20:35:38.672 UTC**,
exit 1. Normal GUI exit removed its session and server, and its listener refused
connections. Checkpoint08 manifest SHA-256:
`6694c8c83e9edd8dbe425f918294df91f1a69fc89651a828d16827d77a4abecc`.
All checkpoints are under `results/ot058-verification/native-windows/`.

A bounded diagnostic on **unchanged installed F** then reproduced the same
`PermissionError` / `WinError 5` by holding the actual regular-file reader open
during `PhaseState.update`. The old reader retained its original bytes; updating
and reading the new record succeeded after closing that handle, with no pending
file left. The interpreter and three selected source files matched before/after.
This establishes the missing concurrent-reader contract, not which specific
handle overlapped the original job. The subsequent correction and its tests
retain the existing scientific, admission and cleanup budgets. Full GUI
execution/readers and the remaining lifecycle sequence have not passed for F.

The correction publishes Windows phase records through a verified owned file
handle using `SetFileInformationByHandle` / `FileRenameInfoEx` with replacement
and POSIX semantics. Existing readers retain the old record while new readers
open the replacement. Pending-file identity, bounded contents, single-link and
ancestor checks remain in force; only immutable API bindings are cached.
The [Windows filename contract](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)
informs the UTF-16 buffer and counted filename length.

The first private modified-source Windows preflight failed: **five tests, no
failures, three errors, no skips**. Two initial publications reported WinError
123 and a post-publication identity check rejected another result. Its filename
buffer omitted a trailing UTF-16 NUL; that defect was corrected without changing
paths, guards or clocks. The owned test process exited 1, although its first
outer PowerShell wrapper returned 0; the recorded test result governs the
failure. The fresh second preflight, with explicit exit-code propagation,
passed **all five tests with no errors, failures or skips**. Its owned process
stopped at **21:07:09.883 UTC**, exit 0, without timeout. It exercises real open
readers, a paused public GUI reader, long non-BMP Unicode paths, pending-file
substitution/hardlinks and the existing telemetry/authority guards. Selected
installed-F sources remained unchanged. The test log SHA-256 is
`1dfd15c8688fe69383a1ff7ae2afd25532c3fcffd322f7cfa841db4691f54dce`.
This is targeted native proof using a private source overlay, not an installed
successor or full-workflow acceptance result; both preflight attempts remain
separately preserved. Checkpoint10 contains both attempts; its manifest SHA-256
is `04c5bb0556fbd2259eab9ea91786b8787ee393d757918ed2d432cca9dbf74abd`.

The first full host check after this correction ran **1,514 tests in 429.255
seconds**, with **28 skips and one error**. The existing live-descendant
cancellation test received macOS `PermissionError` from `os.killpg`; the new
phase tests passed. An unchanged targeted repeat passed in **0.075 seconds**.
The original error remains in
`results/ot058-verification/full-gui/repository-check-phase-publication-01.log`
(SHA-256 `b9a715f4a28eb82081543fa52a260ba7037fdeaea604408117edc92fadd95b6f`);
its cause is not established by the passing repeat. A second full locked check,
with no executable or test changes, passed **1,514 tests in 434.947 seconds**,
with **28 explicit skips**, followed by strict documentation checks. Its log is
`results/ot058-verification/full-gui/repository-check-phase-publication-02.log`,
SHA-256 `6089e0badd018e62fe73acd01b0ff1f4fe7246a62ecfe211bf0a583f6e90da31`.
These are measured test-process durations. Recorded wall timestamps differ from
the monotonic elapsed measurement and must not be treated as uninterrupted
execution times.

## Candidate G: update/native pass and comparison publication failure

On 24 October, clean source `9fe00f84fc5f584a1eefda668c5616eb9ea97abe`
produced candidate `ot058-9fe00f84fc5f-6f461e1c7376662b`. The installer is
201,664,643 bytes, SHA-256
`85a7351e25fde16f8779e877e6a17e8b82cfbf3845cfd66a2bfc3ee0cdc3366a`;
package-manifest SHA-256
`b380942a480216faaf3c866d9840cd8a35236068a8e24a93c86554eacad10105`.
The payload has 24,279 files / 773,740,724 bytes, including 1,212 source files.
All runtime files match F; distribution inventories remain 62/34/12.
Build/static evidence is in `results/ot058-delivery-windows-fix-g/`.

The ordinary-user offline **F-to-G graphical update passed**. All 176 original
saved files remained unchanged; full F/C/G payload audits passed. The default
Finish action opened the browser. The retained C reader reconstructed its
original MMTT reports with identical bytes; G's shortcut startup and normal
shutdown passed. This establishes update continuity, not a new clean-G baseline
or maintenance during an active calculation. Fourteen previously prepared C/F
history identities were checked unchanged by the frozen harness.

The complete installed **Native** phase passed **87 tests in 244.354 seconds**,
with **no failures or errors and four exact allowed skip entries**. The allowed
entries retain the F definitions, including two subtests; they are not four
separate skipped methods. Both full G payload audits passed. This includes the
three new phase-publication methods under actual Windows, not a source overlay.

The following **Shortcuts** phase failed. Start-menu and desktop launches reused
server 8464. Job `job-79e3c177e7754470a4cbf12b2d0c7d82` failed with exit code 1
while running the M3 comparison. Both candidate children finished with exit
code zero, empty stderr and normal completion messages. The parent archive has
`state.json` with status `started` and `state.json.tmp` with status `finished`,
both recording the two finished children. No parent manifest or report was
published. No cancellation, forced cleanup or surviving owned process was
recorded. The original parent exception was not captured by the dispatch
wrapper; the raw archive remains forensic evidence, not a verified result.
Normal GUI Exit subsequently removed the server, listener and session file.

A separate private synthetic probe using G's actual installed interpreter and
three hash-checked source modules reproduced the shared `m3.common.save` /
`recording.atomic_text` failure. An `open_regular` reader held the destination
open: publication raised `PermissionError / WinError 5`, the old bytes remained
readable, and the pending file contained the finished state. Closing that reader
made the same save succeed. The probe changed only fresh temporary synthetic
files. It establishes the reproducible writer/reader incompatibility without
identifying which handle overlapped the original failed comparison.
Its exact 244-byte stdout has SHA-256
`fb5d9915b52760549b81a2873bbe6f41b41b37afea23be8e9397976cedead23b`;
the serial receipt reports exit zero, no timeout and empty stderr.

Immutable evidence under `results/ot058-verification/native-windows/`:

| Checkpoint | Scope | Manifest SHA-256 |
| --- | --- | --- |
| `attempt-05-checkpoint-03` | Closed update, original records and history checks | `2ab120e1eade54b9f12082fab667d3a82e3db2ed4b5c86012644ce9edd727fbe` |
| `attempt-05-checkpoint-04` | Installed native pass and original logs | `5e590c543be5d294510a390df2571792587d58016505e7b28fac035621e7d9f3` |
| `attempt-05-checkpoint-05` | Failed comparison, original states/logs and normal shutdown | `b523108aa44b06951a39ad6ce5f0782bda8b8833c6eeebbcad25d443a6be69ce` |
| `attempt-05-checkpoint-06` | Fresh synthetic held-reader reproduction using installed G | `b6c42b457316a411dac94f9bf83630def02778b36e3ba44f92fd6f8bf0c1e47e` |

G's full smoke, completed browser walkthrough, repair/reinstallation/removal and
post-uninstall reader sequence have not run. The earlier F/G failures are not
superseded by a diagnostic pass. No scientific, fixture, reader, cleanup or
installer deadline was increased for these tests. Host/guest clock discontinuities
prevent inferring uninterrupted elapsed time from wall timestamps; the native
test duration above is its reported test-process measurement.

## Shared publication correction: targeted Windows proof

The correction extends the native handle-based publication contract to the
shared scientific and GUI writers. Five new tests cover a held regular-file
reader on a long non-BMP path, text/byte compatibility, stale pending files,
linked-target refusal, failure preservation and handle cleanup. Native research
writers retain their fixed pending names; GUI writers use fresh owned siblings.
Existing admission guards and all operation deadlines remain unchanged.

A private modified-source preflight on the same Windows VM passed **eight tests
in 2.058 seconds**, with **zero failures, errors or skips**. It included the five
new methods and three existing phase-publication methods. The retained Python
process exited zero and stopped; 114 selected installed-G support files and the
five private overlays matched before/after. This is targeted native proof, not
an installed successor, full payload audit or whole-process-tree audit.
`attempt-05-checkpoint-07` preserves the original logs and receipts; its manifest
SHA-256 is `b48172bab224ba2732e6292b271bc02de9f1a531f3800429e75bab2df4fa53c8`.

The first full host check ran **1,519 tests in 444.924 seconds**, with **30 skips
and one error**. The unchanged live-descendant cancellation test again received
macOS `PermissionError` from `os.killpg`, both in the liveness check and cleanup.
The executable/test inventory remained unchanged. The failed log is
`results/ot058-verification/full-gui/repository-check-generic-publication-01.log`,
SHA-256 `bc5ddfe1d7a4896b1046909e6f3c05521a1cded02e5ced41076b3284ee6d3bea`.
A bounded diagnostic repeated that exact test ten times with its original
120-second contract; all passed. Its wrapper would collect bounded process-group
metadata only after EPERM and re-raise the original error. No EPERM occurred, so
no such metadata was collected. The original cause remains unexplained; these
repetitions do not replace the full repository check. Diagnostic manifest
SHA-256: `a4bee6dda32bddc5f999a6817432f0cb7d9909b6e429648ededaeb39bcb8f37a`.

One explicit second full check, without executable or test changes, passed
**1,519 tests in 425.929 seconds**, with **30 explicit skips**, followed by strict
documentation checks. The earlier macOS process error remains unexplained and
preserved. The passing log is
`results/ot058-verification/full-gui/repository-check-generic-publication-02.log`,
SHA-256 `5bfca0e355abdf9287cc8e1594c3a47ecf0f0065b0641c3986f8ecbf86ab60d9`.
This is host verification, separate from the installed H results below.

## Candidate H: update/native passes and workflow deadline failures

Clean source `4c9fcf2a03c60a8dbef0b12b8deb876973e49b7e` produced
`ot058-4c9fcf2a03c6-4cf03bc468e4e0c5`. The installer is 201,671,771 bytes,
SHA-256 `7d6821e2b17107cc52f4566d362705b919fd8bafdbf98b210966192fa21a16cb`;
package-manifest SHA-256
`e39c15a374d94ccb21ddb6ec37ad72769c0364ca88e8079490b0e91570a6ec2b`.
The independent static audit verified 24,279 payload files / 773,769,716 bytes,
including 1,212 source files. Runtime bytes and the locked 62/34/12 distribution
inventories remain unchanged. Build evidence is in
`results/ot058-delivery-windows-fix-h/`.

**PrepareUpdateFromG and the complete graphical G-to-H update passed** under
ordinary AMD64 user Researcher. Preparation bound 22 historical file identities;
all 343 saved files remained unchanged after installation, with zero additions.
Six full payload audits verified G, retained C and H, including C after its
original MMTT report was reconstructed with identical bytes. H's default Finish
action opened the normal Start page; shortcut startup and maintenance shutdown
also passed. Controller 1856 stopped with exit zero. The stopped older G tab's
“Failed to fetch” message is separate from the successfully opened H page.
This verifies an update from G and an explicit C reader, not a clean H baseline,
G reconstruction of C archives, interactive GUI Exit or active numerical work
during maintenance.

The complete installed **Native** phase passed **92 tests in 238.676 seconds**,
with **no failures or errors and four exact allowed skip entries**, including
two subtests. All nine required modules ran; both full H payload audits passed.
This includes the five new shared-publication methods and existing phase,
process, runtime and setup regressions using the installed H sources.
Controller 7424 stopped with exit zero; the phase completed at **16:00:04.295 UTC**
and controller completion was recorded at **16:00:06.160 UTC**. The test-process
duration is taken from the original log, not inferred from wall timestamps.
Native stderr SHA-256: `1140ce888250d01b5960dd78a2dd5d1f6e9d3efc8ddfbf655e76d34791ada4c3`.

**Shortcuts failed** its unchanged 2,820-second aggregate `workspace-cases` wait;
controller 5824 stopped with exit 1. The workspace child's later result separately
records `Desktop operation exceeded smoke-test deadline` during its unchanged
900-second durable-export observation. The durable job itself failed with
`Operation deadline exceeded` under its original 900-second command limit.
Its log ends with `KeyboardInterrupt` in the final `reader.checkout_identity`
call, while checking the installed reader runtime inventory. It records no user
cancellation request, no forced cleanup and no remaining owned processes;
`worker-result.json` is absent. This does not establish a completed archive.
The workspace child was absent at **17:06:27 UTC**, but its process exit code
was not captured. The prepared passive observer was never executed.

Both H M3 forecast and comparison checks, runs and explicit readers recorded
completion with exit zero before the export failure. They are partial workflow
results, not a Shortcuts pass. In this Windows x64 VM under QEMU TCG, the final
reader integrity check did not finish within the durable-export command limit.
Complete workflow usability within the existing limits is therefore unverified.
The evidence does not isolate TCG as the cause or establish performance on
physical Windows x64 hardware. All original limits and failed receipts remain
unchanged.

A later normal **GUI Exit** was clicked and separately verified at
**17:11:47.730 UTC**: session absent, TCP connection refused and server PID 3032
absent. No server exit code was available. The read-only receipt SHA-256 is
`4bd617e7cf26fb203a2fb4953fea8e97b26bdfb39f022e119cc020f0a807e6da`.
This closure check is separate from the earlier update's maintenance stop.

**The separate FullSmoke run failed** after nine completed jobs, including both
M3 runs/readers and M4 installation/readiness. Its first M4 run exited 1;
controller 2940 stopped with exit 1 at **18:14:45.852 UTC**, after phase completion
at **18:14:44.041 UTC**. The original smoke evidence records a clean authenticated
API shutdown with return code zero. Its `actual_windows_execution: false` field
is preserved: the failed smoke did not reach its success assignment. The bound
acceptance phase and runtime/platform records establish that this was actual
installed Windows execution, without turning the failed result into a pass.

M4's archived state records `WorkerDeadline` in the historical reference at its
unchanged **600-second** limit. The nested reference manifest records
`GlobalInterruption`; the native worker log ends with `KeyboardInterrupt` while
importing NumPy through `numpy.core._multiarray_umath`. Both supplied source
evaluations remained `not_attempted`: **0/2** source/load cases and **0/1** pairs
were accepted. The GUI job recorded no user cancellation, forced cleanup or
remaining owned processes. Runtime attestation had already been written. The
stack locates the interruption during import; it does not establish why the
historical reference exceeded its deadline or how that time was distributed,
and does not isolate TCG as the cause. No supplied-source comparison ran and no
deadline was changed. Campaign, both MMTT routes, cancellation and the report
library were not reached by this FullSmoke attempt;
any supplementary checks require separate results and cannot replace its failure.

Two later GUI **Retain raw evidence** actions passed separate byte-preservation
checks: forecast **43 files / 1,781,010 bytes**, comparison **85 files / 3,200,740
bytes**, with original source trees unchanged. Their receipts retain
`integrity_verified: false`, `reconstruction_verified: false` and `complete: null`;
these raw copies do not establish fresh native reconstruction, scientific
completeness or a successful durable export. All four before/after collectors
closed with exit zero and no live child. A subsequent normal GUI Exit was
confirmed at **18:41:13.198 UTC**: session absent, TCP connection refused and
server PID 6848 absent; no server exit code was available. Original FullSmoke,
Shortcuts and durable-export failures remain unchanged.

Four later, separately selected **API-driven checks passed within partial scope**
on unchanged installed H, each in a fresh workspace:

| Supplemental case | Confirmed scope |
| --- | --- |
| MMTT sensitivity | The supplied increase example completed with 32 uncertainty draws and the expected synthetic classification; native reconstruction preserved JSON/Markdown bytes before and after desktop restart. |
| MMTT sampling | The information-loss example completed with 32 draws, all 60 planned variant pairs and the expected three direction reversals; native reconstruction preserved both report files before and after restart. |
| Cancellation | The 1,024-draw sampling run was cancelled after native analysis was observed. Its job retained the expected cancelled state/exit 1 and incomplete interrupted report; native reconstruction and restart preserved the report bytes. |
| M5 report library | An earlier synthetic archive was indexed, verified, hidden/shown and reopened after restart with unchanged report bytes. This is report-only use; no new M5 model study ran. |

All four controllers and their retained children closed with exit zero, no
observation timeout or child left for inspection. Their jobs recorded no forced
cleanup or remaining owned processes; both desktop shutdowns per case were
clean. Each check reverified all 1,212 installed source files and the private root
interpreter before and after, without claiming a new full dependency audit.
The original scientific and individual observation limits were unchanged. These
API results are separate from a browser walkthrough or independent user session
and do not replace the failed FullSmoke, Shortcuts or durable-export outcomes.

**The separately selected campaign check failed.** Installation and readiness
completed, but its run job exited 1 and accepted **0/2 slots and 0/4
source/scenario evaluations**. Both slot archives record `WorkerDeadline` in
the historical-reference stage at the unchanged **600-second** limit; both logs
end with `KeyboardInterrupt` during NumPy import. Supplied sources remained
unattempted. The case ended before the controlled cancellation point, so this
was not a cancellation-point observation timeout; cancellation and resume were
not reached. There was no user cancellation, forced cleanup or surviving owned
process. The controller and retained child both closed with exit 1, without an
outer timeout, and the owned desktop stopped cleanly. Installed source and the
private root interpreter remained unchanged. As with the FullSmoke failure, the
interrupted stack does not explain the time distribution or establish a TCG-only
cause. The four successful supplemental cases above remain separate results.

**Separate lifecycle Prepare and Reinstall passed.** Reinstallation began with
the desktop running, without an active numerical-job claim. The complete H payload
was verified; all **668** original saved files were unchanged with **zero additions**,
and the previous installation directory was retained. Subsequent fresh reader jobs
reconstructed the two H M3 reports through H and the original MMTT report through C.
All three completed with exit zero, no forced cleanup or remaining owned processes.

**The original Repair phase failed its strict data comparison.** The deliberately
damaged runtime was replaced with the exact **24,279-file / 773,769,716-byte** H
payload, and default browser startup was observed. A later read-only comparison
found **687 of 689 files unchanged**, **two changed**, **zero missing** and **zero
added**. The changed files were the last C MMTT reconstruction's job journal and
observation record: only `verification` changed from `native_reader_verified` to
`recorded_verification`. Reversing that single value in each retrieved current
file exactly reproduced its prior inventory SHA-256 and byte count. The original
before-file bodies were not separately retrieved, and reconstructed bytes are not
presented as originals. This matches H's startup normalization in
`Service.load_journals` and `Observations.__init__`; it does not prove installer-only
causality or turn the failed phase into a pass. Its six subsequent launch/reader
proofs were not reached.

**Uninstall passed.** Its closed phase confirms removal of Windows app registration
and the main shortcuts while retaining the H/C reader shortcuts. All **689** saved
files were unchanged with **zero additions**. Full retained-reader audits passed
for H (**24,279 files / 773,769,716 bytes**) and C (**24,273 files / 773,589,845 bytes**).
The original before-uninstall inventory was retrieved and hashed, alongside the
closed phase and verification records.

**SavedReader after uninstall also passed.** The retained H reader freshly
reconstructed both H M3 reports, and the retained C reader reconstructed its
original MMTT report, with unchanged report bytes. All three jobs completed with
exit zero, no forced cleanup and no remaining owned processes. Full H/C payload
audits passed again. These are API-driven reader checks through the retained
installations, without model reruns or an independent user claim. The original
closed records and final idle observations are retained in checkpoint14 below.

**The separate import-only diagnostic passed.** The exact H native interpreter
emitted all eight ordered markers while importing NumPy 1.26.4, SciPy 1.13.1 and
`experiments.m4.feedback.worker`. Controller and child exited zero in
**110.533083 seconds**, within the unchanged 600-second observation allowance,
with no timeout or cleanup and the selected file bytes unchanged before/after.
The retained 792-byte stderr contains three upstream Gym `SyntaxWarning` messages
about invalid escape sequences, not an import error. This establishes loadability
in that diagnostic only: it did not execute a model or recreate the original
worker's Job/control path, startup work or cold-cache conditions, and does not
explain the earlier M4/campaign deadlines. All those failures remain unchanged.
Diagnostic01 was never executed; the twelve pure helper fixtures are separate
from this actual import measurement and from application acceptance.

Immutable checkpoints under `results/ot058-verification/native-windows/`:

| Checkpoint | Confirmed scope | Manifest SHA-256 |
| --- | --- | --- |
| `attempt-06-checkpoint-01` | H source, static build/audit and prepared harness/media | `dd5d398a21b588fd9baa7f9c3d96e1e1a15fd0526094b7a824af139a7ac27521` |
| `attempt-06-checkpoint-02` | Closed preparation and original data/history bindings | `78b4fa6e871e235b01e8551de14f3873f67ac448d66640158742a7c1d5a4aace` |
| `attempt-06-checkpoint-03` | Closed graphical update, saved-data continuity, retained C reconstruction and H startup/maintenance stop | `1032b532ba98b9cdc8c5419bd2eb4569fc06258ff453ee4d2dc848c939ff16cb` |
| `attempt-06-checkpoint-04` | Closed installed Native92 phase, original logs and payload audits | `1c6cd0865c8aa50b6048ecb3316ce92fb44365a15594a72b32d9fc8959fc7788` |
| `attempt-06-checkpoint-05` | Failed aggregate Shortcuts wait, passed shortcut/pre-audit subchecks and separately labeled progress | `3da0e5275779cf0c7f537a7f220ed707e78b43c98a9db8eefd35fe2b2a2865a8` |
| `attempt-06-checkpoint-06` | Original child/durable failure records; child absence without an exit code; unused observer preparation | `b96fbdd77503aa979f6fb11b5607b6749e2ab24feaa9a23f418742dd27ca77e9` |
| `attempt-06-checkpoint-07` | Closed M3 jobs/report hashes and normal GUI Exit; FullSmoke launch only | `695e84a85b18bf0e9e18ca4f02bdd312b6339d47845ad1b5ce40175f2d0287c2` |
| `attempt-06-checkpoint-08` | Supplemental helper validation and earlier progress; no application acceptance | `da946d867d40d43ca6f42c7173cc62924c2f71cef6fd3f8a7de8a43ffedcf6f1` |
| `attempt-06-checkpoint-09` | Closed FullSmoke failure and original M4 job, report and nested-reference records | `c9a53ff63562049b0cf7c46d0c77e9ba2d2d20fcf3174e89d5c17f15fb05ac72` |
| `attempt-06-checkpoint-10` | Two GUI raw-evidence actions, exact byte-copy verification and subsequent normal GUI Exit | `092b6cb50bcc087aacc82c592bef89b70e99d96a43ed95da611f2b29fc3119cf` |
| `attempt-06-checkpoint-11` | Four scoped supplemental API passes and the closed campaign failure, with both original historical-reference failures | `16519ed2f39bf1f51fe511b566876a79519a85bf66b725cdf3a1460c8c561a44` |
| `attempt-06-checkpoint-12` | Closed lifecycle preparation and same-version reinstallation, 668-file preservation and three fresh reader reconstructions | `7df78c388f58c809704696f836cbc44f2e4cc03c1487e172a9480348adddb05b` |
| `attempt-06-checkpoint-13` | Original Repair failure, exact current snapshot and two verification-status changes with reverse-byte proof | `b4169e98aa8b2cea1feb8e70d1ce9ccf8a3c0f075a3148b81383cfe346470b00` |
| `attempt-06-checkpoint-14` | Closed Uninstall and SavedReader passes, import-only diagnostic and final idle observations | `591fba4d2e98b38fbdf11d8ff9425d9793acda2f7d339d375cad55f550ee0427` |

FullSmoke, Shortcuts, durable export, the supplemental campaign and Repair retain
their separate failed outcomes. Complete GUI workflow/reader acceptance, the final
browser walkthrough and remaining lifecycle checks are pending. Earlier G/F
failures and the unexplained host EPERM are preserved; update/native passes and
individual completed jobs do not close those broader scopes.

The evidence-preservation decision is to retain curated, hash-verified closed
records, selected original reports/logs, inventories and screenshots through bounded
read-only retrieval (RF). These checkpoints support the stated outcomes without
requiring a final ZIP export. Complete synthetic archive bodies and raw-retention
copy contents remain in the guest; this record does not claim their full export or
host reconstruction. A later full archive transfer would support additional
reproduction work, rather than convert any failed acceptance result to a pass.

## Candidate I: clean installation and native retry; workflows pending

Candidate I was built from clean source
`ad4e3a69798f20e849711804aad70d5b3bbc38d7`, build
`ot058-ad4e3a69798f-1be3597ce9b89806`. Its installer is **201,692,703 bytes**,
SHA-256 `7029dec04b084da0c333075d99bf0930de64ac963758a71e7dae320541a34119`;
the payload contains **24,282 files / 773,843,895 bytes**. The locked host check
passed **1,542 tests with 31 skips in 491.829 seconds**, including strict
documentation checks. The original check log is
`results/ot058-verification/full-gui/repository-check-candidate-i-02.log`, SHA-256
`040623b34edb0d18bfe36502f1e538d26edf115b26a4b2c27f4863636308184a`.
Subsequent private harness changes do not create a new installer or tested source
revision.

I changes the Windows control-pipe reader to read only available bytes while
preserving START/CANCEL/EOF handling, owned Job supervision and the original
worker limits. A matched H diagnostic with the blocking control reader reached
NumPy import and then its 600-second deadline. The corrected private diagnostic
completed NumPy import in about ten seconds and the import-only worker in
101.891 seconds, with a live control watcher and exit zero; its sentinel did not
run numerical work. This supports the control-reader fix, not a scientific
workflow pass. Source inventories are now deferred
until requested, with equivalent source closure and no cache across checks.
Archive inventory and same-open-file metadata work was reduced while retaining
full reads, mutation checks and fresh final reopen checks. The earlier archive
diagnostic still failed its 900-second limit during its fourth runtime inventory,
before the final metadata correction; it does not establish an I archive pass.

**Baseline, Install and Shortcuts passed.** The baseline records Windows 11 x64
build 26300 under an ordinary account, absent OpenT1D/workspace, no registered
Python and no enabled WSL feature or installed WSL distributions/packages.
Windows Store Python aliases and the inbox WSL command were observed separately.
This is the verified application/dependency baseline. The offline graphical
installer's default Finish action opened the normal Start page. Both shortcuts
reused the same process/session; maintenance stop and the full payload audit
passed. These steps did not execute scientific workflows.

**The initial Native phase failed:** 121 tests in **635.257 seconds**, one failure,
two errors and six exact allowed skips. Normal completion exceeded the test's
10-second wait, an owned example exceeded its 15-second wait, and cancellation's
30-second analysis-entry observation ended while the worker was still in
`snapshot`, before CANCEL. The full post-test payload audit was not reached.
A quiet diagnostic repeated the three original methods and limits: the owned
example passed in 8.125 seconds; cancellation reached analysis in 28.813 seconds,
closed after CANCEL in 1.484 seconds and reconstructed its report. Direct normal
completion again exceeded ten seconds, with only 0.0625 seconds of child CPU and
no output. This does not identify a loader, import or scheduling cause.

**One explicit unchanged warm Native retry passed:** 121 tests in **311.710
seconds**, no failures/errors and the same six allowed skips, followed by a
successful full payload audit. It used a fresh evidence root retaining the exact
earlier Baseline/Install/Shortcuts identities and the full original failure history.
No source, tests or test limits changed. This is a separate retry result, not a
new clean installation or an explanation of the first failure.

**Two later M4 harness attempts failed.** The v8 workflow stopped at
`Desktop operation exceeded smoke-test deadline` during its fixed **900-second
installation observation**. Planning had completed; the install command retained
its original **1,800-second** product allowance. Exception cleanup requested normal
authenticated desktop shutdown, cancelling that active install. The job recorded
`cancel_requested: true`, cancelled state, exit 3221225786, no forced cleanup and
no remaining owned processes; desktop shutdown returned zero. No M4 readiness,
historical reference, supplied-source run or reader completed, and the post-workflow
full audit was not reached. This was harness preemption, not a scientific result
or expiry of the product's installation allowance.

The v9 successor failed earlier, in its new selected-file guard, before any M4
workflow ran. It compared Windows path and descriptor snapshots as if their
`st_ctime_ns` and mode fields had identical meanings. A narrow correction keeps
path identity/type checks separate from consistent descriptor snapshots before
reading, after reading and on a fresh reopen. The standalone native check passed
in **4.344 seconds**, verifying the three selected hashes before/after and the
actual timestamp/mode differences. This proves the corrected helper only: no
full payload audit, installed-file write or product workflow occurred. The v10
continuation preserves both failed attempts and uses that corrected helper.

**The actual v10 M4 workflow subsequently failed.** Run
`20261025T153153423-M4` closed with controller exit 1 at
**17:02:35.949915 UTC**. Original workflow records confirm installation and
readiness jobs completed with exit zero, followed by the M4 run job failing with
exit 1. All three record no forced cleanup or remaining owned processes; normal
authenticated desktop shutdown returned zero. The selected identity check before
the workflow passed, but `selected-identity-after-workflow.json` is explicitly
missing. No after-check or complete workflow pass is inferred.

The separately retrieved historical worker log declares the original **600-second**
limit and contains completed fasting `native_zero` coarse, tight and reference
markers. Runtime attestation exists. Its interruption stack is in the
padded native integration path, through `quad_vec`, dense output and
`numpy.searchsorted`; NumPy import had completed and computation had begun.
The outer historical log records `GlobalInterruption`. Repeat log/runtime files
are absent. The original state and report confirm historical `WorkerDeadline` at
the unchanged 600-second limit. Both supplied sources remained `not_attempted`,
with **0/2 source/load cases and 0/1 pairs accepted**. The total-time distribution
and cause remain under investigation.
This evidence does not establish that another product code change is required.

### Explicit continuation observation and audit policy

V9 introduced fixed completion observations derived from the existing product
command, admission and cleanup allowances; v10 retains that policy. These are
changed **test-harness observation limits**, not an unchanged-harness retry.
Exact route/configuration guards bind the derivation to the supplied fixtures.
Product/model/configuration limits remain enforced by their existing owners:
historical worker 600 seconds, supplied source 3,600 seconds, M3 candidate 120
seconds, campaign slot 1,800 seconds and durable operation 900 seconds.

| Changed observation | Fixed seconds |
| --- | ---: |
| M4 install / run / reader | 1,920 / 17,490 / 1,770 |
| M3 forecast / comparison run; readers | 4,310 / 4,570; 1,560 |
| Campaign install / resume / reader | 2,220 / 4,980 / 1,020 |
| Durable export / register / verify / reader | 960 |

Campaign's separate controlled-cancellation milestone uses 4,980 seconds while
retaining the first-completed-slot/next-started-slot condition and failure if the
job ends before that point; cancellation closure uses 120 seconds. MMTT's
30-second analysis-entry and 200-second cancellation-close observations, readiness
checks and other route limits remain unchanged. Progress never renews a deadline.

The acceptance-only full-audit schedule now has **six** audits: the successful
full audit before the failed v8 M4 attempt; a mandatory full audit after all six
workflow passes and normal stop/settle, before the maintenance snapshot; and
the four existing maintenance/retained-reader full audits. Each workflow's
before/after selected guard checks the manifest, two root interpreter files and
registered installation/source identity. It explicitly does not verify the full
source or payload inventory. Other installed-file changes may therefore remain
undetected until the mandatory final audit; product integrity checks remain active.
If the workflow group cannot finish, that audit remains not reached.

The separate audit-only measurement checked every payload hash in **814.125
seconds**, within its 1,800-second allowance; controller duration was 834.268569
seconds, with exit zero and no timeout or cleanup. It establishes a complete
24,282-file audit in that run, not a causal speedup or application workflow pass.

### Candidate I preserved evidence and remaining scope

The immutable checkpoints below are under
`results/ot058-verification/native-windows/attempt-07-final/`. They preserve
original bytes/BOMs, completed receipts and explicitly labeled external references.

| Checkpoint | Confirmed scope | Manifest SHA-256 |
| --- | --- | --- |
| `checkpoint-01` | Baseline/Install/Shortcuts, initial Native failure, quiet diagnostic, warm Native pass, audit-only measurement and used helper lineage | `bfaadfb5a1c0a415c316c3004f2aa3a5aec96d7f36339a47bbd22e4482c72484` |
| `checkpoint-02` | Original v8 M4 observer failure/cancelled job and closed v9 preparation with preserved prerequisite/failure histories | `314686deae293026a196fcca014b92a1d185a1cb378a139c1f9492263ee89633` |
| `checkpoint-03` | Original v9 pre-workflow guard failure, native corrected-guard proof and closed v10 staging/parsing/state preparation; no active workflow result | `bd61d7da55c3ee2dd6de6f3569c12f6c757f621561c1f8e0a26afbd33d3e365d` |

The v10 preparation preserved 75 historical records and selected only the four
previously passed prerequisites. Its separate raw state files were not retrieved
in checkpoint-03; its actual preparation stdout was verified against the original
states and bridge. These checkpoints predate the actual v10 M4 failure. Its
closed main batches are separately preserved in
`/private/tmp/ot058-i-v10-m4-failed-original-01/`, manifest SHA-256
`87c86dfddab014d2d35971b3f0c391d35104e8f1cf24ee3db3f73324a68da2a8`;
the nested worker originals are in
`/private/tmp/ot058-i-v10-m4-nested-original-01/`, manifest SHA-256
`ce76d2e29e94e79a2e53c629fc4da924298797e3b2771f4b7b78e9f695b4977a`.
The main batches preserve eight unique originals with five common files byte-equal
across both batches; the selected-after record is explicitly missing. The nested
collection preserves five originals and explicitly lists both missing repeat files.
I's M4 result remains failed; campaign, M3, durable archives, both MMTT
tasks/cancellation, library/raw-retention UI and lifecycle acceptance remain pending.
Earlier H/F/G outcomes remain unchanged.
Curated closed records support the stated results; complete synthetic archive
bodies, VM images, firmware and session credentials are not copied into these
checkpoints. Host/guest wall timestamps are not used to infer elapsed durations
or performance on physical Windows x64 hardware.

## Focused maintenance preparation: directory metadata failure

The user selected a focused maintenance check in the existing VM, without
setting up another Windows computer. A separate helper attempted to preserve
the complete existing workspace, including the failed M4 archive, before
creating one synthetic 32-draw MMTT observations report and native reader.
The unchanged candidate-I preparation failed before creating that fixture or
modifying the installation. Its controller closed with exit one; the default
desktop remained stopped. Repair and Reinstall were not reached.

The installed archive inventory raised `Directory replaced`. A subsequent
read-only native diagnostic reproduced the comparison on an existing GUI
configuration directory: its size was 4096 before opening the no-delete
directory handle and 0 in the subsequent path-stat observations while that
handle remained open. Device, inode, modification time and creation time were
identical. This is distinct from the earlier path-stat/file-descriptor timestamp
issue. The diagnostic did not read report bodies, change installed files or
establish a maintenance pass. The original failed preparation remains retained.
Its exact closed records, diagnostic and private helper provenance are preserved
in `ot058-i-focused-prepare-failed-original-01`, with manifest SHA-256
`2c8ab03cf3ce1eb38c1fc363c01c5ac423ed0a4fcc81be570d059542952a26fd`.
The two retrieval batches contain nine distinct originals and three byte-equal
common records, with no missing members. The failed snapshot record is an error
receipt, not a completed data inventory.

The corrective scope is Windows directory comparison only: retain identity,
timestamps and link/reparse refusal, while excluding the observed unstable
directory-size field. Regular-file size and content checks remain required.
The original failed-I preparation and diagnostic are also preserved under
`results/ot058-verification/native-windows/attempt-07-final/focused-maintenance-failed-01/`,
manifest SHA-256
`904239a041c4b914fbcceabbcbccc38f27538215d0155667c0ea28264f4f64dd`.

## Candidate J: directory correction and focused upgrade continuation

J was built from clean source `f47868a9b135ba3b3aff60568397908e344d7656`
as `ot058-f47868a9b135-47220ef8119b7bb7`. It applies the narrow directory
comparison correction above. Regular-file size/content checks, directory
identity/timestamps, reparse refusal and handle ownership remain enforced.
The scientific algorithms, product deadlines and locked runtime/dependency bytes
are unchanged.

The independently audited payload contains 24,282 files totaling 773,858,663
bytes. The installer is 201,697,149 bytes, SHA-256
`9f2bacaa8a6512bd955908c58af29d32ed677678f4bbc5a6c46597542399d9e8`;
the package manifest SHA-256 is
`7b0a2fad4fe36479b885189cb40c7e2c7a0e20de5cebc4f900c764d26b97b617`.
The locked host check passed 1,545 tests in 448.302 seconds with 32 skips and
strict documentation checks. Its original log SHA-256 is
`804baf131c9c189eeb153333d0ac689f2c1187f23856b40ad7fcfdc581f2a174`.
These results establish host checks and static artifact integrity only.

The graphical installer reached its Finish screen and automatically opened the
browser Start page. The separate upgrade test phase
`20261025T175809852-Upgrade` then failed at the installed-payload audit's
1,800-second observation limit. Its controller closed with exit one at
`2026-10-25T20:16:10.0262360Z`; the audit child remained running for inspection
at phase closure. Its subsequently recovered payload result passed all 24,282
files / 773,858,663 bytes against the exact J manifest, outside the original
allowance. The old process was later absent; no exit code was inferred from that
absence. A normal application stop subsequently returned zero with no session
present. The original Upgrade test phase remains failed.

The original terminal records and complete pre-upgrade snapshot are preserved in
`/private/tmp/ot058-j-upgrade-failed-originals-01/`, manifest SHA-256
`a522e37158662cd82ff89a9ffd68f773e2a1a2bf3845818e0f0fe653b5a28337`.
This collection explicitly remains partial. A separate cumulative collection,
`/private/tmp/ot058-j-upgrade-failed-originals-02/`, preserves the late payload
result with manifest SHA-256
`aeb5bf42760f514c290c66e87958cd96bfb2d06e38548aa021d9fc7cc77baf74`;
it also remains incomplete for the original upgrade sequence. The pre-upgrade
snapshot used private J storage code under I's unchanged interpreter/support;
it establishes neither an I product inventory pass nor post-upgrade preservation.

The failed Upgrade and separate late audit are durably preserved in
`results/ot058-verification/native-windows/attempt-07-final/checkpoint-05/`,
manifest SHA-256
`9faea0770cd044aade7ae5e10c111bcf3abda9bbad5a86fea26a745b9044b986`.

The separate `20261025T205038189-CompleteUpgrade` continuation closed with
controller exit zero at `2026-10-25T21:00:41.5437280Z`. Its fresh full payload
audit passed all 24,282 files / 773,858,663 bytes within the unchanged 1,800-second
limit. Against the original pre-upgrade snapshot, all **366 original files**
remained byte-identical, with no additional files or expected bookkeeping
changes. Normal desktop start/stop passed, and I's exact package manifest and
saved-reader shortcut were retained; no I reader was executed. The 18 directory
and preservation tests passed in 11.343 seconds against actual installed J, with
no failures, errors, skips or private directory override. These are separately closed
continuation results; the original Upgrade remains failed.

Prepare run `20261025T210343283-Prepare` passed one synthetic 32-draw
observations/increase MMTT API case and its first fresh native reader. The report
records complete cohort coverage and the classification “consistent within
investigated assumptions”; reconstruction preserved both original report bodies.
All four example, freeze, execution and reconstruction jobs completed with exit
zero, no forced cleanup and no surviving owned processes. All 366 existing files
remained byte-identical, with no bookkeeping changes and 89 added files.
This phase did not repeat the full payload audit from CompleteUpgrade.

These closed results are preserved under
`results/ot058-verification/native-windows/attempt-07-final/`:

| Checkpoint | Closed scope | Manifest SHA-256 |
| --- | --- | --- |
| `checkpoint-06` | Separate CompleteUpgrade, original-snapshot preservation and native18 | `bd4437f7726162ace85fb00ee839132ac6f0877ad7b3cc828a10d0f0ae2455b4` |
| `checkpoint-07` | Synthetic MMTT API case, original reports/jobs, first fresh reader and preservation | `d2666d2caf84767db488dccd3dafd26e104575e7e7d3be7f1fc4a50ef877e2ab` |
| `checkpoint-08` | Repair, separate restart/maintenance snapshots, full payload and fresh saved reader | `d2160c6a1333331fa62f853a41a96d2bdb52d8982e15ecb65f576664fd65dae5` |
| `checkpoint-09` | Reinstall with the application running, preservation, full payload, fresh saved reader and separate host/guest clock observations | `58afcb8f915f28501f128d81d95196aec8eed354a682be4e1b78a7c0e9fcf7fe` |

Repair run `20261025T211440223-Repair` passed, with controller exit zero at
`2026-10-25T22:53:02.5389930Z`. Before maintenance, normal application restart
preserved 453 of 455 files byte-for-byte and produced exactly two prebound
bookkeeping changes: the earlier MMTT reader job and observation record changed
from `native_reader_verified` to `recorded_verification`. Their exact expected
before/after hashes matched; no files were added and no fresh verification was
claimed from this restart.

The Repair test deliberately removed the stopped installation's
`runtime/pythonw.exe`, retained that original binary outside the workspace, and
added `runtime/OT058-unexpected-test-file.txt`. Running the same J installer
restored the exact current payload without the marker and retained the previous
version directory.

Across the actual maintenance operation, all **455 files remained byte-identical**,
with no additions or bookkeeping exceptions. The full J payload audit verified
24,282 files / 773,858,663 bytes. The fresh saved-reader job completed with exit
zero, no forced cleanup or surviving owned processes, and reconstructed the
original JSON and Markdown reports with unchanged bytes.

Reinstall run `20261025T225552969-Reinstall` passed with controller exit zero;
its original guest completion label is `2026-10-26T00:04:31.0259627Z`.
Maintenance began with the application running, without an active numerical-job
claim. Before maintenance, normal restart preserved 458 of 460 files
byte-for-byte and produced exactly two prebound bookkeeping changes, with no
additions. Across the actual maintenance operation, all **460 files remained
byte-identical**, with no additions or bookkeeping exceptions. The full J payload
audit verified 24,282 files / 773,858,663 bytes, and the same-build installer
retained an additional previous-version directory. Fresh saved-reader job
`job-bc5018977b164687957a330864edad37` completed with exit zero and reconstructed
the original JSON and Markdown reports with identical bytes. The original case
and both report references remain the Prepare artifacts preserved in checkpoint07.

This closes the focused CompleteUpgrade, Prepare, Repair and Reinstall
sequence. The J installation was upgraded from preserved I, not a new clean
baseline; full M4, M3, campaign, archive and remaining lifecycle acceptance stay
open. Earlier failures remain unchanged.

Host screenshot/collection timestamps and guest clock labels were not aligned
during Reinstall. Both domains are preserved as recorded; no elapsed installation
benchmark, timing cause or deadline conclusion is inferred from their difference.
The helper and deadline bytes were unchanged.

## Candidate J: fresh-baseline installation and example workflow

Attempt `attempt-08-clean-j-01` uses the same candidate J installer and a separate
clone of the preserved clean Windows baseline. The disk, UEFI variables and TPM
state were cloned together and checked against their original identities; the
existing maintenance-test VM and its evidence were retained.

Baseline run `20261026T083052488-Baseline` passed with controller exit zero at
`2026-10-26T08:32:01.7765060Z`. The ordinary `Researcher` account ran Windows 11
Enterprise Evaluation on AMD64 without elevation. OpenT1D's installation,
data root and application/uninstall registrations were absent. No Git command
or registered Python installation was found; the only Python commands were
unexecuted Windows Store aliases. WSL was disabled, with no WSL packages or
distributions, and the network adapter was disconnected. The built-in WSL
command was recorded without executing it.

One subsequent read-only metadata retrieval process crashed with access violation
`0xC0000005` (exit `-1073741819`) and empty output streams. The unchanged retrieval
script passed under a fresh request identity. The successful Baseline phase was
not rerun, and the failed retrieval remains separate evidence; no cause is
inferred from the passing read retry.

The closed records, original clone provenance, frozen helper methods and separate
retrieval outcomes are preserved under
`results/ot058-verification/native-windows/attempt-08-clean-j/`:

| Checkpoint | Closed scope | Manifest SHA-256 |
| --- | --- | --- |
| `checkpoint-01` | Clean Baseline, clone provenance and separate read-only retrieval failure/retry | `0c288770624d4570700540bdad2f1c216d504ed3b2c6a55115c580c03a615ddd` |
| `checkpoint-02` | Install, exact full payload, automatic server probe and separate Edge/post-stop observations | `afeac5ce62a3af2ec6fd2657bb5c2f45ecb9dd8326f6c24beac7be208f5ca862` |
| `checkpoint-03` | Start-menu/desktop shortcut reuse and normal stop | `10434dbc47bef7026e48e28629fda38b84282753f095a93ee57c5b66be1b4112` |
| `checkpoint-04` | Synthetic MMTT API case, four closed jobs, original reports and first fresh reader | `46856e3f4a2356a23e2ace655311fbae84937c56fc6e5d827b49c955db60dcff` |
| `checkpoint-05` | Reopen, original case/report references, fresh reader, separate healthy browser review, verified UI Exit and normal VM shutdown | `7993977e4d551c7ac7f5fe0df9d2d856506376a21a4820151988c09386ef9173` |

The separately closed Install run
`20261026T084049053-Install` passed with controller exit zero at
`2026-10-26T09:23:26.2214590Z`. Its original phase record is 2,617 bytes, SHA-256
`5c46628bc88c2bc646adce19052bc61642be8a3927cf36648557140e89cfdaef`.
The graphical Finish screen was observed, and the full installed-payload audit
verified all 24,282 files / 773,858,663 bytes against the exact J package manifest.
The automatically launched local server passed its probe at
`2026-10-26T09:23:00.535087+00:00` as server PID 4460, followed by the harness's
normal application stop.

The default Edge browser presented its first-run setup during automatic launch.
The operator used its ordinary skip choices for accounts, imports and
personalization. By the time the OpenT1D Start page was inspected, the harness
had already stopped the application. The preserved startup screenshot therefore
shows `Failed to fetch` against that stopped service; it establishes neither a
healthy first interactive page nor an additional product failure. The later
healthy browser/report review is recorded separately below. No installer,
product or deadline bytes changed during this observation.

Shortcuts run `20261026T093449245-Shortcuts` passed with controller exit zero at
`2026-10-26T09:36:28.3201630Z`. Both installed shortcuts targeted the exact private
interpreter, and Start-menu and desktop probes used the same server PID 2256.
Normal application stop passed. This phase checked the selected manifest and
root interpreters; it did not repeat Install's full payload audit.

MMTT run `20261026T094215353-MMTT` passed with controller exit zero at
`2026-10-26T09:44:57.0500610Z`. The API-driven observations/increase case used
32 draws and created `obs-study-18804b1e3177408ca70e23385f0d8451`. Its complete
synthetic cohort contained one person and three completed variant pairs. All four
example, freeze, execution and first reconstruction jobs completed with exit
zero, no forced cleanup and no surviving owned processes. The first fresh native
reader preserved the original JSON and Markdown report bodies.

Reopen run `20261026T094826477-Reopen` passed with controller exit zero at
`2026-10-26T09:50:16.6702690Z`. Fresh reader job
`job-dbe4c76667564153b1a36400e276a0cd` completed with exit zero and preserved the
original 125,130-byte JSON and 5,715-byte Markdown reports. The original Reopen
phase record is 2,485 bytes, SHA-256
`64452030fd1d2d4fa9f1cdfe9ab97586f73c80f165e426aba0e6ed6c969ad9dc`.
The normal application stop required by this phase passed.

After the closed Reopen phase, an agent opened a fresh shortcut and separately
viewed the healthy Start page, the results-library row for this exact case and
its saved report. The displayed coverage was 1/1 people and 3/3 variant pairs;
`invented-01` was classified as “consistent within investigated assumptions”.
Displayed totals for all three variants matched the original JSON, and each
variant showed 32 completed draws with zero failed draws. This browser review
issued no new analysis or reconstruction and is distinct from the API-driven
workflow and reader checks. Its original observation record is 2,990 bytes,
SHA-256 `a413a7e09005de1a22baaa78dff18e647ca0095c0c8c899aac0404a879105626`.
It does not reclassify the earlier post-stop screenshot as a healthy automatic
Finish page or establish an independent human session.

The operator confirmed **Exit OpenT1D** in the browser. A separate read-only check
at guest label `2026-10-26T10:08:08.9192940Z` found the application session absent
and zero installed-runtime processes, without forced cleanup. No server exit
code was inferred. The original browser-observation record's pending closure
field remains unchanged; its separate 1,452-byte closure annotation has SHA-256
`a1436f206cbdc017e8f7904923c83f2a1c58fafadb907c61ff093307fc5c62a2`.

After the checks, Windows was shut down normally with `shutdown.exe /s /t 30`,
without the force option. The shutdown request returned zero, and the retained
launcher propagated QEMU's actual exit zero without a forced stop or QMP quit.
The 1,440-byte shutdown record has SHA-256
`5994ee0b99378dde5cfe76185ad1c90a360cbc1c844b3689c45d4f1b78be026a`.
The original maintenance-test VM state was not changed by this test.

These results close the bounded clean-installation, shortcut, single MMTT API
workflow, fresh-reader and saved-report browser-review checks. Complete Windows
workflow/lifecycle and independent-user acceptance remain open.

## Candidate J: attempt 09 native and API verification

Attempt `attempt-09-remaining-j-01` continues testing the unchanged J artifact in
an ordinary-user Windows 11 x64 clone of the normally shut down clean-J VM.
It is a separate verification attempt, not another clean installation.

AttestJ run `20261026T121646478-AttestJ` passed with controller exit zero at
`2026-10-26T12:17:53.1796770Z`. The phase finished label was separately
`2026-10-26T12:17:52.8319260Z`. It checked selected package/source/runtime
identities before and after the phase. This selected-file attestation is not a
full installed-payload audit.

Native run `20261026T121928049-Native` passed with controller exit zero at
`2026-10-26T12:40:11.2004130Z`. Its actual controller PID was 6424, creation
FILETIME `134374907693671369`. The installed-J suite ran **124 tests**, with
**zero failures, zero errors and the six exact declared skips**: three
symbolic-link cases requiring Windows permissions, one POSIX signal/process-group
case and two fixtures requiring a POSIX host-runtime wrapper. No required module
was skipped. The complete post-test payload audit then passed all **24,282 files /
773,858,663 bytes** against the exact J manifest. The phase retained unchanged
selected identities and did not change product/model deadlines.

Original phase/controller records, test results, post-test inventory and the
frozen helper/transport provenance are durably preserved in
`results/ot058-verification/native-windows/attempt-09-remaining-j/checkpoint-01/`.
Its 27,403-byte manifest has SHA-256
`2e88a7bf8bb81ea81b5c3df7507076a277ffbb92843854c11d6da80a1879ca6f`;
all 147 listed files plus the manifest were independently checked against the
physical roster and hashes: 415,799 bytes in listed members and 443,202 bytes
including the 27,403-byte manifest.

Checkpoint01 closes the current-J native suite and its post-test integrity audit
only. Other workflow/reader and lifecycle outcomes are not established by that
checkpoint. All earlier native, workflow and upgrade failures retain
their original outcomes; no independent human session or scientific acceptance
is inferred.

### Sampling-information-loss API workflow

Sampling32 run `20261026T124303303-Sampling32` passed with controller exit zero
at `2026-10-26T12:48:58.4465980Z`. Its actual controller PID was 5692, creation
FILETIME `134374921863428349`. The genuine synthetic case
`sam-study-57935f029f5647f0a2a44bd67a2294dd` covered **five invented people,
four schedules, 60/60 variant pairs and 1,920/1,920 draw pairs** at 32 draws.
No draw pair failed or remained unattempted. The report retained the three
expected nominal three-time-schedule direction reversals. These are constructed
software-control results, not human measurement or clinical guidance.

All five jobs completed with exit zero. Both fresh native readers reproduced the
original JSON/Markdown bytes, including across the normal application restart.
The recorded API and CLI shutdowns both completed cleanly with exit zero. This
is API-driven workflow and reader evidence; no browser-operated sampling analysis
or independent participant interpretation is inferred.

The complete original JSON report is 3,641,419 bytes, SHA-256
`7fe44176ab10bb3e06bcf880d9189c78218bbeb2db208e7d1d1c3153f97063a2`.
The Markdown report is 39,360 bytes, SHA-256
`e7974d1b79b35b7a9f4ca0545f81bacaefbadc288f4c5f73fdf3746b033ab3fc`.
They and the actual controller/job records are durably preserved in
`results/ot058-verification/native-windows/attempt-09-remaining-j/checkpoint-02/`.
Its 59,940-byte manifest has SHA-256
`b41f4540768eb649e5f18db37c99816fd9ac31b1c535a2b4b5d4d1c671096e57`.
All 304 listed files were independently re-read against their hashes and the
physical roster: 9,188,995 bytes in listed members, or 9,248,935 bytes including
the manifest (305 physical files).

The initial private collection rejected the actual Windows extended-length path
prefix and the original report's size above its former 2 MiB bound. The corrected
collector retained strict equivalence to the same bound path and used an 8 MiB
private read cap to retrieve the complete original reports. The failed collection
attempt and correction remain separate from the already closed workflow; the
workflow was not rerun and no product/model limit changed.

The other current-attempt workflow and lifecycle gates remain open until their
own closed evidence is preserved. The separately prepared human-session packet
is unsent and contains no participant outcomes; actual human sessions remain zero.

### Sampling cancellation and interrupted-report readers

Cancel1024 run `20261026T130956856-Cancel1024` passed with controller exit zero
at `2026-10-26T13:13:34.5199210Z`. Its actual controller PID was 7592, creation
FILETIME `134374937993173709`. The test observed genuine native sampling
analysis before requesting cancellation of
`job-6dac3e1069dd4d9294bdbcc8c60af042`, associated with entry
`sam-study-020c4827c0dc49178d7dc4365081f53b`.

The original run job closed in `cancelled` state with exit one,
`cancel_requested: true`, no error, no forced cleanup and no surviving owned
processes. The other four jobs—example preparation, plan freezing and two fresh
readers—completed with exit zero. The interrupted report and fresh reconstruction,
including the reader after restart, retained the same report hashes. Normal API
and CLI shutdowns both returned zero. This verifies the bounded sampling
cancellation/readers; it does not claim a completed 1,024-draw cohort, cancellation
of other workflows, or maintenance during active numerical work.

The original report hashes are JSON
`37ae331267937a1064aa44458197340109d3b79231a823dc80a61ff769f811bf`
and Markdown
`31022769ce3be1eac1adb2ab09c627769c6774e75303760b5727053e7a89b3c7`.
Checkpoint03 preserves the metadata, all five original job records and those
report hashes. At checkpoint creation, the original report bodies remained
under the guest's `driver-data/cancelled-sampling` pending separate collection.
After the environment interruption below, those uncollected bodies are currently
unavailable. This checkpoint does not establish a complete host export of them.

The records are durably preserved in
`results/ot058-verification/native-windows/attempt-09-remaining-j/checkpoint-03/`.
Its 24,606-byte manifest has SHA-256
`a60a005f6b3d5a22c07bdb4a8f91f39362282dbf4b176a68912e106d34824c06`.
All 131 listed members and their physical roster were independently re-read:
449,657 listed bytes, or 474,263 bytes including the manifest (132 physical files).

A separate read-only metadata collection crashed with access violation
`0xC0000005` (exit `-1073741819`) and empty output streams. One retry of the
identical collection script passed with exit zero. Its cause remains unknown;
that collection failure is preserved separately from the already passed
Cancel1024 product test. No workflow was rerun or model deadline changed.

### Interruption of the remaining-test environment

At a later inspection around `2026-10-26T20:21Z`, the task-local VM state and
private helper paths under `/private/tmp/ot058…` were no longer available.
The status of the previously retained execution session 3027 could not be
confirmed. No cause, normal VM shutdown, process exit code or elapsed execution
result is inferred from the missing paths or the changed clock observation.

M3Forecast run `20261026T132021027-M3Forecast` had been launched and was last
observed running at `2026-10-26T13:27:39Z`. No terminal controller receipt or
final M3 workflow result was recovered. Its outcome therefore remains unresolved;
it is neither an accepted pass nor a diagnosed product failure.

The surviving worktree retains the exact J installer and checkpoints01–03,
including the native-suite/post-test inventory, the complete Sampling32 report
bodies and the Cancel1024 original jobs/report hashes described above. The
Cancel1024 report bodies had not been collected from the guest and are currently
unavailable. Missing private state cannot supply additional late workflow or
cleanup claims, and the surviving checkpoints retain their original scopes.

The planned subsequent API phases, remaining lifecycle checks, isolated browser
download/first-execution exercise and fresh I-to-J update were not executed in
the observed record. Their prepared methods do not establish results. All
MacBook-capable testing is therefore not complete, and recovery or rebuilding
must produce separate, actually closed evidence before any additional gate can
close. Earlier failed phases and collection failures remain unchanged.

The private handoff packet survives under
`results/ot058-verification/prepared-human-session-j-01/`. It remains prepared,
unsent and unpublished, with empty participant outcomes and zero actual human
sessions; it does not close independent user acceptance.

## Candidate J: recovery attempt 10 before application installation

Recovery uses the unchanged J artifact identified above. This is a fresh Windows
provisioning and verification attempt, not a restoration of attempt 09's missing guest,
processes or uncollected reports. All attempt 09 results retain their scopes;
its M3 forecast remains unresolved. New VM state and helpers are stored durably
under ignored `results/ot058-recovery/`, with private VM/credential material kept
separate from summarized evidence. Licensed clean installation, healthy first
GUI startup, native verification and the separately scoped GUI/API workflows
below have since passed; complete acceptance remains open.

### Actual transport and ordinary-user baseline

All thirteen transport groups in `results/ot058-recovery/runs/transport-01` through
`transport-13` were independently checked. Their 70 receipt files bind the
ordinary `OT058RECOVERY\Researcher` actor, AMD64/64-bit Windows, namespace and
actual raw output/status to the frozen host/probe/bootstrap source chain.
Groups 01–02 retain client timeouts before readiness; they do not diagnose a guest
failure. Later checks preserve exact binary stdout/stderr, an intentional actual
exit seven, counter-one cached replay with the original PID/creation identity,
and refusal of new work while a timed-out child was held. The intentional
one-second timeout recorded Win32 status 259, unobserved exit and incomplete
pipes; its unchanged cached receipt remains incomplete after the later readiness
flags cleared. A subsequent new request completed with exit zero. No final exit
code is inferred for the timed-out child, and this does not establish worker
restart durability or an application test. The independent review is
`preparation/reviews/transport-actual-independent-review-01.json` under the
recovery root (21,306 bytes, SHA-256
`b4679c37c20382027eb6d8f0095dfdc89c5757eb937a8d324b9eb2b57efa4845`).

Baseline run `20261026T225547079-Baseline`, in namespace
`attempt-10-recovery-j-01`, completed with actual controller exit zero at
`2026-10-26T22:57:34.1159900Z`. Its controller PID was 7696, creation FILETIME
`134375289487929469`. The actual baseline records Windows 11 Enterprise
Evaluation build 26300, a non-elevated Researcher account, AMD64/64-bit execution
and a disconnected Ethernet adapter. OpenT1D's installation, workspace and
application/uninstall registrations were absent. No Git command or registered
Python installation was found. The two Windows Store Python aliases and inbox
WSL executable were recorded separately; they are not installed runtimes.
The WSL feature was disabled, with no WSL packages or distributions.

Original launch/controller/phase/baseline records are retained in
`results/ot058-recovery/runs/clean-09-baseline-originals/`. The actual namespace
above identifies recovery attempt 10 despite that collection directory's name. The
2,207-byte `baseline.json` has SHA-256
`f69b7e84f56c6aaf9f18da3f650cdb662a12bbab7f4bdef3084807bfecd10f8c`.
This closes the stated environment baseline only, not installation or workflow
acceptance on the recovered environment.

### Normal VM shutdown and unvalidated coupled cold copy

The normal Windows shutdown request returned actual serial-command exit zero.
A separate QMP event recorded `guest-shutdown`, and the retained QEMU launcher
returned actual exit zero, with no forced quit/kill. These records are under
`results/ot058-recovery/runs/cold-shutdown-01/`. A separate attempt to close Edge
using another QMP client timed out before the greeting; no key was sent. That
host orchestration failure remains separate from the successful normal shutdown.

The TPM daemon/socket/PID file were already absent, with no matching host process
observed. Its daemon exit code and disappearance cause are unknown. No explicit
TPM control command was sent, and graceful TPM shutdown is not proved.

A coupled cold-copy capture returned actual exit zero with empty stderr. Its
observation was recorded at `2026-10-26T23:08:44.052132+00:00`; this is not an
execution-finish timestamp. Read-only source and destination QCOW2 checks
returned zero; all four state files were sealed/rehashed with owners absent and
the source reverified unchanged. The private manifest is 9,734 bytes, SHA-256
`e2e42ee0619488843882690f6b23efb3458f250fef686ace7e33c37b13d822ae`.
The capture observation is `runs/cold-shutdown-01/capture-observation.json` under
the recovery root; the full private manifest, disk and TPM contents are not
copied into public documentation/evidence.

The capture was recorded as an **UNVALIDATED coupled cold copy**: its creation record
sets `boot_restore_validated` and `TPM_graceful_shutdown_proved` to false.
A separate coupled clone was created with actual exit zero and empty stderr. Its
observation was recorded at `2026-10-26T23:10:37.474840+00:00`, not an asserted
execution-finish instant. Its 3,683-byte private creation provenance has
SHA-256 `f83e888a5c353acd3eff20d104b0738ad7a10b71931104673be49b8276feb63f`;
the observation is `runs/cold-shutdown-01/clone-observation.json`. That record
sets `VM_started` and both source/clone boot-validation flags to false, with the
sealed baseline reverified unchanged. Creation proves no restored-boot outcome.
Those creation flags remain historical facts. The separate bounded clone-boot
observation below supplies partial restore evidence; it does not change those
records or establish full VM/TPM validation.

A separate read-only review checked the baseline originals, shutdown references
and cold-copy metadata/proof references. Its record is
`runs/cold-shutdown-01/independent-review-01.json` under the recovery root
(4,364 bytes, SHA-256
`6009158c47ca4e4b94f32164e6bacd019b811862f450746e03b90eb4bdd606a6`).
Graceful TPM shutdown remains unproved regardless of a later restore result.

### Separate bounded clone-boot observation

The clone reached the Windows desktop after one boot. Its first automatic worker
readiness wait exceeded the fixed 600-second limit. Manually starting the
original worker then failed with `SeSecurityPrivilege` during `Set-Acl` (line 16).
These failures remain in `runs/restore-boot-01/transport-ready/` and
`worker01-existing-cache-startup-failure.json`; reaching the desktop alone did
not establish a working transport or complete restore.

A separately reviewed offline helper repair reported preserving the original
worker and recording a durable dirty marker before writing. The reviewed source
order and actual passed predicates support that sequence; the raw backup and
dirty-marker files were not separately collected. The first elevated repair
attempt (child PID 2724) returned one before mutation; the worker's DOS attributes
were confirmed as 8225 (`ReadOnly`, `Archive`, `NotContentIndexed`). The next
repair (child PID 1116, creation `2026-10-27T00:04:38.9372669Z`) returned
actual zero at `2026-10-27T00:04:54.4880340Z`. It temporarily cleared only
`ReadOnly`, restored the exact attributes and preserved the original owner/DACL,
runtime and Startup entry. The repaired worker's SHA-256 is
`2d442ef79486abe4c8b48a73684f636071bd23b41b0dd861e8321365c797a76c`.
The worker itself remained an ordinary Researcher process. Its manual standard-user
start after the patch is observed; a subsequent automatic logon start is not
tested. Five original raw
JSON records, including both attempts and matched completion identities, are
bound by `runs/restore-boot-01/worker-fix-preserved-originals/collection.json`.
The failed repair attempt is not relabelled as a pass.

Worker PID 6764 became ready at `2026-10-27T00:06:34.615896Z`. The separate
read-only check `recovery10upgrade-readonly-restore-02` returned actual zero at
`2026-10-27T00:08:26.4619680Z`, with child PID 5084, creation FILETIME
`134375332676172079` and elapsed 38.904028 seconds. The probe reported `passed`;
its own `utc` value `2026-10-27T00:07:57.8575300Z` is its reported/start time,
not completion. Its raw result/stdout are
under `runs/restore-boot-01/restore-check02/`. The check verified ordinary
Researcher execution, AMD64/build 26300, the repaired worker and unchanged
runtime hashes, absent application paths, disconnected Ethernet and TPM 2.0
PnP status `OK` with error code zero. No System event 1001 or 6008 was returned
since the probe's cutoff. Recorded events include 1074 at 23:02:34, 6006 at
23:03:04 and 6005 at 23:12:19 on 26 October. The raw result also retains a 6005
with future timestamp `2026-10-27T05:16:28.1350969Z`; no cause, ordering or clock
forensics conclusion is inferred from it.

This is **partial restore evidence after a transport-helper repair**. It does
not prove complete TPM health, preservation of secret TPM state, application
restoration or model/workflow execution. The clone then completed normal
shutdown: the serial shutdown request returned actual zero, QMP recorded normal
guest shutdown and the retained QEMU launcher returned actual zero. Originals
are under `runs/restore-boot-01/shutdown-02/`, including
`qmp-shutdown-observed.json`, `qemu-launcher-exit-observed.json`,
`final-resource-observation.json` and the serial command's raw stdout/result.
The final resource observation found no QEMU/TPM process or loopback port 8765
listener. The TPM daemon's exit code remains unknown. All three local-only
source-ZIP transfer servers returned zero; they are separate from the Microsoft
activation proxy, which had not been started at that checkpoint. No activation
was attempted during the bounded restore check.

The independent final receipt audit is
`runs/restore-boot-01/independent-final-review-01.json` under the recovery root
(5,999 bytes, SHA-256
`b368be7b2a55933cf2843f51edca32c875858bb47e951ec5516afe1defbfbdb7`).
It preserves the partial VM/TPM and helper-startup limits above; it does not
establish application restoration or change the J artifact.

The selected source and sanitized proof records are sealed in
`results/ot058-verification/native-windows/attempt-10-recovery-j/checkpoint-01/`.
Its manifest lists 280 files / 405,906 bytes; the separate 54,810-byte manifest
has SHA-256 `de2a12b4e5a35631336a54bdda56681feb5e0cf2fcc1ee3eb824cc7984d740b9`.
VM disks, firmware/TPM contents, complete private state manifests and credentials
are excluded. The checkpoint retains the failed observations and the limited
scope of the later passing checks.

### Authorized normal Windows activation

The earlier automatic approval rejection remains preserved in
`results/ot058-recovery/preparation/reviews/activation-auto-review-block-01.json`.
It rejected starting the Microsoft activation proxy without explicit permission
for external Microsoft data exchange. On 27 October the user explicitly replied
“Ja, dat mag” to the normal-activation request. The authorization record is
`runs/authorized-activation-02/user-authorization.json` under the recovery root;
it authorizes normal activation and the restricted proxy, not purchasing keys,
rearming or changing the clock.

The next boot observed automatic startup of the repaired ordinary-user worker:
PID 3048, ready at `2026-10-27T02:29:23.758595Z`, with the expected worker hash
`2d442ef79486abe4c8b48a73684f636071bd23b41b0dd861e8321365c797a76c`.
This is separate evidence from the prior manually started worker. A host media
path preflight failure and the first launcher's exit one remain preserved in
`runs/authorized-activation-02/`; they are not relabelled as successful launches.
The corrected VM launch is the one used for activation.

Normal activation then completed with actual `cscript` exit zero. The held
administrator process PID 6380, creation `2026-10-27T02:32:52.7029529Z`, returned
actual zero at `2026-10-27T02:33:45.5739520Z`. Its original 819-byte activation
record has SHA-256
`79db5cef51fb91801c7229e5fe7ccb87d4744638ef4ec2002b96f94d11a70203`.
A new ordinary-user query found `Windows(R), EnterpriseEval edition` with
`LicenseStatus: 1` and `GracePeriodRemaining: 129599`. WinHTTP DIRECT was verified
both in the administrator's finalization and the separate ordinary-user query.
The VM network link was disconnected again.

The authorized proxy ran in a held host execution session. The operator stopped
it with Ctrl-C; its actual exit one with `KeyboardInterrupt` and context cleanup
is preserved, not relabelled as zero. Its listener was subsequently absent;
a separate proxy PID was not recorded. No license key was supplied; private VM
provisioning material remains separate from the activation evidence. No rearming
or backdating was used. The original activation,
administrator observation and launch request, together with the verification
record, are under `runs/authorized-activation-02/preserved-originals/`.

This closes the recovery VM's normal licensing step and resolves the earlier
permission block. It does not change OpenT1D's prerequisites or imply installer,
workflow, scientific or independent-user acceptance. Activation alone implies no installation or workflow result. The subsequent
installation and bounded workflow results are reported separately below. Remaining MacBook work is incomplete;
earlier baseline, partial restore and application evidence retain their scopes.
No new GitHub Actions run or public distribution is claimed.

### Fresh licensed baseline and controlled browser download

A new licensed baseline run `20261027T024138205-Baseline` completed with actual
controller PID 1600, exit zero at `2026-10-27T02:42:45.3116430Z`. Its 2,207-byte
baseline record has SHA-256
`f8086ac8c70cb5180814418a30d0f5434c956b6051b6ab34d6c3ddb103079dda`.
The original records are under
`runs/postactivation-clean-01/baseline-originals/`. The subsequent normal shutdown
and licensed `baseline-02` cold capture are separately recorded under that run
root. The capture returned zero; its observation was recorded at
`2026-10-27T02:56:29.805865+00:00`, not an asserted execution-finish instant.
The private 9,043-byte manifest has SHA-256
`61a0d06264a30600bad4d47f1ca3816220d596a74723d29fe08e6662a4e82e28`.
Source-unchanged and both read-only QCOW2 checks passed. This does not establish
complete TPM restore validation; the TPM daemon's exit code remains unknown.
Private full state is excluded from public documentation/evidence.

Root then observed a genuine Edge download from a controlled local HTTP server.
In this restricted offline environment SmartScreen reported that it could not
scan the file; the operator used the normal Keep action. No policy or alternate
data stream was modified. The server's actual request record reports HTTP 200,
a complete 201,697,149-byte response and SHA-256
`9f2bacaa8a6512bd955908c58af29d32ed677678f4bbc5a6c46597542399d9e8`.
The exact response hash is bound by the original server log below; this is local
transfer evidence, not a claim of public SmartScreen reputation or signing.

The original server log and normal close are under
`runs/postactivation-clean-01/actual-browser-download/`. The first separate
file-facts collector (`postactivation-download-facts-01`, PID 6792) exceeded its
fixed 180-second limit with status 259, unobserved exit and incomplete empty
output; it remains preserved under `download-facts/`. Its receipt supplies no
MOTW, signature or downloaded-file hash result.

The exact read-only diagnostic owner continued consuming CPU for approximately
16 minutes. Root later used ordinary Researcher PowerShell to hold native handle
3208, revalidate PID 6792 against creation FILETIME `134375446040735109`, and
explicitly call `Kill` followed by `WaitForExit`; the observed later exit code
was -1. This was forced test-infrastructure cancellation, not normal completion.
The later observation is
`runs/postactivation-clean-01/download-facts-later-cancellation-observation.json`.
A fresh readiness receipt at 03:33:20 recorded both ownership gates false. The
original 180-second status-259/unobserved/incomplete result remains unchanged and
failed. No installer, application or model process was started, and no security
policy, candidate ADS or application data was changed. This cancellation supplies
no download or application acceptance result.

A separate read-only native SHA-256 diagnostic then completed with actual exit
zero at `2026-10-27T03:40:17.1925230Z` (ordinary PID 4296, creation FILETIME
`134375459988709499`, child elapsed 18.330324 seconds), without timeout or
truncation. It hashed the actual Windows Downloads file: 201,697,149 bytes,
SHA-256 `9f2bacaa8a6512bd955908c58af29d32ed677678f4bbc5a6c46597542399d9e8`.
`SHA256Cng` completed the candidate hash in 6.411768 seconds; both the CNG and
default managed providers matched the standard `abc` test vector. Originals
are under `runs/postactivation-clean-01/native-sha256/`. This establishes the
actual downloaded file's hash. It neither identifies where the earlier collector
stalled nor establishes a managed-provider performance benchmark or cause.
Root also observed the actual 86-byte Zone.Identifier stream with ZoneId 3 in
the GUI; no ADS was fabricated or modified. At this earlier checkpoint the
signature query and installer execution had not yet occurred.

A later completed read-only metadata collector (`download-progress04`) confirmed
the full candidate hash/size, the genuine 86-byte Zone.Identifier stream
(ZoneId 3) and Authenticode status `NotSigned`. Its originals and producer
verification are retained under
`runs/postactivation-clean-01/download04-originals/`. The original timeout and
later forced diagnostic cancellation remain unchanged. The private collector
uses native CNG for its candidate hash; the clean-install observer replaces two
helper-only hash calls. Product bytes, core installer invocation/probe, installer
and scientific deadlines are unchanged. The separate metadata collector has a
fixed 1,800-second ceiling; its completed native response stayed within 180 seconds. The private helpers were independently reviewed.

### Licensed clean installation and native verification

Clean Install03 run `20261027T034743120-Install` completed with controller PID
4568, actual exit zero at `2026-10-27T04:23:52.8047860Z`. Root used the genuine
Downloads NSIS child, accepted the Apache license and observed the healthy first
automatic GUI launch. The full audit verified 24,282 files and 773,858,663 bytes.
The separate FirstStop closed with controller PID 5824, exit zero, a held native
server exit zero, absent session and no forced cleanup. Shortcuts closed with
controller PID 6176, exit zero, reusing server PID 4776. Selected-file AttestJ
(controller PID 2780, zero) is distinct from a full audit.

Native03 closed with controller PID 6584, actual zero at
`2026-10-27T04:51:59.3131080Z`: 124 tests, zero failures/errors and exactly the six
declared skips. Its full post-test payload audit passed. Original phase and
controller records are under `runs/postactivation-clean-01/` in
`install03-originals`, `firststop03-originals`, `shortcuts03-originals`,
`attestJ03-originals` and `native03-originals`. These are new results, separate
from the historical partial recovery checkpoint and attempt 09 evidence.

### Actual GUI Task 1 and normal graphical exit

Root completed Task 1 through the desktop GUI using the new synthetic case
`OT058 recovery J GUI 32 - 2026-10-27`, with 32 draws, then invoked its graphical
reader. Both actual jobs completed with exit zero. The GET-only Capture and
Compare helpers each retained eight raw records; they observed the actual GUI
case and reader without dispatching either. Original JSON (125,122 bytes) and
Markdown (5,715 bytes) remained byte-identical after reconstruction, with source
guards and host hashes verified. Records are under `gui-capture02-originals`
and `gui-compare02-originals` in the same run root. A private ID-query quoting
SyntaxError was corrected in the static transport; it did not rerun the model.
This is agent-operated GUI evidence, with independent human sessions still zero.

Root then clicked the GUI header's Exit action and confirmed the dialog. A
passive observer was ready before the click and sent no stop or signal. It
observed the held server PID 1896 exit zero at
`2026-10-27T05:31:32.5496490Z`, an absent session and no forced cleanup, within
75.647131 seconds of its fixed 120-second wait. The separate verified record is
`actual-gui-exit-verified-01.json` under the run root.

### New sampling API pass and remaining execution

The new Sampling32 phase closed with controller PID 2596, exit zero at 05:38:14
UTC. Five jobs completed zero, including two fresh readers; normal stops left no
subprocess survivors. The original workflow result is retained with the queue's
initial originals. Collection completed at 05:50:31 UTC: the full 3,641,419-byte
JSON and 39,360-byte Markdown bodies are retained under
`runs/postactivation-api-queue-01/initial-originals/`, with the actual chunk
producers under `initial-supplement/`. Its supplement index records complete
retrieval and the expected hashes
`7fe44176ab10bb3e06bcf880d9189c78218bbeb2db208e7d1d1c3153f97063a2`
and `e7974d1b79b35b7a9f4ca0545f81bacaefbadc288f4c5f73fdf3746b033ab3fc`.
This API-driven workflow is separate from the GUI Task 1 above.

### Attempt 10 interrupted sampling reports preserved

The separate attempt 10 Cancel1024 run `20261027T055046091-Cancel1024` closed
with controller PID 864, actual zero at `2026-10-27T05:53:37.1297250Z`; the
original interrupted outcome and already completed-zero fresh readers remain
unchanged. Its report bodies have now been fully host-retrieved in three
chunks: JSON 187,972 bytes, SHA-256
`37ae331267937a1064aa44458197340109d3b79231a823dc80a61ff769f811bf`,
and Markdown 37,922 bytes, SHA-256
`31022769ce3be1eac1adb2ab09c627769c6774e75303760b5727053e7a89b3c7`.
The complete-transfer record is
`runs/cancel-original-reports-01/completed.json`. The separate combined review
is `preparation/reviews/library-native-and-cancel-originals-actual-review-01.json`
(3,611 bytes, SHA-256
`51d49319a862809ebd20a489e4f5b342cb75b89de93e2d6b6a8684e2c852b9cd`).
The full bodies remain interrupted with complete-cohort false. This closes only
attempt 10's report-body gap. Attempt
09's uncollected/lost report bodies remain unavailable and hashes-only.

### New M3 forecast, comparison and cancellation

Attempt 10 M3Forecast run `20261027T055552544-M3Forecast` closed with controller
PID 1644, actual zero at `2026-10-27T06:08:38.4202350Z`. Its actual case is
`m3-study-26e982c91aea40098816aac2400cee2f`. M3Compare run
`20261027T061153616-M3Compare` closed with controller PID 6796, actual zero at
`2026-10-27T06:29:30.5239050Z`, case
`m3-study-264d2ae004bf450ab6219ef0cdf37a95`. Each has four original completed-zero
jobs (fixture, check, run and fresh reconstruction), no forced cleanup or
remaining owned processes, and a clean normal stop. Both complete JSON/Markdown
report bodies and job originals are preserved under their respective
`M3Forecast-originals` and `M3Compare-originals` directories in
`runs/postactivation-api-queue-01/`.

Independent reviews are
`preparation/reviews/m3forecast-actual-independent-review-01.json` and
`m3compare-actual-independent-review-01.json` under the recovery root. Both
planned synthetic people contributed in each case; that does not mean every
origin was forecastable/scored. The readers check retained causal windows,
persistence and analysis arithmetic; they do not independently rerun arbitrary
candidate predictors. This supplies no empirical human or clinical validity.
Attempt 09's missing M3 terminal result remains unresolved and is not backfilled.

M3CancelRaw run `20261027T063204189-M3CancelRaw` closed with controller PID 7664,
actual zero at `2026-10-27T06:41:43.7327010Z`. An actual started native case was
observed before cancellation. Its original run remains cancelled with exit one;
the separate forensic retention job completed zero. The closed result declares
50 files and 1,371,995 bytes with byte copies validated, while
`integrity_verified` and `reconstruction_verified` are false and `complete` is
null. This is raw retention, not a complete or verified reconstructible archive.

Exact metadata and four job originals are preserved in
`runs/postactivation-api-queue-01/M3CancelRaw-originals/`. The bounded metadata
review is `preparation/reviews/m3cancelraw-actual-metadata-independent-review-01.json`.
The 10,195-byte retention receipt body (SHA-256
`b3b84358782889614a18182251f1912189ba59fdaffd5e6517bb4e3d3f2c1f16`)
is now host-preserved as `runs/postqueue-collections-01/m3-0-retention.json`.
The separate review is
`preparation/reviews/postqueue-eight-actual-independent-review-01.json`.
This closes the prior receipt-body gap only. All 50 retained member bodies are
not claimed host-preserved; integrity/reconstruction remain false and
completeness remains null.

### M5 report-library verification

M5Library run `20261027T064336311-M5Library` closed with controller PID 6468,
actual zero at `2026-10-27T06:45:44.1019920Z`. Its actual registered entry is
`archive-896f18d27e1d43c3b6cdc401625b8890`. Three jobs (index and two verifies)
completed zero, without forced cleanup or remaining owned processes; two normal
stops returned zero. Original metadata and job collection completed at 06:48:06
UTC under the queue's `M5Library-*` directories. This is saved-report library
verification, not execution of an M5 model. The independent metadata review is
`preparation/reviews/m5library-actual-metadata-independent-review-01.json`
(3,232 bytes, SHA-256
`cb9cfd54ee19033323c8050f5ba0bc5adbea244755a016a46c780ced02cf9ad7`).
It verifies original jobs, source assertions and declared report hashes. The M5
report bodies have not been host-retrieved; complete body preservation is not
claimed.

### Campaign and M4 failed at reference-worker deadlines

Campaign run `20261027T064821677-Campaign` closed with controller PID 3936,
actual exit one at `2026-10-27T07:22:41.1399580Z`. It accepted zero of two slots
and zero of four source/scenario combinations. Controlled cancellation, resume
and a separate fresh campaign reader were not reached. M4 run
`20261027T072520652-M4` closed with controller PID 6256, actual exit one at
`2026-10-27T07:51:17.6135710Z`; candidate source evaluation was not attempted.
The exact failed phases, metadata and original jobs are retained under the
queue's `Campaign-*` and `M4-*` directories. Consistent metadata retrieval does
not turn either failed product test into a pass.

Separately preserved native report/reference bodies identify historical
`WorkerDeadline` with the unchanged 600-second reference-worker limit for M4
and the first campaign attempt. Both got past imports and completed partial
numerical cases (seven M4, five first-campaign reference cases) before maintained
interruption inside SciPy `quad_vec` integration. Parent deadline and child
maintained-stop evidence are consistent with fixed-deadline interruption while
numerical work was underway. They provide no full-stage timing breakdown and
establish no TCG, CPU, BLAS/provider or mathematical cause. No model physics,
precision or deadline was changed to produce a pass.

Actual body references are under `runs/failure-detail-collections-01/`,
`runs/postqueue-collections-01/` and `runs/reference-continuation-01/`. Independent
reviews are `campaign-failed-actual-metadata-independent-review-01.json`,
`m4-failed-actual-metadata-independent-review-01.json` and
`reference-continuation-actual-independent-review-01.json` under
`preparation/reviews/`. The first two reviews predate body collection; the
separate body review supplies the later deadline/interruption evidence.

A secondary read-only PowerShell metadata query (PID 2828) exited with
`0xC0000005`; its faulting module/cause is unknown. That original failed query
and unreached batch remainder remain preserved. A separately identified bounded
Event query returned zero, and eight different reference-file queries returned
zero; they were not a retry of the crashed query. The failure is reviewed in
`preparation/reviews/failure-detail-powershell-crash-actual-review-01.json`.
These diagnostics do not alter the original Campaign/M4 failures.

### Native library pass; collection and remaining work

LibraryNative run `20261027T082906580-LibraryNative` closed with controller PID
1896, creation FILETIME `134375633481428429`, actual zero at
`2026-10-27T08:35:47.4541300Z`. It used the three actual passed inputs: M3
forecast, M3 comparison and sampling. Full metadata and nine original jobs are
now preserved under `runs/library-native-collection-01/initial-originals/`;
the collect-only host operation returned zero. Three imports, restart and
saved readers completed zero without rerunning native models. The combined
independent review is `library-native-and-cancel-originals-actual-review-01.json`
referenced above. This does not supply missing Campaign/M4 success.

### Durable packages and separately preserved collection failures

Durable run `20261027T091059676-Durable` closed with controller PID 7764, recorded
zero at `2026-10-27T09:51:10.0828120Z`. Two actual M3 packages were exported,
registered, integrity-checked and reconstructed, then read again after restart:
forecast `durable-031505db6b0a4aa0be9fbbe6ba479ae4` and comparison
`durable-d76386498ca547249288dd2c9c5b5423`. All ten accepted jobs completed zero,
with no forced cleanup or survivors and clean normal stops. Report hash sets
match their actual source cases; this is bounded API/reader evidence, not a
claim that every package member was host-exported or that M4/campaign succeeded.

Original common metadata and the first two job bodies are under
`runs/durable-collection-01/initial-originals/`; the other eight are under
`runs/durable-supplement-cim-actual-01/originals/`. The independent union review is
`preparation/reviews/durable-CIM-union-actual-independent-review-01.json`
(19,638 bytes, SHA-256
`fa6ee76b954c74b7886b1378e0da5732aa93b6c3fb2445c2e4871a7c45748e1c`).

A read-only PowerShell collection query crashed separately; a CNG collector then
refused its process-identity guard with exit one. These failures remain preserved,
with no hash-provider cause inferred. Diagnostic snapshots found PID 7764 reused
by `svchost`, unavailable native creation metadata and a native query denied
access. A separate read-only CIM query observed creation 09:57:41.451788 UTC,
disjoint from the original controller's 09:11:01.1883149 UTC creation. Four new
bounded CIM-interval collector variants preserved exact original bytes; they
accept only absence or a typed known-timezone creation interval disjoint from
the original. Original completion zero is checked against its original controller record,
never inferred from PID reuse. The source and actual identity reviews are
`durable-supplement-CIM01-independent-source-review-01.json` and
`durable-controller-identity-actual-independent-review-01.json` under
`preparation/reviews/`.

The first successful CIM query exposed a separate Mac receiver unpacking bug
(three expected return values versus four). Its native query zero and host
failure one remain recorded. That existing receipt was decoded offline; the
corrected receiver dispatched only the three previously unexecuted queries.
No product workflow or first query was rerun. This recovery closes original job
preservation, not the earlier diagnostic failures or any scientific gate.

### Launcher and session controls

Controls run `20261027T101038927-Controls` closed with controller PID 4992, recorded
zero at `2026-10-27T10:11:50.2671850Z`. Its separate private workspace verified
actual launch/same-process reopen; five boundary refusals with HTTP 403 and five
malformed configuration routes with HTTP 400; genuine former-session replay
with new process/credentials; and refusal of the former genuine token. The
fourteen check records preserve no response bodies, tokens or credential hashes.
Held servers 5816 and 6280 each exited zero after exactly one normal API or CLI
stop, without force, with absent sessions and closed listeners. Elapsed time was
30.594 seconds; default workspace absence and unchanged selected J were checked.
These absence observations apply at phase completion, not after later GUI use.

Original phase/controller/report bytes are under
`runs/desktop-controls-collection-actual-01/originals/`. The independent review is
`preparation/reviews/desktop-controls-actual-independent-review-01.json`
(6,800 bytes, SHA-256
`3b8ed0b821beb4dedbe73ac66e7850c8846b6977425e0b174e6bbb64ad8d6187`).
This is session/security/schema verification, not numerical cancellation or
maintenance during an active model run.

### Remaining GUI views and actual export/library operations

The completed run `runs/remaining-gui-actual-01/` preserves 48 screenshots and
operator action records. M3 forecast/comparison, Sampling32, M5's report-only
library and the failed M4/campaign reports were viewed without rerunning their
models. Those views do not establish successful M4/campaign execution or an
all-route GUI model-run pass.

Separate actual GUI actions created M3 export job
`job-71c518adaca348a888a84a9e57c5a252`, package
`durable-89812dbfe86547cba42bd7ad8fa41fc3`, and completed zero before the original
960-second ceiling. The package's 75,444-byte JSON and 2,983-byte Markdown
identities match the original M3 comparison. A valid external Task 1 archive
copy was then indexed by `job-1bc1e723b1c243e8994aa6601447b689` and verified by
fresh reader `job-2538497de6e64448948d8b4908197ce3`, both completed zero. Entry
`archive-5981265fcbad4ca385a9249fc78c7c0b` retained the original 125,122-byte JSON
and 5,715-byte Markdown identities. All 35 original/copied files (443,214 bytes)
remained unchanged through the reader and Hide / Show hidden / Restore actions;
the final reference is visible.

The first internal archive-path refusal created no job and remains visible in
screenshot 36. A separate copy helper failed before copying because it passed a
Path where the storage API required a canonical string. The second helper only
added `.as_posix()` and made the byte-identical permitted copy. Both failure
records remain preserved; no model or failed GUI job was silently rerun.

The final normal Exit/confirmation was observed after a passive observer became
ready. Held server PID 3312, creation FILETIME `134375699597209469`, exited native
zero, with no session, observer stop/signal or forced cleanup. Its 54.679204-second
wait includes operator time and remained within the unchanged 120-second limit.
The verified record is `normal-exit/verified.json` under the GUI run. The
independent review is `preparation/reviews/remaining-GUI-actual-independent-review-01.json`
(14,667 bytes, SHA-256
`4de41f63aaa004d2ba584a62592364c481904caa2d3455cf1c3c27eb3cef634e`).
Screenshots/GET-only observers remain distinct from actual GUI dispatch; no token,
credential hash, raw session or HTML was exported. Report bytes were checked in
Windows against existing originals; no whole new package/member-body export is
claimed by this GUI evidence. Independent human sessions remain zero.

### Dependent RawRetention and frozen lifecycle preparation

RawRetention run `20261027T113202259-RawRetention` closed with controller receipt
6396/zero at `2026-10-27T11:34:34.1599800Z`. Two forensic-copy jobs completed zero
with no forced cleanup or survivors. Forecast retention declared 43 files and
1,780,216 bytes; comparison retention declared 85 files and 3,200,051 bytes,
total 4,980,267 bytes. Byte-copy validation is true for both; integrity and
reconstruction are false and completeness is null. No original M3 model was rerun.

Both complete receipt bodies are now host-preserved under
`runs/raw-retention-receipts-actual-01/`: 8,116 bytes, SHA-256
`ca09fc286c449f6dea53276bc230c4345c956b995404d6872d0a538a6ee8b9e1`,
and 16,945 bytes, SHA-256
`67e9156b47395741133d9a326d88a103e5e1b1b3a4cea4830443caf0947cd176`.
The original phase/metadata/jobs are under `runs/raw-retention-collection-01/`.
Receipt preservation does not mean all 43/85 member bodies were host-exported or
re-read, or that these raw copies are verified reconstructible archives.
The independent actual review is
`preparation/reviews/raw-retention-and-selection-staging-actual-independent-review-01.json`
(21,279 bytes, SHA-256
`4282848ad68cb50a26f328be7beb9cb63044fcea961c2ab349d61ed610a47a70`).

Selection staging bound eight actual sources and eleven cases without inventing
failed M4/campaign cases. Prepare run `20261027T114736672-Prepare` closed with
controller receipt 7652/zero at `2026-10-27T11:52:09.8179740Z`. Fifteen bound
native-zero collection responses preserved the preparation metadata and snapshot.
The independent review is
`preparation/reviews/lifecycle-Prepare-firstpass-actual-independent-review-01.json`
(17,643 bytes, SHA-256
`4059a4fae1ead3d89550b24d26ef83c12c34980f1d326d306162f1e54026c067`).
Eleven cases and 22 original-report references were frozen. This review does not
claim host retrieval of all 22 prepared report bodies, the observer receipt or
the two configuration-job originals. Eight source-controller closures used the
native-policy absence branch; no CIM fallback was recorded in this preparation.
This is preparation, not successful maintenance/removal/retained-reader testing.

### First Maintain attempt refused before installer launch

Maintain run `20261027T120703909-Maintain` closed with controller receipt
7664/exit one at `2026-10-27T12:10:27.9147530Z`. The private helper's first read
of `E:\candidate-j.exe` failed with `Unsafe root path`: its storage reader
refused the drive-root parent before reaching the installer `Popen`. Accepted
jobs were empty and installer/concurrency/native-analysis markers were absent.
A separate read-only diagnostic returned native zero and observed the known
application server PID 3096 still running at that observation. It does not prove
a server exit or any maintenance, cancellation or data-preservation success.

The independent record is
`preparation/reviews/Maintain-drive-root-input-failure-independent-review-01.json`.
This pre-launch input failure remains failed. The second attempt changed only
the installer parameter to the original browser download,
`C:\Users\Researcher\Downloads\OpenT1D-test-windows-x64.exe`, retaining the exact
201,697,149-byte J identity and unchanged helper/source checks.

### Maintain02: inner installation passed; report wrapper failed

Run `20261027T122917125-Maintain` closed with controller receipt 1320/exit one at
`2026-10-27T13:39:44.6031200Z`. The inner graphical installer returned zero and
the concurrent-launch refusal passed. A complete audit matched all 24,282 files
and 773,858,663 bytes. Preservation metadata records 6,987 original files
byte-identical and 36 additions. These bounded successes do not change the
original failed phase or establish its remaining active-work/report gates.

The report-check wrapper used `reports-after-maintenance.json`, already created
by the launch probe. Its successful-result save failed with `FileExistsError`
at lifecycle line 302; the exception-result save at line 304 collided with the
same file. The original 549-byte probe JSON is not the missing report-check
result. The 3,148-byte traceback and probe body are preserved under
`runs/lifecycle-Maintain-report-diagnostic-01/`; the probe identified server
5788 at that observation. No original report was overwritten.

A late sampling job was cancelled with exit one, cleanly and without forced
cleanup, but the native-analysis milestone was not observed after a connection
reset. Active numerical cancellation is therefore **not proved**. The independent
union review is
`preparation/reviews/Maintain02-actual-union-independent-review-01.json`
(2,929 bytes, SHA-256
`3dc51cfb5bb550c056ec24b3a3afc65898fc4271d74c5c79d67730d36b0f379a`).

Five core originals and three separately requested, phase-declared metadata
bodies are fully preserved: inner maintenance, installed payload and data
preservation. A read-only collector then exited with `0xC0000005` (PID 2552,
22.273396 seconds) after ten earlier successful queries, including nine partial
snapshot chunks. Its cause is unknown; that script already used CNG hashing.
The whole 1,664,086-byte pre-maintenance snapshot body remains only partially
host-preserved. A distinct new declared query retrieved the complete 4,476-byte
cancelled-job body (SHA-256
`187575ac242715244f4c1fe276681a95cd980ba0e35178277164b2ae36a307e9`);
this closes its body-collection gap without proving active numerical analysis. No unchanged failed-query retry or
provider-cause conclusion is inferred. Later three small metadata queries were
distinct previously unexecuted requests. The collection failure is retained
separately in
`preparation/reviews/Maintain02-collector-crash-small-selection-review-01.json`.

### Separate targeted report reconciliation and stop passed

Focused run `20261027T135752736-Reconcile` closed with controller receipt
6532/zero at `2026-10-27T13:58:56.1810910Z`. Its GET-only check child PID 9000
returned native zero in 20.508 seconds within the fixed 2,440-second envelope.
The complete 4,100-byte comparison report is host-preserved (SHA-256
`2a3fe24d740809c03e47d0571b82960698066f746ac65e400baff0999d885c00`).
Its eleven ordered cases and 22 report hashes match the immutable prepared-case
record. All four collection queries returned native zero, with raw common
records and child logs preserved under
`runs/focused-report-reconciliation02-collection-actual-01/`. The final review
`preparation/reviews/focused-RF-and-Maintain-cancel-final-independent-review-01.json`
(SHA-256 `2cead2999f9139fd6ff0dc0bc492e023c3667c56bdaa4625549d5caa0506b9f0`)
verifies this report and the separately collected cancelled-job body. No installer
or model was rerun.

One normal CLI stop (PID 8968) returned native zero in 14.121 seconds within
180 seconds. Held server 5788, creation FILETIME `134375819319159449`, exited
native zero; at completion the session was absent, installed process count zero
and gate free, without forced cleanup. The fixed 30-second held-server bound
was unchanged. These are targeted report/stop results, not a full maintenance
pass: Maintain02 remains **failed**, and active numerical cancellation is still
unproved. Uninstall, SavedReader and fresh I-to-J upgrade remain open. No GitHub Actions run,
independent participant session or public release is claimed. All prior failures,
including unresolved attempt 09 M3, retain their original scopes.

### Uninstall05 and its subsequent observer failed

Run `20261027T141257487-Uninstall` closed with controller 2708/one at
`2026-10-27T14:19:41.9677670Z`. Native analysis was observed before the graphical
uninstaller launch (job `job-274341da8d0b445f871aee224d376d72`, PID 4232), and
the job was still running after spawn. NSIS parent 9072 was recorded, but its
PowerShell child query PID 6072 exceeded the fixed 20-second bound. The source
observer failed before the operator clicked Uninstall. Five common originals
and eight diagnostic originals are preserved under
`runs/lifecycle-Uninstall-common-01/` and
`runs/lifecycle-Uninstall-failure-diagnostic-01/`. The independent review is
`preparation/reviews/Uninstall05-failed-operation-actual-diagnostic-independent-review-01.json`
(SHA-256 `e7d435425e56e90c4e84ffdc91035b4c5ed7dc7cbb20cd5b54b8c14efad23b45`).
The sampling job later failed with exit one and `Operation deadline exceeded`,
with no current PID, remaining children or forced cleanup. This was its own
operation deadline, not successful cancellation by the uninstaller.

A separate observer, PID 7156, started for the existing uninstaller but did not
produce Ready, its six control logs/results or a completed observation before
the original `2026-10-27T14:49:18.6825749Z` deadline. No Uninstall click occurred.
A later native-zero event query positively matched Application Error 1000,
record 419, to PID 7156 and creation `0x1dd6621a59d555f`: PowerShell access
violation `0xC0000005` at `2026-10-27T14:44:29.7678189Z`, module unknown. This
establishes the event identity, not a separately observed process exit code or
root cause. Later scoped process metadata found neither 7156 nor its children;
the old Poll default of running with no completion is not a heartbeat.

At 15:06:40 the operator normally cancelled the old NSIS window. A subsequent
native-zero metadata query found only application server 9104 among the scoped
owners, with no 9072, 8508 or 6072; metadata absence does not prove their native
exit codes. The job remained failed. The preserved event and post-Cancel proof
are reviewed in
`preparation/reviews/observer7156-event-oldUninstall-postCancel-independent-review-01.json`
(SHA-256 `3b344d99d6ab0e2314810d69217be32c60d2bd65800add2f491bb8e7c0438ed5`).
Uninstall, active-job cancellation, SavedReader and fresh I-to-J upgrade remain
open. A new private Python controller is source preparation only; no new executed
test or pass follows from it. All earlier failures remain preserved.

### Separate controlled cancellation and retained-reader gates passed

The original failed Maintain02 and Uninstall05 phases retain their outcomes.
A new private controller's first attempt failed during runtime verification
before a model/uninstaller launch; its Start capture was incomplete. Its second
attempt passed prerequisites but failed on normal/extended path representation
before recording native analysis or launching the uninstaller. Its job later
failed its own operation deadline, without forced cleanup or remaining owners.

Controlled run `20261027T160320110-UninstallCancel` then passed its targeted
scope. The operator clicked Uninstall at `16:05:17.741305Z`, after the observer
had bound a running native analysis, and closed the completed window at
`16:06:21.702984Z`. Held uninstaller parent 3960, child 4184 and server 9104
exited native zero; analysis 8432 exited one. Job
`job-8f449f5105674763bfe427d64f2dcb7d` was cancelled cleanly with exit one,
no forced cleanup and no remaining owned processes. Worker 3920 exited native
zero under its launcher's held handle; the launcher's own native exit was not
observed. Full originals are preserved in `runs/pure-uninstall03-closure-actual-01/`.

The first postcheck controller failed its canonical Windows run-name guard
before any audit. Its corrected successor passed three read-only postchecks:
the main and retained-repair J payloads each verified all 24,282 files and
773,858,663 bytes; all 7,023 original data files remained byte-identical, with
728 additions. Those originals are under
`runs/uninstall-postchecks02-closure-actual-01/`. Separate metadata under
`runs/uninstall-postmetadata02-actual-01/` confirmed absent main registration and
shortcuts, the retained J reader shortcut, absent session and free gate. Its
process observation covers CIM-visible paths; held native exits are the primary
stop evidence. Source corrections preserve all original failures and time limits.
The component reviews are
`preparation/reviews/pure-uninstall03-actual-controlled-cancellation-independent-review-01.json`,
`preparation/reviews/uninstall-postchecks02-actual-independent-review-01.json`
and `preparation/reviews/uninstall-postmetadata02-actual-independent-review-01.json`.

The first executed focused reader controller, run
`20261027T163702806-SavedReaders`, failed with `KeyError` before any operation:
its private preflight looked up a nonexistent `experiments/__init__.py` in J's
manifest, where `experiments` is a namespace package. Worker 8688 exited one;
launcher 1216 was later absent, with its own native exit unobserved. The corrected
controller removed only that invalid lookup, retained the Windows canonical-case
fix and passed host checks against the actual producer/postcheck/preparation
bodies before execution. No model, reader or audit ceiling was extended.

Run `20261027T164512905-SavedReaders` passed using the actual retained J shortcut.
Worker 8780 and server 7780 exited native zero; the shortcut-properties child
8364, reader child 6396, normal-stop child 2072 and final-audit child 8240 also
exited native zero. The reader operation took 1,344.719 seconds within its fixed
14,451-second aggregate. Eleven fresh jobs completed zero with no current PID,
forced cleanup or remaining processes: two sampling, two M3 reconstruction,
four library verification, two durable and one observation reader. Eleven ordered
outcomes and 22 original report hashes match the immutable preparation
`aa31571a6a23c58ed09b639d3c2238d2813bf90f49c0291c214102bf7cf8433f`.
The separate final audit took 136.235 seconds within 1,800 and verified the exact
J payload. These are saved-reader/report-verification results, not new numerical
model evaluations. The normal CLI/server bounds remain 180/30 seconds.

Three fixed collection batches preserved 38 originals and a separate declared
query preserved all eleven raw job bodies under
`runs/saved-readers03-closure-actual-01/`. The complete 21,919-byte reader result
has SHA-256 `4f8c3c0393b923649aa318fbdf82748888822efa28c816a87e837c20d3f213e6`.
The final independent review is
`preparation/reviews/saved-readers03-actual-full-closure-independent-review-01.json`
(7,149 bytes, SHA-256
`747dca3de814ec0596809779ea652c4e3cf87b1ee9e0f75efe6a99f2538d7991`).
The 22 report bodies were checked by the installed helper and their hashes
matched on the host; they were not all freshly copied to the host here. Reader
bookkeeping legitimately changes after the earlier postcheck, so its 7,023-file
preservation result is not a new all-data-unchanged claim after the reader run.
The launcher's own native exit remains unobserved. Fresh I-to-J upgrade,
complete maintenance acceptance, failed Campaign/M4 acceptance, independent
human use, signing/public reputation and full VM/TPM validation remain open.

### Attempt 11: fresh I admission and bounded I-to-J upgrade passed

On the separately restored fresh clone, Baseline run
`20261027T173958158-Baseline` recorded controller 5828/zero at
`2026-10-27T17:40:18.9789730Z`. It proves application absence and idle only.
Read-only boot facts separately confirmed ordinary Researcher/AMD64, licensed
Windows, disconnected NIC and exact configured Worker02. Dependency inventory
retains its sealed baseline ancestry; no full VM/TPM restore validation follows.
The Baseline review is
`preparation/reviews/fresh-upgrade-Baseline-actual-independent-review-01.json`.

Original InstallI under helper04, run `20261027T174740323-InstallI`, remains
**failed**: controller 6680 recorded one at `2026-10-27T18:36:24.6304740Z`.
Graphical Finish and healthy automatic startup were observed. Frozen control
flow reaching the audit indicates installer return zero, separately from any
retained installer-handle proof. The private audit child returned signed
`-1073741510` / unsigned `3221225786` (`0xC000013A`), with four empty logs and
no completed payload/explicit shortcut artifacts. The status does not establish
a cause, sender or foreground click target. A single normal CLI stop and idle
check passed afterward. The actual review is
`preparation/reviews/fresh-InstallI-interrupted-audit-actual-independent-review-01.json`
(SHA-256 `c39256e8d1ce06a2418bb88b760fc2178854009980e1fb8e14058b46424c2fa5`).

Separate focused admission03, run `20261027T190741053-IAdmission`, completed
its inner full I audit with held child 7308/native zero. The 756-byte result
has SHA-256 `9d278604f922146a799a25887bf0fdff44132da5c37606d2673b49388bcaa62f`:
all 24,282 files and 773,843,895 bytes matched I's exact manifest. The wrapper
nevertheless failed because PowerShell treats `$I` and `$i` as the same variable;
a loop overwrote its build identifier before the post-audit assertion. The
failed phase and successful inner audit remain distinct in
`runs/I-postinstall-admission03-closure-01/`.

Corrected admission04, run `20261027T192436870-IAdmission`, subsequently
**passed** its separate component scope. It verified the full original I
payload against manifest
`ea2f198b73b8fca7986f6e7188843799490e91f33bfe890bf2fbc105852eafd9`, the actual
I shortcut and basic desktop profile. Audit child 3832, probe child 1356 and
normal-stop child 4676 exited native zero; held server 4804 exited native zero.
The manager completion recorded zero, and before/after checks found no session,
a free gate and zero CIM-visible installed executables. No installer or model
was dispatched. The unchanged individual audit/probe/CLI ceilings were
1,800/1,800/180 seconds. Fifteen full originals and their closed-Poll binding
were independently verified in
`preparation/reviews/I-admission04-actual-closure-independent-review-01.json`
(3,749 bytes, SHA-256
`793ef11f1f93c4ddc428c8519a862be659e4c20575265714d858c6b6cd1fa57f`).
This does not relabel original InstallI or admission03, and is not an I product
archive inventory, model case or fresh I-to-J upgrade pass.

The next OriginalIGuard07 controller, PID 5832 with creation FILETIME
`134376030298196639`, crashed abruptly. A bounded native-zero diagnostic query
matched Application Error 1000, record 322, to that exact process identity:
`0xC0000005` at `2026-10-27T19:30:41.2081289Z`, module unknown. The controller
was later absent, but no separately held native exit code was observed. Its
phase, redirected stdout/stderr, completion and body were absent; no product or
model dispatch was observed. A Poll default of running with no completion is
not a heartbeat. These observations do not identify the failure location,
provider, Get-FileHash/TCG cause or an internal product outcome. Source-bound
Start, absence and event diagnostics are independently reviewed in
`preparation/reviews/OriginalIGuard07-abrupt-controller-actual-independent-review-01.json`
(5,538 bytes, SHA-256
`4949a28720cecb0d7fccfff57f890caac64cad35047aa3202b2bd5b40e85b98f`).
The original crash remains unchanged and its cause is unknown. The following
owned-controller outcomes are separate tests, not proof of a crash remedy.
CP10 retains its original closed scope; no later result is adopted into it.

#### Owned I guard and fresh fixture

A second owned OriginalIGuard07 run, `20261027T194625950-OriginalIGuard`,
passed with held controller 4560/native zero and a six-file inventory. The
1,759-byte inventory body has SHA-256
`f1287ce1fb4b4c9f9c6b36d20442489661f2f386d9bebe6cdf0c0f0d9e41f9e3`.
The six member bodies were hashed inside Windows, not individually copied to
the host. Its bounded inventory scope does not establish a model outcome.

Fixture run `20261027T195400404-FixtureI` then passed with held controller
3796/native zero. Actual I case `obs-study-7c198c20b2b345e2898e278abce6876f`
used one invented person, 32 draws and three variant pairs. Example, freeze,
run and I-reader jobs all completed zero without forced cleanup or remaining
owners. Six complete artifact bodies include the two original reports:
125,130-byte JSON, SHA-256
`b7560c5000bfaddefd0984aed311a6d93830ac8a70a9a42c690ab610d6c18dad`,
and 5,715-byte Markdown, SHA-256
`3da7acc4c925ed7e80d7dd23f41c50668bae2cc7c68e183c6bce0c4545776f29`.
A single Start response used an incorrect host output directory; its six raw
files match the preserved canonical copies and its exact source/actor/native
zero binding was reviewed. This is an explicit single-response path exception,
not a general physical-source-root relaxation or repeated Start.

Optional I inspections 12 and 14 crashed with `0xC0000005` and were not retried;
13 of 18 inspections succeeded, while 15–17 were not dispatched. Five optional
captures remain unresolved in `optional-capture-gaps.json`. Essential fixture
and six whole-artifact evidence remain verified; complete optional capture is
not claimed. The independent case/body review is
`preparation/reviews/FixtureI07-essential-six-originals-independent-review-01.json`.

#### Fresh J upgrade completed its stated scope

Run `20261027T200416355-Upgrade` completed at
`2026-10-27T20:54:42.8316060Z` with held controller 5320/native zero.
The phase finished timestamp, `20:54:42.6999030Z`, is distinct from controller
completion. The exact J payload audit verified all 24,282 files and 773,858,663
bytes against manifest `7b0a2fad4fe36479b885189cb40c7e2c7a0e20de5cebc4f900c764d26b97b617`.

Its preservation check covered 95 original files: **93 byte-identical**, exactly
two precomputed `native_reader_verified` → `recorded_verification` bookkeeping
transitions and zero additions. These changes were bound to each original
schema/path/ID and exact before/after size/SHA before upgrade; neither report
nor arbitrary data changes were allowed. `all_original_bytes_identical` is
**false**, while the declared preservation contract passed. The two changes
belong to the original I reader job and observation entry; both original report
bodies remained byte-identical. The individual 95 after-bodies were not all
separately copied to the host; the installed probe measured the comparison,
with the declared aggregate and exact expected transitions independently checked.

Fresh J reconstruction job `job-018e264d8d3f49619872e712b712b116` completed zero,
with no current PID, forced cleanup or remaining owners. Its recorded output
parity matches both original I report hashes. The freshly transferred report
bodies are the frozen original I reports after upgrade, not additional host
copies of the newly reconstructed J outputs. All 18 focused native tests ran
with zero failures, errors or skips and no private directory override. Two
normal installed CLI stops returned zero; before/after idle proofs found no
session, free gate, zero installed executables and no timeout markers or force.
The observer's own native exit was not observed; its held inner-controller exit
is separate evidence.

The J Finish/Open-checked screen and new localhost59192 home page were reviewed
at original resolution. An older61635 background tab's Failed to fetch and the
Edge Restore pages prompt remain historical/browser context. They are not an
inferred J failure or substitutes for the native/payload evidence. No UI or
keyboard operation was reported after Finish through the actual phase closure.
The retained I manifest/shortcut were verified, but **no retained I reader was
executed after upgrade**. The manifest body was reused from the exact known host
reference after matching the current guest hash/size; no fresh 36-chunk transfer
is claimed. Thirty-five optional J operation-log captures were not queried, so
complete fixed-roster capture is not claimed.

Core/observer originals, primary bodies, the fresh J job and original reports
are preserved under `runs/I-continuation07-Upgrade-01/`. The independent reviews
are `preparation/reviews/Upgrade07-primary-bodies-independent-review-01.json`
(8,201 bytes, SHA-256
`9ff37b09e5c3a2a323bdadfe564a8f2c37dd4f28f3aee8573bf552ec5f944450`)
and `preparation/reviews/Upgrade07-final-artifacts-dedup-independent-review-01.json`
(5,739 bytes, SHA-256
`ff86706026615b15d48efced2d7fc3350cb4f5ae98f1afa92de81fd8680a2b0a`).
This closes the bounded fresh I-to-J test. Original InstallI/admission/guard,
Maintain02/Uninstall05 and older upgrade failures retain their outcomes;
Campaign/M4 numerical acceptance, complete maintenance, independent human use,
signing/public reputation and full VM/TPM validation remain open.

## Windows acceptance still open

Read-only inspection of GitHub Actions on 22 October found jobs failing before
any step started.
The [check annotation for run 39799559954](https://github.com/OpenT1D/OpenT1D/actions/runs/39799559954)
reported failed recent payments or an insufficient spending limit. No new hosted
run was dispatched or claimed. The manual workflow is preparation, not hosted
execution evidence; the local Windows attempt above is separate.

Recovery attempt 10 normal activation passed after explicit user authorization.
Its application acceptance remains open. Remaining acceptance includes complete
workflow coverage on the current candidate, complete maintenance acceptance,
maintenance during active numerical work and independent
installation-to-report use. The separately passed controlled cancellation,
post-removal checks and eleven retained-case readers close only their stated
scopes; they do not relabel failed Maintain02 or Uninstall05. The separately
passed fresh I-to-J test closes only its case/preservation/J-reader/native scope.
I's clean
install/startup, shortcut pass and explicit warm native pass close only their
recorded scopes. Its original native failure, two M4 harness failures, actual
M4 run failure and focused preparation failure remain preserved. J's original
upgrade test failure is also retained. Its separate CompleteUpgrade, synthetic
MMTT API/reader, Repair and Reinstall passes and the fresh-baseline checks
close their stated scopes. The separate attempt 09 installed-J 124-test native pass
and post-test full audit close that native/integrity scope. The separately closed
sampling-information-loss API case closes its stated synthetic workflow/reader
scope. Genuine sampling cancellation and its interrupted readers close only
that separate scope; complete workflow and lifecycle coverage remain open.
H's partial API and Reinstall/Uninstall/SavedReader passes do not establish
those results for J or erase H's strict Repair failure. A/C graphical installation
and C's browser MMTT analysis/reconstruction remain separate evidence.
The earlier ISO-staged candidate checks did not exercise browser download. The
new controlled local download observes a restricted-environment SmartScreen
scan-unavailable/Keep path; public reputation and signing remain unverified. Browser interaction and API-driven workflow checks must be reported
separately. Curated RF checkpoints preserve the reported outcomes; a complete
synthetic-archive export is not claimed or required to report those outcomes.
Signing and public distribution remain undecided. These gates are separate from
local implementation checks and scientific or empirical acceptance.
