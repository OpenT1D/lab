# Historical runtime extension after pinned GlucoSim intake

This follow-up retains the original M0 and M1 historical baselines while
checking one explicitly reviewed runtime addition. It is an internal synthetic
software verification task. Independent human reproduction and biological
validity retain their separate requirements.

## Diagnosis and preserved criteria

[CI run 37014981209](https://github.com/OpenT1D/OpenT1D/actions/runs/37014981209)
executed commit `e77c9d79408b662e285401fc018534a4619fa055`. M0, M1 and M2
retained their native outputs before their historical-context checks failed.
The earlier commit `d6e97db6ae9f0885a15f8ad1b8ea3a488956e98c` added GlucoSim
`0.1.2`, pinned at `6422a91d533125a8feb4f2e8737aecd67fec95c9`. The complete
parsed lock comparison shows this addition and its root dependency declarations;
all pre-existing entries, artifact hashes and options are unchanged.

| Binding | SHA-256 |
| --- | --- |
| Original native lock | `634d5849a1cc4ae37f4f00c12c713f168cffa93a43d5a22b571b0c41478fc95c` |
| Extended native lock | `13d254dcebe8d1ab54c3140cdc07152d719a68477a1378d7fe77fc1568612aa9` |
| Original M0 baseline | `df1baf9bb878055d296f651b1e6bce2f0a85e273c8367ea0d2564e8d1e7c8f0d` |
| Original M1 baseline | `8e84fec115fc9a3812c17e018910ce1b023f735eb09aa0b8838ab792e66331fb` |

The versioned record is `experiments/m0/simglucose/runtime-context/review.json`.
Its archived `legacy-uv.lock` is copied from the parent of the addition commit.
The checker verifies the complete lock difference and original baseline bytes
before selecting the extended context. An original-runtime result retains its
original verification result. Extended results carry separate review/checker
hashes, both lock hashes and the declared package addition.

M0 records 34 locked distributions before importing Gym. Importing the legacy
`pkg_resources` dependency exposes additional vendored distribution metadata;
M1 records that complete post-import inventory. This changes metadata visibility,
not installed versions. M0 permits only the two recorded whole inventories and
verifies the raw inventory against every installed lock entry. M1 requires its
original inventory plus GlucoSim. Unknown locks, package upgrades, missing
packages and mixed historical collections are rejected.

Both original baseline files, all historical trajectories and their origins,
protocols, model/controller sources and all current dependency locks remain
unchanged. Historical comparison still requires exact original output digests;
no numerical tolerance is added or widened.

## Verification route and evidence status

The retained Linux M1 outputs match the complete original `linux_final`
collection of 32 scheduled cases with the extended runtime context. Native PID
terminations remain part of that collection. M2's retained native historical
comparison also passes; the saved report was produced by its recorded source
revision. Reconstructing it with changed checker source changes the reported
analysis-source hash, which must remain visible rather than being overwritten.

The [execution record](../../experiments/m0/simglucose/runtime-context/execution.json)
binds verification to clean commit `0d9048a4d4aba370ae9e5547a6543c0cfaa93899`.
Fresh Mac execution passed the following unchanged criteria:

- M0: eleven native tests, two complete tutorial processes, exact within-process
  reset and exact fresh-process CSV bytes, matching the original Mac digest.
- M1: twelve native tests, all 32 scheduled cases matching the original `mac`
  collection, three exact fresh-process replays and byte-identical JSON/Markdown
  reconstruction with `python -S`. The 28 complete cases and four native
  terminations remain visible.
- M2: thirteen native tests, exact reset/native-boundary checks, fresh-process
  replay, retained signal/deadline attempts and all 40 development cases. The
  original M1 and Cambridge historical outputs match; all 36 complete cases and
  four native terminations remain visible. JSON/Markdown reconstruction is exact
  without site packages.
- C-peptide volume: seven native tests, 60 analyses and 120 fit starts per
  execution, all five acceptance gates passed, zero artifact differences in the
  fresh-process repeat and exact report/figure reconstruction.
- Locked tooling: all 838 repository tests, formatting/lint/navigation checks
  and the documentation build passed.

On retained Linux execution, M0's original digest and reset match; M1 and M2
match the complete original `linux_final` collection, and all 32 common cases
from the separate M1/M2 jobs have exact initial/trace digests. Both saved Linux
reports reconstruct byte for byte from their original `e77c9d7` source using
`python -S`. Current-source serialized reconstruction retains every other
report field and exposes the changed historical-checker analysis hash.

The independent internal agent review of `0d9048a` found no actionable defect
in the code, inventories, original lock/baseline identity, negative historical
contexts or deadline-only CI change. This is an internal code review, not
independent human reproduction. A CLI attempt that selected the tooling
interpreter for M1 failed all 32 scheduled cases because NumPy was absent; it
remains archived alongside the corrected native execution. The current-source
verification attempt on the old Linux M2 report also remains archived.

The local ignored archive retains 2,987 inventoried evidence files, the inventory
and a frozen source snapshot; its digest and inventory are recorded in the execution record. All
463 original experiment files other than the two explicitly changed historical
checker integrations are unchanged from `e77c9d7`.

The initial execution record retains its earlier pending-CI snapshot. The
original likelihood-profile job subsequently exceeded its four-hour limit;
the [profile CI record](../../experiments/m0/simglucose/runtime-context/profile-ci.json)
retains that outcome and its operational follow-up. The complete fresh Mac
campaign and its fresh-process repeat passed all seven gates, with exact
report/figure reconstruction. Subsequent
[hosted candidate verification](../../experiments/integration/runtime_fix_hosted.json)
completed all thirteen CI jobs on 3 October 2026, including fresh Linux historical
checks and the full `macos-14` profile campaign. The earlier execution records
retain their dated pending-hosted snapshots.

Concurrent local work added the common task entry and M3 candidate comparison
on `main` at `ed0ffd91dafbbd06a752bea54fb3b90335ffeb67`. The separate fix
branch incorporates that commit at clean `99084307923b2cbd3b18a422489d0530631329a9`.
All 878 combined repository tests and the documentation build passed. All 271
tracked M0/M1/M2/M4 files at that integration commit remain byte-identical to
the prior reviewed fix. Independent internal compatibility review found no
actionable issue and confirmed preservation of the new workflow, its CI
acceptance and both bounded resource adjustments. The runtime decision now uses
[0056](../decisions/0056-reviewed-runtime-extension.md); frozen source archives
retain the earlier filename and original bytes. This preserves recorded native
execution identities. The profile CI receipt records this integration separately
from the earlier 838-test and native execution stages. Primary `main` remained
untouched during that pre-publication compatibility review.

For a new checkout, keep the locked environments separate. The [M1 tutorial](../m1-tutorial.md) and [M2 tutorial](../m2-tutorial.md) remain canonical for their complete workflows:

```bash
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv run --locked --project experiments/m0/simglucose python experiments/m0/simglucose/run.py --output results/runtime-m0
uv run --locked --project experiments/m0/simglucose python -m experiments.m1 demo --output results/runtime-m1
uv run --locked --project experiments/m0/simglucose python -m experiments.m1.verify --study results/runtime-m1 --output results/runtime-m1-verification
uv run --locked python scripts/check.py
```

## C-peptide volume CI deadline

GitHub's job annotation explicitly records that the volume job exceeded its
30-minute maximum. Its retained artifact contains all 60 primary analyses and
36 repeat attempt files: 34 complete byte-identical analyses, one partial
attempt with one exact retained fit start, and one started attempt without a
fit. The primary numerical gates passed. The repeat and final report/figure
were unfinished; the Linux campaign did not pass.

Increase only this job's operational deadline to 90 minutes to allow the full
frozen matrix, fresh-process repeat and runner variation. This is a bounded
scheduling allowance. The subsequent complete Linux campaign passed all five
gates in 17.95 minutes with zero repeat artifact differences, as recorded in
the hosted receipt. Keep every attempted analysis, original protocol, source, fit start
and numerical acceptance threshold unchanged. The new complete Mac campaign
took 9 minutes 24 seconds, close to the earlier nine-minute Mac execution;
that timing was insufficient to set the original Linux deadline.

## Likelihood-profile CI execution host

The final job annotation establishes the four-hour timeout. The retained
primary execution contains two complete free-volume noisy cases, three partial
cases and four cases that never started. The complete cases pass reconstructed
forward/profile gates under the frozen criteria; the repeat did not start.
The original manifest, source snapshots, lock, every partial checkpoint and
original artifact ZIP are preserved. This Linux campaign remains unaccepted.

Run this complete campaign on `macos-14` with a 360-minute operational ceiling.
The unchanged three-process driver previously completed all nine cases and
27 profiles, including the full fresh-process repeat, on macOS arm64 in
133 minutes. [GitHub's standard runner specification](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
provides three M1 CPU cores for this macOS label and two cores for the private
Ubuntu runner. That resource choice and the complete Mac measurement motivate
the allowance; they do not establish the full cause of the platform timing
difference or guarantee the new hosted duration.

Keep both complete executions, all optimizer starts, solver/refinement checks,
protocol bytes and numerical acceptance criteria. Fresh local execution at
clean commit `547db14bccdf5a21f7ce005afcac7f6fcadd9439` on macOS `26.5.2`
arm64 took 134.46 minutes. Each of the two processes completed nine cases,
27 profiles, 504 sampled points, 148 reference checks and 1,364 optimizer
starts. All seven campaign gates passed with zero repeat artifact differences.
The `python -S` report reconstruction and the figure reconstruction from saved
results are byte-identical. All 42 source snapshots and the native lock/project
bytes match the frozen contract.

Independent internal reviews of the primary execution and complete campaign
found no actionable defect. The archive audit verified all 156 evidence files,
their inventory and all 812 file blobs in the frozen execution-source archive.
The versioned receipt records the review and archive hashes. The subsequent
[hosted run](https://github.com/OpenT1D/OpenT1D/actions/runs/37117782673) at clean
`e4b631de436f1bec9acf49a9887a237a6bfeafbb` passed all thirteen jobs. Its complete
`macos-14` profile execution and fresh-process repeat took 178.44 minutes;
each completed nine cases, 27 profiles and 1,364 optimizer starts. All seven
gates passed, all nine case files repeat byte for byte, and saved report/figure
reconstruction is exact. All 42 source snapshots and the original protocol
match the frozen contract. The
[hosted receipt](../../experiments/integration/runtime_fix_hosted.json) binds
these results, the actual runner label, native versions and all thirteen ZIP
hashes. The original interrupted Linux profile campaign remains unaccepted;
independent human and biological evidence requirements remain open.

## Separately tracked setuptools alerts

The two originally reported medium alerts refer to the same
[setuptools advisory](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c),
`GHSA-h35f-9h28-mq5c` / `CVE-2026-59890`, fixed in version `83.0.0`.
Its source-distribution manifest exclusion can fail on macOS when Unicode file
name normalization differs. This affects source-distribution construction and
can disclose excluded files if such an archive is published.

| GitHub alert | Recorded dependency location | Disposition for this follow-up |
| --- | --- | --- |
| [1](https://github.com/OpenT1D/OpenT1D/security/dependabot/1) | `experiments/m0/simglucose/pyproject.toml` | Keep the legacy runtime pin explicit; alert remains open. |
| [2](https://github.com/OpenT1D/OpenT1D/security/dependabot/2) | `experiments/m0/simglucose/uv.lock` | Same runtime dependency and advisory; alert remains open. |

The runtime uses setuptools `80.9.0` because pinned Gym imports `pkg_resources`.
Isolated build constraints already specify setuptools `84.0.0`; this does not
remove the vulnerable runtime distribution or close either alert. This fix
checks saved artifacts and executes simulations; it does not build or publish
an OpenT1D source distribution. The advisory does not explain the historical
lock mismatch. A runtime migration needs separate dependency/API verification;
no upgrade is made here.

The later dependency-graph scan reports 46 open alert entries: four critical,
four high, eighteen medium and twenty low. These are entries across repository
manifests, not 46 distinct vulnerabilities. The two entries above do not
represent the full current security backlog. Broader remediation remains a
separate investigation; this context fix makes no security-clearance claim.
