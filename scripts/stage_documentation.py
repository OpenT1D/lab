"""Stage visible regular Sphinx output for PR downloads and trusted Pages deployment."""

import argparse
import json
import shutil
import stat
from pathlib import Path


def stage(source: Path, destination: Path) -> dict:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Documentation source must be a real directory")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Documentation destination must not already exist")
    source = source.resolve()
    destination = destination.absolute()
    if source == destination or source in destination.resolve().parents:
        raise ValueError("Documentation destination must be outside its source")
    files = []
    for path in sorted(source.rglob("*")):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("Documentation output contains a symbolic link")
        if stat.S_ISREG(metadata.st_mode):
            if metadata.st_nlink != 1:
                raise ValueError("Documentation output contains a hard link")
            relative = path.relative_to(source)
            if not any(part.startswith(".") for part in relative.parts):
                files.append((path, relative, metadata.st_size))
        elif not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("Documentation output contains a special file")
    required = {Path("index.html"), Path("docs/index.html"), Path("searchindex.js")}
    if not required <= {relative for _, relative, _ in files}:
        raise ValueError("Documentation output is missing its entry or search index")
    destination.mkdir(parents=True)
    try:
        for path, relative, _ in files:
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return {"files": len(files), "bytes": sum(size for _, _, size in files)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(stage(args.source, args.destination), sort_keys=True))


if __name__ == "__main__":
    main()
