"""Build the repository's Markdown sources without maintaining duplicate pages."""

project = "OpenT1D"
copyright = "2026, OpenT1D contributors"
author = "OpenT1D contributors"

extensions = ["myst_parser", "sphinx_external_toc", "sphinxcontrib.mermaid"]
source_suffix = {".md": "markdown"}
external_toc_path = "docs/_toc.yml"
# Only explicitly listed pages belong in the site. Sphinx does not use .gitignore.
external_toc_exclude_missing = True
exclude_patterns = [
    ".*",
    "**/.*",
    "_build/**",
    "data/**",
    "results/**",
    "build/**",
    "dist/**",
    "AGENTS.md",
]
myst_enable_extensions = ["colon_fence", "deflist", "fieldlist", "tasklist"]
myst_fence_as_directive = ["mermaid"]
myst_heading_anchors = 6
nitpicky = True
mermaid_version = "11.12.1"

html_theme = "furo"
language = "en"
html_title = "OpenT1D"
# Reuse the app icon; Sphinx copies it to _static and resolves each page depth.
html_favicon = "../experiments/gui/static/icon.svg"
html_show_sourcelink = False
html_theme_options = {
    "source_repository": "https://github.com/OpenT1D/lab/",
    "source_branch": "main",
    "source_directory": "",
}

# External sites may reject automated fragment checks. Local anchors are checked by MyST.
linkcheck_anchors = False
linkcheck_timeout = 20
linkcheck_retries = 1
linkcheck_rate_limit_timeout = 30
# Historical development evidence remains in the separate private archive.
# Exclude only those authenticated archive URLs; public OpenT1D/lab links are checked.
linkcheck_ignore = [r"https://github\.com/OpenT1D/OpenT1D(?:/.*)?$"]
