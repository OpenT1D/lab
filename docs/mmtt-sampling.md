# MMTT information loss with fewer measurement times

OT-055 compares two or three prespecified reductions in **actually observed**
times through the shared [OT-054 analysis](observation-analysis.md). It retains
the same whole-body total endogenous secretion **including basal** over measured
0–120 minutes, in pmol, and follow-up minus baseline. C-peptide AUC is a separate
reference; the full curve is an analysis reference, not biological truth.

The synthetic CLI and local GUI are implemented. Internal verification covers
numerical controls, raw-input isolation, real execution, cancellation and native
reconstruction. Human
observations, empirical equivalence and independent researcher value are not
established. Public examples are engineered software controls; evaluation IDs
exercise the split logic, not blinded empirical performance. The later
[OT-057 interface verification](research/ot057-uiux-verification.md) records
saved-plan editing, compact comparisons and distinct execution/completeness/check
states on integrated main. The later [public host smokes](publication-security.md)
and [private Windows candidate checks](windows-installation.md) retain their
separate source and artifact scopes. Independent human usability and full
Windows GUI/distribution acceptance remain open.

The [beginner test packet](gui-test-session.md) supplies a separate Dutch task
card and offline feedback form for this route, with moderator expectations kept
apart. It assesses comprehension and independent use; the OT-056 comparative
researcher pilot remains separate.

## Run a complete synthetic comparison

From the repository root, choose fresh paths for every command:

```bash
uv sync --locked
uv run --locked python -m experiments.mmtt_sampling example \
  --case information-loss --development-only --output /tmp/ot055-development
uv run --locked python -m experiments.observation_analysis import \
  --package /tmp/ot055-development/package.json \
  --csv /tmp/ot055-development/observations.csv --output /tmp/ot055-development-import
uv run --locked python -m experiments.mmtt_sampling example \
  --case information-loss --output /tmp/ot055-input
uv run --locked python -m experiments.mmtt_sampling freeze-study \
  --package /tmp/ot055-input/package.json --csv /tmp/ot055-input/observations.csv \
  --settings /tmp/ot055-input/settings.json --design /tmp/ot055-input/sampling-design.json \
  --development-import /tmp/ot055-development-import --output /tmp/ot055-plan
uv run --locked python -m experiments.workflows check mmtt-sampling --config /tmp/ot055-plan
uv run --locked python -m experiments.workflows run mmtt-sampling \
  --config /tmp/ot055-plan --output /tmp/ot055-result
uv run --locked python -m experiments.workflows reconstruct mmtt-sampling \
  --archive /tmp/ot055-result --output /tmp/ot055-reconstructed
```

Read `report.md` and `report.json`. Each schedule also has the complete native
Task 1 report under `studies/<schedule>/`, including its references, point
calculations, conditional visit/change intervals, all perturbations and failures.
The reconstructed report retains these readable child reports. No original input
folder, simulator or R installation is needed for reconstruction. Keep a matching
trusted checkout; archived source snapshots are never executed.

The information-loss case is constructed so that the three-time model conclusion
reverses relative to the full reference. This is a software control under fixed
assumptions, not evidence about a human sampling schedule. `--case constant`
provides an invariance control. `--case incomplete` includes low C-peptide and a
censored visit; `--case steep-response` preserves a boundary-failure control.
Use the **same case** for the development and complete exports.

Exit 0 means all required calculations completed, including possible unresolved
conclusions. Exit 1 retains incomplete, failed or interrupted work; exit 2
refuses CLI admission. Reconstruct incomplete work with `--allow-failed`.
Successful reconstruction does not resolve an indeterminate scientific result.

## Use the local GUI

Start `uv run --locked python -m experiments.gui` and choose **Explore fewer
measurement times**. Prepare one of the four invented controls, inspect the
visit coverage, development selection and actual-time schemas, then review the
shared kinetic/uncertainty settings under **Review or change assumptions**.
For a first example, the supplied settings are ready to freeze. Optionally give
the analysis a recognizable name. **Validate and freeze plan** preserves the
inputs; **Run sampling comparison** executes the full reference and all subsets.
**Use frozen plan** repeats a saved plan. **Edit as new plan** lets you adjust
its settings using the preserved inputs and freeze a separate copy without
reinspection. Changed input files still require inspection; the original plan
remains unchanged. Field errors identify and focus the correction.

For your own synthetic packet, select metadata, CSV, shared settings, sampling
design JSON and a sealed development-only import directory inside the checkout.
The selection roster is checked before development CSV access. Full-curve
analyte failures remain visible while valid reduced children can still run.
Choose schemas using development material only; the GUI does not tune or rank
schemas from evaluation results.

**View result** goes directly to the report. Its opening finding identifies
direction reversals or unresolved comparisons. The supplied four-schedule
comparison separates development/evaluation and retains same-direction, reversal,
unresolved and unavailable counts for every assumption. The same participants
appear under each assumption; variant counts are not independent samples.
Expand details for all planned paired/visit comparisons, conditional intervals,
execution denominators and assay/glucose context. Expand each schedule for its
complete native report, including failed attempts. **Cancel operation** uses the
common owned-process cleanup. A cooperative sealed interruption retains the planned denominators;
an unsealed hard stop is shown as unavailable, not complete.

Use **Check saved analysis** for explicit native reconstruction and the two
download actions for unchanged Markdown/JSON. Saved plans and analyses survive
a server restart. The archive library also registers `mmtt-sampling` archives
from its explicit read-only roots and uses the same fixed native reader.
Names persist in saved plans, reports and Results as local display metadata.
**Analysis finished · results incomplete** describes a finished analysis with
missing required results; an execution failure or interruption has its own label.
**Saved report checked** records reconstruction separately from completeness.
Reconstruction checks evidence; it does not establish empirical equivalence.

## Frozen design and shared settings

| Schedule | Actual minutes retained | Omitted times for a complete source visit |
| --- | --- | --- |
| Full reference | 0, 15, 30, 60, 90, 120 | 0 |
| Five times | 0, 30, 60, 90, 120 | 1 |
| Four times | 0, 30, 60, 120 | 2 |
| Three times | 0, 60, 120 | 3 |

The versioned design records the participant allocation, development selection
identities and rationale. `freeze-study` verifies a development-only shared
import with two linked visits per selected person and the full observed times.
Development metadata and source cells must match the complete study packet.
All visits of a person retain one allocation. Different actual schedules need a
new matching design; nearest-time matching and invented measurements are refused.

Both C-peptide and glucose cells are removed together at omitted times in this
co-sampled synthetic package. The observed fasting sample at 0 and the measured
120-minute endpoint remain. Reduced glucose traces and AUC use retained times;
full measured context remains separately in the full reference archive. No fewer
blood draws are claimed: other required analytes may still need those samples.

Freeze explicit shared settings before execution: kinetic rates, whole-body
volume, initial peripheral factor, visit order, error scales, draw count and
seed. Task 2 supplies `required_times_min` for each child; omit that field from
the base settings. The physical method and all uncertainty/kinetic settings stay
identical across schedules. There is no automatic weight, BSA, glucose or
percentage normalization, participant kinetic fit or clinical uncertainty prior.

[Decisions 0067](decisions/0067-mmtt-feasibility-boundary.md),
[0068](decisions/0068-synthetic-observation-analysis-contract.md) and
[0069](decisions/0069-mmtt-sampling-reuse.md) bind the scientific and reuse scope.
Input C-peptide remains in nmol/L in the shared observation package, then converts
explicitly to pmol/L by exactly 1000. Volume is in L and kinetic rates are per
minute. The estimator integrates secretion in pmol; C-peptide AUC is in
pmol·min/L and glucose AUC in mmol·min/L.

## Remove measurements before analysis

The raw masker inspects CSV framing, declared identities and actual times only
to locate rows. It copies retained glucose/C-peptide/status cells without
numerical parsing, conversion, interpolation or imputation. Each child freezes
its own retained bytes through the native plan builder and uses the same native
runner, initializer, estimator, keyed uncertainty and report reader.

A missing requested time invalidates its visit before initial inventories,
perturbations and estimation. It cannot silently turn into a smaller schedule.
An invalid full reference does not reject a reduced child whose retained inputs
are valid. Original bytes and full-reference failures remain in the parent.
No full-curve state, optimized start, fitted error scale or participant nuisance
estimate is transferred to a reduced call. The nominal fasting equilibrium and
every perturbed initialization are recalculated from retained input.

Keyed measurement errors are identical at retained times across full/reduced
calls, with the same participant-shared offset across visits. Failed draws are
retained. A failed required draw makes the conditional interval unavailable;
no interval is calculated from successful draws alone. Negative inferred rates
remain visible under the shared diagnostic rule, never silently clipped.

## Read the report

Development and evaluation summaries remain separate. Each schedule and variant
shows signed/absolute deviations, bias, mean/median/max absolute differences,
RMS difference and sample SD of differences. Visit totals and participant paired
changes have separate denominators. Zero available pairs produce unavailable
statistics; one pair cannot supply a sample SD. No missing result becomes zero.
The precision SD is descriptive and is not a confidence interval for mean bias.
Repeated visits do not create independent participants.

Every planned paired comparison retains both intervals, directions and shared
across-assumption classifications. Two unresolved directions remain
indeterminate; failed uncertainty is unavailable. Correlation alone cannot
establish preservation or equivalence. Missing references, failed reduced fits,
interrupted atomic work and unattempted schedules stay explicit in coverage.

All visit minima, assay LOQ, censoring, C-peptide AUC, glucose exposure, measured
traces and meal/medication/renal/demographic context remain in comparison JSON
and native reports. No automatic low-value clinical cutoff or silent exclusion
is introduced. The shared source model is not biological truth; different
glucose exposure does not by itself establish beta-cell restoration or treatment
benefit.

## Reconstruction and evidence

The parent retains the frozen source packet, selection evidence, each native
plan, each native result, mask inventories, execution status and comparison
reports under the existing local-tool seals. The reader checks child inputs
against raw masking, identical settings except required times, native arithmetic
and all saved attempts before rebuilding comparisons. Resealed forged attempts,
statistics, dropped schedules and injected journal reports are rejected.

The [verification and case-packet handoff](research/ot055-verification.md) records
current execution. The [preparation record](research/ot055-preparation-verification.md) preserves
earlier checks. The independent manufactured vectors in
`experiments/mmtt_sampling/fixtures/numerical-reference.json` now pass on the
shared estimator: constant, low constant, global linear rise and linear fall,
including unclipped negative-rate diagnostics. Their software tolerance is not
an empirical agreement margin. They were checked against closed-form totals,
compartment conservation and separate C-peptide AUC references.

The separate [empirical evaluation preparation](research/mmtt-sampling-empirical-plan.md)
requires authorized complete observations, assay/context and justified kinetics,
a participant-disjoint freeze, domain-chosen endpoint/change margins, low-value
rules and adequate precision before held-out evaluation. No empirical assessment
runs through this synthetic route. **No reduced schedule meets the criteria**
is a valid research outcome, without proving product value or approving a
prospective clinical sampling protocol.

The older `freeze` (development time inventory) and `freeze-import` (shared
import receipt) commands remain preparation utilities. The executable study
configuration is the sealed directory created by `freeze-study`.
