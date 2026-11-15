"""Explicit invented UTC, isolated from actual calls and real elapsed deadlines.

Invented records use a fixed historical calendar in both parent and fixed child.
The scope never changes ``time.monotonic`` or the process-wide datetime module.
It grants no permission, and every actual boundary explicitly selects real UTC.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from functools import wraps

FIXTURE_UTC = datetime(2026, 11, 10, 14, tzinfo=UTC)
_INVENTED = ContextVar("simglucose_audit_invented_utc", default=False)


def _real_now():
    return datetime.now(UTC)


def now():
    return FIXTURE_UTC if _INVENTED.get() else _real_now()


@contextmanager
def use(invented):
    if type(invented) is not bool:
        raise ValueError("exact-invented-clock-mode")
    token = _INVENTED.set(invented)
    try:
        yield
    finally:
        _INVENTED.reset(token)


def _fixed(function, invented):
    @wraps(function)
    def scoped(*args, **kwargs):
        with use(invented):
            return function(*args, **kwargs)

    return scoped


def invented(function):
    return _fixed(function, True)


def actual(function):
    return _fixed(function, False)


def selected(position):
    """Scope an existing exact-bool ``fixture`` argument; no new caller selector."""
    if type(position) is not int or position < 0:
        raise ValueError("fixture-clock-argument-position")

    def decorate(function):
        @wraps(function)
        def scoped(*args, **kwargs):
            fixture = kwargs.get("fixture", args[position] if len(args) > position else False)
            with use(fixture):
                return function(*args, **kwargs)

        return scoped

    return decorate
