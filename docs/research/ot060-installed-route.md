# OT-060 installed two-route developer slice

## Problem and change

[Increment 2](ot061-064-minimal-services.md) provides project services inside a
checkout. The [next extraction increment](../../ROADMAP.md#shared-core-extraction-queue)
needs separately installed Python and CLI entry points that preserve native
scientific identities, reports and all attempts outside that checkout.

## Scope and contracts

Base: `650db8b078abfb8185442ee19360c2f5b421aebb`, the actual merge of
[PR 29](https://github.com/OpenT1D/lab/pull/29). The integration owner writes on
`codex/ot060-installed-route`; two read-only reviewers investigate and separately
review storage/readers and lifecycle. Root is the sole full-check owner.
[Decision 0082](../decisions/0082-installed-source-payload.md) defines the new
installed boundary.

Build a dependency-free internal wheel containing an explicit source/data
closure in its original layout, preserving native source/protocol/ancestry/lock
bytes. Reuse the project store, dispatch contracts, owned process helper and
native readers. A process-proxy API and isolated CLI keep scientific modules
out of the caller's Python namespace. Do not turn root tooling into a simulator,
redirect legacy ROOT values, fake a desktop manifest or install native runtimes.

Preserve the selected MMTT visit pair, three variants, 128 draws and seed 117;
M4 retains both source pairs, fasting/derived 15 g, adult#001, 240 minutes and
961 quarter-minute samples, with unchanged native numerical gates. Native M4
execution remains explicitly unavailable under the current public policy.
Passive intake, forensic refusal and trusted reading of matching failed evidence
are supported; these do not close native success/parity/complete relocation.

## Acceptance and counterexamples

- Build and non-editably install into fresh CPython 3.12 environments. From an
  unrelated directory create, validate, freeze, run, retry, move and reconstruct
  a MMTT project with identical authoritative reports and original ledger.
- Admit both M4 fixture plans, retain its explicit native-policy refusal, and
  reconstruct matching failed native evidence without setup or Git.
- Keep exact reader inventories and opaque snapshots. Opening/importing never
  executes archived Python. Record complete/incomplete/interrupted outcomes,
  all original denominators and unavailable forensic evidence separately.
- Exercise the isolated launcher under poisoned cwd/PYTHONPATH/sitecustomize,
  fake uv and fake checkout environments; only the identified installed payload
  and current admitted interpreter may run. Preserve owned cleanup and unrelated
  processes on the claimed host.
- Test an actual installed wrapper-build A to B transition with unchanged native
  reader bytes, then refusal of a deliberately incompatible reader candidate.
  No general upgrade, other-host, release or human acceptance follows.

## Evidence and review handoff

Select checks from the development map: original project/packet and native-reader
regressions, new installed-artifact tests and the integration owner's final
`uv sync --locked` / `uv run --locked python scripts/check.py`. Retain actual
wheel identities, exact source/dirty state, commands, outcomes, failures and
skips under local ignored `results/ot060/`. A clean build is required for the
formal artifact; dirty builds are explicit development fixtures only.

Before implementation, a separate source-layout probe captured 191 original
files/1,680,344 bytes and successfully ran native standard-library MMTT and both
selected readers outside the checkout, with byte-identical reports and inert
poisoned cwd/PYTHONPATH. That was a source-data probe, not a wheel or native M4
success. The final record will separate installed software checks, current-main
hosted results and remaining native/scientific/host/upgrade/human gates.

## Implemented developer checks

The selected macOS arm64 host uses CPython 3.12.13 and uv 0.11.16. The initial
installed exercise used a copied wheel in a fresh virtual environment outside
the checkout, with an unrelated cwd and poisoned environment/module/tool
lookups. It performed actual MMTT execution, retries, report reconstruction and
project relocation; authoritative report bytes matched. No native runtime was
installed. A separately identified source/data layout probe precedes that wheel
evidence and is not substituted for it.

`tests/test_installed_sdk.py` builds and non-editably installs two wheels with
different wrapper-build descriptors and identical native reader bytes. Its
checks cover complete/censored MMTT, a source-controlled interrupted native
archive, actual B retry of A's frozen plan, byte-exact B reconstruction after
relocation, and original A versus current B application provenance bound to the
actual installed manifests. Both M4 plans retain their source pairs and
derivation; explicit execution records policy refusal with unavailable slots.
Matching controlled failed M4 evidence reconstructs its report/figure bytes.
These failed cases are not successful native M4 execution.

An unchanged copied candidate first opens the project successfully; changing a
native reader then refuses on frozen source identity without changing the
project head. This positive control prevents an unrelated environment-path
refusal from masquerading as reader compatibility coverage. The two internal
wrapper builds are bounded fixtures, not two public versions or a broad upgrade
matrix. Python API calls leave scientific modules out of the host namespace.

The separate reviewers found and rechecked the following defects before final
handoff; permanent adverse tests retain the affected cases:

- Facade bytecode could be read without manifest validation. The isolated CLI
  now uses an independent cache prefix before imports; a valid-header stale
  facade cache stays inert while the CLI succeeds.
- Fresh outputs inside an existing project could corrupt its store. Creation,
  example export, reconstruction and relocation now refuse any such destination
  before writes, including another project's descendants.
- A facade edit after the builder's source snapshot could be packaged under
  incorrect clean provenance. All staged inputs now match that snapshot and the
  final source inventory must still match. A disposable clean Git fixture
  reproduces the race and requires refusal before a successful receipt.
- Special-file reads could block verification; bounded nonblocking regular-file
  checks now reject a FIFO promptly. Bootstrap/validator reads use verified raw
  bytes rather than rereading executable source after validation.
- A failure constructing process ownership could leave descendants alive. The
  client retains live session cleanup and independent direct-child reaping;
  a real controlled tree fixture verifies root/child cleanup while an unrelated
  process remains alive. A reaped numeric process group never becomes fallback
  authority.
- The first full local check ran 1,740 tests with 32 skips and one failure in
  installed cancellation. The original observer could select a transient
  inherited-group `uname` child during platform metadata collection, before
  native supervision. The corrected native-phase probe requires the attempt
  worker log and a freshly checked child session. It passed five fresh-build
  repeats. This also exposed a real early-cancellation gap: the broker could
  terminate during project publication before its inner supervisor installed
  handlers. The broker now queues a run-scoped cancellation event before
  dispatch and through sealing, then skips native launch and seals an
  interrupted forensic attempt if cancellation is already queued. A separate
  installed trusted trace harness injects a real SIGTERM at `begin()` entry;
  it requires a cleanly reopenable terminal attempt, unavailable slots and no
  worker launch. The original failed full-check log is retained, not counted
  as a pass.

The installed cancellation probe uses the real installed broker/native commands
and unchanged source/input bytes. A trusted test observer start-validates and
temporarily stops its live native child, sets the real cancellation event, then
resumes that same child after signal forwarding. The attempt seals as
interrupted, observed owned cleanup is empty and an unrelated process survives.
This is controlled stop/resume evidence, not a particular numerical-phase
interruption. The original service regressions separately exercise controlled
native MMTT signal interruption, deadlines, nested ownership and explicit
retries. Imported interrupted SDK evidence proves its reader path. General host
lifecycle qualification remains separate.

## Integration and final handoff

Increment 2 was merged as PR 29 at
`650db8b078abfb8185442ee19360c2f5b421aebb`. Actual main runs
[Repository checks 40917010373](https://github.com/OpenT1D/lab/actions/runs/40917010373)
and [CodeQL 40917010665](https://github.com/OpenT1D/lab/actions/runs/40917010665)
succeeded. Those hosted results qualify that integrated base, not this later
installed candidate or native simulation validity.

The integration owner's ignored `results/ot060/` retains development and final
logs separately. The final receipt binds the clean source revision, clean wheel
receipt/SHA-256, outside-checkout installation/exercise and actual root-check
results. `installed-reviewed.log` records the installed regression selection;
`reviewed-targeted.log` retains the earlier exact-reason assertion failure,
followed by its correction. `final-check.log` and `final-receipt.json` are the
authoritative final local check handoff. A local pass does not claim a hosted
pass. The canonical [installed guide](../installed-sdk.md) owns user commands.

Native M4 success, parity and complete installed relocation remain open under
the reviewed public runtime boundary. Other OS qualification, general reader
upgrades, publication/distribution, independent usability, human-data evaluation
and biological validity remain separate gates. The developer candidate does
not close the full increment-3 exit or OT-060/061/064 packages.
