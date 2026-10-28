# Browse existing archives in the local GUI

The [local GUI](local-gui.md) can register archives from explicitly allowed
read-only directories. The original archive remains authoritative. Metadata
reading, native reconstruction, numerical acceptance and completeness are
separate observations.

## Find your results

Open **Results** to find two groups. **Your experiments** provides shortcuts to
retained own-workspace M4 studies, M3 forecasts/comparisons, paired observation
analyses, campaigns and
registered durable packages. Selecting one opens its existing report/control
view. **Added archives** contains read-only archives registered from allowed
directories. Own experiment shortcuts do not register or copy their archives,
and package/foreign archive shortcuts grant no execution or resume authority.

The report summary separates retained execution information, comparison coverage
and the saved-analysis check. An added archive may lack a separately recorded
process-completion status; the summary leaves that execution information
unavailable. Metadata's recorded outcome is not treated as process completion.
Full denominators and failed or incomplete cases remain part of the report.
For a maintained M4 study, the original native report status is also shown;
`interrupted` remains distinct from failed numerical acceptance and a successful
reconstruction. Catalogue acceptance retains its existing meaning. Selecting
an added archive moves keyboard focus and the viewport to its detail heading;
passive refresh does not move focus. While another operation owns the execution
lane, the disabled saved-analysis button explains the restriction beside it and
offers **View operation** to return to that task.
Use **Check saved analysis** for the explicit native reader
operation; its result does not establish human predictive performance or model
validity. Optional recorded-file diagnostics retain their narrower scope.

## Allow archive directories

Start from a known checkout with its locked tooling:

```sh
uv sync --locked
.venv/bin/python -m experiments.gui --archive-root /absolute/path/to/archives
```

Repeat `--archive-root` for additional directories. The workspace is available
by default. Select an allowed root and relative directory in the archive
library, declare its existing task and optional local tags, then add it.
Directories are not discovered by scanning your computer. Symlinks, path
escapes and special files are refused. Source/configuration/output permissions
for new studies remain restricted to the GUI workspace. Registration refuses
archives that contain the GUI administration directory, and entries inside this
server's own administration directory. Its studies remain accessible through
**Results → Your experiments** and recorded operations, using their existing
routes rather than library registration. Archives in explicitly allowed sibling worktrees
remain eligible.

Registration freezes a pointer and starts bounded metadata indexing. Original
archives are not copied or edited. Derived metadata and verified reports live
in the GUI checkout's ignored `results/gui/` administration. Indexing,
reconstruction and model execution share the one-active-operation limit.

A library pointer does not preserve original experiment bytes. Use
[durable experiment archives](durable-experiment-archives.md) to export an
eligible maintained M4 or synthetic M3 archive, or an own-workspace study/campaign, to an explicit
`--archive-store` outside this checkout. **More → Export / open archives**
registers package wrappers, verifies integrity and explicitly reconstructs
with the matching trusted reader. Imported packages gain no resume or process
ownership authority.

## Inspect metadata and verify evidence

The library displays metadata for the eight existing scientific tasks. Use
task, text and recorded-status filters to find entries. Missing or malformed
archives remain visible with their error; successful indexing alone is not
scientific verification.

Each reference shows its registration date and allowed-root identifier. If its
root is no longer enabled, start with that directory explicitly allowed or add
the archive from a currently allowed folder. This does not grant broader file
access. **Hide reference** removes a pointer from the normal list without
deleting archive files. Select **Show hidden references**, open the reference
and choose **Restore reference** to bring it back. Hiding and restoring require
an idle execution lane; hidden entries still count toward the 128-reference
limit. Restoration preserves availability and verification restrictions.

Full native reconstruction and JSON/Markdown downloads select `m4-study-secure`,
`m3-forecast`, `m3-compare`, `m5-prognosis`, `mmtt-sensitivity` and
`mmtt-sampling`. The trajectory figure is available
for M4 only. Its **Read graph data → Load saved graph values** action displays
the numeric values from the matching native JSON: accepted model curves and
the first accepted source's control/reference curves, matching the native SVG
scope. The table calculates no trajectory values or metrics and performs no
interpolation. A byte-identity mismatch refuses the table; the original JSON
remains available through the native report route for fuller inspection.
M3 reports preserve all planned participants/origins, failed or unattempted
cases, forecast errors and comparison common support. The browser does not
recalculate metrics. Its M3 report presentation accepts up to 128 planned
participants and eight frozen comparison candidates; larger native reports
can be inspected through their native CLI and its JSON/Markdown output. Cohort completeness describes coverage, not prediction
accuracy. Existing synthetic input/predictor paths are not reopened or executed.
Passive M3 metadata requires the original top-level `report.json`. If that
report is absent, metadata remains unavailable; explicit verification can
reconstruct a sealed archive through the fixed native reader into fresh derived
output. It does not create a report in the original archive. An unsealed archive
remains a recorded pointer/error and cannot gain a verified native report. Other historical tasks retain their existing
[compatible-reader CLI](historical-readers.md); the library does not choose
an arbitrary archived module or Python executable.

The synthetic `mmtt-sensitivity` reader preserves all declared paired visits,
required variants, point/perturbation failures and conditional intervals. It
replays the same frozen variates and exact algebra, then requires identical
native JSON/Markdown bytes without importing archived Python. The shared
[observation report](observation-analysis.md) keeps C-peptide AUC and glucose
context separate from total secretion. An interrupted atomic analysis retains
its roster as unavailable; successful reconstruction does not make it complete.
Both original report formats can be downloaded from the selected snapshot.

The synthetic `mmtt-sampling` reader reconstructs raw subsets and each native
shared-core result before rebuilding full-reference differences and paired
conclusion comparisons. It preserves incomplete/interrupted denominators,
development/evaluation separation and all measured context. No empirical
agreement margin or reduced blood-draw recommendation is implied.

The recorded-file check follows each supported manifest schema's declared
base directory and claim structure. Maintained M4 reference seals use the native
`reference/` base. A matched check covers supported recorded claims only;
unknown schemas show unsupported checks, malformed claims remain explicit,
and missing or changed bytes show mismatches. These observations do not verify
all archive bytes, source authenticity or scientific results. Originals are
never rewritten to satisfy a check. [Decision 0063](decisions/0063-reliable-archive-library.md)
records this boundary.

Choose **Check saved analysis** explicitly before relying on a saved report. A verified
snapshot binds the reader result and displayed report bytes. Passive browsing
does not rehash an entire source archive: its freshness label states when the
source has not been rechecked since the worker. Recheck after external edits.
Detected identity/report changes or a failed recheck withdraw verification.
A server restart retains recorded evidence but requires a new check for live
verification. Keep failed sources and full planned denominators in view.

## Read synthetic M5 prognostic reports

Register an existing sealed `m5-prognosis` directory under an allowed archive
root, then explicitly verify it. The fixed native M5 reader checks the archive
in place; the library copies only verified original JSON/Markdown bytes into
its own report snapshot. Neither the supplied model nor original model-bundle
paths are executed or reopened. Both original reports must exist, and the native
file inventory, implementation/lock identities and byte limits must agree.
Missing M5 reports cannot use the M3 reconstruction fallback.
[Decision 0064](decisions/0064-native-m5-archive-library.md) fixes this boundary.

The view retains all 32 invented participants: 24 development and eight
evaluation, with 20 and seven eligible respectively. Exclusions and later
infusions remain visible. Development and excluded rows have no evaluation
attempts. Each eligible evaluation participant shows both attempt positions,
saved predictions and runtime identities; missing attempts, interruptions,
failures and repeat disagreement remain explicit.

Execution accounting and paired comparison completeness are separate. All
attempts can finish while every candidate fails. Successful native verification
can therefore yield an incomplete comparison. The full eligible baseline is
shown separately from candidate and baseline errors on the same successfully
paired participants, in `U/day`. Zero pairs retain native `null` paired metrics;
the view explains their unavailable support and does not substitute zero or
calculate new scores. These invented associations establish no human prognosis
or treatment effect.

Model/source/state identities and rights/training declarations are bound to the
same verified snapshot. Training and rights remain supplier self-attestations.
The declaration is displayed separately; original JSON/Markdown downloads are
unchanged, and no model/state/source download or M5 execution control is added.
Changed cached reports or declarations withdraw their view and downloads
together. Restart retains recorded evidence; explicit re-verification restores
live verification. Unchanged snapshot rechecks preserve open details and focus,
and late responses for an obsolete selection cannot replace the current report.
The [OT-044 verification record](research/m5-archive-library-verification.md)
records the separately executed internal checks and remaining evidence limits.

## Limits

Long indexing and reconstruction run as owned workers with bounded inventory
and deadlines. Cancel through the GUI; closing its tab does not stop a worker.
Original archive inventories are checked around operations and must remain
unchanged. Local Python remains trusted researcher code, not sandboxed input.

Agent/browser checks are internal software verification. The prepared
[independent GUI exercise](gui-researcher-exercise.md), broader task support,
human-data assessment and biological validity remain separate evidence work.
