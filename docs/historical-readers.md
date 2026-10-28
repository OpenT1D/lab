# Reconstruct archives with a trusted historical checkout

Some scientific archives bind their reader sources and runtime locks. A maintenance update may change those bytes, so the current reader correctly refuses the old archive. Keep that refusal: do not rewrite the archive, replace its recorded hashes or install an outdated environment to bypass it.

The historical reader helper runs a fixed saved-evidence reader from an existing checkout that you explicitly trust. It uses the current Python interpreter with `-B -E -s -S`, without loading site packages or the historical checkout's virtual environment. It does not install dependencies, change Git state, execute archived source snapshots or dispatch a module named by the archive.

## Choose the reader explicitly

Bootstrap the current root tooling with `uv sync --locked`, as described in the [task setup guide](task-setup.md). Separately retain a clean checkout at the full Git revision that matches the archive's recorded sources. Creating or selecting that checkout is your explicit action; this helper never fetches, checks out or creates one.

For example, replace the placeholders with your trusted checkout, its full 40-character Git revision and a saved campaign:

```sh
.venv/bin/python -B -S -m experiments.historical_readers reconstruct campaign \
  --archive /absolute/path/to/saved-campaign \
  --checkout /absolute/path/to/trusted-reader-checkout \
  --revision FULL_40_CHARACTER_GIT_REVISION \
  --output /absolute/path/to/fresh-reconstruction
```

The fixed task allowlist is `p1-controller`, `m3-forecast`, `m3-compare`, `m4-secretion`, `m4-compare`, `m4-study`, `m4-study-secure`, `m5-prognosis` and `campaign`. Each task selects its known native reader command. The secure successor needs a trusted checkout containing `experiments.m4.secure_study`; selecting an older checkout without it fails explicitly. An unknown task or incompatible historical revision is refused; archive metadata never selects executable code. `--allow-failed` permits preserved failed M4 or campaign evidence to be reconstructed, while completeness remains false. The reader timeout defaults to 120 seconds; `--timeout-seconds` accepts an integer from 1 to 1800.

The checkout must be its Git root, have the exact requested revision, and have no modified tracked or nonignored untracked files. Ignored virtual environments may exist but are not selected or imported. The helper records the current interpreter, trusted checkout revision, all tracked file hashes, fixed command and full source archive inventory. Output must be fresh and must not overlap either checkout or the source archive. Symlink archive entries and tracked checkout paths are refused.

## Inspect the receipt

The output retains `reader.log`, `receipt.json`, the native reader's `reconstructed/` outputs and a sealing `manifest.json`. M5's existing reader verifies its saved report in place; its helper output contains the log and receipt instead of a copied native report. The complete source archive and tracked checkout inventories are checked after success, failure, timeout or interruption. A reader failure retains diagnostics and receives no successful verification claim. Active readers and their process group are terminated and reaped on timeout or interrupt.

`verified_reconstruction: true` means the selected historical reader accepted saved evidence with unchanged inputs. `complete` separately describes whether that evidence is complete and accepted by the task. Reconstruction does not rerun a simulation, import a supplied algorithm, independently reproduce scientific behavior or establish biological validity. Trust the selected checkout's reader code before invoking it: isolation from historical site packages does not sandbox trusted Python source.

Keep the original archive and its provenance authoritative. The receipt records which reader checkout was used; it does not claim that an old environment is safe to reinstall or that the current implementation accepts different source identities.

For maintained M4 studies and `maintained-campaign` evidence, use the separate
[durable-archive guide](durable-experiment-archives.md) to preserve complete
native bytes and the exact full trusted-reader inventory outside disposable
worktrees. Its `reconstruct` operation requires a clean checkout at the
package's recorded full revision, including after documentation-only changes.
The historical helper's `campaign` task still selects the original campaign
reader; it is not an alias for `maintained-campaign`.
