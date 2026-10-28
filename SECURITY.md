# Security policy

OpenT1D has implemented checkout-based research workflows, a local browser interface and repository tooling. There are no supported versioned releases or production services. Security fixes are developed for the main branch; a version-support policy will accompany the first software release. The [publication preparation record](docs/research/publication-preparation.md) distinguishes current dependency findings from release readiness.

## Execution and dependency scope

The local GUI binds to loopback; it is not a hosted multi-user service. Supplied
Python methods execute with the local user's permissions and are trusted code,
not sandboxed uploads. Historical numerical environments retain open dependency
advisories and must be assessed under their recorded scope. The
[publication inventory](docs/research/publication-preparation.md#dependency-and-hosted-ci-findings)
records the targeted root-tooling fixes separately from those remaining alerts.
The [source-publication security boundary](docs/publication-security.md) inventories
all 50 distinct advisories and describes enforced installation/CI exclusions.
Historical native locks remain vulnerable; no alert is dismissed by this policy.

## Reporting a vulnerability

Send confidential vulnerability reports to [Matthiasvdgalien97@gmail.com](mailto:Matthiasvdgalien97@gmail.com). The maintainer confirmed mailbox ownership and message receipt on 25 October 2026. Reports are handled by the project maintainer. Do not publish exploit details, credentials or personal data in an issue. The maintainer must complete the [publication checklist](docs/maintenance.md#before-opening-the-project-to-public-contributions) before accepting public contributions.

If the repository's Security tab offers **Report a vulnerability**, that GitHub feature can be used for a private report. Its availability must be checked; this document does not enable it.

A useful report identifies the affected commit or dependency, the impact and the minimum steps needed to reproduce the problem without exposing other people's data. Where possible, suggest a mitigation. There is no bounty program or guaranteed response time at this stage.

## Security and scientific correctness

Examples of security problems include unsafe execution of untrusted model files, credential exposure and vulnerabilities in build or data-processing tooling.

A reproducible numerical error, incorrect unit conversion or unsupported scientific claim normally belongs in an issue using the scientific-correctness category. If it also exposes confidential information or has an exploitable security impact, use private reporting first.

## Handling and disclosure

The maintainer assesses impact, coordinates a fix and agrees on disclosure with the reporter where possible. A confirmed issue affecting a release should receive a documented correction and, where appropriate, an advisory. Preserve enough information to identify affected versions while excluding sensitive details.

For a committed credential, revoke or rotate it promptly; deleting the latest file alone does not invalidate the credential. Handle any affected data according to the applicable data agreement and incident process.
