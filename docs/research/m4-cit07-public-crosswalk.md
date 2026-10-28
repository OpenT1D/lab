# BC-015-P2 — CIT-07 public variable crosswalk

This is a **public dictionary audit**, not a participant-level join. It follows
the [BC-015-P1 readiness preflight](m4-measurement-readiness.md) without changing
the [BC-004 human-measurement contract](m4-paired-protocol.md) or any M4 model.
On 25 September 2026 we inspected eight individually listed public variable
dictionaries for the [NIDDK CIT-07/08 Version 2 release](https://test.repository.niddk.nih.gov/study/92),
DOI [10.58020/qx8b-gk69](https://doi.org/10.58020/qx8b-gk69). The catalogue
says participant data are **available for request**. Neither that statement
nor an accessible dictionary grants OpenT1D access to participant records.
No records, request or external review were involved.

## Prespecified boundary and source identity

The [source manifest](../../experiments/m4/measurement_readiness/public-dictionaries.json)
names only public document URLs, exact SHA-256 hashes, table identities and
expected fields. The [reader](../../experiments/m4/measurement_readiness/public_crosswalk.py)
uses the Python standard library to inspect the first worksheet *after* its
bytes match the manifest. It writes a field-level report and never opens a
participant dataset. The source XLSX files remain in ignored `results/`; they
are not redistributed. This tests the released **schema description**, not
the number or quality of observed samples. The official test-domain download
endpoints were accessible; the production document endpoints were not directly
retrievable in this session. The test mirror's identity and bytes are pinned,
but production-release equivalence remains unverified.

| Public dictionary | Fields relevant to this question | What the dictionary establishes |
| --- | --- | --- |
| [FSIGT Raw](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67507) | `ACCESSION`, `StudyID`, `NumDaysInitial`, the time field (with a trailing ASCII space in its name), `glu` (mg/dL), `ins_tosoh` (Tosoh µU/mL) | Dynamic glucose and insulin columns; no C-peptide column |
| [C-peptide/glucose/creatinine](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67500) | `ACCESSION`, `NumDaysInitial`, fasting and 60/90-minute C-peptide and glucose; `Creatinine` | Sparse fixed challenge points, without an FSIGT sample-time or insulin column |
| [Rudbeck clinical](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67544) | `ACCESSION`, `NumDaysInitial`, `Sample` labels and `C_Peptid` (pmol/L) | Some C-peptide sample labels, but no glucose, insulin or documented FSIGT event identity |
| [Insulin use](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67518) and [mean insulin](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67530) | `Insulin` in units/day; seven-day `Mean_Insulin` | Treatment summaries, not minute-resolved FSIGT administration |
| [GFR](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67510) and [weight](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67553) | `ACCESSION`, `NumDaysInitial`, GFR or kg weight | Potential covariate fields, without verified same-test coverage or timing |
| [Drug dose](https://test.repository.niddk.nih.gov/api/entity/v1/study/documents/download/file/67504) | `Drug`, transplant-relative start/stop days, `Dose`, `Unit` | Regimen metadata; its enumerated drug list does not supply an FSIGT insulin-injection record |

`ACCESSION` is described as a masked subject ID and `NumDaysInitial` as days
since first transplant in several dictionaries. Those common names permit a
*candidate subject/day linkage*, not proof of the same visit, challenge or
actual collection clock. No dictionary examined supplies a validated
cross-dataset FSIGT event identifier. The [CIT-07 protocol v8, §§9.1.2.5–8,
pp. 80–82](https://test.repository.niddk.nih.gov/media/studies/cit-07/Protocol.pdf)
defines MMTT glucose/C-peptide at fasting, 60 and 90 minutes and posttransplant
FSIGT C-peptide at baseline and through 10 minutes; FSIGT glucose/insulin
continue through 180 minutes, with protocol insulin injection at 20 minutes.
Protocol timing is not evidence of the actual injection and samples for each
released visit. The Rudbeck `Sample` labels cannot be reassigned to FSIGT by
matching minute numbers.

The C-peptide dictionary labels `Creatinine` as “Fasting Creatinine (ng/mL)”,
whereas the protocol's C-peptide/glucose/creatinine ratio uses creatinine in
mg/dL. Treat that as an **unresolved source-unit discrepancy**, not a
conversion instruction. Assay matrix, quantification limits, precision,
insulin cross-reactivity and actual treatment timing are not established by
these eight dictionaries.

## Reproduction and verdict

Download only the eight public dictionary documents named in the manifest to
an ignored local directory using their listed URLs and filenames. Then run:

```sh
python3 -m experiments.m4.measurement_readiness.public_crosswalk \
  --source-dir results/m4-measurement-readiness/public-dictionaries \
  --output results/m4-measurement-readiness/cit07-public-crosswalk-next.json
python3 -m experiments.m4.measurement_readiness.run \
  --candidate experiments/m4/measurement_readiness/candidate-cit07-dictionaries.json \
  --output results/m4-measurement-readiness/cit07-dictionaries-next
```

Use new output paths. The completed [execution record](../../experiments/m4/measurement_readiness/execution-public-crosswalk.json)
identifies the local reports. The second command reuses the frozen BC-015-P1
eight-item preflight with more precise source links: **2 supported, 5
unverified, 1 contradicted**. The dictionaries narrow *which* fields are
missing but do not close the core late-C-peptide contradiction or make a
paired human packet ready for design review. The code's
`verified_same_challenge_gic_crosswalk=false` is a conservative source verdict,
not evidence that no suitable measurements exist anywhere. No parameter was
fitted and no held-out human comparison was run.

## Next evidence gate

The [unsent review brief](m4-collaboration-brief.md) now asks for a versioned
release-level crosswalk linking subject, exact challenge/visit, specimen and
actual collection time; confirmation of whether any **late FSIGT C-peptide**
series exists outside the core schedule; actual FSIGT insulin-input and assay
metadata; correction of the creatinine unit; and allowed use/derived-output
terms. A laboratory specialist and secretion/kinetic modeller must assess the
assay and model fit, while a statistician must determine whether participants
can be reserved before fitting. Until those facts and authorization exist,
OT-026 remains an exploratory synthetic coupling, and OT-027 gains no therapy
evidence from this crosswalk.
