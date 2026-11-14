# Minimal shared project services

Extraction increment 2 adds internal services for `mmtt-sensitivity` and
`m4-study-secure` around the existing task workers and authoritative readers.
[Decision 0081](decisions/0081-minimal-project-services.md) defines the storage
and process boundary; the [task/evidence record](research/ot061-064-minimal-services.md)
owns its acceptance cases. The [OT-059 packet](shared-core-contracts.md) remains
the unchanged metadata reference. This initial extraction was developer software
in a checkout. The subsequent [installed SDK](installed-sdk.md) and
[shared workbench](installed-gui.md) now expose the same project services.

The bounded [sampling extension](research/installed-mmtt-sampling.md) adds
`experiments/shared_services/sampling.py` as a separate adapter under
[decision 0085](decisions/0085-installed-mmtt-sampling.md). It captures four raw
files and the sealed development import, retains schedule/person/variant slots,
and admits associated native parent/child reports with their saved draw ledgers.
Explicit reconstruction remains the trusted arithmetic check. Parent and all
available child report hashes survive relocation. The installed descriptor is
version 3; the OT-059 version-1 packet and original service evidence below remain
unchanged. The installed M4 successor retains its separate guide and evidence.

## Project and immutable history

`experiments.shared_services.store.create` creates a fresh project.
`store.opened(..., write_access=True)` holds an exclusive POSIX file lease for
each mutation and execution. Readers hold a shared lease. Concurrent writers
are refused. The first tested service host is local Apple Silicon macOS; the
code admits POSIX hosts, while Linux service qualification and Windows service
support remain unverified. Existing host smokes qualify their own boundaries.
Project objects expire when their `opened` context exits. Retaining an object
does not retain authority to read, execute, export or mutate it; reopen it under
a new lease. Invalid attempt modes and foreign/finished workspaces refuse
before event publication or cleanup can alter assets.

The project contains `HEAD.json`, `events/`, `work/`, `pending/` and `.lock`.
Every event has a consecutive sequence number, previous-event identity and
complete sealed file inventory. The committed head binds the event count and
tip. Opening checks the complete roster, chain, regular files, native plan
association, snapshots, retry ordinals and terminal outcomes. Missing last
events, extra/duplicate events, swapped directories and changed asset bytes
are refused. There is no API for pruning or replacing an attempt. Checksums
detect inconsistencies against the retained head; they do not authenticate a
store against someone rewriting its entire history and every checksum. Keep
independent project copies for disaster recovery and externally anchored
provenance when needed.

`routes.freeze` captures exact original inputs, native source/protocol/lock
identities and reader snapshots. Derivation supplies a prior `parent` plan ID;
the original plan remains immutable. The selected M4 fixture retains its
original config bytes and a separate effective config with project-relative
source paths. Source/declaration bytes remain exact. Native reports bind that
effective config, and the shared freeze binds both forms. The two existing
Dalla Man/ultradian example pairs are the admitted M4 sources in this increment.
MMTT uses its existing sealed native plan without scientific conversion.
Only public synthetic fixtures are admitted; private references, permissioned
handoff and support-bundle export are still separate OT-064 work. The bounded
[developer diagnostics](#developer-diagnostic-export) below export counts only.

An event is published with the existing atomic exclusive directory primitive,
followed by a flushed head replacement. A power loss or forced termination
between those operations can leave pending or extra event evidence. Opening
fails closed and preserves it; automated journal repair is not implemented.
An unfinished registered execution can reopen as unfinished and be explicitly
recovered after execution is confirmed stopped. Recovery never adopts or
signals a persisted PID. A committed terminal event whose duplicate live
workspace was not removed is also refused pending forensic inspection.

## Developer diagnostic export

From a checkout, use the locked root environment to summarize an existing valid
synthetic project into one fresh JSON file outside that project:

```sh
uv run --locked python scripts/export_project_diagnostics.py \
  --project /absolute/path/to/project \
  --output /absolute/path/to/new-diagnostics.json
```

The version-1 report contains only fixed exporter/report/store schema identities,
supported task types, plan and attempt counts, plans without attempts, and counts
grouped by process status, result execution status and completeness. Process and
result status remain separate: a failed coordinator can retain a complete native
result, and a completed process can produce incomplete scientific evidence.
A durable start without a finish counts as `unfinished`, with `unknown` result
status and completeness. It does not prove a currently running process.
Retries and unfinished attempts remain in the totals.

The tool opens the current shared project store with `write_access=False` and
holds its shared read lease through publication. Existing ledger and native
binding validation must succeed; the source bytes remain unchanged. Project
names, local paths, host records, inputs/observations, supplied model code,
scientific reports, identifiers, free-text logs and error text are omitted.
It runs no task, model callback, reader reconstruction command or recovery;
existing validators retain their passive checks. This summary neither verifies
scientific conclusions nor transfers a reconstructible project.

Invalid, corrupt, unknown, incompatible or writer-locked projects are refused
with the fixed stderr category `project_refused`. Unsuitable destinations,
including linked ancestors, locations inside the project and existing outputs,
use `output_refused`; a non-POSIX host uses `unsupported_host`. Refusals exit
nonzero without publishing a successful report. Output parents must already
exist. A complete staged file is published exclusively, so an existing or newly
appearing destination is never overwritten. Success exits zero without printing
project details. The first local host is macOS using the existing POSIX store;
this adds no Windows support or distribution qualification. There is no fallback
parser, migration or repair. LT1 review bundles, permissioned handoff and broader
OT-064/073 distribution work remain separate.

## Synthetic diagnostic support handoff

This prepared OT-064/073 exercise uses the existing version-1 diagnostic JSON
for `mmtt-sensitivity` and `mmtt-sampling` on the current trusted checkout.
The first local host is Apple Silicon macOS. It prepares a sender/recipient
handoff and tests software accounting; no actual recipient session, independent
usability result or scientific validation is recorded by this preparation.
The exporter, store schema and shared interfaces are unchanged.

The [non-blind AI control](research/ot064-073-diagnostic-ai-control.md) records
fifteen accounting matches on the prepared JSON packet. The reviewer had prior
implementation/reference knowledge; the human recipient exercise remains open.

### Prepare the controlled cases

From the checkout with the locked root environment, choose a fresh scratch
directory outside projects and the checkout, with an existing parent:

```sh
uv run --locked python - <<'PY'
from pathlib import Path
from tests.test_project_diagnostics import prepare_support_handoff

root = prepare_support_handoff(
    Path("/private/tmp/mmtt-diagnostic-support").resolve()
)
print(root / "recipient")
PY
```

This is a developer test-fixture recipe, not an installed SDK command or a
general project mover. It creates only new invented fixtures. Preparation runs
the unchanged standard-library MMTT analyses and uses controlled coordinator
receipts for complete, incomplete, failed and interrupted cases. Those receipts
do not demonstrate actual process interruption. No physiological runtime is
installed. The unclosed starts are constructed with no running worker.

The helper exports each fixture, copies it under a shared read lease, checks
complete inventories, then removes its own original projects and input
directories. It exports the relocated fixtures again and requires identical
JSON and unchanged project inventories. Execution, analysis, reconstruction and
recovery entry points are guarded during both export phases. The trusted
checkout and its matching reader bindings remain available.
This fixture-only copy does not extend `Store.relocate`: that production method
still refuses unfinished attempts. No application upgrade or wider historical
reader compatibility follows from the exercise.

Successful preparation produces fifteen files, `case-A.json` through
`case-O.json`, in `recipient/`. Existing output directories are refused.
Use the packet only after preparation exits successfully with all fifteen
files. Retain an incomplete preparation for inspection and choose a new scratch
directory for another attempt.

The `sender/` directory retains the relocated projects and the before-relocation
JSON. It contains frozen inputs, logs and other evidence excluded from the
diagnostic. Copy **only `recipient/`** to the recipient's separate location,
along with the questions below. Keep the sender directory and reference key
separate until first answers have been recorded. Directory separation alone is
not access control, and these published deterministic cases are not a blinded
empirical study.

### Questions for the recipient

Read only the supplied JSON files. For each case:

1. Record the reported task, frozen-plan count, attempt count, plans without
   attempts and every outcome count. Distinguish a valid empty report from an
   absent file; absence is not a zero-attempt result.
2. Identify process completion with incomplete evidence, recorded failures or
   interruptions, unclosed starts and plans that have never started an attempt.
3. Explain which reports retain both a failed and a complete attempt. State
   whether their order or the identity of the latest attempt is available.
4. State what cannot be concluded about current process liveness, failure cause,
   host/application compatibility, report authenticity and scientific validity.

`unfinished` records a start without a finish; it does not prove a running
process. A `completed` process does not imply complete evidence. A diagnostic
contains no scientific report and cannot reconstruct an analysis. It omits
identifiers, ordinals, free-text errors and local provenance. It is not a signed
attestation or an independent verification of the producer's source project.
If an export was refused, ask the sender for its fixed refusal category rather
than interpreting a missing JSON file as an empty project.

### Sender reference key

All files use `opent1d.project-diagnostics/1`,
`opent1d.export-project-diagnostics/1` and `opent1d.project-store/1`.
In each paired case below the first letter is `mmtt-sensitivity` and the second
is `mmtt-sampling`. Case A has no task row.
Outcome notation is `process_status / execution_status / completeness × count`.

| Cases | Frozen plans | Plans without attempts | Attempts | Expected outcomes |
| --- | --- | --- | --- | --- |
| A | 0 | 0 | 0 | No task row or outcomes |
| B, I | 1 | 0 | 1 | `completed / completed / complete × 1` |
| C, J | 1 | 0 | 1 | `completed / completed / incomplete × 1` |
| D, K | 1 | 0 | 1 | `failed / failed / incomplete × 1` |
| E, L | 1 | 0 | 1 | `interrupted / interrupted / incomplete × 1` |
| F, M | 1 | 0 | 1 | `unfinished / unknown / unknown × 1` |
| G, N | 1 | 1 | 0 | No outcomes |
| H, O | 1 | 0 | 2 | `completed / completed / complete × 1` and `failed / failed / incomplete × 1` |

F retains a partial workspace; M has no workspace. Both correctly retain the
unclosed start. H and O are constructed as an explicit successful retry after
a failed attempt on the same plan. The JSON retains both counts but does not
encode their order or retry linkage. The sender key supplies that construction
history; it cannot be inferred from outcome ordering in the JSON.
Case A reports no frozen plans; it says nothing about available task capabilities
or separate GUI drafts.

The four `DiagnosticSupportHandoffTests` in
`tests/test_project_diagnostics.py` compare all fifteen reports with a literal
accounting oracle, require byte-identical JSON after original paths disappear,
check the recipient file roster and omission controls, preserve the production
unfinished-relocation refusal, and refuse reuse of an existing preparation.
Run the complete diagnostic family with:

```sh
uv run --locked python -m unittest tests.test_project_diagnostics -v
```

The actual human recipient exercise remains **open and unrun**. No first human
interpretation answers, case-assistance observations or participant task times
have been recorded. When a recipient is available,
record their first answers, assistance, errors and actual elapsed time before
revealing the key. Keep unanswered or blocked cases and corrections in that
record. Fixture generation and an internal technical review cannot stand in
for that observation or qualify a wider support/distribution scope.

## Developer example

Use the locked root environment. Run this Python from the checkout, choosing
fresh absolute project and reconstruction paths outside disposable installs:

```python
from pathlib import Path
from experiments.shared_services import execution, routes, store

fixtures = Path("experiments/shared_contracts/fixtures").resolve()
project_path = store.create("/absolute/path/to/project", "invented paired study")
with store.opened(project_path, write_access=True) as project:
    plan = routes.freeze(project, "mmtt-sensitivity", {
        "package.json": fixtures / "mmtt-package.json",
        "observations.csv": fixtures / "mmtt-observations.csv",
        "settings.json": fixtures / "mmtt-settings.json",
    })
    attempt = execution.execute(project, plan, timeout=600)
    execution.reconstruct(project, attempt, "/absolute/path/to/rebuilt-report")
    project.relocate("/absolute/path/to/portable-project")
```

A retry must explicitly pass `retry_of=attempt`; it creates another registered
attempt. `routes.import_attempt` passively copies an existing native archive
that matches a frozen plan. Neither opening nor importing starts a worker,
setup command or archived Python. Imported results remain unchecked until the
explicit trusted reader succeeds. A refused input does not publish a freeze.
Passive native intake requires completed MMTT's own frozen plan and full raw
draw/variate ledger, and binds failed/interrupted admission to the shared plan
and original package. Incomplete failed snapshots remain admissible with that
retained admission. M4's own frozen scientific source/declaration pairs must
match the shared freeze as well as its report. Descriptive ledger/report
consistency is checked during intake; the explicit reader still performs full
arithmetic replay. Resealing a structurally incomplete or swapped native payload does not
make it admissible.

## Execution and failure accounting

`execution.execute` registers a start before admission or launch. Runtime
checks are passive and reuse the existing task selection. Missing M4 runtimes
produce a failed forensic attempt without setup or numerical execution. An
admitted worker uses the existing dispatch command, trusted checkout working
directory and filtered environment. M4 execution and reconstruction each use
a separate process, preserving its non-thread-safe activation boundary.

An optional cancellation event, a handled TERM/INT/HUP or the deadline asks
the native coordinator to stop. Thirty seconds allow its own sealing and
cleanup; the outer owner then cleans remaining observed descendants using
live OS start identities, including separately sessioned children. A process
created and orphaned entirely between observations, an uncatchably killed
outer owner and hostile process escape are outside this polling guarantee.
Process isolation is not a hostile-code or network sandbox. An importing or
reading operation never authorizes supplied scientific execution.

Terminal events retain stdout, admission, process observations, native files
and partial forensic evidence. A surviving owned process prevents terminal
sealing. A hard-stopped or unavailable worker gets no fabricated native
report: all planned slots remain unavailable and native reconstruction is
explicitly unavailable. `execution.recover(..., execution_stopped=True)` seals
an unobserved previous execution as interrupted forensic evidence after that
explicit attestation; partial bytes remain intact.

The process receipt and native execution status are separate. A worker can
exit nonzero after writing a completed but scientifically incomplete MMTT
analysis. The native result retains every required variant and all planned
draws/visits. Completeness, recorded reconstruction and `synthetic-only`
scientific evidence cannot be promoted by process completion. Successful
reconstruction adds its own immutable ledger event linked to the attempt and
original report hashes. Native payloads remain authoritative.
Reader verification also requires a zero exit code and an observed empty
owned-process set; incomplete or unknown cleanup cannot publish verification.

## Reader and compatibility matrix

| Project / native evidence | Trusted reader and required identity | Admission and current evidence |
| --- | --- | --- |
| Store schema `opent1d.project-store/1`; MMTT plan/report version 1 | Fixed `experiments.observation_analysis` entrypoint. Exact current native implementation, protocol, ancestry, runtime-file selectors and additional static reader dependency inventory. | Complete, completed-but-incomplete and signalled interrupted MMTT reconstruct after project relocation with identical `report.json` and `report.md`. Exact execution runtime is required for execution, not comparison to a historical reader host. |
| Same store; maintained M4 config/run/report version 1 | Fixed `experiments.m4.secure_study` entrypoint in a separate process; exact retained reader/source inventory plus the native frozen protocol/lock/path-set and runtime-attestation gates. | Two-source fasting/derived 15 g intake and controlled failed-reference relocation reconstruct byte-exact JSON/Markdown/SVG with explicit failure admission. Complete native M4 execution/relocation remains unverified for this service. |
| Failed or incomplete native archive | Same matching trusted reader; `allow_failed=True` required. | Refused without that flag; all planned denominators stay present. |
| Forensic workspace without an admissible native report | No invented reader path. | Retained and relocatable after terminal recovery; native reconstruction unavailable. |
| Different reader/schema/implementation/protocol/ancestry or selected lock | No automatic upgrade, download or archived-code fallback. | Refused. A retained matching trusted checkout is required; supported upgrade transitions belong to increment 3 and later OT-064. |
| Other host/application version | No compatibility implied by directory portability. | Only the tested local macOS service behavior is claimed. Other host, clean-install, upgrade, installer and intended-user gates remain open. |

Both selected routes retain native source snapshots plus the additional OT-059
static reader inventory, including package entrypoints and parent initializers.
These files are opaque provenance, never executable reader instructions.
The historical-reader helper supports neither MMTT route. Reconstruction uses
the fixed trusted current reader and preserves all its stricter gates; it does
not load a module, interpreter, working directory or environment from metadata.
Snapshots alone cannot authorize an implementation upgrade.

Run `uv run --locked python -m unittest tests.test_shared_services -v` for the
bounded service checks. The integration owner also runs the full repository
check. These checks establish software behavior on synthetic fixtures, not
native M4 parity, biological validity or independent usability.
