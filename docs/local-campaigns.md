# Small local M4 study campaigns

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

A campaign executes a fixed list of [M4 initial-load study](m4-configurable-study.md)
configurations and repetitions. It preserves each attempt and resumes explicitly
after checking prior evidence. The scientific task remains the native study;
campaign reports describe execution, coverage and identities. They do not average
different loads into a model ranking or select a winner.

## Prepare a fixed matrix

Use `opent1d.local-campaign-config/1` with exactly `schema`, `task`, `cells`,
`repeats` and `timeout_seconds`. The only task is `m4-study`. Each ordered cell
has a unique safe `id` and an explicit native `config` path, resolved relative
to the campaign configuration. Prepare native configurations before execution;
the campaign does not generate parameter changes or tune a source.

```json
{
  "schema": "opent1d.local-campaign-config/1",
  "task": "m4-study",
  "cells": [
    {"id": "midpoint", "config": "midpoint-study.json"},
    {"id": "historical_load", "config": "historical-load-study.json"}
  ],
  "repeats": 2,
  "timeout_seconds": 10800
}
```

The bound is 1–32 cells, 1–8 repetitions and at most 128 total study slots.
The outer deadline is an integer from 1 to 10800 seconds per complete native
study. It does not replace the native configuration's stage/source budgets.
Execution follows cell order, then ascending repetition number. Different
configurations retain separate scientific conditions and denominators.

## Check and execute

Install the existing locked tooling, native and observer projects using the
[task-directed setup guide](task-setup.md). Campaign execution does not install
dependencies. Check only reads configurations, declarations, source hashes,
protocols, locks and installed package metadata; it does not import a source.

```bash
uv run --locked python -m experiments.campaigns check --config campaign.json
uv run --locked python -m experiments.campaigns run \
  --config campaign.json --output results/my-campaign
```

Output must be a fresh directory separate from supplied inputs. Before the
first dispatch, the campaign freezes standalone configurations, model and
declaration bytes, source parameters, protocol/implementation/lock identities
and actual Python/package versions. Original source paths are provenance;
execution uses the copied sources and their relative frozen configuration.
No human observations are accepted by this campaign route.

## Read attempts and resume

The campaign root's `manifest.json`, `plan.json`, configuration and snapshots
remain immutable. `sessions/session-0001/` contains the first session's state,
sealed manifest and reports. Each dispatched slot has an `attempts/<slot>/`
directory containing a command log, linked receipt, immutable manifest and
native `archive/`. Native report paths in the campaign table are relative to
the campaign root. Source/scenario coverage comes from the entire planned
matrix, including failed, interrupted and unattempted slots.

An ordinary failed study does not stop later slots. SIGINT, SIGTERM or SIGHUP
stops further dispatch, forwards cancellation to the native owner and waits
for numerical-worker cleanup before sealing the session. The outer supervisor
allows at most 20 seconds for cleanup after cancellation or a deadline, longer
than the native numerical supervisor's 10-second grace. This cleanup allowance
does not change the scientific run budget. Partial native output
remains diagnostic evidence and cannot satisfy a complete study slot.

```bash
uv run --locked python -m experiments.campaigns resume \
  --campaign results/my-campaign
```

Resume first checks frozen configurations/source/protocol/locks, installed
runtime identities, prior session and attempt inventories, and authoritative
native reconstruction. It appends the next numbered session and links the
previous session manifest. Each remaining slot gets one attempt. Every retry
links its prior dispatched attempt manifest. The first completely accepted
attempt satisfies its slot permanently; accepted slots are verified and
skipped. Previous manifests, reports, failures and raw evidence are retained.

Changing the matrix, a frozen source, numerical protocol, implementation,
runtime or prior output requires a fresh campaign. An unsealed hard-killed
session remains forensic evidence and cannot be automatically resumed or
accepted; retain it and start a new campaign. This bounded route does not
attempt arbitrary crash repair.

## Reconstruct without executing models

```bash
uv run --locked python -m experiments.campaigns reconstruct \
  --campaign results/my-campaign --output results/my-campaign-report
```

Add `--allow-failed` to reconstruct retained failed or incomplete coverage.
The report output must be a new external directory. Reconstruction uses the
standard library and registered native reader, with no source callbacks,
simulators, NumPy or SciPy. Numerical environments are needed for execution
and identity-checked resume, not report reconstruction.

The [machine protocol](../experiments/campaigns/protocol.json) and
[isolated execution plan](research/ot032-ot037-execution-plan.md) define scope.
Independent researcher use, biological validity, treatment benefit and a
public release retain separate evidence requirements.
