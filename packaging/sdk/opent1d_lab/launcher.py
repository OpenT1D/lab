"""Entry for the installed isolated POSIX shell launcher."""

import json
import sys
import tempfile
from pathlib import Path

package = Path(__file__).absolute().parent
# Run the same verified bootstrap for validation before loading the facade.
# The bootstrap's normal request is a passive installation-info operation.
if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-I", "-B", "-S", str(package / "_bootstrap.py")],
        input=json.dumps({"action": "installation"}).encode(),
        capture_output=True,
    )
    if result.returncode:
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        raise SystemExit(result.returncode)
    # -B prevents cache writes, but does not prevent reading an old or forged
    # valid-header .pyc. A fresh private prefix makes all facade imports read
    # their inventoried source while leaving normal API caches untouched.
    with tempfile.TemporaryDirectory(prefix="opent1d-sdk-pycache-") as cache:
        sys.pycache_prefix = cache
        sys.path.insert(0, str(package.parent))
        from opent1d_lab.cli import main

        raise SystemExit(main())
