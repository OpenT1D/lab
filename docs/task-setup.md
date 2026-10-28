# Plan, check and explicitly install task runtimes

Task-directed setup uses the existing locked projects required by a supported researcher task. Planning and checking are separate from installation. The [common researcher entry](local-workflow-entry.md) continues to run installed environments directly; execution never silently installs dependencies.

Users of the [Windows installation candidate](windows-installation.md) do not
perform these developer setup commands. Its three locked runtimes are included;
readiness verifies their manifest-bound bytes and distribution identities
offline. The installed setup action verifies those components without invoking
uv or downloading packages. Missing or changed components require repair with
the installer. Checkout setup below retains its existing explicit contract.

Use `uv` from the recorded checkout on macOS or Linux. Explicitly bootstrap the existing root tooling first; the repository selects Python 3.12:

```sh
uv sync --locked
```

The commands below then use `.venv/bin/python`. The tools themselves use the standard library and can also run with an already available Python 3.12 interpreter. The first installation may require network access. Setup installs the declared root tooling and task runtimes; it does not download researcher models or observations, execute supplied callbacks or establish scientific acceptance.

In an independent public snapshot, [the publication policy](publication-security.md)
refuses installation of historical native environments before starting any
installer. The planning/check examples remain available; the native install
example below is for deliberate private-archive research. Begin public use with
the two synthetic MMTT tasks and the patched root environment. Old task names
containing `secure` do not supersede the current advisory inventory.

## Create a bound setup plan

```sh
.venv/bin/python -B -S -m experiments.setup plan m4-study \
  --output results/setup-plan
.venv/bin/python -B -S -m experiments.setup check \
  --plan results/setup-plan --output results/setup-check
```

Plans bind the exact existing `pyproject.toml`, `uv.lock`, Python selection files and setup implementation identities, including the shared process helpers used to supervise installation. They also bind the discovered `uv` executable identity. Each operation uses fresh output and preserves a sealed plan or receipt. Changed implementation bytes are refused before readiness checks, installation or output creation. If those identities change, create a new plan rather than editing the old one.

| Task | Required execution projects |
| --- | --- |
| `m3-forecast`, `m3-compare`, `m5-prognosis`, `mmtt-sensitivity`, `mmtt-sampling` | Root tooling/orchestration |
| `p1-controller` | Root and locked simglucose |
| `m4-secretion`, `m4-compare`, `m4-study` | Root, locked simglucose and locked beta-cell observation |
| `m4-study-secure` | Root, maintained simglucose and locked beta-cell observation |

All reconstruction setup needs only root Python/tooling. Add `--reconstruct` when planning that operation. Preparing M3 donors or other route-specific development inputs retains the separate commands and environments in its canonical guide.

For P1 execution, optional `--source PATH` reads the existing controller declaration without importing it. Declared extra dependencies must already occur at their declared versions in the current native lock. Setup refuses an unlocked dependency or conflict; it does not add or upgrade packages.

## Read readiness or request installation

`check` examines the installed interpreter and declared distribution metadata without importing those distributions. It also runs offline `uv sync --locked --check` for full selected-project environment consistency. Missing environments return `ready: false` without installation. Foreign active-environment, project, index, configuration and Python-path selectors do not redirect these checks.

To install the planned projects explicitly:

```sh
.venv/bin/python -B -S -m experiments.setup install \
  --plan results/setup-plan --output results/setup-installed
```

The only installation commands are the existing locked setup operations:

```sh
uv sync --locked
uv sync --locked --project experiments/m0/simglucose
uv sync --locked --project experiments/m0/simglucose_secure
uv sync --locked --project experiments/m4/beta_cell/runtime
```

Only projects needed by the plan are invoked. Installation uses sanitized environment selectors and checks source, lock, project and tool identities before and after each operation. Post-install checks verify Python/distribution metadata and full lock consistency. Logs and per-project outcomes remain in the setup receipt. `--offline` prevents network access and Python downloads during installation; it uses the recorded `uv` executable's default cache and requires the needed artifacts to be present there. Online installation uses an isolated temporary cache.

The maintained M4 task selects its new native project explicitly; historical
routes retain their frozen locks. The [local GUI](local-gui.md) offers the same
explicit installation followed by a separate task configuration check.

Outputs cannot overlap a plan, locked input file or target environment. Root tooling remains separate from numerical projects; no global package installation, arbitrary archived setup script or unlocked dependency is supported. The caller remains responsible for using the correct supported checkout.

## Continue with the task

After readiness succeeds, follow the task's canonical guide and run its normal checks and experiment. For example, the common entry checks model/configuration admission separately:

```sh
.venv/bin/python -m experiments.workflows check m4-study \
  --config experiments/m4/initial_load/example.json
```

`ready: true` describes installed environments and their locks. It does not prove callback behavior, numerical acceptance, source rights, model validity or independent researcher usability. The [roadmap](../ROADMAP.md) keeps these evidence requirements separate.
