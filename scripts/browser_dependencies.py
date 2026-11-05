"""Configure bounded, authenticated Ubuntu acquisition on ephemeral browser CI."""

import os
import re
import stat
from pathlib import Path

APT_NETWORK = """Acquire::http::Timeout "30";
Acquire::https::Timeout "30";
Acquire::Retries "1";
APT::Update::Error-Mode "any";
"""


def official_mirror(text):
    """Replace only an exact Ubuntu Azure URI, retaining every source option."""
    pattern = r"(?<!\S)https?://azure\.archive\.ubuntu\.com/ubuntu/?(?=\s|$)"
    return "".join(
        line
        if line.lstrip().startswith("#")
        else re.sub(pattern, "https://archive.ubuntu.com/ubuntu", line)
        for line in text.splitlines(keepends=True)
    )


def configure(mirrors, config):
    if not stat.S_ISREG(mirrors.lstat().st_mode):
        raise ValueError("Expected a regular hosted Ubuntu mirror list")
    original = mirrors.read_text()
    selected = official_mirror(original)
    # Never overwrite a caller's configuration, follow a link or relax signing.
    with config.open("x") as stream:
        stream.write(APT_NETWORK)
    mirrors.write_text(selected)
    print(
        "Ubuntu Azure mirror replaced" if original != selected else "No Azure Ubuntu mirror present"
    )
    print("APT acquisition: 30s connection/data timeout, one transport retry; update errors fail")


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        raise ValueError("This configuration is only for an ephemeral hosted browser runner")
    configure(
        Path("/etc/apt/apt-mirrors.txt"),
        Path("/etc/apt/apt.conf.d/80opent1d-browser-network"),
    )


if __name__ == "__main__":
    main()
