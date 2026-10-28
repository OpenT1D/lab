# M3 forecasting workflow

M3/1 prepares an offline, CGM-only 30-minute forecast assessment using existing scikit-learn Ridge and persistence. The [protocol](research/m3-protocol.md) owns research rules, the [feasibility review](research/m3-data-feasibility.md) owns data/rights selection, and the [evidence record](research/m3-reproduction.md) owns demonstrated results. Public commands below use invented synthetic observations. They do not download patients or reproduce a human study.

## Install and verify

Use a clean committed checkout, Python 3.12, and uv 0.11.16 or newer on macOS or Linux. Keep the existing M0 environments unchanged. The new estimator environment pins scikit-learn 1.7.2, NumPy 2.2.6, SciPy 1.15.3 and transitive dependencies separately; root tooling contains no estimator or simulation package.

```sh
uv sync --locked
uv sync --locked --project experiments/m3/runtime
uv run --locked python scripts/check.py
uv run --locked --project experiments/m3/runtime python -m unittest discover \
  -s experiments/m3 -p test_native.py -v
uv run --locked python -m experiments.m3.verify --output results/m3/verification
```

Use new output paths for every attempt. Verification freezes inputs/settings, fits only development, executes the complete synthetic schedule, repeats in new processes, checks known-evaluation reuse and actual cancellation/deadline handling, and reconstructs the report with `python -S`. Retain the whole directory, including failed attempts. The scientific meaning of a synthetic error value is only that this software example computed it.

## Execute the steps separately

```sh
uv run --locked python -m experiments.m3 fixture --output results/m3/input
uv run --locked python -m experiments.m3 freeze \
  --registry results/m3/input/registry.json --output results/m3/plan
uv run --locked python -m experiments.m3 fit \
  --plan results/m3/plan/plan.json --output results/m3/fit
uv run --locked python -m experiments.m3 evaluate \
  --plan results/m3/plan/plan.json --fit results/m3/fit --output results/m3/study
uv run --locked python -S -m experiments.m3 report \
  --study results/m3/study --output results/m3/reconstructed.json
cmp results/m3/study/report.json results/m3/reconstructed.json
```

Freeze requires committed, unmodified source and checks each registry-listed file's bytes. It hashes evaluation files without parsing their values. Fit reads only training files, splits them by the protocol's elapsed-time rule, learns scaling and coefficients from development, and saves diagnostic validation forecasts. Its `freeze.json` binds that learned model, validation trace and fit result before evaluation. Evaluation records access before reading values. A later execution against the same plan requires `--reuse` and a new output directory; the report then identifies known evaluation reuse. Copying a plan cannot make inspected data unseen: the researcher must preserve access history across copies, institutions and dataset repackaging.

`report.json` includes all people and scheduled origins, prediction versus scoring coverage, exclusions, failures, error metrics, origin-glucose strata, censoring lower bounds and the participant bootstrap. It also reconstructs validation. Positive primary MAE difference means Ridge was worse than persistence on the available paired observations. An interval from six people remains descriptive. No automatic clinical success threshold or physiological validity label is produced.

## Normalized data contract

This is a bounded internal JSON format, `opent1d.m3/1`, not a stable public API. The generated fixture is the canonical complete example. `registry.json` identifies source, release, evidence kind, rights, clock and a list of source-linked people. Each person has one training file and one evaluation file, exact SHA-256 hashes and half-open elapsed-minute bounds. Identities must be unique; training/testing time overlap and duplicate file reuse are rejected. Human membership must identify the original six-person cohort in the private crosswalk.

An observation document contains `schema`, `person`, `clock`, `unit` and `rows`. Each row preserves:

| Field | Meaning |
| --- | --- |
| `time` | Nonnegative elapsed measurement minute; strictly increasing, no duplicates |
| `available` | Earliest available minute, never earlier than measurement |
| `segment` | Contiguous clock segment; no prediction history crosses a segment change |
| `raw_time` | Original timestamp text retained privately |
| `status` | `measured`, `missing`, `invalid`, `censored_low` or `censored_high` |
| `value` | Positive finite number for measured CGM; otherwise null |
| `bound` | Optional positive censor bound; null for measured/missing/invalid values |

Units are explicit `mg/dL` or `mmol/L`; the latter converts using the protocol's factor 18. Clock labels distinguish UTC, shifted local time and elapsed synthetic time. No timezone is guessed. Any clock repair needs a verified external mapping and a new recorded normalization identity. Fractional intervals and off-grid observations are preserved; they do not silently become five-minute samples. Six exact features and a target 30 minutes later are required for ordinary scoring. There is no interpolation or implicit missing-zero convention.

The supplemental synthetic signal fixture illustrates unknown meals and recorded delivery alongside changing basal commands. The bounded `integrate_intervals` function integrates known disjoint rates over actual half-open durations and reports unknown coverage. It rejects mixed command/delivery meanings and amount-as-rate inputs. Those supplemental signals never enter M3/1 predictors.

## Conditional Ohio-style intake

The optional `normalize` command supports only the publicly documented/parser-observed `patient/glucose_level/event` XML grammar (`ts`, `value`, day-month-year time). It preserves exact elapsed local time, rejects unreviewed CGM attributes, XML entities and nonfinite values, and records zero without a censor flag as invalid. It does not adopt another parser's resampling, merging of training and test, or insulin imputation. An absent meal remains unknown. Other source sections are listed as excluded, not converted to physiological input.

**Only self-authored XML fixtures have exercised this adapter. No actual provider release has been tested.** An authorized recipient must verify units, flags, timestamps, identity, availability assumptions and native grammar before use; an incompatible release is rejected or needs a documented adapter correction before freezing. There is no universal XML importer or assumed latest release.

The intake JSON supplies `kind`, `person` (local alias), `source_person` (native ID), `origin_local` (same declared origin for both files), and `source_sha256`. Human intake additionally requires `authorized_processing: true`, a nonempty `authorization_reference` and `native_cgm_semantics_reviewed: true`, backed by actual authorization/review. These fields record a review; setting them does not grant rights. Raw inputs, intake metadata and outputs must be outside the repository.

```sh
uv run --locked python -m experiments.m3 normalize \
  --input /secure/local/study-source.xml --intake /secure/local/intake.json \
  --output /secure/local/converted-attempt
```

This is a command template for a later authorized user, not an instruction to obtain data now. `status.json` retains completion or the original failure type/location; `observations.json` and `conversion.json` preserve consumed native-input, intake and output hashes, the native participant ID and local alias, and the producing code provenance. Freeze checks those identities against the private registry before fitting. Add the normalized file and conversion receipt to the private registry: each human descriptor additionally requires `conversion_file` and `conversion_sha256`. Keep the actual terms, dictionary and archive identities in the rights record. Supply declared analysis bounds from the reviewed source metadata, not from favorable score selection.

The human registry gate also requires six explicit reviews (`authorized_processing`, `derived_retention`, `release_verified`, `format_verified`, `identity_reviewed`, `availability_reviewed`), terms/dictionary/archive SHA-256 identities, and authorization, retention, availability-assumption and reserved-material references. It cannot verify legal validity or detect people hidden behind unknown aliases. No human record was acquired for this implementation. See the feasibility page for the concrete outstanding institutional steps and storage plan.

## Failures and evidence

The supervisor records state before initialization, uses a bounded child process and keeps completed newline checkpoints. SIGINT/SIGTERM/deadline retain interruption; unfinished hard-killed attempts remain visibly unsealed. A partial final JSON line is counted separately and rejected for successful runs. Failed or unattempted people remain in every planned denominator. Required nonnumeric, boolean, null and nonfinite signals, duplicate JSON keys, exponent overflow, changed input bytes and missing provenance are rejected.

Worker diagnostics retain exception types and stack locations without serializing arbitrary input-bearing exception messages. Diagnostic failure does not replace the original raised exception. Derived row-level forecasts and targets are still health data when inputs are human; the artifact format does not anonymize them. Keep human reports and source identities private and obey the actual agreement's retention limits. No command uploads them.

Reports can be reconstructed without the original observations or estimator installation, using the producing code/lock/protocol revision, saved coefficients, causal history audit, targets and statuses. Preserve these permitted derived artifacts as well as private source receipts. Public synthetic archives can reuse the existing tool:

```sh
uv run --locked python experiments/m0/archive.py \
  --source results/m3 --destination results/m3-archive/example
uv run --locked python experiments/m0/archive.py --destination results/m3-archive/example
```

Do not apply public CI upload or unrestricted archive policies to human data. Local preservation is not offsite backup, independent reproduction or a public release. M0/M1/M2/IV-001 historical evidence and the simglucose setuptools advisory remain unchanged.
