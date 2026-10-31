# Internal M4 and connected-study candidate

This roadmap-step-6 candidate extends the installed Python/CLI SDK and shared
workbench with the maintained M4 secretion study and its connected synthetic
chain. It is a source/data wheel requiring host CPython 3.12 and separately
reviewed native dependencies. Exact-artifact qualification selects Apple Silicon
macOS. It does not provide a standalone `.app`, public native distribution,
signing, clean-host acceptance or intended-user evidence.

The [two-MMTT candidate](internal-mmtt-candidate.md) remains available with its
existing scope. This guide owns the integrated candidate; the [installed M4
guide](installed-m4.md) owns runtime attachment and scientific execution, and the
[connected protocol](research/connected-synthetic-study.md) owns the synthetic
study's numerical meaning. Read [decision 0090](decisions/0090-integrated-native-candidate.md)
for the qualification selected before execution.

## Build and attach

From clean source, retain the wheel and `receipt.json` together:

```sh
uv sync --locked
uv run --locked python scripts/build_sdk.py \
  --output /private/tmp/integrated-candidate \
  --build-label internal-integrated --integrated-candidate
uv venv --python 3.12 /private/tmp/integrated-environment
uv pip install --no-deps --link-mode=copy \
  --python /private/tmp/integrated-environment/bin/python \
  /private/tmp/integrated-candidate/opent1d_lab-0.0.0.dev0-py3-none-any.whl
/private/tmp/integrated-environment/bin/opent1d-lab installation
```

Descriptor 5 enforces the exact ordered identifiers `mmtt-sensitivity`,
`m4-study-secure`, `m4-study-installed`, `mmtt-sampling`. Three routes execute;
the historical `m4-study-secure` identity retains passive intake/readers and
execution refusal. The connected study composes maintained M4 and sampling
services. The wheel ships no numerical dependencies. `--mmtt-only` and
`--integrated-candidate` are mutually exclusive; the default developer descriptor
3 is retained.

Follow the explicit reviewed preparation in the [M4 guide](installed-m4.md).
Use ordinary, separately inventoried native and observer site-package directories:

```sh
/private/tmp/integrated-environment/bin/opent1d-lab attach-runtimes \
  --native-site /private/tmp/reviewed-m4/native/lib/python3.12/site-packages \
  --observer-site /private/tmp/reviewed-m4/observer/lib/python3.12/site-packages \
  --output /private/tmp/integrated-attachment.json
/private/tmp/integrated-environment/bin/opent1d-lab gui \
  --workspace /private/tmp/integrated-workspace \
  --runtime-attachment /private/tmp/integrated-attachment.json
```

An attachment binds the exact application descriptor, interpreter path and
reviewed source/dependency inventories. A second installation of the same wheel
needs a fresh attachment for execution. A missing attachment produces an explicit
retained failed first attempt; foreign or changed attachments refuse admission.
Checking and reading never install dependencies. The root tooling environment
does not become a simulation environment. Historical installation and public CI
guards remain in force.

## Exercise the integrated workflow

Create a project outside the installation. Prepare M4 source/load inputs, inspect
them and freeze plans before execution. A four-member comparison can select both
sources under fasting and initial 15-g conditions from one combined four-slot
plan. Freeze that comparison before running the plan. This exercises four fixed
conditions; it does not establish separate executions of parent-linked plans.

For the connected study, state a question and freeze its declaration before its
forward plan runs. The workbench exposes explicit next actions: run the fixed
forward, materialize its verified observations and downstream plans, then run
sampling. Materialization is a writing operation; reconstruction is read-only.
A failed forward blocks descendants. Preserve first failures when retrying.

Interpret native acceptance, inverse point recovery and interval completeness
separately. The complete and missing-observation examples each retain 72 planned
rows. The selected complete example expects 72 available/complete rows and six
matched plus eighteen mismatch point checks. The missing example expects 48
available points, 36 complete rows and 24 unavailable points; point support and
interval completeness differ. Schedule selection uses development evidence only.
Known synthetic truth is not observed biological truth, and mismatch controls
do not establish biological validity or calibration.

Download JSON, Markdown and CSV reports, retain explicit saved ledger tips, quit
and reopen the server, and move the whole project when handing it off. Preserve
units, the native 0–240-minute quarter-minute grid and the downstream declared
0–120-minute prefix. Closing a browser tab does not stop the server.

## Compatibility and replacement

| Evidence | Integrated candidate behavior |
| --- | --- |
| Both MMTT tasks and current comparisons | Uses the existing trusted scientific readers and exact current comparison identity. |
| PR-43 MMTT comparisons at the pinned source in decision 0089 | Retains the single supported comparison-reader transition, original report bytes/provenance and separately recorded current reader identity. |
| M4 and connected projects with exactly unchanged native/shared reader bindings | Reconstructs preserved evidence without old applications, runtime directories or a current execution attachment. Complete inventories and authoritative report checks remain required. |
| Clean merged PR-44 predecessor at `b96a288ce4b0a0feaae4929475c992e95e6b7624` | Qualification compares its developer wheel's entire embedded source/data payload with the integrated wheel. Its direct M4 execution is imported retrospectively into an A project; C's connected execution is prospective. |
| Unknown/changed native readers, scientific bindings or resealed altered evidence | Refuses. There is no changed-native-reader migration or archived callback execution. Older PR-43 native evidence has no newly granted exception. |
| Replacement and rollback | Keep exact old/new wheels, receipts and complete projects. Install separately, stop the old server, reopen preserved evidence. Rollback uses the retained old application for its old work; reverse reading of new work is not promised. |

Descriptor changes alone do not establish compatibility. This wrapper expansion
preserves the complete embedded scientific/service payload and comparison
registry. Any later relevant source change needs its own reader decision and
artifact qualification.

## Repeat qualification

Keep the clean PR-44 predecessor wheel/receipt, a clean integrated wheel/receipt,
an explicitly reviewed runtime preparation receipt, and the retained PR-43 MMTT
qualification bundle from the [reader exercise](internal-mmtt-candidate.md).
Select a fresh canonical directory outside the checkout:

```sh
uv run --locked python scripts/qualify_integrated_candidate.py \
  --predecessor-wheel /private/tmp/predecessor/opent1d_lab-0.0.0.dev0-py3-none-any.whl \
  --predecessor-receipt /private/tmp/predecessor/receipt.json \
  --candidate-wheel /private/tmp/integrated-candidate/opent1d_lab-0.0.0.dev0-py3-none-any.whl \
  --candidate-receipt /private/tmp/integrated-candidate/receipt.json \
  --runtime-receipt /private/tmp/reviewed-m4/receipt.json \
  --mmtt-predecessor /private/tmp/mmtt-reader-qualification/relocated \
  --output /private/tmp/integrated-qualification
```

The program copies ordinary reviewed role directories, validates six selectors,
rights inventory and complete locked/upstream/file rosters, and installs three
isolated dependency-free SDK environments offline. It binds the actual installed
descriptors and clean source to the wheel hashes, rather than trusting labels.
It executes direct A and workbench-HTTP C four-slot native studies and requires
all inherited reference/source/observation/repeat/refinement gates. The scientific
parity roster includes primary and repeat reference/source/observer evidence and
both BC-008 numerical rosters: **274 files must match byte for byte**. Commands,
timing, runtime attestations and seals remain separate execution evidence.

The candidate then exercises complete/missing connected studies, prospective
comparisons, exact authenticated downloads and relaunch/prefix reconstruction.
Twelve installed numerical tests and the checkout-dependent observer/beta-cell
reference suites (15/23) use the reviewed roles; their environments are reported
separately. Missing/foreign/altered attachment cases, a cancellation after an
actual numerical child, owned cleanup and an unrelated surviving process are
required. Relocation physically withdraws old installations, projects, inputs
and all three private role directories before the fresh reader reconstructs
unchanged A/C reports. Unknown readers and resealed grid/repeat alterations must
refuse while originals remain unchanged. Current MMTT chains and the pinned
PR-43 reader transition are also exercised.

Retain `qualification.json`, phase receipts/logs, exact artifacts, source state,
scientific parity inventory and report bundles. A failed phase stops qualification
and remains evidence. Native payloads and full reports include parameter records:
keep the whole qualification directory private and out of Git. Public summaries
may describe bounded outcomes without redistributing those records.

`formative-packet/` contains candidate-bound unanswered participant tasks, a real
failed recovery project, separate technical reference reports and a blank
observation template. Preparation records no human session. Intended-user work,
an independent recipient, clean-host installation, distribution rights and a
public release remain separate gates. Root regression checks, real-browser
checks, actual-host native qualification and hosted CI are distinct evidence.
