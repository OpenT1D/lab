# BC-006: initialization, basal secretion and scale audit

The [prespecified source audit](m4-source-audit-protocol.md) narrows three BC-001 gaps. The author's whole-pancreas convention and separate basal term are identifiable. A pre-bolus granule-pool calculation explains the explicit 92.7-microgram initialization to its reported decimal precision. **This is an internally checked explanation, not an author-confirmed correction or biological review.** No existing secretion or kinetic implementation is changed.

The isolated worktree is `/private/tmp/opent1d-beta-cell-reference`, branch `codex/beta-cell-reference`, base `bb4ac19`. The [source record](../../experiments/m4/source_audit/sources.json) supplies URLs, hashes, locators and access limits; the [execution record](../../experiments/m4/source_audit/execution.json) records actual numerical checks. The previous BC-001 through BC-005 results remain historical.

## Primary-source findings

The [paper](https://doi.org/10.1098/rsfs.2012.0085), final equations 3.2–3.7 and 4.10–4.13, and the [preprint](https://www.dei.unipd.it/~pedersen/InterfaceFocus_preprint.pdf), PDF pages 5–9, distinguish docked, primed and fused pools. Both inspected versions print `p_minus+f` in the initializer. The reduced output omits the separately specified basal term. The change of variable defines Y as a glucose-dependent coefficient times D.

The [author file](https://www.dei.unipd.it/~pedersen/secr_model_IVGTT_new.ode), lines 3, 34–40, 67–72 and 94–95, instructs basal pre-equilibration, declares a docked seed of 311 micrograms and X(0)=92.7, and codes basal secretion 0.58 microgram/min. Its C-peptide block specifies a pancreas/4-litre conversion, rounded to 43, plus an additional multiplier 0.5. This documents implementation choices; it does not establish physiological calibration for T1D.

Fresh author-file and preprint downloads match the BC-001 hashes. The saved published equation image was visually checked; fresh PMC/publisher retrieval was blocked or failed. No correction was found in the inspected author entry, targeted searches or Crossref metadata; that is not proof none exists. The named glucose-file endpoint again returned HTTP 404 to a header-only request. No participant data or reusable source-code license was obtained.

## Mathematical reconciliation

The following is OpenT1D's deduction, not a substituted publication equation. At subthreshold basal glucose, fusion is inactive. Setting the two basal pool derivatives to zero gives

```text
R_b = p_plus * D_b / p_minus
D_b = M(G_b) / r
```

An ideal instantaneous threshold activation recruits `H_pre = Phi(G_max)*R_b` from that pre-existing pool. In contrast, the printed initializer equals `H_qss = p_plus*Phi(G_max)*D_b/(p_minus+f)`, the active quasi-steady pool. At identical D and activation fraction their ratio is `(p_minus+f)/p_minus = 621`. A small active pool maintained during rapid turnover is not the initial stored inventory.

| Convention | D (microgram) | Pre-bolus recruited pool (microgram) | Printed active-pool formula (microgram) |
| --- | --- | --- | --- |
| BC-001 caption parameters, basal glucose 5 mmol/L | 322.058824 | 96.038982 | 0.154652 |
| Author seed, exact threshold conversion 130/18 mmol/L | 311 | 92.739536 | 0.149339 |
| Continuum equilibrium at author basal glucose 4.9127222 mmol/L | 312.607134 | 93.218780 | 0.150111 |

The seed-based candidate rounds to 92.7, without fitting any parameter. However, 311 is a seed, not a recovered saved post-warmup state. Its continuum basal residual is 0.128571 microgram/min. The source warmup/reinitialization sequence, finite threshold discretization and cohort stimulus have not been reproduced. The file also contains a derived `!X0` expression using `f`, whereas its fusion-rate parameter is `fplus`; that expression is not the explicit X(0) assignment. [XPPAUT syntax](https://sites.pitt.edu/~phase/bard/bardware/xpp/help/xppodes.html) identifies the exclamation form as a derived parameter. We do not infer its runtime meaning or silently substitute names.

Finite fusion adds another distinction. In an isolated initial pool with no replenishment, H decays at `p_minus+f`, feeds F at rate f and returns unprimed inventory separately. The eventual released fraction is `f/(p_minus+f) = 620/621`; F initially equals zero and fills over finite time. Replacing this process with an instantaneous X jump is an approximation, not a consequence of changing one denominator. The audit verifies this isolated diagnostic analytically and numerically; it does not implement the complete granule model.

## Quantified consequences and remaining reduction gap

With the same BC-001 synthetic input, coefficients and Y(0)=0, the difference between two initial X values follows exactly `delta X(t)=delta X(0)*exp(-m*t)`. Relative to literal BC-001 initialization, using the author's explicit X value changes initial secretion by 57.378116 microgram/min and adds 92.545348 micrograms to the analytical secretion integral over 100 minutes. This is an initialization contrast, not an empirical model improvement.

For `Y=q(G)*D`, differentiation gives `Y'=q*D' + q'(G)*G'*D`. The second term is absent from the literal reduced ODE. At the audit fixture G=6 mmol/L and D=311 micrograms, the retained term is +0.00300699 and the omitted term is -0.00714753 microgram/min², reversing the derivative's sign. This fixture is a local algebraic diagnostic, not a fitted patient state. Finite differences independently agree with the complete product rule. Thus the omission cannot be assumed negligible for every permitted state merely because its formula is simple.

There is also a timing/convention distinction: under the caption initialization, the algebraic post-bolus value `q(G_max)*D_b` is 0.958843 microgram/min, whereas the reduced delayed state starts at zero. Replacing the X denominator alone does not reconcile this Y initialization or the missing product-rule term. Selecting a revised model requires a separate protocol and review.

## What the scale and basal findings resolve

The author's comment identifies a whole-pancreas mass convention, narrowing the previous unit ambiguity. Using its stated insulin molar mass, 1 microgram corresponds to 172.176309 pmol. Division by its stated 4 litres gives 43.044077 pmol/L per microgram. The coded 43 differs by -0.1024%; the separate factor 0.5 makes the complete coefficient 21.5, or 49.9488% of the unscaled conversion. That additional factor is not unit conversion. It is mathematically confounded with secretion amplitude or an effective observation volume; the inspected assets supply no independent calibration to distinguish those interpretations.

The code's separate basal rate converts to 99.862259 pmol/min under that molar-mass convention. This is a source-specific value, not a measured basal rate for the current nominal kinetic profiles, residual T1D function or a graft. M0 remains mobilization, not secretion. BC-004/005's declared synthetic basal is a different engineering input.

A future molar secretion inlet should convert mass to moles once, apply explicitly justified whole-body/body-mass normalization once, and let the observation module own its volume. It must not import the author's concentration conversion or extra multiplier into BC-003's amount-based inlet. No additional scale, basal rate or multiplier has been adopted in existing runs.

## Reproduce and inspect

```bash
uv sync --locked
uv sync --locked --project experiments/m4/beta_cell/runtime
uv run --locked python -m experiments.m4.source_audit.run \
  --output results/m4-source-audit/my-reference
uv run --locked python -S -m experiments.m4.source_audit.run \
  --reconstruct results/m4-source-audit/my-reference \
  --output results/m4-source-audit/my-reconstructed.json
cmp results/m4-source-audit/my-reference/report.json \
  results/m4-source-audit/my-reconstructed.json
uv run --locked --project experiments/m4/beta_cell/runtime \
  python -m unittest experiments.m4.source_audit.test_numerical -v
uv run --locked python scripts/check.py
```

The [audit code](../../experiments/m4/source_audit/audit.py) separates algebra from [numerical verification](../../experiments/m4/source_audit/numerical.py) and [artifact execution/reconstruction](../../experiments/m4/source_audit/run.py). Public source-extraction facts are archived, but copyrighted source files remain in ignored inspection storage. Failed/interrupted runs retain status and any artifacts; an existing output path is refused. Reconstruction recalculates algebra and diagnostics from saved states, without solving the ODE or executing archived code. Hashes detect changes, not maliciously rewritten provenance.

Run `results/m4-source-audit/reference-02` passes every frozen numerical limit: isolated-pool state discrepancy 7.318e-11 microgram, mass discrepancy 6.662e-16 microgram, initial-condition difference discrepancy 1.137e-13 microgram, solver discrepancy 1.208e-8 microgram, chain-rule finite-difference relative discrepancy 2.643e-10, and repeat discrepancy zero. These checks substantiate the calculations; they do not settle author intent. Root and scientific-runtime locked synchronization passed. The repository check passed 292 tests, lint/navigation checks and the strict documentation build. Three separate numerical tests passed. A fresh-process repeat produced all 11 deterministic artifacts byte-identically, and `python -S` reconstructed the identical report. Remote CI was not run. The machine execution record contains exact values, hashes and check outcomes. The first two complete runs were superseded only to correct source line locators; numerical code, criteria and results were unchanged.

## Verdict and review handoff

### Local verification follow-up, 27 September 2026

The unchanged BC-006 runner was executed in a fresh `codex/roadmap-non-p1` worktree at `results/m4-source-audit/roadmap-review-20260927-01` using the locked M4 runtime. Its completed report passed the frozen numerical criteria and has SHA-256 `4b80cad57346fd68eb809ab2e6cd56b2227e45308e3c7b0c2efda5cad9`, identical to the original report hash in the checked-in [execution record](../../experiments/m4/source_audit/execution.json). A `python -S` reconstruction produced byte-identical JSON, and the three dedicated numerical tests passed. The ignored local archive is not versioned and is removed with the review worktree. This checks deterministic software behavior on the same synthetic inputs and code; it adds no author confirmation, new source interpretation, human observation or independent human reproduction.

| Issue | Current verdict | Still required |
| --- | --- | --- |
| Native scale | Whole-pancreas intent and exact molar conversion documented | A justified calibration/body-size rule for the chosen population; explanation of the extra observation multiplier |
| Basal secretion | Separate coded term identified; M0 excluded as a substitute | A measured or independently justified baseline and capacity-scaling convention |
| X initialization | Pre-bolus inventory explains 92.7 to source precision | Author/reviewer confirmation, exact warmup state/clock and reference input/output |
| Reduced dynamics | Product-rule and Y-initialization distinctions demonstrated | Choice of approximation and applicability assessment before a revised model |
| External domain review | Not performed; [focused review packet](m4-collaboration-brief.md#source-reconciliation-review-packet) prepared | Named qualified reviewer, inspected version, written findings and disposition |

OT-024 and the relevant OT-015 specification gain a more precise source assessment. OT-025's dynamic cohort reproduction remains partial and OT-026's biological/glucose-feedback criteria stay open. The bounded internal audit is complete; no external endorsement, author-approved erratum, human fit or therapy mechanism is claimed. The next decision is to obtain confirmation of these source conventions and choose a reviewed model scope, before changing secretion dynamics or adding glucose feedback. No message, access application or patient download was sent.
