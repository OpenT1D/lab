# C1/1.2 — OpenAPS example lineage and locked source baseline

**OT-019, 26 September 2026.** This simulator-free follow-up investigates
the failed example parity in [C1/1.1](c1-oref0-preflight.md). It checks a
bounded set of exact upstream revisions and records a reproducible source
baseline. It does not qualify an M1 comparator or execute a native case.

## Which source and example match?

The upstream `examples/suggested.json` was introduced in
[commit `9b63e442`](https://github.com/openaps/oref0/commit/9b63e442c9e6d55da2e128566a00cba29671f7cb)
and has no later change in the tested line of history. The
[source-history audit](../../experiments/c1/oref0_example_history.py) runs
the committed command and fixture at four exact revisions under one
recorded runtime:

| Revision | Source role | Committed example | CLI output | Strict JSON parity |
| --- | --- | ---: | ---: | --- |
| `9b63e442` | Example introduced | 0 U/hour | 1 U/hour | Fail |
| `acb01500` | [0.7.0 release](https://github.com/openaps/oref0/releases/tag/v0.7.0) | 0 U/hour | 1 U/hour | Fail |
| `69d76737` | [0.7.1 release](https://github.com/openaps/oref0/releases/tag/v0.7.1) | 0 U/hour | 1 U/hour | Fail |
| `88cf032a` | C1/1.1 pinned source | 0 U/hour | 1 U/hour | Fail |

At the introduction commit, the audit also replays the **entire**
`examples/example.sh` calculation chain from copied, unchanged inputs.
Its generated `iob.json` and `meal.json` match the committed JSON exactly;
the generated `suggested.json` still differs in rate, insulin requirement,
prediction and reason. The same negative result follows when the original
CLI's positional autosens/meal arguments are used. Thus simply recomputing
the upstream prerequisites does not repair this example at its origin.
This audit does not claim that no intervening commit or historical Node 8
setup could ever have produced the file. The four tested revisions share the
locked current-source dependency graph for this bounded comparison.

## Locked current-source baseline

The [OpenT1D npm lock](../../experiments/c1/oref0-package-lock.json) was
generated against `88cf032a`, which has no upstream committed npm lock.
It records 175 installed packages. `npm ci --ignore-scripts --offline` in a
clean external checkout reproduced the earlier C1/1.1 JSON **byte for
byte** under Node 22.22.2 and npm 10.9.7. The pinned upstream basal suite
passes 52/52 tests; the full upstream suite remains 228 passing and 16
failing on this host. The source was not modified.

The [source baseline](../../experiments/c1/oref0-source-baseline.json)
binds that exact source revision, lock hash, runtime, upstream test-file
hash, 52-test pass count and CLI output hash/action. The history audit
verifies all nine baseline checks. This is **our output fingerprint** backed
by upstream-authored behavioral tests, not a replacement upstream example
or proof that every algorithm branch is correct. The old mismatched
`suggested.json` stays visible as negative evidence. A change in source,
dependencies, runtime or output requires a new reviewed baseline; it must
not silently overwrite this one.

The lock exposes unresolved license metadata: four packages have no
license expression in the lock, and one declared package is GPL-3.0-only.
Only metadata is committed here, not dependency source or binaries.
Redistribution/licensing assessment remains open if a future module bundles
any dependency. Historical packages and the original Node 8 environment
were not reproduced by this lock.

## Reproduce and decision boundary

From a full external clone of [OpenAPS `oref0`](https://github.com/openaps/oref0),
check out `88cf032aa74ff25f69464a7d9cd601ee3940c0b3`, use Node
22.22.2/npm 10.9.7, copy the OpenT1D lock into that checkout as
`package-lock.json`, then run `npm ci --ignore-scripts --no-audit --no-fund`.
From the OpenT1D root run:

```sh
python3 -m experiments.c1.oref0_example_history \
  --source /path/to/external/oref0 \
  --output results/c1-oref0-example-history.json
```

The JSON and a byte-identical fresh-process repeat are retained outside
Git; hashes are in the [C1 evidence index](../../experiments/c1/evidence-index.json).
[Decision 0037](../decisions/0037-c1-oref0-source-baseline.md) accepts
upstream-authored tests plus the locked local fingerprint as a source
baseline for **simulator-free adapter work**. It leaves comparator
eligibility closed. The next gate is causal reconstruction of glucose,
own insulin history/IOB and announcements, followed by a verified mapping
of five-minute temp-basal behavior and failure/reset states onto M1's
three-minute U/min interface. An altered algorithm needs its own method
label. No C1 native outcome matrix is authorized by this baseline alone.
