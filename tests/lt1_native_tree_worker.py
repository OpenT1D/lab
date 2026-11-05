"""Fixed fresh-invented-tree worker; never used by production remove()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.lt1_diagnostic.native_tree_removal_worker import execute  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(execute(invented=True))
