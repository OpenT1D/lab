# M4 secretion boundary and preparation for OT-026

Subsequent execution: [BC-002](m4-kinetic-results.md) implements and verifies the kinetic-only stage below. This page preserves the BC-001 proposal/evidence record; full metabolic feedback and biological review remain open.

Version 1.0, 20 September 2026. This is the OT-015 boundary specification and a **proposed** OT-026 implementation sequence. No metabolic coupling, controller change, C-peptide model or therapy mechanism is implemented by this document. The standalone [protocol](m4-protocol.md) has a narrower question: glucose input to evoked insulin secretion under the selected reference's IVGTT assumptions.

## What exists and what the new module adds

M1/M2 already execute two pinned metabolic engines, preserve failures and provenance, and reconstruct reports. Their whole-engine boundaries preserve absorption, distribution and clearance. The new standalone reference adds a source-attributed secretion calculation and its numerical evidence; it does not modify those engines. Neither a successful numerical check nor an additional insulin inlet establishes a valid T1D secretion model.

The [LIT-001 audit](lit001-engine-audit.md) was checked against the actual source again for this work. Both temporary upstream checkouts were clean and `git rev-parse HEAD` matched the existing pins. File hashes matched the checked-in [audit register](../../experiments/literature/lit001/engine-audit.json):

| Engine | Pin and inspected file | Verified finding |
| --- | --- | --- |
| simglucose | `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`; `simglucose/patient/t1dpatient.py`; SHA-256 `7ad1302fbf064805e2294bbcffd482e55448e37e48b63e629a1ed7f11c701547` | `Action` has only `CHO` and `insulin` (line 11). Insulin input enters the first subcutaneous depot (lines 118, 195); plasma/liver equations have no endogenous input (lines 173–192). |
| LT1 Cambridge | `9a6092065bd821f88691cd8d03b0550acd665573`; `src/core/models/Cambridge.ts`; SHA-256 `aa9b72e27e7bc947a9bd77123137dc24fd0e06383214daf94bcf2f5ceee8efad` | `iir` is converted from U/h to mU/min (line 128), feeds `S1`, then `S2`, then plasma `I` (lines 155–157). No liver compartment or endogenous input is present. |

These conclusions come from executable derivatives, not parameter names or comments suggesting an optional IV injection. Sources: [simglucose patient](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L114-L203), [Cambridge derivatives](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L120-L175).

The separately developed LIT-002 worktree was inspected read-only at base commit `5cc110710e8c521a08c0cc9a5e025c93523d2ab5`, with uncommitted additions. Its `experiments/literature/lit002/kinetics.py` isolates conserved subcutaneous depot equations; its `native/coupling.mjs` replaces Cambridge absorption and retains native systemic elimination. Inspected hashes are respectively `d5d60fdc4584b9799cf402db6a6a98926d42e61b4cbd81e23948a010b1be94ae` and `412c7aab7148477e25248a7ed85d7d174363be95d56c79b1a7b8aff36c4c1a5f`. This is a source-inspection statement, not a new execution or acceptance of that branch. Its source-pin guards, native-versus-modified derivative checks, conserved input bookkeeping and simulator-free report pattern are useful precedents. Its subcutaneous kinetics are **not** endogenous secretion, and neither its absorption code nor its physiological change is imported here.

Shared infrastructure is reusable selectively. `experiments/m1/artifacts.py` records an attempt before initialization, hashes sources and saves complete/failed status; the M4 runner can retain that pattern. M1's row schema and CGM metrics are specific to its interval contract and cannot describe intracellular pools or secretion without a new schema. M0's locked native environments remain the future engine runtimes; no new general plugin host is needed.

## Selected future route and its scientific boundary

Use the pinned simglucose plasma/liver insulin subsystem for a first **kinetic-only** OT-026 inlet experiment. It is preferable to Cambridge for this question because it already separates liver and plasma insulin. This selection does not establish that its fixed coefficients are suitable for residual secretion or a particular transplant.

The selected standalone Pedersen–Cobelli reduction exports the literal Equation 4.11c evoked release, `SR = m*X`, in micrograms/min. Glucose is in mmol/L and time is in minutes. Its states represent secretory pools, not vascular compartments; no portal transit, hepatic extraction or systemic clearance has already occurred. Unlike the full model's Equation 3.7, Equation 4.11c does not add basal secretion. It must not be relabeled total endogenous insulin or a dose of a pharmaceutical product. The reduction assumes the declining glucose phase after a rapid IV glucose challenge. [Pedersen and Cobelli, 2013, sections 2–4](https://pmc.ncbi.nlm.nih.gov/articles/PMC3638483/).

Before any numerical connection, independently justify whole-body scaling and the basal release component for the target population. The published illustrative pool masses are not a fitted T1D participant or a number of transplanted cells. Keep evoked and basal rates in separate fields. For a declared insulin molar mass `MW_I` in g/mol and measured/declared body weight `BW` in kg, the dimensional bridge would be:

```text
q_pmol_per_kg_min = q_microgram_per_min * 1e6 / (MW_I * BW)
```

No numeric molar mass or insulin mass-to-activity conversion is selected here. The future protocol must source and record it; `6000 pmol/U` in simglucose's exogenous input is an upstream activity convention, not a justification for assigning units of U to the granule model. An explicit whole-body interpretation is required even if the arithmetic conversion is correct.

For a justified total rate `q_liver` entering the liver and a separately justified peripheral rate `q_peripheral`, the proposed nonnegative-region equations are:

```text
Ra_SC = ka1*S1 + ka2*S2
dIp/dt = -(m2+m4)*Ip + m1*Il + Ra_SC + q_peripheral
dIl/dt = -(m1+m30)*Il + m2*Ip + q_liver
plasma_insulin = Ip/Vi
```

`Ip`, `Il`, `S1`, `S2` are pmol/kg; rates are pmol/(kg min); `Vi` is L/kg. The new inlet belongs at `dxdt[9]` for liver entry, not `action.insulin`, `dxdt[10]` or a pump command. Peripheral appearance belongs at `dxdt[5]`, if later justified. Source identity and a versioned experimental wrapper/patch must distinguish the modified route from intact simglucose. Preserve and explicitly test the upstream nonnegative-state derivative guards; do not silently replace their behavior.

This mapping is consistent with the liver input in Dalla Man, Rizza and Cobelli's original insulin kinetic Equation 3. Their Equation 10 also includes a direct portal-insulin effect on glucose production. The inspected simglucose line 151 omits that term and uses only glucose and a delayed peripheral insulin signal; its liver extraction coefficient `m30` is fixed. Therefore merely adding `q_liver` does **not** reconstruct the complete original model or support portal-versus-peripheral metabolic equivalence. [Dalla Man et al., 2007, Equation 3, p. 1742; Equation 10, p. 1744](https://doi.org/10.1109/TBME.2007.893506). Those two equation pages were visually checked in the [public source PDF](https://isbgroup.eu/files/Dalla%20Man%202007.pdf), SHA-256 `8780106c17434f6b553856c5bc0414c9a4fe1b5e8296b640aaa8c15d31b5eedc`; the local copy is ignored research material, not redistributed repository content.

## Ownership, route and double-counting rules

| Process or route | Proposed owner and boundary |
| --- | --- |
| Glucose-dependent evoked release | Standalone secretion module; it owns its secretory pool delays. A capacity multiplier is an exploratory functional scale, not cell count, graft survival or therapy response. |
| Basal endogenous release | Separately sourced and explicit configuration in a later protocol; absent from the present literal reduced output. Do not infer it from the T1D virtual profile's basal pump rate. |
| Portal transport | No separate transit model is present. Any future transport delay must have evidence and one owner. Do not describe an intracellular pool delay as portal transport. |
| Liver/plasma distribution and loss | simglucose alone: `m1`/`m2` exchange, `m30` hepatic loss, `m4` peripheral loss. Never apply an additional first-pass survival fraction before the liver inlet and also count the same extraction through `m30`. |
| Subcutaneous pharmaceutical delivery | Native pump/input and native `S1`/`S2` absorption; remains separate from secretion. A simultaneous LIT-002 absorption replacement would be a new comparison requiring its own controls. |
| Native pancreas | Candidate liver-entry approximation; validate its kinetics and hepatic action separately before glucose-outcome claims. |
| Intrahepatic islet graft | Liver entry is a candidate, not proof of native-pancreas equivalence. Vascularization, stimulus exposure, pulsatility and site-specific extraction remain questions. |
| Systemically drained graft | Candidate peripheral entry after any explicitly modeled local transport; it does not automatically inherit pharmaceutical SC absorption. A subcutaneous implant is not a subcutaneous insulin injection. |
| C-peptide | A later independent secretion-observation pathway with its own kinetic constants, volume and renal-function assumptions. Do not send C-peptide through insulin clearance or infer secretion by equating its measured concentration to an insulin rate. |

Meier et al. measured pulsatile secretion in 10 islet recipients and first-pass extraction by hepatic catheterization in only two autograft recipients. Their findings support investigating liver exposure but do not supply a universal graft extraction coefficient. The distinct populations and small catheterization sample prevent simply assigning its reported extraction to every transplant. [Meier et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16873697/).

For any proposed combined inlet, the mass accounting check is:

```text
d(S1+S2+Ip+Il)/dt = u_SC + q_liver + q_peripheral - m4*Ip - m30*Il
```

`m2*Ip` and `m1*Il` are transfers, not disappearance. The ledger must also include any later explicitly added transit inventory. This identity holds in the ordinary nonnegative region with fixed normalization; tests must expose invalid states or altered guards rather than hide a balance error by clipping outputs.

## Initialization, timing and the minimum OT-026 test

The next bounded experiment should replay a declared secretion trace into the insulin subsystem only, while keeping glucose as a prescribed external input. It must not feed arbitrary meals, rising glucose oscillations or CGM into the IVGTT reduction. A closed secretion–glucose loop requires a reference applicable to that glucose regime or a separately justified extension and evaluation.

Use minutes from an explicit post-bolus origin, monotonic sample timestamps and declared interpolation. Split at every forcing knot. The secretion integration clock and the native one-minute step are not interchangeable. A coupled solver or a conservative interval-integral transfer must account for secretion between exchanges; merely passing the value at the end of an interval can lose or advance released insulin.

For the first kinetic-only test, use zero insulin inventories and a declared finite liver input so that mass and independent analytic response are unambiguous. This is an engineered inlet test, not a fasting person. Separately test native profile initialization with **zero added secretion** against intact simglucose. For any later basal comparison, record prior SC delivery, endogenous basal release, every insulin inventory and equilibrium calculation; adding secretion to an unchanged basal pump regimen changes exposure and does not measure reduced insulin need.

Required future checks are:

1. Pin/hash identity and exact zero-extension agreement with native derivatives and trajectories; only the named input derivative may change.
2. Dimensional conversion fixtures, integrated input amounts and route-specific source attribution; no activity/mass or whole-body/per-kg ambiguity.
3. Independent matrix-exponential solution of the two-compartment linear insulin subsystem for zero, constant and finite-pulse liver inputs, with separately computed integral mass balance.
4. Zero capacity with appropriately zero initial evoked pools, no input, positive finite outputs, reset/repeat equivalence, malformed input rejection and durable partial/failure artifacts.
5. Joint refinement of secretion integration, native solver and communication interval. Set absolute/relative tolerances and an effect-relative criterion before comparing scenarios; a small modeled contrast is unresolved if comparable to the numerical change.
6. Route contrasts at equal **secreted amount**, retaining distinct systemic exposure. Do not force equal concentrations and then call the dose difference a biological discovery.
7. A comparator without secretion and a fixed-input/constant-baseline secretion comparator. Assess whether time-varying release adds information after overall exposure and initial conditions are accounted for.

These checks are specified here, not executed. Their tolerances belong in the separately frozen OT-026 protocol once scale, scenario and runtime are selected. Existing M1/M2 reference artifacts must remain unchanged.

## What observations can distinguish

Glucose alone generally cannot resolve secretion amplitude, hepatic extraction, peripheral clearance and insulin action in this proposed composition. For a fixed linear kinetic block, scaling secretion and inversely scaling an observation gain produces identical concentration observations; unknown effective volume or functional scaling can therefore confound capacity even before adding glucose dynamics. Synthetic recovery with chosen fixed parameters tests the estimator under those assumptions, not human identifiability.

A future dynamic study should measure plasma glucose, sufficiently early and frequent C-peptide and insulin, assay limits and uncertainty, body size, renal function, basal history, exogenous insulin identity/timing and the glucose challenge. C-peptide can inform endogenous secretion only through an appropriate kinetic observation model and its assumptions. Insulin measurements additionally require distinguishing administered insulin/assay cross-reactivity and clearance; C-peptide does not by itself identify first-pass insulin extraction. Dynamic excitation and independent kinetic information may separate some parameter combinations; record profile likelihoods or equivalent uncertainty and report unresolved combinations instead of forcing unique estimates.

For transplantation, also require graft site, time since implantation, treatment/immunosuppression, repeat standardized function tests, concurrent exogenous delivery and relevant safety/outcome definitions. Do not infer a graft's anatomical cell mass from a release multiplier. A decline in that multiplier is a hypothetical functional scenario until longitudinal observations support its interpretation.

The OT-026 gate is therefore a source-linked, reviewed **kinetic inlet** with checked numerics and explicit basal/scale conventions. The following gate is a secretion model supported for the intended glucose regime plus an identifiable observation plan. Only then can a separately frozen study assess modeled glucose or external-insulin requirements. M5 additionally needs a named intervention, target population, longitudinal endpoint and independent observations; numerical capacity sweeps are preparation for that study, not evidence of a treatment effect.
