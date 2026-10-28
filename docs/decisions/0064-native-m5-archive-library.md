# 0064 — Native synthetic M5 reports in the archive library

Date: 6 October 2026

Status: accepted for implementation; execution evidence is recorded separately.

## Context

The general archive library indexes `m5-prognosis`, but its verified report
whitelist currently covers maintained M4 and synthetic M3. Native M5 verifies
its exact sealed archive in place, including saved report bytes, without a fresh
output argument. It preserves 32 invented participants and both held-out
prediction attempts. Rights and detailed training declarations remain in the
verified model declaration rather than in the original native report.

## Decision

Add exactly `m5-prognosis` to the fixed library verification whitelist, using
the unchanged current native reader through catalogue `verify_one`. After native
success, copy only original `report.json` and `report.md` into a fresh GUI-owned
`reconstructed` directory. Bind every copied digest to the initial frozen source
inventory. Check source inventories before and after verification and after
copying; refuse transient substituted bytes even if the source is restored.
Native exact file membership, regular-file checks and the 500,000-byte per-file
limit remain authoritative. Missing reports cannot use the M3 fallback.

The M5 API uses `task`, native `schema`, `native_report`, `verification`,
`verification_scope`, `source_freshness`, `report_completeness` and
`report_sha256`. A `model_declaration` projection and
`model_declaration_sha256` are retained in the owned worker receipt and bound
library entry. The projection includes model identity, source/state hashes,
rights basis, input/output contract, runtime and training declaration from the
same worker-verified catalogue. Report and declaration identities must agree.
HTTP never rereads source declarations or scans source inventories. Declaration
hash changes withdraw the same snapshot as report changes. Statements remain
supplier self-attestations, not independent rights or training verification.
Only original report JSON/Markdown are downloadable.

Use explicit M3/M4/M5 dispatch and a dedicated bounded M5 view. Preserve all 32
people (24 development / eight evaluation; 20 / seven eligible), exclusions and
later infusions. Each eligible evaluation participant retains both attempt
positions, statuses, saved predictions and runtime identities. Other participants
have no evaluation attempts. Keep execution accounting distinct from paired
comparison completeness; the native completeness rule requires both. Display
the full eligible baseline separately from baseline/candidate paired errors.
Preserve native null metrics, signed differences and U/day; compute no new
scientific metric or advancement criterion. Zero-pair explanatory text is UI
context, not an invented native report field. Synthetic scope stays visible.

Reuse one active operation, fixed argv/environment, safe roots/opaque pointers,
owned deadlines and cleanup. Restart retains recorded verification without
adopting processes. Unchanged snapshot rechecks preserve open details and focus;
obsolete selection/request responses are ignored. Current snapshot or artifact
failures withdraw reports, declarations and downloads together.

## Scope and verification

No native M5 scientific file, protocol, lock or CLI changes; no M5 run/export,
candidate import/execution, fitting, original external-input access, human-data
route or new durable package support. Native successful reconstruction can retain
an incomplete candidate comparison. Read-only agent review is internal evidence.

Verify native/worker/HTTP/browser parity and byte-identical downloads for
complete, mixed-failure, zero-pair and sealed interrupted cases. Retain full
rosters, original source inventories and raw evidence outside disposable
worktrees. Refuse missing/unsealed/tampered/unsafe archives, substituted copies
and changed report/declaration snapshots. Test cancellation, restart, ownership,
stale responses and M3/M4/campaign/durable regressions. Run locked repository
checks with Node and actual local-server/process permissions available. Independent
usability, empirical validity, hosted verification and publication remain separate.
