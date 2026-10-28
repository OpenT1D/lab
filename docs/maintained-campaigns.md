# Maintained local M4 campaigns

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

A maintained campaign repeats declared
[maintained M4 studies](m4-maintained-study.md). It selects `m4-study-secure`
under `MAINTAINED-CAMPAIGN/1`. The historical
[local campaign route](local-campaigns.md) retains its original protocol and
runtime; existing archives are not converted or relabeled.

## Declare the matrix

Prepare each native `m4-secure-study-config/1` configuration first. Then save
one campaign configuration with exactly the following fields. Cell paths are
relative to this file unless absolute. Source paths remain relative to their
native study configuration.

```json
{
  "schema": "opent1d.maintained-campaign-config/1",
  "task": "m4-study-secure",
  "cells": [
    {"id": "fasting", "config": "fasting-study.json"},
    {"id": "load_15g", "config": "load-15g-study.json"}
  ],
  "repeats": 2,
  "timeout_seconds": 10800
}
```

Use one to 32 distinct cells, one to eight repeats and at most 128 study slots.
The per-study outer budget is an integer from one to 10800 seconds. Native
stage/source budgets remain unchanged. Execution follows cell order and then
ascending repetition. Different conditions retain separate scientific reports;
there is no pooled outcome, tuning or automatic winner selection.

## Prepare and run

Install the existing task locks through [task-directed setup](task-setup.md)
for `m4-study-secure`. Installation remains explicit. Metadata reads frozen
configuration, source/declaration and protocol/lock identities without running
models. Check additionally checks installed runtime metadata.

```sh
uv sync --locked
.venv/bin/python -m experiments.maintained_campaigns metadata --config campaign.json
.venv/bin/python -m experiments.maintained_campaigns check --config campaign.json
.venv/bin/python -m experiments.maintained_campaigns run \
  --config campaign.json --output results/maintained-campaign
```

Choose a fresh output directory outside inputs. The campaign copies source and
configuration bytes before dispatch and records actual runtime identities.
Python sources are trusted local researcher code. This synthetic route accepts
no human observations and does not install dependencies during execution.

## Cancel, retain attempts and resume

SIGINT, SIGTERM or SIGHUP stops later dispatch and asks the native owner to
finish cleanup. The campaign allows thirty seconds outside the execution
budget for child cleanup, then seals the session. Cooperative handlers remain
installed through final sealing and report-cache writes. A late stop can retain
already completed scientific outcomes. Failed, interrupted and
unattempted slots retain their full planned accounting. Ordinary study failures
do not erase evidence or prevent later cells from being attempted.

```sh
.venv/bin/python -m experiments.maintained_campaigns resume \
  --campaign results/maintained-campaign
```

Resume verifies original frozen inputs, implementation/protocol/lock/runtime
identities, all prior sealed sessions and native archives before appending a
session. Accepted slots are verified and reused. Remaining slots receive one
new attempt; previous attempts and manifest links remain immutable. A no-op
resume dispatches no new attempts. A changed plan or unsealed hard-killed
session requires a fresh campaign; retained partial output remains forensic
evidence rather than an accepted result.

## Reconstruct reports

```sh
.venv/bin/python -B -S -m experiments.maintained_campaigns reconstruct \
  --campaign results/maintained-campaign --output results/campaign-report
```

Add `--allow-failed` for failed or incomplete coverage. Reconstruction writes
a fresh external report directory using the fixed standard-library reader;
it does not execute models or require their numerical environments. Reports
retain every slot, attempt and planned source/scenario denominator.

A later implementation change requires an explicitly identified compatible
reader checkout matching the archived source inventory. Retain the original
checkout or its exact Git revision alongside the archive. Reconstruction selects
trusted current checkout code; it does not execute archived Python.
[Durable experiment archives](durable-experiment-archives.md) preserve the
complete native campaign, every attempt/session and exact trusted-reader
identity in storage outside disposable worktrees. Their separate CLI accepts
`maintained-campaign`; keep the package wrapper when restoring its `archive/`.
The [OT-041 acceptance record](research/durable-archive-verification.md) verifies
relocated reconstruction of a partial campaign without its original execution
checkout or numerical environments. The
[earlier execution record](research/experiment-workspace-verification.md)
retains the historical checks and records the later unavailability of their
original ignored raw artifacts.

The [machine protocol](../experiments/maintained_campaigns/protocol.json) and
[architecture decision](decisions/0060-maintained-campaigns-and-experiment-workspace.md)
define this scope. Internal verification does not establish independent
researcher usability, biological validity or clinical benefit.
