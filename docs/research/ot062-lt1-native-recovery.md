# OT-062 native launch preparation and logical recovery evidence

PR #60 was critically reviewed and merged as
`bc323c91600d11f3d8046c24b2ca04e7e0c5a207`. Its tree equals reviewed/tested
`88332f61268b643185b7f86100c6542469e3df5e`: 2,029 local tests with 32 expected
skips, and all required jobs in hosted run 41533158512 passed. The additional
review exercised truncated journals, contradictory completion, request guards,
denial/control combinations and ownership failures. Those results belong to
the [Python host/removal increment](ot062-lt1-host-removal.md), not to native
Node/LT1 qualification.

[ADR 0100](../decisions/0100-lt1-prelaunch-and-recovery-evidence.md) defines this
read-only successor. Actual names, host/account/session/storage observations,
personal policy and private record hashes stay outside Git and public reports.
Configured Git commit attribution and ordinary GitHub account metadata remain
public. No production authority is added.
The [bounded result summary](../../experiments/lt1_diagnostic/native-recovery-review.json)
contains no private identifiers or private record hashes.

## Native preparation before startup

[native_preflight.py](../../experiments/lt1_diagnostic/native_preflight.py) accepts
bounded supplied bytes with externally retained spec/policy/input hashes. It pins
the already selected Node version, platform, archive and executable, fixed
integration worker, exact argument list and a three-key environment. No Node
flags, preload variables or inherited environment additions are accepted. Private
staging, packet and output roots must be separate and outside the checkout. These
are lexical checks; they do not inspect real paths, symlinks, modes, ACLs or staged
bytes.

The working directory is the checkout root used by the current shared supervisor.
The packet explicitly labels stdio defaults unqualified and resource policy as
deadline/grace only. It makes no claim about closed inherited descriptors, stdin,
rlimits, hard RSS, arbitrary cwd support or immutable bootstrap. Worker environment
checks happen after Node starts; a future outer launcher must enforce the reviewed
environment and command before that startup. This module does not implement or
dispatch that launcher.

Source/reader/collector maps, plan bytes, setup receipt and runtime/rights/security/
host review inputs are bound together. Opaque review or receipt bytes are not
parsed as actual approvals. Static map consistency is not complete dynamic module,
standard-library, dylib or OS closure, and cannot replace the existing setup and
worker verifiers.

The denominator keeps six actual native case families: bootstrap, modules,
addons, process ownership, file/network behavior and host mechanism. Invented or
Python fixture results cannot satisfy their `actual-native` origin. All review
gates and cases remain visible. Even a fully supplied packet can only be ready
for independent review; setup, execution, candidate-started, host-qualified and
new-authority flags always remain false. No candidate runtime is started by the
assessor or its tests.

## Private read-only host observations

[host_context.py](../../experiments/lt1_diagnostic/host_context.py) supplies a
separate explicit Python API, `capture()`, with no CLI or caller-selected command.
It requires canonical source and uses four fixed `/usr/sbin/sysctl` queries on
Darwin arm64: boot-session UUID, kernel UUID, OS build and kernel release. It binds
the tool and local static collector/Python identities before/after acquisition,
and records the observer PID, parent, process-start observation and POSIX session.
Each query has a two-second timeout; output is size-checked after acquisition.
This is not a hard memory/RSS sandbox or an immutable host attestation.

The raw result contains private identifiers and must be retained in an owner-only
location outside Git. Missing/failed/unsupported values are explicit unknowns;
the pure assessor checks their schema and declared observation age. Supplied
hashes/clock and observations require trusted review. They do not detect an
unreported reboot, altered input or new host after collection. A POSIX session is
not login/audit-session continuity, and this short-lived observer is not the
future launch owner. A later admitted launch needs a current observation and
actual native process/confinement evidence.

One explicit private capture on the declared Darwin arm64 host returned all four
queries with no unknown fields. Its static collector inventory covered 49 public
source files. A separately retained 68-file source/reader preparation packet was
structurally consistent and blocked: review gates are pending, no actual setup
receipt exists and all six native case families remain unrun. Its assessment
clock is the historical capture completion, not current launch readiness. The
raw identifiers/inputs are private; these availability observations supply no
native qualification.

## Logical recovery, timing and authority

[recovery_evidence.py](../../experiments/lt1_diagnostic/recovery_evidence.py) reads
only supplied metadata bytes. It opens/deletes no paths and resumes no operation.
The existing [retention planner](ot062-lt1-private-controls.md) still owns policy,
original origins, copy history and no-extension rules. A copy in quarantine
remains the same retention subject.

A separate approved scope must identify the supported ordinary application-access
and restore boundary, its context, all registered copies, and expected coverage
receipts for **live, quarantine, snapshot and backup** channels. The schema
explicitly excludes physical forensics and privileged memory. It is not a claim
that those paths are safe or impossible, nor a new requirement to introduce key
destruction. An actual scope outside this boundary needs its own reviewed design.

Current observations need exact copy/subject/channel/method/receipt bindings and
fresh coverage. Missing copies remain in the denominator; unknown coverage,
retained copies or a still-available recovery window prevent a complete result.
For live/quarantine the method is namespace readback; snapshots/backups require a
reviewed recovery inventory. An invented inventory proves only software behavior.
Hashes do not prove that a claimed inventory covers the actual storage.

The result separates these questions:

| Result | Meaning |
| --- | --- |
| `scoped_removal_evidence_complete` | All supplied requirements for the declared scope are satisfied; `kind` remains invented or observed |
| `registered_copy_timing` | Qualified timing of known registered copies only |
| `retention_timing` | `met`, `missed`, `pending` or `unknown`, accounting for incomplete coverage and recovery conflicts |
| `policy_conflicts` | Holds and recorded recovery beyond the deadline remain explicit |
| Authority/physical flags | Always false; the assessor grants no deletion, setup, execution or physical-erasure clearance |

Unknown original time can coexist with complete current scoped absence but cannot
prove deadline compliance. Observed late absence or presence at/after the deadline
can prove a missed deadline. A presence observation before the deadline cannot
prove continued presence after it. A recorded recovery window beyond a deadline
prevents a `met` conclusion even after that recovery window has passed; current
scoped absence may still be reported separately. Copy/evidence contradictions
cannot establish either timely removal or a timing violation.

## Remaining qualification and actual removal

The native acceptance cases and actual recovery coverage remain open. Existing
runtime security/restricted-use decisions, exact setup materialization and verified
receipts, immutable startup/source, native module/addon/file/network/IPC/process
behavior and C15–C18 require their own evidence. All production setup-request,
setup-receipt, execution and removal lists remain empty.

For actual removal, first inventory the original subject and every live/quarantine/
snapshot/backup copy under the privately reviewed scope. Preserve original clocks
and exact copy identities; unknown origins cannot be reset from current file
timestamps. Establish quiet ownership and what ordinary restore paths retain.
Then review a concrete removal mechanism for that storage and exact request under
the [manual procedure](ot062-lt1-private-controls.md#manual-removal-and-verification).
Only separately admitted removal may mutate those named objects. Keep a minimal
nonpayload receipt outside the target and observe all reviewed recovery channels
again. Unknown backup/snapshot state yields incomplete evidence; root/hosted tests
cannot close it. This increment removes no existing private dossier, audit,
snapshot, backup, container or key and changes no host settings.

A read-only application to the existing private decision-record pilot remains
incomplete: the original retention time is still unknown, copy/restore coverage
is incomplete, its registered copy is present and the recovery-scope proposal has
no approval. Its timing is unknown and all authority flags are false. The original
policy and predecessor/copy history were preserved; only a new metadata assessment
was retained privately. No personal payload was copied into the new evidence.

Pure tests use invented seven-day examples and mocked OS/process/tool reads.
Positive scoped-evidence examples are distinct from permission and physical
sanitization. Regression controls cover missing/stale/future evidence, context and
history mismatch, retained quarantine, unknown origins, late recovery and deadline
observation boundaries. Numerical behavior, historical guards/readers/baselines,
native locks and public task/SDK/GUI/CI scope remain unchanged.

The [owned pre-start/recovery successor](ot062-lt1-prestart-recovery-probe.md)
enforces the fixed launch boundary under the existing empty authorities and adds
separate read-only storage observations. This preparation record retains its
original source inventories and unqualified stdio conventions.
