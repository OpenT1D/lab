# OpenT1D documentation

OpenT1D supplies reproducible research tools for connecting researcher-owned
models, controllers and appropriately authorized observations. It does not
supply a patient dataset. Start with the task you want to perform below;
the [local entry](local-workflow-entry.md) discovers and checks supported routes.
Each linked guide owns its model contract and scientific interpretation.

For shared-service development, the [OT-059 contract packet](shared-core-contracts.md)
inventories all ten routes and their source/runtime/reader boundaries. It freezes
two-route fixtures before migration. The [minimal project services](shared-project-services.md)
add bounded storage, isolated execution and matching trusted readers; the installed
SDK and complete native route migration remain planned.

The independent public snapshot has a
[bounded installation and CI policy](publication-security.md). Historical native
locks retain advisories and are excluded from automatic public setup. The route
catalogue below describes implemented research software, not a promise that all
native environments are currently maintained for public installation.

## Start with one synthetic task

For a first run, follow the [paired meal-test example](observation-analysis.md#run-the-complete-synthetic-cli-example).
It needs the locked root tooling and uses a standard-library calculation, without
physiological simulators or patient data. The [local GUI](local-gui.md) exposes
the same task through **Explore paired meal tests**. Freeze, run, inspect and
reconstruct the supplied example before supplying your own synthetic inputs.
Then try [reduced measurement schedules](mmtt-sampling.md) on the same core.

**Current software:** P1/0.1–0.4 and the bounded M3 forecast, M4
secretion/glucose/C-peptide and M5 prognostic researcher workflows have
completed their internal technical verification. M0 native references,
M1/M2 experiments and IV-001 verification remain available. The
[M3/M4/M5 integration record](research/researcher-workflow-integration.md)
documents their combined local execution and reconstruction. The two synthetic
MMTT tasks below also have implemented CLI/GUI routes on one shared core and a
verified 22-case CLI/notebook chain. Their seven interface follow-ups are
integrated into main; the [OT-057 record](research/ot057-uiux-verification.md)
binds the internal browser checks and remaining Windows/human evidence steps.

**Separate acceptance and evidence steps remain open.** Independent human
M2 reproduction and intended-user P1 execution have not occurred. A human
reviewer conditionally cleared one exact internal P1 Git-bundle handoff;
that decision does not clear broader distribution or complete product
acceptance. M3 human predictive evaluation, M4 biological and
observation-based assessment, and M5 human prognosis and treatment evidence
retain their own requirements. These open steps do not block unrelated
internal development. There is no stable general model API, published
simulation release or established clinical benefit.

For Windows users, the [OT-058 installation candidate](windows-installation.md)
bundles all current GUI routes and their runtimes in one offline installer.
No GitHub checkout, WSL or separate Python setup is required by that flow.
The exact private J candidate has bounded clean-install and workflow checks. A
new installer built from the integrated source needs its own qualification;
public distribution and independent user acceptance remain open. The commands
below describe the developer checkout.

For Apple Silicon, the [unsigned internal MMTT candidate](mac-mmtt-candidate.md)
bundles its own interpreter for the two synthetic tasks. Its source and binary
checks are separate from signing, downloaded-copy and independent-user acceptance.

## Choose a researcher task

These ten bounded tasks use synthetic inputs and trusted local Python
sources. Their contracts deliberately support specific experiments. Follow
the chosen guide for its locked environments, supported inputs, fresh output
paths and evidence limits.

| Task | Required input | Result | Canonical execution guide |
| --- | --- | --- | --- |
| Connect a rate controller to an M1 experiment | Controller source and hash-bound declaration; causal observations and rate actions in U/min under the supported M1 contract | Four-condition study, actions, failures and reconstructible comparison report | [P1 external-controller workflow](p1-external-controller.md) |
| Compare a frozen CGM forecaster with persistence | Predictor source, frozen settings, declaration and synthetic study configuration; six available five-minute CGM values predict 30 minutes ahead | Participant/origin coverage, paired forecast errors and model-free report reconstruction | [M3 researcher forecast workflow](m3-researcher-forecast.md) |
| Compare multiple frozen CGM forecasters on one task | At least two predictor declarations and one shared synthetic roster, observation identity, origin schedule and worker budget | Common-support participant errors, all-candidate contrasts, full failure accounting and reconstructible reports | [M3 frozen-candidate comparison](m3-candidate-comparison.md) |
| Compare a causal secretion source in glucose feedback | Source, declaration and configuration under the one-state callback; the host owns basal replacement and portal/liver transfer | Candidate, constant-basal and reference glucose/insulin/C-peptide tracks, report and reconstructible figure | [M4 researcher workflow](m4-researcher-workflow.md) |
| Compare multiple frozen secretion sources on one task | Ordered source/declaration roster, common verified BC-008 reference and shared worker budgets | Joint glucose/insulin/C-peptide trajectories, descriptive contrasts, complete failure accounting and reconstructible report/figure | [M4 source comparison](m4-source-comparison.md) |
| Study secretion sources across selected initial gastric loads | Frozen sources and an ordered subset of 0, 15 and 30 gram initial solid loads under M4-STUDY/2 | Load-specific controls, numerical gates, full trajectories, retained failures and reconstructible descriptive comparison | [Configurable M4 study](m4-configurable-study.md) |
| Run the initial-load study with the maintained native environment | Frozen sources, selected 0/15/30 gram initial loads and the explicit successor configuration | Inherited numerical criteria, maintained runtime attestation and reconstructible native report | [Maintained M4 study](m4-maintained-study.md) and [local GUI](local-gui.md) |
| Compare a frozen prognostic model with a simple reference | Python model, frozen JSON state and declaration; projected landmark inputs on the fixed invented participant task | Repeat predictions, full-roster failure accounting, paired errors and reconstructible report | [M5 researcher workflow](m5-researcher-workflow.md) |
| Assess a paired meal-test secretion conclusion across assumptions | Declared synthetic metadata/CSV, actual 0–120-minute times and frozen fixed-kinetic variants/error settings | Paired whole-body secretion, conditional intervals, separate measured references, complete failure accounting and reconstruction | [Observation analysis CLI and GUI](observation-analysis.md) |
| Compare information loss from fewer MMTT measurement times | Synthetic paired observations, a sealed development-only import, prespecified raw subsets and shared settings | Full-reference deviations, paired directions, all failures and reconstructible native reports | [Sampling CLI and GUI](mmtt-sampling.md) |

For a fixed controller comparison, the [P1 first research workflow](p1-research-workflow.md)
requires no supplied controller. The [pinned upstream PID example](p1-upstream-pid-tutorial.md)
shows one existing source through the intake. The separate
[P1 intended-user exercise](p1-acceptance-exercise.md) uses a distinct
GlucoSim source and records independent interpretation and usability;
its [acceptance packet](research/p1-product-acceptance-review.md) owns the
conditional rights decision and the open product-acceptance record.

For the local research workflow, use [task-directed locked setup](task-setup.md),
[frozen local campaigns](local-campaigns.md) and the
[archive catalogue](experiment-catalogue.md). The historical campaign route
selects `m4-study`; the separate [maintained campaign CLI](maintained-campaigns.md)
selects `m4-study-secure`. Catalogue verification and metadata reading are
separate operations.

The [local GUI](local-gui.md) configures, checks, installs, runs, cancels
and reconstructs maintained M4 studies. Its [campaign view](gui-campaigns.md)
adds frozen matrices and explicit resume; the [archive library](gui-archive-library.md)
reads explicitly allowed external evidence and reconstructs fixed M3/M4/M5 native
reports. The [OT-043 record](research/archive-library-verification.md) binds
corrected recorded-claim diagnostics and the native report/download checks.
The [OT-044 record](research/m5-archive-library-verification.md) binds native
synthetic M5 reports, complete roster/attempt accounting and supplier declarations
in that same library. It adds report verification and downloads only.
The implemented [M3 GUI increment](gui-m3.md) adds preparation and explicit
execution of frozen synthetic forecasts/comparisons. Its
[verification record](research/m3-gui-verification.md) retains actual local
CLI/browser/relocation checks; independent researcher use remains open.
[Durable experiment archives](durable-experiment-archives.md) preserve maintained
M4 studies and campaigns outside disposable worktrees, with byte verification,
fresh restore, explicit compatible-reader reconstruction and GUI export/registration.
Their [acceptance record](research/durable-archive-verification.md) retains the
local internal scope. The [independent GUI exercise](gui-researcher-exercise.md)
is prepared; a researcher has not yet performed it.
The [test-session entry](gui-test-session.md) adds version-bound packet preparation,
explicit launch files and local observation export/restore, with an actual
Windows/WSL host check and human sessions still separate.

The [roadmap](../ROADMAP.md) is the canonical implementation plan. Its
[post-integration internal work packages](research/roadmap-history-2026-10-28.md#post-integration-internal-work-packages)
record the completed local entry and multiple-candidate comparison. The
[OT-029/030 verification record](research/ot029-ot030-verification.md) binds their
local acceptance and preserves separate external evidence requirements.

## Understand the platform and evidence

- **Direction and architecture:** [vision](vision.md),
  [architecture](architecture.md), [tool-first decision](decisions/0045-tool-first-research-platform.md)
  and [decision records](decisions/README.md).
- **Native experiments and verification:** [M0 reproduction](research/m0-reproduction.md),
  [M1 tutorial](m1-tutorial.md), [M1 evidence](research/m1-reproduction.md),
  [M2 tutorial](m2-tutorial.md), [M2 evidence](research/m2-reproduction.md)
  and [IV-001 internal verification](internal-verification.md).
- **Forecast routes and observation boundaries:** [Ohio preparation](m3-tutorial.md),
  [AZT1D preparation](m3-azt1d-tutorial.md), [frozen-model transfer](m3-external-tutorial.md),
  [PhysioCGM intake](physiocgm-intake-tutorial.md) and the separate
  [authorization-bound execution protocol](research/physiocgm-execution-protocol.md).
- **Biological references and synthetic coupling:** [standalone secretion](m4-beta-cell-tutorial.md),
  [forward C-peptide](research/m4-cpeptide-results.md), [paired kinetics](research/m4-paired-kinetics-results.md),
  [source audit](research/m4-source-audit-results.md), [glucose feedback](research/m4-feedback-results.md),
  [joint identifiability](research/m4-joint-identifiability-results.md) and
  [current measurement gaps](research/m4-measurement-readiness.md).
- **M5 source and study preparation:** [question protocol](research/m5-cell-therapy-protocol.md),
  [data contract](research/m5-cell-therapy-data.md), [CIT-07 crosswalk](research/m5-cit07-dictionary-crosswalk.md),
  [source-shaped rehearsal](m5-native-rehearsal.md), [synthetic prognosis](m5-synthetic-prognosis.md)
  and the [unsent scientific review packet](research/m5-domain-review-brief.md).
- **Preserved optional research:** the historical [C1 controller study](research/c1-controller-protocol.md),
  [negative-method review](research/c1-method-comparator-review.md) and
  [G2P2C technical readiness](research/c1-g2p2c-native-smoke-plan.md) retain
  their original results and open comparison gates. [LIT-001 findings](research/lit001-results.md)
  and the [LIT-002 absorption experiment](lit002-tutorial.md) preserve separate
  literature and synthetic component evidence.

## Contribute and maintain

Read [Contributing](../CONTRIBUTING.md) and the [development guide](development.md)
for local work. The [model guide](research/models.md), [data guide](research/data.md)
and [validation guide](research/validation.md) explain source assessment and
evidence. The [model-card](templates/model-card.md) and
[experiment-protocol](templates/experiment-protocol.md) templates document
assumptions; they are not executable interchange schemas.

[Governance](../GOVERNANCE.md) identifies responsibility.
[Licensing](licensing.md) and [citation](citation.md) explain reuse and credit;
the [maintenance guide](maintenance.md) covers repository setup, releases
and scientific corrections.

## Research reports

The public guides and these detailed research reports are in English. The reports
preserve their original dated findings; translation does not constitute a new audit:

- [T1D modeling landscape and project design](research/project-design.md):
  simulator candidates, data, standards and scientific evidence.
- [Repository foundation research](research/repository-foundation.md):
  lessons from existing projects and the repository decisions.
- [Repository foundation review](research/repository-foundation-review.md):
  review findings and the scope of the original foundation checks.
- [Product-direction research](research/product-direction.md):
  research jobs, existing tools and the shared laboratory direction.
- [Internal numerical verification](research/internal-verification-results.md):
  the historical IV-001 results, numerical sensitivity and recorded limitations.

The reports support the roadmap; they are not separate competing backlogs.
Optional usability-session cards are available in English and Dutch; the
experiment interface and public guides use English. The
[session guide](gui-test-session.md) explains how to select the card language.
