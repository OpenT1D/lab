# ADR 0097: Separate LT1 setup requests from verified setup receipts

- Status: accepted for implementation; native setup remains unadmitted
- Date: 2026-11-02

## Context

The existing `native-admissions.json` setup list admits hashes of actual reviewed
setup receipts. Using that same list to authorize a request to create a receipt
would make setup authorize its own evidence. The selected payload and risk
worksheet are preparation, not an authorization or actual installation result.

## Decision

Keep the existing setup-receipt and execution lists unchanged. A separate fixed
trusted `setup-request-admissions.json` contains exact reviewed request hashes;
its production list starts empty. Unknown requests refuse before parsing their
metadata, reading supplied packet paths or creating output. No request-supplied
registry, approval flag, worksheet, environment override or native receipt hash
can substitute for this authority.

A request binds the named host, canonical private parent/fresh attempt name,
current stager source/Python identity, bounded immutable input byte identities,
closed destination file map/modes and rights/security/harness receipt byte IDs.
Receipt bytes are not interpreted as semantic approval: the exact request and
actual decisions must be reviewed before admission. Native requests additionally
require the selected Darwin arm64 host and isolated/no-site Python startup.
Those flags and hashes do not qualify a complete bootstrap/stdlib/dylib/host TCB.

The stager writes only data. It performs no network acquisition, dependency
resolution, package-manager/lifecycle script, engine import or subprocess launch.
The output is a private materialized inventory with both setup admission and
native execution authority false. It is not an actual verified setup receipt.
Outer process success/cleanup, source/input provenance and inspection of the
actual output remain prerequisites to later, separate setup-receipt admission.
Execution admission remains another distinct gate.

## Consequences

The low-level trusted-registry injection exists for invented fixture tests.
Production calls always load the fixed trusted request authority. This is a
trusted application-code boundary, not isolation from arbitrary Python running
as the same user. No SDK/task/GUI setup route or qualified native bootstrap is
added by this increment.

Payload paths are a bounded ASCII subset with case aliases, traversal, special
members and file/parent collisions refused. Descriptor-relative writes pin owned
inodes, exclusive creation avoids overwrites, and a new attempt is required for
every retry. Mode/UID checks do not establish ACL policy or a hostile-owner
sandbox; actual host confinement is separately qualified. Read-only files remain
modifiable by their owner. Failed/pending evidence is retained without recursive
cleanup, and private process/manifest/receipt records are not public exports.
