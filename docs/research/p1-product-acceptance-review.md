# P1 — Product acceptance review packet

**Status:** the bounded software evidence is complete for internal technical
use. On 26 September 2026, an authorized human project representative approved
a **conditional rights decision** for one exact local Git bundle and one named
internal technical participant. No independent tester is currently available,
so no transfer, participant exercise or P1 product-acceptance decision has
occurred. This separation follows the
[P1 roadmap](../../ROADMAP.md#p1--first-usable-research-product).

## Declared offering and task

The proposed narrow offering is a versioned local checkout and English guide
for one synthetic M1 research task. An intended simulation researcher or
algorithm developer who did not build P1 uses the supplied, source-pinned
GlucoSim proportional controller bundle. They inspect its declaration,
install the locked dependencies, run conditions A–D on `adult#001`/seed `101`,
reconstruct the report, replay the actions, and explain its evidence limits
without live coaching. The [participant guide](../p1-acceptance-exercise.md)
is the canonical exercise. The [P1/0.4 technical record](p1-internal-followup.md)
records the clean internal run. The earlier [PID worked example](../p1-upstream-pid-tutorial.md)
remains a separate source-intake reference.

The reviewed distribution is a local Git bundle of commit
`1abe1b68401688fd1fa1a13e5b9a2941147015a8`, SHA-256
`7ed481e4f6f34a4e289f8415859aa5aae95fea1dea5a22c1dc658cc3b27afbda`,
to one named researcher for internal technical evaluation. A public source
repository, an archive including run artifacts, and a bundled runtime contain
different assets and need separate review. The existing Git remote does not
contain this local revision; use the exact reviewed bundle for handoff.
No hosted service, installed application, stable general API, human dataset,
medical-device connection, or clinical dosing use is included in this task.

The human review considered the bundle's full reachable repository history
and conditionally cleared this narrow handoff. Before supplying it, record
the named eligible participant, internal purpose and access conditions. The
facilitator verifies the bundle, then has the participant clone it into a
clean directory.
The participant records `git rev-parse HEAD` and compares it with the handed
off commit before following the guide. The conditional decision does not
permit public release, another recipient, a prebuilt runtime or sharing a
generated study.

## Evidence available before human review

| Roadmap criterion | Current evidence | Outstanding record |
| --- | --- | --- |
| Declared user and research task | The narrow role, four conditions, supported setup and report questions are fixed in the participant guide | Identify an actual eligible participant and record prior involvement |
| Supported local workflow | P1/0.1–0.4 provide locked installation, two-file source preflight, complete case accounting, action replay and simulator-free reconstruction | Observe the participant's uncoached execution, failures and interpretation |
| Source and method behavior | GlucoSim commit, upstream file hash, 3-minute held-CGM behavior, U/hour-to-U/min conversion and method-specific tests are in the P1/0.4 record | Human review of intended-use wording and support scope |
| Rights and notices | Human conditional decision below for the exact internal Git bundle; repository and upstream license declarations, hashes and asset origins are recorded | Name recipient and enforce the conditions; table-level provenance remains unresolved and public/runtime rights are unreviewed |
| Product claim | Proposed only for this checkout-based synthetic task | Maintainer reviews both human records and writes a dated accept, revise or reject decision |

Passing CI or reproducing the maintainer's report does not establish
independent usability. One exercise also does not establish demand or broad
compatibility. Preserve a failed or assisted attempt as evidence; do not
convert it into a passing result by silently changing the participant's task.

### Facilitator technical rehearsal, 26 September 2026

A clean worktree at `1a84540166676be5d0c72c135672c05808e64c19` ran the
participant commands as a **maintainer rehearsal**, with `uv 0.11.16` and
Python 3.12.13 on macOS arm64. The first draft used a bare `python --version`;
that command was unavailable on this host, so the guide now queries the
Python selected by `uv` after sync. The locked root and native environments
installed; the GlucoSim preflight returned `contract_checked`. All four
synthetic cases completed. Simulator-free reconstruction was byte-identical
to the original reports, and action verification replayed 3,840 actions.
The report SHA-256 values were
`44dbcb5d38de750a8e8b0eae001b4e960195784a1ab04408e5c755a689b5e764`
for `report.md` and
`dfa77419d27290a750bbebcf05700caf4faafd42170beb95e18c1f8201d44450`
for `report.json`. The complete study is retained locally under ignored
`results/p1/acceptance-technical-dry-run-1a84540/`; it is not a participant result or an
accepted product claim. A later guide-only change does not alter the
simulation inputs or reported output hashes.

## Source, asset and rights inventory for the reviewer

This inventory records source declarations and assets used; it is not a
general permission to redistribute them. The human decision below applies
only to the exact bundle and internal use. Use the actual distribution
contents, [licensing policy](../licensing.md), lockfiles and retained study
inventory for any later review.

| Asset | Pinned basis and current handling | Human determination needed |
| --- | --- | --- |
| Original OpenT1D workflow, adapters and guides | Repository [Apache-2.0 license](../../LICENSE) and [NOTICE](../../NOTICE); the supplied two-file adapter is committed here | Confirm contributor authority, attribution, support and the files included in the offering |
| GlucoSim proportional agent | [`heuristic.py` at `6422a91`](https://github.com/HassDhia/glucosim/blob/6422a91d533125a8feb4f2e8737aecd67fec95c9/src/glucosim/agents/heuristic.py), SHA-256 `8528202b65e2068f5520e066add8293c944136f5d936dc2e30d5e9512878e6aa`; repository [MIT declaration](https://github.com/HassDhia/glucosim/blob/6422a91d533125a8feb4f2e8737aecd67fec95c9/LICENSE); installed from a locked Git dependency, not copied into OpenT1D | Check exact upstream notice and inclusion obligations for source checkout, runtime bundle or copied outputs; confirm rights basis for the intended offering |
| simglucose physiology, sensor, pump and PID reference | Commit `a6f6777`, package `0.2.11`, repository [MIT declaration](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/LICENSE); installed from a locked Git dependency | Review code notice and the separate origin/permission of bundled virtual-patient, questionnaire, sensor and pump tables in the [model card](models/simglucose.md) |
| Other runtime dependencies | Exact native versions are in `experiments/m0/simglucose/uv.lock`; NumPy is a direct adapter import | Inventory licenses and notices if a runtime or dependency archive will be distributed |
| Invented inputs and generated output | No participant records are used; local studies contain copied OpenT1D adapter source, traces, diagnostics, manifests, lockfile and reports | Decide whether any full study is shared or published; inspect actual bytes and applicable upstream/data notices before doing so |

The P1 declaration's `rights: licensed` field is the supplier's attestation,
not independent rights verification. The GlucoSim adapter executes trusted
local Python with the user's process permissions. The existing model card
does not establish an independent chain of title for simglucose's parameter
tables. These questions must be answered for the chosen distribution; a
source link and a license name alone do not close them.

<a id="human-rights-review-record--conditional-internal-scope"></a>

### Distribution-rights review record — conditional internal scope

The authorized reviewer stated their decision authority and approved the
prepared scoped proposal in the task conversation on 26 September 2026. The
proposal, its SHA-256, the reviewer's exact statements and full conditions are
retained outside version control in
`results/p1/acceptance-handoff-1abe1b6/RIGHTS-REVIEW-RECORD.md`.

| Field | Reviewer entry |
| --- | --- |
| Reviewer name/role and date | Authorized OpenT1D project representative; 26 September 2026. Personal name was not supplied. |
| Exact commit and distribution contents inspected | Git bundle of `1abe1b68401688fd1fa1a13e5b9a2941147015a8` only; SHA-256 above. The prepared audit checked reachable commit authors and tracked paths, not every line of historical content. |
| Distribution mode: named checkout, public repository, artifact archive or bundled runtime | One named independent researcher receives the local bundle for internal technical evaluation; no tester is currently available. |
| OpenT1D contribution and notice decision | Conditional transfer of the full-history bundle under the representative's authority; retain `LICENSE` and `NOTICE`; no public push or wider circulation. |
| GlucoSim code, notice and package decision | Direct pinned upstream installation by the participant under its published terms; no OpenT1D redistribution of code or runtime. Retain source attribution. |
| simglucose code and parameter-table decision | Direct pinned upstream installation and local synthetic evaluation only. The reviewer accepted the explicitly unresolved table-level origin for this limited scope; no copying, vendoring, publication or redistribution of the CSVs. |
| Other dependency and generated-output decision | Lockfiles only are transferred; no prebuilt runtime, third-party package archive, generated study, report or human data. |
| Required notices, exclusions or conditions | Name recipient and purpose before transfer; verify bundle hash and commit; preserve `LICENSE` and `NOTICE`; keep upstream notices; exclude other recipients, public release and clinical use. |
| Unresolved rights questions and who will resolve them | Separate table-level provenance remains unverified. Any broader distribution needs a new review and, where necessary, source-holder clarification. |
| Conclusion for the declared distribution: permitted, conditional or not cleared | **Conditionally cleared** for the exact internal handoff, subject to the recorded conditions. No actual transfer yet. |

## Independent user record and final decision

Retain the participant's actual commands, exit codes, timing, report hashes,
answers and deviations using the [exercise record](../p1-acceptance-exercise.md#exercise-record).
Record whether they completed and interpreted the workflow without coaching,
which problems were encountered, and whether they would use this declared
task. Do not substitute an agent or a maintainer who built P1. Keep names,
contact details and any private study files outside version control.

After both human records exist, the maintainer reviews each P1 roadmap item
and records the decision below. A negative usability finding can lead to a
guide or software change and a fresh independent attempt. A conditional
rights finding must identify what may be offered and what remains excluded.

| Final decision field | Maintainer entry |
| --- | --- |
| Date and reviewed checkout revision | |
| Intended-user result and deviations | |
| Rights review conclusion and distribution mode | |
| Supported product claim and evidence limits | |
| Open issues, owner and next action | |
| Decision: accept, revise and retest, or reject | |

Until the independent exercise and maintainer decision are completed, the
accurate status is **internally verified research software; P1 product
acceptance open**. Neither this packet nor the synthetic results imply
clinical benefit, safety or treatment suitability.
