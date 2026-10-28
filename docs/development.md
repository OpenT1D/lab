# Development guide

The root toolchain checks the research software and builds the repository documentation. It does not install OpenT1D as a simulation package. No physiological models or clinical datasets are downloaded by these commands.

## Set up

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). From your clone, run:

```sh
uv sync --locked
```

The repository selects Python 3.12 through `.python-version`. uv creates an isolated `.venv` and installs the versions in `uv.lock`; it can download Python if the selected version is unavailable. The first setup needs network access. See [uv's Python guidance](https://docs.astral.sh/uv/guides/install-python/) if your environment manages Python separately.

`pyproject.toml` currently contains a development dependency group only. There is no published simulation package. The checkout-based simulator commands use a separate pinned environment, documented in the [M1 tutorial](m1-tutorial.md) and the [M2 tutorial](m2-tutorial.md). M2 also uses the separately locked LT1 Node environment; the root environment remains tooling and orchestration only.

## Check a change

Run the same entry point used by CI:

```sh
uv run --locked python scripts/check.py
```

It checks Python tooling style, Markdown, YAML, citation metadata, navigation, documentation regression tests and a clean documentation build. Sphinx warnings, including unresolved document references, fail the build. The file checks include untracked, non-ignored files, so they also cover a first contribution before it is committed.

The Markdown configuration allows long prose lines and template checklists. It checks structure rather than imposing hard wrapping on research reports. The root suite also checks bounded contracts, artifact validation and analysis fixtures. It does not execute native physiology; run the isolated checks in the canonical tutorials as appropriate. Neither passing tooling tests nor native regression equality establishes biological validity.
The [public source policy](publication-security.md) limits the initial supported
exercise to the two synthetic MMTT tasks. Default CI runs the root suite and
standard-library boundary checks; historical native jobs require explicit
private-archive dispatch and cannot run in the public snapshot.

## Preview the documentation

```sh
uv run --locked python scripts/check.py
uv run --locked python -m http.server 8000 --bind 127.0.0.1 --directory _build/html
```

Open `http://127.0.0.1:8000/docs/index.html`. Stop the server with Ctrl+C. You can open `_build/html/docs/index.html` directly for reading; use the local server for search and browser-loaded assets.

Rerun `scripts/check.py` after changes to refresh the preview. It replaces the generated HTML directory, including old pages and downloads. A direct Sphinx rebuild does not remove all obsolete output, even with `-E -a`; use the repository check before sharing or publishing the site.

Markdown files are the canonical content on GitHub and in the generated site. Sphinx, MyST and the external table of contents build root documents and `docs/` together. List each new public guide explicitly in `docs/_toc.yml`; the repository check catches missing entries. Do not create a second copy of the README or roadmap.

The site includes only the listed pages. Data, results, build outputs and hidden directories are excluded from page discovery. Sphinx does not honor `.gitignore`, so those exclusions are configured separately. Review explicit includes, images and downloadable asset links as well: they can copy a file into the site even when it is not a page.

The research report's Mermaid diagram uses a pinned browser library from jsDelivr and requires network access to render. The document text, navigation and search are served locally.

The [M3 tutorial](m3-tutorial.md) owns the separately locked statistical-estimator environment and synthetic forecast checks. Repository tests also validate M3 contracts and artifacts; native estimator execution remains separate, as do all original physiological regression jobs.

## Individual checks

```sh
uv run --locked ruff check docs/conf.py scripts tests experiments
uv run --locked ruff format --check docs/conf.py scripts tests experiments
uv run --locked python -m unittest discover -s tests -v
uv run --locked cffconvert --validate
```

External links can be checked separately:

```sh
uv run --locked sphinx-build -E -a -b linkcheck -c docs . _build/linkcheck
```

Review `_build/linkcheck/output.txt`. Some publishers and private repositories reject automated requests. Investigate those results and retain a narrow, documented exception only when needed. Network availability must not become an unrelated pull-request merge blocker. Internal references are checked in the required HTML build.

## Dependencies

Use `uv add --group dev PACKAGE` for a justified new repository tool. Commit both `pyproject.toml` and `uv.lock`, and run the full checks. To update an existing tool, use `uv lock --upgrade-package PACKAGE`, then `uv sync --locked` and the same checks.

Review dependency changes for compatibility and workflow impact. GitHub Actions are pinned to full commit hashes with readable release comments. The inactive `.github/dependabot.example.yml` preserves a future update configuration. Automatic version updates are disabled for the initial source publication.

## Documentation conventions

Use a clear title and short sections. Prefer relative links to repository files, primary sources for scientific claims and explicit status for proposed features. Add an explanation of units and assumptions when an example depends on them.

Keep Dutch research reports under `docs/onderzoek/`. The site uses that directory and the explicitly retained historical `docs/research/internal-verification-results.md` report to set their document language to Dutch while retaining English interface labels. Other guides and generated index/search pages use English. If a new document needs another language, update this convention, the language configuration and its rendered-HTML regression test together.

The M1 and M2 tutorials each own their runnable workflow. How-to guides explain specific tasks, reference pages define exact contracts and explanations describe design choices. Avoid documenting a hypothetical API as if it already exists.
