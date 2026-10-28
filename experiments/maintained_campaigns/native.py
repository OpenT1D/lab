"""Fixed maintained-study admission and authoritative reader; no archived dispatch."""


def prepare(path):
    from experiments.m4.secure_study.common import prepare as native_prepare
    from experiments.m4.secure_study.common import require

    result = native_prepare(path)
    require(result["schema"] == "m4-secure-study-preparation/1", "Wrong native preparation")
    return result


def source_paths():
    from experiments.m4.secure_study.common import source_paths as native_sources

    return native_sources()


def reconstruct(path):
    from experiments.m4.secure_study.common import require
    from experiments.m4.secure_study.report import reconstruct as native_reconstruct

    result = native_reconstruct(path, allow_failed=True)
    require(result["schema"] == "m4-secure-study-report/1", "Wrong native report")
    return result
