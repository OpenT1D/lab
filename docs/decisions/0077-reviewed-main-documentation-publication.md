# 0077 — Documentation artifacts and reviewed main publication

Date: 28 October 2026

Status: accepted; live service acceptance requires hosted evidence.

## Context

The strict repository build already produces Sphinx HTML with project-relative
links, search and downloads. Publishing documentation must preserve the public
runtime boundary and keep untrusted PR execution separate from deployment rights.
The Pages upload Action archives a directory while dereferencing links; its outer
artifact filter alone does not establish safe tar contents.

## Decision

Stage a fresh tree of visible regular build files for both PR HTML downloads and
Pages uploads. Reject symbolic links, hard links and special files, including
hidden entries; omit dot-prefixed paths and require the entry and search files.
Keep assets and downloads byte exact. Do not stage stale output or research input
directories. This controlled-build check does not promise isolation from hostile
concurrent local writers.

Keep root checks read-only. A successful PR root check uploads one-day HTML for
inspection. Only a trusted repository main push uploads a Pages artifact; only a
separate job after the complete public gate can deploy it. Bind that job to the
main-only `github-pages` environment, grant Pages/identity writes there alone and
use the current run/attempt artifact name. Do not add the deployment to its own
gate's dependencies. Cancel superseded PR runs, serialize main/deployment runs
without cancellation and keep manual dispatch non-publishing.

Pin the Pages Actions and record the composite upload Action's exact transitive
artifact Action in the selected-revision allowlist. Do not widen publisher access.
Use workflow-type Pages with an explicitly verified main environment rule.

## Consequences

PRs can inspect the same staged content without deployment credentials. All
public check families must pass before main can publish, and failures preserve
the previous site. Artifact expiration bounds storage without deleting the live
site. The repository homepage is set only after actual site acceptance.

The [publication guide](../documentation-publication.md) owns commands, controls
and acceptance requirements. Initial Pages activation and successful HTTP/browser
checks remain operational evidence, separate from this decision, scientific
validity and release qualification.
