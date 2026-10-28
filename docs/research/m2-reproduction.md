# M2 implementation and evidence

**M2 software implementation is complete; independent human reproduction remains open.** [Decision 0004](../decisions/0004-m2-native-process-tracks.md) selects bounded native process tracks after reassessing LT1/APS against the implemented M1. [OT-014](m2-protocol.md) specifies development/evaluation separately from OT-001. The [canonical tutorial](../m2-tutorial.md) owns installation, execution, freeze and reconstruction instructions.

Scheduling update, 14 September 2026: [decision 0005](../decisions/0005-internal-verification-and-external-review.md) moves independent reproduction to later external review without closing the original criterion or changing any result below. Internal verification and M3 preparation may proceed.

## Established integration evidence

PR [#13](https://github.com/OpenT1D/OpenT1D/pull/13) introduced the decision, protocol and host feasibility probe. All four jobs passed on exact head `dbc6d64774d7d35306d98ce3643ac9d0f1687936` in [CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34749994194), and on merged main `17a682c3150c97d6810cb0f3a80bda6905d33793` in [main CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34750139744).

PR [#14](https://github.com/OpenT1D/OpenT1D/pull/14) integrated Cambridge with controlled native LT1 PID/MPC, separate point metrics, a process supervisor and saved-artifact reader. All five jobs passed on exact head `5d3a8909829b655b38056b7900773af70b3b5a3d` in [CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34750713445), then on main `cb5b552bc63bb3cd203f34562a7b071ed42e76d3` in [main CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34751240309). The added native suite has thirteen tests, including all eight controller/condition trajectories against direct execution and native reset, original M0 output, event/amount checks and information boundaries.

The committed local and exact-head Linux MPC/A point trace has SHA-256 `6bd91394a0fc726392285eb8758f3c112a0a81a448854ac559804f971d31f1ec`; full native callbacks have SHA-256 `e66d7aad06f6bf38d56823dd4b16c51d8a6b83e512b28a49e8de4ae7dd678e2e`. Native source inventory, configuration, lock and effective settings match. These previously retained outputs seed the new M2 historical check. M0/M1 baselines remain unchanged. No numerical tolerance or new-run enrollment is used.

Process verification demonstrated exact new-process replay and reconstruction with `python -S`, plus retained SIGINT, SIGTERM and deadline attempts. A local SIGKILL review retained the unsealed partial trace, left the killed supervisor unfinished and confirmed that its Node worker stopped at the next native callback. This does not guarantee storage or power-failure recovery.

## Review findings and preserved attempts

The initial historical fixture used a different JSON field insertion order for the original meal announcement. All 1,441 parsed callback records were exactly equal; only serialization order differed. The fixture was restored to the original order and matched the unchanged historical digest. No controller, equation or tolerance changed.

Draft reconstruction failures exposed a Python tuple/JSON-list mismatch in comparison metadata, alongside tracked source edits during ongoing authoring runs. M2 now uses JSON-stable comparison fields, with a full-report round-trip regression check. Review also found that the new simglucose worker initially omitted its actual Python version, platform and architecture; those fields are now recorded and mandatory even for partial traces. The failed attempts and logs were retained. Dirty authoring attempts remain diagnostic evidence, not accepted clean reproductions. Definitive clean committed development runs subsequently passed historical checks and exact JSON/Markdown reconstruction. No evaluation cases were executed before these corrections.

## Observed frozen evaluation

The 648-case study finished with 384 complete runs and 264 retained native simglucose PID terminations; no case was removed, left unattempted or reported as an execution error. The study status is `finished_with_failures`, not `completed`. All 320 simglucose basal-bolus runs completed; PID completed 56 of 320. All eight Cambridge runs completed. Each A–D condition contains 94 complete and 66 terminal simglucose cases, plus two complete Cambridge cases.

Of the 264 terminal runs, 132 stopped before scoring and 132 supplied only partial scored coverage. Entirely unobserved scored delivery is null in all 132 cases, not zero insulin. PID comparisons retain only 14 of 80 planned seed pairs per contrast, from four of eight profiles: adult#004 (one pair), adult#005 (four), adult#008 (six) and adult#010 (three). These are selected complete-pair descriptions; they cannot establish performance across the planned population.

The following table shows changes in each track’s own 70–180 mg/dL exposure summary, in percentage points (pp), rounded to three decimals. simglucose summarizes mean subcutaneous intervals; Cambridge uses plasma point quadrature. Profile ranges are ranges of within-profile seed means, not confidence intervals. Full per-seed ranges, low-glucose outcomes, delivery, runtime, coverage and every exclusion remain in the saved report.

| Engine / controller | Condition versus A | Median change (pp) | Profile range (pp) | Complete / planned pairs | Included / planned profiles |
| --- | --- | --- | --- | --- | --- |
| simglucose / basal_bolus | B | -63.469 | -67.042 to -47.062 | 80/80 | 8/8 |
| simglucose / basal_bolus | C | -20.979 | -33.646 to -1.708 | 80/80 | 8/8 |
| simglucose / basal_bolus | D | +0.000 | +0.000 to +0.000 | 80/80 | 8/8 |
| simglucose / pid | B | +0.000 | +0.000 to +0.000 | 14/80 | 4/8 |
| simglucose / pid | C | +0.000 | +0.000 to +0.000 | 14/80 | 4/8 |
| simglucose / pid | D | -0.069 | -2.083 to +0.347 | 14/80 | 4/8 |
| lt1_cambridge / lt1_pid | B | +0.000 | +0.000 to +0.000 | 1/1 | 1/1 |
| lt1_cambridge / lt1_pid | C | +0.000 | +0.000 to +0.000 | 1/1 | 1/1 |
| lt1_cambridge / lt1_pid | D | +0.069 | +0.069 to +0.069 | 1/1 | 1/1 |
| lt1_cambridge / lt1_mpc | B | -4.931 | -4.931 to -4.931 | 1/1 | 1/1 |
| lt1_cambridge / lt1_mpc | C | +0.347 | +0.347 to +0.347 | 1/1 | 1/1 |
| lt1_cambridge / lt1_mpc | D | +0.417 | +0.417 to +0.417 | 1/1 | 1/1 |

Complete loss of announcements reduces the in-range summary for both meal-aware complete systems shown here. Half announcements have opposite aggregate signs for simglucose basal-bolus and Cambridge MPC. Masking also shows opposite signs between the distinct PID implementations, with a within-simglucose profile sign reversal. Those observations describe complete systems with different controllers, targets, compartments and populations; they do not isolate a physiological cause or imply that withholding information improves treatment.

Within the simglucose complete-pair subset, the basal-bolus/PID in-range ordering reverses across A–D for adult#005 and adult#010. Four evaluation profiles have no complete controller pairs, so their ordering remains unassessable. Cambridge has no in-range rank reversal in its one structural case; no between-profile uncertainty or absence of population reversals can be inferred from that singleton. There is no pooled model/controller ranking.

The validated freeze has SHA-256 `caa698db3da0d316d8938e97b798cabf3ff8b5079d27f827988b0323cbd6aee7`. The verified evaluation report JSON has SHA-256 `d0b2a98345485340ef7ec42e5513babc9d240026a08dd520525a73715e79774a`. All 648 cases passed strict artifact reconstruction. JSON and Markdown were rebuilt byte for byte with `python -S`, including from a separate checkout without installing either engine or its isolated dependencies. These hashes identify this saved study; runtime/provenance bytes need not match a new execution.

Independent human reproduction remains open. A different process, platform, CI run or AI session does not close it. No patient records or data access were obtained, no release or public archive was published, and no biological or clinical validation is claimed.

The [M2 index](../../experiments/m2/evidence-index.json) identifies nine verified bundles in the maintained main checkout's ignored `results/m2-archive`. Final documentation-PR/main CI bundles added after this record use a separate local `supplemental-index.json`, verified by the same archive tool; do not blindly add overlapping inventories. Use the original archive verifier and retain both bundle and inventory when transferring them. Local retention is not an external backup.

## Frozen study implementation

PR [#15](https://github.com/OpenT1D/OpenT1D/pull/15) adds the two-track dispatcher, strict simglucose artifact reader, complete schedules, freeze gate, conditional comparisons and canonical tutorial. All five jobs passed on exact head `7672d115bb9d94c6f20719dbc10ee2be9afe5cc5` in [CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34752424190). The merged main is `d44ea126ee5b99764c6a9cd75d4df39bb9ea8f6a`; all five jobs also passed in its separately checked [main CI](https://github.com/OpenT1D/OpenT1D/actions/runs/34753228486).

The definitive local development/native verification and evaluation use the exact clean PR head above. The freeze was written after its local and Linux checks passed. No settings or analysis changed after evaluation began. A documentation-only successor does not replace this recorded execution identity: reproduce the frozen checkout, not an arbitrary later `main`.

The local 40-case development study completed 28 simglucose and all eight Cambridge runs, retaining the four original simglucose PID terminal cases. Every simglucose initial/trace digest matches the complete historical Mac M1 collection; Linux matches the complete `linux_final` collection. Cambridge's retained PR #14 native and point digests match exactly. Both platforms reconstruct the entire development JSON and Markdown report byte for byte with `python -S`. Neither a tolerance nor a baseline update was needed.

The PR #15 final checks comprise 51 repository tests, 11 M0 Python tests, 12 M1 native tests, 10 LT1 tests and 13 M2 native tests, plus actual native reproductions and full development studies. Native equivalence includes all eight controlled Cambridge combinations, original M0 reference output, reset, shortened events and masked information. Separate process checks cover fresh execution, SIGINT, SIGTERM, timeouts and simulator-free reconstruction. CI installs isolated locked environments from clean checkouts; no simulation dependencies were added to root tooling.

## Acceptance mapping

| M2 requirement | Demonstrated result | Scope or remaining limit |
| --- | --- | --- |
| Reassess the host against M1 | Decision 0004 compares LT1, APS and bounded native processes; the native reference feasibility probe agrees exactly | APS is source-reviewed, not a second fully built host |
| Second physiological family | Native LT1 Cambridge/Hovorka runs alongside the pinned simglucose UVA lineage | One Cambridge parameterization, no invented paired patients |
| Preserve native behavior | Direct/bounded/reset equality across all eight Cambridge configurations; historical M0/M1/M2 outputs and fresh processes | Same-configuration software equivalence, not equality between models |
| Explicit combinations and useful rejection | Strict engine/profile/controller/condition/seed validation; unsupported profiles, devices and bolus-producing combinations fail with retained errors | Bounded protocol, no universal plugin API |
| Keep coupled engines intact | Native equations, solvers and loops remain owned by their engines; the supervisor schedules whole runs | MPC's private predictor is an estimator, not duplicate subject physiology |
| Preserve scientific intent | Both tracks implement the same intended meals, initialization and A–D information changes | Native ingestion, targets, cadence, compartments and population differ visibly |
| Suitable stronger published reference | Native LT1 MPC_Hovorka2004 integrated with recorded IFAC settings and constrained observations/history | Published-method structural reference; paper-identical behavior, optimized head-to-head superiority and clinical validity are not established |
| Separate development and evaluation | Exact clean commit, protocol, source and locks frozen before 640 unused simglucose cases | Cambridge's eight repeats remain structural development; no tuning or invented held-out cohort |
| Uncertainty, reversals and failure coverage | Complete-pair seed ranges, equal-weight profile medians/ranges, sign/rank reversals, per-condition statuses and exclusions | Conditional descriptive comparisons; no pooled glucose/controller ranking or physiology-only causal claim |
| Time, amount, signal and lifecycle checks | U/h integration over actual duration, final-command exclusion, fractional event fixtures, once-only announcements, post-generation masking, finite states and partial-run tests | Public Cambridge protocol fixes its one-minute callback grid; ideal sensing supplies no stochastic cohort evidence |
| Artifact reconstruction | Inventories and exact consumed bytes checked, including unsealed input; JSON/Markdown rebuilt with `python -S` | Retain the complete study and recorded analysis checkout |
| Clean installation and regression protection | Five CI jobs install locked runtimes and retain all original M0/M1 checks | Passing CI is software evidence, not biological validation |
| Evidence preservation | Checked bundle and inventory hashes in the M2 index; original M0/M1 stores reverified | Local retention is not public distribution or an offsite backup |
| Independent human execution | Canonical tutorial, exact execution commit and result template prepared | **Open: another person has not executed and recorded the protocol** |

## Independent reproduction packet and limits

Use clean commit `7672d115bb9d94c6f20719dbc10ee2be9afe5cc5`, Python 3.12.13, uv, Node 22.22.2, Git, and the locked environments. The [tutorial](../m2-tutorial.md) owns all installation and execution commands. It specifies the original M0/M1 checks, the native M2 suite, process verification, 40-case development, freeze, 648-case evaluation and reconstruction without a simulator. Preserve complete study directories, per-run logs/manifests/configurations/runtime/initial/trace/result files, the freeze and both verification records. The [result template](../../experiments/m2/reproduction-result.example.json) records the person's identity, environment, exact commit, commands, outcomes and deviations. Do not prefill a person's name or success.

A second person should run those commands, compare historical checks and observed coverage with this record, retain their own failed attempts, and record discrepancies before drawing conclusions. Identical frozen reruns are reproduction, not permission to retune on the inspected evaluation. Any later correction affecting interpretation must disclose evaluation reuse and preserve the original results.

The MPC predictor shares Cambridge ancestry with the simulated plant. This study therefore does not establish robustness to physiological model mismatch. The native PID implementations also differ in formula, basal feed-forward, gains, targets and state initialization; their shared label does not make them equivalent.

The execution and self-review here were AI-assisted. No other person, outside researcher or independent reviewer is claimed. No direct messages or reproduction invitations were sent. No patient records, access applications, parameter redistribution, public release, DOI, clinical validation or stable API were added. The existing setuptools runtime advisory remains documented in the [maintainer guide](../maintenance.md#m0-runtime-compatibility).
