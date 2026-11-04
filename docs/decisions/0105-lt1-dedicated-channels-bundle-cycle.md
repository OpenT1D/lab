# 0105 — LT1 dedicated channels and whole-bundle removal cycle

## Decision

Select an explicit POSIX descriptor adapter for the bounded entry exchange and
an integrated fresh-metadata bundle removal fixture. Keep the existing launcher,
supervisor, native workers, process owner and four empty authority lists unchanged.

Use fixed inherited socket descriptors 3 (ACK input) and 4 (frame output), separate
from each other and from all stdio descriptor identities. Validate before adoption;
own and close only these descriptors afterward. The current-process wrapper must
pass existing observation admission before descriptor inspection. Its later handoff
rechecks admission. No model import or worker continuation follows an ACK.

Exercise real tooling-Node parent/child channels under the existing process owner,
with bounded parsing, EOF, failure, timeout and cancellation. This is a process
integration fixture, not selected-runtime, native profile or C15–C18 qualification.

Compose published invented bundles, explicit copy-registration proposals and exact
whole-bundle removal requests. Requests stay pinned to the immutable stored base;
the registration successor stays separate. Production removal must refuse. Only a
trusted test seam may remove newly created invented metadata. Independently inspect
complete and interrupted prefixes; leave proposed copy states conservatively present.

## Consequences

No setup, native execution or production removal admission is added. Actual native
descriptor inheritance/profile/fixed-entry wiring, bootstrap, phase and confinement
still require separate reviewed evidence. Existing private records, original clocks,
copy/restore scope and effective erasure remain outside this fixture's claims.
