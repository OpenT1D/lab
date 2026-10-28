# 0030 — Source metadata before human beta-cell assessment

Status: accepted locally on 25 September 2026.

## Context

BC-014 assessed the pointwise gain profile only on synthetic observations.
BC-004 already requires a permitted, visit-linked glucose/insulin/C-peptide
release, assay and treatment details, and an independent allocation before
empirical inference. The NIDDK CIT-07 catalogue describes dynamic FSIGT
glucose/insulin and separate C-peptide datasets, but a catalogue listing
does not verify a joined late C-peptide series or grant access.

## Decision

BC-015-P1 tests a strict **source-metadata** packet before any human import.
It may identify documented, unverified and contradicted requirements. Even a
complete packet is only suitable for scientific design review; it never
authorizes human execution. Keep actual release verification, permission,
domain review, participant allocation and a frozen empirical protocol as
separate gates. Do not adapt BC-014's synthetic noise or cutoff to a human
cohort without new evidence.

## Alternatives and consequences

A direct patient-data adapter would have no verified input contract or
authorization. A prose checklist alone would not expose incomplete evidence
consistently. This bounded preflight checks the evidence accounting and
archive, while deliberately calculating no biological output. Revisit the
contract only after actual permitted release metadata and expert review
establish a defensible study-specific question.
