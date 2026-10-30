# P1/0.3 — Source-pinned third-party PID intake

**Scope:** software verification of one existing controller on the P1/0.2
synthetic M1 task. This is not an independent controller family, a strong
comparator, a clinical assessment, or P1 product acceptance.

## Selection and source

The first external source is Jinyu Xie's
[`simglucose` PIDController](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/pid_ctrller.py)
at commit `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`, package version
`0.2.11`, PID-file SHA-256
`1eb84cbf2485e2eb591d221cdbf2d276072794a95ff97825795fe1bfb2c2b5bf`.
The already locked M1 environment installs this revision. The upstream
repository declares [MIT terms](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/LICENSE).

This source fits the three-minute CGM-to-U/min P1 contract and needs no new
package or trained weights. It is also M1's existing PID reference, so this
exercise verifies **external source intake**, not a new scientific method or
an independent efficacy comparison. The OpenAPS `oref0` path has unresolved
five/three-minute and action semantics; the G2P2C path needs a checkpoint
outside P1/0.2's two-file source contract. Those are separate future
compatibility questions.

### Candidate-fit screen

The pinned PID was selected for the first bounded intake after checking
alternatives against the *existing* two-file, three-minute, causal-CGM and
U/min contract. This screen is not a ranking of controller quality.

| Source inspected | Contract finding | Disposition |
| --- | --- | --- |
| [`uciAPC` at `7b3b3cd`](https://github.com/rland93/uciAPC/tree/7b3b3cd888b36b3f787f58d041ae3464d514c27c) | The published `src/controller.py` contains unresolved `<<<<<<<` merge markers; `python3 -m py_compile` raises `SyntaxError` at line 7. Its PID also reads profile tables and uses removed NumPy `asscalar`. | Do not wrap an unexecutable source or silently repair its method and parameters for the first P1 example. |
| [Berián et al. source at `e013b7f`](https://github.com/jberian/closed_loop/tree/e013b7f4c681073d6f0e8891fa8ba000ab2fd2d8/Simulation/simglucose_with_blockage) | The article controller uses a modified simulator action with a blockage field, five-minute history and separate `AP_params.csv`. The [repository README](https://github.com/jberian/closed_loop/blob/e013b7f4c681073d6f0e8891fa8ba000ab2fd2d8/README.md) calls the license GPL v2 while its [root LICENSE](https://github.com/jberian/closed_loop/blob/e013b7f4c681073d6f0e8891fa8ba000ab2fd2d8/LICENSE) contains LGPL v3 text. | A distinct contract and licensing clarification by a human reviewer would be needed; do not treat the publication's source availability as permission to port it into P1. |
| [OpenAPS `oref0`](c1-comparator-route.md) | Existing C1 audit found unresolved source-state and five/three-minute action semantics. | Keep the recorded no-go; do not re-label the source as a P1 rate controller. |
| [G2P2C](c1-g2p2c-training-freeze.md) | The actor requires trained weights and a source-specific missing-CGM fallback; P1/0.2 copies only two source files and does not bind an external checkpoint. | Its completed C1 technical smoke does not make this two-file route reproducible. |

This screen explains the narrow first choice. It does not prove that the
current intake handles an unrelated controller family; an intended user
bringing their own trusted method remains useful evidence for broader
compatibility decisions.

The [two-file adapter](../../experiments/p1_external/simglucose_pid/controller.py)
imports the installed upstream class; it does not copy upstream controller
code. At construction it checks the installed PID file's SHA-256. The
declaration separately pins the adapter bytes and exact dependency version.
The adapter passes only released CGM and a three-minute sample time to the
upstream policy. It ignores announced meals because the upstream PID does.
On a masked interval it passes the held CGM again, so upstream integral and
derivative state still update. Upstream reset starts previous CGM at zero,
which causes a first-action derivative transient. The adapter bounds the
upstream signed basal output to P1's 0–0.2 U/min; this changes the delivered
method. Its bolus output remains zero. No profile parameter, latent glucose,
future meal, or raw masked sample is passed to the controller.

## Technical evidence

The method-specific native tests check the source hash gate, independent
arithmetic for startup, fresh, held and recovery samples, reset, and both
rate bounds. The P1 preflight accepts the declaration. From clean revision
`69912c34d968e28a73ac4c63841d701736a3f7b6`, all four 960-interval
cases completed; each case manifest records `worktree_dirty: false`.
Source-only replay reproduced 3,840 actions and simulator-free
reconstruction produced byte-identical `report.json` and `report.md` files.
The clean run is retained locally under ignored
`results/p1/upstream-pid-clean-69912c3/`; its report SHA-256 values are
`7770c11fe35b21904f4775abe5cb48c565cf20e141209cf4332c329f4238cfde`
for JSON and
`3b6739c6c7b1ef494675447b97726b39e66ec79d3bf472680050143c550d55ef`
for Markdown. Re-run the commands in the
[user guide](../p1-upstream-pid-tutorial.md) from a clean checkout and keep
the complete study directory as the numerical record. A fresh report may
have different manifest hashes because runtime metadata includes elapsed
time; compare reconstructed bytes within each study and its numerical
metrics across studies.

| Condition | Completed | Scored 70–180 mg/dL | Scored below 70 mg/dL | Delivered insulin |
| --- | ---: | ---: | ---: | ---: |
| A, full announcements | 960/960 | 38.958% | 13.958% | 97.083 U |
| B, no announcements | 960/960 | 38.958% | 13.958% | 97.083 U |
| C, half announcements | 960/960 | 38.958% | 13.958% | 97.083 U |
| D, 30-minute CGM mask | 960/960 | 38.958% | 13.958% | 97.146 U |

A/B/C glucose, CGM and command traces are identical, as expected when
announcements are ignored. D changes 24 commanded intervals compared with
A. In each case, 397 of 960 recorded basal commands are at zero and
86 at 0.2 U/min. Thus the P1 rate limits materially shape this adapted
controller. The small rounded D differences and single profile/seed cannot
support a performance ranking or a real-world safety claim.

## Rights and distribution review

| Asset | Current basis | Open review item |
| --- | --- | --- |
| Upstream PID code | Pinned GitHub source and repository MIT declaration; imported from the locked dependency, not copied into this repository | Human reviewer checks notice obligations and whether the selected distribution package includes all needed notices |
| P1 adapter | Original OpenT1D code under Apache-2.0; source hash in its two-file declaration | Maintainer confirms contribution and intended support scope |
| Virtual patient and device parameters | Existing pinned simglucose installation; no parameter table is added by this P1 change | Existing model-card provenance limits remain; human review before redistribution or product claims |
| Input and output | Invented meals, generated sensor traces and local study artifacts; no participant data | Decide what, if anything, can be published and retain native provenance |

The declaration is a supplier attestation, not a legal conclusion. The
adapter runs trusted local Python with the user's process permissions. A
human review of distribution rights and an independent intended-user execution record were
required by [P1 acceptance](../../ROADMAP.md#p1--first-usable-research-product).
The later [conditional review](p1-product-acceptance-review.md) covers one
exact internal checkout; independent execution remains open.
