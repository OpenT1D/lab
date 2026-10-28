# Compare a supplied secretion model on the M4 synthetic challenge

**Current public scope:** this native research route is outside the initial
two-task public exercise. Its pinned environments retain advisories and are
excluded from automatic public installation. Read the
[current runtime and CI policy](publication-security.md) before using the
historical setup commands below.

This bounded workflow accepts one **trusted local Python source file** and
compares its evoked secretion with the unchanged [BC-007 reference](research/m4-chain-results.md).
Both traces receive the same prescribed synthetic glucose values from 0 to
100 minutes at 0.25-minute intervals. Each trace is passed through the
existing insulin liver inlet and C-peptide central inlet, with the same
separate synthetic basal state for the total case. No glucose feedback,
calibration or human observations are involved.

## Model contract

Provide a regular `.py` file with a function:

```python
def secretion(times_min: list[float], glucose_mmol_l: list[float]) -> list[float]:
    ...
```

The function receives the full 401-point time and glucose arrays and returns
401 **evoked** secretion rates in `pmol/(kg min)`. Rates must be finite,
nonnegative and at most 1000 in that unit. This upper limit only protects the
numerical workflow; it is not a physiological range. The interface does not
support an implicit basal rate, a different grid, C-peptide-specific scaling,
data fitting or changes to the BC-007 kinetics. The same molar rate is routed
to the insulin liver inlet and the C-peptide central inlet. A stateful model
may integrate internally before returning its complete output array.

Supply a JSON declaration alongside the source:

```json
{
  "schema": "m4-model/1",
  "model_id": "your-model-and-version",
  "source_sha256": "64 lowercase hexadecimal SHA-256 digits of the Python source",
  "rights_basis": "your basis for running and retaining this source locally",
  "dependencies": "Python and exact packages or environment lock used by this model",
  "output_unit": "pmol/(kg min)"
}
```

The source hash must match the file bytes. The declaration records the
supplier's identity, rights statement and dependency claim; the workflow
does not independently audit those claims or lock the model's packages. The
selected Python interpreter and version are recorded. The model is **local
trusted code**, not a security sandbox. Use only source you have permission
to run. The workflow copies it into the output archive. Keep confidential
source and any private data outside version control and choose an output
location appropriate for its rights. Model stdout and errors are saved in
`model.log`.

## Run

From the repository root, prepare the locked environments and create a fresh
BC-007 archive:

```console
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked python -m experiments.m4.chain.run --output /tmp/bc007-reference
```

Create your declaration with the SHA-256 of your source file. The included
[`example_model.py`](../experiments/m4/external_secretion/example_model.py)
is an invented interface exercise, not an externally reviewed model. Then:

```console
uv run --locked python -m experiments.m4.external_secretion.run \
  --model /path/to/model.py \
  --declaration /path/to/model.json \
  --reference /tmp/bc007-reference \
  --output /tmp/m4-external-result
```

Use `--model-python /path/to/venv/bin/python` if the model needs its own
installed dependencies. `--timeout` sets the model execution limit in seconds
(default 30, allowed 1–600). The selected interpreter runs the archived source
with isolated Python startup; imports must be available in that interpreter.
Only a single source file and its declared environment are included in this
version. Package code and external files are not copied automatically.

The workflow verifies the BC-007 reference archive before copying it, checks
the model declaration and output, executes both kinetic branches in their
locked environments, and records numerical solver/oracle, input accounting
and positivity checks. A failed run preserves a failed manifest and logs.
It does not turn a passing numerical check into biological validity.

## Inspect and reconstruct

`report.json` gives source identity, integrated secretion and, for incremental
and synthetic-basal cases, the candidate and reference input amounts, sampled
peak concentrations, maximum absolute concentration difference, and final
concentration difference in both branches. It also records whether the
candidate passed the numerical checks. Interpretation of those differences
requires a scientific question and suitable independent observations.

Reconstruct the report from archived inputs and trajectories without running
the supplied source or either kinetic solver:

```console
uv run --locked python -m experiments.m4.external_secretion.report \
  /tmp/m4-external-result --output /tmp/m4-external-reconstruction.json
```

Reconstruction checks hashes, the full BC-007 archive, the source and glucose
contract, branch input equality, numerical ledgers and the saved report. The
archive preserves source snapshots and environment lockfiles for inspection.
It cannot prove that the supplier's declared dependencies or rights are
complete, and it does not establish reproducibility outside the recorded
local environment.
