# Synthetic meal-test session card

Use only the supplied invented data. Explain your reasoning aloud if comfortable,
and keep your first answers, including unsuccessful work. You can use the supplied
operational guide and ask for help; the facilitator records that help. Do not use
health records or make clinical decisions. You may pause or stop the session.

The facilitator provides the installed application, loopback start address,
working recovery-project folder and export location. Tasks use the English labels
in that application. A text copy of the failed attempt's actual receipt is also
provided for task 4; the GUI exposes its status but has no receipt viewer.
Keep a short written explanation and the related report
identities for each task. Report uncertainty or a block rather than guessing.

## 1. Inspect a paired meal test

Create a project using **Invented paired visit** (paired `complete`). Inspect
its observations, visit order and assumptions. Explain what the analysis is
intended to estimate and which inputs identify this study. Keep a frozen base
plan; leave it unrun for the comparison in task 2.

## 2. Compare a changed assumption

Derive a related editable study from that plan. Change the `nominal` variant's
volume to 5.502 L and explain the reason for that change in its rationale. Keep
all other assumptions, required variants and observations. Preserve both plans
and their relationship. Declare a comparison of their `nominal` variants, with
the original as baseline, before either plan runs.

Use this comparison question: does the direction or magnitude of the estimated
follow-up-minus-baseline secretion change depend on the volume assumption?
Run the comparison and save its JSON, Markdown and CSV reports. Explain the
estimates, paired changes, comparison direction, uncertainty and limitations.
Address direction and magnitude separately. Keep the
saved report ledger tip and report identities for task 5.

## 3. Investigate fewer measurement times

Use **Invented information loss** (sampling `information-loss`) and its existing settings
and development inputs. Declare a comparison of `nominal/full` with
`nominal/three-times`, using full as baseline, before running the plan. Inspect
both the comparison and the native schedule reports. Explain what changes, how
the schedule is selected and what this example allows you to conclude.

Repeat with **Incomplete measurements** (`incomplete`) in a separate plan and comparison.
Explain the available, incomplete and unavailable evidence. Retain every planned
case and distinguish point values from interval information. Save the reports
and your first explanation even if you cannot complete the task.

## 4. Recover unsuccessful work

Open the supplied **working copy** of the recovery project. Investigate its
unsuccessful attempt. Explain what evidence you can inspect, what happened and
what you would do next. Recover where possible while retaining the first outcome,
linking any retry explicitly. Keep both outcomes and any resulting report.

## 5. Hand off and reconstruct

Keep a complete copy of your project at the supplied new location. Provide the
designated recipient with its application identity, project location, task-2
comparison ID, saved ledger tip and report hashes. Have the recipient reopen it
in the declared receiving installation and reproduce that saved report. Explain
what was preserved, checked and left untested. If no recipient is available,
record that and perform a self-reopen separately.

Keep the original project and first answers. Tell the facilitator about blockers,
help used and any changes you made. At the end, describe the most confusing step,
any evidence you could not interpret and what would help you use it again.
