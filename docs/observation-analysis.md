# Retrospective observation analysis

OT-054 implements one bounded offline analysis of invented paired meal tests,
within the [OT-053 narrow boundary](research/ot053-mmtt-feasibility.md).
It estimates total endogenous secretion over measured 0–120 minutes under
explicit fixed kinetics, then assesses the paired conclusion across frozen
engineering assumptions. It is separate from the causal M4 simulation callback.
Human-data analysis, individual T1D kinetics and researcher value remain open.
The shared core, CLI and local GUI provide the complete synthetic Task 1
route. The [internal verification record](research/ot054-verification.md)
separates this bounded software evidence from the open empirical and user gates.
The later [OT-057 interface verification](research/ot057-uiux-verification.md)
records saved-plan editing, field recovery and report navigation on integrated
main. The later [public host smokes](publication-security.md)
and [private Windows candidate checks](windows-installation.md) retain their
separate source and artifact scopes. Independent human usability and full
Windows GUI/distribution acceptance remain open.

The [beginner test packet](gui-test-session.md) supplies a separate Dutch task
card and offline feedback form for this route, with moderator expectations kept
apart. It assesses comprehension and independent use; the OT-056 comparative
researcher pilot remains separate.

## Run the complete synthetic CLI example

From the repository root, choose fresh local directories:

```sh
uv sync --locked
uv run --locked python -m experiments.observation_analysis example --output /tmp/ot054-input
uv run --locked python -m experiments.observation_analysis freeze \
  --package /tmp/ot054-input/package.json --csv /tmp/ot054-input/observations.csv \
  --settings /tmp/ot054-input/settings.json --output /tmp/ot054-plan
uv run --locked python -m experiments.workflows check mmtt-sensitivity \
  --config /tmp/ot054-plan
uv run --locked python -m experiments.workflows run mmtt-sensitivity \
  --config /tmp/ot054-plan --output /tmp/ot054-result
uv run --locked python -m experiments.workflows reconstruct mmtt-sensitivity \
  --archive /tmp/ot054-result --output /tmp/ot054-reconstructed
```

Read `/tmp/ot054-result/report.md` and `report.json`. The example has one invented
pair and three required variants. The model-light C-peptide AUC and measured
glucose context are shown separately from total secretion. The production
calculation uses the Python standard library; no simulator or R installation
is needed. Root Python remains repository tooling, not a simulation package.
The optional numerical source-parity check below uses the historical BC-003
lock, which retains advisories and is outside automatic public setup. It is not
required to run the standard-library example above; see
[the current runtime policy](publication-security.md).

`example --case` also accepts `assumption-dependent`, `unresolved` and `censored`.
These are engineered development controls. The assumption-dependent case has
higher C-peptide AUC but different uncertainty labels under nominal and
initial-inventory assumptions. It illustrates the distinction between the
reference and primary endpoint; it is not an empirical participant finding.

`--config` is the **sealed plan directory**, not its JSON file. Edit settings
before `freeze`; freeze binds the endpoint/protocol, exact input bytes, ordered
visits, variants, error procedure, source ancestry, trusted implementation and
runtime before evaluation. Changed bytes or runtime are refused. Use a new
plan explicitly after a change. A `check` verifies frozen bytes and identities
without calculating estimates; invalid observations are retained by `run`.

Existing output directories are refused. Run exit status 0 means all required
calculations completed, including an unresolved conclusion; 1 means an
incomplete/failed/interrupted analysis; 2 means a refused CLI admission.
Use `--allow-failed` on reconstruction for an incomplete or interrupted archive.
Successful reconstruction verifies the recorded analysis; it does not turn a
failure or an unresolved result into a resolved scientific conclusion.

For import-only diagnosis before freezing, the separate `import` command takes
`--package`, `--csv` and a fresh `--output`; `verify-import --archive` checks it.
`import.json` retains all declared visits and validation errors. Its CLI prints
status, leaving source cells in the local snapshot. Invalid imports exit 2.

## Use the local GUI

Start the [local interface](local-gui.md), then choose **Paired meal-test
analysis → Explore paired meal tests** on Start. The other secretion card
runs the separate forward simulation task.

1. Choose an example and **Prepare example**. Alternatively, open **Use your
   own synthetic CSV and metadata** and select metadata, observations and a
   settings JSON from this checkout. **Inspect observations** validates the
   declared units, linkage, actual times, missing/censored cells and complete
   visit roster without estimating secretion. Paths outside the checkout,
   symlinks and declared human packages are refused.
2. Keep the supplied settings for a first example, or open **Review or change
   assumptions** for baseline/follow-up order, each variant's rate constants,
   volume, initial peripheral factor, rationale and uncertainty controls.
   All supplied variants remain required. To add/remove variants, edit the
   settings file and inspect again. Optionally enter an **Analysis name**;
   example names are supplied automatically.
3. Choose **Validate and freeze plan**, then **Run paired analysis**. Freeze
   retains original input/settings bytes and calls native import, freeze and
   common-entry check. Editing any field requires a fresh freeze. **Use frozen
   plan** repeats an unchanged plan; **Edit as new plan** starts a separate draft
   using its preserved inputs. Changed settings survive the next freeze and the
   original plan stays unchanged. Invalid fields open their details, receive
   focus and show a specific correction beside the field.
4. Read the three interpretation labels, paired totals and conditional
   intervals, per-visit intervals and minimum-rate boundaries, and every
   perturbation denominator. Expand visit context for glucose, measured
   C-peptide AUC, actual observations, assay/LOQ and medication/renal context.
   Expand failures for every failed visit/draw and required unattempted draw.
5. **View result** opens the selected operation's report directly. Choose
   **Check saved analysis** to reconstruct through the fixed native
   reader. **Download report** and **Download full JSON** return the original
   Markdown/JSON bytes. The label identifies the saved plan; draft edits do
   not change an existing report. Reopening the server downgrades an earlier
   verification to a recorded check until explicitly checked again. Saved names
   appear in the plan selector, report and Results. They are local display
   metadata and do not enter the frozen scientific files.

**Analysis finished**, **results complete/incomplete** and **Saved report
checked** describe separate facts. A completed execution may retain unavailable
required results. A saved-report check confirms reconstruction, not scientific
validity or a resolved conclusion. Actual execution failures and interruptions
retain their own status.

One global operation owns the execution lane. **Cancel operation** uses the
existing process supervisor; a cooperative interruption retains the declared
roster with explicitly unavailable atomic results. Closing the browser does
not cancel a worker. Both completed and incomplete analyses appear in
**Results → Your experiments**. The [archive library](gui-archive-library.md)
can register separate copies/exports of sealed native `mmtt-sensitivity`
archives, reconstruct them and display the same report. GUI administration
paths themselves cannot be registered as foreign archives.

Display rounds numbers to eight significant digits. Full JSON retains exact
stored values. The browser computes no estimates or intervals. Display checks
report-byte identity; explicit reconstruction additionally checks frozen
inputs, protocol, trusted source and retained attempts. Changed evidence
withdraws the report/downloads until unchanged evidence is restored and checked.
The GUI admits 32–1024 draws and seeds through 9007199254740991; the CLI supports
larger exact 64-bit seeds. Other native work/size limits remain unchanged.

## Local observation contract

`experiments.observation_analysis.observations` accepts metadata schema
`opent1d.observations/1` and UTF-8 CSV bytes. This initial route admits declared
synthetic observations only. No human-data eligibility, access authorization or
T1D parameter default follows from a valid import.

Metadata declares `data_kind: synthetic`, invented-data `provenance`, fixed
`units`, and a `participants` roster. Units are `min` for time, `mmol/L` for
glucose and `nmol/L` for C-peptide. Convert other units explicitly before import
and document that conversion in provenance; the importer never guesses units.
Original bytes are retained by the analysis archive. The estimator converts
C-peptide to pmol/L by multiplication by exactly 1000.

Each participant has an `id`, one `allocation` (`development` or `evaluation`),
`context` and exactly two `visits`. Context retains `age_years`, `sex`,
`weight_kg`, `height_cm`, `renal_context` and `population`. Allocation belongs
to the participant, so their visits cannot cross the split. Each visit retains
an `id`, `challenge_id`, `protocol`, `meal`, `medication_context` (including
insulin context), and `assay`. Assay metadata retains its `id` and
`cpeptide_lod_nmol_l` and `cpeptide_loq_nmol_l`. These are declarations, not
independently verified source or medical facts.

The exact CSV header is:

```text
participant_id,visit_id,challenge_id,time_min,glucose_mmol_l,glucose_status,cpeptide_nmol_l,cpeptide_status
```

Use declared identities, increasing actual sample times, measured 0 and 120
minute endpoints, and no repeated sample times per visit. Resolve technical
replicates explicitly before import and retain the conversion procedure.
Glucose status is `observed` or `missing`; C-peptide status additionally permits
`below_loq`. Missing or censored cells must be blank. A numerical C-peptide value
below the declared LOQ is rejected unless represented as censored. Import
preserves missing/censored statuses; it does not substitute zero or half a limit.
The fixed synthetic analysis fails affected visits rather than imputing them.
Missing glucose context also prevents a resolved paired conclusion.

Settings may additionally declare `required_times_min`. Missing required measured
times invalidate that visit before initialization, perturbations or estimation.
Task 2 uses this shared admission rule to enforce its frozen sample subsets;
the numerical estimator and uncertainty procedure remain identical.

The importer returns every declared visit, its parsed rows, and row-numbered
errors. Absent visits remain explicit failures. Unknown identities or broken
CSV framing remain package-level errors. Invalid rows are never silently dropped
from an otherwise accepted visit. Diagnostics do not echo cell contents.

## Frozen method and assumptions

[Decision 0068](decisions/0068-synthetic-observation-analysis-contract.md) and
`experiments/observation_analysis/protocol.json` specify the bounded method.
It independently expresses the two-compartment process equations described by
[Polonsky et al. (1986)](https://doi.org/10.1172/JCI112308), with
[BC-003 ancestry](research/m4-cpeptide-results.md). No upstream GPL R code or
product dependency is used. The OT-053 R-function audit is a separate external
source check, not the implementation of this route.

Central concentration is piecewise linear on actual measured times. The
peripheral inventory update is exact on each interval. Summing central and
peripheral inventory changes plus irreversible elimination gives total
secretion, including basal, in **whole-body pmol**. This retains both endpoint
intervals. There is no extrapolation and no simultaneous kinetic fit.

The plan supplies `k1_per_min` (central to peripheral), `k2_per_min` (return),
`k3_per_min` (irreversible central removal), `volume_l` and
`initial_peripheral_factor`. Nominal initialization uses observed C-peptide at
0 minutes: central amount is `V*C(0)` and peripheral amount is
`(k1/k2)*V*C(0)`. Factor 1 is equilibrium; other factors are explicit
prehistory stresses. Baseline is recalculated for every perturbation and
retained observation subset. No per-person estimate learned from another
curve enters the estimator.

The primary contrast is the second declared `visit_order` visit minus the
first, in pmol. There is no division by weight, BSA, glucose, duration or
baseline secretion. Demographic context is preserved without silently changing
scale. Equimolar insulin/C-peptide appearance is an explicit assumption.
Glucose, injected insulin and hepatic extraction do not alter C-peptide
removal in this bounded model.

The example supplies BC-003 nominal coefficients as synthetic controls, an
explicit whole-body volume of 4.585 L, a 20% volume stress and a 75% initial
peripheral-inventory stress. They are engineering cases, not a human range or
T1D prior. The nominal profile is not assigned from a normal/type-2 demographic
category. A concentration interpolant fits by construction; this supplies no
independent goodness-of-fit or biological-validity evidence.

Negative inferred rates and totals are retained. The method checks interval
endpoints and any interior rate minimum analytically. A rate below the fixed
1e-9 pmol/min numerical tolerance marks a boundary failure; the tolerance is
not a clinical threshold. Required failed visits/variants remain in the report.
The bounded calculation refuses more than 500,000 planned interval evaluations
while retaining the declared roster and required variants.

## Conditional uncertainty and interpretation

The example declares 128 synthetic perturbations: independent Gaussian error
with SD 2 pmol/L at each retained C-peptide observation, plus one participant
Gaussian offset with SD 1 pmol/L shared across both visits and retained times.
These are invented controls, not measured assay precision. The same perturbed
observations are used across variants. Keyed streams depend on the frozen
seed, person, draw, visit and retained time, so omitted observations cannot
influence another sample's random stream.

Each draw repeats initialization, interpolation and total integration. Preserve
all failed draws, including a perturbation below the declared LOQ or a negative
inferred secretory rate. Any failed required draw makes that variant's interval
unavailable. Never select successful draws alone for a nominal interval.

| Frozen outcome | Report interpretation |
| --- | --- |
| Every required variant completes and all nominal 95% intervals are strictly above zero, or all strictly below | Consistent within investigated assumptions, with increase/decrease shown |
| Complete variants give different direction labels with at least one resolved direction | Assumption-dependent |
| Any required fit/uncertainty/context failure, or all intervals contain zero | Insufficiently determined |

An interval containing zero is unresolved; it does not establish no change.
Intervals are central synthetic perturbation intervals with linear
order-statistic interpolation, conditional on the frozen assumptions. Human
coverage is untested. Differences between variants are shown separately and
never averaged into a posterior. No default cohort significance test, treatment
contrast or clinical margin is provided. A different glucose stimulus can
accompany a secretion difference without establishing restored beta-cell
function or a treatment effect.

## Saved analysis and failure handling

`frozen/` retains original CSV/metadata/settings, the protocol and opaque source
snapshots. `attempts.json` retains every point calculation, interval inventory,
shared perturbed observation vector and attempted uncertainty result.
`report.json` contains full-precision paired results, references, per-variant
counts and all failed draws. Markdown shows readable totals, intervals,
measured traces, context and every failure. `execution.json` keeps execution
state separate from scientific completeness. The existing local-tool manifest
seals all bytes, and the [experiment catalogue](experiment-catalogue.md) uses
an explicit native reader for this task.

Reconstruction replays the same frozen keyed variates and exact algebra,
verifies attempts and rebuilds identical report bytes. It uses the installed
trusted implementation and checks source/plan identities. It does not choose a
new seed, optimize kinetics, import archived Python or call a simulation/R
engine. Archive/source snapshots stay unchanged. Retain a matching trusted
checkout for this version; source snapshots themselves are never executable
reader instructions.

A cooperative interruption preserves its state, frozen/admission bytes and
complete declared roster. Unfinished atomic analysis attempt statuses are
explicitly unavailable; they are not invented fit results. A hard kill can
leave an unsealed directory, which the normal reader refuses. This retains
forensic evidence without claiming a verified complete archive.

## Reuse and current verification

Bounded regular-file intake, strict JSON, fresh directories and archive sealing
reuse existing OpenT1D helpers. The common task entry, task-directed root setup
and catalogue have explicit `mmtt-sensitivity` registrations. The kernel's
preprocessing/initialization/estimation boundary only receives its supplied
observations. OT-055 must remove observations before calling that same boundary.
This is a bounded task contract, not a general plugin API.

The earlier [BC-013 profile analysis](research/m4-profile-likelihood-results.md)
assumes a fixed synthetic coupled model, regular grid and engineering noise;
[BC-015-P4](research/m4-sampling-window-results.md) assumes a known injected
pulse. Their optimizers and confidence rules were assessed and not copied into
this different inverse problem. The existing forward BC-003 model and its
independent analytical kernel are used as numerical references.

Focused checks cover equilibrium, nonzero initial inventory, a separate RK4
integral, high-precision small-interval expressions, unit covariance, boundary
failures, paired uncertainty, unresolved conclusions, censoring/context errors,
plan hashes, real CLI/catalogue execution, fresh-process repeats, relocation,
resealed forged results and an actual SIGTERM interruption. These are internal
software checks. The [integrated verification record](research/ot054-verification.md)
adds real GUI jobs, browser display checks and final locked repository checks.

The explicit source-parity command is:

```sh
# Historical private-archive reference check; not needed for the public MMTT task.
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked --project experiments/m4/beta_cell/runtime python \
  -m unittest experiments.observation_analysis.test_numerical -v
```

Both unchanged BC-003 analytical and ODE forward paths are checked. For its
known synthetic positive-input control, the 15-minute interpolant produces a
negative local inferred rate and a 197.7902 pmol endpoint discrepancy. The
failure is retained. Refining the grid gives discrepancies 1.13671, 0.0454334
and 0.00283950 pmol at 5, 1 and 0.25 minutes against the 25,200 pmol known total;
the last meets the prespecified 1e-4 relative criterion. This tests numerical
convergence and exposes a coarse-sampling limitation; it does not validate
MMTT physiology or any clinical sampling schedule.

`experiments/observation_analysis/preparation.json` remains the historical
import-only preparation record. Independent human use, empirically supported
T1D kinetics/uncertainty and comparative researcher benefit retain their separate
roadmap gates.

## Controlled companion-task handoff

`experiments/observation_analysis/handoff.json` binds the shared core to commit
`23e1bc12bc52b2443dca4f6157c474df1e9188f8` and records its schemas, code hashes,
verification and the masking boundary required by OT-055. The estimator and
shared analysis hashes remain unchanged by GUI integration. Its historical
`core-verification.json` records the earlier core-only stage; the integrated
verification record binds final Task 1 acceptance. This handoff does not
authorize human execution.
