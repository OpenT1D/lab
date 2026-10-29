# Minimal shared project services

Extraction increment 2 adds internal services for `mmtt-sensitivity` and
`m4-study-secure` around the existing task workers and authoritative readers.
[Decision 0081](decisions/0081-minimal-project-services.md) defines the storage
and process boundary; the [task/evidence record](research/ot061-064-minimal-services.md)
owns its acceptance cases. The [OT-059 packet](shared-core-contracts.md) remains
the unchanged metadata reference. This is developer software in a checkout;
an installed SDK/CLI and GUI migration belong to later increments.

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
handoff and support-bundle export are still separate OT-064 work.

An event is published with the existing atomic exclusive directory primitive,
followed by a flushed head replacement. A power loss or forced termination
between those operations can leave pending or extra event evidence. Opening
fails closed and preserves it; automated journal repair is not implemented.
An unfinished registered execution can reopen as unfinished and be explicitly
recovered after execution is confirmed stopped. Recovery never adopts or
signals a persisted PID. A committed terminal event whose duplicate live
workspace was not removed is also refused pending forensic inspection.

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
