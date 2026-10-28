# OT-055 schedule preparation verification

Date: 18 October 2026. Scope: historical internal synthetic preparation through
`73a9b2e`. The hashes, checks and open items below describe that snapshot.
The canonical sampling guide describes the subsequent implementation.

The [sampling guide](../mmtt-sampling.md) is the canonical user route. The
[empirical preparation](mmtt-sampling-empirical-plan.md) records the separate
unresolved scientific evaluation requirements. No fitted secretion estimates,
participant results or independent human sessions were produced here.

## Source and dependency boundary

The six-file shared planning snapshot was checked against every SHA-256 in its
supplied manifest and committed separately as `3ec9e07`, based on
`3567fbc5f72a02acf0c91b0476c976c3c7c52e7b`. Preparation uses branch
`codex/ot-055-sampling-information` in its assigned worktree only.

The checked OT-054 preparation commit `0a9d558` was integrated locally as
`78c3676`, preserving both tasks' changelog/roadmap updates during conflict
resolution. Its verification record `6b1efbc` was integrated as `7439b8a`.
The failure-retention correction `f4d719d` was integrated as `5b6e3ab`;
its full verification update `f17172c` was integrated as `c3ceb10`.
The observation package, CSV importer, sealed snapshot and trusted revalidation
are reused directly. No uncommitted predecessor code was copied.

This is an **import preparation handoff**, not the estimator handoff. OT-053
subsequently completed the narrow source/scope dossier in `cd10cb0` and bound it
in `4f38f01`. All 15 handoff digests were checked against their named origin
commit before integration as `6f64f4b` and `b25cd37`. The permitted boundary is
synthetic fixed-kinetic source-model estimation with exact interval integration,
whole-body total secretion including basal in pmol, and follow-up minus baseline.
Human execution remains unauthorized. No second estimator was built. Identical planning documents in the four branches need to be
reconciled once during integration.

## Checks actually executed

- `uv sync --locked` installed the root tooling environment. The initial sandbox
  attempt could not access the normal uv cache; the authorized installation ran
  outside that restriction. Subsequent commands used a writable temporary cache.
- Twenty-six targeted `unittest` cases passed: exact-time subsets, fixed endpoints,
  evaluation-selection refusal, duplicate schedules, missing samples, omitted
  value poisoning, deep-copy isolation, linked-visit inventory validation,
  duplicate JSON fields and CLI source-hash/overwrite behavior. Shared-import
  cases add full fixture coverage, development-only access before CSV parsing,
  relocation, source-manifest binding and modified-archive refusal. A regression
  check reproduces and fixes boolean window endpoints and overflow from invalid
  extremely large time values; both now produce explicit validation failures.
  Six additional comparison tests check hand-calculated bias/precision/absolute
  differences, all missing pairs, zero references and negative paired changes,
  numerical range handling, direction reversals and unresolved agreement.
  Five raw-mask tests additionally cover deletion before analyte/status parsing,
  missing interior requests, wholly missing visits, structural input errors and
  unchanged retained cells. They exercise arithmetic and raw masking, not an
  estimator adapter or complete report.
- The documented CLI freeze was executed locally into an ignored results
  directory. Both saved source digests matched the fixture files. Its receipt
  SHA-256 was `77b91d1689b6ed5e71647b3ca063c482cc900ba12c2df01e1c975ad9cf97dce1`.
- The shared local route was executed: export development fixtures → OT-054
  import → shared verification → schedule freeze from the import → relocate →
  reverify with Python `-S`. The selection receipt SHA-256 was
  `837db327810b73959366c15e2a41bac587a44607f267a0e61e45a3018f6ef3c1`;
  its bound import manifest digest was
  `ab305813d3ebdc097c4a4b39dacb1a72e1f8fbe1444270cfc11347df9357c1e4`.
- Four manufactured numerical acceptance vectors were independently prepared
  under decision 0067: constant, low constant, linear rise and linear fall.
  Their closed-form integrals agree with the compartment conservation expression
  at 60-digit decimal precision. They are not yet estimator-output checks.
  Constant totals are 4,320 and 540 pmol under the explicitly invented kinetics;
  the falling case has a negative terminal rate that must not be silently clipped.
- A local raw-mask/archive case retained an invalid full import with ten planned
  visits, while the masked child imported 30 retained rows successfully. Poisoning
  omitted cells did not change child CSV bytes. Both invalid-full and valid-child
  archives revalidated after relocation. Their manifest SHA-256 values were
  `f42e8906cfafee916ea83496c146a1a4774e46b6266cbc0e5340b980edf1e983`
  and `b718d5ef53fd73dcb364b32b4394414d58e8c0b9ec9a9e29caef8bd97ce04b5f`.
  This demonstrates input/diagnostic retention and isolation, not estimation.
- Ruff and Markdown checks passed for the preparation changes. The documentation
  built successfully with Sphinx warnings treated as errors.
- The first root check ran 1,296 tests with 13 existing skips and failed with
  two failures and 30 errors under sandbox localhost/process restrictions. A
  targeted GUI diagnostic confirmed `PermissionError` at `socket.bind`. The
  latest integrated locked check passed **1,315 tests with 13 existing skips**,
  all linters/navigation checks and the strict documentation build, with the
  required local-process permissions. This includes the `f4d719d` failure-retention
  correction, twenty-one sampling tests and the integrated OT-053 scope. The five
  raw-mask tests added during that run passed separately, for 26 targeted tests.
  No second numerical estimator was introduced.

These are preparation checks. The poisoning check proves that omitted values
cannot affect projected rows; it does not prove estimator-level isolation.
No full import-to-estimation user flow, conditional uncertainty calculation,
comparison report, archive reconstruction or GUI interaction is claimed.

## Required next technical evidence

Integrate a checked OT-054 **estimation** commit implementing the now-bound
OT-053 method/scope. The importer and its archive reader are already reused;
reuse execution, uncertainty and task reporting for full and reduced calls. Demonstrate fresh refits without full-curve-derived
participant parameters, numerical agreement with independent known cases,
removed-value perturbation invariance at the output level, preserved planned
failures and byte-identical report reconstruction after relocation.

Then execute the complete local researcher route, including low values, one
failed paired visit, missing requested times, full-reference failure and changed
glucose context. Supply OT-056 with runnable archives and model-specific expected
answers. The current fixtures support a schedule-preparation exercise only.

The machine-readable `experiments/mmtt_sampling/preparation.json` binds the
source digests, upstream commits, checks and remaining acceptance requirements.

Technical completion remains open. Held-out empirical acceptance and independent
researcher usefulness also remain open and cannot be inferred from passing
software checks or from agreement with the full reference curve.
