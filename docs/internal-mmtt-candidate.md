# Internal MMTT candidate and reader transition

This bounded roadmap-step-6 candidate installs the Python/CLI SDK and project
workbench for **`mmtt-sensitivity` and `mmtt-sampling` only**. It requires the
declared host CPython 3.12 interpreter; it is not a standalone `.app`, signed
installer or public release. Qualification selects local Apple Silicon macOS.
The wheel remains `0.0.0.dev0`; its source revision, complete manifest and wheel
SHA-256 identify the actual artifact, rather than that development version.

The separately selected [integrated candidate](internal-integrated-candidate.md)
adds maintained M4 and connected-study qualification with explicit reviewed
runtime attachment. It preserves this two-task build and its compatibility scope.

## Build and retain the candidate

Read the [installed guide](installed-sdk.md) for Python, CLI and workbench use.
From a clean checkout, use a fresh output directory:

```sh
uv sync --locked
uv run --locked python scripts/build_sdk.py \
  --output /private/tmp/mmtt-candidate-b --build-label internal-mmtt-b --mmtt-only
uv venv --python 3.12 /private/tmp/mmtt-candidate-environment
uv pip install --no-deps --link-mode=copy \
  --python /private/tmp/mmtt-candidate-environment/bin/python \
  /private/tmp/mmtt-candidate-b/opent1d_lab-0.0.0.dev0-py3-none-any.whl
/private/tmp/mmtt-candidate-environment/bin/opent1d-lab gui \
  --workspace /private/tmp/mmtt-candidate-workspace
```

Retain `receipt.json` and the wheel together. Descriptor version 4 admits exactly
the ordered two-task roster and excludes native runtime admission. Python, CLI,
HTTP and the isolated worker enforce that boundary; the workbench omits native
and connected-study controls. The default broader developer wheel still uses
descriptor version 3 and its separately qualified runtime boundaries.

Projects and concepts live outside the installation. Stop the server before
replacing the environment; closing a tab leaves it running. Retain both exact
wheels and receipts, install B in a separate environment, then open the complete
project in B. Reconstruction is read-only, including direct native MMTT reports.
It writes new reports outside the project and retains A's original provenance.
Creating a plan or explicitly running an analysis remains a writing operation.

## Supported compatibility matrix

| Preserved evidence | Candidate B behavior |
| --- | --- |
| Project-store version 1, unchanged MMTT scientific plan/source/protocol/runtime selectors | Uses the existing authoritative MMTT readers. Exact saved input, native report, allocation, all-draw ledger and failure checks remain required. |
| MMTT comparisons frozen by A, merged PR 43 at `fc041c6e51463ae640d97c55719e742253e453e0` | Supports one pinned transition to B's changed comparison reader. The complete prior reader identity and complete qualified successor closure, roots and schema must match the packaged register. Every other definition field is reconstructed canonically. |
| A's initial, complete, incomplete, failed, interrupted and saved-prefix reports | Retains fixed first attempts and every member. Reconstructs the original report bytes at the explicit saved ledger tip; later retries cannot replace the selected first attempt. |
| Current B comparisons | Uses exact current reader identity. A has no promise to read new B comparisons. |
| Unknown/altered prior reader, changed successor helper/renderer/source, schema or scientific binding | Refuses. Updating an installed file manifest alone cannot authorize the transition. No archived code is imported or executed. |
| A's M4 or connected-study projects, including projects mixed with MMTT | Outside this candidate; refuse without modifying originals. Shared-service edits change M4's transitive source identity. A new native-capable artifact needs its own admission, references and qualification. |
| Rollback | Reinstall the retained exact A artifact and reopen preserved A evidence. This is not reverse migration of new B work. |

The original report's `definition.reader` remains A's frozen identity. The
reconstruction operation separately returns the actual current `reader` and
`reader_transition`, including both identity digests and the registry digest.
The installed manifest binds the registry bytes. Application labels do not
authorize compatibility, and there is no general historical-reader fallback.
See [decision 0089](decisions/0089-internal-candidate-reader-transition.md).

## Repeat the exact-artifact qualification

Retain a clean A wheel built from the specified predecessor before replacing
that checkout. Supply both actual receipts and wheels to a fresh output folder:

```sh
uv run --locked python scripts/qualify_reader_candidate.py \
  --a-wheel /private/tmp/mmtt-candidate-a/opent1d_lab-0.0.0.dev0-py3-none-any.whl \
  --a-receipt /private/tmp/mmtt-candidate-a/receipt.json \
  --b-wheel /private/tmp/mmtt-candidate-b/opent1d_lab-0.0.0.dev0-py3-none-any.whl \
  --b-receipt /private/tmp/mmtt-candidate-b/receipt.json \
  --output /private/tmp/mmtt-candidate-qualification
```

The procedure checks clean, distinct source identities and wheel hashes, then
installs ordinary copies offline in separate environments. A executes both MMTT
chains with complete and missing observations, preserves a deadline failure,
cancels actual observed analysis, and retains retries and initial report tips.
An independent constant-concentration oracle checks basal-inclusive secretion.
The procedure relocates the complete project and makes the original application
and project locations unavailable before B reads every saved report. It checks
the entire preserved project inventory, reopens that evidence in restored A,
and repeats current task workflows through B. No physiological runtime is
installed or executed. Logs and failed runs remain in their own output folders.

Installed regression tests separately exercise capability refusals, authenticated
HTTP downloads, readonly reconstruction, restart and source/definition changes.
The Chromium candidate case can consume the exact clean wheel via
`OPENT1D_READER_CANDIDATE_RECEIPT` pointing to its retained receipt; otherwise it
builds a development fixture. A development build is not an artifact receipt.

## Prepared formative exercise and open gates

The [first-session supplement](mmtt-formative-session.md) fixes a short MMTT-only
task order, artifact/start checklist, separate neutral participant card, actual
reference key and blank observation/report structure. Use it with the retained
packet; preparation does not record a human session or independent handoff.

Successful qualification generates `formative-packet/`: give only `participant/`
to an actual intended analyst. Keep `facilitator/`, its actual reference reports
and blank observation template separate. A participant recovery project contains
an actual unsuccessful attempt without the facilitator's reference answers.
The packet binds the candidate receipt,
host and file hashes. It asks the analyst to inspect invented inputs, derive and
compare an assumption, investigate reduced sampling, recover a failure and
reopen moved work after replacement. The facilitator records first answers,
assistance, critical interpretation errors, blocked work and retries. Directory
separation is not access control.

No user session, independent recipient, installation-usability finding or
productivity improvement follows from these technical materials. Signing,
notarisation, clean-host installation, other-platform qualification, native
packaging, broader reader transitions and public release remain open. Software
and numerical checks do not establish biological validity or human sampling
equivalence. The [roadmap](../ROADMAP.md) owns the subsequent work.

## Explicit M3-era comparison successor

The current source adds the separately selected
[exact successor packet](decisions/0092-exact-m3-reader-successor.md). The original
version-1 registry is byte-preserved. A version-2 packet pins one complete current
reader and admits only A, the exact historical B reader including its original
policy digest, and the exact MMTT comparison identity computed from
`6e77f7b86d3418ac5702dfb1efdd0edf68cabd90`. The latter is a generic MMTT comparison
frozen during M3 development; this is not migration of M3 forecasts or native
M4/connected studies. Unknown predecessors, altered helpers and every non-reader
definition field remain refused. Original report/definition bytes and project
inventories remain unchanged; the operation receipt names the actual transition.

For a newly built version-2 successor, explicitly add
`--reader-policy opent1d.comparison-reader-transition/2` to the qualification
command above. The default keeps the original literal version-1 assertion for
historical A-to-B reproduction. The version-2 mode extracts the packet from the
hash-verified successor wheel and binds its complete reader, packet digest,
historical registry and exact M3-era predecessor. It reports qualification
schema 2; it never relabels an old version-1 receipt. The original task,
failure/cancellation, saved-prefix, relocation, rollback and constant-input
controls still run. Additional retained B/M3-era comparisons need their own
installed source-bound replay evidence, not a declaration that a root check
qualified a wheel. Final exact artifacts and receipts belong to the associated
CI integration PR; distribution and native qualification remain separate.
