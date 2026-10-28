# OT-035 and maintained runtimes — internal verification

**Scope:** the isolated implementation selected on 4 October 2026, from baseline
`9e7348e56fc3ec5b9ed404423b6cb6a2eeb51a4b`.
[Decision 0059](../decisions/0059-maintained-runtimes-and-local-gui.md) and the
[execution plan](ot035-maintenance-execution-plan.md) were frozen first.
Implementation and local verification were isolated on `codex/gui-integration`
before integration into main.

## Maintained environments and preserved evidence

| Package | Actual local verification |
| --- | --- |
| Root HTTP/tooling | urllib3 2.8.0; all other 61 locked package blocks unchanged. Installed-package security checks, locked sync and historical-reader checks pass. |
| Maintained M4 successor | Separate `m4-study-secure` identity, urllib3 2.8.0 and setuptools 84.0.0; unchanged attributed engine, NumPy 1.26.4 and SciPy 1.13.1. Complete installed/native source attestation and 12 inherited numerical checks pass. |
| Both C1 environments | PyTorch 2.13.0, bounded declared checkpoint intake, 13 checkpoint tests in each environment and exact synthetic source/intake actor probes pass. Full trained replay is locally verified from the retained trusted inputs. |

The [M4 runtime protocol](m4-secure-runtime-protocol.md) binds the new execution
and its narrow resource adapter. Its definitive native run used clean revision
`7a9ce66b9df4695fe5683cfd3f5051ca4275affa`. The autonomous maintained reference,
all three initial-load controls and both source workflows pass: 2/2 sources,
6/6 source/load cells and 1/1 pair. Standard-library reconstruction reproduces
JSON, Markdown and SVG exactly. All 330 compared scientific output files agree
byte for byte with the retained historical M4-STUDY/2 execution; native
scientific identities agree apart from declared installation locations.

The retained three-source negative fixture keeps its failed source, accepts the
two valid sources and preserves all planned cells/pairs. A tight whole-source
deadline preserves both nonaccepted cells; a native interruption preserves the
blocked source and later unattempted source. Their explicitly opted-in readers
reproduce the failed reports exactly. Callback PIDs are no longer live after
cleanup. Failed reconstruction without opt-in and resealed runtime/reference
tampering are refused. The local receipt is
`/private/tmp/opent1d-security-acceptance-20261004/native/acceptance-receipt.json`,
SHA-256 `820a7dba67869dab24aba8fc2d4dd4414de7d98364e0c5e800f6d7cfe8708231`.

The [C1 verification record](../../experiments/c1/g2p2c-security-verification.json)
and [runtime guide](c1-g2p2c-security-runtime.md) identify clean revision
`11a2213b6517ab36c62bbad7edc93b24fe8a2cb4`. Both declared profiles and their
fresh native repeats pass, with 960 intervals per attempt and exact repeat
initial/trace/report bytes. Source/intake state/action parity, missing-CGM basal
fallback and RNG/reset checks pass. Torch 2.2 and 2.13 outputs are not identical:
the largest adult#001 glucose difference is approximately 0.000195 mg/dL;
the exact field counts and values remain in that record. Historical training
and comparator status are unchanged. The first loader attempt failed on
Torch's own lazy internal classes; its four failed attempts remain preserved.
No numerical criterion or checkpoint changed in the correction.

The [historical-reader helper](../historical-readers.md) reconstructs all seven
historical scientific routes and the local campaign through an identified clean
reader checkout, without installing historical dependencies. Original archive
inventories remain unchanged. An incompatible current checkout and a copied,
resealed campaign with a substituted root lock are refused. Its ten-command
receipt is `/private/tmp/opent1d-security-acceptance-20261004/tooling/summary.json`,
SHA-256 `b0a508e6f7fa85a1dcabc2508e9fbcd36a51211a635e63b2505a2c415fce68b1`.

These are scoped dependency changes. Historical native locks retain their
recorded versions, and the C1 training project's setuptools 80.9.0 remains
unchanged. No claim that every repository advisory has been resolved is made.

## Local GUI and integration

The [local GUI](../local-gui.md) registers one complete maintained M4 task.
Configuration and source snapshots, explicit locked installation, one active
owned operation, native result display and reconstruction remain separate.
Scientific artifacts stay outside GUI job administration.

The complete 0/15/30 gram GUI study and a separate CLI execution accept 2/2
sources, 6/6 source/load cells and 1/1 pair. Their independent standard-library
readers reproduce each archive's JSON, Markdown and SVG exactly. The
GUI/CLI comparator confirms all 330 scientific output files are byte-identical,
with the same numerical gates, controls, trajectories and descriptive pair
metrics. Administrative paths, timing, logs and seal hashes remain separately
recorded and accounted for by the comparator. Both
archive inventories, the frozen configuration and all 101 reader source files
remain unchanged. The comparator receipt is
`/private/tmp/opent1d-gui-acceptance-20261004/gui-cli-scientific-parity.json`,
SHA-256 `cd1fdcfc8576e9867e05de978757429d55b2e633e47a69a4c0fa6692147a1453`.

The actual GUI negative-flux study exits with failure and retains its complete
planned roster: 0/2 accepted sources, 0/2 accepted source/load cells and 0/1
accepted pair. Both sources fail the nonnegative pancreatic-rate boundary;
shared controls still pass. The retained native archive is
`results/gui/job-2c85191023444c6d91f36c64494b6b31/archive`, with manifest SHA-256
`59e41ea9173eeb2b6f0e514823be18b4d01cd5938034cca54ab47568e0c956cd`.
Passive configuration readiness did not establish source acceptance.
A successful GUI reconstruction preserves this failed/incomplete scientific
status and all zero accepted denominators.

Actual browser cancellation and SIGHUP during native execution both retain
cancelled GUI jobs with native exit code 1, without forced cleanup. None of
their six and seven observed processes, respectively, remain live. The SIGHUP
server exits with code 0; a server can restart on the same port after releasing
the manager lock. The restarted browser shows the earlier positive study as
unverified with its prior verification recorded. A fresh GUI reconstruction
exits with code 0 and restores current numerical acceptance and reader
verification. Actual JSON and Markdown download buttons save bytes identical
to the native archive. The 390-pixel mobile layout retains visible history
controls and a loaded figure.

Controlled delayed report and figure responses cannot replace a later selected
job; the previous figure is hidden while a new figure is pending. A whitespace
change to a derived reconstructed JSON report withdraws current acceptance and
shows the changed-archive status. The derived bytes are restored afterwards;
both sealed original native archives remain unchanged. These actual browser
checks bind final frontend revision `5dffa589` in
`/private/tmp/opent1d-gui-acceptance-20261004/browser-edge-proof.json`, SHA-256
`a5f516c409c18791f079d193c0740e79693780d426607640a01f88a43fbd1ef6`.

Explicit locked setup completes for root tooling, the maintained native runtime
and the observer runtime. A separate passive task check establishes installed
metadata and declaration readiness without executing candidate Python; only
the later native run assesses behavior. The GUI retains configuration/source
snapshots and uses the registered CLI and authoritative native reader.

The 27 focused GUI checks cover live process ownership, cancellation/deadlines,
concurrent-server refusal, SIGHUP cleanup, restart accounting, bounded path/body
intake and withdrawal of stale report verification. An exclusive kernel lock
permits one manager of a checkout's GUI journals. Descendant cleanup is bounded
to processes observed under the live owner and identified by OS start identity;
saved PIDs confer no authority. Trusted source execution is not sandboxed, and
an uncatchable server kill cannot guarantee cleanup. After restart, a retained
verification marker records prior evidence; a fresh reconstruction is required
for current verification.

The full required repository check at clean `12d6426` passes: 1,037 tests,
13 explicitly skipped, plus lint, formatting, Markdown/YAML, citation metadata,
navigation and the documentation build. Its retained log is
`/private/tmp/opent1d-gui-acceptance-20261004/repository-check-final.log`, SHA-256
`875c478db76e4ab18044817b4fac3c1cc9533939d07af486e18eb09fe1742150`.
Subsequent frontend verification at `5dffa589` separately passes JavaScript
syntax, eight controlled Node VM checks, the actual delayed-selection browser
checks above and a keyboard skip-link focus check.
The [GUI verification record](../../experiments/gui/verification.json) owns the
final local receipt and its exact browser/process scope.

## Hosted and independent evidence

Two additional prepared CI jobs exercise the full maintained M4 study and both
C1 checkpoint/synthetic actor boundaries. The prepared policy lists 16 checks;
all 14 historical jobs retain their commands. The full trained C1 gate uses
locally retained trusted checkpoints and native archives; CI has no published
input bundle and does not retrain or invent a download source.

On 4 October 2026, the published baseline's
[Repository checks run](https://github.com/OpenT1D/OpenT1D/actions/runs/37154955017)
still reports that jobs were not started because recent account payments failed
or the spending limit needs increasing. The successful Dependabot workflow on
the same revision is a separate administrative run. This candidate has no
hosted execution claim. Billing and live branch-protection settings were not
changed.

The 4 October 2026 integration into main uses the retained local checks above.
GitHub Actions minutes were reported exhausted when integration was authorized;
hosted verification of this increment remains unclaimed.

The [independent GUI exercise](../gui-researcher-exercise.md) is prepared and
unexecuted. Independent usability, human M2 reproduction, P1 acceptance,
human-data evaluation, biological validity, treatment benefit and a public
release remain separate open evidence requirements. Local verification here
uses macOS arm64/CPU; prepared Linux jobs do not establish executed Linux or
CUDA equivalence.
