"""Prepare a local source repository without private development history."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
from pathlib import Path


def git(root, *args, identity=None):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    if identity:
        name, email = identity
        env.update(
            GIT_AUTHOR_NAME=name,
            GIT_AUTHOR_EMAIL=email,
            GIT_COMMITTER_NAME=name,
            GIT_COMMITTER_EMAIL=email,
        )
    return subprocess.run(
        ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", *args],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
    ).stdout


def prepare(source, output, *, author_name, author_email):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not re.fullmatch(r"(?:[0-9]+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com", author_email):
        raise ValueError("Use the maintainer's GitHub noreply email for the new history")
    if not author_name.strip() or any(char in author_name for char in "\r\n<>"):
        raise ValueError("Supply a valid public author name")
    if output.exists():
        raise ValueError("Output must be a new directory; existing work is never replaced")
    if output.is_relative_to(source):
        raise ValueError("Keep the public candidate outside the private source checkout")
    if git(source, "rev-parse", "--show-toplevel").decode().strip() != str(source):
        raise ValueError("Source must be the repository root")
    if git(source, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("Commit and review the source changes before exporting")
    if git(source, "ls-tree", "--name-only", "HEAD", "publication-snapshot.json").strip():
        raise ValueError(
            "Export from the reviewed private preparation branch, not a prior snapshot"
        )
    if any(row.startswith(b"160000 ") for row in git(source, "ls-tree", "-r", "HEAD").splitlines()):
        raise ValueError("Submodule contents need an explicit distribution review")
    revision = git(source, "rev-parse", "HEAD").decode().strip()
    archive = git(source, "archive", "--format=tar", "HEAD")
    output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as exported:
        exported.extractall(output, filter="data")
    files = {
        str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema": "opent1d.publication-snapshot/1",
        "private_source_revision": revision,
        "history": "New root commit; private development objects and refs are not copied.",
        "exported_files_sha256": files,
        "historical_evidence": "See docs/public-source.md and publication-source-map.json.",
        "published": False,
    }
    (output / "publication-snapshot.json").write_text(json.dumps(manifest, indent=2) + "\n")
    git(output, "init", "--initial-branch=main")
    git(output, "config", "user.name", author_name)
    git(output, "config", "user.email", author_email)
    names = b"\0".join(name.encode() for name in [*files, "publication-snapshot.json"]) + b"\0"
    listing = output / ".git" / "publication-files"
    listing.write_bytes(names)
    try:
        git(output, "add", "--pathspec-from-file=" + str(listing), "--pathspec-file-nul")
    finally:
        listing.unlink()
    git(
        output,
        "commit",
        "-m",
        "Initial public source snapshot",
        identity=(author_name, author_email),
    )
    if git(output, "rev-list", "--all", "--count").strip() != b"1":
        raise ValueError("Unexpected history in prepared repository")
    if git(output, "remote").strip() or git(output, "tag").strip():
        raise ValueError("Unexpected remote or tags in prepared repository")
    git(output, "fsck", "--full", "--no-reflogs")
    return {
        "private_source_revision": revision,
        "initial_commit": git(output, "rev-parse", "HEAD").decode().strip(),
        "commit_count": 1,
        "exported_files": len(files),
        "remote_count": 0,
        "published": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--author-name", required=True)
    parser.add_argument("--author-email", required=True)
    args = parser.parse_args()
    try:
        receipt = prepare(
            args.source,
            args.output,
            author_name=args.author_name,
            author_email=args.author_email,
        )
    except (ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
