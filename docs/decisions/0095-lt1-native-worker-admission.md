# 0095 — Separate LT1 native worker admission

Date: 1 November 2026. Status: accepted for implementation; no native admission.

## Context

[Decision 0094](0094-lt1-diagnostic-harness-reader.md) deliberately has a closed
native entry and an engine-free reader. Its invented controls do not authenticate
an installed runtime or authorize a host. The full candidate Node archive also
contains affected npm packages; the earlier twenty-package headless scan did not
cover that payload.

## Decision

Add a separate worker and positive staging verifier. Preserve the old closed
entry, worker, lock, reader identities and publication boundaries. Trust comes
from an exact grant digest in the worker's fixed reviewed registry, never from
flags, a request-selected registry, declared approval booleans or a checksum
computed from the submitted packet. Setup-receipt admission and execution-grant
admission are separate lists. Both lists initially remain empty.

A grant binds the selected source revision, exact plan/mode, named host and
staging root, running executable/version/platform/architecture, complete staging
inventory, current worker import closure, and exact setup/host/security/rights
receipt bytes. A future grant review must inspect those receipts and the actual
installation. Receipt hashing is not signature verification or confinement.
Verify before registering the TypeScript loader or importing candidate source.
Use the existing direct/wrapped constructions and recorder without replacing
native initialization, integration, scheduling or pump behavior.

## Consequences and open gates

The [worker guide](../research/ot062-lt1-native-worker.md) records passive runtime
findings and executable fixture controls. No registry entry, installation or
native result is created. Positive verifier tests use an explicitly invented
trust root; they do not qualify the production worker's native branch.

There is no admitted launch route. Before any execution grant, integrate the
existing process supervisor/Ownership and immutable project ledger, prove clean
startup, immutable staging and external file/network confinement, retain durable
callback prefixes and failure slots, and observe cancellation/deadline/descendant
cleanup on the named host. The current single-attempt worker result is neither a
reader packet nor a trusted store seal. Keep native settings, states and full
reports private until a separate export review.
