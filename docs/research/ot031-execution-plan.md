# OT-031 internal implementation and execution plan

**Specified:** 3 October 2026 before implementation and comparison execution.
The [roadmap](../../ROADMAP.md#proposed-internal-follow-up--ot-031-multiple-m4-secretion-sources)
owns the bounded scope; [decision 0057](../decisions/0057-m4-source-comparison.md)
and the [frozen protocol](m4-source-comparison-protocol.md) own coordination
and analysis. This plan is not an execution result.

## Work isolation and division

Implement on the separate managed worktree
`WORKTREES/m4-source-comparison/OpenT1D`,
branch `codex/m4-source-comparison`. Preserve the original checkout and
its existing local roadmap commit. Use separate agents for protocol/security
review, coordinator implementation and report/acceptance work, with the
parent coordinating integration and the final independent code review.
Keep historical source-hashed numerical packages, declarations and locks
unchanged. New comparison code belongs in `experiments/m4/comparison/`.

## Dependency triage before selected work

Read-only GitHub Dependabot inspection on 3 October 2026 found eight open
critical/high records representing three distinct advisories. These counts
describe records across manifests, not eight distinct vulnerabilities.

| Advisory and records | Selected-path assessment | Disposition |
| --- | --- | --- |
| [GHSA-53q9-r3pm-6pq6](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6), critical; #5, #14, #23, #33 | PyTorch 2.2.0 in the two optional C1 policy/training project and lock pairs. The repository's checkpoint deserialization calls are in `g2p2c_policy_adapter.py` and `g2p2c_trained_preflight.py`; M4 does not use them. | Keep outside OT-031 execution. The advisory remains open and needs a separate C1 remediation/compatibility review. |
| [GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw), high; #42, #45 | urllib3 2.7.0 in root and simglucose locks; advisory concerns an unbounded chunk-size line during streamed chunked network responses. Selected M4 sources/host/worker/readers have no urllib3 or requests network callsite. | No applicable exploit route identified in the selected local comparison; retain numerical locks. |
| [GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77), high; #41, #44 | Same root and simglucose locks; advisory concerns HTTPS-proxy TLS policy separation. Selected M4 code does not configure proxies or perform HTTP requests. | No applicable exploit route identified in the selected local comparison; retain numerical locks. |

The C-peptide runtime lock contains neither PyTorch nor urllib3. The
read-only audit used `gh api --paginate repos/OpenT1D/OpenT1D/dependabot/alerts`
filtered to open critical/high records, checked the three primary upstream
advisories, inspected declared versions and searched Python callsites in
the selected M4 packages and their reused kinetic code. Whole-repository
search located the C1 checkpoint calls and an unrelated literature fetch
using standard-library urllib. Selected numerical loading uses the pinned
native profile and local runtime assets. Locked dependency installation is
performed by uv rather than these Python urllib3 clients.

This is a scoped code-path inference, not vulnerability remediation, an
exploit test, a complete transitive dependency audit or a claim that arbitrary
trusted supplied Python is network-free. No lock upgrade is selected:
changing the native lock would change the fixed runtime identity required
by historical reconstruction without addressing an observed selected-path
network exposure. Broader dependency/security work remains open.

## Ordered implementation gates

1. Review and commit the decision, prose and machine protocol before new
   comparison implementation or execution. Record that freeze commit in
   later execution metadata.
2. Implement strict metadata-only intake, immutable roster/settings/source
   snapshots, common reference checking and sequential supervised children.
   Reuse unchanged single-source execution and preserve every source/scenario.
3. Implement artifact-derived combined JSON/Markdown/SVG, exact common
   control/grid checks, descriptive pairwise contrasts and simulator-free
   reconstruction, including failed and incomplete evidence.
4. Add focused tests for independent contrast arithmetic; frozen identities;
   incompatible grids and shortened evidence; common control disagreement;
   source failure with subsequent execution; full roster/null support;
   source deadline/global interruption cleanup; and archive preservation.
5. Execute the final two-source Dalla Man/ultradian roster from a clean
   committed source revision with one verified reference. Execute a separate
   failing third-source roster and preserve it. Repeat and reconstruct the
   reports in fresh processes without candidate execution. Record exact
   hashes and observed numerical/check outcomes.
6. Add the separately versioned route to the existing common entry. Verify
   passive checking and explicit native execution/reconstruction, then run
   `uv sync --locked` and `uv run --locked python scripts/check.py` plus
   required isolated numerical checks. Update canonical guides, navigation,
   roadmap/changelog and the separate execution record to actual outcomes.

## Execution boundaries and evidence

Use entirely synthetic scenarios and already attributed Dalla Man and
ultradian component examples; no patient data or credentials enter artifacts.
Use fresh output directories under temporary local storage. Pin source,
declaration, parameters, common reference, settings, numerical project/lock
and implementation revision. The supplied example's per-stage/source budgets
are 600/3600 seconds. Preserve ordinary failures and run later sources; on
global interruption stop after terminating/reaping the active group and
retain all later sources as unattempted. Never remove a failed source or
promote partial trajectories to a successful complete comparison.

Results must state this internal software scope and separate numerical
verification from model validity. Unobserved checks stay open. Do not claim
independent researcher use, biological accuracy, whole-ultradian reproduction,
empirical calibration or treatment benefit. This plan neither requires nor
represents a public release or new external message.
