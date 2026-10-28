# Index and verify local experiment archives

The catalogue keeps local pointers to authoritative researcher archives. It reads task, protocol, model, configuration and recorded status metadata, preserves the complete requested roster and lets you filter it. Archive verification is a separate explicit operation. Source archives remain unchanged.

Use the recorded checkout with Python 3.12. The [task setup guide](task-setup.md) covers the explicit root tooling bootstrap and locked environments. The commands below use its `.venv/bin/python`. Catalogue reading and native reconstruction use the standard library; they do not import supplied models, run simulations or perform the separate P1 controller action replay.

## Declare archive pointers

Create a local request such as `inputs/catalogue.json`:

```json
{
  "schema": "opent1d.catalogue-request/1",
  "entries": [
    {
      "id": "primary",
      "task": "m4-compare",
      "archive": "../results/m4-comparison",
      "tags": ["primary", "synthetic"]
    },
    {
      "id": "repeat",
      "task": "m4-compare",
      "archive": "../results/m4-comparison-repeat",
      "tags": ["repeat", "synthetic"]
    }
  ]
}
```

The request has exactly `schema` and `entries`. It accepts one to 128 ordered entries with exactly `id`, `task`, `archive` and `tags`. IDs are unique, start with a lowercase letter and contain at most 64 lowercase letters, digits, underscores or hyphens. Each entry has at most 16 distinct nonempty tags of at most 128 characters. Relative archive paths resolve against the request file's directory. Symlink archive pointers and archive entries are refused.

The explicit task adapters are `p1-controller`, `m3-forecast`, `m3-compare`, `m4-secretion`, `m4-compare`, `m4-study`, `m4-study-secure`, `m5-prognosis` and `mmtt-sensitivity`. Retain the matching implementation checkout for native verification. For a [local campaign](local-campaigns.md), point to a native study under `sessions/session-000N/attempts/<cell>--rNNN/archive`; the campaign administration root is a different archive format.

The [maintained M4 study](m4-maintained-study.md) has its own task/protocol
identity. Historical and maintained executions cannot become same-experiment
repeats merely because their numeric curves agree. For an older archive whose
scientific reader requires a different checkout, use the explicit
[historical-reader route](historical-readers.md).

## Read metadata, then verify separately

Choose fresh output directories:

```sh
.venv/bin/python -B -S -m experiments.catalogue index \
  --config inputs/catalogue.json --output results/catalogue
.venv/bin/python -B -S -m experiments.catalogue list \
  --catalogue results/catalogue --task m4-compare --tag primary
.venv/bin/python -B -S -m experiments.catalogue verify \
  --catalogue results/catalogue --output results/catalogue-verified
```

Indexing reads JSON metadata and the complete regular-file byte inventory. A readable entry gets `metadata_status: metadata_read` and `verification.status: not_requested`. Recorded hash agreement has scope `recorded_hashes_only`: matching digests do not establish numerical or semantic validation. Missing, malformed or unsupported metadata stays in the requested roster with an explicit metadata error. Recorded-claim diagnostics remain separate.

Recorded claims use a fixed schema-specific path base and claim structure.
In particular, a maintained M4 reference seal is rooted at its native
`reference/` directory. Per-manifest diagnostics identify matched supported
claims, changed/missing bytes, malformed claims and unsupported schemas;
unknown schemas cannot produce a matched result. Aggregate agreement covers
supported recorded claims only and does not authenticate all archive bytes.
Digest diagnostics remain separate from readable metadata and authoritative
native reconstruction. [Decision 0063](decisions/0063-reliable-archive-library.md)
records this convention; original archives are never rewritten by these tools.

Verification invokes only the task's registered native reader, under root Python with `-S`, into fresh directories inside its own output. M5's existing reader verifies its saved reports in place without modifying them. Every source archive inventory is checked before and after reconstruction. `verified_reconstruction` means the native reader accepted saved evidence; `complete` remains a separate boolean. A successfully reconstructed failed or incomplete report stays failed or incomplete. For preserved failed M4 archives, explicitly add `--allow-failed`.

The output contains `request.json`, `catalogue.json`, `report.md` and a sealed `manifest.json`. Verification also retains native reconstruction outputs and logs. It refuses output directories that overlap a source archive or the earlier catalogue. Keep source archives available at their recorded paths; the catalogue preserves pointers rather than copying experiments.

Filters `--task`, `--protocol`, `--model`, `--status` and `--tag` can be combined. `list` reports the scope of stored verification receipts; it does not repeat native validation. The catalogue does not establish training rights, empirical accuracy, independent user acceptance or biological validity.

## Check conservative repeat compatibility

```sh
.venv/bin/python -B -S -m experiments.catalogue compare \
  --catalogue results/catalogue-verified --left primary --right repeat
```

This command checks eligibility for complete repetitions of the same experiment. Both entries must have successful native reconstruction and complete evidence. It explicitly reruns their native readers and requires matching task, protocol, configuration, full input/scenario/person roster, frozen model source/settings/state identities and scientific implementation/runtime conditions. M4 signatures include the saved shared control trajectories and exact grid. Missing or incompatible conditions produce explicit reasons and `eligible: false`.

Repeat conditions include the saved Python version, platform, native parameter table and source digests, and native/observer package versions. M4 native identity excludes only the two installed file locations; their source digests and all other identity fields remain required, while the original paths stay in the authoritative archive. `metadata.repeat_condition_coverage` states whether the archive records all required conditions. Historical secretion and prognostic archives without a saved platform remain readable and reconstructable, but cannot establish repeat eligibility. Missing runtime evidence in a complete new M4 study or source comparison is refused as incomplete metadata.

The command returns no new scientific metrics or cross-task score. Different methods belong in the supported [M3 candidate comparison](m3-candidate-comparison.md) or [M4 source comparison](m4-source-comparison.md), which own their paired support and interpretation. A source archive altered since indexing cannot gain eligibility, even when its manifest has been rewritten to match the changed bytes. Re-index a deliberately new archive as a new experiment.

This is a bounded local catalogue. It adds no arbitrary plugin execution, global experiment store or automatic method ranking.
