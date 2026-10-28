"""Two observed legacy import APIs, backed by the standard library.

This is a process-local compatibility boundary for the pinned simglucose/gym
sources, not a general replacement for setuptools or pkg_resources.
"""

import importlib.metadata
import sys
from contextlib import contextmanager
from pathlib import PurePosixPath
from types import ModuleType

from .common import require


def resource_filename(package, resource):
    require(
        package == "simglucose" and isinstance(resource, str),
        "Only pinned simglucose resources are supported",
    )
    path = PurePosixPath(resource)
    require(
        not path.is_absolute() and ".." not in path.parts and str(path) == resource,
        "Unsafe legacy resource path",
    )
    distribution = importlib.metadata.distribution("simglucose")
    target = distribution.locate_file("simglucose")
    for part in path.parts:
        target /= part
        require(not target.is_symlink(), "Legacy resource cannot contain symlink")
    require(target.is_file(), "Missing installed legacy resource")
    return str(target)


class EntryPoint:
    def __init__(self, item):
        self.item = item

    @classmethod
    def parse(cls, value):
        name, separator, target = value.partition("=")
        require(separator == "=" and name.strip() and target.strip(), "Invalid entry point")
        return cls(importlib.metadata.EntryPoint(name.strip(), target.strip(), "legacy-gym"))

    def load(self, require_dependencies=True):
        require(require_dependencies is False, "Only observed gym load(False) is supported")
        return self.item.load()


@contextmanager
def native_imports():
    require("pkg_resources" not in sys.modules, "Unexpected legacy dependency already loaded")
    module = ModuleType("pkg_resources", __doc__)
    module.resource_filename = resource_filename
    module.EntryPoint = EntryPoint
    sys.modules["pkg_resources"] = module
    try:
        yield
    finally:
        require(sys.modules.get("pkg_resources") is module, "Legacy import binding changed")
        del sys.modules["pkg_resources"]
