# BC-007: prescribed glucose to paired kinetic outputs

Specified before numerical execution on 20 September 2026, from `f96fe29`, for the next bounded OT-026 deliverable. The [machine protocol](../../experiments/m4/chain/protocol.json) fixes cases, source identities, runtime versions and numerical criteria. [Decision 0022](../decisions/0022-glucose-secretion-kinetic-chain.md) defines the composition. BC-001 through BC-006 remain unchanged.

## Question and scope

Can one reproducible execution carry prescribed synthetic glucose through the existing secretion reference into separate insulin and C-peptide kinetic outputs, preserving units, initial conditions, process ownership and source identity? The glucose curve is an imposed declining post-IVGTT exponential, not a prediction. There is no glucose feedback, patient fit or therapy effect.

Reuse the scientific ancestry already documented in the [BC-001 model card](models/pedersen-cobelli2013.md), [BC-002 boundary](m4-kinetic-boundary.md), [BC-003 card](models/polonsky1986-cpeptide.md), [BC-004 contract](m4-paired-protocol.md) and [BC-005 execution](m4-paired-kinetics-protocol.md). [BC-006](m4-source-audit-results.md) remains the explicit limitation on initialization, basal interpretation and observation scaling. No new scientific parameter or source correction is adopted.

## Execution and boundary

Start a fresh, complete BC-001 run inside the chain archive, using its unchanged protocol and locked environment. Reconstruct and verify it before transfer. Its literal printed initialization, Y(0)=0, nominal parameters and synthetic glucose input remain authoritative. Source outputs carry minutes, mmol/L, micrograms and micrograms/minute; source glucose is displayed beside the downstream outputs but never overwritten by a metabolic trajectory.

Interpret the evoked mass output as an explicitly uncalibrated whole-body signal. Convert exactly once by `q = gain * secretion * 1e6 / (5808 * 102.32)` to pmol/(kg min). Apply the same molar input to the native insulin liver inlet and C-peptide central inlet. Distribution volumes belong to the respective observation models. Do not apply an extra hepatic fraction, subcutaneous absorption, the author's C-peptide observation multiplier or a second body-mass normalization.

The primary transferred signal is the piecewise-linear interpolant of the 0.25-minute source samples, without extrapolation. Each segment's trapezoidal integral defines the transferred amount; it does not assert knowledge of the exact unsampled secretion. Both branches report from 0 to 100 minutes on the source grid. Insulin uses the existing BC-005 nonzero-inventory wrapper and C-peptide the existing BC-003 solver, in their separate unchanged environments.

Cases are zero increment, half increment, full increment, full increment plus synthetic basal, basal only, and a constant increment with the same integrated amount as the full source. Gains apply only to evoked secretion; they are hypothetical amplitude scenarios, not fitted residual function. The separate basal input is the existing BC-004 engineering fixture, 153.48 pmol/min (1.5 pmol/(kg min)). It stays fixed when evoked gain changes. Synthetic-total and basal-only cases start from BC-004's separate stationary inventories; cumulative ledgers start at zero. Time zero is the post-bolus source clock: basal inventories are continuous while evoked input starts immediately, with no instantaneous kinetic inventory injection.

The insulin profile and nominal C-peptide group parameters are a synthetic pairing, not measurements from the same person. The source population does not confer T1D or transplant validity on this composition.

## Checks fixed before results

Compare each branch's tight RK45 solution with DOP853 and an independent matrix-exponential propagation. Preserve exact regression against the historical zero-initial insulin path where applicable. Verify input identity, one-time conversion, original source provenance, finite complete grids/states, nonnegativity and mass conservation including initial inventories. Check exact zero, half/full linearity, basal equilibrium, total = basal + increment for all states/ledgers, equal delivered amount of the constant comparator, and deterministic repeated integration. Report the comparator's concentration differences descriptively; there is no empirical superiority criterion.

Independently rerun the unchanged secretion model at 0.125 and 0.0625 minute output spacing with its reference solver. Require agreement at the original nested sample times. Transfer each interpolant into both kinetic branches, using identical output times and reference settings. Compare 0.25 and 0.125 minute source sampling against the finest interpolant: the latter is a numerical comparison reference, not exact continuous-input truth. This distinguishes source sampling from kinetic solver error. Require finest pair concentration difference at most 0.01 pmol/L, middle/coarse error ratio at most 0.35, and relative integrated-source difference between the finest two samplings at most 1e-4.

Other limits: independent state discrepancy 1e-7 pmol/kg; solver concentration discrepancy 1e-5 pmol/L; mass/input discrepancy 1e-7 pmol/kg; negativity allowance 1e-9 pmol/kg; linearity/superposition 1e-7 pmol/kg; basal drift 1e-8 pmol/kg; conversion relative discrepancy 1e-12; equal-amount discrepancy 1e-10 pmol/kg; nested source samples 1e-10 microgram/min; exact zero for paired forcing, historical zero-initial regression and repeated output. These maxima apply at recorded times and are numerical tolerances, not physiological bounds.

## Artifacts and evidence

Archive the complete BC-001 run, original/finer source samples, boundary protocol, derived forcings, initial inventories, parameters, source snapshots, both locks, runtime/native identities, all numerical/reference outputs, logs, report and figure. Reject incomplete/failed source or branch runs. Preserve failure status, refuse overwrite and never use saved code as executable reconstruction input. Standard-library reconstruction must verify hashes and recompute summaries from saved states; regenerating numerical reference states requires rerunning the experiment.

Perform meaningful unit/failure tests, fresh-process repetition, simulator-free report reconstruction and artifact-only figure reconstruction. Update the roadmap only for this demonstrated synthetic chain. Source confirmation, biological review, glucose feedback, independent observations and M4/OT-026 completion remain separate open criteria.
