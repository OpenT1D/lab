# M3, M4 and M5 researcher workflow integration

**Status:** internally verified on 2 October 2026. This record concerns
synthetic software integration and preserves the separate evidence limits
of the three workflows.

The combined checkout retains the original M3 forecast, M4 secretion and
M5 prognosis implementations. It does not connect their scientific models
into a new multiscale model. The [execution record](../../experiments/integration/researcher_workflows.json)
binds source revisions, local artifact hashes and observed checks.

## Source history and scope

The clean execution commit is `e90fc9a540f5f695cd5504eb94a94700af9f8ec8`,
following these branches from common base `a0a10da`:

| Workflow | Original tip retained in history | Canonical guide |
| --- | --- | --- |
| M3 | `9b65a83` | [Researcher forecast intake](../m3-researcher-forecast.md) |
| M4 | `3534528` | [Secretion and C-peptide comparison](../m4-researcher-workflow.md) |
| M5 | `e21e1cb` | [Frozen prognostic model comparison](../m5-researcher-workflow.md) |

The branches were merged in M4, M3, M5 order without rewriting their
commits. Shared documentation conflicts retain all three additions;
decisions 0052, 0053 and 0054 are registered. The M3 CI verification remains,
and the existing locked beta-cell CI job now includes the five new M4
numerical tests. Hosted CI has not been executed for this local integration.

A separate agent review checked exact blob identity: all 42 branch-specific
files remain byte for byte unchanged. All 754 baseline files outside shared
documentation and CI remain unchanged, including dependency locks, tooling
and historical source/evidence. The three original tips remain ancestors
of the integration revision. The subsequent evidence commit adds only this
record, its navigation entry, execution metadata and a changelog entry.

## Observed checks

`uv sync --locked` and `uv run --locked python scripts/check.py` passed on
the clean execution commit: **826 repository tests** and the documentation
build, including formatting, lint, Markdown, YAML, citation and navigation
checks. The final evidence documents are separately checked and built.
Native execution uses the unchanged isolated locks under
`experiments/m3/runtime`, `experiments/m0/simglucose` and
`experiments/m4/beta_cell/runtime`; the root environment remains tooling only.

| Workflow | Integrated execution evidence |
| --- | --- |
| M3 | Both trend and frozen native-donor Ridge examples pass; each checks 1,550 reference predictions and 1,516 paired targets over two planned people. Fresh-process traces match exactly. JSON and Markdown reports reconstruct byte for byte after original invented inputs are removed. |
| M4 | Five isolated numerical tests pass. A shared fresh BC-008 reference completes 44 primary and 44 repeat trajectories and passes all 20 criteria. Dalla Man and ultradian routes each complete eight primary and eight repeat causal trajectories, accept six observer cases, complete six primary and six repeat observation cases and pass all 13 observation checks. No repeat artifacts change. All six JSON, Markdown and SVG report files reconstruct byte for byte with `python -S`. |
| M5 | The exported frozen example retains all 32 invented people, fits its example solely on 20 eligible development people and produces reproducible paired predictions for all seven eligible held-out people. The reconstructed report equals the run report without candidate execution or refitting. |

M3 reference arithmetic is independently checked for these worked examples;
reconstruction does not independently reproduce every possible supplied
algorithm. No evaluation refitting occurs in the M3 verification. M4 remains
a synthetic, one-way C-peptide observation of its unchanged feedback route.
M5 remains a prognostic analysis shape with complete failure accounting.

## Reproduce the integration checks

Use fresh output paths. From the repository root:

```sh
uv sync --locked
uv run --locked python scripts/check.py
uv sync --locked --project experiments/m3/runtime
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked python -m experiments.m3.researcher verify \
  --output results/integration/m3
uv run --locked --project experiments/m4/beta_cell/runtime \
  python -m unittest experiments.m4.researcher_workflow.test_numerical -v
uv run --locked python -m experiments.m4.researcher_workflow.run \
  --config experiments/m4/researcher_workflow/dalla_man.json \
  --output results/integration/m4/dalla-man
uv run --locked python -m experiments.m4.researcher_workflow.run \
  --config experiments/m4/researcher_workflow/ultradian.json \
  --reference results/integration/m4/dalla-man/reference \
  --output results/integration/m4/ultradian
uv run --locked python -S -m experiments.m4.researcher_workflow.report \
  results/integration/m4/dalla-man \
  --output results/integration/m4/reconstructed-dalla-man
uv run --locked python -S -m experiments.m4.researcher_workflow.report \
  results/integration/m4/ultradian \
  --output results/integration/m4/reconstructed-ultradian
uv run --locked python -m experiments.m5.researcher_workflow.run export-example \
  results/integration/m5-model
uv run --locked python -m experiments.m5.researcher_workflow.run run \
  results/integration/m5-model results/integration/m5
uv run --locked python -m experiments.m5.researcher_workflow.run reconstruct \
  results/integration/m5
```

Compare the reconstructed M4 JSON, Markdown and SVG bytes with each original
report as described in its canonical guide. Local output is retained under
`results/integration/` in the integration worktree and is not versioned.
A new execution has its own provenance and may produce different metadata
hashes; do not relabel it as the archived execution above. Saved hashes
record artifact consistency rather than authenticated execution.

No unrelated historical native campaigns were rerun for this additive
integration. Independent human usability, authorized observation assessment,
biological validity and treatment benefit retain their original evidence
gates. These local checks establish coexistence of the bounded workflows
and their reproducible analysis; they establish no human predictive or
therapy result.
