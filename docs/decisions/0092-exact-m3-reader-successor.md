# 0092 — Qualify an exact M3-era MMTT comparison reader

Date: 1 November 2026. Status: selected before qualification.

## Observed boundary

M3 changes `routes.py` and `execution.py` and adds six transitively imported
reader helpers. The historical comparison transition correctly refuses that
unqualified successor. The 37ee62a integrated run retained two read errors and
one identity assertion failure. This is not permission to update a frozen
fingerprint silently or to trust arbitrary archived source.

## Decision and preselected acceptance

Preserve the entire historical `reader_compatibility.json` byte for byte:
SHA-256 `6b50b5b97f9888e55f2fdddd86388a35963ce090291f37850cffb4863ed6f0e0`.
Preserve its exact A-to-B transition, predecessor metadata and successor closure.
Add a separately packaged version-2 qualification packet for one exact current
successor C. Only the historical A reader, complete historical B reader including its
original compatibility digest, and one exact M3-era MMTT comparison identity
from `6e77f7b86d3418ac5702dfb1efdd0edf68cabd90` may transition to C. The latter
was recomputed from a disposable Git archive of that source; its canonical
metadata SHA-256 is
`b6fb575b6bf5532a53f0fb2fd20a3efad5bfadc162dae9f010a2e0d6442e24ec`. Pin C's whole
reader closure, schema and roots. No generic chain traversal, partial matching,
new native route, registry migration or archived-code execution is selected.
The code pins that complete additional identity; the packet cannot nominate
arbitrary additional predecessors.

Keep both MMTT tasks, all original definition fields, scientific plans, input
bytes, units, uncertainty, denominator/failure support, first attempts, prefixes,
report bytes and historical tolerances. The changed reader/transition belongs
in the reconstruction receipt, not the frozen original definition. Refuse
changed A/B/C fields or any successor source hash; retain readonly inventories.
Keep native M4/connected and migration of the M3 task itself outside this
exception. MMTT comparisons frozen by the exact M3-era reader are included;
that is a distinct metadata identity, not an exception for M3 forecasts.

Before acceptance, run the unchanged reader-transition suite, extra A/B/M3-era/C exact
metadata and unknown-task counterexamples, direct constant-input arithmetic,
both real MMTT task chains and relocated saved-prefix/retry/failure evidence.
Build the exact clean successor wheel with both registry files bound. Qualify
that artifact against the retained clean A wheel with the existing installed
qualification procedure; separately exercise B-to-C preserved comparisons.
Review the full source/packet and changed-reader counterexamples independently.
The CI owner reruns the complete integrated root suite and actual browser/hosted
families on the final source. A passing test cannot qualify an unmatched future
reader, a native artifact, independent use or scientific validity.
