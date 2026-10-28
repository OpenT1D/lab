# Maintained M4 runtime execution

`M4-STUDY-SECURE/1` is the explicit maintained execution successor to
`M4-STUDY/2`. Its machine contract is
`experiments/m4/secure_study/protocol.json`. The native project is
`experiments/m0/simglucose_secure`; it changes only urllib3 from 2.7.0 to 2.8.0
and setuptools from 80.9.0 to 84.0.0. The other 32 dependency package/version
and source identities remain identical, including both pinned upstream engines,
NumPy 1.26.4, SciPy 1.13.1, pandas 2.2.3 and matplotlib 3.9.4.

Setuptools removed `pkg_resources` in version 82. The pinned gym/simglucose
sources still import its resource and entry-point helpers. A successor-only
startup adapter provides the two observed APIs using standard-library
distribution metadata and entry points, restricts resource access to regular
installed simglucose files and restores the module binding on return. It copies
no historical setuptools implementation and edits no installed engine files.
See the [Setuptools release history](https://setuptools.pypa.io/en/latest/history.html#v82-0-0).

The scientific equations, source contract, loads, solver settings, numerical
criteria, units, state and time conventions, native guards and C-peptide
observation are inherited unchanged. Historical projects, locks, scientific
protocols, implementation files and archive guards remain byte-identical.
Dependency maintenance does not establish physiological, human or clinical
validity.

Use the explicit task `m4-study-secure`, or
`python -m experiments.m4.secure_study run --config CONFIG --output FRESH`.
The configuration uses `m4-secure-study-config/1` and otherwise the same ordered
sources, supported scenario subset and finite stage/whole-source budgets as the
inherited study. `check --config CONFIG` is passive. Install the separate
project with `uv sync --locked --project experiments/m0/simglucose_secure`;
the unchanged observer project is also required. Execution never implicitly
installs an old or new runtime.

The default baseline is an owned `m4-secure-reference-run/1` archive. It retains
the original BC-008/2 protocol as an explicitly inherited scientific contract,
runs its unchanged mathematical worker and criteria in the maintained native
interpreter, and seals the maintained runtime descriptor, actual installed
distribution/upstream identity, exact commands, budgets, exits and fresh-process
repeat. It does not create a historical BC-008 execution manifest. Optional
`--reference PATH` accepts either this maintained reference or an unchanged
historical BC-008 reference after the historical reader and all original
source/lock guards pass. Supplied historical evidence is labelled inherited;
new scenario-specific controls are always executed again.

The successor uses an explicit startup context in dedicated coordinator,
worker and reader processes to bind its own schema, protocol, source inventory
and commands to unchanged numerical/orchestration functions. Each binding is
restored on return. This API is not a thread-safe in-process service; callers
use the registered subprocess command. No archive-supplied source is imported.
Nested inherited scientific artifact schemas identify their scientific format;
the successor plan, manifest, report and reference execution receipt identify
the current execution. Every launched numerical stage checks and records the
actual installed distributions and locked runtime identities before solving.

Reconstruct with
`python -B -S -m experiments.m4.secure_study reconstruct --archive ARCHIVE --output FRESH`.
The reader uses only the standard library, verifies the complete sealed archive,
configuration, protocol, source/declaration/helper bindings, process ledger,
actual runtime receipts, inherited numerical criteria, repeats and descriptive
contrasts, and compares all existing derived bytes before writing a fresh
output. Failed/interrupted evidence requires `--allow-failed`, preserves the
entire frozen denominator and cannot support incomplete source pairs.

All numerical process groups retain the inherited bounded cleanup. The owned
baseline coordinator has a 20-second outer cleanup allowance, longer than its
10-second worker cleanup, without changing the declared execution budget.
Numerical parity, gates, repeat equality, failure/interruption cleanup and
standard-library reconstruction require separate retained execution evidence;
a dependency lock or CI pass is not model validation.
