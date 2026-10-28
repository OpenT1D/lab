# Working in OpenT1D

OpenT1D has implemented bounded M1 and M2 workflows; independent human M2 reproduction remains open as a later external-review item, not a blocker for internal verification or M3 preparation. M3 adds synthetic CGM forecast preparation; human evaluation remains conditional on authorized release verification. Read the README,
CONTRIBUTING.md and the relevant part of ROADMAP.md before making substantial
changes. The roadmap is the canonical implementation plan.

## Project direction

- Build an open modular T1D laboratory with shared infrastructure and useful modules.
- Reuse upstream models where suitable; whole-engine integration is valid modularity.
- Distinguish planned features, working software, reproduced references and scientific evidence.
- Preserve model ancestry, units, time conventions, process ownership and source attribution.
- Do not invent citations, data access, numerical results, APIs, partnerships or release metadata.

## Repository work

- Write public-facing guides in English; preserve the Dutch research reports.
- Keep each guide canonical and update `docs/_toc.yml` for new public documentation.
- Use `uv sync --locked` and `uv run --locked python scripts/check.py` for repository checks.
- The root Python environment is for tooling; it does not contain a simulation package.
  Native M0 probes use separate locked environments under `experiments/m0/`.
- Add numerical checks when model behavior exists and the change warrants them.
- Keep research inputs, credentials and private health records out of version control and logs.
- Describe checks actually run and limitations that remain. Do not equate a CI pass with model validity.

Use short decision records for changes to shared architecture or scientific
conventions. Routine fixes do not require a decision record or extra approval.
