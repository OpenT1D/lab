"""Only the observer's own fresh invented Popen uses this fixed coordinator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.lt1_diagnostic.native_route_coordinator import main

main(invented=True)
