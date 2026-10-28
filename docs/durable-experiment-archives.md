# Preserve and restore experiment evidence

OT-041 adds a directory package for an existing maintained M4 study or campaign.
Its [decision](decisions/0061-durable-experiment-archives.md) and
[versioned contract](../experiments/durable_archives/contract.json) define the
scope. The CLI and local GUI are implemented and internally verified locally.
The [acceptance record](research/durable-archive-verification.md) binds native
execution, byte preservation, relocated reconstruction and browser checks.
Independent researcher use, historical artifact recovery and biological results
remain separate from this software verification.

A report download and an archive-library pointer are useful for reading, but do
not preserve the full original experiment. Keep the package in independently
retained storage outside disposable implementation checkouts. A single local
copy is not a redundant backup. Choose and maintain the storage location
explicitly; this tool does not upload evidence to a cloud service.

## What the package preserves

`opent1d.durable-archive/1` contains four parts:

| Part | Meaning |
| --- | --- |
| `archive/` | Every original native file and empty directory, including frozen inputs, failures, interrupted attempts, session history, logs and reports |
| `reader/` | All tracked bytes from the explicitly trusted clean reader checkout at its full Git revision; preserved as data, never executed automatically |
| `evidence/` | The fixed authoritative reader's export reconstruction receipt, log and reconstructed outputs |
| `manifest.json` | Exact file/directory inventory, sizes, SHA-256 identities, task, reader identity and recorded reconstruction/completeness |

The explicit task whitelist contains `m4-study-secure`, `maintained-campaign`,
`m3-forecast` and `m3-compare`. OT-042 extends OT-041 through
[decision 0062](decisions/0062-synthetic-m3-gui.md), preserving package /1 and
M4 readers. Its [verification record](research/m3-gui-verification.md) binds
actual M3 CLI/browser/relocation and unsealed-retention checks. The campaign task
selects `experiments.maintained_campaigns`, not the historical campaign module.
Native archive bytes and saved absolute provenance paths are not rewritten.
A reconstructible failed or incomplete archive can be exported; unsuccessful
attempts remain in its original roster. Unsealed or incompatible top-level
evidence that the fixed reader refuses is not relabeled as a verified package.
Keep such original forensic evidence separately. The [M3 GUI](gui-m3.md)
provides bounded raw retention to the explicit store, copying the available
archive, prepared synthetic configuration and provenance. This separate
`opent1d.m3-forensic-retention/1` directory has no verified-package or
reconstruction claim and is not accepted as a durable package.

## Export an existing archive

The developer route below uses Python 3.12 and an explicitly trusted checkout.
Local execution is verified on macOS. OT-058 adds native Windows file/process
primitives and verified installed readers through the
[Windows installation candidate](windows-installation.md); actual Windows
execution and installation acceptance remain open. Linux execution also remains
unverified. From a developer checkout, install tooling with `uv sync --locked`.
The reader checkout must be explicitly trusted, clean and at the full recorded
Git revision. Working tracked bytes must match the Git objects, including files
that an index flag could hide from a normal status display. Ignored numerical
environments are not copied or used for saved-evidence reconstruction.

Replace the placeholders below with your actual retained storage, archive and
trusted reader checkout. The output directory must not exist.

```sh
archive_store=/absolute/path/to/independently-retained-archives
reader_checkout=/absolute/path/to/trusted-clean-checkout
reader_revision=FULL_40_CHARACTER_GIT_REVISION
.venv/bin/python -B -E -s -S -m experiments.durable_archives export \
  --task m4-study-secure --archive /absolute/path/to/native-study \
  --checkout "$reader_checkout" --revision "$reader_revision" \
  --output "$archive_store/exported-study"
```

For a maintained campaign, use `--task maintained-campaign` and the complete
native campaign root. M3 export uses `--task m3-forecast` or `--task m3-compare`
and its complete native study root. The fixed forecast reader uses `report
--study`; comparison uses `reconstruct --study`, without an M4 `--allow-failed`
argument. Existing original top-level JSON/Markdown must match authoritative
evidence byte for byte; missing reports are allowed only if the sealed native
reader succeeds. The exporter runs only the fixed saved-evidence reader
with failed coverage allowed, copies all bytes with bounded streaming reads,
and checks that the original archive and trusted reader remain unchanged.
Fresh staging is published without overwriting an existing destination.
Export and restore destinations remain outside the reader checkout. Package
and native-source overlap is refused. Fresh reconstruction output may use the
checkout's Git-ignored `results/` subtree; tracked reader bytes must still remain
unchanged before and after the operation.

The manifest itself is bounded to 8 MiB; a package allows at most 50,000 files,
100,000 entries, 256 MiB per file and 2 GiB total. Links, special files,
noncanonical paths and case/normalization aliases are refused. Package work is
bounded to 900 seconds. The default reader deadline is 120 seconds;
`--timeout-seconds` accepts 1–1800 seconds, with the effective deadline capped
by the remaining package-operation budget. Owned cleanup can follow the deadline.

## Verify bytes, restore and reconstruct

An integrity check reads saved package bytes without executing model or reader
snapshots:

```sh
.venv/bin/python -B -E -s -S -m experiments.durable_archives verify \
  --package "$archive_store/exported-study"
.venv/bin/python -B -E -s -S -m experiments.durable_archives restore \
  --package "$archive_store/exported-study" \
  --output /absolute/path/to/another-retained-store/restored-study
```

Restore copies the complete package to a fresh directory. It does not install,
repair, execute or resume a study, and it does not adopt archived process IDs.
The restored native archive is `restored-study/archive/`. Preserve its wrapper
and reader/evidence metadata as well as the native directory.

Explicit reconstruction is a separate action:

```sh
.venv/bin/python -B -E -s -S -m experiments.durable_archives reconstruct \
  --package /absolute/path/to/another-retained-store/restored-study \
  --checkout "$reader_checkout" --revision "$reader_revision" \
  --output /absolute/path/to/fresh-reconstruction
```

Use a clean checkout at exactly the package's recorded full reader revision,
with tracked bytes matching its preserved reader inventory. This first version
intentionally requires that exact revision, even after a documentation-only
commit. A different current revision does not invalidate the package's saved
bytes; select the retained compatible checkout explicitly. The package never
fetches Git history, creates a checkout or executes its `reader/` or archived
model sources. In the installed application, an explicitly retained installation
at that exact revision supplies the verified source inventory and private
interpreter; source and runtime bytes are checked against its package manifest.
An archived source snapshot never grants executable-reader trust. The original archive location and
original numerical environments need not exist for reconstruction.

## Use the local GUI

Prepare an existing storage directory outside the current checkout, then start
with an explicit store:

```sh
.venv/bin/python -m experiments.gui \
  --archive-store /absolute/path/to/independently-retained-archives
```

The GUI may create only fresh opaque package children in that store. It does
not grant arbitrary write access to browser-supplied paths. Export selects a
known stopped sealed M3 run, completed or failed native M4 study/campaign,
or a registered supported study; the authoritative reader still decides whether its saved evidence is
reconstructible. Without a configured store, export is unavailable.

Package registration uses an explicitly allowed root and relative directory.
Registering, verifying and reconstructing use bounded owned workers and the
existing one-active-operation rule. The original registered package remains
read-only. Passive browsing shows cached metadata; it does not rehash the
entire package on each HTTP request. Recheck after external changes.

The developer GUI reconstructs with its current trusted clean checkout. A
different recorded revision requires the CLI route with a compatible checkout.
The installed GUI instead verifies its retained installed source and private
runtime. For a different recorded revision, exit OpenT1D and open the matching
**Saved readers** shortcut. The installer creates a separate writable archive
store automatically; its location and retention policy are documented in the
installation guide. Imported archives gain no execution, resume
or process-ownership authority. Numerical reports remain separate from GUI
administration.

## Interpret the result

Keep these meanings separate:

- **Integrity verified:** the package bytes agree with its inventory.
- **Reconstruction verified:** the explicit authoritative reader accepted saved
  evidence without a new model run.
- **Complete:** the native task's planned coverage and numerical acceptance
  passed (M4), or the native complete-cohort field is true (M3). A verified
  failed or incomplete report keeps its original status. Execution completion
  and cohort completeness remain distinct.

SHA-256 identities establish saved consistency, not authentic execution,
independent reproduction or clinical validity. Packaging does not establish
redistribution rights. Preserve source ancestry, license notices and any data
restrictions before sharing; private health records and credentials do not
belong in public packages or Git. This maintained synthetic route introduces
no human observations.
