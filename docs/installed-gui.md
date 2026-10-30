# Installed project GUI and formative preparation

The thin GUI is an internal interface to the [installed SDK](installed-sdk.md).
It uses the same immutable plans, parent links, attempts and trusted readers as
Python and the CLI. Its workspace catalog and job labels are convenience state;
the SDK project is the authoritative research record. This interface covers
supplied MMTT examples and the [installed M4 successor](installed-m4.md).
The older checkout GUI and its historical exercises retain their own scope.

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
2. Select a task and supplied example, prepare/validate it, inspect its details
   and freeze a named plan. The GUI does not accept arbitrary file uploads.
   Use the SDK for other supported intake. For 15 g, choose the fasting plan
   under **Derived from**; the original remains frozen. The default suggestion
   can be changed explicitly. **Inspect frozen inputs** shows original hashes,
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
6. **Copy complete project** relocates all plans, inputs, attempts and native
   evidence to a fresh folder. Open the copy and verify its reports before
   removing the original. A report download alone is not a project handoff.

MMTT represents whole-body total endogenous secretion including basal, in pmol
over the observed 0–120 minutes; change is follow-up minus baseline. The supplied
settings retain three assumption variants and 128 perturbations with seed 117.
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

## Prepare an actual user exercise

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
