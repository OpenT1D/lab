# OT-062 runtime and rights admission proposal

Date: 1 November 2026. Inspected checkout:
`af4c13a9dd1d2dd5851cc6f7a302ebc558a096da`. This extends the
[native contract audit](ot062-adapter-audit.md) with a passive runtime/rights
assessment and proposed acceptance cases C15–C18. **No native installation,
execution, public CI, bundle or parameter redistribution is authorized by this
document.** The [metadata snapshot](../../experiments/adapter_audit/runtime-rights.json)
is descriptive evidence, not an installer policy or executable admission file.
Every authorization in it is false.

The proposed order is LT1 first, on one declared macOS arm64 host, after the
conditions below have been met. Historical simglucose remains excluded from
fresh/public setup; prepare a separately identified patched successor before
requesting its native checks. Retaining an old lock preserves a reference
identity, not permission to execute it. The separately admitted M4 candidate
does not admit these M1/M2 environments. The existing
[publication boundary](../publication-security.md),
[rights assessment](../licensing.md) and
[roadmap order](../../ROADMAP.md#stretch-and-subsequent-expansion) remain in force.

## What was inspected

Only public source and registry/advisory metadata were fetched. Three archives
were hashed and inspected in memory: Gym 0.9.4 and setuptools 80.9.0/84.0.0
wheels. None was extracted, installed, imported or built. No interpreter archive,
parameter CSV or native result was downloaded. Source retrieval and OSV queries
are network reads; no native setup or experiment was run.

The snapshot binds package versions, registry metadata hashes, upstream notices,
source revisions and advisory ranges. It protects 26 files: all 19 tracked
locks/baselines plus selected manifests, policies and audit fixtures. Raw
responses, archives and inspection logs remain under ignored
`results/adapter-audit/runtime-rights-20261101/`. Their public URLs and SHA-256
identities are recorded in the snapshot; that does not promise those mutable
registry responses will retain the same bytes on a later date.

| Boundary | simglucose | LT1 Cambridge |
| --- | --- | --- |
| Upstream source | simglucose 0.2.11, `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`; the same lock includes GlucoSim 0.1.2, `6422a91d533125a8feb4f2e8737aecd67fec95c9` | LT1 source package 2.1.0, `9a6092065bd821f88691cd8d03b0550acd665573` |
| Preserved lock | `experiments/m0/simglucose/uv.lock`, SHA-256 `13d254dcebe8d1ab54c3140cdc07152d719a68477a1378d7fe77fc1568612aa9` | `experiments/m0/lt1/package-lock.json`, SHA-256 `44ad7ba062a7d67032d91fcc9e0fa2aa3910b3856dce76bee5ba32093c1a150e` |
| Interpreter contract | Manifest `>=3.12,<3.13`; lock `==3.12.*`. Historical execution used 3.12.13; the patch is **not locked** | Node 22.22.2, enforced by the existing M2 worker; changing Node needs a new explicit runtime/worker identity |
| Selected package inventory | 34 nonvirtual packages: 32 registry packages and two Git sources. NumPy 1.26.4, SciPy 1.13.1, pandas 2.2.3, matplotlib 3.9.4, Gym 0.9.4, setuptools 80.9.0 | 20 npm packages plus private root; TypeScript 5.7.3, ts-node 10.9.2 and `@types/node` 22.10.7 |
| Build boundary | Manifest/lock constrain setuptools 84.0.0 and wheel 0.43.0. These two constraints are not a complete separately locked build closure or historical build-artifact receipt | The selected headless toolchain is separate from upstream's full frontend/oref0 package graph. Preserve the historical script-disabled installation approach in any future reviewed setup |
| Metadata check | All 164 lock-referenced registry artifact URL/SHA pairs match retrieved registry metadata; this does not verify downloaded artifact bytes | All 20 locked tarball URLs/integrities match registry metadata; tarball bytes were not fetched |

The conservative LT1 import traversal covers seven selected entrypoints and 45
TypeScript files, including type imports, with no bare imports or dynamic
import/require flags found. It is a text inspection, not a runtime trace or a
replacement for the historical full source inventory. That inventory still
covers all `src`, reference and licence files, together with a clean pinned
checkout. Upstream's `postinstall: patch-package` and broader package graph are
outside this headless selection. Registry lifecycle metadata also declares
prepare scripts in acorn, acorn-walk and ts-node; fetching metadata did not run
them. Neither finding authorizes running lifecycle scripts later.

## Security disposition

The two OSV batches contain 84 package/version queries by role: 56 for selected
runtime/toolchain/build entries and 28 for distributions vendored inside the two
setuptools wheels. After deduplicating GHSA/PYSEC aliases, there are **49 distinct
matching GHSA IDs**. No matched GHSA was withdrawn in the retrieved records.

| Matched role/package | GHSA matches | Disposition |
| --- | ---: | --- |
| Runtime Pillow 12.3.0 | 41 | Historical lock retained; no fresh admission. Reported fix is 13.0.0 |
| Runtime urllib3 2.7.0 | 3 | Historical lock retained; reported fix is 2.8.0 |
| Runtime certifi 2026.7.22 | 1 | Historical lock retained; current reported fix is 2026.10.18 |
| Runtime setuptools 80.9.0 | 2 | Includes archive/build behavior and a Windows-specific legacy path; reported fixes are 83.0.0 and 84.1.0 |
| Runtime vendored jaraco.context 5.3.0 | 1 | Present in the hashed setuptools wheel; GHSA-58pv-8j8x-9vj2 reports path traversal, fixed at 6.1.0 |
| Runtime vendored wheel 0.45.1 | 1 | Present in the same wheel; GHSA-8rrh-rw8j-w5fx reports an archive path issue, fixed at 0.46.2 |
| Build setuptools 84.0.0 / wheel 0.43.0 | 1 each | Their IDs overlap runtime matches; not two additional distinct vulnerabilities. The build setuptools wheel contains 12 vendored metadata rows with no additional OSV matches |
| LT1's 20 selected npm packages | 0 | No dated name/version matches; Node/V8, OS/compiler, upstream Git code and unqueried embedded components are outside that result |

Thus there are 49 runtime package/advisory matches including the two vendored
components, and two build matches, across 49 distinct IDs. The snapshot lists
every matched ID, range, patched version, severity and primary response hash.
The original runtime setuptools wheel contains 16 vendored distributions; a
top-level lock scan alone misses this part of the inventory. Historical
`pkg_resources` runtime-context inspection also exposed vendored distributions.

These are affected-version matches, not demonstrated exploits in this task.
Synthetic inputs and absence of ordinary image use do not establish that all
affected code is unreachable. The
[jaraco.context advisory](https://github.com/advisories/GHSA-58pv-8j8x-9vj2),
[wheel advisory](https://github.com/advisories/GHSA-8rrh-rw8j-w5fx) and
[setuptools advisory](https://github.com/advisories/GHSA-xmj3-9gf7-h52w)
are primary evidence for the additional build/vendor boundary. The Python
name/version queries for simglucose and GlucoSim do not cover their pinned Git
commits or substitute for a source review.
This bounded inventory supplements the publication review; it does not replace
its broader manifest/alert inventory or alter its installation allowlist.

Official release records show later security releases
[Node 22.23.4](https://nodejs.org/en/blog/release/v22.23.4) and
[Python 3.12.16](https://www.python.org/downloads/release/python-31216/).
An LTS/security-supported series does not make the historical patch current.
Those releases are inputs to a future candidate assessment, not selected or
installed successors here. Node's published 22.22.2 checksums were inspected;
no binary bytes, signatures or actual interpreter provenance were verified.
Python's source-release identity likewise does not identify a uv-managed binary.

For simglucose, propose a new project/runtime identity with a separately locked
build closure and complete interpreter, wheel, bundled-library and vendor
inventory. Resolve the legacy `pkg_resources` dependency under that identity;
the M4 process-local compatibility approach is a precedent to assess, not a
drop-in clearance. Keep numerical pins where feasible, but do not call an
ancillary patch numerically neutral without checking it. Compare a successor
against the unchanged historical references; retain and investigate differences.
No tolerance relaxation or automatic baseline enrollment is permitted.

For LT1, first resolve the exact Node artifact/security decision. Prefer a
separately identified patched candidate; retain the existing Node guard until
its successor is explicitly implemented and reviewed. An exact historical
22.22.2 reproduction would require its own dated risk disposition. Neither
zero npm matches nor an older macOS/Linux reference supplies that disposition.

## Rights and output boundary

The pinned simglucose, GlucoSim and LT1 MIT notices match the retained
[simglucose](../../LICENSES/simglucose.txt),
[GlucoSim](../../LICENSES/GlucoSim.txt) and [LT1](../../LICENSES/LT1.txt) notices
byte for byte. Preserve those notices and scholarly attribution. This establishes
the inspected code declarations, not independent chain of title for physiology
tables, device assets, parameter origins or a right to distribute a native bundle.
Cambridge/Hovorka and Andersen ancestry remain as documented in the
[LT1 asset card](models/lt1-cambridge.md); the
[simglucose card](models/simglucose.md) separates parameter asset classes.

The pinned simglucose manifest includes parameter CSVs and additional
test/example/results CSV assets. The snapshot records only path, Git blob ID
and size for `Quest.csv`, `pump_params.csv`, `sensor_params.csv` and
`vpatient_params.csv`; no table payload was fetched or copied. Review the
actual installation payload, including any extra data files, before setup.
The existing private full parameter records remain private. Do not publish
full native records/reports merely because they can be reconstructed.

The exact locked Gym 0.9.4 sdist has SHA-256
`94f91ca790bab1243c584bcc3dc5f5e610709e500a554570bdc5464215c13888`
and is 157,829 bytes. Its 191 archive members contain no standalone
LICENSE/COPYING/NOTICE; `PKG-INFO` declares `License: UNKNOWN`. The registry
license declaration is empty. Resolve this artifact's licence/provenance and
notice requirements before proposed admission; do not infer them from today's
Gym repository. This is a specific evidence gap, not a conclusion that every
Gym source file lacks usable rights.

The npm metadata declares 17 MIT, one BSD-3-Clause, one ISC and one Apache-2.0
package. Python metadata includes other declarations, including certifi MPL-2.0
and matplotlib's PSF terms. The pinned pyglet source notice is BSD-3-Clause,
despite incomplete registry licence metadata. These are declarations/source
notices, not complete artifact clearance. Native NumPy/SciPy wheel libraries,
interpreter notices and any redistributed source/data still need an actual
payload inventory and applicable notices. No upstream contact or new rights
grant was obtained in this assessment.

Propose separate decisions for restricted local use and public redistribution.
A reviewer must record the scope and basis for local use of the selected code,
parameter and device assets. Until separately cleared, keep native inputs, full
parameter records and raw reports in access-restricted local storage. Export
only specifically reviewed metadata and sanitized summaries. Public installer,
bundle, table and full-report redistribution remain outside the proposed local
execution admission.

## Proposed admission sequence

| Gate | Required evidence before proceeding | Current decision |
| --- | --- | --- |
| A — Runtime/security | Exact source/interpreter/artifact hashes, OS/architecture, complete runtime/build/vendor inventory, current advisory disposition and verified setup receipt. A successor has a new identity; old locks remain unchanged | Pending for both engines; no installation admitted |
| B — Rights/use | Retained notices and recorded restricted-use basis for each selected source/parameter/device asset, resolved Gym gap where applicable, private output/export scope | Pending; no distribution clearance |
| C — Harness/method | Reviewed versioned direct/wrapped harness, controller, source inventory, input case bytes, numerical oracles and trusted readers. Explicit allowlists must recognize the new diagnostic contract | Pending; audit-1 is not admitted by existing M1/P1/M2 controller enums |
| D — Host execution | Named operator/reviewer and one macOS arm64 host; concrete file/network/process controls, per-attempt deadlines, cleanup bound and private result location; explicit execution authorization for the frozen packet | Pending; no native run admitted |
| E — Acceptance | All planned C15–C18 attempts and failures retained, direct/native controls, process observations and engine-free reconstruction/relocation reviewed on that exact revision | Unrun; no native acceptance claim |

Runtime/security, rights and harness reviews may be performed by the appropriate
maintainers; this proposal does not invent approvals or assign named people.
Complete the pre-install review in A, the use/rights decision in B and the
planned harness scope in C before requesting installation. A separately
authorized setup step would then supply A's actual setup receipt; that receipt
is required before D can admit execution.
The execution request must enumerate the exact approved case IDs and artifact
identities, not just say “run native checks.” Installation admission and later
execution admission are distinct. Refresh the advisory assessment before setup;
any changed identity requires review of the affected gate.

Use a dedicated trusted workspace and synthetic development inputs only. Proposed
execution has no network access, enforced by a reviewed host mechanism; a child
process alone does not enforce this. Restrict writable paths to the attempt's
private output/scratch directory, retain stdout/stderr without credentials or
parameter rows, and record the actual mechanism and its limits. Setup network
access, if later authorized, is a separate bounded artifact acquisition step.
Create private output directories with owner-only access. No mechanism is
implemented or qualified by this document.

## Proposed C15–C18 execution packet

First run the unchanged applicable M0 and historical M1/M2 reference checks,
with their own controllers, horizons, context requirements and exact historical
criteria. A successor mismatch is a retained difference requiring diagnosis;
never rewrite an old baseline to pass it. A passing new 30-minute diagnostic
cannot replace a failing or unavailable historical reference. If the historical
artifact cannot be admitted, mark that comparison unavailable explicitly.

Then propose a **new, separately identified 30-minute development diagnostic**:
simglucose adult#001 with the declared Dexcom/Insulet presets and seed 101; LT1
Cambridge with the M2 declared equilibrium and seed 101. Preserve synthetic
2024-07-20 clocks and each engine's native solver, reset and sensor cadence
(three-minute simglucose outer intervals; five-minute LT1 control ticks with
native intervening callbacks). Do not change the old 48-hour task or teach its
reader to accept a new grid implicitly. Freeze a new diagnostic reader/harness
before execution.

Use the audit's lagged proportional rate controller: target 120 mg/dL, gain
0.01 U/h per mg/dL, rate clipped to [0,3] U/h, memory reset to target. On a fresh
released sample, compute from prior memory, then update it; a stale observation
commands basal without changing memory. Native basal must be recorded with its
source and unit conversion, and fit the controller's declared bounds; otherwise
refuse the profile/contract. The fixture's 1.2 U/h is not a native basal value.
Only basal rate is supported, converted to U/min for simglucose, with native
pump quantization/clipping retained. This controller is a diagnostic instrument,
not an efficacy candidate or a bolus interface.

Within each engine/runtime/input pair, require exact equality of matched
serialized initial/reset state, samples, controller memory/actions, modeled
delivery and status between direct and wrapped paths. Exclude only declared
operational fields such as PID, wall time and output path; do not round outputs.
Both paths must use independently inspected native entrypoints, not call the
same adapter as their oracle. The new diagnostic has no historical baseline;
repeatability alone cannot exclude a shared defect. Check its controller against
the independent arithmetic/fixture oracles as well as native parity. Preserve all existing historical numerical
criteria. An additional quantity that cannot meet exact equality needs a
separately justified, preregistered criterion before its case is admitted.

| Case | Concrete proposed attempts | Acceptance/refusal oracle |
| --- | --- | --- |
| C15 — Reset, parity, identity | Fasting direct/wrapped pair; reset twice in one process and repeat in a fresh process. Record initial state, sensor consumption, native basal, seeds and runtime/source/input hashes. Separately change simglucose seed to 102, and change C16's actual meal from 40 to 80 g, reidentifying each attempt | Repeats and direct/wrapped pairs meet the above equality criterion; separate negative controls on the unchanged historical runners must reject two identically wrong replays against their historical baseline. A changed seed changes identity even if a deterministic selected component emits the same numbers. LT1 seed 102 is refused by the current M2 contract until explicitly supported; do not silently widen it |
| C16 — Events and causal availability | Start actual 40 g meal at minute 15; LT1 ingestion lasts 15 minutes, while simglucose retains its native eating queue. Deliver the distinct 20 g announcement once at minute 15. Delay the generated simglucose minute-9 sample until minute 15 and mask minutes 12/15 after generation; delay LT1 minute-10 sample until minute 15 and mask its minute-15 sample. Include an unchanged unfiltered native control. Separately probe LT1's minute-2.5 event with 1.5-minute duration and a simglucose numeric event time unrepresentable in integer native minutes | Raw native sampling/noise consumption is unchanged by filtering. Before release, retain prior source time; at 15 expose the delayed sample with original measurement time, one announcement and one sampled memory transition. Actual intake follows each native mechanism. Record intervening callback counts. LT1 preserves native fractional boundaries; simglucose refuses an unrepresentable requested time before silent rounding. A new reader must explicitly admit the LT1 grid. Future actual-meal changes cannot alter the pre-event prefix |
| C17 — Failure and partial evidence | Invalid/nonfinite initial state; test-owned failure after two completed intervals; truncated output; native failure plus diagnostic-export failure; cancellation before initialization and while blocked; outer deadline and forced termination. Include complete controls and a terminal callback with a diagnostic-only tail | Bad initialization has no stale rows. Preserve primary error alongside diagnostic error, completed prefix and noncomplete status. Keep every planned attempt and full denominator; unavailable metrics are null. Reject fabricated completion, padded tails and a final command with no completed delivery interval. Trusted readers distinguish inspectable forensic evidence from reconstructible native reports |
| C18 — Ownership and relocation | On the declared host, worker creates observed child/grandchild; the test coordinator separately starts an unrelated sentinel outside the worker ownership tree, with its own OS start identity. Exercise C17 stops, coordinator crash and app-close cancellation through the owner. Copy complete, partial and failed attempts, then reconstruct with retained trusted readers in a fresh process without either engine installed | Observe actual OS start identities; stop exactly owned processes, preserve sentinel and retain escalation evidence. Proposed bound is 40 seconds after stop request: the shared service's default 30-second cooperative grace plus a proposed 10 seconds for outer cleanup/verification. Surviving/unverifiable ownership fails acceptance and prevents terminal sealing. Hash the exact consumed reader/source/input/result bytes; complete supported reports reconstruct byte-exactly, partial/failed evidence retains its admitted status or explicit reconstruction refusal; no supplied code executes on opening |

Proposed short diagnostic attempts have a 300-second outer execution deadline;
the 40-second cleanup bound is separate and is a software acceptance budget,
not a biological or numerical tolerance. The 30-second value is the
[shared service](../shared-project-services.md) default grace, not a measured
total cleanup guarantee. Freeze the process-observation and polling mechanism
before testing it. The existing OT-061 polling limitation for
unobserved orphaning and hostile escape remains explicit; do not claim a hostile
code sandbox. Historical reference deadlines remain their own declared values.
Linux x64 requires a separate host receipt before any new claim; Windows is
outside this first proposal despite unrelated Windows service evidence.

The sampled controller must never run inside a continuous RHS callback.
Repeated/out-of-order RHS probes use the audit's separate pure positive control
and stateful negative control; they do not authorize duplicate sampled updates
or prove arbitrary supplied code pure.

## Verification and remaining OT-062 work

Review this document against the snapshot, pinned source and unchanged policies;
reconcile package/advisory counts, notice and lock hashes, navigation and links.
Run the existing simulator-free audit tests and normal repository checks in the
root tooling environment. The PR handoff records exact revisions, outcomes and
separate technical review. These checks supply no new C15–C18 native result.

Even after gates A–E pass for both engines, OT-062 still needs its integrated
OT-059/060/061 boundary, a second compatible controller and a reusable adapter
template/conformance suite. The subsequent research question and workbench
reuse follow the roadmap. This assessment changes no lock, baseline, tolerance,
model, native runtime, production admission or distribution policy.
