# OT-027-P3 — CIT-07 public-dictionary crosswalk

**Reviewed 25 September 2026.** This is a source-pinned inspection of five
public dictionaries linked from the official [CIT-07/08 Version 2
catalogue](https://test.repository.niddk.nih.gov/study/92). The
[manifest](../../experiments/m5/source_crosswalk/public-dictionaries.json)
records their document URLs and SHA-256 hashes; the
[report](../../experiments/m5/source_crosswalk/report-public-dictionaries.json)
records the exact labels checked. No participant table, request-only dataset,
access grant or expert endorsement was used. The earlier [public-source
assessment](m5-cit07-feasibility.md) and [OT-027/0.2 protocol](m5-cell-therapy-protocol.md)
remain the question and schedule context.

## Source field roles

| Public dictionary | Verified fields and role | Boundary |
| --- | --- | --- |
| [Patient Status](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67533) | `ACCESSION` is a masked subject key; `NumTX` is transplant count; `Numdays2ndTX` and `Numdays3rdTX` are days since first transplant for later infusions | Relative repeat-infusion timing is described, but actual completeness and dates are unverified |
| [IEQ Infused](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67517) | `ACCESSION`, `TX` transplant order and `PostTransplantIEQ` quantity | Its nine listed variables do not include an infusion day/date; joining order to Patient Status is a candidate mapping only |
| [C-peptide/glucose/creatinine](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67500) | `ACCESSION`, `NumDaysInitial` days from first transplant, fasting and 90-minute C-peptide/glucose fields, initial/final-visit indicators | Same-row analyte fields are documented, but actual MMTT identity, assay/censoring and eligible-person coverage are not verified |
| [Daily Insulin](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67518) | `ACCESSION`, `NumDaysInitial` days from first transplant, `Insulin` use in units/day | Actual seven-day presence, diary provenance, duplicate handling and observed doses require the release |
| [Mean Insulin](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67530) | `ACCESSION`, `NumDaysInitial` **start of the seven-day calculation interval**, `EndDay` its end, `Mean_Insulin` units/day, `Weight` kg and `Ins_kg` units/kg/day | The start field is **not a visit day**; its relationship to the one-year visit and daily records is unverified |

The shared key name supports a proposed person join. It does **not** prove
that the MMTT row, seven daily doses, mean summary, weight and infusion
events belong to the same eligible visit. `pstintvst` and `pstfinvst` occur
in the MMTT, daily insulin and mean insulin dictionaries, but their labels
only say “time point indicator” based on initial or final transplant; the
inspected dictionaries do not decode their values. `Flag08` appears in the
MMTT and daily insulin dictionaries but not in the three other inspected
dictionaries, so study-subgroup handling also needs a release-level rule.

**Clock correction:** `NumDaysInitial` must be interpreted per table. In
the MMTT and daily insulin tables it is a day since first transplant. In
the mean insulin table it is the *start* of the summary interval. An exact
equality join from a day-365 MMTT row to `Mean_Insulin.NumDaysInitial`
would therefore pair unlike events. `EndDay` and visit indicators are
candidate aids, not a verified visit-date crosswalk. This source-specific
finding does not change the proposed first-infusion origin or day-75/day-365
candidate windows; it prevents a false implementation of them.

## Record-stage checks still required

For one authorized, versioned native release, a private source converter
must first verify the `ACCESSION` roster and CIT-07/CIT-08 partition, the
first and later infusion days, and how `TX` order maps to them. It must then
identify actual 70–80-day MMTT rows and assay-qualified fasting/90-minute
measurements; identify 351–379-day **first-infusion visits** independently
of the mean interval start; and join seven distinct, consecutive reported
daily insulin entries to each mean interval. Verify the arithmetic, units,
contemporaneous weight, duplicates and missingness. Report every person
and all intervening infusions before any split or model fit. The
[synthetic preflight](../m5-release-preflight.md) rehearses these structural
checks after normalization. The [source-shaped CSV rehearsal](../m5-native-rehearsal.md)
exercises the five-table mapping with invented rows; neither tool is a
verified human-release converter.

The subsequent [public form and laboratory audit](m5-cit07-form-lab-audit.md)
identifies visit 15 and Y1 as separate scheduled 365-day clocks and shows
that routine MMTT collection uses a 90-minute sample while 60-minute
sampling is conditional. It does not decode the released visit indicators
or prove an actual same-visit join.

The catalogue still marks the full Version 2 data package as **available
for request**. It links a separate [CIT-07 public-data
page](https://www.itntrialshare.org/project/CIT/CIT-07PUBLIC/begin.view?pageId=study.DATA_ANALYSIS)
for material associated with the primary publication only. That link did
not yield an inspectable data packet during this review, and its scope and
rights have not been established as equivalent to Version 2. No
participant-level feasibility count, empirical protocol freeze, prognostic
model or treatment claim follows from these dictionaries.

## Reproduce the dictionary assessment

Download only the five public XLSX documents named in the manifest into an
ignored or temporary directory under the listed filenames. Then run:

```sh
uv run --locked python -m experiments.m5.source_crosswalk.run \
  --source-dir results/m5-public-dictionaries \
  --output results/m5-public-crosswalk-next.json
```

The runner checks source hashes, table and variable names, and the exact
field labels behind the clock correction. It reuses the M4 public-XLSX
reader. The committed report was produced from those five downloaded
documents with no participant values. A changed source document fails
closed until it is separately reviewed and recorded.
