# AI development workflow trial

**28 October 2026.** This internal trial accompanies the bounded
[AI-development roadmap item](../../ROADMAP.md#next-implementation-ai-development).
It exercises the [development workflow](../development.md) against existing
review cases. It does not repair the cases or establish agent productivity,
independent scientific validation or intended-user acceptance.

## Scope and environment

The runtime under review was public revision
`8cd1c110ae9709823bd0d965c5bf1b1d55a0f74b`. The trial used macOS on arm64,
CPython 3.12.13 under the repository's Python 3.12 selector, and Node v22.22.2. Root setup used
`UV_CACHE_DIR=/private/tmp/opent1d-review-uv-cache uv sync --locked` successfully.
No native environment was installed or executed. Public Actions activation,
Mac packaging and scientific convention changes remain separate work.

Two agents at Extra High worked in isolated worktrees: one owned the short
agent instructions, canonical component/test map and existing issue/PR
templates; the other owned the two repository skills. The integrating agent
owned temporary counterexample fixtures and the full repository check. The
agents then reviewed each other's artifacts. Agent review is internal technical
review, not independent scientific assessment.

The skills live under `.agents/skills/`, the repository location described by
the [official Codex skills documentation](https://learn.chatgpt.com/docs/build-skills).
Their frontmatter validation checks structure; behavioral observations below
are a separate, bounded exercise.

## Counterexample observations

Fixtures used invented bytes and short-lived local Python processes under a
temporary directory. Runtime files in the checkout were not edited. These
were reproductions of already identified cases, not blind bug-discovery tests.
The temporary harness and machine-specific logs are not committed regression
tests; permanent tests belong with the later fixes.

| Case and procedure | Observed result | Review handoff and remaining acceptance |
| --- | --- | --- |
| POSIX temporary-file symlink: create an unrelated file containing `original`, point the expected temporary name at it, call `atomic_write_bytes` or `atomic_write_text`, then inspect both the unrelated bytes and published entry with `is_symlink()`. | Both writers changed the unrelated bytes and published the symlink as the destination. | The happy-path publication behavior does not cover this counterexample. A later fix must preserve unrelated bytes and refuse linked output, with byte/text and caller regressions on supported hosts. |
| GUI caller: invoke the real `Service.persist` method with a minimal synthetic job and a temporary data-directory receiver; pre-create `job.tmp` as the unrelated-file symlink. | The unrelated bytes changed and `job.json` was a symlink. | This checks the actual persistence method without starting a GUI server; it is not a browser or full-job lifecycle test. |
| Catalogue supervision: a session leader starts a Python descendant, waits for its PID-file readiness signal and exits with code 0 or 7. After `storage.supervise` returns, probe descendant liveness. Keep a separate-session control process alive. | Return values were `completed`/0 and `failed`/7. In both cases the descendant was still alive; the unrelated control remained alive. The harness killed its trial descendants and reaped its direct control children in cleanup. | A later fix must handle descendants after normal exit and crash, then cover timeout and cancellation across the affected supervisors while preserving unrelated processes. This trial did not execute the latter cases or Windows Job behavior. |
| Setup source identity: copy the listed setup sources, process-helper inventory and root lock/selectors into a temporary checkout. Freeze an `mmtt-sensitivity` plan, change the copied `platform_process.py` bytes, and validate the old plan. Mutate a listed source as a control. | The old plan accepted the helper change. Mutating listed `setup/core.py` then raised `Setup implementation changed`. All three entries in `platform_process.SOURCE_FILES` were absent from setup's `SOURCES`. | The trial patched only the checkout roots and `uv_identity` (to `None`) to isolate source identity. No install was attempted. A later fix must reuse the process inventory and reject helper changes before installation. |

The source-identity trial copied and changed real file bytes rather than
mocking the digest result. The listed-source control distinguishes the missing
inventory from a validator that accepts every mutation. Process checks waited
for a readiness file rather than guessing from a fixed startup delay.

## Numerical review route

The scientific skill was exercised on the existing synthetic observation
estimator controls, without changing equations, fixtures or tolerances:

```sh
uv run --locked python -m unittest discover -s tests -p test_observation_estimator.py -v
```

All six tests passed. They include a separate RK4 balance/integration oracle,
high-precision small-interval checks, unit covariance and explicit invalid or
negative-result handling. The existing tests retain their declared tolerances.
This establishes only those synthetic software checks; it does not validate
human kinetics or justify new numerical acceptance thresholds.

The separate reviewer followed the scientific skill using the raw estimator,
tests, task guide and protocol, then tried disposable in-memory source copies.
The integrating agent reran the harness and confirmed these observations:

| Deliberate counterexample | Six unchanged estimator tests | Supplemental observation |
| --- | --- | --- |
| Unmodified source control | Six passed, no errors or skips. | Establishes that the fixture itself runs. |
| Halve the elimination integral (`/ 2` to `/ 4`) | Two assertion failures: separate RK4 integral and equilibrium; no import/runtime errors. | Those controls distinguish this mass-balance error. |
| Relax `RATE_TOLERANCE` from `1e-9` to `1e-6` | Six passed; this suite missed the deliberately changed boundary. | A hand-calculable near-boundary vector distinguishes it: original reports `boundary_failed`, relaxed copy reports `completed`. |

The near-boundary vector uses the existing nominal synthetic variant with
`k1_per_min=0`, times `[0, 120]` minutes and concentrations
`[7.240000261723009, 1.0]` pmol/L. Its final rate is
`volume_l * (end - start) / 120 + k3_per_min * volume_l * end`, approximately
`-1e-8` pmol/min. This is a test-coverage observation, not a newly selected
runtime defect. Neither mutant, the supplemental harness nor a permanent
regression test is included in this PR. The historical native BC-003 parity
check was not run under the public installation policy.

The reviewer also ran the estimator, shared sampling estimator and analysis
suites together (16 tests passed, no skips), then the observation workflow suite
(six passed, no skips). The latter covers CLI/catalogue, failed and interrupted
evidence, forged results and relocated reconstruction. These results remain
bounded to their synthetic fixtures and exercised root environment.

## Verification and review observations

The targeted publication-security suite also passed all six tests, including
the byte-exact published-source inventory. The 14 mapped historical files,
including `docs/research/ot031-execution-plan.md`, remain bound to their recorded
published hashes. Their historical identities and the roadmap's retained anchor
are not rewritten by this change.

One technical review round produced two wording corrections: attribute the
Python selection to `.python-version` rather than `uv.lock`, and keep prose
changes that alter scientific meaning within the scientific skill's discovery
scope. Both were corrected before final verification. Review found no runtime,
test, lock, CI-policy or packaging changes to integrate. The final diff and
revision are handed off separately in the PR.

Maintainer review time and a productivity baseline were not measured. Known
cases cannot measure a blind missed-regression rate. Correction rounds,
technical review outcomes and final-revision checks are recorded in the PR
handoff; no speed, quality or throughput improvement is inferred from this
small trial. Future real changes should record actual maintainer interventions,
unnecessary edits and regressions against their reviewed revisions.
