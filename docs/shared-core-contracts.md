# Shared-core contract and extraction packet

OT-059 increment 1 freezes an internal metadata boundary for
`m4-study-secure` and `mmtt-sensitivity`. The routes still use their existing
workers, scientific payloads and readers. No stable SDK, general engine API or
route migration is claimed. [Decision 0080](decisions/0080-two-route-contract-packet.md)
owns this boundary; the [task and verification record](research/ot059-contract-extraction.md)
retains scope, checks and review.

## Frozen packet and version policy

The [fixture packet](../experiments/shared_contracts/fixtures/packet.json)
contains one project, five input assets and three plans: M4 fasting, its derived
15 g plan and one invented MMTT visit pair. The
[case index](../experiments/shared_contracts/fixtures/cases.json) names positive,
refused, failed and relocated cases. The
[reference outcomes](../experiments/shared_contracts/fixtures/outcomes.json)
retain observed execution/coverage/roster projections after native-reader
reconstruction; tests compare these independently frozen expectations. Original
JSON/CSV bytes are retained. These projections contain no M4 numerical success.
The CSV fixtures preserve the original `csv.writer` CRLF bytes; the narrow
`.gitattributes` exception prevents Git line-ending conversion from invalidating
their frozen identities.
`experiments.shared_contracts.core.validate` is an internal fixture validator,
not a runtime, storage service or plugin API. It performs no supplied-code
execution. Its two explicit passive bindings delegate configuration admission
to the existing tasks. M4 fixture source paths resolve against the retained
fixture directory; this is not a new general source resolver.

The packet schema is `opent1d.contract-packet/1`. Each descriptor uses
`opent1d.shared-{kind}/1`; unknown versions and fields are refused. IDs are
SHA-256 of UTF-8 JSON with sorted keys, compact separators and finite numbers,
excluding the descriptor's `id`. They identify descriptor content, not an
execution API or a release. Raw asset SHA-256 binds the original file bytes.
Changing a scientific input or binding creates a new plan; derivation records
the previous plan's ID without changing it. Assets use canonical project-relative
POSIX paths; absolute, traversal and symlink paths are refused. Moving the project
preserves these identities. A later store must seal its complete all-attempt
ledger; a standalone metadata document cannot prove an omitted attempt existed.

| Descriptor | Required version 1 fields beyond `schema`, `id` | Meaning |
| --- | --- | --- |
| Project | `name` | Local synthetic project identity; display name participates in this fixture identity. |
| Asset | `path`, `sha256`, `role`, `rights` | Original bytes; roles are scientific input, native report or execution record. This packet admits public synthetic fixtures only. Private asset references/export policy belong to OT-064. |
| Plan | `project_id`, `parent_id`, `task`, `family`, `payload`, `binding`, `planned_slots` | Ordered immutable administrative roster; payload maps native filenames to asset IDs. Binding preserves separate protocol/method, implementation, ancestry/source and locked runtime-file identities. |
| Attempt | `plan_id`, `ordinal`, `execution_status`, `slot_statuses` | Every terminal attempt, starting at ordinal 1; every planned slot remains complete, failed or unavailable. Retry adds an attempt. Status is completed, failed or interrupted. |
| Result | `attempt_id`, `report_asset`, `execution_asset`, `reader`, `states` | Exactly one retained outcome per terminal attempt. The execution asset retains actual runtime/phase/error or native stage records; an absent worker is not an observed runtime. |

The task-owned native report is authoritative. `reader` records the trusted
module, report schema, implementation inventory and prohibition on archived-code
execution. Schema version, method/protocol version, metric convention, source
identity, runtime identity and reader identity are separate facts. Metric
conventions stay in the native protocol/payload; this packet introduces no
generic metric API. A matching module name alone is insufficient compatibility
evidence.

Result states separately retain `completeness` (complete/incomplete),
`reconstruction` (unchecked/verified/refused) and `scientific_evidence`
(`synthetic-only`). Reconstruction is a recorded check, not an authenticated
certificate: packet validation checks linked bytes, native plan association,
status and reader identity, while an explicit native reconstruction verifies
the result arithmetic and report. Metadata cannot promote a completed process
to scientific completeness, an incomplete result to complete, or a synthetic
check to human/biological evidence. Test-generated descriptors exercise all five
record types against real saved reports, including failures.

## Scientific payloads and provisional families

| Provisional family | Existing routes | Preserved boundary and refusal |
| --- | --- | --- |
| Sampled stateful control | `p1-controller`; cross-check M1/M2 | P1 calls once per 3 min; held CGM retains measurement time, availability and age. Basal and bolus fields are rates in U/min; action interval is `[start,end)`, stored glucose is `(start,end]`. Actual meals and announced carbohydrate differ. Refuse skipped clocks, future observations, incompatible units or unsupported action semantics. |
| Causal continuous source | Four M4 source/study routes | Pure RHS callback receives current `t,G,Gdot,Z,Sb,h,parameters`, returns pancreatic rate in pmol/(kg min). Host owns initialization, solver, portal transit, SC replacement and observation. Repeated/out-of-order probes catch selected hidden-state defects, without proving arbitrary code pure. A sampled controller is not an RHS callback. |
| Frozen causal forecast | Both M3 routes | Retain actual/available observation times, six exact causal times, horizons, origins, split and full failed-pair denominator. Targets are withheld until prediction; retain finite negative forecasts. No automatic refit from an evaluation score. |
| Frozen landmark prognosis | `m5-prognosis` | Frozen model/state, development/evaluation separation, landmark inputs without future outcomes, U/day output and full eligible denominator. No treatment/cure interpretation. |
| Offline paired observation analysis | `mmtt-sensitivity` | Retrospective inverse analysis, actual times, missing/censored values, context, fixed kinetics, all variants and failed draws; whole-body total secretion including basal in pmol, follow-up minus baseline. No causal simulator callback. |
| Offline sampling comparison | `mmtt-sampling` | Mask raw observations before parsing, conversion, initialization or estimation; reuse the same estimator, retain all planned schedules and variants. No full-curve state may leak into a reduced schedule. |

These families are descriptive and provisional. Existing M2 engine work does
not establish conformance to this new packet. LT1's native U/h infusion,
point-valued plasma glucose and event schedule cannot acquire M1 interval
semantics through a unit conversion. A bolus amount in U is refused at that
boundary. OT-062 must exercise applicable families with the second native
engine before a shared compatibility claim.

The M4 fixture uses the two existing Dalla Man and ultradian example
source/declaration pairs, first `fasting`, then a distinct derived
`gastric_load_15g` plan. The latter initializes gastric solid at 15,000 mg;
it is not an announced meal or a timed meal event. Preserve adult#001,
240 min, 961 samples at 0.25 min, SC/basal/portal ownership, reference
verification, controls, refinement and fresh-process repeats. Native protocol
bytes and tolerances are unchanged. Source/scenario slots have denominator 2
in each fixture; the full task payload retains source pairs, stages and repeats.

MMTT retains one invented participant with before/after visits, `nominal`,
`volume-120`, `peripheral-075`, 128 draws and seed 117. Time is min,
glucose mmol/L, measured C-peptide nmol/L (explicit multiplication by 1000 to
pmol/L), volume L and rates per min. The three shared pair slots preserve the
native visit/draw ledgers and failure rules; they do not replace them. MMTT's
after-minus-before contrast differs from M4's left-minus-right trajectory
contrast. Original context, uncertainty and source ancestry remain in the
task payload, without flattening them into generic signal ports.

## Ten-route source, runtime and reader inventory

The [machine-readable inventory](../experiments/shared_contracts/route-inventory.json)
lists exact paths and SHA-256 values, runtime selectors/required package pins,
registered run/reader modules, additional static dependencies, administration
sources and M5 archive aliases. `inventory.py` recomputes it passively; drift
fails the packet check and needs an explicit contract review, not automatic
baseline regeneration. Counts below describe declared inventories, not a
universal import closure or a guarantee that legacy snapshots captured every
dependency.

| Route | Native source inventory authority | Execution environment | Reader boundary |
| --- | --- | --- | --- |
| `p1-controller` | `p1_external.__main__.LOCAL_SOURCES`, `source_code_hashes()`; 13 files | Root coordinator; simglucose lock, supplied dependencies must fit | Current implementation hashes; controller remains opaque in reconstruction. `verify_actions` is separate explicit supplied-code execution. |
| `m3-forecast` | `m3.researcher.common.provenance().sources`; 40 | Root/stdlib supplied callback | Current provenance hashes; predictor/settings opaque. |
| `m3-compare` | `m3.comparison.common.provenance().sources`; 47 | Root/stdlib | Current child and comparison provenance hashes. |
| `m4-secretion` | `researcher_workflow.common.SOURCES + REUSED`; 20 direct, plus protocols/observer locks and nested causal/reference snapshots | Root; simglucose and observer locks | Own manifest/protocol plus nested readers; no general equality of own implementation snapshots to current bytes. |
| `m4-compare` | `comparison.common.SOURCES`; 63 | Root; simglucose and observer locks | Archived source hash = frozen provenance = current bytes. |
| `m4-study` | `initial_load.common.source_paths()`; 127, AST closure from explicit roots | Root; simglucose and observer locks | Current path set; archived bytes against frozen hashes, protocol/locks against frozen identities. |
| `m4-study-secure` | `secure_study.common.source_paths()`; 139, original inherited roots plus maintained dependencies | Root; secure simglucose and observer locks | Frozen snapshot/path-set policy plus maintained execution identity and completed-stage runtime attestations. |
| `m5-prognosis` | `researcher_workflow.contract.SOURCES`; 5 aliases plus embedded protocol, generated fixture, supplied model/state and tooling lock | Root/stdlib | Five implementation aliases equal current bytes; supplied model/state opaque; checks original report in place. |
| `mmtt-sensitivity` | `observation_analysis.plan.source_identity()`; 18, plus 5 ancestry files and protocol | Root/stdlib | Current implementation, protocol and ancestry, retained opaque snapshots. Exact runtime checked for execution. |
| `mmtt-sampling` | `mmtt_sampling.plan.source_identity()`; 27, plus 7 ancestry files, both protocols and development seal | Root/stdlib | Current sampling/shared identities, frozen development evidence and nested MMTT reader. |

Runtime selectors identify `pyproject.toml`, `uv.lock` and the selected
`.python-version` (including the inherited root selector). The simglucose
projects pin NumPy/SciPy 1.26.4/1.13.1; the observer pins 2.2.6/1.15.3. They must
remain isolated. M3's separate statistical runtime is a donor-fit/verification
dependency recorded by provenance, not the runtime of the registered frozen
forecast route. P1 protocol settings and M5's protocol/fixture are generated
task payloads; they are not invented static source filenames. Supplied code,
declarations, state, settings, observations and actual installed native source/
parameter provenance are captured by each route, not guessed by this inventory.

All ten readers are selected by `catalogue.formats.reconstruction_args` and
the explicit registry. `historical_readers.core.TASKS` supports eight of them
plus campaigns; **neither MMTT route is supported by that helper**. For MMTT,
retain an identified trusted matching implementation and invoke its own reader.
Archived Python is opaque provenance. Moving an archive does not authorize an
implementation upgrade or establish reader/app/host compatibility. OT-064 must
define and test the retained-reader and upgrade matrix explicitly.

## Extraction map and layered quality matrix

| Existing owner | Extractable service and immediate consumer | Keep task-owned / next gate |
| --- | --- | --- |
| `catalogue.storage`, regular-file helpers, task freezes | Project-relative asset inventory, fresh destinations and immutable identity for minimal OT-064 | Native payloads, trust checks, private-reference/export policy; no imported-code execution on open. |
| M4 `initial_load.common.prepare`, MMTT `plan.freeze/load_plan` | Common project/plan lineage and version dispatch for OT-060 | Scientific validation, ancestry, protocol bytes, kinetics, reference requirements and runtime admission. |
| M4 `initial_load.run`/secure adapter; MMTT `run`; campaign ledgers | Plan slots plus every terminal attempt for minimal OT-061 | Original stages, atomic visits/draws, failed/partial evidence and explicit retry. M4 activation mutates module bindings and is not thread-safe; retain isolated workers. |
| `platform_process`, task supervisors and setup | Explicit setup/start/deadline/cancel/app-close lifecycle and identified environments for OT-061 | Current process ownership; actual per-host cleanup/unrelated-process checks. Runtime isolation is not a hostile-code sandbox. |
| Native `report.reconstruct`/`run.reconstruct`, catalogue dispatch, historical helper | Trusted reader dispatch and result metadata for minimal OT-064 | Task arithmetic/report bytes and historical version policy. MMTT needs its own retained trusted-reader route. |
| Registry/GUI managers | Thin task/asset/capability selection for later OT-065 | No new scientific dispatcher or callback interpretation in the GUI; no SDK/GUI migration in this increment. |

| Layer | Fixture/check in this packet | What it establishes | Remaining gate |
| --- | --- | --- | --- |
| Schema, identity, lineage | Packet byte/version/path/family/roster refusals and exact ten-route inventory | Bounded metadata admission and drift detection | Durable store sealing and full all-attempt provenance, OT-064/066 |
| Scientific contract | Both M4 source intakes, fasting/15 g derivation; MMTT native freeze; P1 clock/action cross-check; existing RHS negative probes | Preserved native payload meanings and declared denominators | Second-engine family conformance, OT-062 |
| Actual offline calculation | Complete, censored and interrupted MMTT fixtures | Standard-library execution, separate process/completeness states and retained variants | Independent empirical kinetics/uncertainty and human-data authorization |
| Native numerical behavior | Existing protocol/reference identities retained; controlled M4 reference-launch failure | Passive admission and failure accounting only | No new M4 native success/parity run; reviewed native environment and unchanged numerical gates required |
| Readers and relocation | Moved MMTT complete/incomplete/interrupted archives and M4 failed archive, exact report bytes, explicit failure admission | Matching trusted reader reconstructs bounded saved cases | Complete native M4 relocation and declared reader/app/host upgrade matrix |
| Process and host | Controlled failure/interruption injection, existing root process tests | Bounded retained-evidence behavior; no new host qualification | Real worker kill/deadline/cancel/close and unrelated-process preservation on each claimed OS |
| Scientific and user evidence | Explicit `synthetic-only`; separate recorded reconstruction state | No evidence promotion | Biological validity, independent researcher acceptance and later Windows installer/family usability exercise remain separate |

Run the bounded suite with root tooling:

```sh
uv sync --locked
uv run --locked python -m unittest tests.test_shared_contract_packet -v
```

The integration owner also runs the repository's full check. This packet does
not install historical native environments or bypass the
[public runtime boundary](publication-security.md). Local fixture checks are
not hosted CI, native M4 parity, a Windows installer acceptance or human use.
