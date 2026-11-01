# Bounded CI orchestration and diagnostics

Selected: 1 November 2026, before optimization, on clean
`5dbdd24703480c7504fce3db6e6867ff33b3ca3e`. Its merge tree is identical to
`aa1a62f31ecc90565fb98e01af14987f21607079` from PR 45. This work changes
verification orchestration, not numerical methods, scientific tolerances,
reference outputs or native installation policy. The [development guide](../development.md)
owns the runnable checks; [decision 0076](../decisions/0076-public-check-families.md)
owns the required public families.

## Measured problem and acceptance

The exact [baseline workflow](https://github.com/OpenT1D/lab/actions/runs/41291111008)
retains two different attempts on that source:

| Attempt and job | Observation |
| --- | --- |
| 1, Root checks `124802396765` | All 1,850 tests passed in 2,377.604 seconds, with 33 expected Linux skips. The 40-minute job limit cancelled the subsequent documentation phase. |
| 2, Root checks `124811477445` | The same 1,850 tests passed in 2,075.377 seconds, with 33 expected skips; documentation and the job also passed. |
| 1, Chromium `124802396675` | The connected case expired at 150 seconds during project reopening. The 480-second suite limit subsequently expired; 11 cases passed and one was unrun. The integrated candidate case passed. |
| 2, Chromium `124811477639` | All 13 cases passed in about 6.8 minutes; the connected case took about 134.7 seconds. |

Those Linux jobs used Ubuntu 24.04 x86-64 image `20261021.618`, uv 0.11.16,
CPython 3.12.13, Node 24.22.1 and Playwright 1.64.1. The retained Apple Silicon
control on the same source ran the 1,850 tests in 1,426.034 seconds with 32
expected skips. These host differences are not a measured optimization.
A new clean-tree Chromium trace on the merge base passed the connected case in
about 108 seconds on Darwin arm64 with the same Python/Node/Playwright versions.
Its largest waits were asynchronous UI/job completion: about 15 seconds for
report withdrawal, 15 for the failed stage and 13 for the frozen study. Fixture
setup took about 9 seconds. A selector disabled while reopening later became
enabled. This evidence identifies total budget pressure; this trace alone does not establish
a permanently stuck selector or a product defect. The later M3 trace exposed
a separate real pending-request visibility/synchronization defect, preserved
with its regression in the [integrated M3 source](installed-m3.md#hosted-chromium-correction). An interrupted profiling
probe identified repeated source-closure traversal as a major cost. It is
neither a passing suite nor an uninstrumented performance comparison.

A separate [installation run](https://github.com/OpenT1D/lab/actions/runs/41250127517)
attempt 1, Firefox job `124681792683`, exhausted the 300-second installer limit.
Azure Ubuntu metadata/package acquisition stalled; fallback metadata from the
Ubuntu archive succeeded, but package-index requests still used Azure. No
browser tests ran in that job. Installation availability, test correctness and
suite-budget exhaustion are separate outcomes.

Acceptance preserves every existing test case and assertion, negative/missing
case, source/reader binding, process cleanup, publication guard and frozen
scientific criterion. Require complete discovery/selection accounting, bounded
failures and an independent technical diff review. Keep one final full-check
owner, actual Chromium execution and exact PR-head hosted results. No dependency
cache, native policy bypass, hidden retry, test omission or weaker tolerance is
part of this change.

## Selected implementation

Partition the complete root discovery over four isolated Linux jobs, keeping
whole modules and their original case/class/module fixture order. The
[timing weights](../../tests/root-test-timings.json) derive from consecutive
verbose completion timestamps of the first baseline root job. They include
intervening fixture overhead and only guide scheduling. Unknown modules use
their case count; weights are never an allowlist. The initial estimated loads
are approximately 596 seconds per shard. They are estimates, not new hosted
measurements. Discovery/import errors fail before selection; empty or invalid
shards fail. Tests verify the full multiset union, including repeated IDs, and
fixture lifecycle. Class/module fixture skips explicitly explain their planned cases without
changing unittest's original skip outcome. A prematurely stopped runner cannot
pass with selected cases unrun. Receipts replace old evidence before discovery and record the
source, selected IDs, digest, counts, outcomes, durations and skip reasons.

The default local command still runs style, all root tests and documentation.
The hosted `Root checks` job runs style/documentation and the paired boundary
after the full root-test matrix succeeds. This preserves the previous preflight
for both embedded and downstream private/manual native checks. The public gate
requires the matrix as an additional family; a failed, missing, skipped or
cancelled family cannot pass.

Run application Chromium cases in three isolated Playwright shards with one
worker per job and zero retries. The CI configuration enables case sharding;
each case retains a fresh application, installation and workspace. The integrated
local selection contains all 13 original cases plus the M3 case. Documentation retains separate
Chromium/Firefox/WebKit jobs and their complete page/fault checks. Builds and
installations remain uncached and repeated across those isolated jobs: avoiding
an extra cross-job artifact trust/cache boundary is preferable for this bounded
change. This spends additional runner/setup time to reduce the critical path;
no reduced total CPU consumption is claimed.

The connected case receives a bounded 180-second total reserve after the
134.7-second pass and 150-second expiry on identical source. The 15-second action and default 30-second assertion limits remain. The M3
completion helper explicitly retains its bounded 60-second job wait and the
changed-study assertion. Each CI shard keeps a 480-second suite ceiling; the
local combined 14-case suite retains M3's 720-second ceiling. Sharding prevents this
long case from consuming the later cases' shared global budget. This budget
change does not speed up reconstruction or qualify slow native work.

Only ephemeral hosted browser runners replace the exact Azure Ubuntu mirror
URI with the [official Ubuntu archive](https://ubuntu.com/project/docs/how-ubuntu-is-made/concepts/package-archive/)
over HTTPS. Suites, components, signing keys and unrelated sources are retained.
[APT transport settings](https://manpages.ubuntu.com/manpages/noble/man5/apt.conf.5.html)
bound connection/data waits to 30 seconds with one transport retry;
[update errors remain fatal](https://manpages.ubuntu.com/manpages/noble/man8/apt-get.8.html).
There is no repeated apt/dpkg installation or accepted failed dependency phase.
The official locked Playwright CLI runs system dependency acquisition and browser
download separately, under the original combined 300-second budget. Phase logs
identify the failing acquisition. On Linux, the complete dependency installer/supervisor runs explicitly as root
on the ephemeral runner; the browser cache remains temporary and application
tests run as the runner user. This prevents the supervisor losing permission
to terminate apt or `_apt` descendants. Owned process groups receive bounded cleanup
on timeout/interruption or orphaned descendants; unrelated processes are retained.
The mirror change reduces the observed endpoint failure exposure, but cannot
guarantee future network availability.

## Check provenance and verification handoff

The old PR rollup included the failed/cancelled attempt-1 checks even after
attempt 2 succeeded. The exact successful attempt-2 gate was `124819233502`;
its previous failed same-run gate was `124811150787`. Selecting an arbitrary
check by name, its largest ID, or the PR's overall UI label loses provenance.

From the checked revision, use the read-only diagnostic:

```sh
uv run --locked python scripts/ci_run_status.py --repository OpenT1D/lab \
  --run RUN_ID --sha FULL_PR_HEAD_SHA
```

It uses authenticated `gh api`, binds the workflow path, run, source, latest
attempt and complete current public-job roster, paginates latest jobs/all check
runs and detects an attempt changing during collection. A rerun may retain a
successful earlier-attempt job; its original attempt remains explicit. Older
same-run check entries remain in the report. Failure, cancellation, missing
coverage and incomplete API reads do not become success. This script writes no
GitHub status, changes no branch protection and supplies no merge eligibility
or clean-rollup assertion. Use the script from the matching source configuration;
its current job roster deliberately does not qualify the predecessor layout.

The pull request retains before/after host, source/tool identities, commands,
full existing coverage plus added orchestration cases, failures/skips, critical
review and exact final local/hosted receipts. Compare Linux run durations with
Linux durations; report the Mac full check separately. A successful local check
is not a hosted result, and a single faster hosted run is not a general speedup
claim. Native numerical qualification, intended-user acceptance and biological
validity remain separate. The combined source must be checked explicitly; previous standalone receipts
do not qualify it, and subsequent M3 edits require new verification.

## Exact M3 integration

At the user's explicit coordination request this CI branch incorporates the
repaired M3 predecessor `e502d6427d0e4648457617f35532039c0c78e5a5` (PR 46).
Its production SDK/CLI, adapter, readers, workbench and pending-action fix remain
owned by that predecessor. The staged CI diff is reviewed against that exact
base. Only `docs/development.md` conflicted textually; resolution retains both
M3 guidance and the bounded CI orchestration. Automatic merges of the workflow,
ToC and connected case are also inspected explicitly. The connected case keeps
M3's delayed-completion/changed-study assertions and this increment's measured
180-second total reserve. Root and browser rosters include every new M3 case;
untimed root modules are selected with the normal fallback weight.

The M3 predecessor's 20-minute combined Chromium job becomes separate
15-minute documentation and application jobs, with an unchanged five-minute
documentation budget and eight-minute per-shard application budget. The
12-minute local combined-suite budget remains. Final acceptance uses the
integrated commit's full local check, actual browser cases, hosted source/run/
attempt receipts and separate critical review, with one full-check owner.
The associated CI pull request is stacked on the M3 branch; neither PR is merged
by this workflow. No previous native M4 or M3 result is relabelled as evidence
for a new exact installed artifact.

## Search completion follow-up from PR 48

A separately reported Firefox failure on `eb2284688b6976b9a9e708c71a9ee8bf9583708e`,
[run 41300144495](https://github.com/OpenT1D/lab/actions/runs/41300144495),
attempt 1, job `124829203433`, retains artifact `13081505129`. The actual
result navigation began while the 800-millisecond summary fetch body was pending.
The receipt retained its `NS_BINDING_ABORTED`, a JavaScript network error and the
intended target-asset 404. The target 404 assertion passed; the subsequent
summary-before-navigation assertion failed. This is a real early-completion
error, not a prefetch exception or lost asset detection.

The separate two-file fix `d227ae9196d9c40dd310833909554a6fca717381` can be
cherry-picked without the M3/SDK or workflow migration. The existing monitor now
tracks every actual request through `requestfinished`/`requestfailed`, requires
a fresh 500-millisecond quiescence after completion and lets browser callbacks
settle before its final error check. Its Node-side 15-second deadline also
bounds blocked browser settlement. It issues no extra fetch, erases no error
and keeps the original monitor active through result navigation. This checks
the bounded Sphinx completion boundary and queued callbacks; it is not a promise
that arbitrarily delayed future page activity can never occur.

All original fault assertions remain. Seven additional real-browser cases cover
a fetch started after an already reached idle state, response headers without
a completed body, deferred 404/abort, queued console/JavaScript faults and page
timers holding settlement callbacks. The three cached-idle regressions fail
against an unchanged predecessor helper because the summary is still empty or
the expected fault has not yet been awaited. A first candidate's unbounded
browser-evaluation path was independently reproduced and corrected before
handoff. The final 13 search cases passed in all three engines (39 cases,
15.9 seconds locally); that targeted result is separate from the final full
browser matrix and hosted acceptance. The adapter audit reuses this exact fix
and owns its separate final-source checks; this branch remains the only owner
of the complete M3/CI integration check.

## Follow-up after the first integrated run

The first PR 49 run on clean `37ee62a`, run `41302689708` attempt 1, failed and
is retained. Root shard 4 ran all 450 cases in 388.125 seconds but exposed the
SDK-scope error-message regression; the M3 owner supplied exact fix
`6e77f7b86d3418ac5702dfb1efdd0edf68cabd90` without weakening its assertion.
Root shard 3 ran 499 cases in 702.899 seconds and exposed three reader-transition
failures. [Decision 0092](../decisions/0092-exact-m3-reader-successor.md) selects
the separately qualified successor while preserving the entire historical
registry. Known existing M3-era MMTT comparisons have their own exact pinned
identity; no wildcard, native exception or archived-code execution is added.
The associated installed qualification explicitly selects policy 2; historical
policy-1 qualification remains distinct.

All three hosted documentation engines and platform smokes passed on that first
source. Chromium group 1 passed four cases but exhausted the connected case's
180-second total during its final replay. The trace shows that replay starting
about 170 seconds after the first interaction, with preceding reads taking
about 15 seconds; setup and cleanup also consume the total budget. All actions
were admitted, and the pending panel accurately exposed unfinished work. The
new bounded total is 240 seconds, preserving every 60-second job, 15-second
action, default 30-second assertion, prefix-byte, restart and reflow check.
Three explicit file groups now separate the long flows: connected/internal,
comparison/integrated/MMTT and workbench/sampling/M3. Current IDs partition as
2/6/6, exactly once. The selector checks the full configured and recursive
on-disk application inventories, including unexpected nested specs; unknown,
missing, duplicate or invalid selections fail. Each job retains one worker,
zero retries and a 480-second suite budget. The local full roster is unchanged.

The first local application attempt had 13 passes and one comparison timeout.
Its trace's approximately 249-second event gap coincides with host Maintenance
Sleep from 12:37:36 to 12:41:46 Europe/Amsterdam. That interrupted-host result is
retained and does not motivate a product or comparison-timeout change. The
owner's first full root attempt was explicitly interrupted (exit 130) after the
known hosted contract failures; it is not a full pass. The final source must
receive a fresh complete check and actual local/hosted outcomes. Wall-clock
comparisons across sleep, changed source, extra coverage and different runners
are not a causal speed benchmark.
