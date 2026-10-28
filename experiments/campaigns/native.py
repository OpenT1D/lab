"""Only the explicitly selected standard-library M4 study boundary is callable."""


def prepare(path):
    from experiments.m4.initial_load.common import prepare as native_prepare

    return native_prepare(path)


def reconstruct(path):
    from experiments.m4.initial_load.report import reconstruct as native_reconstruct

    return native_reconstruct(path, allow_failed=True)
