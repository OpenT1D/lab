# OT-062 correlated attempt and recovery readback

PR #62 was critically reviewed on `41b4f68c03e768c11b856fc7de80831740b30571`
and merged as `af75fdabaf5295cbe77443d5dfd382dab9f235d0`, with an identical tree.
The retained full check passed 2,112 tests with 32 expected skips; all sixteen
required jobs in hosted run 41702982547 passed. Fresh review added thirty pure
start/log/owner controls and seventeen recovery/binding checks with no open
finding. These results verify the [preceding increment](ot062-lt1-prestart-recovery-probe.md).

[ADR 0102](../decisions/0102-lt1-attempt-and-recovery-readback.md) selects two bounded
read-only consumers. Implementation and final verification are pending in this
successor's draft pull request. No runtime, storage query or removal is selected.

## Selected scope

Correlate exact attempt journal/process/plan files with existing engine/integration
packet bytes and the same owner, source and host-mechanism identities. Reuse the
engine-free journal reader. Preserve partial prefixes and primary process errors.
Keep all six native case families unrun until case-specific native instrumentation
exists; a normal completed attempt cannot prove confinement or universal IPC safety.

Convert a retained recovery observation into a proposed successor copy register,
compatible logical observations and retained per-copy provenance. Preserve original
clocks, holds, policy, predecessor and every copy. Unknown readbacks remain unknown.
Retain raw intervals, age conservatively from their start and never infer an exact
absence instant. Successful system queries never establish channel coverage.

## Gates

Existing authorities remain empty. Actual setup/native execution, native
instrumentation/C15-C18, approved ordinary recovery scope, complete copy/restore
coverage, original timing and separately admitted removal remain open. Real private
payloads, host identifiers and raw receipts remain outside version control.
