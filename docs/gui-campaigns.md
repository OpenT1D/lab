# Manage maintained M4 campaigns in the local GUI

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

Use the [local interface](local-gui.md) to prepare an ordered matrix of frozen
studies, repeat its cells and retain every execution attempt. The GUI selects
the same [maintained campaign CLI](maintained-campaigns.md) and authoritative
readers. It adds experiment administration around the existing synthetic M4
study; numerical criteria, source ancestry and native units remain unchanged.

## Repeat one study

Open **More → Repeat experiments**. In **Study to repeat**, choose a current
frozen study configuration or a saved study from this GUI workspace, then select
**Use this study**. If a current configuration has not yet been saved, configure
it in **Insulin secretion** and use **Check setup** first. The selection loads
the already captured configuration as a new one-study campaign draft; it replaces
the current unsaved matrix draft. It neither executes models nor resumes a saved
campaign.

Choose **Repetitions per study**, then use **Check campaign** and, when ready,
**Run campaign**. If environments are missing, explicitly use **Install task
environments**, then **Recheck campaign**. Setup and execution remain separate.
The fixed reader and numerical criteria still assess every retained attempt.

## Prepare an immutable matrix

Configure the study form with reviewed local sources and a declared subset of
the existing initial gastric loads. In **More → Repeat experiments**, open
**Study configurations and execution limit**, enter a unique lowercase
cell ID and choose **Add current study as cell**. This captures a separate
immutable study configuration. Later changes to the study form do not edit
that cell. Add more cells, replace a cell by capturing the form again, or
remove/reorder cells before preparing the matrix.

Choose one to eight repetitions per study and an optional execution limit for each
attempt. The bounds are one to thirty-two cells and at most 128 planned slots.
Cells execute in displayed order, with repetitions in ascending order. Planned
source/load cases remain visible separately from complete accepted slots.
The per-cell native stage/source budgets remain in its captured configuration.

**Check campaign** freezes a new matrix and checks its inputs and installed
runtime identities without executing models. Editing the draft requires a new
matrix and check. In the campaign panel, **Install task environments**
explicitly uses the existing locked setup for `m4-study-secure`; choose
**Recheck campaign** afterwards. Every installation attempt invalidates previous
study and campaign readiness because it can change shared environments,
including when installation fails or is cancelled. The ordinary study panel
retains its separate automatic study check after successful installation; that
check does not restore campaign readiness.

## Execute, cancel and resume

**Run campaign** starts a fresh campaign through the fixed CLI. Study, campaign
and library operations share one active worker and the checkout's GUI manager
lock. The interface shows observed process states and retained accounting.
Source Python is trusted local researcher code and runs with your permissions.

**Cancel operation** asks the live owner to stop dispatch and clean up nested
workers. The GUI allows ninety seconds for cleanup and reporting, outside its
execution deadline; the campaign and native owner retain their shorter cleanup
windows. A cancellation during final reporting can leave completely accepted
scientific results while the GUI operation records cancellation. Already sealed
scientific outcomes remain immutable.

Select an existing own-workspace campaign and choose **Check for resume**
before **Resume remaining slots**. The worker repeats readiness checks, and the
CLI verifies the original runtime, inputs, prior sessions and native archives.
Accepted slots are reused; remaining slots receive new linked attempts. A
no-op resume starts no model attempt. A changed matrix requires a fresh campaign.

A restart retains configuration and campaign records, resets readiness and
records earlier verification. It does not adopt saved process IDs or silently
resume work. Hard-killed, unsealed output remains forensic evidence. A later
explicit resume/reconstruction can refuse it; preserve that evidence and start
a fresh campaign rather than repairing its seal.

## Inspect and reconstruct evidence

The results view keeps all planned slots, unsuccessful/unattempted outcomes,
linked attempts, native partial denominators and numbered sessions. Process
status, complete-slot coverage and reader verification are separate. Results
remain per cell; the GUI provides no pooled curve or automatic model ranking.

Find own campaigns through **Results → Your experiments** or the saved-campaign
list in **Repeat experiments**. In the selected campaign, **Check saved analysis** selects the fixed
standard-library reader, with explicit
failed-archive handling, and writes a fresh report outside the scientific
inventory. This requires no numerical environment check or model execution.
It verifies original archive inventories around reconstruction. **Download JSON**
and **Download report** return the canonical reconstructed bytes.

A verified snapshot records the worker's source check and report identity.
Passive HTTP browsing reads bounded cached reports and does not rehash the
entire campaign. Its freshness label states that source files have not been
rechecked since the worker. Reconstruct explicitly after external changes.
Detected unavailable/changed cached artifacts, failed reconstruction checks
and a server restart withdraw the live verification marker.

The [read-only archive library](gui-archive-library.md) handles explicitly allowed
external scientific archives. Campaign resume selects opaque IDs of campaigns
created in this GUI workspace. Historical scientific archives retain their
[compatible readers](historical-readers.md).

The existing bounded campaign workflow is implemented and internally verified
locally. The [execution record](research/experiment-workspace-verification.md)
binds that native, process and browser scope; verification of the simplified
study-selection presentation now includes the local browser check of a saved
M4 configuration producing a fresh one-cell draft, focus on repetitions and
closed optional matrix settings. The follow-up's locked repository suite and
documentation build pass. Fresh native campaign execution was not repeated in
this presentation follow-up; the existing native record retains its own scope.
That evidence remains separate
from the prepared [independent GUI exercise](gui-researcher-exercise.md),
biological validity and human-data assessment. Hosted verification and
publication retain their separate evidence steps.
