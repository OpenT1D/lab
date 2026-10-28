# M5 source-shaped CSV rehearsal

The [CIT-07 public-dictionary crosswalk](research/m5-cit07-dictionary-crosswalk.md)
identifies a specific conversion risk: `NumDaysInitial` is a visit-relative
day in the C-peptide and daily insulin tables, but the **start of a seven-day
interval** in the mean insulin table. This tool exercises those distinct
roles with five invented CSV tables whose selected headers match the public
dictionaries. It extends the earlier [normalized synthetic
preflight](m5-release-preflight.md) toward a source-specific converter. It
does not accept human data or claim that the real CIT-07 release has been
verified.

## Run the invented tables

From the repository root, choose new output paths:

```sh
uv sync --locked
uv run --locked python -m experiments.m5.native_rehearsal.fixture \
  results/m5-native-shaped-synthetic
uv run --locked python -m experiments.m5.native_rehearsal.run \
  --intent experiments/m5/native_rehearsal/intent-synthetic.json \
  --source-dir results/m5-native-shaped-synthetic \
  --output results/m5-native-shaped-synthetic-report.json
```

The [checked-in example report](../experiments/m5/native_rehearsal/report-synthetic.json)
has three invented `SYNnnn` people. Two pass the **candidate structural**
checks, one lacks a daily insulin row, and one of the passing cases has a
second transplant on day 150. These fixture counts say nothing about the
number of usable CIT-07 participants. The report records source file and
public-dictionary-manifest hashes so the example can be repeated; it
contains no human identifiers or clinical observations.

## What the checker does

The five input filenames are `patient_status.csv`, `ieq_infused.csv`,
`cpeptide.csv`, `insulin.csv` and `mean_insulin.csv`. These names are a tool
convention, not a claim about native archive filenames. The checker uses
only the selected columns listed in the [public dictionary
manifest](../experiments/m5/source_crosswalk/public-dictionaries.json):

- It starts with every `PatientStatus` person, assigns first-infusion day
  zero, checks `NumTX` against the second/third-infusion days, and compares
  those transplant orders with `ShareIEQ_Infused.TX`.
- It finds a **candidate** 70–80-day C-peptide/glucose row with fasting and
  90-minute values. The dictionary alone does not establish the actual MMTT
  challenge identity or assay/censoring policy.
- It treats `Mean_Insulin.NumDaysInitial` and `EndDay` as an interval, then
  looks for exactly one reported daily insulin row on each of its seven
  inclusive days. It does not use the interval start as the one-year visit
  day. It retains missing or ambiguous intervals and all roster cases.
- It reports any second or third infusion between the candidate function
  row and mean-interval end. This is intervening treatment, not a claim
  about a first-graft effect.

The report deliberately leaves `one_year_visit_linkage_verified`,
`mmtt_challenge_identity_verified`, `cit07_cit08_partition_verified` and
`diary_semantics_and_arithmetic_verified` false. The public dictionaries
do not decode the visit indicators or establish diary provenance and
rounding rules. A person's `candidate_structure_complete: true` therefore
does **not** mean that person is eligible for a prognostic analysis. The
runner reads the intent first and rejects any non-synthetic kind before
opening CSV files. Replacing participant names with `SYNnnn` does not turn
real health records into an invented fixture; do not pass a real release to
this tool.

## Human-release handoff

The [OT-027 data contract](research/m5-cell-therapy-data.md) and
[source crosswalk](research/m5-cit07-dictionary-crosswalk.md) list the
remaining gates. An authorized private intake must bind exact release
bytes and permitted use, verify native headers and study partitions,
decode the initial/final-visit indicators, establish true challenge and
visit identities, check assay and diary units and missingness, recompute
seven-day means with a reviewed rounding rule, and keep every person and
failure in a private report. Independent transplant, assay and statistical
review must precede an empirical protocol freeze. No model fit or treatment
evaluation is part of this rehearsal.
