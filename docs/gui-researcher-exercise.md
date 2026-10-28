# Independent GUI researcher exercise

**Status:** proposed formative study; no recruitment, participant or independent
result is recorded. The earlier prepared M4 task is retained below
and extended to assess finding results, evidence interpretation and recovery.
The [test-session entry](gui-test-session.md) supplies the version-bound packet,
explicit launch files and local observation worksheet. A first novice pilot
records usability findings separately from the intended-researcher round below.
This exercise assesses the [local GUI](local-gui.md) through one synthetic M4
initial-load study and identified saved reports. It is separate from the historical
[P1 exercise](p1-acceptance-exercise.md) and its exact conditional handoff.

## Internal technical preflight

An agent-operated check on 6 October 2026 installed the locked maintained M4
runtime through the GUI and ran the two supplied sources under all three initial
loads on candidate `974fe7d9ea39ba566dc3cfc9f50f95e05824ecaf`. The native report
accepted 2/2 sources, 6/6 source/load cases and 1/1 source pairs. Explicit saved
analysis reconstruction reproduced JSON, Markdown and SVG bytes. All 46,128
rendered cells in the twelve live graph tables matched the original native
values and units. A separate actual cancelled run retained its interrupted
status, 0/6 accepted cases and full planned denominator; its saved analysis
reconstructed without turning incomplete evidence into acceptance.

The local packet in ignored `results/ui-user-study-20261006/` identifies the
candidate, source bundle, complete/cancelled archives, internal checks and six
blank session records. It contains no participant results or sent invitations.
This technical preflight makes the task ready for intended-user observation;
it does not populate the observation table below or close usability acceptance.

## Participants and questions

Plan a first round with **four to six researchers who did not build the GUI**.
Include diabetes or biology researchers with limited programming experience and
computational researchers who use Python or scientific analysis tools. Record
domain experience and prior software experience separately; a first-time
OpenT1D user may already be a domain expert. This is a proposed recruitment
profile, not evidence that participants are available.

The study asks whether a researcher can:

- choose a supported task and understand its models, synthetic inputs and units;
- complete the explicit setup/check/run route and find their own saved result;
- distinguish execution, numerical acceptance, comparison coverage and saved
  analysis verification, including incomplete or failed evidence;
- recover from a configuration error and use the interface with keyboard input
  and a narrow display.

Use one common task route with optional details. The study does not assume that
a separate beginner/expert mode is necessary. A small formative sample can
identify problems and guide fixes; it cannot establish population-wide success
rates or scientific validity.

## Freeze the handoff

Before transferring a bundle, identify the clean checkout commit, supported
platform, source/declaration bytes, licenses and permitted handoff scope. Use
the two supplied synthetic sources and existing 0/15/30 gram conditions. Review
the actual new bundle's rights; historical P1 permission is not automatically
permission for this new checkout. Record any unresolved question honestly. Freeze
the task instructions, available help, installed-environment state and expected
artifact paths before the first session. Record whether installation is part of
the assessed task; a preinstalled session does not assess installation usability.

Select a real retained failed or incomplete synthetic archive that the candidate
checkout's fixed reader supports. Verify its identity and expected coverage in
advance. Preserve its original bytes and full planned denominators. Include a
complete archive for contrast if available. Do not invent a failure, alter
scientific results or present a mocked report as native execution evidence.
Record the archive/task/readers supplied; interpretation findings apply to those
specific report types. Reader registration grants no execution or resume rights.

A researcher who did not build the pilot receives the identified checkout and
the canonical GUI guide. Do not invent participant availability, a date or
responses. Use no personal health records or device connection. Keep contact
information and identifying feedback private unless attribution is permitted.
Record screens or audio only with that participant's permission. A public record
uses non-identifying roles and observations rather than contact details.

## Uncoached session

Plan **45–60 minutes** per session. Long environment installation or native
execution may require a separate recorded session; do not silently substitute a
precomputed run for the participant's execution. Time is diagnostic information,
not a pass threshold.

Read the goal, not the intended button sequence. Ask the researcher to think
aloud where comfortable. Ask interpretation questions after the relevant task
without supplying the definitions in advance.

1. Record the checkout revision, OS and Python/uv versions; start the local UI.
2. "Compare the supplied insulin secretion models under all three starting
   conditions." Before checking, ask which models, profile, observation duration
   and initial loads will be used. Ask whether the inputs describe real people,
   and what the visible units mean. In optional model details, ask the difference
   between source code and its declaration.
3. "Make this experiment ready and run it." Explicitly install missing
   environments if the scoped session requires it. Ask whether a readiness check
   ran a model and what selecting Run will execute. Record messages, errors and
   help actually requested.
4. During the run, ask the researcher to visit another view and find the ongoing
   operation again. Ask how to cancel and what closing the browser would do.
   Use a separate fresh run for an actual cancellation exercise and retain its
   evidence; do not interrupt the only complete study.
5. "Leave the study view, then find your experiment in Results." Ask the
   researcher to identify their run and inspect planned/accepted denominators,
   source statuses and trajectory units. Record the first navigation choice and
   any incorrect interpretation of empty or unavailable results.
6. "Check the saved analysis and download its report." Ask what was verified,
   whether supplied model code was rerun and where the local evidence is retained.
   Ask what changes after a server restart or external archive edit. Distinguish
   a report pointer from an independently retained archive package.
7. Open the identified incomplete or failed report. Ask "What can you conclude
   from this report, and what remains missing?" Record the researcher's own
   explanation of full denominators, failed/excluded cases, unavailable metrics
   and any paired comparison support. Ask why verified saved analysis can remain
   incomplete or numerically failed, and whether synthetic output supports
   accuracy in people, biological validity or treatment benefit.
8. Exercise one reversible configuration error: in model details enter an invalid
   source ID, submit the check, then restore the original ID. Observe whether the
   offending field is revealed, its message is understandable and the researcher
   can recover. Do not change model bytes or execute an unchecked configuration.
   Complete navigation and one disclosure/error-recovery task using only the
   keyboard. Inspect the same task at an identified narrow viewport (for example
   390 CSS pixels); record whether this used a real device or a resized desktop.

Do not coach the researcher through a hidden difficulty or fill in their
answers. Assistance is allowed when requested, but must be recorded.
If installation, execution or an interface defect blocks progress, record the
block before providing an identified saved report for the remaining interpretation
tasks. Those later tasks do not turn the blocked execution task into a success.

## Criteria fixed before observation

Record each task as **completed without moderator help**, **completed with help**,
**blocked**, or **not assessed**, with evidence. Reading the supplied canonical
guide is permitted and recorded; direct moderator instruction counts as help.
Task completion requires the correct outcome, not merely clicking a button.

| Criterion | Evidence needed |
| --- | --- |
| Configure and run | Correct supplied models and three loads; researcher completes the scoped setup/check/run route. |
| Find own results | Researcher finds the correct retained experiment from Results after leaving its task view. |
| Understand the task | Researcher identifies synthetic scope, model/profile/time context, initial rather than timed loads, and relevant units. |
| Interpret evidence | Researcher distinguishes process completion, numerical acceptance, coverage and saved-analysis verification; recognizes retained failures and absent comparison support. |
| Respect comparison support | Researcher does not compare unmatched subsets, interpret an unavailable metric as zero, or infer human/clinical validity from synthetic output. |
| Recover and navigate | Researcher corrects the invalid field, reaches operation controls with keyboard input and completes the scoped narrow-display task without inaccessible controls or lost evidence. |
| Preserve reports | Researcher downloads the native report and explains local retention, pointer/package differences and when verification needs a new check. |

Classify observed issues before deciding follow-up work:

- **Blocking:** a supported task cannot be completed or its result cannot be found.
- **Misinterpretation:** a label or presentation leads to an incorrect evidence
  conclusion, loss of failures/denominators, or an unsupported human/treatment claim.
- **Recoverable difficulty:** completion requires help, a workaround or avoidable
  navigation; no incorrect scientific conclusion is recorded.
- **Presentation:** cosmetic or preference feedback without a demonstrated task
  or interpretation effect.

For a scoped usability acceptance recommendation, resolve every observed blocking
or misinterpretation issue and repeat its affected tasks on the identified fixed
candidate. Record unresolved difficulties and unassessed platforms/tasks.
Do not turn a small sample's fraction of successes into a general product claim.
Independent usability acceptance does not establish numerical, biological or
clinical validity and does not authorize publication or human-data evaluation.

## Record actual observations

Create a private non-identifying record for each actual session. Leave fields
empty until observed; a planned task is not a participant result.

| Field | Actual observation |
| --- | --- |
| Non-identifying role, domain experience and software experience | |
| Checkout/source/report identities, platform and environment state | |
| Start/end time, guide use and actual moderator assistance | |
| Per-task completion classification and first navigation choices | |
| Configure/check/install/run outcomes and retained artifact paths | |
| Finding own Results and correctly identifying the experiment | |
| Cancellation and retained evidence | |
| Reconstruction outcomes and report hashes | |
| Complete/partial report interpretation, denominators and unavailable metrics | |
| Configuration error, recovery, keyboard and viewport/device observations | |
| Errors, unclear labels, workarounds and issue severity | |
| Researcher's own interpretation of limitations | |
| Rights questions and usability verdict | |
| Deviation, fix candidate and affected-task retest | |

The maintainer assesses the actual record and deviations. An agent browser run
or CI pass provides internal technical evidence and cannot fill this table.
Internal delivery can finish while this independent-user criterion remains open.

## Method references

The proposed study uses task observation and explicit researcher roles because
scientific software serves specialized, sometimes distinct user communities;
[Ramakrishnan and Gunter (2017)](https://escholarship.org/uc/item/0w5547jv)
describe integrating user research into scientific software development.
[W3C's cognitive accessibility guidance](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o2p04-page-important/)
supports testing whether important actions and information are directly findable.
These sources inform the method; they provide no OpenT1D participant results.
