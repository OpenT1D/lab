# Native adapter contract audit: simglucose and LT1

Date: 1 November 2026. Scope: preparatory OT-062 audit against public base
`5dbdd24703480c7504fce3db6e6867ff33b3ca3e` (merged PR 45).

The existing engine references support two distinct native execution contracts.
They do not establish that the same controller has run on both engines. This
audit proposes one small sampled-controller acceptance question and supplies
invented transcripts that distinguish selected boundary faults. It adds no
native adapter, shared SDK integration or numerical result. The
[roadmap order](../../ROADMAP.md#stretch-and-subsequent-expansion) remains M3
reuse followed by integrated adapter acceptance; preparatory audits may precede
that integration. OT-059 version-1 fixtures, OT-061 services, OT-063 comparisons,
model code, locks, historical protocols and baselines are unchanged.

## Evidence and source key

Evidence labels are independent dimensions: **software** means existing inspected
implementation; **reference** means an already recorded native reproduction;
**fixture** means an invented controlled example checked here; **proposal** means
an unintegrated acceptance boundary; **open native check** means no new native
execution establishes it. Historical private commit/run URLs remain historical
references. This audit did not retrieve or reverify their full local archives.
The [validation guide](validation.md) separates these from scientific validity
and independent human reproduction.

Primary source files below were read at the exact pinned revisions on this
audit date. These are assertions about those revisions; current upstream heads,
additional models/devices and later APIs were not assessed.

| Key | Pinned primary source and inspected responsibility |
| --- | --- |
| S1 | [simglucose env.py](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/simulation/env.py): `reset`, `mini_step`, `step`, history |
| S2 | [T1DPatient](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py): initial state, meal queue, basal and native solver |
| S3 | [InsulinPump](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/actuator/pump.py): rate quantization and limits |
| S4 | [CustomScenario](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/simulation/scenario.py): numeric hours, minute rounding and event matching |
| L1 | [LT1 Simulator](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/Simulator.ts): reset order, native loop, events and component seeds |
| L2 | [Cambridge](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts): equilibrium, units and derivatives |
| L3 | [AbstractODEPatient](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/AbstractODEPatient.ts): native initialization and input/RHS evaluation |
| L4 | [IdealCGM](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/sensors/IdealCGM.ts): five-minute plasma observations |
| L5 | [StaticInsulinPump](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/actuators/StaticInsulinPump.ts): rate/bolus distinction and shortened-step TODO |
| L6 | [LT1 PID](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/controllers/PID.ts): sampled updates and state |
| L7 | [SolverRK1_2](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/solvers/SolverRK1_2.ts): staged derivatives and rejected-step retries |

Local source anchors are [M1 adapter](../../experiments/m1/adapter.py),
[information/controller](../../experiments/m1/control.py),
[outer loop](../../experiments/m1/simulation.py),
[LT1 boundary](../../experiments/m2/cambridge.mjs),
[worker](../../experiments/m2/worker.mjs) and
[supervisor](../../experiments/m2/run.py). Decisions
[0003](../decisions/0003-m1-interval-contract.md),
[0004](../decisions/0004-m2-native-process-tracks.md),
[0046](../decisions/0046-p1-external-controller-boundary.md) and
[0080](../decisions/0080-two-route-contract-packet.md) own existing boundaries.
This proposal does not supersede them or adopt a new shared convention.

## Identity, ancestry and existing evidence

simglucose is Jinyu Xie's version 0.2.11 at
`a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, implementing the UVA/Padova 2008
lineage. Its [MIT declaration](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/LICENSE)
requires retaining the notice. The [asset card](models/simglucose.md) distinguishes
physiology tables, questionnaire/controller assets and device presets; table-level
title and parameter ancestry have not been independently established. Do not
publish these tables or transfer another implementation's regulatory status.
M0 uses adolescent#001; M1 development uses adult#001–002 with fixed Dexcom and
Insulet presets. These are synthetic parameterizations, not sampled people.

LT1 is Heiko Peuscher and contributors' source package 2.1.0 at
`9a6092065bd821f88691cd8d03b0550acd665573`, under its
[MIT declaration](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/LICENSE.md).
The selected Cambridge/Hovorka model is distinct from LT1's convenient UVA demo.
The [asset card](models/lt1-cambridge.md) retains Hovorka/Andersen ancestry and the
dated parameter-source follow-up. MPC is LT1's implementation of the cited
Hovorka 2004 method, with IFAC reference settings; paper-identical behavior and
meal-study biological validity have not been established. Cambridge's single
reference is not matched to any simglucose profile or cohort.

The [M0 record](m0-reproduction.md) reports native reset/new-process references
for each engine, and [M1](m1-reproduction.md) reports direct/native equivalence,
historical collections and four retained development PID stops. The
[M2 record](m2-reproduction.md) reports controlled LT1 PID/MPC equality, separate
metrics, 648 planned evaluation cases and complete failure accounting. Its
Cambridge cases remain structural demonstrations; the two PID implementations
differ in formulas, target, initialization and basal feed-forward. The
[IV-001 record](internal-verification-results.md) adds bounded refinement,
initialization, mutation and robustness evidence, with sensitivity and failures.
These records are inherited evidence, not new runs performed for this audit.
The canonical [M1](../m1-tutorial.md), [M2](../m2-tutorial.md) and
[verification](../internal-verification.md) guides retain their exact commands.

Root Python is tooling and standard-library analysis. Historical simglucose has
its own Python 3.12 lock (including NumPy 1.26.4, SciPy 1.13.1, pandas 2.2.3 and
runtime setuptools 80.9.0). That lock also contains the separately pinned
glucosim source; its presence does not authorize a new combination here.
LT1 uses Node 22.22.2, TypeScript 5.7.3 and ts-node 10.9.2 under its separate
npm lock. The selected headless native graph uses relative source imports;
that observation says nothing about the complete LT1 frontend or other
controllers. [pins.json](../../experiments/adapter_audit/pins.json) retains both
lock paths and SHA-256 identities for these fixtures.

The [public setup boundary](../publication-security.md) excludes automatic
historical native installation. The separately admitted M4 successor does not
admit new M1/M2 execution. No native dependencies were installed here. Future
native checks need a separately assessed locked environment and applicable
source/runtime/table-rights clearance; an old tutorial command is insufficient.

## Comparison matrix

| Contract | simglucose pinned path | LT1 Cambridge pinned path | Evidence status and consequence |
| --- | --- | --- | --- |
| Initialization/reset/basal | S2 restores table state, digestion bookkeeping and dopri5; random initialization is off in M1. Native basal uses `u2ss * BW / 6000` U/min. S1 resets patient, sensor, pump and scenario. | L1 resets solver, sensor, controller, actuator, then patient. L3 initializes from an explicit state if supplied, otherwise the computed equilibrium; L2 derives insulin/equilibrium from Gpeq. M2 fixes Gpeq at 124.91784824923789. | Software + reference. Preserve native reset including sensor consumption. Neither the 24-hour initialization nor default state proves convergence. A controller's first output need not equal the plant equilibrium infusion. |
| Clock and cadence | Synthetic naive midnight 2024-07-20; native minute advances, three-minute outer intervals. S4 interprets numeric event times as hours and rounds to minutes; M1 divides elapsed minutes by 60. | UTC 2024-07-20; native one-minute maximum outer step shortened by component/event boundaries, five-minute sensor/control cadence; L7 adaptive RK1/2 stages. | Software + reference. No timezone conversion between synthetic clocks, cadence coercion or universal step API. Fractional event support in a native test is broader than M2's public reader grid. |
| Actual and announced events | S4 releases a meal amount to S2's native eating queue (5 g/min); `CHO` history is an outer mean of event input, not consumed grams. M1 releases announcement amounts separately at interval start. | L1 ingests `carbs/duration` g/min, with meal-start amount and announcement history separate. M2 fixes duration 15 min; MPC retains previously permitted announcement history for prediction. | Software + reference. Same intended totals do not imply identical absorption. A once-delivered announcement may remain history; never add its grams to actual intake. |
| Measurement and availability | S1 initial BG is a subcutaneous point; later BG and CGM summarize the preceding three native minutes. `reset` calls sensor measurement twice at zero. M1 masks after generation, holds the original source time. | L4 gives ideal plasma Gp every five minutes; callback points occur more often. Sensor boundary generates before filtering and retains last released source time. | Software + reference; separate measurement/availability timestamps are a proposal. Existing D is masking/hold, not arbitrary delayed delivery. No plasma/tissue conversion follows from equal mg/dL. |
| Observation space | Controller gets copied CGM, observation/source time and availability plus permitted new announcements; BB has fixed profile assets. Native history/state is diagnostic only. | Bounded controller gets copied CGM accessor and permitted announcement history; the native callback retains state and raw samples only for diagnostics. | Software + reference. The unrestricted upstream info/scenario objects exceed the causal contract. Proposal gives no latent state, future events, reward or live native object. |
| Action units and delivery | S3 basal and the field named bolus are both U/min; native quantization/clipping remain. Completed interval delivery integrates modeled rate times minutes. | L5 `iir` is U/h, `ibolus` is U; pump quantizes and upper-bounds, but lacks a lower clamp. Negative modeled delivery fails M2. Bolus duration under early callbacks is unresolved. | Software + reference. Proposal supports nonnegative basal rate only: U/h divided by 60 for simglucose; no dose conversion. Preserve commanded versus modeled delivery and omit terminal commands. |
| Controller state/order | M1 resets once; observes/announces/commands, then native step, then checkpoints completed interval. No reset at scoring. | L1 advances patient with prior medication, then sensor, controller, pump, callback. L6 update is called on outer callbacks but changes native PID state only at its sampling times. | Software + reference. Proposal mutates sampled state exactly once per declared control tick; intervening LT1 callbacks hold output. There is no universal common PID. |
| Solver and process ownership | SciPy dopri5 and native patient own physiological state/integration. M1 owns outer information/control schedule. | Simulator and native solver own event integration. L3 passes time-dependent input into staged derivatives; L7 may retry at earlier stage times. | Software. Stateful sampled controller must never run inside continuous RHS/input callbacks. Host process scheduling owns whole attempts, not physiological steps. |
| Seeds/repeat | M1 sensor seed is explicit; unchanged input/environment reset and process replay are reference checks. Changed seed changes the stochastic sensor, not necessarily every signal. | L1 uses `seed || 1`, hence zero aliases one, with offsets +1 sensor, +2 controller, +3 pump, +4 patient. Ideal-device M2 is one deterministic parameterization. | Software + reference. Reject ambiguous seeds in the proposal. Seed/input changes create new identities; distinct seeds need not yield distinct deterministic traces. |
| Failures and partial output | M0 native runner historically continues despite terminal flags; M1 stops after its terminal interval. Valid completed trace excludes failed diagnostic-only tails. | Worker writes native diagnostics before validation, then validated points. Supervisor retains status, errors and partial evidence; a full point set alone is insufficient. | Software + reference. Preserve these different termination contracts. The fixtures only check transcript accounting, not actual interruption. |
| Timeout/cancel/cleanup | M1 catches deadline/signals and retains completed checkpoints; hard kills remain unfinished. | M2 kills/waits for its immediate child; worker detects a missing supervisor at the next callback. | Software + historical reference. This does not prove arbitrary descendant cleanup, prompt cancellation in a blocked solver, Windows ownership or SDK integration. New OT-061 lifecycle tests remain open native/host checks. |
| Identity and reconstruction | Saved input/protocol/lock, installed code/table hashes, effective settings, diagnostics and analysis revision; M1 reader verifies consumed bytes. | Setup checks exact clean upstream Git revision including ignored extras; worker inventories source and npm packages; M2 reader verifies sealed and partial bytes. | Software + reference. `python -S` reconstruction is already recorded. Fixture identity checks are synthetic; they neither execute readers nor authenticate supplied artifacts. |

L3's profile calculation evaluates parameters at the current local midnight.
Fixed Cambridge defaults underpin the retained reference; time-varying
parameters, other timezones and arbitrary profile replacement need explicit
checks before support. Do not describe the native profile call as purely a
function of the frozen UTC start for those untested configurations.

## Smallest proposed acceptance boundary

Question: **does a sampled rate controller consume only released observations,
update its memory once per control tick, and issue a correctly translated basal
rate through each intact engine?** This is a causal execution acceptance
question, without a controller efficacy or pooled glucose estimand.

Choose one invented diagnostic controller, **lagged proportional basal / audit-1**.
It has one memory value `p`, initialized to the frozen target 120 mg/dL, plus
the last consumed measurement timestamp. Before each command, select the newest
measurement whose availability time is no later than the tick; retain its
measurement timestamp and mark whether it is new to this controller. On a new
sample, command `clip(b + k * (p - 120), 0, 3)` U/h, then set `p` to the released
glucose. If no new sample is available, command `b` and retain memory. A released
older sample must never displace a more recently measured released sample.

Here `k = 0.01 U/h per mg/dL`; `b` is an explicitly frozen rate in [0,3] U/h.
These constants are invented diagnostic settings, without treatment meaning.
The executable controls use **b = 1.2**, which is not a claimed native basal
for either engine. For a future native case, separately declare and record
the chosen b and its relation to native initial/equilibrium infusion, without
altering the native initial state to fit the controller. Start with one existing
development parameterization per engine and the unchanged native devices.
Select checks before running it and preserve the denominator if it fails.

simglucose calls at elapsed 0,3,6,… before stepping; LT1's future wrapper calls
the same algorithm at elapsed 0,5,10,… after native sensor generation and holds
its output on other callbacks. Keep native sample meanings, pumps and solvers.
This is the same event-indexed policy at different native cadences, with different
observation compartments; it cannot isolate physiological differences or supply
a matched elapsed-time feedback experiment. A question requiring identical
sampling or the same physiological compartment is refused at this boundary.

Map the output solely to simglucose basal U/min (`rate / 60`, bolus rate zero)
or LT1 `iir` U/h (no `ibolus`). This is a dimension-preserving rate conversion;
it is not an insulin dose or a conversion between glucose compartments. Keep
command and native modeled delivery separately. Existing M1/P1 and M2 controller
allowlists do **not** admit this controller; they must not be bypassed here.
A later reviewed adapter extension must retain their historical paths and
test direct native versus wrapped construction under this exact new policy.
One native run, one controller and their parity checks must precede any second
controller, broader question or claim that OT-062/LAB-A–C is completed.

Actual events remain engine-owned; copied newly released announcement IDs can
refer to frozen announcement records (id, intended start, availability, grams).
This controller ignores announcements, but transcript delivery still checks their
causal release exactly once. No actual-event table enters its inputs. Future
native A/B runs may differ in physiology after actual meals even when no
announcement is released; the causal invariance check applies to identical
observation prefixes and controller information, not entire glucose trajectories.

No shared decision record is adopted because this is a proposal/fixture oracle,
not an interface or scientific-convention change. Integrated acceptance will
need its own bounded decision, OT-059 capability binding, OT-061 process owner,
OT-064 trusted reader and OT-063 comparison scope.

## Conformance cases selected before new execution

[cases.json](../../experiments/adapter_audit/cases.json) contains two invented
positive transcripts. [check.py](../../experiments/adapter_audit/check.py) is a
standard-library Decimal oracle for this packet only, not a native runner,
generic artifact reader, pump simulation or production controller. The
[tests](../../tests/test_adapter_audit.py) pass an unmodified control before
each transcript mutation and require a specific rejection reason. A syntax
error, import failure or timeout cannot count as detection.

Each positive input uses four ticks and samples 120,180,60,150 mg/dL measured
at ticks 0,1,2,3. Availability is at ticks 0,1,3,4. Thus tick 2 holds the
tick-1 observation, tick 3 releases the delayed tick-2 value, and the final
sample remains unavailable during all calls. Commands are independently
calculable as 1.2,1.2,1.2,1.8 U/h, with memory-before 120,120,180,180.
The 40 g actual meal starts at tick 2; its distinct 20 g announcement becomes
available at tick 1. This deliberately includes a permitted announcement of a
future event, distinct from leaking an unannounced future event.

The invented delivery rates differ from commands: simglucose-unit rates
0.018,0.020,0.020,0.025 U/min over 3 min give **0.249 U**; LT1-unit rates
0.9,1.2,1.2,1.5 U/h over 5 min give **0.400 U**. These are arithmetic controls,
not outputs of the native pumps. The fixture endpoint has no terminal command.

| Case and explicit input/mutation | Expected behavior and independent oracle | Refusal reason or acceptance; evidence |
| --- | --- | --- |
| C01: both unmodified four-tick transcripts | Above hand-calculated states, commands and delivery amounts; source and lock identities match the frozen packet | Accept; fixture |
| C02: repeat the transcript; then inject previous state 60 at reset | Identical repeat result; first memory must be target 120 | `controller-state`; fixture. Real reset/sensor/solver repeat is an open native check |
| C03: expose the tick-2 raw 60 before availability; add patient state | Only the newest released sample and allowlisted record cross the boundary | `causal-observation` / `row-fields`; fixture |
| C04: change unavailable final sample 150 to 999 and reidentify input | Same controller prefix; future unavailable data cannot affect the result | Accept unchanged prefix; fixture. Native process comparison remains open |
| C05: mark held observation fresh; relabel delayed measurement as current; use integer 1 as freshness | Hold retains original time; measurement time differs from availability; freshness is boolean | `causal-observation`; fixture |
| C06: release announcement at tick 0 or again at tick 2 | IDs released once, at first eligible tick; retained history is distinct | `announcement-delivery`; fixture |
| C07: change actual meal 40 to 80 g, preserve released observations/announcement and reidentify input | Controller transcript unchanged; no equality claim for future native physiology | Accept; fixture |
| C08: use current 180 before computing tick-1 command, giving 1.8 | Command uses prior memory 120, hence 1.2; only then update state | `controller-order`; fixture |
| C09: duplicate or reverse a sampled update | At most one memory transition at exactly each declared tick; no retry inside this sampled callback | `rows` / `update-clock`; fixture |
| C10: label next call minute 180; action unit U; divide rate by sample duration; request bolus or extra field | Clock is elapsed minutes; rate conversion preserves dimensions; this contract accepts basal rate only | `update-clock` / `action-unit` / `rate-conversion` / `unsupported-action`; fixture |
| C11: seed 102 or basal 2 without new identity; change source/lock; boolean seed; unavailable initial sample | Input/source/runtime identity changes; no ambiguous seed or silent initial fill | `identity` / `seed` / `initial`; fixture. Actual seed response and basal residual are open native checks |
| C12: one completed interval with failed/deadline/unfinished status, then false completion or no reason | Keep observed prefix and noncomplete state; undefined delivery with no observed interval is null | Accept prefix; `completion` / `failure-reason` / `undefined-amount`; fixture |
| C13: negative/boolean delivery, NaN command, or sum 4.8 commanded rates as U | Finite numeric values, nonnegative modeled delivery, integrate actual completed duration only | `delivery` / `command` / `delivery-amount`; fixture |
| C14: inspect/rebuild packet using Python `-S` | No simulator/controller imports; receipt binds exact fixture input bytes | Accept; fixture only, not native-reader compatibility |
| C14a: initial sample 180,1000,0 with unchanged reset memory 120; then substitute initial sample for reset memory | First command stays 1.2; second command is respectively 1.8,3,0 U/h (0.03,0.05,0 U/min); upper and lower clips have hand-calculated positive controls | Accept controls; `controller-state` for wrong initialization; fixture |
| C14b: target 121, gain 0.02 or cap 4, with consistently reidentified input; boolean observation timestamps at zero | This packet fixes audit-1's target/gain/cap; equal-looking booleans are not numeric times | `controller-settings` / `causal-observation`; fixture, added after technical review |
| C14c: b=0.6 and first measured glucose 0; four commands 0.6,0,0.6,1.2 U/h | Tick-1 preclip rate is −0.6, so the zero command requires the lower clamp; delivery controls give 0.120/0.200 U on the two cadences | Accept; fixture added after a lower-clamp source mutation survived the first clipping control |
| C15: native reset twice and fresh process with fixed seed/source/input; altered seed and altered input as separate cases | Compare direct and wrapped initial state, reset sensor-call sequence, trace, delivery and status; old M0/M1 historical checks remain independent oracles | Open native check under new controller; existing references cover their own controllers only |
| C16: native off-grid event, masked sample and delayed release at a control tick | Native event times/intake remain unchanged; generate sensor before filtering, record actual versus announced events and availability; check callback count separately from control updates | Open native check; use M2 fractional-event test as an inherited example, not a claim that its reader accepts new grids |
| C17: initialization failure, missing/truncated trajectory, terminal interval plus diagnostic tail, timeout/cancel/hard kill, diagnostic export failure | Zero stale rows after reset failure; completed records only; primary error preserved; all planned attempts/unfinished cases retained; no padded tail or success inferred from length | Open native/reader/process checks for new integration; inherited M1/M2 tests retain the old oracles |
| C18: worker owns child/grandchild; unrelated sentinel process; cancel during initialization and blocked native work | Bounded stop of exactly owned processes, explicit deadline/escalation status and retained prefix; sentinel survives; inspect restart/relocation without native execution | Open per-host OT-061/064 check; historical immediate-child/callback evidence does not close it |

Continuous RHS conformance is deliberately separate. Under
[decision 0048](../decisions/0048-m4-causal-secretion-intake.md), an RHS returns
derivatives/output from the current time/state without hidden mutable history.
Existing `test_example_baseline_and_out_of_order_purity` and
`test_bad_source_results_and_hidden_state_fail_preflight` in
[the M4 source tests](../../tests/test_m4_causal_secretion.py) supply a passing
pure control and a rejected call-counter source for repeated/out-of-order probes.
They can run without native physiology. They do not make the sampled diagnostic
controller a valid RHS, prove arbitrary supplied code pure, or establish native
solver conformance. C09 requires sampled duplicates to fail; an RHS must tolerate
repeated/stage-reordered evaluation of identical arguments. Preserve the native
solver as the only integrator and never mutate sampled controller state there.

## Verification receipt and remaining gates

Checks were selected before creating new transcript output: positive arithmetic,
as-of release, state-update order, rate translation, all-attempt accounting,
identity mismatch and simulator-free inspection; native C15–C18 were selected
but left unrun. The root commands are:

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -p test_adapter_audit.py -v
uv run --locked python -m unittest discover -s tests -p test_m4_causal_secretion.py -v
uv run --locked python -S -m experiments.adapter_audit.check
uv run --locked python scripts/check.py
```

The initial targeted audit run passed 14 tests. A separate technical agent
review reproduced two gaps: boolean observation times compared equal to numeric
zero, and a reidentified cap-4 policy passed controls that never reached a clip.
The checker now validates all observation numbers strictly and fixes audit-1's
target/gain/cap. Added non-target initialization and both clipping controls,
plus the review's negative cases, passed in the subsequent 16-test run.
Review then removed the lower clamp in memory: that mutation survived because
the initial zero-glucose control reached exactly zero before clipping. A new
b=0.6 control reaches a strictly negative preclip rate and requires zero output;
the expanded suite has **17 tests**. The original endpoint control is retained.
The first added clipping test exposed a float representation difference from
computing `1.8 / 60`; the control now uses the independently calculated literal
0.03 U/min. These Decimal checks cover selected exactly represented fixture
values; they do not prescribe a tolerance for arbitrary binary native outputs.
Direct/wrapped native comparisons must retain the applicable historical exact
checks and select any additional numerical oracle before execution.

Final revision, full-check outcome, exact commands,
skips and separate technical review are recorded in the PR handoff. The author
owns the sole final full repository check; the reviewer runs targeted checks.
Local results are not hosted CI. Agent review is technical review, not an
independent human reproduction or biological assessment.

Remaining gates include admission of a new exact native environment, the new
controller's direct/wrapped parity and reset, event/availability observations,
native pump mapping, actual process cleanup per host, complete trusted-reader
and relocation checks, then integrated SDK/CLI/workbench acceptance. A second
controller/question and two-engine study remain unimplemented. No baseline,
tolerance, numerical criterion, runtime lock or rights claim was relaxed.
Full parameter records, restricted reports, private inputs and credentials stay
outside Git and public logs; this packet contains only invented inputs and
public source/lock identities.
