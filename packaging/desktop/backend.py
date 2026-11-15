"""Start only the bundled installed SDK; host Python packages stay excluded."""

import sys
import tempfile
from pathlib import Path

backend = Path(__file__).resolve().parent
sys.path.insert(0, str(backend / "lib/python3.12/site-packages"))

# -B prevents writes, not reads of a forged valid-header .pyc. Match the
# existing SDK launcher's fresh-prefix rule before importing the facade.
with tempfile.TemporaryDirectory(prefix="opent1d-desktop-pycache-") as cache:
    sys.pycache_prefix = cache
    from opent1d_lab._desktop import main

    main()
