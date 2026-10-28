"""Admit this installed source/runtime before opening the bounded desktop profile."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.desktop.__main__ import main  # noqa: E402
from experiments.desktop.provenance import source_version  # noqa: E402
from experiments.desktop.runtime import packaged_capabilities, verify_packaged_project  # noqa: E402

if packaged_capabilities(ROOT) is None or source_version(ROOT)["dirty"]:
    raise ValueError("This Mac application's installed source identity changed")
verify_packaged_project(".", ROOT)
raise SystemExit(main())
