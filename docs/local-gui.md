# Use the local experiment interface

For the initial public exercise, use **Explore paired meal tests** and the
sampling task with root tooling. The M4 forms preserve historical routes whose
native runtimes are excluded from automatic public setup; see
[the current installation policy](publication-security.md).

The local interface exposes a complete
[maintained M4 initial-load study](m4-maintained-study.md),
[campaign management](gui-campaigns.md), a
[read-only archive library](gui-archive-library.md) and
[durable experiment archives](durable-experiment-archives.md) in a local browser.
OT-042 also implements [synthetic M3 forecast/comparison](gui-m3.md), and
OT-054 adds [paired observation sensitivity analysis](observation-analysis.md).
OT-055 adds [full versus reduced sampling comparisons](mmtt-sampling.md) using
the same owned process lifecycle and fixed native analysis core.
The maintained M4 form selects `m4-study-secure`; equations, numerical
criteria and native archive readers remain responsible for scientific results.

## Start locally

The [Windows installation candidate](windows-installation.md) includes every
current GUI route, three private runtimes and a launch shortcut. It uses a
separate writable workspace, verifies included components offline and provides
**Exit OpenT1D**. The canonical installation guide owns its platform scope,
retained readers, repair and open Windows acceptance checks. The following
commands describe the developer checkout route.

For the prepared human test, use the separate
[test-session packet and launch files](gui-test-session.md). They retain the
same GUI and scientific routes; Windows/WSL needs its own host verification.

Use Python 3.12 and uv in an identified macOS or Linux checkout:

```sh
uv sync --locked
.venv/bin/python -m experiments.gui
```

The command prints a loopback URL and opens the browser. Use `--no-browser` to
open the printed URL yourself or `--port 8765` to select a port. The service
binds to `127.0.0.1`. A stopped/restarted server has a new session token; reload
the page rather than reusing a stale browser session.

An operating-system lock permits one GUI server per checkout. A second server
is refused before it can load or alter that checkout's job administration.
Stopping the server with Ctrl+C, SIGTERM or SIGHUP requests owned-worker cleanup
before releasing the lock.

## Find your workflow

The interface opens on **Start**, explaining the virtual lab and its four
research questions. **Glucose forecasts** compares 30-minute predictions with
later values in invented glucose data, with errors and scored-prediction
coverage. **Insulin secretion** compares models under the same initial
carbohydrate loads, with glucose and insulin curves over four simulated hours.
**Paired meal-test analysis** compares a paired 0–120-minute secretion
conclusion across frozen engineering assumptions on invented observations.
**MMTT measurement times** compares the full reference with fewer observed
times under those same assumptions. Both meal-test routes start with compact
supplied settings; optional details, named plans and saved reports remain
available. See the [paired analysis guide](observation-analysis.md) and
[sampling comparison guide](mmtt-sampling.md) for their complete flows. The
[OT-057 verification record](research/ot057-uiux-verification.md) records the
seven interface fixes integrated into main and their internal macOS retests.
Each question has its own **Explore** button. The two MMTT examples use root
tooling in the public source checkout. Other cards require their declared
runtimes; the historical M4 runtime is excluded from automatic public setup.
Use the task guide and installation policy to check availability for the selected
checkout or packaged profile. Example results do not establish performance in
people.
**Results → Your experiments** opens retained own-workspace
M4 studies, M3 forecasts/comparisons, paired observation and sampling analyses, campaigns
and registered durable packages
through their existing report/control views. **Added archives** contains the
separately registered read-only archive library. A result shortcut changes the
view; it grants no new execution, resume or reader authority. **More** contains
**Repeat experiments** and **Export / open archives**. The same small header works
on desktop and mobile; there is no separate dashboard or sidebar.

The secretion study shows its selected models, fixed `adult#001` reference
profile, 240-minute observation window and synthetic inputs before checking.
Forecast intake is explicitly labeled for synthetic observations, including
**Use your own synthetic files**. Optional files, execution budgets and source identities stay behind **Options**
or an explicitly labeled disclosure. Invalid fields open their containing
options automatically so validation remains actionable. Forecast preparation
reveals its form only after inputs are selected. The forecast and secretion forms show
**Check setup** first and reveal **Run experiment** only when the unchanged
native readiness rules permit it. Missing M4 environments reveal the explicit
installation action; checking and running remain separate operations.

Switching views preserves the current configuration and displayed evidence;
it neither starts nor cancels a workflow. Browser Back/Forward and the view's
URL fragment return without resetting its form. Reloading reinitializes the
interface. M4 editable inputs are saved in bounded, workspace-scoped storage in
this browser tab and restored on reload. The draft notice offers **Reset to
supplied examples** and reports storage failures. Closing the tab may discard
the draft; it is not a portable experiment archive. Reload always requires a
fresh setup check. Other workflow drafts and checked readiness are not restored.
A running operation stays visible above every view. For the two MMTT routes,
**View progress** opens running progress/cancellation controls, **View result**
opens a finished operation's report and **View setup** opens a finished setup
operation without a result. Other routes retain **View operation**. **Recent
work** on Start opens retained operations in their corresponding workspace.

**Results → Your experiments** orders all workflow types by latest recorded
activity and shows its local date/time. Legacy entries without a recorded time
say **Time not recorded**. Failed and cancelled experiments remain visible.
M3 example preparation and setup checks explicitly state that no predictor has
run; report coverage applies only after execution or saved-analysis checking.
M3 metric summaries show four significant digits and mark missing metrics
**unavailable**. Original JSON and native downloads retain exact stored values;
display rounding changes no calculation or acceptance threshold.

To repeat a study, open **More → Repeat experiments**, choose a current frozen
or saved own-workspace configuration in **Study to repeat**, then select
**Use this study** and set **Repetitions per study**. Check the new campaign
before running it. This creates a fresh one-study draft rather than resuming a
saved campaign. Optional matrix editing remains in **Study configurations and
execution limit**; the [campaign guide](gui-campaigns.md) describes that route.
M5 remains a report-review route in **Results**; navigation adds no M5 execution.

## Configure and check

The initial form selects two attributed supplied models and the existing
0/15/30 gram initial gastric-load conditions. These are initial conditions,
not timed meals. Review optional model details to select your own reviewed
Python and matching declaration files within this checkout, using the workspace
browser or a relative path. Two to eight distinct source IDs are supported;
stage/source execution budgets can be changed in the optional settings.

**Python model** is the calculation code (`.py`); **Model declaration** is its
matching JSON identity, ancestry, units and interface. Keep the supplied pair
together. **Source ID** is a short name starting with a lowercase letter, using
only lowercase letters, numbers, underscores or hyphens (1–64 characters).
The fixed observation window is 240 simulated minutes, distinct from computer
execution time.

**Check setup** saves a new immutable configuration and snapshots its source
bytes under ignored `results/gui/`. Validation is passive: it does not execute
the selected Python. The registered task also checks required locked runtimes.
If they are missing, **Install task environments** explicitly installs them;
the UI then performs a separate configuration check before permitting a run.
Installed environments alone do not establish numerical or scientific success.

Selected sources are trusted local Python and run with your permissions. The
local service is a bounded control surface, not a sandbox. Hidden/symlink paths,
foreign web requests, arbitrary shell commands and reused output destinations
are refused. GUI logs and inputs remain local and outside version control.

## Run, cancel and inspect

**Run experiment** starts the registered CLI as an owned subprocess. One operation
is active at a time. Progress shows observed operation states, not an estimated
completion percentage. **Cancel operation** requests native cleanup and retains
the available evidence. Closing the browser tab does not cancel a study;
use the cancellation button or stop the local server.

The operation strip and M4 activity panel show elapsed computer time from
recorded process timestamps. The native M4 runner does not report live progress
per model or condition; the GUI explicitly says so. No completion estimate is
inferred. Operations in another workflow use the global **View operation**
shortcut; their completion messages do not become M4 study results.

The results view summarizes recorded execution, available comparison coverage
and the saved-analysis check separately. It displays numerical acceptance and full planned/accepted
source/load/pair denominators, per-source outcomes and the native trajectory
figure. Failed sources remain visible. **Check saved analysis** invokes the
standard-library native reader, including explicit failed-archive handling.
Reader verification and report completeness remain separate. Downloaded JSON
and Markdown are the native report artifacts, not recomputed UI metrics.
Current verification is withdrawn if archive or displayed report bytes change.

For a text alternative to the maintained M4 figure, open **Read graph data** and
choose **Load saved graph values**. The table displays values from the native
JSON whose byte identity matches the displayed report. It includes the accepted
model curves and the same first accepted source's control/reference curves as
the native SVG. It calculates no trajectory values or metrics, performs no
interpolation and changes no numerical criteria. Native JSON remains the full
artifact; this bounded table view has a separate size limit.

GUI job receipts live beside the native `archive/`, never inside its scientific
inventory. Preserve the full archive and a compatible reader checkout.
Before disposing of an implementation worktree, explicitly
[export a durable package](durable-experiment-archives.md) to independently
retained storage with `--archive-store`. A restart retains recorded operations
but does not adopt saved process IDs or silently resume
interrupted work. Retained verification markers record prior evidence;
use **Check saved analysis** again for current verification after restart.
An unsealed interrupted archive may have no reconstructible report; keep its
evidence rather than labeling it complete.

Native supervisors own scientific-worker cleanup. The GUI tracks observed live
descendants by their OS start identity, including separate sessions and owner
death; it never derives signalling authority from saved job receipts.
Cleanup covers descendants observed while the server is live. An uncatchable
server kill or machine failure cannot guarantee that cleanup ran.

## Scope and evidence

Single studies and [maintained campaigns](gui-campaigns.md) use the existing
fixed synthetic profile/grid. The [archive library](gui-archive-library.md)
indexes eight task types and verifies maintained M4, synthetic M3 and synthetic M5 evidence from explicitly
allowed read-only roots. Campaign resume selects own-workspace opaque IDs.
Durable archive registration grants read-only verification/reconstruction;
restoring or registering a package grants no execution or resume authority.
Historical archives use their own compatible reader checkouts, through the
[historical-reader guide](historical-readers.md).

Internal browser/process/numerical verification is separate from independent
researcher usability. The [GUI researcher exercise](gui-researcher-exercise.md)
defines a proposed four-to-six-person formative study, including finding own
results, incomplete evidence interpretation and keyboard/error-recovery tasks;
no participants or independent results are implied by this guide.
Synthetic reports establish no clinical dose, treatment benefit or biological
model ranking.
