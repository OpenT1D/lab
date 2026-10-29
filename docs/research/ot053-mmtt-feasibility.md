# OT-053 — Feasibility of paired MMTT secretion analysis

**Decision, 18 October 2026: NARROW.** Proceed with a bounded, entirely
synthetic OT-054 preparation using fixed, explicitly supplied C-peptide
kinetics. OT-055 may subsequently test removal of synthetic observations
through that same core. No screened source establishes authorized access to
enough complete adult visit pairs, defensible individual kinetics or an
empirical sampling-equivalence margin. Human analysis, a clinical sampling
recommendation and demonstrated product benefit remain open.

This completes the feasibility decision required by the
[original OT-053 acceptance plan](roadmap-history-2026-10-28.md#planned-mixed-meal-analysis-tasks), not the empirical
or product gates. [Decision 0067](../decisions/0067-mmtt-feasibility-boundary.md)
records the scientific boundary. No participant records were downloaded,
no access application or outreach occurred, and no researcher has agreed to
participate. Public metadata and papers establish possible sources, not access.

The [current delivery plan](../../ROADMAP.md#common-laboratory-delivery-plan)
selects subsequent work. This dated feasibility decision preserves its original
scientific boundary and proposed pilot criteria; it does not impose a general
competitive-advantage requirement on laboratory development.

## One intended researcher task

The intended user is an analyst in an adult T1D beta-cell preservation research
team, working with a secretion modeller and an assay specialist. This is a
proposed user profile, not an enrolled person. Their concrete decision is:
**can the direction of a person's baseline-to-12-month change in estimated
0–120-minute endogenous secretion be reported consistently across the
prespecified assumptions, or must that conclusion be qualified?** The first
empirical candidate is the adult subset of TrialNet TN05, preferably considered
within a prespecified arm rather than pooling treatment contexts. No treatment
contrast or efficacy claim is part of this task.

The proposed population is adults aged at least 18 at baseline, with established
T1D and measurable residual secretion, two linked standardized MMTTs and
sufficient assay/renal information for the eventual kinetic protocol. An assay
LOQ is not a new clinical eligibility threshold. Do not select participants on
their observed change, replace a missing 12-month test with a convenient visit,
or infer a complete adult subset from whole-study enrolment. Keep everyone
screened, each intended visit and every failure in the coverage table.

The proposed full schedule is fasting −10 and 0 minutes and post-meal 15, 30,
60, 90 and 120 minutes for laboratory glucose and C-peptide. This resembles
the schedule described by [Lachin et al. (2011), Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC3213096/).
It is a candidate observation design, not proof of a particular release's
actual times or adequacy for deconvolution. Preserve actual collection times
relative to the recorded meal start, meal formulation/dose/completion, fasting,
insulin and other medications, and deviations. Do not prescribe insulin changes
to research participants. An empirical protocol must resolve nominal versus
actual clocks and endpoint coverage before fitting; no extrapolated 120-minute
tail is allowed in the initial synthetic implementation.

## Source and data matrix

The screen is targeted, not an assertion that no suitable data exist anywhere.
Sources were checked on 18 October 2026 unless explicitly marked as an earlier
repository audit. Production NIDDK catalogue/FAQ opens returned 403; the
official test-domain renderings were readable through the web tool. A separate
direct TN05 HTML fetch returned 503. Search-index descriptions and the test
mirror are not verification of a production release's bytes or rights.

| Candidate and primary source | Measurement and paired-visit evidence | Population, assay and metadata fit | Access evidence and disposition |
| --- | --- | --- | --- |
| [TN05, Version 2, DOI 10.58020/1bv7-0y43](https://repository.niddk.nih.gov/study/76); [inspected test rendering](https://test.repository.niddk.nih.gov/study/76) | Catalogue describes a two-hour C-peptide outcome within a longer MMTT and follow-up. It lists Research Labs, examinations, medications and missed-visit tables. These are leads; no field-level challenge/sample crosswalk or adult paired completeness count was verified. | Includes ages 8–45 and recent-onset T1D: adult filtering is necessary. Per-sample glucose linkage, assay limits/precision, renal context and actual insulin timing remain unverified in the released tables. | Available for request, with T1D-related permitted-use restrictions. No project approval, DUA, received bytes or complete-pair count. **Preferred conditional lead**, not executable data. |
| [TN03](https://repository.niddk.nih.gov/study/112); [inspected test rendering](https://test.repository.niddk.nih.gov/study/112); [Greenbaum et al. (2008)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2551636/) | The paper reports repeat MMTTs; this supports a repeatability question, not baseline-to-year-one disease change. The inspected catalogue says Data Expected, with zero datasets and zero public documents. | Mixed adult/child population. The paper records a changing C-peptide LOQ and substitution at the LOQ, so historical numeric values cannot automatically be treated as uncensored observations. | No released participant dataset or access grant established. **Do not select as an available cohort.** |
| [CIT-07/08](https://repository.niddk.nih.gov/study/92), assessed in the [25 September field audit](m4-cit07-public-crosswalk.md) | That audit found fasting/60/90-minute MMTT fields, without a dense 0–120-minute C-peptide series. Related FSIGT fields are a different challenge. | Adult transplant context differs from residual native secretion; renal and immunosuppression context matter. The audit retains a creatinine-unit discrepancy. | Request-only source, no grant or paired observation coverage established. **Reject the audited core schedule for this task**, without claiming no additional substudy exists. |
| [NCT01817959 registry](https://clinicaltrials.gov/study/NCT01817959?tab=results), assessed in the [25 September aggregate audit](m4-alternative-observation-screen.md) | Public meal summaries at several time points/visits are group aggregates. The earlier audit retains inconsistent visit labels and analyte denominators. The current web rendering supplied no additional usable record details. | Transplant population; individual covariance, censoring and exact same-test linkage are unavailable from summaries. | Public aggregate readability supplies neither individual records nor an IPD grant. **Exclude as a paired fitting/evaluation dataset.** |

There is **no verified count of usable authorized pairs** for the selected
task. No adult paired sample size or precision/power conclusion can be inferred
from catalogue row counts, specimen counts, paper enrolment or group means.

Before a human protocol can be frozen, an authorized local custodian must
establish all of the following from the actual release, without publishing
private values or identifiers:

1. Exact release identity, hashes and approved project/person/use/derived-output
   terms, including retention, export, publication and any redistribution limits.
   The [NIDDK requestor FAQ](https://test.repository.niddk.nih.gov/faq) describes
   controlled access, ethics documentation and a use agreement; public catalogue
   access does not satisfy these conditions.
2. A versioned crosswalk joining participant, ordered visit, challenge, specimen,
   analyte, actual collection clock, value, unit and missing/censoring code.
   Separate C-peptide and glucose rows must be linked to the same test.
3. Counts of adults with both designated visits, endpoint coverage and each
   measured schedule, plus all excluded/incomplete pairs and reasons. Freeze a
   participant-disjoint development/evaluation allocation before modelling;
   all visits of a person stay together.
4. Assay platform/calibration, specimen matrix, per-era/sample LOD and LOQ,
   precision near low values, censoring/reported substitutions, sample handling
   and assay changes between visits. Neither zero nor LOQ/2 is a silent default.
5. Visit-specific body size, age and demographic context required by the selected
   kinetics, renal measurements and their timing, insulin/medication exposure,
   meal completion and protocol deviations. Obtain a population/renal kinetic
   justification; a good concentration fit alone cannot supply it.
6. A statistician's precision design using the available pairs, low-signal cases,
   missingness and paired covariance. Task 2 requires researcher-defined
   acceptable errors and uncertainty before held-out assessment. No empirical
   sample size or clinical equivalence margin is selected here.

## Common endpoint and synthetic conventions

These conventions freeze the bounded preparation. They are design decisions,
not measured findings or a human calibration. Both tasks must retain them until
a separately versioned, source-specific protocol explicitly supersedes them.

| Quantity | Convention |
| --- | --- |
| Time and observations | Elapsed minutes from meal start; canonical laboratory glucose in mmol/L and C-peptide in pmol/L. Keep original units/bytes and explicit conversion identity. No CGM substitution for laboratory glucose. |
| Secretion | Whole-body endogenous insulin secretion `q(t)` in pmol/min, inferred from C-peptide appearance under an explicitly stated equimolar-release assumption. No insulin hepatic extraction, injected insulin or SC absorption is applied to C-peptide. |
| Primary endpoint | `S_v = integral(q_v(t), t=0..120)` in pmol, **including basal secretion**; `Delta S = S_followup - S_baseline` in pmol. Positive means higher estimated secretion under those tests. |
| Normalization | Primary endpoint is whole-body, without division by weight, BSA, glucose, test duration or baseline secretion. No percent change near zero. Any later mass/BSA-normalized endpoint must have its own name, denominator and visit convention. |
| Separate references | Trapezoidal measured C-peptide AUC in pmol·min/L; mean C-peptide AUC is that value divided by 120, in pmol/L. Neither is `S_v`. Also show fasting glucose, glucose AUC in mmol·min/L, measured glucose/C-peptide traces and meal/insulin context. |
| Initial state | Synthetic nominal: `Q1(0)=V*C(0)`, `Q2(0)=(k1/k2)*Q1(0)`, basal `q_b=k3*Q1(0)`. States are whole-body pmol; `V` is L; rates are min⁻¹. Do not reset a nonzero fasting test to empty compartments. |
| Basal handling | Do not subtract fasting C-peptide and label the result total secretion. An incremental diagnostic, if requested later, must add back `120*q_b` before producing this primary endpoint. A −10-minute sample is evidence about fasting stability, not part of the 0–120 endpoint. |
| Pair and summary | The pair is explicitly ordered by the plan, not inferred from filenames. OT-054 preparation reports individual pairs and all attempts; it provides no default cohort significance test or treatment contrast. A cohort estimand/summary and missing-pair rule require an empirical plan before evaluation. |

The exact dimensional conversions are `1 nmol/L = 1000 pmol/L` and
`1 pmol/mL = 1000 pmol/L`. A mass-based C-peptide conversion must declare its
molecular-mass convention; BC-003's rounded 3021 g/mol belongs to that source
and its synthetic controls, not an unexamined assay harmonization rule.

An observed secretion difference may reflect a different glucose stimulus or
clearance/assay assumptions. It is not by itself recovery, beta-cell mass,
insulin requirement or a treatment effect. Greenbaum's repeat-test study also
found glucose context relevant to the C-peptide response; its study entry
glucose range is not adopted here as a clinical decision rule.

## Method and reuse audit

| Source/method | What can be reused | Limits and OT-053 disposition |
| --- | --- | --- |
| [Polonsky et al. (1986)](https://www.jci.org/articles/view/112308), and the existing [BC-003 model card](models/polonsky1986-cpeptide.md) | Two-compartment C-peptide dynamics, independently implemented forward controls and explicit mass/volume units. The source includes normal volunteers and insulin-deficient T1D kinetic experiments. | Exogenous C-peptide kinetic evidence does not establish residual-secretion inference accuracy. Existing nominal group coefficients are synthetic controls, not individual demographic estimates or a distribution. Reuse the mathematical model and verification ancestry for preparation. |
| [Van Cauter et al. (1992)](https://pubmed.ncbi.nlm.nih.gov/1551497/) | Standard kinetics conditioned on body size, sex and age can avoid individual bolus studies in the studied populations. | The abstract describes 200 decay curves in normal, obese and non-insulin-dependent diabetes subjects. Its reported agreement is not a T1D uncertainty bound. Full parameter-table transcription was not independently repeated in this audit. **No normal/niddm category is selected for T1D.** |
| [`insulin.secretion`](https://github.com/kstier/isr.deconv/tree/320497e33cbdff2cc7f7d9f0c370080ab5a00229), version 0.0.2 | Existing linear/spline inverse implementation and demographic helpers are useful external audit/comparator candidates. | Source pinned and inspected; native R execution and spline dependency behavior remain unverified. Numerical and input/endpoint issues below prevent unqualified adoption. No root dependency or copied implementation is added. |
| [Mari 2002 prior source audit](m4-independent-source-preflight.md) and oral minimal models | Possible future stimulus-response models, with source-specific fitted components. | Whole-trace fitting is appropriate offline but not inside the causal M4 callback. Similarly named responsivity indices do not equal integrated secretion. A second fitted method is unnecessary for the first bounded task. |
| Existing BC-011–015 and execution/archive code | Numerical controls, failure accounting, sensitivity patterns, provenance and reconstruction patterns. | Existing experiments assume specific synthetic forcing/noise/grids. They do not validate a measured-data error model or provide a general observation-analysis API. OT-054 must introduce an explicit separate contract, leaving historical outputs intact. |

### Current upstream identity, rights and source findings

The [source manifest](../../experiments/ot053_feasibility/source-manifest.json)
pins the full current GitHub commit
`320497e33cbdff2cc7f7d9f0c370080ab5a00229`, version 0.0.2, and SHA-256 hashes of
the inspected implementation, helpers, DESCRIPTION and license. The indexed
[r-universe package page](https://kstier.r-universe.dev/insulin.secretion)
showed 0.0.1 at `ee2cd76a5e…`, whereas the
[current manual](https://kstier.r-universe.dev/insulin.secretion/doc/manual.html)
showed 0.0.2. The current source corrects the older helper's BSA/volume unit
handling; do not report the old volume issue as an unfixed current defect.

DESCRIPTION declares GPL ≥3 and imports `glue`, `lifecycle`, `npreg` and
`rlang`; the inspected source tree had no `tests/` directory. Absence of that
directory is not proof that no validation exists elsewhere. The license file
contains GPLv3. Reuse cannot relabel that code Apache-2.0: the
[Apache compatibility explanation](https://apache.org/licenses/GPL-compatibility.html)
distinguishes inclusion of Apache code in GPLv3 works from the reverse.
Adoption would need a documented distribution arrangement, notices, license
and corresponding-source obligations, plus a dependency audit. A subprocess
alone is not an automatic license exemption. This dossier selects no such
integration and redistributes no upstream code.

The following findings refer to
[`R/isr.deconv.R` at the pinned commit](https://raw.githubusercontent.com/kstier/isr.deconv/320497e33cbdff2cc7f7d9f0c370080ab5a00229/R/isr.deconv.R):

- Input validation checks equal lengths and at least two observations, then
  sorts times. A production wrapper still needs finite values, unique increasing
  times, valid positive kinetic/volume inputs, units, censoring and coverage
  checks; sorting must not silently resolve conflicting duplicate samples.
- The first observation enters the initial peripheral-equilibrium convention.
  This is an assumption about prehistory, not an independently measured state.
- The linear path approximates a concentration-times-exponential integrand
  using nodes at the first time and interval midpoints. Even a constant
  concentration therefore incurs a spacing-dependent integration error.
- Its returned rates are at interval midpoints; treating them as an observed
  0–120-minute endpoint, trapezoiding between them and discarding the endpoint
  intervals would change the estimand. Full-window integration needs an explicit
  convention and an independent check.
- The spline path fixes `spar=0.3` and contains a derivative scaling adjustment.
  Spline dependency normalization, negative-rate behavior, smoothing choice,
  endpoint behavior and error propagation need a locked native R comparison.
  The adjustment is an audit question, not a demonstrated spline defect here.

### Targeted local probe and numerical boundary

The [standard-library analytical probe](../../experiments/ot053_feasibility/probe.py)
hash-checks the inspected source files and uses synthetic observations with
declared fixed reference constants. It
neither runs R nor imports or reproduces the whole external estimator. No
`Rscript` executable was found on PATH or the three standard installation paths
recorded in the manifest. A separate probe executes two unmodified source
functions in a temporary WebAssembly R runtime, as described below; no native
R installation or complete package installation was performed.

For a constant central amount `M`, exact equilibrium secretion is `k3*M`.
Approximating the exponential integral by the source's midpoint-node
trapezoids changes it by
`-k1*k2*M*exp(-k2*t)*(I_approx-I_exact)`. This follows from the two-compartment
equations and supplies an analytical audit independent of R's integrator.
With BC-003's fixed synthetic T1D nominal rates, the
[recorded controls](../../experiments/ot053_feasibility/probe-results.json)
find maximum absolute rate errors of **4.5327%**, **4.7746%** and **16.8738%**
for schedules `[0,15,30,60,90,120]`, `[0,30,60,90,120]` and `[0,60,120]`.
On a one-minute grid the error is 0.00556%. These are mathematical consequences
for one invented equilibrium case, not observed human biases or executed
package outputs. They justify a native upstream test before adoption.

The same probe independently checks basal balance and unit covariance:
`V=4.585 L`, `C=200 pmol/L`, `q=47.684 pmol/min`, so total secretion is
`5722.08 pmol` and C-peptide AUC is `24000 pmol·min/L`. Their different units
are intentional. These numbers do not describe a participant.

The separate [R-function harness](../../experiments/ot053_feasibility/webr-probe.mjs)
loads the hash-checked, unmodified `isr.deconv.R` and `isr.volume.R` into
[WebR](https://docs.r-wasm.org/webr/latest/api/js/classes/WebR.WebR.html) 0.6.0,
R 4.6.0, under Node 22.22.2. Its
[results](../../experiments/ot053_feasibility/webr-results.json) record runtime
binary and harness hashes. For the same constant-concentration cases, the
executed linear routine's maximum rate errors are **4.5326%**, **4.7746%** and
**16.8738%**, agreeing with the analytical controls within the prespecified
`1e-5` absolute tolerance on relative error. At 105 minutes in the first case
it returns approximately 45.5227 rather than the exact 47.684 pmol/min.

The helper returns 4620.5556 mL for its invented 86.2 kg, 181.5 cm male example,
confirming the current unit correction's arithmetic. Deliberately invalid
negative volume returns negative rates, and duplicate times return nonfinite
rates with seven retained "collapsing to unique 'x' values" warnings. These are
selected source-function behaviors requiring intake validation, not clinical
findings. The full package, its imported dependencies, plotting, spline path
and a native Rscript build remain untested. The separately locked WebR runtime
is audit tooling only, not a selected OT-054 product dependency.

A numerically feasible OT-054 candidate is **fixed-kinetic two-compartment
deconvolution with piecewise-linear C-peptide and exact interval integration**.
This uses the existing source model, not a newly fitted glucose-secretion law.
For an interval of width `h`, concentration `C0 + m*x`, and fixed kinetics,
derive the peripheral update from the existing ODE:

```text
Q2(h) = exp(-k2*h)*Q2(0)
      + k1*V*[C0*(1-exp(-k2*h))/k2
              + m*(h/k2 - (1-exp(-k2*h))/k2^2)]
integral(q) = V*(C(h)-C0) + Q2(h)-Q2(0)
              + k3*V*h*(C0+C(h))/2
```

The integral follows by adding the two compartment equations; it includes
inventory changes and eliminated amount. OT-054 must independently implement
and check this derivation against forward known-input cases and a separate
numerical calculation, including stable small-interval expressions. It must
not silently clip negative inferred rates or label an interpolated fit as
biological validation. This is a technical target, not a shipped estimator.

## Uncertainty and interpretation requirements

Keep three separate outputs: conditional measurement uncertainty for each
frozen variant, differences between variants, and failures/indeterminate cases.
Do not pool variants into a posterior or call a numerical stress range a human
parameter distribution. Initial synthetic variants may compare fixed BC-003
nominal profiles and deliberately labelled initial-inventory/scale stresses;
none becomes an empirical T1D prior, confidence interval or normal-to-T1D map.

The empirical protocol must justify assay error versus concentration, detection
and quantification censoring, calibration/batch correlation and within-person
kinetic uncertainty. Propagate errors by repeating the entire preprocessing and
estimation operation, including baseline/initialization; retain failed draws.
Use shared nuisance draws between a person's visits where appropriate, rather
than fabricating independence. Replicate measurements/kinetic information are
needed to justify that covariance. A sensitivity grid cannot replace them.
Do not simultaneously fit arbitrary secretion and all clearance/volume
parameters to one C-peptide trace. Glucose remains stimulus context in this
bounded estimator, not a denominator that creates a new endpoint.

For the synthetic Task 1 rehearsal, a conditional interval strictly above zero
labels an increase; one strictly below zero labels a decrease; an interval
containing zero is unresolved, never proof of no change. If all required
variants succeed and give the same resolved direction, report "consistent
within investigated assumptions". Differing labels with at least one resolved
direction are "assumption-dependent". All unresolved labels, or any missing/
failed required variant, give "insufficiently determined" with the available
results still shown. A nominal 95% interval may exercise this reporting rule
with declared invented error assumptions; it has no claimed human coverage.
The human interpretation rule, meaningful-change margin and uncertainty method
must be frozen with domain input before any empirical evaluation.

Task 2 must remove measurements **before** baseline calculation, interpolation,
uncertainty estimation and fitting. Any retained fasting measurements must be
part of its explicit schedule/input package. Do not transfer a full-curve
peripheral state, smoothing setting fitted to that person, or nuisance estimate
learned from omitted observations. Keep both endpoints at 0 and 120 in the
initial subsets, retain glucose at the declared available times, and call the
full curve a reference analysis rather than truth. No blood-draw reduction is
claimed unless the complete multi-analyte protocol can omit those draws.

## Strong comparator and intended-user test

| Workflow | Evidence available now | Matched comparison and remaining gate |
| --- | --- | --- |
| [AOMM plus competent scripts](https://www.nanomath.us/aomm) | Vendor describes local Windows OGTT/MMTT batch analysis, secretion indices including total secretion, and precision measures. | Inspect the actual licensed build and permitted exports. Verify whether its total endpoint, kinetic and initial-state choices can match this plan, then add competent scripts for pairing/variants/coverage as needed. No API, automated connector or exact estimator equivalence is assumed. Vendor claims are not our benchmark results. |
| [SAAM II plus competent scripts](https://www.nanomath.us/saamii) | Vendor describes model construction/estimation in a Windows application. | A competent modeller must configure the same equations, kinetics, errors and window, verify outputs, then use scripts for the same variants/schedules/report rubric. Access, license, installation and export behavior are unverified here. |
| Well-prepared notebook | A notebook can use the very same future OT-054 estimator, with organized data validation, variants, uncertainty, pairing, diagnostics and export. No external licensed tool is necessary for this comparison. | Have an experienced analyst prepare and debug it before timing. Match information, cases, computing environment and support. Count preparation and maintenance; a deliberately weak notebook is not an acceptable baseline. |
| OpenT1D bounded route | Existing provenance/failure/archive patterns are plausible reuse. | No task implementation or observed advantage yet. Batch plots, uncertainty and local processing alone do not distinguish it from the comparators. Test fewer missed assumptions, complete failure coverage and reconstruction with measured effort. |

The formative test remains the roadmap's **six researchers from at least two
teams**, with an independent domain reviewer and counterbalanced tool order.
This is recruitment/design intent, not six known participants. Use matched
synthetic case packs first: a clean pair, changed glucose context, incompatible
units, a censored/low-signal sample, a missing endpoint, a duplicate conflict,
a failed variant and a reduced-schedule leakage trap. The rubric requires the
correct endpoint/unit/pair, both references and context, all attempts,
uncertainty limits and a justified conclusion; an incomplete/incorrect report
cannot count as a fast success.

Freeze the strongest applicable comparator and rubric before sessions. Measure
active time to correct complete reports, installation/compute/support time,
interpretation errors, timeouts and assistance, as well as first-study and
repeat-study preparation/maintenance effort. Retain the proposed progression
criteria of at least five of six completing each task correctly, at least 30%
lower median active time per task and no extra critical interpretation errors;
report paired variation without pretending six users power a market claim.
If licensed access cannot be established, run only the disclosed notebook
comparison and leave superiority to AOMM/SAAM II untested. No tool sessions,
licensed runs or user-value findings occurred in OT-053.

## Controlled handoff and remaining evidence

The shared planning baseline is local commit
`37f027b` on `codex/ot-053-mmtt-feasibility`, based on
`3567fbc5f72a02acf0c91b0476c976c3c7c52e7b`. All six supplied planning-file
hashes were verified before copying into the clean assigned worktree.
The [handoff record](../../experiments/ot053_feasibility/handoff.json) names
the exact checked dossier/probe commit for downstream consumption. Integrators
must account for the identical planning patch already present in other branches;
do not overwrite their working changes or cherry-pick that patch twice.

OT-054's permitted boundary is one separate offline synthetic observation
contract and one fixed-kinetic estimator, with explicit supplied parameters,
unit conversion, ordered visits, retained failures, per-variant uncertainty,
the full-window endpoint and saved-analysis reconstruction. Reuse suitable
infrastructure; do not add an empirical importer default, demographic T1D
mapping, causal M4 adapter or competing Task 2 estimator. Source/runtime/plan
identities and original-versus-canonical units belong in its saved records.

Before calling that implementation verified, require constant-basal and known
nonconstant forward inputs, independent integral/mass checks, time-unit and
concentration/volume covariance, numerical refinement, fresh-process repeat,
selected censoring/duplicate/coverage failures and reconstruction after moving
the archive. Freeze tolerances appropriate to each reference before testing.
The native upstream R/spline audit remains necessary **if that package is later
adopted**; it does not block an independently expressed source-model synthetic
implementation with its own numerical controls.

OT-055 should consume a controlled OT-054 commit and demonstrate observation
masking/refitting through the same core, with no removed-data leakage. Candidate
synthetic subsets can exercise infrastructure, but no empirical equivalence
claim is permitted until authorized full observations, development selection,
researcher-defined margins, adequate paired precision and a held-out freeze
exist. OT-056 may prepare its rubric and cases; actual researchers and licensed
comparators remain separate dependencies.

This dossier's reproducible local command is:

```sh
uv sync --locked
uv run --locked python -m experiments.ot053_feasibility.probe \
  --source-dir /private/tmp/ot053-insulin-secretion-current \
  --output /private/tmp/ot053-probe-repeat.json
uv run --locked python scripts/check.py
```

Fetch only the public source files at the exact URLs in the source manifest
into the specified source directory; no automatic data or package download
occurs. Use a new output path. The probe refuses existing output and source
hash mismatches. Compare its JSON with the committed result within numerical
roundoff if using a different Python/libm build. The handoff records actual
verification and its limits. Repository checks establish software/documentation
consistency, not kinetic applicability, human usability or biological validity.

The [focused verification record](../../experiments/ot053_feasibility/verification.json)
also records an exact JSON repeat in a fresh process, refusal to overwrite an
existing result, and refusal of an altered source file before output creation.
The complete locked repository check passed **1,288 tests with 13 existing
skips**, lint/navigation checks and the strict documentation build. No model
behavior or GUI route was added by this dossier. The separate R harness also
repeated exactly in a fresh process and a fresh locked temporary installation.
To reproduce that
separate audit, explicitly install its own frozen development runtime and run:

```sh
npm ci --prefix experiments/ot053_feasibility/webr-runtime \
  --ignore-scripts --no-audit --no-fund
node experiments/ot053_feasibility/webr-probe.mjs \
  experiments/ot053_feasibility/webr-runtime/node_modules/webr \
  /private/tmp/ot053-insulin-secretion-current /private/tmp/ot053-webr-repeat.json
```

The [audit-only lock](../../experiments/ot053_feasibility/webr-runtime/package-lock.json)
does not change the repository's root Python environment or install the full
R package. Use a fresh output filename. No upstream source, runtime binaries or
participant measurements are redistributed with the dossier.
