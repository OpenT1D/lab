"""Live owned stage supervision with bounded nested cleanup."""

import signal
import threading
import time

from experiments.shared_services.execution import supervise as owned_supervise

from . import context
from .common import dump, require


class Control:
    def __init__(self):
        self._signal = None
        self.cancelled_at = None
        self.cancel = threading.Event()
        self.active = None

    def stop(self, signum, _frame=None):
        if self._signal is None:
            self._signal, self.cancelled_at = int(signum), time.monotonic()
        self.cancel.set()

    @property
    def signal(self):
        if self._signal is None and context.CANCELLED:
            self.stop(context.CANCELLED[0])
        return self._signal


def supervise(args, log_path, timeout, control, *, grace_seconds=10):
    if control.signal is not None:
        control.cancel.set()
    receipt = owned_supervise(
        args,
        log_path,
        timeout=timeout,
        cancel=control.cancel,
        grace=grace_seconds,
        header={"argv": args, "timeout_seconds": timeout},
    )
    receipt.update(timeout_seconds=timeout, grace_seconds=grace_seconds)
    dump(log_path.with_suffix(log_path.suffix + ".ownership.json"), receipt)
    require(receipt["remaining_owned_processes"] == [], "Stage process cleanup remains unresolved")
    if receipt["status"] == "interrupted":
        signals = receipt["received_signals"]
        control.stop(signals[0] if signals else signal.SIGTERM)
        return receipt["exit_code"], "GlobalInterruption"
    if receipt["error"] == "WorkerDeadline":
        return receipt["exit_code"], "WorkerDeadline"
    return receipt["exit_code"], None if receipt["status"] == "completed" else "WorkerExit"


def validate_receipt(log_path, argv, budget, exit_code, status, grace):
    from .common import read

    receipt = read(log_path.with_suffix(log_path.suffix + ".ownership.json"))
    require(status in {"completed", "failed", "interrupted"}, "Terminal stage evidence required")
    require(
        isinstance(receipt, dict)
        and receipt.get("argv") == argv
        and receipt.get("timeout_seconds") == budget
        and receipt.get("grace_seconds") == grace
        and receipt.get("exit_code") == exit_code
        and receipt.get("remaining_owned_processes") == []
        and isinstance(receipt.get("owned_processes"), list),
        "Stage command/budget/exit/ownership evidence differs",
    )
    require(
        receipt.get("status") == status
        and (status != "completed" or (exit_code == 0 and receipt.get("error") is None)),
        "Stage lifecycle status contradicts ledger",
    )
    return receipt
