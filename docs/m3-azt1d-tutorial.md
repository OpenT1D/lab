# AZT1D causal forecast workflow

This separate route implements the input and window rules of [AZT1D-M3/0.1](research/m3-azt1d-protocol.md). It does not replace the [Ohio M3/1 workflow](m3-tutorial.md). It converts one frozen phase, preserves source-row lineage, fits the fixed Ridge estimator on qualified development windows, freezes the learned model after diagnostic validation, and evaluates against persistence. Reports reconstruct from saved artifacts without the original files or estimator packages. All implementation evidence is synthetic; no human predictive result is established. See the [implementation acceptance record](research/m3-azt1d-reproduction.md).

## Run the synthetic example

Use the repository's locked tooling environment. All inputs created below are invented; the commands do not acquire or read patient files. Choose fresh output directories for each attempt.

```sh
uv sync --locked
uv run --locked python -m experiments.m3.azt1d fixture \
  --output results/azt1d-example/input
uv run --locked python -m experiments.m3.azt1d normalize \
  --input results/azt1d-example/input/source.csv \
  --intake results/azt1d-example/input/development-intake.json \
  --output results/azt1d-example/development
uv run --locked python -m experiments.m3.azt1d prepare \
  --conversion results/azt1d-example/development \
  --output results/azt1d-example/prepared
```

The fixture includes numerically identical duplicates, a conflicting duplicate, missing glucose and a microsecond-preserving clock-phase change. Its short length does not meet the human 288-window/24-hour requirement. The generated validation and evaluation intake files can exercise synthetic conversion independently. `prepare` accepts only the development phase.

`development.json` records every registered origin, eligible training windows, history and target exclusions, timing metadata and the operational coverage verdict. Counts reconcile without treating rows as independent people or as clinical time coverage. No estimator is fitted by these commands. The full study commands below add isolated fitting and evaluation without changing these conversion rules.

## Native conversion contract

The CSV grammar is strict. The standard nine-column header contains `EventDateTime`, `DeviceMode`, `BolusType`, `Basal`, `CorrectionDelivered`, `TotalBolusInsulinDelivered`, `FoodDelivered`, `CarbSize` and `CGM` in the reviewed order. The known alternative header contains `Readings (CGM / BGM)`; its glucose stays `unsupported`, including its registered timestamps in accounting. Neither schema supplies a separate availability timestamp.

An intake JSON uses schema `opent1d.m3.azt1d/1` and contains:

| Field | Meaning |
|---|---|
| `kind` | Explicit `synthetic` or `human`. Never label human files synthetic. |
| `person` | Private local alias, bound to the allocation for human processing. |
| `phase` | `development`, `validation` or `evaluation`; reserve is not an import phase. |
| `source_sha256` | Hash of the complete native CSV bytes. |
| `origin_local` | Exact first source timestamp, in naive local ISO seconds or microseconds. |
| `start_us`, `end_us` | Half-open phase bounds in integer microseconds from that origin. |
| `row_start`, `row_stop` | One-based native data-row indices; header excluded, stop exclusive. |
| `policy` | Explicit glucose status convention with its evidence reference. |

The converter verifies the row slice against every source timestamp and row width. It does not interpret glucose outside the selected phase. Hashing and CSV transport still encounter the full file's bytes; that is not an assertion that the file itself was never opened. Glucose from other phases is not included in normalized output or diagnostics. Equal-time groups cannot be cut across phases. The declared origin must equal the first source timestamp. Backward clocks, missing columns and unexplained formats are rejected, never repaired by sorting or rounding.

The normalized document contains `schema`, `person`, `clock`, `unit`, `bounds_us` and `rows`. Each row retains `time_us`, `available_us`, `segment`, `raw_time`, `status`, `value`, `bound` and `source_rows`. Exact numeric duplicate comparison precedes floating conversion. Same-time conflicts become `ambiguous`; identical glucose can collapse with all contributing source rows retained. No insulin totals or physiological inputs are constructed.

## Explicit glucose status policy

There is no built-in assumption that a device's boundary value is an exact measurement. The caller must supply one of these reviewed conventions:

- `numeric_boundary: verified_exact`, with a nonempty `reference` supporting exact positive numeric values.
- `numeric_boundary: exclude`, with explicit finite positive `lower < upper` and a nonempty `reference`. Values at or outside those bounds become `invalid`, not asserted censored values. Select bounds from documented semantics or an explicitly prespecified conservative rule, not test performance.

An optional `tokens` map can define `LOW` or `HIGH` with `status` equal to `censored_low` or `censored_high`, respectively, and a positive `bound`. Without that rule those tokens are invalid, not guessed boundary readings. Empty/NA/N/A are missing; NaN, infinity, overflow and nonpositive numbers are invalid. Unsupported text is never echoed in error output.

The synthetic fixture's `verified_exact` reference applies only to its invented numbers. It is not evidence for the actual AZT1D release.

## Human intake and held-out restrictions

Human inputs, intake files, bound references and outputs must resolve outside the repository. The converter requires explicit reviews for authorization, derived retention, release, units, status policy, clock and availability, with authorization, retention and availability references. These records attest a review; setting flags does not create rights or scientific evidence.

Human intake additionally supplies `allocation_reference` and `partition_reference`. Each is an object containing an absolute local `file` path and its `sha256`. The allocation is the existing private 25-file intake registry with twenty study roles and five reserved roles. It must retain unique aliases/source hashes and its `policy_sha256`. A partition uses schema `opent1d.azt1d.partition-reference/1`; its alias, phase, native source hash, policy hash, data-row indices and elapsed bounds must agree with the intake. The CLI does not generate a new allocation or override the previously frozen 60/20/20 split. Fractional-microsecond boundaries are rounded up only to express the same half-open interval over integer instants; source timestamps are never rounded.

The `reviews` object requires these booleans to be true: `authorized_processing`, `derived_retention`, `release_reviewed`, `units_reviewed`, `status_policy_reviewed`, `availability_reviewed`, `clock_reviewed`. It also requires nonempty strings `authorization_reference`, `retention_reference`, `availability_reference`.

**Direct human evaluation conversion remains disabled.** The study runner can authorize it only against the frozen source/allocation/split, a verified learned model and a durable access ledger. Reserve participants are rejected before source access. Reviewed human development and validation conversion remain supported; the development-preparation command never uses validation. No human conversion or evaluation was run while implementing this route. A private, referenced release policy and authorized processing remain execution conditions.

## Artifacts, failures and checks

Conversion creates a private intake snapshot, normalized observations, a conversion receipt and `status.json`. The receipt binds native bytes, intake identities, normalized bytes, source-row counts, protocol and code fingerprints. `prepare` rejects altered bytes, incomplete conversions, changed code and incomplete source-row lineage. Outputs use new directories and restrictive creation permissions. Actual encryption, synchronization settings and access by other software remain operator responsibilities.

The CLI prints completion or a safe exception class, not patient values, identifiers, paths or arbitrary exception messages. Conversion failures retain a safe failure status when output creation has begun. Preparation preflight failures create no new output; a failed write is not a successful completed study. The full study additionally retains subprocess failures, partial traces, deadlines, cancellation and planned but unattempted participants.

The repository check runs synthetic importer, causal-window and service tests, including future-value poisoning, duplicate conflicts, microsecond offsets, missing targets, allocation tampering, unsupported people, output tampering and safe diagnostics:

```sh
uv run --locked python -m unittest discover -s tests -p 'test_m3_azt1d_*.py' -v
uv run --locked python scripts/check.py
```

The [decision record](decisions/0008-azt1d-causal-forecast.md) separates the implemented synthetic workflow from conditional human execution and independent reproduction. Neither passing tests nor a successful conversion demonstrates predictive improvement.

## Run a complete synthetic study

Install the existing, separately locked estimator environment. The root environment remains tooling-only. This example invents two ten-day records; only development and validation are normalized before fitting.

```sh
uv sync --locked --project experiments/m3/runtime
uv run --locked python -m experiments.m3.azt1d study-fixture \
  --output results/azt1d-study/input
uv run --locked python -m experiments.m3.azt1d freeze \
  --registry results/azt1d-study/input/registry.json --output results/azt1d-study/plan
uv run --locked python -m experiments.m3.azt1d init-ledger \
  --plan results/azt1d-study/plan/plan.json
uv run --locked python -m experiments.m3.azt1d fit \
  --plan results/azt1d-study/plan/plan.json --output results/azt1d-study/fit
uv run --locked python -m experiments.m3.azt1d evaluate \
  --plan results/azt1d-study/plan/plan.json --fit results/azt1d-study/fit \
  --output results/azt1d-study/evaluation
uv run --locked python -S -m experiments.m3.azt1d report \
  --study results/azt1d-study/evaluation --output results/azt1d-study/reconstructed.json
```

A single verification command exercises the same stages and compares saved and reconstructed reports:

```sh
uv run --locked python -m experiments.m3.azt1d.verify \
  --output results/m3/azt1d-verification
uv run --locked --project experiments/m3/runtime python -m unittest discover \
  -s experiments/m3/azt1d -p test_native.py -v
```

Fitting uses the unchanged M3 runtime: the same equal-person weights enter both StandardScaler and fixed Ridge. A person qualifies from development alone: at least 288 windows spanning at least 24 hours. Unqualified people remain planned; they do not select a replacement from reserve. Validation is diagnostic and does not alter coefficients. A qualified final comparison additionally needs 288 paired evaluation scores spanning 24 hours. The report weighs contributing people equally and bootstraps whole people; it preserves separate coverage and incomplete-cohort status. No synthetic error value is a human accuracy estimate.

## Study registry and access history

The study registry is a private JSON object with `schema`, `kind`, `people`, `ledger` (an absolute external path) and `prior_access`. Each person has `id`, an absolute native `source`, `development` and `validation` conversion references (`folder`, `sha256` of conversion.json), and `evaluation`. The latter contains an `intake_reference` (`file`, `sha256`) plus the complete `origins_us` schedule from authorized timestamp-only intake. The freeze validates metadata without opening glucose observations or native CSVs. It binds the complete roster, source identities, adjacent elapsed 60/20/20 slices, policies and registered evaluation origins. Evaluation conversion must reproduce that exact schedule.

For a human registry, retain all twenty study participants, the same allocation reference and five untouched reserved roles. Supply study `reviews`: `authorized_fitting`, `authorized_evaluation`, `overlap_reviewed` and `prior_access_disclosed`, all true, with a nonempty `reference`. These declarations attest the actual reviewed scope; they cannot create authorization. Human freezing additionally requires committed, reviewed sources. Complete the native unit/schema and scientific checks before asserting the intake reviews.

`prior_access` is exactly `reviewed: true`, `status: none|present|unknown`, and `reference`. Human records require a meaningful disclosure reference. Disclose the earlier bounded intake and any subsequent inspection; directory copies and newly initialized files cannot restore an unseen holdout.

`init-ledger` is explicit and refuses existing files. The local ledger uses exclusive creation, restricted permissions, advisory process locks, a hash chain and fsync. Each evaluation attempt records access before normalization and before execution, bound to the person and learned freeze. Reusing a frozen model appends history and exposes repeated access. Once this ledger records evaluation access, fitting a new model through that plan is rejected. A changed research question requires a documented amendment and disclosed reuse, not deletion of history.

The ledger is a local audit trail, not an independent external witness. Someone able to replace the ledger and every pinned receipt can rewrite history. A copied report verifies its saved ledger prefix; it cannot certify that no later live access occurred. A failed write authorizes no read and is retained for investigation rather than silently repaired.

## Conservative boundary policy from public documentation

Reviewed on 20 September 2026. [AZT1D version 1](https://data.mendeley.com/datasets/gk9m674wcx/1), DOI `10.17632/gk9m674wcx.1`, identifies the original CC BY 4.0 release. The [authors' paper, version 1](https://arxiv.org/html/2506.14789v1), sections II and III-B, describes Dexcom G6 Pro and the `CGM` unit mg/dL. These statements have not been verified against every native source record in this implementation task.

The [official G6 Pro user guide](https://dexcompdf.s3-us-west-2.amazonaws.com/Dexcom-G6-Pro-User-Guide.pdf), LBL017179 Rev 007, March 2022, printed pages 121 and 146, documents a numerical range of 40–400 mg/dL and LOW/HIGH indications outside it. This is device evidence, not proof of the AZT1D CSV mapping or exactness at its boundaries.

A supported conservative intake choice is therefore `numeric_boundary: exclude`, `lower: 40`, `upper: 400`, with a reference recording these sources and the explicit assumption that interior numeric CGM values are reported point observations. Do not supply a LOW/HIGH token mapping until the release-specific meaning is established. Boundary and outside-range numbers stay invalid rather than being asserted censored; unknown text remains invalid. This narrows the assessed observations and leaves extreme-glucose accuracy unresolved. It does not establish online availability, remove the mixed CGM/BGM restriction or justify physiological/controller claims. Freeze the selected policy before fitting; it is not selected by evaluation performance.
