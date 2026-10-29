"""Regression checks for the documentation build and its publication boundary."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.check import check_navigation

REPOSITORY = Path(__file__).resolve().parents[1]


class EffectiveLanguages(HTMLParser):
    """Read inherited languages of rendered text and accessible control labels."""

    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self):
        super().__init__()
        self.stack = []
        self.root_language = None
        self.text = []
        self.labels = []
        self.permalink_parents = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        language = attrs.get("lang", self.stack[-1][1] if self.stack else None)
        if tag == "html":
            self.root_language = language
        if tag == "a" and "headerlink" in attrs.get("class", "").split():
            self.permalink_parents.append(self.stack[-1][0])
        for attribute in ("aria-label", "title", "placeholder"):
            if attrs.get(attribute) and any(element == "body" for element, _ in self.stack):
                self.labels.append((attrs[attribute], language))
        if tag not in self.VOID_ELEMENTS:
            self.stack.append((tag, language))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack and data.strip():
            self.text.append((data.strip(), self.stack[-1][1]))


class DocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="opent1d-docs-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.write("docs/index.md", "# Documentation\n\nPublic documentation.\n")
        self.write("docs/_toc.yml", "root: docs/index\n")
        shutil.copy2(REPOSITORY / "docs" / "conf.py", self.root / "docs" / "conf.py")
        icon = Path("experiments/gui/static/icon.svg")
        (self.root / icon).parent.mkdir(parents=True)
        shutil.copy2(REPOSITORY / icon, self.root / icon)

    def write(self, name: str, text: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-E",
                "-a",
                "-W",
                "--keep-going",
                "-b",
                "html",
                "-c",
                str(self.root / "docs"),
                str(self.root),
                str(self.root / "_build" / "html"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_local_notes_are_not_published_or_indexed(self) -> None:
        names = [
            "data/private/notes.md",
            "data/raw/notes.md",
            "results/notes.md",
            "build/notes.md",
            ".local/notes.md",
            "docs/.local/notes.md",
            "unlisted-notes.md",
        ]
        for name in names:
            self.write(name, "# Local notes\n\nPRIVATE_SYNTHETIC_SENTINEL\n")
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.root / "_build" / "html"
        self.assertTrue((output / "docs" / "index.html").exists())
        for name in names:
            self.assertFalse((output / Path(name).with_suffix(".html")).exists(), name)
        for path in [*output.rglob("*.html"), output / "searchindex.js"]:
            self.assertNotIn("PRIVATE_SYNTHETIC_SENTINEL", path.read_text(encoding="utf-8"))

    def test_missing_document_fails_the_build(self) -> None:
        self.write("docs/index.md", "# Documentation\n\n[Missing](missing.md)\n")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing.md", result.stderr)

    def test_rendered_reports_guides_and_ui_use_english(self) -> None:
        self.write(
            "docs/_toc.yml",
            "root: docs/index\nentries:\n  - file: docs/research/foundation-report\n"
            "  - file: docs/research/internal-verification-results\n"
            "  - file: docs/research/english-guide\n",
        )
        self.write(
            "docs/research/foundation-report.md",
            "# Research report\n\nResearch content.\n\n## Research findings\n\n"
            "More research content.\n",
        )
        self.write(
            "docs/research/internal-verification-results.md",
            "# Historical verification report\n\nResearch content.\n\n"
            "## Research findings\n\nHistorical findings.\n",
        )
        self.write("docs/research/english-guide.md", "# English guide\n\nResearch guidance.\n")
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.root / "_build" / "html"
        reports = {"docs/research/foundation-report", "docs/research/internal-verification-results"}
        for page in (
            *sorted(reports),
            "docs/research/english-guide",
            "docs/index",
            "search",
            "genindex",
        ):
            with self.subTest(page=page):
                parsed = EffectiveLanguages()
                parsed.feed((output / f"{page}.html").read_text(encoding="utf-8"))
                self.assertEqual(parsed.root_language, "en")
                self.assertTrue(all(lang == "en" for _, lang in parsed.text), parsed.text)
                self.assertIn(("Skip to content", "en"), parsed.text)
                self.assertIn(("Research report", "en"), parsed.text)
                self.assertIn(("Toggle site navigation sidebar", "en"), parsed.labels)
                self.assertTrue(parsed.labels)
                self.assertTrue(all(lang == "en" for _, lang in parsed.labels), parsed.labels)
                if page in reports:
                    # Furo styles permalink visibility using direct children of
                    # headings; language annotations must not insert a wrapper.
                    self.assertEqual(parsed.permalink_parents, ["h1", "h2"])
                    self.assertIn(("Research content.", "en"), parsed.text)
                    self.assertIn(("Research findings", "en"), parsed.text)
                    self.assertIn(("On this page", "en"), parsed.text)
                    self.assertIn(("Previous", "en"), parsed.text)
                elif page == "docs/index":
                    self.assertEqual(parsed.permalink_parents, ["h1"])
                    self.assertIn(("Public documentation.", "en"), parsed.text)
                elif page == "genindex":
                    self.assertIn(("Index", "en"), parsed.text)

    def test_clean_build_removes_retired_pages_and_downloads(self) -> None:
        self.write("docs/_toc.yml", "root: docs/index\nentries:\n  - file: docs/retired\n")
        self.write("docs/retired.md", "# Retired\n\n[Download](retired.txt)\n")
        self.write("docs/retired.txt", "SYNTHETIC_RETIRED_CONTENT\n")
        initial = self.build()
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        output = self.root / "_build" / "html"
        self.assertTrue((output / "docs" / "retired.html").exists())
        self.assertTrue(list(output.rglob("retired.txt")))

        self.write("docs/_toc.yml", "root: docs/index\n")
        (self.root / "docs" / "retired.md").unlink()
        (self.root / "docs" / "retired.txt").unlink()
        # Exercise the production build, including its cleanup, in the fixture.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; "
                "from scripts.check import build_documentation; "
                "build_documentation(Path(sys.argv[1]))",
                str(self.root),
            ],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((output / "docs" / "index.html").exists())
        self.assertFalse((output / "docs" / "retired.html").exists())
        self.assertFalse(list(output.rglob("retired.*")))
        self.assertNotIn("retired", (output / "searchindex.js").read_text(encoding="utf-8"))

    def test_missing_heading_fails_the_build(self) -> None:
        self.write("docs/index.md", "# Documentation\n\n[Missing](#missing-heading)\n")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing-heading", result.stderr)

    def test_new_public_guide_requires_navigation_entry(self) -> None:
        with self.assertRaisesRegex(ValueError, "docs/new-guide.md"):
            check_navigation(["docs/index.md", "docs/new-guide.md"], self.root)

    def test_navigation_rejects_missing_or_ignored_page(self) -> None:
        self.write("docs/_toc.yml", "root: docs/index\nentries:\n  - file: data/private/notes\n")
        with self.assertRaisesRegex(ValueError, "data/private/notes.md"):
            check_navigation(["docs/index.md"], self.root)

    def test_github_and_agent_guides_are_not_required_in_site(self) -> None:
        check_navigation(
            ["docs/index.md", ".github/pull_request_template.md", "AGENTS.md"], self.root
        )
