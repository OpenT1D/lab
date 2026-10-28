# C1 patched PyTorch runtime

The two isolated C1 policy and training environments now select `torch==2.13.0`
with Python 3.12, NumPy 1.26.4 and the existing simulation ancestry. This is a
new runtime identity. The original C1 training, trained-actor intake and native
smoke records describe Torch 2.2.0 and remain historical evidence.

## Security selection and checkpoint boundary

The [upstream critical advisory](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)
reports that `weights_only=True` could still execute code before the 2.6.0
patch. Checking a checkpoint's SHA-256 did not repair that loader. The dated
alert snapshot also includes a
[TorchScript issue through 2.12.1](https://github.com/advisories/GHSA-rrmf-rvhw-rf47).
The selected [2.13.0 release](https://github.com/pytorch/pytorch/releases/tag/v2.13.0)
is outside every affected Torch range in that snapshot. Its
[publisher distribution](https://pypi.org/project/torch/2.13.0/) includes a
CPython 3.12 macOS 14+ arm64 wheel. This scope does not establish that unknown
vulnerabilities are absent.

The [frozen protocol](../../experiments/c1/g2p2c-security-runtime.json) binds
the candidate, old lock/checkpoint identities and acceptance rules before
native execution. The [shared loader](../../experiments/c1/g2p2c_checkpoint.py)
requires the exact patched runtime and verifies declared bytes before loading.
It accepts a stored ZIP state dictionary within 64 MiB and 1,024 entries,
refuses legacy pickle/TAR and TorchScript containers, and uses only
`weights_only=True`. There is no unsafe retry or user-defined class allowlist.
PyTorch 2.13's fixed import/inference defaults are distinguished by object
identity from added user globals. The resulting payload must have exact actor keys,
shapes and dtypes, with plain dense finite CPU `float32` tensors; strict
`load_state_dict` follows.

These checks provide a bounded format and identity boundary for trusted,
declared local checkpoints. PyTorch deserialization is not an adversarial
sandbox. They do not qualify arbitrary downloaded model files.

## Separate verification route

Install both new locks explicitly:

```sh
uv sync --locked --project experiments/c1/g2p2c_policy_source
uv sync --locked --project experiments/c1/g2p2c_training_source
```

Use a clean G2P2C checkout at
`37f7b7e161e9c1e7b702c8eebdc5cc7eb4f81d70` and an unchanged recorded OpenT1D
checkout whose ignored `results/` store contains the two original declared
training checkpoints and smoke artifacts:

```sh
experiments/c1/g2p2c_training_source/.venv/bin/python -B -m \
  experiments.c1.g2p2c_security_runtime run \
  --source /path/to/pinned/G2P2C \
  --historical-root /path/to/recorded/OpenT1D \
  --output results/c1-g2p2c-security-runtime
```

The runner checks the historical attempt, plan, summary, checkpoint and source
preflight against their original hashes and lock identity. It freezes current
implementation and runtime hashes separately. Neither original result store
nor historical training freeze is rewritten. The old training launcher refuses
new training under the updated lock; a future training study needs its own
freeze.

Each selected trained actor must retain its tensor digest, match all seven
source/intake outputs on 16 invented states, repeat 741 invented causal commands
after reset and preserve the caller's RNG. Two known condition-D native cases
then run in fresh supervised workers, followed by independent process repeats.
Each case must complete 960 three-minute intervals, preserve ten exact
profile-basal commands during missing CGM and replay all saved commands using
released observations. Actions remain finite, bounded and zero-bolus.

Every worker has a 600-second deadline and bounded process-group cleanup.
All four planned attempts remain in the archive, including failed or
unattempted ones. The report describes changed old/new trace fields and maximum
absolute differences without imposing or assuming cross-version equality.
New-runtime initial snapshots, traces and case reports must repeat byte exactly.

Reconstruct saved accounting and descriptive differences without Torch,
NumPy, actor imports or simulation:

```sh
python3.12 -B -S -m experiments.c1.g2p2c_security_runtime reconstruct \
  --archive results/c1-g2p2c-security-runtime \
  --output results/c1-g2p2c-security-runtime-reconstructed.json
```

The reader checks the complete archive inventory, frozen protocol, roster,
recorded native boundary and saved report. It verifies recorded execution
evidence; it does not independently rerun source actor inference.

## Verification scope

The [execution receipt](../../experiments/c1/g2p2c-security-verification.json)
records achieved checks, commands, hashes and any old/new numerical differences.
At clean revision `11a2213b6517ab36c62bbad7edc93b24fe8a2cb4`, both profiles
and all four native attempts passed. Every new-runtime initial snapshot, trace
and case report matched its fresh-process repeat byte exactly. Stdlib-only
reconstruction reproduced the aggregate report bytes; its SHA-256 is
`950dc1c4500eaf7e4b1ff0f910584b69e7749c6b97a1163cf0b8875176f38033`.
The checkpoint suite passed 13 tests in each locked runtime; seven new stdlib
tests plus eight inherited training/intake/smoke tests passed separately.
The process deadline test reached a resistant worker and verified that worker
and group were gone after cleanup. The policy source probe matched state and
sampled actions on 16 synthetic frames and repeated its report byte exactly.

Both old/new initial snapshots match. Cross-version trace equality is false:
adult#001 changes 400 basal commands, 354 glucose values, 354 raw CGM values,
353 released CGM values and one delivered-rate value. Their maximum absolute
differences are respectively `2.8101777344e-7 U/min`, `1.9522896132e-4 mg/dL`,
`1.9522866950e-4 mg/dL`, `1.9477320419e-4 mg/dL` and `8.3333333333e-6 U/min`.
Adult#002 changes 143 basal commands by at most `1.0539865256e-7 U/min`;
all other saved trace fields match. These are descriptive runtime differences,
not an efficacy analysis or a newly chosen numerical acceptance tolerance.

An earlier implementation at `ca05dd6` rejected Torch's own lazily registered
inference classes before simulation. All four failed attempts and their
reconstructible archive remain preserved. The correction distinguishes exact
pinned runtime objects from user additions; no version, checkpoint or numerical
criterion was changed.

Native execution is separate from the repository tooling checks. Current
verification targets CPU on macOS arm64; universal lock resolution alone is
not execution evidence for Linux, Windows, CUDA or other accelerators.

Full training is not repeated. The old method findings, scheduling deviation,
unqualified comparator status and absence of an efficacy comparison remain
unchanged. The separate [C1 readiness decision](../decisions/0044-c1-g2p2c-native-readiness.md)
retains that scientific boundary.
