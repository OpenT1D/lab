# OpenT1D

**An open, modular virtual laboratory for type 1 diabetes research.**

OpenT1D supplies research software for connecting researcher-chosen models,
controllers and appropriately authorized observations in reproducible experiments.
It preserves inputs, assumptions, failures and reconstructible reports. Public
examples use invented data; OpenT1D does not supply a patient dataset.

**Status:** working development software with bounded, internally verified
workflows. No version has been released. Independent researcher acceptance,
human-data evaluation and biological validity remain separate open questions.
There is no stable general model API or general multiscale digital twin.

The public source destination is [OpenT1D/lab](https://github.com/OpenT1D/lab).
The [public-source preparation guide](docs/public-source.md) explains the new
public Git root and the location-redacted historical records. Earlier development
commit IDs refer to private originals, not commits in that new history.

OpenT1D is intended for computational research. It must not be used to determine
insulin doses, operate medical devices or make clinical decisions.

## First research task

Start with **a synthetic paired meal-test analysis**: inspect whether a conclusion
about estimated insulin secretion changes when the analysis assumptions change.
This route uses the Python standard library for its calculation and needs no
physiological simulator, patient records or R installation.

With Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) and a local
checkout, run from the repository root:

```sh
uv sync --locked
uv run --locked python -m experiments.gui
```

Open the loopback URL printed by the server and choose **Explore paired meal
tests**. Prepare a supplied example, validate and freeze its plan, run the
analysis, then check and download its saved report. Stop the server with Ctrl+C.
Use the [paired-analysis guide](docs/observation-analysis.md) for exact steps,
interpretation and the complete CLI alternative. The root environment installs
repository tooling; it does not install a general simulation package.

A second [synthetic task](docs/mmtt-sampling.md) compares full and reduced meal-test
measurement schedules on the same analysis core. These examples demonstrate
software behavior under declared assumptions, not performance in people.
A separate internal [Windows 11 x64 installer candidate](docs/windows-installation.md)
bundles all current GUI routes and their runtimes. Its [OT-058 record](docs/research/ot058-installer-verification.md)
retains bounded clean-install, workflow, preservation and upgrade checks, plus
failed M4/campaign deadline cases and open maintenance/independent-user gates.
This integration is a new source identity; the previous J executable's checks do
not verify a newly built installer. Public installer distribution, signing and
its separate runtime/table-rights review remain open.

A bounded [unsigned Apple Silicon MMTT candidate](docs/mac-mmtt-candidate.md)
bundles its own interpreter for the two synthetic tasks. Its guide explains the
internal build, saved workspace and exact-artifact checks. Signing, notarisation,
clean-host and independent-user acceptance remain separate.

Historical native environments retain dependency advisories. The public snapshot
[limits automatic setup and CI](docs/publication-security.md) to the reviewed
source scope; old native guides are research records. The word `secure` in an
older task name does not establish that its dependencies are currently patched.

## Project status

| Available development workflow | Canonical guide and evidence |
| --- | --- |
| Paired meal-test sensitivity and reduced sampling, through CLI and GUI | [Paired analysis](docs/observation-analysis.md), [sampling](docs/mmtt-sampling.md), [internal verification](docs/research/ot056-researcher-pilot.md) |
| Synthetic glucose forecasts and frozen candidate comparisons | [M3 guide](docs/m3-researcher-forecast.md), [comparison](docs/m3-candidate-comparison.md), [GUI](docs/gui-m3.md) |
| Secretion sources and configurable synthetic glucose/insulin/C-peptide studies | [M4 guide](docs/m4-researcher-workflow.md), [maintained study](docs/m4-maintained-study.md) |
| Frozen synthetic prognostic models and reconstructible reports | [M5 guide](docs/m5-researcher-workflow.md), [combined M3–M5 verification](docs/research/researcher-workflow-integration.md) |
| Native engine references, controller experiments and numerical verification | [M1](docs/m1-tutorial.md), [M2](docs/m2-tutorial.md), [internal verification](docs/internal-verification.md) |
| Repeated campaigns, saved results and portable experiment archives | [Campaigns](docs/maintained-campaigns.md), [archive library](docs/gui-archive-library.md), [durable archives](docs/durable-experiment-archives.md) |

The [documentation start page](docs/index.md) maps all ten registered tasks to
their inputs, outputs and supported contracts. The [roadmap](ROADMAP.md) records
implementation status and outstanding evidence. A passing software check does
not establish biological validity, clinical benefit or independent usability.

## Product direction

The [public-development queue](ROADMAP.md#public-development-priorities) selects
agent-development improvements, reliability/CI work, documentation and a bounded
Mac application as the immediate delivery priorities. The shared-laboratory
increment develops common services around the working routes:
common project, execution and result services, compatible native adapters and a
question-led workbench. Its test is whether a second method and research task
reuse the infrastructure with less integration work. The
[delivery plan](ROADMAP.md#common-laboratory-delivery-plan) owns implementation
order; the [product requirements](docs/product-laboratory.md) define acceptance.
The internal [OT-059 contract packet](docs/shared-core-contracts.md) inventories
all ten routes and freezes two-route metadata/reader fixtures. Shared execution,
storage, SDK migration and distribution capabilities remain planned.

## What we are building

The long-term ambition connects glucose metabolism, insulin, beta-cell function,
immunity, devices and therapies through scientifically justified experiments.
Whole native engines and component replacement are both valid forms of
modularity. Preserve model ancestry, units, timing and process ownership;
[architecture](docs/architecture.md) and [decision records](docs/decisions/README.md)
explain the existing boundaries. Original controllers and mechanisms are optional
research, not prerequisites for using the tools.

## Explore the repository

- [Documentation](https://opent1d.github.io/lab/): choose a task, run it and interpret its limits.
- [Roadmap](ROADMAP.md): completed work, next packages and open evidence.
- [Development](docs/development.md): locked tooling, checks and documentation preview.
- [Research reports](docs/onderzoek/projectopzet.md): the research basis, translated into English.
- [Maintainer guide](docs/maintenance.md): publication checklist and first-release criteria.
- [Publication preparation](docs/research/publication-preparation.md): dated audit findings and unresolved actions.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SUPPORT.md](SUPPORT.md) and
[GOVERNANCE.md](GOVERNANCE.md). Contributions can improve software, documentation,
source assessment or reproduction. Keep personal health records, credentials and
restricted inputs out of issues, pull requests and logs. Confidential reports
follow [SECURITY.md](SECURITY.md) and the [code of conduct](CODE_OF_CONDUCT.md).

## License and citation

Original OpenT1D material is licensed under [Apache-2.0](LICENSE); see
[NOTICE](NOTICE) and [licensing](docs/licensing.md) for upstream boundaries.
Third-party dependencies retain their own terms. Cite the exact commit or actual
release using [CITATION.cff](CITATION.cff), and cite the upstream methods and data
used. No release version, release date or DOI has been assigned.
