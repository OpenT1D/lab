# OT-062 entry observations and private review bundles

PR #63 was critically reviewed again and merged as
`07eb0a97c22747acb94a8ce44422794106dc5cc5`, with the same tree as corrected
`081481c86264f133f35904059e76a0be0ace4110`. Review found and fixed impossible
owned-process ancestry and contradictory known readbacks before merge. The renewed
full check passed 2,149 tests with 32 expected skips; all sixteen required jobs in
hosted run 41720121918 passed. Six ownership guard controls, an independent
125-graph matrix and thirteen recovery old/new counterexamples support the fixes.
These results verify the [preceding readback increment](ot062-lt1-evidence-readback.md).

[ADR 0103](../decisions/0103-lt1-entry-observation-review-bundle.md) selects two
bounded implementation components. This successor's draft PR records implementation
and final verification. No actual native execution or private removal is selected.

## Selected entry-observation scope

Prepare a fixed producer library and one strict frame reader. The producer has
no CLI or launch route; its observation gate does not precede an already running
Node or establish a pre-model phase. Pure supplied facts remain invented. The
reader correlates a separate externally pinned parent entry PID/start/executable
observation with owner, attempt, nonce, profile and exact grants. Returned frame
bytes need later reviewed transport: the journal output must still be empty and
the current sandbox profile allows no new evidence-root writes. All six native
families remain unrun; real fixed-entry wiring and qualification remain open.

## Selected private bundle scope

Save exact bounded recovery inputs, proposals and per-copy provenance under a
new private flat manifest. Preserve original clocks, holds and predecessor; keep
unknown origins unknown. An intent precedes copied inputs. Exclusive publication
and readback preserve failure prefixes and uncertain durability. Reopening checks
external manifest/current-register/context identities, original replay and a
separate nondecreasing current assessment. No active register or private pilot is
replaced automatically.

Only the entire own closed bundle may supply a proposed exact removal request.
Store request/context/journal elsewhere and capture signatures after the last
publication/readback step. No partial request for an existing evidence directory
is inferred from a point observation. Actual removal admission, complete ordinary
restore coverage and effective erasure remain open.
