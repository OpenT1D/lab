# OT-064/073 diagnostic JSON AI control

## Outcome and evidence boundary

On 14 November 2026, a non-blind AI control of the fifteen synthetic diagnostic
JSON cases found no accounting discrepancy. All fifteen reports parsed, matched
the recorded AI extraction and matched the sender's literal accounting reference.
Two deliberately inconsistent copies were rejected by the local review checks.

The same AI assistant had previously prepared the cases and read their
implementation and reference. This was a re-reading with prior knowledge. Saving
the reading before the current reference-file comparison does not make it blind
or independent. The fifteen matches are fixed-packet accounting observations,
not an unassisted-comprehension score or a human-usability result.

The **human recipient exercise remains open and unrun**. No first human
interpretation answers, correctness assessment, assistance during case
interpretation or participant task duration were collected. Human onboarding
details and private observation forms are outside this public record.

The canonical [support exercise](../shared-project-services.md#synthetic-diagnostic-support-handoff)
owns preparation, recipient questions and the sender key. This report records
one completed AI control and leaves that human acceptance boundary intact.

## Candidate and method

| Item | Recorded identity or scope |
| --- | --- |
| Candidate source | `49a1c69584c12058ef7cbcc72efbd8fb1d8ee9df`, a clean temporary checkout |
| Diagnostic schema | `opent1d.project-diagnostics/1` |
| Exporter identity | `opent1d.export-project-diagnostics/1` |
| Project schema | `opent1d.project-store/1` |
| Material | Fifteen JSON reports, A–O; Dutch translation of the four canonical questions |
| Local host/interpreter | Darwin 25.5.0, arm64; CPython 3.12.13 |
| Check completion | 14 November 2026, 23:03:11 +01:00 (Europe/Amsterdam) |
| Retained recipient ZIP SHA-256 | `13b434a21a4441a4b59418b16ec09b0a314d8997b5a5874870abc0cab4e29609` |

The [frozen source and literal reference](https://github.com/OpenT1D/lab/blob/49a1c69584c12058ef7cbcc72efbd8fb1d8ee9df/tests/test_project_diagnostics.py)
define the cases used here. The ZIP identity covers the JSON files, translated
questions and archive metadata; it is not a canonical identifier for every
newly packaged copy.

The assistant recorded a per-case reading, then checked field sets, types,
versioned identities, nonnegative counts, unique task/outcome rows, task/root
totals and outcome/attempt totals for this fixed packet. It compared the
extracted values and categories with the received JSON and then with the sender
reference. These local review checks are specific to this exercise, not a new
general-purpose schema validator.

The stored packet hash, individual JSON hashes and ZIP contents matched the
preparation record. Two mutations were applied only to in-memory copies.
Afterwards, the original JSON, ZIP and human observation record were unchanged.
Relocation and source-project preservation are covered by the existing
[preparation and fixture checks](../shared-project-services.md#prepare-the-controlled-cases);
this AI control adds received-JSON interpretation and consistency observations.

## Per-case reading

Outcome notation is
`process_status / execution_status / completeness × count`.
Outcome-row order is not interpreted as chronological.

| Case | Reported task | Frozen plans | Attempts | Plans without attempts | Reported outcomes |
| --- | --- | --- | --- | --- | --- |
| A | No task row | 0 | 0 | Not exported | No outcome rows |
| B | `mmtt-sensitivity` | 1 | 1 | 0 | `completed / completed / complete × 1` |
| C | `mmtt-sensitivity` | 1 | 1 | 0 | `completed / completed / incomplete × 1` |
| D | `mmtt-sensitivity` | 1 | 1 | 0 | `failed / failed / incomplete × 1` |
| E | `mmtt-sensitivity` | 1 | 1 | 0 | `interrupted / interrupted / incomplete × 1` |
| F | `mmtt-sensitivity` | 1 | 1 | 0 | `unfinished / unknown / unknown × 1` |
| G | `mmtt-sensitivity` | 1 | 0 | 1 | No outcome rows |
| H | `mmtt-sensitivity` | 1 | 2 | 0 | `completed / completed / complete × 1`; `failed / failed / incomplete × 1` |
| I | `mmtt-sampling` | 1 | 1 | 0 | `completed / completed / complete × 1` |
| J | `mmtt-sampling` | 1 | 1 | 0 | `completed / completed / incomplete × 1` |
| K | `mmtt-sampling` | 1 | 1 | 0 | `failed / failed / incomplete × 1` |
| L | `mmtt-sampling` | 1 | 1 | 0 | `interrupted / interrupted / incomplete × 1` |
| M | `mmtt-sampling` | 1 | 1 | 0 | `unfinished / unknown / unknown × 1` |
| N | `mmtt-sampling` | 1 | 0 | 1 | No outcome rows |
| O | `mmtt-sampling` | 1 | 2 | 0 | `completed / completed / complete × 1`; `failed / failed / incomplete × 1` |

A has no task row, so no per-task `plans_without_attempts` field is exported.
Zero unattempted plans can be derived from its zero-plan total; that is distinct
from reading a present per-task field. A reports no frozen plans, not the absence
of GUI drafts or available task capabilities. A missing file would be an
unavailable observation rather than an empty report.

C/J demonstrate recorded process/execution completion with incomplete evidence.
D/K record failure; E/L record interruption. Their causes and independent
physical-process facts are not supplied by these summaries.

F/M report an unclosed attempt with unknown execution status and completeness.
The JSON does not establish current process liveness or workspace presence.
The sender's knowledge about a partial or absent workspace is additional
construction information.

G/N retain a frozen plan without an attempt. H/O retain a complete and a failed
attempt on their single plan. The JSON does not encode chronological order,
the latest-attempt identity or an explicit retry link. The sender key's
failed-then-successful-retry history cannot be recovered from outcome ordering.

## Accounting and counterexamples

| Aggregate | Observed count |
| --- | --- |
| JSON reports | 15 |
| Frozen plans | 14 |
| Attempts | 14 |
| Plans without attempts | 2 |
| `completed / completed / complete` | 4 |
| `completed / completed / incomplete` | 2 |
| `failed / failed / incomplete` | 4 |
| `interrupted / interrupted / incomplete` | 2 |
| `unfinished / unknown / unknown` | 2 |

Outcome counts sum to fourteen attempts. Equal aggregate plan and attempt
counts do not imply one attempt per plan: G/N have no attempt, while H/O each
have two. All seven paired cases B/I through H/O have equal accounting except
for the task name.

| Deliberate in-memory change | Observed rejection |
| --- | --- |
| Remove H's failed outcome while retaining two attempts | Outcome counts no longer equal attempts |
| Change B's root plan count to two while its task row still reports one | Root plan total differs from task totals |

Both altered copies remained syntactically valid JSON. Their rejection checks
the sensitivity of the local accounting review; it does not add malformed-project
export/refusal coverage. Neither original reports nor frozen baselines were
changed.

The received JSON uses the fixed allowlisted fields and carries no raw inputs,
local paths, logs, free-text errors or scientific report values. That observation
is limited to these fifteen files.

## Retained case identities and reproduction

The following SHA-256 values identify the exact JSON bytes read. The source
revision above and the canonical preparation recipe can regenerate the case
data and accounting for comparison with these identities. A freshly packaged
ZIP may have a different hash because packaging metadata or question material
can differ.

| Case | JSON SHA-256 |
| --- | --- |
| A | `bbb757900fbb85315931ce7baefff0780b99b641bcd94675ff25420fd3669479` |
| B | `354525d54df934bc467abd978526f21580e9b92328a9ef50e1cd4620b112997f` |
| C | `3dda0f825163a3a8c815c2c0ba67819a0bae3f6544e479f1569610cab6b1c227` |
| D | `daca7bfe6136872edaa451ef2e1b49631e40a4b4724d15b4ddb6b9c4c89677f7` |
| E | `dbc088e775b6344d58bdbf9d30e71878babe7cf970797be9b97095f9a74dfba0` |
| F | `7bc3cb320067e20009995ca4e4a04f1b22c9822569e502e8998e72e041e3cea8` |
| G | `f1cc855bf2e19d9222d9490401e08625d2d7afbfc95d420af7ac75da1b9e726c` |
| H | `c9c6d16dbe97ecd052c9bee56da71d37b331bc83330e76ef09544639075982ea` |
| I | `b2fd1d849d2114b13d2f01a3d0134865af3c9059050c68167f793ab6bc819774` |
| J | `b247fc1e05eb73c0c97cbc21967768cd98df09b879325575302aee81c0e18c42` |
| K | `a25ab909ce56a59ee1ff3e011301b653070a000efe067d095e685bc3a6baec28` |
| L | `2109bebd76ed199ae8ed444c4d1573773add728f8b0ebfb425325c1538f52f9a` |
| M | `0aeab8e2882537defdb807e8c9b451b34d2cddc7e293174a384908f5fd3423ee` |
| N | `524f575523e116627739e4e033e6ca44c912aa7dd0c295f27d8c625c3fe67abb` |
| O | `429e9e40c5164f9453393d4db52f0171917eacb89df03842356539eae02fb414` |

The original local evidence consists of `ai-reading.json`,
`check-results.json`, `check_ai_reading.py` and the preparation inventory.
Those local records remain separate from private human observation material.
This documentation preserves the candidate, case identities, method, findings
and counterexamples; it does not publish raw human forms or the local checker
as a maintained product API.

This is local AI/control evidence. Existing candidate
[main CI](https://github.com/OpenT1D/lab/actions/runs/43639287226) supplies separate
implementation checks on the pinned source. Required CI for the documentation
revision is recorded in its own PR; the earlier run does not qualify later edits.

## Limitations and next observation

The fixed packet covers two synthetic MMTT tasks in separate zero/one-task
projects. Mixed-task projects, invalid/refused source exports and wider
host/application/reader compatibility are outside this AI control.

Declared schema/exporter identities do not prove host or application
compatibility. Local hash agreement establishes internal packet integrity,
not a signed producer/source attestation. These status/count summaries do not
contain the numerical analysis needed to reconstruct a scientific report or
assess biological validity.

No software defect was detected in this bounded control. Possible
reader-confusion points are process completion versus complete evidence,
unfinished versus currently running, and aggregate outcomes versus the latest
attempt. These are hypotheses for later observation, not observed human errors.

The human recipient exercise remains **open**. Its first answers, assessment,
case assistance and participant times remain unfilled. If that exercise resumes,
record actual prior exposure to this case-level AI report and the published key
before presenting questions. Preserve the earlier exposure record, first
answers, assistance and later corrections separately. This AI control closes
neither independent user acceptance nor broader OT-064/073 qualification.
