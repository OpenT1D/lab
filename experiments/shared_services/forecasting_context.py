"""Current verified SDK identity and fixed M3 child entry; no scientific changes."""

import sys


def activate(bootstrap, artifact):
    from experiments.m3.comparison import common, study
    from experiments.m3.researcher import common as child

    source = artifact["source"]

    def source_version(_root):
        return dict(source)

    # These are current trusted imports, never archived module bindings. Only
    # administrative revision/dirty metadata changes; native source hashes stay
    # owned by the unchanged M3 provenance providers.
    common.source_version = child.source_version = source_version
    original_spawn = study.spawn

    def spawn(argv, **kwargs):
        prefix = [sys.executable, "-B", "-S", "-m", "experiments.m3.researcher", "run"]
        if argv[:6] != prefix:
            raise ValueError("Unexpected installed M3 child command")
        return original_spawn(
            [sys.executable, "-I", "-B", "-S", str(bootstrap), "--m3-child", *argv[5:]],
            **kwargs,
        )

    study.spawn = spawn
