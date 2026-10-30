# Installed MMTT sampling integration

## Selected scope before implementation

Base: `120178d1a0aca75b0222f9e37b09424389dd1d4d`, merged roadmap PR 37.
Implement step 2 of the [selected window](../../ROADMAP.md#selected-development-window-first-integrated-laboratory)
under [decision 0085](../decisions/0085-installed-mmtt-sampling.md).
The integration owner implements SDK/shared services and workbench on
`codex/installed-mmtt-sampling`, with separate read-only technical review.
One owner runs the final full check. Agent review is not independent user or
scientific acceptance.

Reuse the native [sampling task](../mmtt-sampling.md) without changing its
scientific files, protocols, units, frozen controls or tolerances. Support all
four supplied synthetic cases through the existing installed Python/CLI and
loopback workbench. Arbitrary GUI intake and editable studies remain subsequent
work. Preserve current MMTT sensitivity and historical/native M4 boundaries.

## Acceptance and counterexamples fixed before outputs

1. Build and noneditably install the SDK in a fresh POSIX CPython 3.12 environment;
   from an unrelated directory, export inputs, validate, freeze, inspect, run,
   retry, reconstruct and relocate sampling through CLI and Python.
2. Compare complete native and adapted parent/child report bytes for the same
   frozen scientific plan. Retain the engineered information-loss reversal and
   constant-input control; do not refreeze expected scientific outcomes.
3. Reject evaluation-containing development evidence, changed development cells,
   changed design/allocation, missing resources and changed source identity.
   Refusal must not publish a freeze or launch an estimator.
4. Preserve incomplete and cancelled attempts, all planned schedules/people/
   assumptions/draws, explicit retry and `allow_failed` semantics. Observe owned
   cleanup and preserve an unrelated process; a forced stop may remain forensic.
5. Refuse resealed missing/swapped child reports, dropped draws and parent/child
   contradictions. Opening/importing never executes archived Python. Rebuild all
   available parent/child reports after original input/project paths are absent.
6. Use the installed GUI and SDK on one project with identical plan/attempt IDs.
   Prepare/freeze/run/verify sampling, inspect its development/evaluation report,
   access unchanged child reports and reopen the relocated project after restart.
   Reject unknown/traversal paths and withdraw tampered nested report copies.
7. Run relevant native sampling reference/workflow, shared service, SDK, GUI and
   frontend checks; inspect an actual installed browser flow. Preserve source
   inventories and legacy controls. One owner runs `uv sync --locked` and
   `uv run --locked python scripts/check.py` on the final integrated revision.

## Evidence and limitations

Implementation, checks, exact artifact identities and review results are pending.
Retain actual receipts under ignored `results/installed-mmtt-sampling/`; report
failures and unavailable checks explicitly. Root checks do not qualify other
OS/application combinations, native M4 parity, human-data applicability,
independent usability or biological validity. No human session is selected.
