# OT-057 MMTT interface verification

**Status, 22 October 2026:** all seven internal UI/UX findings are implemented,
locally retested and integrated into local and GitHub main. This record covers
internal software verification. Windows execution, independent human usability,
the comparative OT-056 researcher pilot and empirical applicability remain open.
The [roadmap](roadmap-history-2026-10-28.md#mmtt-interface-follow-up-ot-057) owns the scope.

## Implementation and integration identity

The initial internal walkthrough exercised four supplied examples on main
`9e8078ffa223bf513bd8e0a4085538dbeb44dda6`. The fixes were developed in a separate
worktree on `codex/mmtt-uiux-fixes` and committed as
`7447831ee4995f4cdd4b0179253d2d71d60af02b`.

The 19 October merge `ac94080c70b855b4e67a86c677e654caf0395bde` has exactly the
same file tree as that implementation commit. On 22 October, local main and
GitHub `refs/heads/main` both resolved to this merge. The maintainer requested
skipping CI/CD: the merge message includes `[skip ci]`, workflow files were not
changed, and the GitHub Actions query returned zero runs for the merge SHA.
Local verification is not a hosted CI pass. No public release or updated Windows
packet is established by this integration.

## Seven resolved findings

| Finding | Implemented behavior | Internal verification |
| --- | --- | --- |
| UX-01: saved-plan editing | **Use frozen plan** and **Edit as new plan** separate reuse from a newly checked freeze; original plans stay unchanged | Both task-copy routes preserve settings edits and input identities; changed-input refusal is covered by regression checks |
| UX-02: hidden invalid inputs | Errors name the field and variant, open its details and focus the input | Hidden nominal volume 0 was revealed, corrected to 5 L and retained through freezing |
| UX-03: completed-operation navigation | **View result** opens the matching rendered report; running progress/cancellation remains accessible | Direct navigation and reopening exercised locally; regression checks cover delayed loading/polling and late navigation |
| UX-04: excessive setup detail | Supplied settings are compact; **Review or change assumptions** exposes optional details | Both supplied routes exercised; affected visit coverage and invalid fields remain visible |
| UX-05: hard-to-read sampling reports | Headline and full/five/four/three-time comparisons precede retained details | Allocation/variant counts, unresolved outcomes and unavailable comparisons checked against native reports |
| UX-06: indistinguishable saved items | Example or optional user names persist as GUI metadata, outside scientific archives | Named plans/results survived reload and reopened the correct report; restart and legacy fallback covered by regression checks |
| UX-07: ambiguous completion | Execution, result completeness and saved-report verification have separate states | The low/censored example stayed **Analysis finished · results incomplete** after successful reconstruction; actual failure/cancellation distinctions covered by regression checks |

## Observed macOS browser results, 19 October

Five plans were frozen: Task 1 original and 5 L copy, Task 2 direction-reversal
original and 5 L copy, and Task 2 low/censored original. The Task 2 copy was
checked through freezing; it was not one of the four executed analyses below.
Original plans retained their 4.585 L setting and recorded input hashes.

| Executed analysis | Report completeness | Saved report check |
| --- | --- | --- |
| Task 1 consistent-increase original | Complete | Native reader verified |
| Task 1 consistent-increase 5 L copy | Complete | Native reader verified |
| Task 2 constructed direction reversal | Complete: 60/60 required variant pairs; 7,680/7,680 perturbation pairs | Native reader verified |
| Task 2 low/censored control | Incomplete: 36/60 required variant pairs; 6,000/7,680 perturbation pairs | Native reader verified; incompleteness preserved |

The direction-reversal example showed three-time reversals for 2/2 development
and 3/3 evaluation participants per variant. These are engineered controls,
not empirical findings. Variants are not additional participants. The compact
comparison retains allocation-specific unavailable outcomes and native
denominators; successful reconstruction does not make an incomplete report
complete or establish scientific validity.

The final implementation passed `uv sync --locked` and
`uv run --locked python scripts/check.py`: **1,393 tests, 13 existing skips**,
format/lint checks, documentation metadata/navigation and the warning-as-error
documentation build. No estimator, units, frozen scientific convention or native
archive contract was changed by these interface fixes.

Local ignored evidence is retained in the implementation worktree under
`results/uiux-mmtt-fixes-2026-10-19/`: `verification.json` records plan/input and
report identities, `repository-check.log` records the final check, and browser
captures cover field recovery, both report states, direct navigation and named
results after reload. These local files are not distributed by this guide.

## Remaining evidence and next actions

1. The [22 October beginner packet](mmtt-beginner-packet-verification.md) now
   binds a clean implementation based on integrated main, with local receiving
   installation and both MMTT flows checked. Existing packets and installed
   checkouts do not automatically follow main.
2. Record installation, localhost access, start/stop and both task routes on an
   actual Windows/WSL host. The macOS run does not establish Windows support.
3. Observe independent users and retest any resulting fixes. A beginner's session
   is separate from the [OT-056 comparative pilot](ot056-researcher-pilot.md),
   which still requires qualified comparators, researchers and independent review.
4. Retain the OT-053 synthetic boundary until authorized observations and the
   empirical protocol requirements are satisfied. No comparative product value,
   biological validity or treatment benefit is established here.

The [Task 1 guide](../observation-analysis.md) and
[Task 2 guide](../mmtt-sampling.md) remain canonical for operation; this record
owns the bounded interface verification rather than duplicating their steps.
