# M5 synthetic visit-linkage preflight

The [OT-027/0.2 question](research/m5-cell-therapy-protocol.md) asks whether an
observed day-75 graft-function measure adds prediction of later reported
insulin burden. The [public CIT-07 screen](research/m5-cit07-feasibility.md)
identifies a plausible schedule, but no participant-level linkage or usable
cohort has been verified. This preflight rehearses the **join and coverage
rules** with invented identifiers and availability flags. It supplies a tool
and an example, not a dataset, source-specific converter or clinical result.

## Run the invented example

From the repository root:

```sh
uv sync --locked
uv run --locked python experiments/m5/release_preflight/run.py run \
  experiments/m5/release_preflight/intent-synthetic.json \
  experiments/m5/release_preflight/packet-synthetic.json \
  results/m5-synthetic-preflight
uv run --locked python experiments/m5/release_preflight/run.py reconstruct \
  results/m5-synthetic-preflight
```

The output directory must be new. It contains the normalized invented input,
report, source-code copy and SHA-256 manifest. Reconstruction verifies the
artifacts and recomputes the report using the matching current implementation.
`results/` is ignored by Git. The example has three invented people: two
structurally linked, one with a missing diary day, and one of the linked people
has an additional infusion between visits. These are fixture counts only.

## Normalized packet contract

`intent.json` must declare the exact `ot027-synthetic-intent/1` schema,
`synthetic` data kind, `invented` source and `days_since_first_infusion`
clock. The runner checks this **before opening the packet**. `packet.json`
uses the `ot027-synthetic-packet/1` schema and four tables:

| Table | Fields | Structural rule |
| --- | --- | --- |
| `participants` | `alias` | Unique invented `SYNnnn` key; every person remains in the report |
| `infusions` | `alias`, `day` | Exactly one day-zero first infusion per person; additional days remain visible |
| `mmtt` | `alias`, `visit_id`, `day`, `challenge`, `samples` | Exactly one MMTT at day 70–80 with observed C-peptide and glucose at minute 0 and 90; duplicated sample minutes fail |
| `insulin` | `alias`, `visit_id`, `day`, `semantics`, `diary_days`, `mean_summary_available`, `weight_available` | Exactly one visit at day 351–379; seven distinct consecutive diary days no later than the visit, with a mean summary; semantics must state reported daily total units |

Each record key must refer to a roster alias. The report retains failed
people, their issue codes, available weight status and infusions strictly
between the selected landmark and outcome. A seven-day mean summary without
seven diary-day coverage flags remains unverified. `weight_available` is
reported but does not gate a units/day outcome. A future release may only
use units/kg/day after verifying the actual contemporaneous weight and units.

The packet contains **availability flags and relative days, no glucose,
C-peptide, insulin or weight values**. It cannot verify assay units, limits,
actual values, collection dates, diary amounts or an arithmetic seven-day
mean. It rejects beta-score and other extra participant/visit fields so the
day-365 function result cannot silently become the day-75 predictor. It also
rejects a pump-delivery label substituted for self-reported insulin. The
window rules are the current *candidate* OT-027/0.2 schedule, not a verified
release schedule or a clinical endpoint definition.

The [CIT-07 public-dictionary crosswalk](research/m5-cit07-dictionary-crosswalk.md)
shows why normalization needs care: `Mean_Insulin.NumDaysInitial` is the
seven-day interval start, not the outcome visit day. Do not pass native rows
to this checker without a verified source-specific converter.

The [source-shaped CSV rehearsal](m5-native-rehearsal.md) now checks that
distinction on invented rows before producing any normalized candidate.

## Boundary for real studies

Do not put participant records into this packet, even after replacing names
with `SYNnnn`; the runner cannot prove that a file is invented. It has no
human-data authorization or native CIT-07 converter. An authorized release
needs a separate private, source-specific crosswalk and rights review before
record-level verification. That review must check source bytes, actual
infusion/visit IDs and dates, MMTT challenge and assay semantics, insulin
diary amounts and seven-day arithmetic, weight, missingness, treatment
context and person-disjoint allocation. Domain experts must review the
scientific interpretation before an empirical protocol is frozen. A clean
synthetic report establishes only that these structural checks can run.
