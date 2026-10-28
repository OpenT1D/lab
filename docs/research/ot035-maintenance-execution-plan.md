# OT-035 and maintained runtimes — execution plan

**Frozen scope:** 4 October 2026, baseline
`9e7348e56fc3ec5b9ed404423b6cb6a2eeb51a4b`.
This is an implementation plan, not a verification result.
[Decision 0059](../decisions/0059-maintained-runtimes-and-local-gui.md) owns
the shared architectural and scientific boundaries.

## Isolated ownership

| Managed worktree / branch | Ownership |
| --- | --- |
| `security-tooling` / `codex/security-tooling` | Root HTTP lock, explicit historical-reader helper and tests |
| `security-native-runtime` / `codex/security-native-runtime` | Maintained native runtime, successor M4 execution identity and native acceptance |
| `security-g2p2c` / `codex/security-g2p2c` | Coherent PyTorch migration, checkpoint boundary, source/causal parity and replay |
| `gui-runner` / `codex/gui-runner` | Loopback service, frozen inputs, allowlisted subprocesses, lifecycle and service tests |
| `gui-pilot` / `codex/gui-pilot` | Accessible browser forms and result display |
| `gui-integration` / `codex/gui-integration` | Decision/contract freeze, shared task hooks, guides/navigation, CI and reviewed integration |

Three agents initially own disjoint maintenance packages. Root coordinates,
freezes contracts and develops the GUI while these run. Freed agents then
cross-review GUI security, process ownership and browser acceptance. Never edit
another package's shared file without handing off ownership. Commit each
reviewed increment and integrate on the dedicated branch; preserve main.

## Dependency and historical acceptance

Inspect actual advisory ranges and compatible wheels before choosing a patched
runtime. Root HTTP changes should leave unrelated package blocks unchanged.
Native changes retain historical locks/protocols and attributed numeric engine
and package pins; a new execution identity binds the maintained environment.
PyTorch maintenance must not silently redefine accepted historical checkpoints
or findings. Record runtime-induced differences instead of relaxing gates.

Historical reconstruction uses an existing explicit trusted clean checkout and
full Git revision, with current standard-library Python and fixed known reader
commands. Verify archive inventories before/after, fresh output, source identity,
deadline/signal cleanup and refusals for dirty/changed/mismatched inputs. No
installation of historical vulnerable dependencies is needed for this route.

## GUI contract

One supported synthetic initial-load task and one active study. The UI offers
declared source/declaration selection, existing scenario subset, budgets,
passive configuration/setup checks, explicit locked install, explicit run,
cancel, recorded result inspection and explicit native reconstruction. Select
the maintained execution successor explicitly once its identity is frozen.

The server uses a new package outside existing scientific inventories. Static
assets and its API are served only on loopback. Host/Origin/session-token checks,
fixed argv, bounded inputs, safe workspace paths, escaped text and isolated job
administration protect its local control surface. It is not a sandbox for a
researcher's Python source.

Configuration/source identities are frozen before dispatch. Output directories
are fresh and cannot overlap inputs. The native CLI is the owner of science and
its process descendants. Cancellation waits for its cleanup and preserves
available failure evidence. Progress reports observable stages; do not invent
a completion percentage. Report completeness and verified reconstruction remain
separate from process exit or successful installation.

## Predeclared acceptance

1. The same configuration has matching scientific GUI/CLI outcomes; execution
   timestamps, checkout paths and administrative identifiers may differ.
2. Invalid configurations, changed frozen sources, absent runtimes and overlapping
   output fail before model execution.
3. Failed sources and interrupted studies preserve complete planned denominators
   and visible status; no partial prefix becomes a successful study.
4. Cancellation/deadline checks leave no owned workers behind.
5. Authoritative reconstruction reproduces report bytes and retains failed status.
6. Browser checks cover configuration, missing setup, start/cancel, successful
   results and reconstruction; labels and keyboard operation remain usable.
7. Root locked checks and relevant native numerical/process tests pass. Record
   commands, exits, hashes, runtime identities and preserved failures.

Canonical guides, navigation, roadmap and changelog describe implemented scope
only after these checks. Recheck hosted CI, reporting account restrictions
separately from code failures. Do not change billing, visibility or protection
settings as a workaround.

## Independent exercise

Prepare a new GUI task on an identified clean checkout, with synthetic inputs,
source/rights scope and an uncoached configure/check/run/inspect/reconstruct
exercise. Record actual assistance, errors and participant interpretation only
after a real researcher performs it. The original P1 exercise remains separate.
Internal verification may finish before a tester is available; independent
usability remains open in that case.
