"""Run the same repository checks locally and in CI."""

import argparse
import subprocess
import sys
from pathlib import Path
from shutil import rmtree
from time import perf_counter

from sphinx_external_toc.parsing import parse_toc_yaml

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, root: Path = ROOT) -> None:
    print(f"\n> {' '.join(args)}", flush=True)
    started = perf_counter()
    try:
        subprocess.run(args, cwd=root, check=True)
    finally:
        print(f"Elapsed: {perf_counter() - started:.3f} seconds", flush=True)


def build_documentation(root: Path = ROOT) -> None:
    """Replace the generated site so removed pages cannot remain reachable."""
    output = root / "_build" / "html"
    if output.exists():
        rmtree(output)
    run(
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
        "docs",
        ".",
        "_build/html",
        root=root,
    )


def check_navigation(markdown: list[str], root: Path = ROOT) -> None:
    """Require public Markdown pages to be explicitly listed before publishing."""
    site_map = parse_toc_yaml(root / "docs" / "_toc.yml")
    if site_map.globs():
        raise ValueError("List documentation pages explicitly in docs/_toc.yml; do not use globs.")
    listed = {name.removesuffix(".md") + ".md" for name in site_map}
    public = {
        name
        for name in markdown
        if name != "AGENTS.md" and not any(part.startswith(".") for part in Path(name).parts)
    }
    missing = sorted(public - listed)
    unavailable = sorted(listed - public)
    errors = []
    if missing:
        errors.append(f"Add public documentation to docs/_toc.yml: {', '.join(missing)}")
    if unavailable:
        errors.append(
            f"ToC pages missing or excluded from Git's file list: {', '.join(unavailable)}"
        )
    if errors:
        raise ValueError("\n".join(errors))


def check_style() -> None:
    # Include new, untracked files so the first contribution is checked too.
    files = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    files = sorted({name for name in files if name and (ROOT / name).is_file()})
    markdown = [name for name in files if name.endswith(".md")]
    yaml = [name for name in files if name.endswith((".yml", ".yaml", ".cff"))]
    python = ("docs/conf.py", "scripts", "tests", "experiments", "packaging/sdk/opent1d_lab")
    run("ruff", "check", *python)
    run("ruff", "format", "--check", *python)
    run("pymarkdown", "--config", ".pymarkdown.json", "scan", *markdown)
    run("yamllint", "--strict", *yaml)
    run("cffconvert", "--validate")
    check_navigation(markdown)


def check_tests() -> None:
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("style", "tests", "docs"))
    args = parser.parse_args(argv)
    stages = {"style": check_style, "tests": check_tests, "docs": build_documentation}
    for stage in (args.stage,) if args.stage else stages:
        stages[stage]()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
