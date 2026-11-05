# 0110 — One owned LT1 native route

## Context

PR #70 supplies a source-bound entry continuation and conservative packet-copy
readback. Its entry is a library, its positive continuation is invented, and the
legacy integration worker reopens packet paths. Those boundaries do not yet form
an executable, byte-bound native attempt. Complete the route in one successor PR
rather than adding separately merged preparation layers.

## Decision

Select a version-2 fixed launcher, exec shim, entry CLI, owned-buffer worker and
engine-free route reader. Reuse the existing process owner, descriptor handoff,
engine/integration grant verification, constructors, attempt journal and trace
validation. Keep historical launchers, workers, readers, source inventories and
all four operational authority lists unchanged. New entry code/profile bindings
need their own complete source roster; the earlier software roster is not native
qualification for this route.

The trusted launcher API takes raw grants and independently reviewed source
context, with cancellation. Derive the executable, command, roots and profile
from those bindings; accept no caller-selected command, runtime, policy or
continuation. Exact canonical execution and actual-setup admissions precede
private paths or channel resources. Repeat source, owner, root and byte checks
at the final spawn boundary.

Use the unchanged process owner with dedicated inherited FD3/4 and a fixed exec
shim. The shim executes the fixed sandbox/candidate/entry command in the same PID.
Raw grants never appear in process arguments. Carry only the bounded entry,
observation and external source context through one fixed internal environment
field, not the potentially large packet buffers. Enforce a 64 KiB ceiling and the
actual exec-size budget before spawn. The entry owns and readmits the carrier,
then removes it before a version-2 exact-environment observation. Distinguish the
four owner-supplied keys, runtime-added keys and the actual post-removal keyset.
The ordinary-tooling Mac bootstrap exposes `__CF_USER_TEXT_ENCODING`; do not
strip that key to make the old three-key observer pass. Bind the complete runtime
keyset and values to independently reviewed private host context and reject
unexpected additions or changes. The actual selected runtime and whole startup
remain a separate host-qualification obligation; a supplied environment is not
an observation of its complete startup lineage.

After exact declared admissions, read the eight fixed packet members once into
owned buffers and bind their actual bytes before descriptor adoption. Complete
the exact owner/nonce/frame/ACK exchange and recheck cancellation/source/ownership
before the fixed worker. The worker uses those same buffers through semantic
engine/integration validation, TypeScript loading, direct or wrapped construction
and durable journaling. It must not reopen the private packet to acquire another
version. Preserve loader/model failures, valid prefixes and distinct primary and
export errors.

The route reader binds the actual outer process receipt, frame/ACK, packet pins,
current implementation and durable journal. Function invocation or a successful
ACK cannot establish model completion. Use the strict existing journal/trace
reader for row and interval meaning; incomplete, signalled or failed ownership
cannot become a complete native result.

For C15, run two resets of the same constructed engine in the same process,
retain a distinct durable subjournal for each session and compare a separately
owned fresh-process counterpart. Keep the real outer receipt and actual argv
unchanged. The version-2 reader must bind each fixed session subdirectory to that
actual parent output/owner; do not relabel a receipt to satisfy the historical
single-journal reader's output-path check. Reuse the unchanged scientific trace
validator for each committed session and exact scientific comparisons.

C18 coordinator-loss observation is a separate fixed operation. An owner killed
by the test cannot return its real outer receipt. The observer must use a genuine
live fixed-coordinator child created by that observer, not a saved PID or a fake
process handle. Bind the observer and coordinator start identities, fixed argv,
entry/source and precise stop action in an exact reviewed execution envelope.
Check authority before process-table/private-path/signal intake. Any preliminary
non-native coordinator may only wait for reviewed input; it cannot start the
native route or select another command. Retain a missing owner receipt as missing
and incomplete. Cleanup must preserve unrelated processes and use actual owned
identities; never manufacture an outer receipt or a store seal.

Preserve LT1 revision `9a6092065bd821f88691cd8d03b0550acd665573`, audit-1 plan,
seed 101, native reset/solver/sensor/pump ownership, causal release and separate
measurement/availability times. Keep the fractional 150000 ms start and 90000 ms
duration, units, callback grid, terminal behavior, exact interval accounting and
all frozen baselines/tolerances. No new physiological model or controller is
selected.

## Acceptance and remaining gates

Before implementation, select one positive end-to-end invented control through
the actual launcher/shim/CLI/channels/worker/journal/reader and distinguishing
controls for closed gates, oversized carriers, source/owner/packet replacement,
wrong ACK/EOF, late cancellation, loader/model failure, deadline and unrelated
process preservation. Fixed invented constructors are test code only; their
origin cannot be promoted to observed native evidence. Compare direct/wrapped
fixture behavior against the existing protocol and independent reader.

Keep current runtime/security and rights findings in the same PR, retaining
historical records and private identities outside Git. Confirmed limited-use
conditions do not accept runtime risks, missing notice/ancestry evidence or
unqualified storage. A newly announced security release without a fixed artifact
is not clearance for the selected binary.

Complete case-specific native qualification wiring in this same increment, but
actual selected-runtime setup and C15–C18 execution require separate reviewed
admissions. Until then, native cases remain unrun. Neither software checks nor
this route establishes complete private copy/restore coverage, effective erasure,
scientific validity, store/GUI migration or distribution rights.
