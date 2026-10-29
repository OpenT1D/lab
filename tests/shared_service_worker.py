"""Controlled failures for project-service tests; never a production dispatcher."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("m4-fail", "mmtt-stop", "tree", "crash"))
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.mode == "m4-fail":
        from experiments.m4.secure_study.run import run_study

        with patch(
            "experiments.m4.secure_study.adapter.supervise",
            side_effect=FileNotFoundError("controlled absent native stage"),
        ):
            run_study(args.config, args.output)
    elif args.mode == "mmtt-stop":
        from experiments.observation_analysis.run import run

        def wait(*_args):
            print("analysis-ready", flush=True)
            while True:
                time.sleep(0.02)

        with patch("experiments.observation_analysis.run.evaluate", side_effect=wait):
            run(args.config, args.output)
    else:
        args.output.mkdir()
        child = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-S",
                "-c",
                "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
            ],
            start_new_session=True,
        )
        (args.output / "child.pid").write_text(str(child.pid))
        (args.output / "partial.txt").write_bytes(b"unfinished evidence\x00\r\n")
        if args.mode == "crash":
            # Leave enough time for live ancestry observation before leader exit.
            time.sleep(0.4)
            os._exit(7)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(0.02)


if __name__ == "__main__":
    main()
