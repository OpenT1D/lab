# 0079 — Direct current CPython for Windows standard-library workers

Date: 28 October 2026

Status: accepted; exact final Windows execution remains an acceptance requirement.

## Context

A [Windows hosted probe](https://github.com/OpenT1D/lab/actions/runs/40769727642)
delayed Job assignment until the actual worker had
published its identity while START remained closed. The current venv launcher
and actual worker had different PIDs; assigning the launcher did not include
the already-created worker. No scientific module work ran, and private-pipe EOF
ended the fixture. A gated module alone therefore cannot prove Job membership.
Separate strict completion probes also observed an associated nonleader with
exit code 109 and a nonsignaled process handle. Its executable was not identified;
that observation does not authorize dropping it from the ownership inventory.

## Decision

For the two Windows source MMTT tasks, require the **current** interpreter to be
CPython 3.12 independently of the declared root environment's installed metadata.
Retain that metadata, uv, frozen source/runtime and input checks. Explicitly use
the current interpreter with `-S` for their workflow dispatch and reconstruction.
The calculations already require only the standard library. Other tasks, POSIX
selection and installed Windows-v1 project routing retain their previous commands.

For a Windows module launch with explicit `-S`, substitute only when the requested
executable has the current CPython 3.12 executable's absolute path context and
is the same existing file. Hardlinked launchers in another venv retain that
venv's requested path and configuration. Use
its absolute, regular `sys._base_executable`, resolved inside `sys.base_prefix`.
Reject a different base with virtual-environment or `._pth` overrides. A current
direct executable retains its exact command, including packaged path configuration.
Foreign interpreters and site-enabled launches retain their requested interpreter;
there is no PATH search or automatic substitution of another runtime.

CPython's [venv implementation](https://github.com/python/cpython/blob/v3.12.13/Lib/venv/__init__.py#L146-L155)
uses this base executable, and its [path initialization](https://github.com/python/cpython/blob/v3.12.13/Modules/getpath.py#L294-L362)
binds it to the current installation. Python 3.12 [`-S`](https://docs.python.org/3.12/using/cmdline.html#cmdoption-S)
excludes site initialization. For the admitted current venv this selects the same
actual CPython binary and standard library that its redirector would start,
without an intermediate process creating children before assignment.

Keep the private START/CANCEL pipe, retained Popen handle and live Job as the
only control authorities. Preserve strict descendant and zero-grace cleanup
assertions. Record requested argv, actual bootstrap argv and selection reason in
an optional GUI journal field; older journals remain readable. This information
does not change the normal user flow or claim that the venv launcher was executed.

## Consequences and acceptance

The changed helper remains in the existing source-identity inventories. Plans
frozen against its prior bytes require a new explicit freeze. There is no change
to native locks, scientific calculations, tolerances or historical evidence.

Require the actual before-START worker to be a member of the assigned Job, all
five immediate cleanup controls and all six Windows HTTP task repetitions to
pass without retries, skips or forced cleanup. Local mocked guards establish
selection and rejection behavior, not Windows membership. The integration owner
also checks the final source revision and separate hosted families.

This convention does not qualify foreign/site-enabled Windows environments,
broaden public native installation or identify the earlier nonleader. Revisit
it for a new Python minor version, a different distribution layout or a task
requiring site-packages; those need separately proven launch ownership.
