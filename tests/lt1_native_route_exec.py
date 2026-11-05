"""Fixed invented counterpart of the same exec implementation, not native admission."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.lt1_diagnostic.native_route_exec import execute

execute(invented=True)
