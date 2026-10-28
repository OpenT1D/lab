# BC-015-P1 — Paired human-measurement readiness

This is a source-metadata feasibility assessment after [BC-014 synthetic
coverage](m4-coverage-results.md). The [decision](../decisions/0030-metadata-before-human-assessment.md)
keeps empirical human evaluation behind separate rights, release and
scientific-review gates. The [BC-004 conditional measurement contract](m4-paired-protocol.md)
remains the basis for the requested variables. No participant record was
obtained, opened or scored for BC-015-P1.

The follow-on [BC-015-P2 public-dictionary crosswalk](m4-cit07-public-crosswalk.md)
inspects exact variable fields and preserves this original assessment.

## Question and executable boundary

Does a **specific released dataset** document enough visit-linked laboratory
glucose, insulin and C-peptide observations to design an independent test of
the existing secretion/kinetic model? The metadata preflight checks eight
requirements with explicit minimum evidence levels. It admits only fixed
source-level fields and public HTTPS document links. It rejects participant
fields, unrecognized measurement values, URL query tokens and symlink input.
Its strongest output is "metadata packet for design review"; the
`human_execution_authorized` flag is always false. It neither interprets
clinical measurements nor judges biological model validity.

The [frozen machine protocol](../../experiments/m4/measurement_readiness/protocol.json),
[candidate record](../../experiments/m4/measurement_readiness/candidate-cit07.json)
and [runner](../../experiments/m4/measurement_readiness/run.py) are separate
from BC-014's model and assessment draws. A requirement is supported only
when its finding is supported and its source tier meets the declared minimum.
Contradiction is retained even if other evidence is incomplete. Counts never
turn a catalogue entry into access permission.

## CIT-07/08 source assessment

On 25 September 2026 the indexed [NIDDK CIT-07/08 Version 2
catalogue](https://repository.niddk.nih.gov/study/92) described an **FSIGT
Raw** dataset with glucose and insulin, a separate
**C-peptide/glucose/creatinine** dataset, and an additional C-peptide clinical
dataset. It describes the resource as *available for request*, not already
provided to OpenT1D. The official [test-domain rendering of that
catalogue](https://test.repository.niddk.nih.gov/study/92) exposed those
descriptions; direct retrieval of the production page and roadmap document
returned HTTP 403 in this check. The test-domain page is useful public
metadata, not a verified production data dictionary, patient release or
license grant. The [NIDDK requestor FAQ](https://test.repository.niddk.nih.gov/faq)
describes controlled access and data-use conditions. No request was submitted.

The previously inspected [CIT-07 protocol
v8](https://repository.niddk.nih.gov/public/study_document/Documentation/CIT-07_Protocol_Version_8.0_20Aug12.pdf),
pp. 81–82, schedules C-peptide in its core FSIGT only through 10 minutes,
while glucose/insulin continue later and exogenous insulin is introduced.
This contradicts a late C-peptide series **for that core FSIGT schedule**.
It does not prove that no other CIT-07 substudy or unlisted release contains
late samples. The separate Miami oral-test schedule in the
[measurement inventory](m4-cpeptide-measurements.md) would require another
secretion question, not a relabelled IV glucose experiment.

| Requirement | CIT-07 core FSIGT finding | What remains necessary |
| --- | --- | --- |
| Same-visit dynamic G/I/C-peptide | Unverified | Release dictionary and visit/time linkage for all three analytes |
| Early and late C-peptide | Contradicted by core protocol | Evidence of an additional suitable late series, if any |
| IV stimulus route, dose and clock | Supported by protocol | Confirm implementation and actual visit records |
| Exogenous-insulin timing | Unverified | Recorded per-visit input, not schedule alone |
| Assay units, matrix, limits and precision | Unverified | Full laboratory dictionary, censoring and cross-reactivity |
| Renal and body-mass context | Unverified | Linkable time-specific release fields |
| Population and graft route | Supported by protocol | Reviewer-defined analysis population |
| Participant-disjoint allocation | Unverified | Actual coverage and visit/participant linkage before split |

The completed [local report](../../experiments/m4/measurement_readiness/execution.json)
has **2 supported, 5 unverified and 1 contradicted** requirement. Therefore
the core CIT-07 FSIGT metadata packet is **not ready for model-design review**
under the declared contract. This is a source/schedule verdict, not an
analysis of the 48 study participants or a claim that appropriate data do
not exist elsewhere.

## Run and verification

From the isolated worktree root:

```sh
uv sync --locked
uv run --locked python -m experiments.m4.measurement_readiness.run \
  --candidate experiments/m4/measurement_readiness/candidate-cit07.json \
  --output results/m4-measurement-readiness/cit07-02
```

Use a new output path; the completed local audit is
`results/m4-measurement-readiness/cit07-01`. The archive snapshots the
candidate, frozen protocol, runner and report with SHA-256 hashes. A
standard-library-only reconstruction matches the saved report byte for
byte. Five focused tests cover the CIT-07 gap verdict, a synthetic complete
packet that still cannot authorize human execution, forbidden patient
fields, token-bearing URLs, symlinks and tampering after rehashing.
The final `uv run --locked python scripts/check.py` passed 632 repository
tests, lint and the strict documentation build.

## Review and next gate

The [unsent collaboration brief](m4-collaboration-brief.md) now asks a
custodian and assay/kinetic reviewers for a **versioned variable and visit
crosswalk beyond the public dictionary fields, actual C-peptide times,
assay/renal and treatment fields, and
the exact permitted research and derived-output terms. It asks whether an
independent participant or study allocation is feasible. It does not ask
for a data transfer. Once separately authorized metadata and scientific
review answer those questions, write a new population-specific empirical
protocol and freeze the held-out allocation before fitting. CIT-07 is a
transplant cohort; residual endogenous T1D secretion needs its own source
assessment. OT-026 and M4 remain incomplete.
