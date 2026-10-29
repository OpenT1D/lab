# OT-061/064 minimal two-route services

## Problem and change

The [extraction queue](../../ROADMAP.md#shared-core-extraction-queue) needs a
store and owned lifecycle around the existing `m4-study-secure` and
`mmtt-sensitivity` workers. The OT-059 metadata packet cannot prove that an
entire attempt was omitted. Increment 2 records starts before launch and
preserves the complete sequenced ledger, freezes and terminal evidence.

## Scope and contracts

Base: `718800a735be2d812088a448decb43c94304e621`, the OT-059 merge. The
integration owner writes on `codex/ot061-064-minimal-services`; exactly one
read-only GPT-6.1 Sol reviewer uses xhigh for independent lifecycle/storage/reader
investigation and final technical review. The integration owner alone runs the
final full repository check. This is the bounded proposal in the repository PR
template convention; no remote issue is implied.

Reuse regular-file snapshots, atomic exclusive publication, process ownership,
task dispatch and authoritative readers. Preserve raw scientific inputs,
source/reader snapshots, immutable plans and derivation, every explicit retry,
native reports and unfinished forensic evidence. Keep execution, completeness,
reconstruction and synthetic scientific evidence separate. New architecture is
recorded in [decision 0081](../decisions/0081-minimal-project-services.md).

M4 keeps both existing Dalla Man/ultradian sources, fasting and a derived
15 g gastric-load plan, adult#001, 240 minutes, 961 samples at 0.25 minutes,
reference/source/RHS state and derivative/rate outputs, SC/basal/portal
ownership, solvers, observer, refinement and fresh-process repeat gates. MMTT
keeps one invented visit pair, nominal/volume-120/peripheral-075, 128 draws,
seed 117, original context/units/availability and failure/draw denominators,
and after-minus-before contrasts. No scientific baseline or tolerance changes.

Excluded: installed SDK/CLI (increment 3), other routes, universal stepping,
native installation, GUI redesign, cache/campaign platform, Windows installer,
second-engine family conformance and independent human use. Native success
requires its admitted environment; a controlled failure supplies no parity.

## Acceptance and counterexamples

- Create, freeze and derive immutable plans with exact original asset bytes;
  reject missing, swapped, duplicate or changed plan/asset/attempt identities.
- Register before starting an isolated worker; retain success, interruption,
  controlled failure, deadline and explicit retry. Preserve every planned slot
  and unfinished payload; no fabricated native report on forced termination.
- Refuse lost ledger suffixes, unknown entries, duplicate attempts, mismatched
  runtime/source/reader identity and concurrent writers.
- Relocate complete and incomplete projects; dispatch the existing trusted
  readers and compare authoritative report bytes. Require explicit admission
  for failed/incomplete evidence; never execute archived Python or run setup.
- Exercise owned-process cleanup with a real child and preserve an unrelated
  process on the declared local macOS host.
- Test matching readers and refused implementation upgrades. Retained reader
  snapshots remain opaque; neither MMTT route uses `historical_readers`.

## Evidence

Local host: Apple Silicon macOS 26.5.2, CPython 3.12.13 and uv 0.11.16.
The integration owner's `uv sync --locked` passed using the existing cache
after the sandbox denied its first cache access. No native runtime was installed.
Neither the current worktree nor the original checkout had the selected M4
secure/observer environments. Production M4 execution therefore recorded an
actual passive runtime refusal, without numerical execution or setup.

| Command / case | Observed outcome |
| --- | --- |
| `.venv/bin/python -m unittest tests.test_shared_services -v` | Initial 10 cases passed after correcting a temporary-directory alias; expanded 13-case suite passed after review fixes. |
| `.venv/bin/python -m unittest tests.test_shared_services tests.test_shared_contract_packet tests.test_m4_secure_study tests.test_observation_workflow -v` | 43 tests passed, no skips. Existing packet and native-reader controls remain unchanged. |
| `uv run --locked python scripts/check.py --stage style` | Passed. An earlier direct Python invocation lacked `ruff` on PATH; that invocation supplied no style result. |
| Retained local service exercise | Four plans, six attempts: real MMTT complete/retry/completed-incomplete/signalled-interrupted; actual M4 runtime refusal; separately generated controlled M4 native-stage launch failure. All five native reports reconstruct after relocation with identical authoritative bytes; forensic runtime refusal remains unavailable. |
| Independent reviewer checks | Original three counterexamples reproduced, then refused after correction. Seven focused regressions passed, including real nested process cleanup and unrelated-process preservation; `git diff --check` passed. |

The retained exercise script, original and relocated projects, rebuilt reports,
summary and logs are under local ignored `results/ot061-064/`. The exercise ran
on the base revision plus the uncommitted service changes; each native M4 plan
retains its actual source/dirty provenance. It is not a final-revision native
success receipt. Early targeted tests exposed eight errors from macOS `/var`
temporary-directory aliases; canonical temporary paths corrected them. Those
errors were not process or numerical success observations.

The integration owner alone runs the final full check after committing the
integrated changes:

```sh
uv sync --locked
uv run --locked python scripts/check.py
```

`results/ot061-064/final-receipt.json` records the actual checked revision,
dirty state, commands, exit outcomes, timing and final log. Consult that receipt
for its outcome; this tracked record does not anticipate success. A later
relevant edit requires another receipt. Local checks are not hosted CI.

## Limitations and review handoff

The read-only reviewer inspected the new services, tests, callers and canonical
documentation against `718800a`. Three findings were independently reproduced
and fixed before final integration:

- **P1, process metadata failure:** repeated observation errors could skip
  cleanup and be rewritten as an empty process receipt. The owner now forces
  previously observed live identities and reaps its direct child. Unverified
  cleanup remains explicitly unknown, blocks terminal sealing and preserves
  the start/workspace for explicit stopped-execution recovery. The regression
  preserves an unrelated process and checks no terminal event was invented.
- **P2, output alias:** lexical output separation accepted `..` or symlink
  aliases into the project. Reconstruction, relocation and snapshot creation
  now use the existing canonical regular-ancestor/fresh-path guard before writes.
  Both aliases refuse and leave the project reopenable.
- **P2, M4 intake:** an archive could lack its native manifest/model snapshot
  and still acquire native metadata. Intake now requires the complete native
  inventory/manifest and passive maintained frozen-plan/source gates, without
  activation. Missing assets refuse before an import start is published.

The reviewer repeated the original cases after correction and ran seven focused
regressions, all passing, with no remaining actionable finding in the bounded
diff. Final separately reviewed identities:

| File | SHA-256 |
| --- | --- |
| `experiments/shared_services/execution.py` | `6519f9cc5d98354bd4da92a785e93c31707b684fe3cddc398e6fa7b83e7f96a6` |
| `experiments/shared_services/routes.py` | `cd3a5546cdfebdc18c4ee0580ecc74c9295b7864978a387fa3782e7f17466c19` |
| `experiments/shared_services/store.py` | `d8b5d84d5f9582524eee73cc903a2f2a581d4de3f0f7ca996bac48d4d71b2b72` |
| `tests/test_shared_services.py` | `6f69d0b03c87c747577b11fcc462fedd9887a4eb0685ed6c1bd02088ba273046` |

Service tests also cover lost
suffixes, swapped/duplicate events, changed original/snapshot/native files,
rehash-resistant roster/slot/parent contradictions, runtime/reader refusal,
opaque imported Python, explicit failure admission and byte-exact native reports.
No existing scientific source, protocol, lock, baseline or tolerance changed.

This closes the bounded service implementation and local macOS evidence,
including complete/incomplete/interrupted MMTT and failed M4 relocation. It
does not establish native M4 success/parity or complete native relocation.
Those require the selected admitted environments and the unchanged reference,
refinement, observer and fresh-process gates. Installed increment 3, supported
reader/application upgrades, other service hosts, Windows installer, second
native-engine family conformance and independent intended-user/biological
evidence remain separate. Interrupted event/head publication fails closed with
forensic evidence; automated journal repair is not implemented. Agent review
does not establish independent scientific validation. Substantial AI assistance
is explicit in the ownership above.

## Critical double-check of the committed services

On 29 October, the user requested another critical review with multiple agents.
Two read-only GPT-6.1 Sol reviewers independently inspected clean commit
`ba084ae23088dba6887178616d3b34b2e126b763` against the original `718800a` base.
One investigated storage, freeze identity and readers; the other investigated
lifecycle and evidence claims. The integration owner remained the only writer
and full-check owner. The original receipt above is preserved unchanged.

Six bounded corrections were reproduced on disposable projects before fixes:

- A project object retained after its `opened` context could bypass a newer
  writer's exclusive lease. The subsequent writer could collide and leave the
  store unreadable. Every service operation now requires the live context's
  lease; context exit invalidates the object before releasing the lock.
- A completed MMTT archive could lose its native freeze, draw file or raw
  perturbation evidence, be resealed, and still acquire complete native metadata.
  An interrupted archive could similarly lose its admission. Intake now requires
  the native frozen-plan association, raw draw/variate fields and rosters,
  descriptive native report consistency and exact failed admission association.
  Failed partial snapshots retain the native reader's existing allowance. Full
  numerical replay remains an explicit trusted-reader operation.
- A failed M4 native plan could substitute the other source/declaration pair,
  reseal its native inventory and keep the original shared/report metadata.
  Each native scientific source/declaration now matches the shared frozen pair,
  in addition to its own native frozen gates and report binding.
- Reader completion alone could publish verification despite a nonempty or
  unknown owned-process cleanup receipt. Supervision now marks that unresolved,
  and reader verification independently requires zero exit and empty cleanup.
  Actual native reader outputs with injected adverse cleanup receipts refuse
  without adding a verified ledger event; these injections do not demonstrate
  an actual unkillable child.
- An invalid `begin` mode could commit an event that the store subsequently
  refused. Unsupported modes now refuse before any event or workspace write.
- `finish` could snapshot and remove a foreign caller-supplied directory, then
  leave the original work directory inconsistent with its terminal event.
  It now requires the exact owned active workspace and refuses already terminal
  attempts before writing or deleting anything.

The helper argument cases were internal Python API misuse, not a demonstrated
GUI or CLI exploit. They are still useful boundaries for subsequent SDK work.
The stricter intake gates preserve valid version-1 archives; malformed native
payloads previously mislabeled admissible are refused. No native scientific
source, protocol, runtime lock, frozen fixture, baseline or tolerance changed.

The updated service suite has 17 tests. The combined service/OT-059/maintained
M4/observation workflow command above passed 47 tests with no skips. The
lifecycle reviewer additionally passed six focused tests, repeated its original
mode and reader-cleanup cases, and checked an actual ownership-constructor
failure: the direct worker was reaped, cleanup stayed explicitly unknown and an
unrelated process survived. The storage reviewer repeated all four original
intake cases and the escaped-lease case, with unaltered original/moved MMTT
controls still passing. Its five focused regressions passed. Both reviewers
reported no remaining actionable finding within their inspected scope;
`git diff --check` passed. Their exact reviewed source identities are retained
in `doublecheck-review.json` and match the corrected commit's code.

The integration owner's fresh committed-revision full-check result and final
review identities are retained under local ignored
`results/ot061-064/doublecheck-final-receipt.json`,
`doublecheck-final-check.log` and `doublecheck-review.json`. Consult those
receipts for the actual final revision, dirty state, outcomes and limitations;
this tracked record does not anticipate a pass. The previous `final-receipt.json`
continues to refer only to `ba084ae`. Native M4 success/complete relocation,
other hosts, supported upgrades, installed use, second-engine families and
independent human/scientific acceptance remain open as described above.

## Public integration and CodeQL triage

The service branch was updated from main `d0f0515`; only the changelog overlap
needed manual resolution. The native/reader inventory remained byte-identical
and the retained project still opened with four plans and six terminal attempts.

[PR 29](https://github.com/OpenT1D/lab/pull/29) initially produced one new
`py/clear-text-storage-sensitive-data` signal at the shared metadata writer.
The retained SARIF flow starts at the local variable `trusted` assigned from
`reader_identity`, then follows the descriptor's public `reader` field to JSON
storage. That object contains a fixed module/schema, public source filenames
and SHA-256 hashes, a compatibility label and an archived-execution prohibition;
it contains no credential or private observation bytes.

The upstream [sensitive-data heuristic](https://github.com/github/codeql/blob/main/shared/concepts/codeql/concepts/internal/SensitiveDataHeuristics.qll)
classifies names containing `trusted` as potentially secret; its
[Python assignment model](https://github.com/github/codeql/blob/main/python/ql/lib/semmle/python/dataflow/new/SensitiveDataSources.qll)
marks the assignment's right-hand side as the source. Rename that local to
`reader_metadata` to describe its actual content. Persisted descriptor fields
and bytes stay unchanged. No query, result suppression, native source, baseline,
tolerance or alert dismissal is introduced. The exact SARIF and subsequent
local/hosted receipts are retained in local ignored `results/ot061-064/`.
