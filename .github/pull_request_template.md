## Problem and change

Describe the problem and minimal reproduction (synthetic inputs), or the claim
being corrected. Explain the resulting behavior and link the related issue and
applicable roadmap item.

## Scope and contracts

State the smallest complete change, affected components, reuse and exclusions.
Identify scientific/compatibility contracts preserved or deliberately changed:
units, timing, causal inputs, source identity, failure accounting, frozen
baselines/tolerances, archive readers, runtimes and upstream rights as relevant.
Link a decision record if shared architecture or scientific conventions change.

## Acceptance and counterexamples

Describe the cases that demonstrate the intended behavior and a negative case
that could expose an incomplete fix. For a defect, record the old behavior and
the result after correction. Documentation-only changes can name the claims,
links and navigation checked.

## Evidence

List the revision/dirty state, commands actually run, outcomes, skips and retained
output locations. Identify the owner/result of the final full repository check;
explain missing checks. Distinguish local results from hosted CI. For models or
experiments, link the reference, protocol and numerical evidence and state the
scope of scientific review. Do not refreeze outputs or loosen tolerances merely
to pass a check.

## Limitations and impact

Note changed results, compatibility, upstream rights or unresolved assumptions
when relevant. Mention substantial AI assistance when useful for review.

## Review handoff

Give the reviewer the changed behavior, relevant callers/readers and unresolved
risks in a few lines. The separate technical review records its reviewed
revision, counterexamples, findings and disposition. Agent review is not
independent scientific validation.

## Review checklist

- [ ] The change is focused and its purpose is explained.
- [ ] Relevant checks were run, or missing checks are explained above.
- [ ] Documentation and scientific claims match the implemented behavior.
- [ ] Included material can be contributed under its stated terms; attribution is preserved.
- [ ] No credentials, personal health records or restricted data are included.
- [ ] Changelog, model card or protocol updated where relevant, or not applicable.
