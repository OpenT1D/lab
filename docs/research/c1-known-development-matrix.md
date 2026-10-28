# C1/0.4 — Known-case simglucose development matrix

**OT-019 development, 25 September 2026.** This record declares a diagnostic
matrix before its execution. Its profiles, seeds and A–D conditions have
already been used in M1/M2 work. The matrix is therefore development
material, not a new evaluation or a test of unseen physiology. The
[C1 study design](c1-controller-protocol.md) and
[method record](c1-method-feasibility.md) govern later comparison and freeze
requirements.

## Question and fixed attempts

The [first native example](../c1-simglucose-development.md#local-development-finding)
lost one 3-minute 70–180 interval and gained one below-70 interval versus
unchanged basal-bolus on adult#001/101/B. Examine the action/trace timing,
then measure whether that direction persists across the entire small known
roster. Report both favorable and unfavorable directions; no tuning decision
or superiority claim follows automatically.

The fixed roster is adult#001 and adult#002 × seeds 101 and 102 ×
conditions A–D. Every one of its 16 profile/seed/condition cells has four
planned processes: unchanged M1 basal-bolus, the C1 example trend overlay,
the adapted bounded PID, and one **exploratory overlay adjustment**. The
adjustment raises only the overlay activation target from 140 to 180 mg/dL;
its gain, low cutoff and action bounds remain the example values. This tests
whether suppressing extra commands at modest glucose elevations removes
the low-boundary regression. The same planned cells and saved settings are
used for all four methods; native runs remain separate processes.

The schedule, profile identities and stochastic sensor seeds are paired
within each cell. The reported outcomes are M1's scored-day three-minute
mean subcutaneous interval percentages in 70–180, below 70, below 54 and
above 250 mg/dL. The report also retains full status and completed interval
counts. For each overlay case, it records commanded extra U in warmup and
scored days, the first scored extra-command time, and intervals that cross
below 70 in one paired trace but not the other. These timings describe
association in one simulator; they do not isolate a physiological mechanism.

All 64 cases are written to `plan.json` before execution. Each subprocess
retains its own M1 or C1 artifact bundle and a separate attempt record. A
simulator-free reconstruction verifies the fixed roster, input bytes,
native bundle and command replay, and computes every pair from saved traces.
Any failed, terminated, timed-out or unverifiable process remains in the
planned denominator. An incomplete pair has no invented outcome difference.
The committed evidence index identifies the ignored local store by hashes;
it is not an external backup.

Coverage alone cannot qualify the adapted PID as a **strong comparator**.
That still requires a declared comparable tuning opportunity, matched causal
information and action constraints, numerical checks, and a frozen selection
rule before new-scenario evaluation. The old M1 basal-bolus remains a
historical anchor. Cambridge integration and the exact C1 freeze remain
separate work.

## Execution and results

Run the fixed matrix from a clean checkout with the locked native M0
simglucose environment:

```sh
experiments/m0/simglucose/.venv/bin/python -m experiments.c1.development_study run \
  --output results/c1-known-development
```

`report --study results/c1-known-development` reconstructs the JSON report
without importing simglucose.

The declared matrix ran from clean commit `0c367fc` in the ignored local
directory `results/c1-known-0c367fc`. All **64/64** processes returned zero,
were accepted by their strict M1/C1 readers and completed **960/960**
three-minute intervals. Every manifest records that revision and a clean
worktree. Within each native route the source-hash map was identical across
all cases. Rebuilding the simulator-free report matched the saved JSON
semantically; the [local evidence index](../../experiments/c1/evidence-index.json)
records its plan and report hashes and the report includes the 64 native
manifest hashes. This is reproducible local synthetic evidence, not an
external backup or independent evaluation.

Paired differences below are versus unchanged basal-bolus, in **percentage
points** of the scored day. The four B cells are in profile/seed order
adult#001/101, adult#001/102, adult#002/101, adult#002/102. Signs are
reported by case, not treated as independent people or pooled across
physiological engines.

| Method on missing-announcement B | 70–180 differences | Cells with more below 70 | Cells with more above 250 |
| --- | --- | ---: | ---: |
| Example overlay, target 140 | −0.208, 0, 0, 0 | 1/4 | 0/4 |
| Exploratory overlay, target 180 | 0, 0, 0, 0 | 0/4 | 0/4 |
| Adapted bounded PID | +11.042, −7.917, +37.917, +25.625 | 2/4 | 2/4 |

The original adult#001/101/B loss was one interval: the overlay glucose
fell below 70 at interval start minute **1773** while the base stayed just
above 70. The overlay's first *scored-day* extra command was at minute
**1926**, after this low crossing. Its warmup commands totalled about
**0.191 U**, and its scored-day commands about **0.403 U**. The adjusted
variant reduced warmup extra commands to about **0.007 U** and removed this
threshold crossing; it also gave no in-range gain. The trace timing rules
out a preceding scored-day extra command as the immediate explanation, but
does not prove that warmup extra insulin caused the difference. Other native
state and accumulated effects were not isolated in a controlled ablation.

Across all 16 cells, the example overlay increased below-70 exposure in
**4**, with no below-54 increases; it increased 70–180 exposure in **2**,
decreased it in **3**, and left it equal in **11**. The higher-target variant
had no below-70 or below-54 increases, but gained 70–180 exposure in only
**1/16** cells and in **0/4** B cells. Thus the targeted adjustment removes
the observed low-exposure regression on these known cases but still
provides no B in-range benefit. It is not a successful C1 candidate under
the proposed primary endpoint.

The adapted bounded PID completed all 16 cells, establishing this narrow
software coverage result. Its B in-range direction reversed in one seed,
and its below-70 and above-250 directions each worsened in two B cells.
Across all conditions it decreased 70–180 exposure in **11/16** cells and
increased below-54 exposure by **4.167 percentage points** in
adult#001/102/C. It is therefore **not qualified as the strong simglucose
comparator** by this development matrix. Coverage does not repair those
trade-offs or supply a comparable tuning budget.

The next C1 decision should revisit the control method and comparator
design against these retained negative results before adding Cambridge or
opening a new-scenario evaluation. No evaluation set has been opened, and
no superiority or human treatment result follows from this matrix.
