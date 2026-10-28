"""Build the repository's Markdown sources without maintaining duplicate pages."""

from docutils import nodes
from sphinx.writers.html5 import HTML5Translator

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
templates_path = ["_templates"]
html_title = "OpenT1D"
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


def document_language(docname):
    """Research reports are Dutch; public guides and generated pages are English."""
    dutch = docname.startswith("docs/onderzoek/") or docname == (
        "docs/research/internal-verification-results"
    )
    return "nl" if dutch else "en"


def mark_report_titles(app, doctree):
    """Preserve Dutch pronunciation when titles are reused in navigation."""
    if document_language(app.env.docname) == "nl":
        for title in doctree.findall(nodes.title):
            title[:] = [nodes.inline("", "", *title.children, classes=["language-nl"])]


def set_page_language(app, pagename, templatename, context, doctree):
    # Furo's base.html uses this value on <html>. Do not change the global
    # Sphinx locale: its navigation, controls and generated pages stay English.
    context["language"] = document_language(pagename)


class LanguageHTMLTranslator(HTML5Translator):
    """Keep generated English permalink labels separate from article language."""

    def add_permalink_ref(self, node, title):
        start = len(self.body)
        super().add_permalink_ref(node, title)
        if len(self.body) > start:
            # Preserve Furo's heading > .headerlink selector: a wrapper changes
            # hover visibility and spacing. Annotate Sphinx's generated anchor.
            self.body[start] = self.body[start].replace(
                '<a class="headerlink"', '<a lang="en" class="headerlink"', 1
            )


def setup(app):
    # Annotate titles before Sphinx's collectors copy them into the ToC.
    app.connect("doctree-read", mark_report_titles, priority=400)
    app.connect("html-page-context", set_page_language)
    app.set_translator("html", LanguageHTMLTranslator)
