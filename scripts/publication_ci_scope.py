"""Keep historical native CI an explicit private-archive operation."""

import os
from pathlib import Path


def native_enabled(root, *, private_repository, historical_requested):
    return (
        private_repository
        and historical_requested
        and not (root / "publication-snapshot.json").exists()
    )


if __name__ == "__main__":
    enabled = native_enabled(
        Path(__file__).resolve().parents[1],
        private_repository=os.environ.get("PRIVATE_REPOSITORY") == "true",
        historical_requested=os.environ.get("HISTORICAL_REQUESTED") == "true",
    )
    print("native_enabled=" + str(enabled).lower())
