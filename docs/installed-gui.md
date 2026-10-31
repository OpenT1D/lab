# Installed project GUI and formative preparation

The thin GUI is an internal interface to the [installed SDK](installed-sdk.md).
It uses the same immutable plans, parent links, attempts and trusted readers as
Python and the CLI. Its workspace catalog and job labels are convenience state;
the SDK project is the authoritative research record. This interface covers
supplied examples and user-chosen synthetic inputs for paired-sensitivity and
reduced-sampling MMTT, plus editable selected configurations for the
[installed M4 successor](installed-m4.md).
The older checkout GUI and its historical exercises retain their own scope.
The [bounded internal MMTT candidate](internal-mmtt-candidate.md) deliberately
admits only the two MMTT tasks and their comparisons. Its startup view and
service gates omit native/connected execution and runtime attachments.

Use the SDK build/install procedure, then launch from any working directory:

```bash
/private/tmp/opent1d-sdk-env/bin/opent1d-lab gui \
  --workspace /private/tmp/opent1d-gui-workspace
```

Open the printed `http://127.0.0.1:PORT` address. A port is selected automatically;
`--port` may select a local port. Choose a canonical absolute workspace outside
the SDK environment and all existing project stores. Only one server may own
that workspace. The candidate selects POSIX CPython 3.12; current local native
qualification is macOS arm64. It is not a public installer or a clean-host test.

## Research workflow

1. Create a named project, or open an existing SDK project folder. Opening and
   refreshing read the ledger; they do not execute a task. GUI project handles
   and display names differ from the authoritative plan and attempt IDs.
2. Select a task and supplied example, or choose **Start with my synthetic
   inputs**. Upload or edit the named UTF-8 source files, inspect/edit assumptions
   and save a concept. **Validate saved inputs** uses the SDK without estimation.
   Correct invalid text in the retained concept; validation errors do not erase
   it. **Freeze plan** requires this exact saved and validated revision. For 15 g,
   explicitly choose the fasting plan under **Derived from**, save and validate;
   the original remains frozen. **Inspect frozen inputs** shows original hashes,
   scientific configuration and the recorded parent.
3. Select a saved plan and **Check readiness**. MMTT uses the standard library.
   Native M4 needs an explicitly reviewed attachment for this exact installed
   artifact. Under **Prepared native runtimes**, select it or create one from
   the separately prepared native/observer folders. No dependency installation
   or archived callback runs through the GUI. Old artifacts' attachments refuse
   execution until recreated for the current application.
   Readiness records that check's snapshot. Changing the project, plan or
   runtime selection, including in another tab, requires a new check; an older
   result cannot mark the new selection ready. External runtime file changes
   are not monitored continuously. Check again after changing those files;
   execution independently validates its actual runtime selection through the SDK.
4. **Run plan** creates an attempt through the SDK. One SDK action runs per
   workspace. The screen shows elapsed time and the facade's action, without
   inventing native phase percentages. **Stop run** requests SDK cancellation
   and waits for ownership cleanup. A missing attachment can produce a retained
   admission failure. Correct it and run an explicit new attempt; the retry
   preserves earlier failures. Unfinished crash evidence requires the existing
   explicit CLI recovery procedure after the old executor has stopped.
5. In **Attempts**, distinguish execution outcome, native/forensic payload,
   scientific completeness and planned-slot counts. **Verify saved report**
   explicitly calls the trusted reader. Incomplete native evidence requires
   the separate checkbox; forensic-only failures have no admissible report.
   MMTT offers JSON/Markdown; M4 additionally offers SVG. Verification checks
   saved analysis, without rerunning physiological models. The displayed copy
   records verification time; verify again to assess changed project evidence.
   Sampling additionally lists each native measurement-schedule analysis with
   explicit read and JSON/Markdown download actions. The parent retains its
   development/evaluation split and all planned slots. Only fixed, hashed report
   paths are served; changed nested copies withdraw the displayed verification
   on refusal or the next invalid-state update. Verify again from the preserved
   project to create a fresh copy.
6. **Copy complete project** relocates all plans, inputs, attempts and native
   evidence to a fresh folder. Open the copy and verify its reports before
   removing the original. This GUI action also copies concept revision histories
   to the new workspace handle, clearing their validation. A CLI project copy
   carries the authoritative SDK ledger; it does not transfer GUI workspace
   concepts. A report download alone is not a project handoff.

## Edit, save and recover a study

**Saved study concepts** reopens a named concept after a browser reload or server
restart. Edits autosave after a short pause; **Save concept** or Ctrl/Cmd+S saves
explicitly. Only **Saved revision** acknowledges server persistence. Keep the
server terminal open through shutdown. Unsaved browser recovery text is scoped
to that browser origin; a different port/browser does not carry it. The last
acknowledged server revision remains the recovery boundary after a crash.

Each saved revision retains its exact source bytes and immutable history.
**Restore as a new revision** appends the chosen earlier contents rather than
rewinding history. Uncommitted interrupted writes are reported without replacing
the committed revision. Damaged concepts are listed separately and cannot be
frozen. Limits are 200 concepts per workspace, 1,024 revisions and 64 MiB of
deduplicated source blobs per concept. Start a new concept when a limit is reached.

Two tabs cannot silently overwrite each other. After a conflict, **Reload saved
version** explicitly discards local edits, while **Keep my edits as a new concept**
preserves them separately, including the chosen frozen parent. The picker keeps
an explicit selection across background status polling. Uploads preserve the
latest file/text choice even if an older file read finishes later.

For MMTT, supply `package.json`, `observations.csv` and `settings.json` using the
[paired input contract](observation-analysis.md). Sampling additionally needs
`design.json`, `development-package.json` and `development-observations.csv` under
the [sampling contract](mmtt-sampling.md). The SDK seals that explicit development
pair; it never silently selects a development cohort from evaluation outcomes.
Metadata/design must declare matching identities and development allocation.
The selected M4 editor accepts `config.json`, with its existing fixed source pair
and supported scenarios/timeouts. It accepts no uploaded model code or new runtime.

JSON files are bounded to 128 KiB each and CSV files to 512 KiB, within a 2 MiB
concept request. These GUI limits are narrower than some native CLI limits.
Untouched uploads preserve UTF-8 BOM/CRLF bytes. A structured edit rewrites only
its relevant JSON file; raw editors support all admitted fields. Large 64-bit
seeds retain their exact raw representation; structured controls refuse to round
values outside JavaScript's safe integer range.

Input admission is separate from scientific completeness. Native import
diagnostics can retain censored, missing or invalid visits; freezing does not
invent estimates or shrink planned support. Inspection exposes the full visit
roster and error counts with bounded diagnostic text and explicit truncation.
Original source bytes remain available for correction and native analysis.

**Derive an editable study** exports the selected frozen plan's original inputs
through the SDK, retaining it as parent. Changing a previously frozen concept
also derives from that freeze. Save and validate the changed assumptions, then
freeze a new plan. No original plan, attempt or report is overwritten. An open
unfrozen concept blocks accidental execution of an older plan; **Return to frozen
plans** makes that choice explicit. Changing scientific inputs or parent clears
validation/readiness. A late response cannot replace newer edits or mark them valid.

The [workbench evidence record](research/editable-workbench.md) separates actual
installed tests, keyboard/focus and accessible-name checks, narrow/200-percent-text
reflow observations and separate technical review. Actual screen-reader use,
formal accessibility qualification and independent intended-user acceptance remain open.

MMTT represents whole-body total endogenous secretion including basal, in pmol
over the observed 0–120 minutes; change is follow-up minus baseline. The supplied
settings retain three assumption variants and 128 perturbations with seed 117.
Choose **Fewer meal-test measurement times** for information-loss, constant-input,
incomplete or steep-response controls. Preparation retains the sealed development
selection and separate evaluation participants. Schedule allocation and the
estimator are unchanged; full curves are references, not biological truth.
The M4 examples retain both sources, 240 minutes and 961 quarter-minute outputs.
The 15 g condition is an initial gastric load, not a timed meal. These examples
demonstrate synthetic software behavior, not biological accuracy or treatment
effects. Preserve missing/censored values and all failed planned slots.

Closing a browser tab keeps work running. **Stop server**, Ctrl+C or TERM stops
admission, requests cancellation of a run, drains other SDK actions and waits
for owned cleanup before exit. Keep the terminal open until it exits. A force
kill or machine loss remains an unobserved crash; saved PIDs are never adopted.
Restart does not automatically execute, attach a runtime or recover an attempt.
The workspace retains convenience labels and unobserved-action notices; reopen
and refresh the authoritative project after interruption.

The server binds loopback, verifies fixed Host/Origin, uses a per-session header
token and bounded HTTP/JSON, and serves only fixed assets and explicit verified
report copies. It is not an authenticated remote collaboration service. Keep
private health records out. Native parameter/table redistribution rights remain
separate; the GUI does not grant permission to distribute those project bytes.

## Compare variants and frozen plans

Use **Compare frozen plans and variants** before running the selected plans.
Choose plans with the same task, original observations, participant allocation,
visit order and scientific support. Plans may differ in their declared MMTT
assumptions or sampling schedules. Sampling retains its development seal.
Installed M4 supports only its existing reviewed source/load selections and
requires its separately prepared attachment for execution.

1. Name the comparison and state the research question. Choose an unattempted
   frozen plan, **Load plan variants**, select its assumption/schedule or
   source/load, name the member and **Add member**. Repeat for 2–16 distinct
   plan/selector combinations. Several members may share one plan.
2. Choose an explicit **Baseline member** and **Freeze comparison roster**.
   Inspect the exact changed fields, including selected kinetic/volume values,
   retained sampling times and initial load/source identities. Incompatible
   input support is refused; the editable roster remains available for correction.
   Changes to the name, question or baseline while freezing remain in the editable
   roster; the saved comparison retains exactly the submitted values.
3. **Run next unattempted plan** executes unique plans sequentially in frozen
   roster order. The first attempt remains selected, including failures and
   incomplete results. A later retry cannot replace it. To repeat previously
   executed assumptions, first derive and freeze a fresh plan, then freeze a new
   comparison before its execution. Recover an unfinished attempt through the
   existing explicit SDK recovery path before another execution.
   Existing archives cannot be imported as a comparison member's first attempt;
   use a separate plan for retrospective intake.
4. **Reconstruct current comparison** verifies saved native evidence and keeps
   every planned member/case, including unattempted and unavailable values.
   Download JSON, Markdown and **comparison CSV**. Inspect allocations, units,
   point/interval completeness and the explicit member-minus-baseline direction.
   Unresolved intervals do not establish no change; there is no biological score.
5. A report records its exact ledger tip. Paste it under **Saved report ledger
   tip** and **Reconstruct saved snapshot** to reproduce that report after later
   execution/retries, restart or project copying. Refreshing current statuses
   creates a new view; it does not alter earlier report snapshots. Choosing a
   different comparison clears the previous status/report context. Delayed reads
   cannot replace a newer verification or its download identity.

MMTT reports retain whole-body secretion including basal over 0–120 minutes in
pmol, with follow-up minus baseline. M4 tables retain its complete 0–240-minute
quarter-minute grid and native signal-specific AUC, time-mean and pointwise
contrasts. They require entire-source/reference/control acceptance. Neither
route supplies empirical equivalence, a new interval for between-member
differences, treatment effects or independent usability evidence. The
[comparison record](research/workbench-comparisons.md) owns the bounded checks.

## Connect known secretion to inverse analysis

**Connected synthetic study** freezes a named question and the versioned protocol
before execution. Choose a new bounded forward plan or an unused existing
four-slot M4 plan. Select the complete observation case or the predeclared
missing-evaluation control, then **Freeze connected study**. The two source
methods represent synthetic cases with development/evaluation allocations.

**Inspect connected study** reads the fixed stages and current ledger tip. The next-action
button performs exactly one explicit step: run the forward plan, materialize or
resume the observation bridge and frozen downstream plans, or run the inverse
and sampling plan. Select the exact-artifact M4 attachment under **Prepared
native runtimes** before forward execution. Each run uses the ordinary SDK
process ownership and **Stop run** controls. Recover an unfinished attempt
explicitly before starting another; a failed first attempt remains selected.
A changed project ledger requires another inspection before advancing.

**Verify connected study** reconstructs the chain without running native models.
It retains all 72 planned truth-comparison rows, including unattempted,
missing-point and failed-draw endpoints. The report badge shows native evidence
completeness and numerical point-check acceptance separately. Download JSON,
Markdown or **study CSV**. The displayed identity is the study and saved ledger
tip. Choosing or freezing another study withdraws the previous report and its
downloads. A saved tip under **Connected report ledger tip** reproduces an earlier
snapshot after later attempts, restart or project copying.

The two native-stage report buttons verify preserved forward and full/reduced
reports through their existing readers; incomplete native reports require the
existing explicit checkbox. No failed stage is fabricated. Generated observations
are sealed separately from known source truth; neither an interval crossing zero
nor an unavailable interval establishes no change. Read the
[SDK protocol and commands](installed-sdk.md#connected-synthetic-study) and
[bounded numerical evidence](research/connected-synthetic-study.md). This study
does not expand the formative human exercise below or establish sampling
agreement in human data.

## Prepare an actual user exercise

The original exercise below still selects paired MMTT and M4 references. Adding
sampling to the installed interface does not expand that packet, freeze new
human tasks or record any participant evidence. The
[sampling integration record](research/installed-mmtt-sampling.md) describes its
separate software/browser checks.

The selected [verification and preparation record](research/ot065-072-shared-gui.md)
owns this bounded formative exercise. First retain a real reference project with
complete MMTT, fasting and parent-linked 15 g attempts, plus a failed native-task
attempt. Use the clean installed candidate that will be observed:

```bash
/private/tmp/opent1d-sdk-env/bin/opent1d-lab prepare-study-packet \
  --reference-project /private/tmp/reference-project \
  --mmtt-attempt MMTT_ATTEMPT_ID --fasting-attempt FASTING_ATTEMPT_ID \
  --load15-attempt LOAD15_ATTEMPT_ID --failed-attempt FAILED_ATTEMPT_ID \
  --output /private/tmp/shared-gui-pilot
/private/tmp/opent1d-sdk-env/bin/opent1d-lab verify-study-packet \
  --packet /private/tmp/shared-gui-pilot
```

Replace the IDs with actual SDK ledger values. Preparation refuses dirty builds,
wrong tasks/conditions, changed supplied inputs, missing terminal evidence and
the wrong 15 g parent. It reconstructs on a disposable complete project copy,
checks the original project stayed byte-identical and writes the packet manifest
last. A failed preparation may retain a partial folder without a valid manifest;
use a fresh destination. Preparation executes no new simulations and needs no
runtime attachment. The packet binds the full installed descriptor, source/build,
actual reference plans/attempts, original inputs and report hashes. This identity
is distinct from the wheel hash; retain the actual wheel and build receipt too.
Verification detects changed files or a different installed candidate, but its
hashes are not external authentication against wholesale replacement.

Give only `participant/Tasks.html` to the analyst. Keep `facilitator/Guide.html`,
actual reference reports and `observations.template.json` separately. Directory
names are not access control if the whole packet is shared. The packet contains
no upstream source/table/runtime bundle. Copy the blank observations outside the
sealed packet before recording sessions; all human fields start unanswered.

Recruit an actual intended analyst who did not build the candidate; a distinct
actual recipient is needed for a handoff claim. Freeze candidate, packet hash,
host, runtime attachment, task order, allowed guide/help and reference answers
before observing. Record unassisted, assisted, blocked and not-assessed tasks;
first answers, help content, critical interpretation errors, independent
adjudication and retests stay distinct. Separate active work, unattended compute
and total elapsed. Long native computation may require split sessions. Record a
block before using saved reports as a fallback. Do not count internal agent
rehearsals as participants, installation usability or independent acceptance.
Historical OT-056 comparisons, broader OT-072 qualification, other hosts and
biological evaluation retain their separate protocols and open gates.
