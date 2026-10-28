# 0078 — Dependency review with complete comparison evidence

Date: 28 October 2026

Status: accepted; hosted dependency-graph acceptance remains separate.

## Context

The maintained public scope uses root development tooling and two standard-library
tasks. Historical native environments retain separate locks and advisories. Root
updates should be reviewed without rewriting those historical inputs. The single
required public result must not accept incomplete dependency data.

## Decision

Prepare monthly grouped Dependabot updates for root uv tooling and Actions only,
with three open version-update PRs per ecosystem. Exclude experiments, packaging
and test assets from uv discovery. Updating a pinned Action also requires review
of its upstream runtime/transitive actions and the exact selected-action policy.

Add a PR-only Dependency Review v5 job using a full immutable SHA and read-only
token. Fail introduced high/critical advisories in runtime, development and
unknown scopes. Disable comments, license checks, warning-only mode and scorecard
calls. V5 uses Node 24 directly and declares no transitive `uses` references.
This choice does not create a license-clearance process or remediate old alerts.

The action's snapshot retry timeout may return incomplete comparison data.
After action success, read all pages of the same exact-SHA comparison with a
120-second warning-retry bound. Reject HTTP, JSON, encoding and pagination errors,
redirects, and warning headers from any page. Once warning-free, require the
normalized full dependency/advisory set to equal the action's unfiltered
`dependency-changes` output. Retain a short count/hash/SHA completeness receipt;
never print the token or environment. A later complete graph cannot bless a
partial scan that already returned success.

Require this job in the existing aggregate. Accept its `skipped` result only for
explicit `push` or `workflow_dispatch` events; PR skips, missing events and every
other unsuccessful public family fail. Keep private native guards and their
fifteen job definitions intact. Keep fork/Dependabot permissions read-only;
unavailable graph data fails rather than selecting a PAT or privileged trigger.

## Consequences and acceptance

The comparison guard adds no second advisory filter: the official action remains
the vulnerability-policy checker. Completeness and matching inventories do not
establish that all vulnerabilities are known. Large/unsupported comparisons can
fail within the declared page/byte/time bounds and need maintainer investigation.

Before claiming operation, inspect a safe root uv-lock delta in the hosted graph
and a disposable known-high-advisory PR that makes the job and aggregate fail.
Remove the probe and obtain green PR/main checks. Existing alert triage, native
remediation and numerical/scientific validity remain separate work.

## Sources

- [Pinned v5 action, retry behavior and full output](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/main.ts)
- [Pinned per-page warning handling](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/dependency-graph.ts)
- [Dependency comparison API and read-only permissions](https://docs.github.com/en/rest/dependency-graph/dependency-review)
- [Dependabot options and scan exclusions](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
