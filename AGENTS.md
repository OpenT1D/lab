# Working in OpenT1D

Read [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the relevant
part of [ROADMAP.md](ROADMAP.md) before substantial changes. The roadmap owns
implementation order. The [development guide](docs/development.md) owns the
component/test map, environment selection and task/review handoff.

The initial maintained public exercise is the two synthetic MMTT tasks. Other
bounded workflows have internal verification records; independent usability,
human-data evaluation and biological validity remain separate open questions.
Initial publication used disabled public Actions. Hosted activation requires the
reviewed [public runtime and CI boundary](docs/publication-security.md), verified
settings and current-revision results. Local checks are not hosted CI results.

## Project direction

- Build shared infrastructure around useful research tasks; reuse upstream
  models where suitable, including whole native engines.
- Distinguish planned features, working software, reproduced references and scientific evidence.
- Preserve model ancestry, units, time conventions, process ownership and source attribution.
- Do not invent citations, data access, numerical results, APIs, partnerships or release metadata.

## Repository work

- Write public-facing guides in English; preserve the Dutch research reports.
- Keep each guide canonical and update `docs/_toc.yml` for new public documentation.
- Use `uv sync --locked` and `uv run --locked python scripts/check.py` for repository checks.
- Root Python is tooling, orchestration and the standard-library MMTT tasks, not
  a simulation package. Native work uses its separately locked task environment.
- Use isolated worktrees for concurrent writing, at most two implementation
  changes initially, one owner per shared interface and a separate diff review.
  Assign the final full repository check to one owner.
- Add numerical checks when model behavior exists and the change warrants them.
- Preserve frozen baselines and tolerances; investigate mismatches before
  proposing a scientifically justified change.
- Keep research inputs, credentials and private health records out of version control and logs.
- Describe checks actually run and limitations that remain. Do not equate a CI pass with model validity.

Use short decision records for changes to shared architecture or scientific
conventions. Routine fixes do not require a decision record or extra approval.
