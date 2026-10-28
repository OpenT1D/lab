"""Run inherited numerical checks inside the maintained explicit startup context."""

import unittest

from .adapter import activate
from .common import NATIVE_PROJECT, protocol
from .compat import native_imports
from .runtime import attest, validate


def main():
    validate(attest(NATIVE_PROJECT), NATIVE_PROJECT, protocol())
    with activate(), native_imports():
        from experiments.m4.causal_secretion import test_numerical as causal
        from experiments.m4.feedback import test_numerical as feedback
        from experiments.m4.initial_load import test_numerical as study

        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromModule(module)
            for module in (feedback, causal, study)
        )
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
