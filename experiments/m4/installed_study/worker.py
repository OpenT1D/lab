"""Explicit startup of the maintained interpreter; unchanged numerical functions."""

import argparse
import signal
from pathlib import Path

from experiments.platform_process import handled_signals

from .common import NATIVE_PROJECT, OBSERVER_PROJECT, dump, protocol, require
from .runtime import attest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--kind", choices=("baseline", "reference", "source", "observer"), required=True
    )
    parser.add_argument("--label", choices=("primary", "repeat"))
    parser.add_argument("--source")
    args = parser.parse_args()
    protocol()
    require(
        (args.kind in ("baseline", "reference")) == (args.source is None),
        "Source identity mismatch",
    )
    require((args.kind == "baseline") == (args.label is None), "Worker repeat label mismatch")
    interrupted = False

    def stop(_signum, _frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt("Maintained stage interrupted")

    for s in handled_signals():
        signal.signal(s, stop)
    if args.kind == "baseline":
        record = attest(NATIVE_PROJECT)
        dump(args.directory / "runtime.json", record)
        from .compat import native_imports

        with native_imports():
            from experiments.m4.feedback.worker import run

            run(args.directory)
        return
    from experiments.m4.initial_load import worker

    from .adapter import activate

    inherited_runtime = worker.runtime
    if args.kind == "observer":
        folder = args.directory / "children" / args.source / "observations" / args.label
    else:
        folder = (
            args.directory
            / ("reference" if args.kind == "reference" else "children/" + args.source)
            / args.label
        )

    def actual_runtime(project):
        record = attest(OBSERVER_PROJECT if args.kind == "observer" else NATIVE_PROJECT)
        dump(folder / "runtime.json", record)
        return inherited_runtime(project)

    from contextlib import nullcontext

    from .compat import native_imports

    with activate(), nullcontext() if args.kind == "observer" else native_imports():
        worker.runtime = actual_runtime
        try:
            if args.kind == "observer":
                worker.observation(args.directory, args.label, args.source)
            else:
                worker.numerical(args.directory, args.label, args.source)
        finally:
            worker.runtime = inherited_runtime


if __name__ == "__main__":
    main()
