# Internal installed M4 candidate

`m4-study-installed` is an explicit execution successor with separately reviewed
native, observer and build locks. It reuses the original equations, source
examples, parameter identities, units, solvers, grid and numerical criteria.
The historical `m4-study-secure` task keeps its own identity and installation
exclusion. Original projects/attempts remain data that matching trusted readers
can reopen. No historical lock is relabelled or patched in place.

This is an internal candidate. The [verification record](research/ot060-native-m4.md)
owns actual execution/parity/relocation results and outstanding gates. The
initial maintained public exercise remains the two MMTT tasks. Public native
bundling, parameter/table redistribution, other hosts, independent user use and
biological validity require separate evidence.

## Prepare the exact candidate dependencies

Use the selected source revision and root tooling, then choose a fresh canonical
absolute output path. The preparation command validates the dated policy,
complete dependency review and six selector hashes before creating output or
launching an installer:

```bash
uv sync --locked
uv run --locked python scripts/prepare_m4_runtimes.py \
  --output /private/tmp/opent1d-m4-dependencies
```

The receipt identifies the actual native/observer/build directories, complete
installed distributions, upstream commits and process outcomes. Native has
NumPy 1.26.4/SciPy 1.13.1; observer has NumPy 2.2.6/SciPy 1.15.3. The separate
directories preserve the incompatible environments. Installation is explicit;
checking, opening and running a project never installs dependencies.
The [runtime protocol](research/m4-installed-runtime-protocol.md) describes the
scientific and execution boundaries. Local installation does not grant a right
to publish upstream parameter tables or a bundled runtime.

## Install and attach the SDK

Build and copy-install the source/data wheel using the
[SDK guide](installed-sdk.md#build-and-install). The new artifact descriptor is
`opent1d.installed-sdk/2`. It contains no numerical dependency payload. Keep its
Python environment separate from the dependency directories and projects.

Use the installed SDK Python/CLI from any unrelated directory. Attach the two
explicit site-packages directories to that current SDK interpreter, writing a
fresh attachment file outside the project and SDK environment:

```bash
SDK=/private/tmp/opent1d-sdk-env/bin/opent1d-lab
"$SDK" attach-runtimes \
  --native-site /private/tmp/opent1d-m4-dependencies/native/lib/python3.12/site-packages \
  --observer-site /private/tmp/opent1d-m4-dependencies/observer/lib/python3.12/site-packages \
  --output "$PWD/m4-attachment.json"
```

Attachment verifies complete byte/file and package/source inventories and the
current interpreter/application identity. Each fresh execution process rechecks
the binding and starts with isolated Python flags, a private cache and only the
selected dependency role. No `.pth` or site startup script is evaluated. The
two known legacy resource APIs and pinned setuptools distutils startup context
are invoked explicitly. Checksums establish consistency, not authentication of
a hostile installation owner or an OS sandbox.

## Create, freeze and explicitly execute

```python
from pathlib import Path
import opent1d_lab as lab

root = Path.cwd()
attachment = root / "m4-attachment.json"
project = lab.create_project(root / "m4-study", "Invented installed M4 study")
plans = []
for case in ("fasting", "gastric_load_15g"):
    inputs = lab.example("m4-study-installed", root / case, case=case)["inputs"]
    lab.validate("m4-study-installed", inputs)
    plan = project.freeze(
        "m4-study-installed", inputs, parent=plans[0] if plans else None
    )["plan"]
    plans.append(plan)
    admission = project.check(plan, runtime_attachment=attachment)
    result = project.run(plan, runtime_attachment=attachment, timeout=10800)
    print(result)
```

Both plans use the original Dalla Man and ultradian sources, adult#001,
240 minutes and all 961 quarter-minute samples. The prescribed 15 g condition
changes the initial gastric amount; it introduces no timed meal, controller or
fitting. Every reference, source, observer and fresh-process repeat must pass
before a complete result. A process exit alone does not establish that result.
Inspect complete/incomplete status, all planned slots, reports and receipts.
`retry_of=previous_attempt` explicitly starts another retained attempt.

The CLI mirrors these operations: use `example --task m4-study-installed
--case fasting`, `validate`/`freeze --config ...`, and
`check`/`run --runtime-attachment ...`. Native stage and whole-source budgets
remain in the frozen input; `run --timeout` is the outer deadline. Cancellation
and failures retain evidence and unavailable cells. An unresolved cleanup
cannot become a successful terminal attempt. The original historical task
does not gain execution permission from a new attachment.

## Reopen and relocate

```python
project.reconstruct(result["attempt"], root / "original-report")
project.relocate(root / "moved-study")
moved = lab.open_project(root / "moved-study")
moved.reconstruct(result["attempt"], root / "moved-report")
```

Reconstruction needs the matching trusted SDK source, with no attachment,
NumPy, SciPy, simulator or original callback/environment paths. It verifies
source/protocol/runtime snapshots, command and ownership ledgers, all numerical
gates and repeats, then requires exact JSON, Markdown and SVG report bytes.
Archived paths describe the original execution; they never select code to run.
Incomplete/failed native evidence needs explicit `allow_failed=True` and retains
that status. A forensic attempt without an admissible native archive has no
native reconstruction; its original ledger and evidence remain available.

Retain the original project until the moved copy is verified. Keep full native
parameter records and upstream payloads local while their separate publication
rights remain unresolved. A successful relocation or numerical check does not
establish a human or clinical result.
