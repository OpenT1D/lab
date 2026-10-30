"""Explicit maintained coordinator, preserving inherited process ownership."""

from experiments.m4.initial_load.run import run_study as inherited_run

from .adapter import activate
from .common import protocol


def run_study(config_path, output, reference_path=None):
    protocol()
    with activate():
        return inherited_run(config_path, output, reference_path)


execute = run_study
