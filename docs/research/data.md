# Data and provenance

Data assessment starts in M0, alongside candidate-model reproduction. Personalization comes later, but the first model choices should already be informed by what relevant measurements can support.

Researchers obtain and manage their own appropriately authorized observations;
OpenT1D supplies intake, provenance and evaluation tools, not a patient
dataset. Invented public fixtures are labeled as software examples. See the
[tool-first decision](../decisions/0045-tool-first-research-platform.md).

## Choose data for the question

Record the target population, disease stage, observations, interventions and time resolution needed for the proposed claim. Assess whether the dataset actually contains those variables and whether missingness makes the question unanswerable.

The [research report](../research/project-design.md#9-data-strategy) reviews candidate sources including MetaboNet, JAEB, TrialNet and HPAP/PANC-DB. A listing in that report does not mean access has been granted or that redistribution is permitted.

The [M0 data-fit assessment](m0-assessment.md#data-fit) proposes a source-level DCLP3 audit first, records its meal-data limitation, and distinguishes it from later MetaboNet harmonization or OhioT1DM access. It is a documentation review, not an acquired or verified patient dataset.

## Required provenance

For each dataset or parameter asset, record its provider, source URL or accession, version, retrieval date, applicable terms, permitted uses and permitted outputs. Record selection rules, participant overlap, processing steps, variable definitions, units, time zone handling and quality flags.

Keep observations separate from inferred or imputed values. Missing insulin or carbohydrate records must not silently become zero. Distinguish a delivery command from measured delivery where the source allows it.

## Public and restricted materials

Use small synthetic fixtures or explicitly redistributable data for public examples and automated checks. Synthetic data must be labeled and its generation documented. It is useful for software verification but is not external biological validation.

Restricted inputs remain outside version control and outside public CI. The ignored `data/private/` and `data/raw/` paths are conveniences, not access controls. An ignore rule cannot remove a file already tracked by Git.

Contribute a permitted converter, manifest template and instructions for authorized users to obtain data from the original provider. Do not publish restricted raw records, derived individual-level outputs or identifying metadata without confirming permission. Small counts, hashes and filenames can also disclose information; choose public provenance fields deliberately.

## Evaluation design

Define development and evaluation partitions before fitting or tuning. Split at the participant or study level when needed, and check overlap between aggregated sources. A held-out time segment can answer a different question from a new participant or intervention study.

Preserve the data-processing version with each result. If access terms prevent full public reproduction, state exactly what is restricted and provide a public synthetic workflow to verify the mechanics. Do not claim the public example reproduces private scientific results.

The [M0 data card and crosswalk](m0-data-fit.md) records the completed public-documentation assessment, with native release verification and authorized access explicitly pending.

The current [M3 feasibility review](m3-data-feasibility.md) selects a conditional six-person OhioT1DM CGM-only forecast question and documents why existing physiological replay is unsupported. The [M3 tutorial](../m3-tutorial.md) supplies executable synthetic mechanics and an explicitly unverified native-release adapter; its human review of data-use rights is not a grant of access.
