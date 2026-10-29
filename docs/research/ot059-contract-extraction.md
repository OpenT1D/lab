# OT-059 contract and extraction packet

## Problem and change

The [shared-core extraction queue](../../ROADMAP.md#shared-core-extraction-queue)
needs a reviewable contract before services are extracted from existing routes.
Ten registered tasks currently retain different scientific payloads, source
inventories and trusted readers. This increment inventories those boundaries
and freezes the smallest metadata contract exercised by `m4-study-secure` and
`mmtt-sensitivity`.

## Scope and contracts

The integration owner writes the packet, descriptors, fixtures, validation and
canonical English documentation. One read-only GPT-6.1 Sol reviewer (xhigh)
investigates the existing contracts and separately reviews the final diff.
This follows the repository proposal/PR template; no remote issue number is
implied. Base revision: `5d0c3d1950ecfc7500133f76c1ed98afa8016e76`.

Reuse authoritative intake, source inventories and readers. Preserve scientific
payload bytes, ancestry, units, compartments, clocks, causal availability,
process ownership, planned denominators, all attempts, baselines and tolerances.
Separate schema, method, metric, runtime and reader identities, and execution,
completeness, reconstruction and scientific evidence states.

M4 uses both existing example sources under `fasting`, then a derived plan for
`gastric_load_15g`; its horizon, grid, numerical gates and reference remain
unchanged. MMTT uses one invented visit pair and all three required variants.
Cross-check the sampled control and continuous RHS families without claiming
interchangeability. Families remain provisional until a second native engine
exercises them.

Excluded: route migration, an installed SDK, a universal stepping API, new
scientific mechanisms, native environment installation, Windows installer work
and independent-user acceptance. The later family usability exercise is a
separate gate.

## Acceptance and counterexamples

- Inventory exactly the ten registered routes, runtime locks, scientific/source
  identity providers and reader dependencies, including MMTT's absence from the
  historical-reader helper.
- Validate shared descriptors and their links to unchanged native payloads;
  reject changed bytes, unsupported versions, mismatched lineage, missing
  planned slots and incompatible family semantics.
- Retain concrete positive, refused, failed and relocated reference cases.
  Exercise passive M4 admission and a controlled failed native launch without
  installing its runtimes; do not label these native numerical success.
- Execute and reconstruct the standard-library MMTT fixture, including an
  incomplete case and relocation. Require explicit failed-archive admission.
- Publish an extraction map and layered quality matrix identifying downstream
  OT-060/061/064 work and separate native/scientific/human gates.

## Evidence

Before implementation: clean detached worktree at the base revision; created
`codex/ot059-contract-extraction`. Targeted checks below used that revision plus
the uncommitted packet/docs/test changes. Existing scientific implementation,
protocol, lock, baseline and tolerance files were unchanged.

Local environment: macOS Apple Silicon, CPython 3.12.13, uv 0.11.16 and Node
22.22.2. Root setup `uv sync --locked` passed after allowing access to its
existing cache. An earlier sandboxed attempt could not access that cache; a
temporary-cache attempt could not resolve package downloads. Neither installed
a native simulation runtime.

| Command / check | Observed outcome |
| --- | --- |
| `uv run --locked python -m unittest tests.test_shared_contract_packet tests.test_m4_causal_secretion tests.test_p1_external -v` | Initial 18 tests passed; preserves existing RHS/controller negative controls. |
| `uv run --locked python -m unittest tests.test_shared_contract_packet tests.test_m4_secure_study tests.test_observation_workflow tests.test_historical_readers -v` | Initial 34 tests: 33 passed; the historical SIGTERM process-inspection case hit sandbox denial of `ps`. This was an environment failure, not a passed process check. |
| `uv run --locked python scripts/check.py --stage style` | Passed before review fixes; full final check repeats style on the final tree. |
| `uv run --locked python -m unittest tests.test_shared_contract_packet -v` | Final 11 packet tests passed after review fixes, including rehashed metadata counterexamples. |
| Reviewer checks | Initial inventory/native-intake controls 2/2 passed; five focused checks and all three original counterexamples passed after fixes. |

Targeted uv commands used a writable temporary cache where needed. The
integration owner is the sole full-suite owner. The final locked setup/check
uses ordinary process inspection permissions and retains its exact revision,
dirty state, exit outcome and log under local ignored `results/ot059/`:

```sh
uv sync --locked
uv run --locked python scripts/check.py
```

Read the final receipt/log for the outcome; this tracked record does not
anticipate a pass or represent a hosted CI receipt. Final source changes need
another full-check receipt. No historical native installation is authorized
by this packet; the public runtime boundary remains in force.

## Limitations and impact

This is an internal contract/extraction artifact, not shared service migration,
native parity evidence, a release, biological validation or independent user
acceptance. Substantial AI assistance is explicit in the ownership above.

## Review handoff

The read-only reviewer inspected all new code, fixtures and documentation plus
the tracked diff against the base revision. Three P2 findings were reproduced
on disposable copies and resolved:

- A rehashed report could change its native MMTT method/schema/settings without
  losing the shared-plan association. Admission now binds the native envelope,
  method, settings, runtime and planned coverage to retained inputs/bindings.
- A POSIX-relative `C:/outside.json` could become a drive path under Windows
  joins. Admission now rejects colon/drive/ADS/NUL before host joins and reuses
  regular-file/reparse checks. The path counterexample was lexical; it is not
  a Windows-host execution result.
- Rehashed interrupted/censored attempts could claim complete slots. Admission
  now requires the exact native participant/variant or source/scenario status
  projection; unavailable and failed slots cannot be promoted to complete.

The reviewer repeated the original counterexamples after correction and found
no remaining issues within that scope. Reviewed SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `experiments/shared_contracts/core.py` | `b8fce40971b8bb056f2d5dc39440c7f13856640bb40ad76e6561e812e8f4278b` |
| `experiments/shared_contracts/selected.py` | `96adb642bdb2fe16c3929ccbe6fb1275c3643ffe0e62dfcec7491e078be0dc12` |
| `tests/test_shared_contract_packet.py` | `14e9a1e0dbf750199367a9c7df1a1c8bcdf71fcac2e1717ed68ec481335606e8` |

Agent review establishes a separate technical review, not independent human or
scientific validation. The [contract guide](../shared-core-contracts.md) owns
the extraction map and layered quality matrix. Next gates are minimal shared
OT-061/064 services, then installed OT-060 use; native M4 success/complete
relocation in an explicitly reviewed environment, second-engine conformance,
reader upgrades and host lifecycle evidence remain open. Windows installer
completion and the later family/intended-user exercise are separate and do
not block this packet.

## Critical double-check of the committed packet

On 29 October, the user requested a further independent review with two agents.
Both read-only GPT-6.1 Sol reviewers used xhigh reasoning on clean revision
`c5337a3160341812769d361074fb4351fbf0c14d`. One challenged metadata admission
with rehashed counterexamples; the other compared the inventory and scientific
claims directly with native entrypoints/readers. The integration owner remains
the only writer and full-suite owner.

Four bounded correction groups were confirmed before further changes:

- Native report and execution statuses could disagree; M4 acceptance summaries
  could additionally contradict unattempted source/status records.
- MMTT runtime records could disappear on both sides or become identical
  arbitrary strings. The correction requires the existing native runtime shape,
  without comparing a saved runtime to the review host.
- M4 report source provenance and its native execution-contract object could
  disagree with the shared frozen binding.
- Declared native source inventories omitted known reader import dependencies.
  A disposable change to `experiments/m3/workflow.py` broke both M3 reader
  entrypoints while the original inventory drift check still passed. Additional
  static reader dependencies must include actual package entrypoints and parent
  initializers, without changing frozen native source lists. M5's existing
  current-tooling-lock reader equality gate also needs explicit documentation.

Acceptance requires refusing these rehashed contradictions while retaining
unchanged complete/incomplete/interrupted controls and relocated readers. The
reader inventory must detect helper and implicit package-initializer changes.
These are metadata/identity corrections; numerical arithmetic, native protocols,
scientific baselines/tolerances and the public installation boundary stay intact.
Focused regressions, both reviewers' fix checks and a fresh full repository
receipt on the final integrated revision are required after correction.

All four correction groups are implemented and separately re-reviewed. The
contract reviewer repeated the original rehashed cases, including promoted
unattempted M4 slots; each now fails for its intended consistency reason.
Unmodified complete, incomplete, interrupted and relocated controls still pass.
The saved-runtime check deliberately accepts a well-formed record from a
different host. It does not authenticate that observation or compare it with
the reconstruction host.

The inventory reviewer repeated the original disposable M3 helper failure:
the unmodified inventory matches its frozen metadata, while the helper change
now changes both M3 reader inventories. All locally loaded modules from all ten
actual `-B -S` reader imports are represented. A separate passive fixture also
covers transitively imported parent initializers. Static imports from mixed
read/run modules include lazy execution branches; dynamic imports, external
packages and supplied-code dependencies remain explicit exclusions.

Final targeted packet checks: 14 tests passed. Against the previous
`selected.py` implementation, the two new admission regression methods produced
seven assertion failures and no import/runtime errors; the same checks pass
after correction. The contract reviewer independently ran all 14 tests; the
inventory reviewer ran three selected controls and its disposable import/drift
and package-parent probes. Both report no remaining actionable findings within
their scope. These are local agent reviews, not independent human/scientific
acceptance.

| Corrected file | Separately reviewed SHA-256 |
| --- | --- |
| `experiments/shared_contracts/selected.py` | `8939d223b06e80bc01707087a88339b4a889b63573fd2173ccf6d9b2524cb559` |
| `experiments/shared_contracts/inventory.py` | `5ea157dd0521b05dea60625914fc4acb689d895ffc8facc27accdd997c1f5cea` |
| `experiments/shared_contracts/route-inventory.json` | `44a1ea37b2685b1162550df3e997672251e2ee2c1b82ec3603b14f451481eb7d` |
| `tests/test_shared_contract_packet.py` | `2beb2b08218cbd5f3a98ac5044aea1ee893728dcf5b381b7cb3eb5903bee664e` |

The original `results/ot059/final-receipt.json` remains the unchanged receipt for
`c5337a3`. The integration owner's new full check after committing these
corrections retains its exact revision, dirty state, skips, command outcome and
log under local ignored `results/ot059/doublecheck-final-receipt.json`. The
retained targeted and old-behavior logs are alongside it. This record does not
anticipate that new full-check result. Native science inputs, protocols,
baselines and tolerances remain unchanged; the same native and external gates
remain open.
