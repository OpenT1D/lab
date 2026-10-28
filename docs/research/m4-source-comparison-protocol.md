# M4-COMPARISON/1 — Frozen multiple-source comparison protocol

**Specified:** 3 October 2026, before implementation and new comparison runs.
This protocol implements the bounded question in
[OT-031](roadmap-history-2026-10-28.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources)
under [decision 0057](../decisions/0057-m4-source-comparison.md).
The [machine protocol](../../experiments/m4/comparison/protocol.json) freezes
the analysis and inherited protocol/runtime file identities. Execution and
observed outcomes belong in a separate verification record.

## Question and scope

How do several frozen causal secretion responses differ in modeled glucose,
insulin and C-peptide under identical fixed synthetic conditions? The
consumer is a researcher comparing trusted local sources compatible with
the existing [single-source workflow](../m4-researcher-workflow.md).
This is a software and numerical comparison, without human observations,
calibration, source tuning, biological ranking or treatment inference.

## Configuration and identities

Use schema `m4-source-comparison-config/1` with exactly four keys:
`schema`, `sources`, `timeout_seconds` and `source_timeout_seconds`.
`sources` is an ordered list of two to eight entries, each with exactly `id`,
`model` and `declaration`. IDs must be unique safe directory names. Relative
paths resolve against the configuration directory. Every model and
declaration must be a regular file and satisfy unchanged `M4-CAUSAL/1`
intake, including the model source hash, units, dependencies, ancestry,
rights basis and flat numeric parameters. Metadata validation must not
import or execute a supplied source.

`timeout_seconds` is the inherited per-stage budget, an integer from 1 to
1800, and also bounds fresh reference generation. `source_timeout_seconds`
is an integer from 1 to 10800 bounding the entire supervised child workflow.
The supplied two-source example uses 600 and 3600 seconds respectively.
These are worker budgets, not a promise about total coordinator duration.

Before dispatch, archive the complete ordered configuration, source and
declaration bytes and hashes, parameters, comparison protocol, inherited
protocols, numerical projects/locks and coordinator source inventory.
Reject changed identities or unsupported settings before supplied source
execution. Source names, versions and declared ancestry/rights remain
visible in the combined report; a valid hash does not certify those claims.

## Fixed conditions and process ownership

Reuse unchanged `M4-RESEARCHER/1`, `M4-CAUSAL/1`, `BC-008/2` and BC-010's
frozen numerical/observation settings. Their exact file identities, and
the two numerical lock/project identities, are pinned in the machine
protocol. No configuration field overrides these conditions:

- Scenarios in order: `fasting`, then `gastric_load_30g`; the latter starts
  with 30000 mg in the gastric solid compartment at time zero.
- The pinned adult#001 native profile; 0 to 240 elapsed minutes inclusive,
  sampled every 0.25 minutes, with 961 samples in each trajectory.
- The inherited 25% synthetic SC basal replacement, matched initial plasma
  insulin, native/basal initialization and fixed external SC schedule.
- The unchanged one-state callback and units; same-stage native glucose and
  glucose derivative; host-owned `Z(0)=Sb`, portal state and liver arrival.
- The three tracks `candidate`, `host_constant_basal` and `bc008_reference`.
- Passive C-peptide input from total pancreatic appearance `Spo` in
  `pmol/(kg min)`, with inherited equimolar assumption, initial inventories,
  rate constants, volume and archived piecewise-linear source interpolation.

The gastric load is a synthetic initial condition, not an announced meal
or bolus. No source may add another basal input, portal state, hidden mutable
state, future glucose or C-peptide feedback. C-peptide applies no SC input,
hepatic extraction, insulin transit, molecular conversion or second
body-weight division. The callback remains trusted local code; archived
execution cannot independently prove its purity or biological suitability.

## Common reference and execution

Create one complete BC-008 reference before source dispatch, or accept one
supplied through `--reference` only after unchanged reference reconstruction
passes and all required source/reused/runtime snapshots match the fixed
checkout. Refuse incompatible references before creating output. Every
source receives this same verified reference archive. Its identity must
remain unchanged across the entire comparison.

Execute the ordered source roster sequentially in separate supervised child
process groups through unchanged `M4-RESEARCHER/1`. Each source retains eight
inherited causal cases, eight fresh-process causal repeats, six observer
cases and six fresh-process observer repeats. Preserve the same numerical
criteria and all archived diagnostics; no threshold is chosen from curves.
Run ordinary subsequent sources after an individual source failure. On
global interruption, terminate and reap the active group, retain the
interrupted attempt and mark later sources as `not_attempted`.

## Acceptance, descriptive contrasts and failure accounting

The full planned denominator is every frozen source times both scenarios.
Keep each source and scenario visible as completed, failed, interrupted or
unattempted, with the child's stage/error and numerical checks. A source is
accepted only if its entire causal/observer/repeat workflow is complete and
passes. Partial prefixes and individually completed scenarios cannot be
promoted to accepted comparison support.

Verify common protocol, native profile, initial/basal/SC conventions,
runtime identities and the complete sample grid. The saved common BC-008
reference and host constant-basal glucose/insulin/C-peptide trajectories
must agree exactly across accepted children. Disagreement makes the
comparison fail and produces null direct contrasts with its reason.
It must not silently create different comparison groups.

For every unordered source pair, use roster order to define left minus
right. Compute separate descriptive glucose (`mg/dL`), plasma insulin
(`pmol/L`) and central C-peptide (`pmol/L`) contrasts for each scenario only
when both complete sources are accepted and the common-condition/control
checks pass. Use all 961 exact saved times; do not shorten, resample, drop
samples or interpolate across unmatched grids. For values `a_i`, `b_i`,
times `t_i`, differences `d_i=a_i-b_i` and duration `T=240 min`, report:

- Signed AUC difference: `sum((d_i+d_(i+1))/2 * (t_(i+1)-t_i))`, in the
  trajectory unit times minutes.
- Signed time-mean difference: signed AUC difference divided by `T`.
- Maximum absolute pointwise difference: `max(abs(d_i))`, in the trajectory
  unit. This is descriptive trajectory separation, not an accuracy score.

The pairwise result is null with an explicit reason if either full source
is ineligible or identity/condition/grid/control checks disagree. Preserve
all other accepted pairwise descriptions in the report when a separate
source fails; a failed complete roster remains failed overall. Do not
select a winner, pool scenarios into a ranking or infer superiority from
lower glucose, insulin or C-peptide. Retain each child's original reference
and constant-basal diagnostics alongside the new direct contrasts.

## Archive, reconstruction and verification

Refuse existing or overlapping output directories. Preserve source
snapshots, configuration, protocol and runtime inventories, common reference,
complete child archives, command/log/exit evidence and full planned roster.
The coordinator owns its own provenance outside source-hashed historical
packages; old single-source readers and commands stay unchanged.

Reconstruct `report.json`, `report.md` and `figure.svg` from saved artifacts
using only the standard library, without importing a supplied source,
NumPy, SciPy or a simulator. Verification checks the child archives through
their unchanged readers and recomputes identity, coverage, controls and
contrasts. A reader is not independent reproduction of arbitrary callback
implementation. Failure reconstruction needs an explicit failed-archive
option and must retain missing-evidence/null-result reasons.

Acceptance evidence must cover both existing source structures, reference
and control agreement, a rejected or failing source, shortened/mismatched
evidence rejection, deadline/interruption ownership, exact fresh-process
repeats and byte-identical simulator-free reconstruction. Validate the
common entry after the native task passes. Run locked repository checks
and appropriate numerical checks; record commands and limitations actually
observed in the separate execution record.

## Evidence limits

This increment does not introduce human observations, fit secretion
parameters, reproduce the full ultradian engine, determine insulin need,
identify cell mass or establish treatment benefit. Existing source
sampling/coarsening limits remain explicit. Independent researcher use,
population calibration, paired observations and domain review remain open.
