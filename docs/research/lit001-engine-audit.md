# LIT-001 source-to-engine audit

Version 1.0, 20 September 2026. **L5 source inspection completed for the two pinned engines.** This records implemented insulin pathways and their documented ancestry; it is not a paper-figure reproduction, a lispro validation or a physiological change. The scope comes from the [LIT-001 plan](literature-research-plan.md#8-source-to-engine-audit). The [machine-readable audit](../../experiments/literature/lit001/engine-audit.json) records file hashes, exact locations, findings and unresolved items.

## Main finding and consequence

Both engines already own subcutaneous absorption and systemic insulin kinetics. simglucose uses two subcutaneous depots with absorption from both, followed by plasma/liver exchange. LT1 Cambridge uses two serial depots with absorption from the second, followed by a single plasma elimination compartment. These structures are materially different. Neither inspected patient module names a conventional lispro product, concentration or population-specific lispro validation.

The immediate value of the literature dossier is to compare a fully specified published kinetic model with these existing structures, resolve parameter ancestry where possible and select an informative standalone reference. It does not justify replacing either engine or labeling its present parameters as lispro-specific. Keep controller development separate: a controller's private predictor is not an additional absorption process in the simulated subject.

## Inspected sources and verification boundary

| Engine | Inspected revision and identity | Native scientific attribution |
| --- | --- | --- |
| simglucose | `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`; package 0.2.11 in [setup.py, lines 3–10](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/setup.py#L3-L10) | [README, line 9](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/README.md#L9) identifies the 2008 UVA/Padova lineage. The [parameter glossary, lines 3–8](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/definitions_of_vpatient_parameters.md#L3-L8) combines a meal-model paper, the later New Features paper and code-based inference. This is not a verified parameter-by-parameter ancestry chain. |
| LT1 Cambridge | `9a6092065bd821f88691cd8d03b0550acd665573`; package 2.1.0 and Cambridge profile 2.1.0 | [Cambridge.ts, lines 27–43](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L27-L43) cites Hovorka et al. (2004), *Nonlinear model predictive control of glucose concentration in subjects with type 1 diabetes*, and Andersen's 2014 thesis, *Software for in Silico Testing of an Artificial Pancreas*. This audit verifies those citations in code, not that every default has been traced to an original experimental estimate. |

The local M0 runtime/source directories were absent. Public upstream repositories were fetched into temporary directories and checked out at the exact OpenT1D pins. `git rev-parse HEAD` matched both pins and `git status --porcelain=v1` was empty in each checkout. SHA-256 hashes were calculated from the inspected files. The files and versions correspond to the existing [simglucose](models/simglucose.md) and [Cambridge](models/lt1-cambridge.md) cards. No upstream source or parameter table was copied into OpenT1D, and no engine was installed or executed for this audit.

## 1. simglucose: delivered rate to insulin concentration

### Input and state semantics

The controller supplies `basal` and `bolus` as rates in U/min. The pump separately quantizes and limits each rate; the native environment adds their modeled outputs and calls the patient once per one-minute step. The word `bolus` therefore does not mean an instantaneous state jump. The basal-bolus controller divides its calculated bolus amount by the environment sample interval before returning it. See [pump.py, lines 23–39](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/actuator/pump.py#L23-L39), [env.py, lines 48–81](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/simulation/env.py#L48-L81) and [basal_bolus_ctrller.py, lines 64–80](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/basal_bolus_ctrller.py#L64-L80).

Let `u` denote the delivered native rate in U/min and `BW` the virtual profile's body weight in kg. The implemented conversion is `u_pmol = 6000*u/BW`, in pmol/kg/min. The factor 6000 is an upstream insulin-unit convention; its occurrence in code does not verify compatibility with every published assay or insulin formulation. [T1DPatient.model, lines 114–119](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L114-L119)

The following names are descriptive audit aliases for the code's zero-based state indices. Dimensions follow the implemented conversion and concentration equation, checked against the relevant glossary entries; they do not rely on every glossary label being correct.

| State | Audit meaning | Dimension | Source |
| --- | --- | --- | --- |
| `x[10] = S1` | First subcutaneous depot | pmol/kg | Patient lines 194–199 |
| `x[11] = S2` | Second subcutaneous depot | pmol/kg | Patient lines 194–199 |
| `x[5] = Ip` | Plasma insulin amount per body mass | pmol/kg | Patient lines 172–180; `Ip/Vi` is concentration |
| `x[9] = Il` | Liver insulin amount per body mass | pmol/kg | Patient lines 190–192 explicitly give the unit |
| `It = Ip/Vi` | Plasma insulin concentration | pmol/L | Patient line 179; `Vi` is L/kg |
| `x[6]` | Delayed insulin action signal for utilization | pmol/L | Patient line 183 |
| `x[7]`, `x[8]` | Successive insulin signals for glucose production | pmol/L | Patient lines 185–188 |

The exact executable equations are in [T1DPatient.model, lines 172–199](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L172-L199). In the nonnegative state region, with time in minutes, they reduce to:

```text
dS1/dt = u_pmol - (ka1 + kd)*S1
dS2/dt = kd*S1 - ka2*S2
RaI    = ka1*S1 + ka2*S2
dIp/dt = -(m2 + m4)*Ip + m1*Il + RaI
dIl/dt = -(m1 + m30)*Il + m2*Ip
It     = Ip/Vi
```

Here `kd`, `ka1`, `ka2`, `m1`, `m2`, `m4` and `m30` have dimension 1/min. `RaI` is an audit alias for the two influx terms in the plasma equation, not a native exported signal. The code multiplies several derivatives by whether the corresponding state is nonnegative. The displayed equations describe the nonnegative region; that implementation detail must be retained in a later direct comparison rather than silently replaced with another positivity rule.

`ka1*S1` provides a direct path from the first depot; `kd*S1` transfers insulin to the second. There is no separate subcutaneous degradation or bioavailability term in these equations. Algebraically, `d(S1+S2)/dt = u_pmol - RaI`. In the systemic subsystem, `d(Ip+Il)/dt = RaI - m4*Ip - m30*Il`. These are algebraic interpretations of the inspected code, not measured mass-recovery results. The plasma loss `m2*Ip` transfers to the liver; it must not be counted as irreversible clearance. The liver-to-plasma term `m1*Il` likewise transfers rather than eliminates insulin.

The patient does not add endogenous insulin secretion. It uses the parameter `m30` as a fixed coefficient in the liver equation. A separate `m5`, `HEb` or `CL` column in the upstream table is not evidence that the patient function dynamically applies the corresponding process. The insulin-related columns read by the function are the coefficients shown above plus concentration/action/basal quantities; the glossary's discussion of variable hepatic extraction must not override the implemented equation.

### Parameters, body weight and reset

The patient reads the selected row of `simglucose/params/vpatient_params.csv`; the [loading code, lines 40–64](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L40-L64) selects a virtual profile by ID or name. Its header is inventoried by hash in the audit; row values are not reproduced. `BW` converts a whole-body dose rate into body-mass-normalized states. It is a profile parameter, not BMI and not a measured participant identifier.

On reset, the initial state is copied from the profile's thirteen state columns unless a caller supplied a custom initial state. The solver restarts at `t0` using SciPy `dopri5`; optional random initialization changes only glucose-related states. Meal bookkeeping is also reset. A standalone kinetic comparison must preserve depot/plasma/liver initial states and basal history, or explicitly study a new baseline-adjusted experiment. [T1DPatient.reset, lines 247–285](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L247-L285)

There are material documentation ambiguities in the upstream glossary/controller comments: glossary line 26 calls `Ip` a mass but gives pmol/L, while line 35 gives the basal plasma amount as pmol/kg; `ki` is labeled mg/kg/min at line 57 although its executable first-order delay equation requires 1/min; controller comments describe `u2ss` using pmol/(L*kg), although `u2ss*BW/6000` is treated as U/min. We use the executable relationships to state dimensions and flag these discrepancies rather than propagating them as verified scientific definitions. [Parameter glossary, lines 24–57](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/definitions_of_vpatient_parameters.md#L24-L57), [controller, lines 34–64](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/controller/basal_bolus_ctrller.py#L34-L64)

The baseline calculation in the patient function is used for logging, not added as a second infusion. The actual delivered rate must contain any intended basal component. The environment's `BG` output is subcutaneous glucose, while the internal `It` is plasma insulin; neither `BG` nor `CGM` is a measurement of insulin. [Patient lines 205–220](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L205-L220)

## 2. LT1 Cambridge: serial absorption and plasma elimination

### Input, states and equations

LT1 distinguishes controller infusion `iir` in U/h and bolus `ibolus` in U. The pump supplies a modeled infusion in U/h to the patient. Cambridge converts this to `r = 1000*iir/60`, in mU/min. `S1` and `S2` are whole-body insulin amounts in mU; `I` is plasma concentration in mU/L; `VI` is L/kg and `BW` is kg. Thus `VI*BW` is the total distribution volume in L. These quantities differ from the per-kg amounts in simglucose. [Signals.ts, lines 43–64](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/types/Signals.ts#L43-L64), [Cambridge.ts, lines 124–128](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L124-L128), [state definitions, lines 227–238](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L227-L238)

For `tau = tmaxI` and time in minutes, the [implemented subsystem, lines 154–162](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L154-L162) is:

```text
dS1/dt = r - S1/tau
dS2/dt = (S1 - S2)/tau
RaI    = S2/tau
dI/dt  = RaI/(VI*BW) - ke*I
dx1/dt = -ka1*x1 + (ka1*SIT)*I
dx2/dt = -ka2*x2 + (ka2*SID)*I
dx3/dt = -ka3*x3 + (ka3*SIE)*I
```

Only the second depot feeds plasma. There is no separate local degradation term, liver insulin state or endogenous secretion term in this subsystem. `ke*I` is the plasma elimination term. `RaI` is again an audit alias, in mU/min. For fixed `VI` and `BW`, the algebraic balances are `d(S1+S2)/dt = r-RaI` and `d(VI*BW*I)/dt = RaI-ke*VI*BW*I`. If a future experiment makes volume or body weight time-varying, these fixed-volume balance identities cannot be applied without accounting for that change.

The model's `ka1`, `ka2` and `ka3` govern **insulin-action deactivation**, not absorption. They must not be populated with simglucose's absorption constants just because the symbols match. Absorption is controlled by `tmaxI`, documented as a short-acting-insulin absorption time, with a code default of 55 min. `ke` and `VI` default to 0.138/min and 0.12 L/kg. These are verified software defaults, not newly verified estimates for conventional lispro in adults. [Parameter descriptions, lines 187–218](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L187-L218)

For an ideal depot impulse and fixed parameters, `tmaxI` describes the peak of the serial-depot appearance profile, not necessarily the peak time of plasma concentration. The latter additionally depends on the elimination equation, initial conditions and input duration. This is an equation-derived distinction, not a fitted numerical result.

### Parameter-source follow-up, 27 September 2026

The primary [Hovorka et al. (2004) paper, Tables 1–2 on p. 909](https://www.stat.yale.edu/~jtc5/diabetes/NonlinearModelPredictiveControl_Hovorka_04.pdf) prints `ke=0.138/min`, `VI=0.12 L/kg` and `tmax,I=55 min`. It attributes `ke` and `VI` to Hovorka et al. (1993), and the 55-minute short-acting-insulin absorption parameter to Howey et al. (1994) and Rave et al. (1999). These values, roles and units match the pinned LT1 defaults and the implemented `VI*BW` volume conversion. This is a source-to-code match, not an independent review of the cited 1993/1994/1999 studies or proof of unchanged patient-specific calibration.

The [1993 paper's original abstract](https://pubmed.ncbi.nlm.nih.gov/8338148/) describes a five-compartment insulin-kinetics study in people with non-insulin-dependent diabetes. Its full parameter derivation was not inspected here. Thus the 2004 citation identifies a source lineage, not direct evidence that the fixed one-compartment LT1 values were estimated for the current virtual T1D profile.

The other two cited records also need a narrower reading. [Howey et al. (1994), original abstract](https://pubmed.ncbi.nlm.nih.gov/8314011/) describes a 10 U glucose-clamp comparison in ten healthy men with separate zinc-free lispro, zinc-containing lispro, subcutaneous regular insulin and intravenous regular-insulin arms. It reports **plasma concentration** peak times of 42 min for zinc-free lispro and 101 min for subcutaneous regular insulin. Those endpoints are not the serial-depot appearance peak `tmaxI`, and the zinc-containing formulation is a separate arm. [Rave et al. (1999), original article record](https://diabetesjournals.org/care/article/22/5/865/20847/Premixed-formulations-of-insulin-lispro-Activity) is a brief report on **premixed lispro activity profiles** in people with T1D; its article text is access restricted and PubMed provides [no abstract](https://pubmed.ncbi.nlm.nih.gov/10332707/). Its title and accessible metadata do not establish a 55-minute appearance peak for an unmixed product. The inspected primary records therefore identify the cited studies and an endpoint mismatch, but do not independently derive Hovorka's 55-minute model setting. Full methods and numerical provenance remain open.

The [Andersen 2014 thesis, Appendix D example (PDF p. 125)](https://www2.imm.dtu.dk/pubdb/edoc/imm6768.pdf) independently prints `TS=55.0`, `Ke=0.138` and `VI=0.12`. Its Section 3.1.2 labels `VI` in L without an explicit `/kg`; the 2004 primary table resolves the intended per-kg convention for the published Hovorka parameter, and the pinned LT1 equation multiplies by body weight. Andersen's Table 3.2 (PDF p. 36) describes a separate virtual-cohort distribution, not the fixed LT1 profile. The matching numerals do not establish that LT1 inherited that cohort, specifies conventional lispro as a product, or reproduces the original studies. The historical LIT-001 source inventory and numerical artifacts are unchanged.

An independent dimensional sentinel uses a declared illustrative 70 kg body mass and 1 U/h constant infusion. The published/pinned volume convention gives `VI*BW=8.4 L`; with complete steady-state absorption, `1000/60/(0.138*8.4)=14.377732 mU/L`. Treating `0.12` as a whole-person volume instead gives `1006.441224 mU/L`, exactly 70 times larger. This arithmetic verifies the consequence of the unit boundary; it is not a native trajectory, patient concentration or new numerical result for LIT-002.

### Reset, pumps and controller separation

Cambridge computes steady-state depot amounts from the equilibrium infusion: `S1=S2=iir*tmaxI*1000/60`, with plasma concentration obtained through `VI*BW*ke`. The wrapper uses a supplied initial state when present, otherwise its calculated equilibrium. Reset attaches the solver and resets the last update time; it does not generate a new clinical person. [Cambridge steady state, lines 91–117](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/models/Cambridge.ts#L91-L117), [AbstractODEPatient.ts, lines 177–258](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/AbstractODEPatient.ts#L177-L258)

The inspected upstream reference overrides the subject's equilibrium glucose, selects IdealCGM and StaticInsulinPump, and configures an MPC controller; it does not provide a patient cohort or a lispro formulation record. [ReferenceScenario.ts, lines 19–48](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/examples/MPC/IFAC_EDT_2025_Hauser/scripts/ReferenceScenario.ts#L19-L48)

`MPC_Hovorka2004` constructs its own Cambridge instance, extended Kalman filter and forward-Euler prediction solver. Its reset initializes a prediction sequence and uses a five-minute internal solver step; its prediction routine advances that private model using candidate infusion rates and announced meals. The controlled subject instead uses the Simulator's patient and solver. Consequently a change to subject parameters would not automatically update the controller's private model, and changing both simultaneously would confound a physiology comparison. [MPC_Hovorka2004.ts, lines 49–120](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/controllers/MPC_Hovorka2004.ts#L49-L120), [prediction, lines 232–249](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/controllers/MPC_Hovorka2004.ts#L232-L249)

StaticInsulinPump quantizes and upper-bounds commands, adds configured error and returns `iir + 60*ibolus`, with the intention of expressing a bolus over one minute. Its source explicitly leaves earlier callbacks unresolved, and it does not apply a lower-bound clamp. These already motivate the [M2 support restrictions](../decisions/0004-m2-native-process-tracks.md#scientific-conventions-and-limits). A standalone absorption reference should use a fully specified infusion or initial depot input without claiming that an arbitrary native bolus callback reproduces an ideal injection. [StaticInsulinPump.ts, lines 67–93](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/actuators/StaticInsulinPump.ts#L67-L93)

The Simulator resets its solver and modules, advances the subject under the previous medication, then updates sensor, controller and actuator. Its default outer step is one minute, shortened at requested events. The subject solver is RK1/2 with adaptive steps, distinct from the MPC's forward Euler predictor. These clocks and initial conditions must remain explicit in any later coupled test. [Simulator.ts, lines 179–250](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/Simulator.ts#L179-L250), [event timing, lines 319–341](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/Simulator.ts#L319-L341), [SolverRK1_2.ts, lines 20–69](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/src/core/solvers/SolverRK1_2.ts#L20-L69)

## 3. Comparison and unresolved evidence

| Item | Verified relationship or difference | Consequence for LIT-001 |
| --- | --- | --- |
| Delivery boundary | U/min in simglucose; U/h in LT1 | Convert dose rates explicitly; preserve amount and infusion duration. |
| Depot units | pmol/kg versus whole-body mU | Record body weight and unit conversion; a shared numeral is not a shared dose. |
| SC topology | Two appearance paths versus serial-only appearance | Compare model equations rather than generic simulator labels. |
| `ka1`, `ka2` | Absorption constants versus action-deactivation constants | Never transfer values by symbol alone. |
| Systemic kinetics | Plasma/liver exchange with two irreversible losses versus one plasma elimination compartment | Compare concentration only after accounting for each systemic model. |
| Local degradation | No independent term in either inspected SC subsystem | A paper with local degradation introduces a new process; it is not a parameter rename. |
| Formulation | Neither inspected patient module identifies conventional lispro or concentration | Product-specific evidence remains unresolved. |
| Initialization | Profile state vector versus calculated equilibrium/custom state | Retain basal history and baseline semantics; do not infer zero initial depots. |
| Insulin output | Derived internal plasma concentration versus named internal `I` state | Neither routine CGM/glucose output supplies a measured insulin validation target. |
| Parameter provenance | simglucose table/glossary; LT1 constants with model-level citations | Original study, estimation method and intended-population provenance remain incomplete. |
| Controller | Separate command generator; LT1 MPC has its own Cambridge predictor | Keep the open-loop kinetic audit separate from closed-loop performance. |

The serial subcutaneous structure is an algebraic special case of the simglucose depot equations if `ka1=0` and `kd=ka2=1/tmaxI`, after consistent unit normalization. This observation does **not** establish that the pinned parameters satisfy those conditions, that the full engines are equivalent, or that their systemic kinetics can be interchanged. No such parameter change was made.

The simglucose upstream license is MIT with Jinyu Xie's notice; LT1 declares MIT with Heiko Peuscher and contributors' notice. The corresponding source licenses are [simglucose LICENSE](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/LICENSE) and [LT1 LICENSE.md](https://github.com/hpeuscher/loopinsight1/blob/9a6092065bd821f88691cd8d03b0550acd665573/LICENSE.md). This audit verifies declarations; it does not establish an independent chain of title for every upstream parameter asset or extend permission to original journal figures and data. No upstream parameter CSV is redistributed here.

## 4. Decision and completed checks

**Decision:** retain both native engines unchanged. Use the LIT-001 standalone dossier to assess whether a published lispro kinetic reference is reconstructible, with input normalization, local losses, systemic clearance, assay semantics and initial conditions recorded. Any later sensitivity study must justify its parameter ranges from the selected source. Any structural coupling must explicitly replace the native process it takes over, retain a baseline, compare with parameter-only calibration and pass a separate protocol.

Current M3/1 remains a CGM-only statistical forecasting protocol. Its outputs cannot identify the above insulin mechanisms or supply a direct insulin kinetic evaluation. B1 improvement claims still require suitable observations and reserved assessment under the roadmap.

Completed for L5: exact Git revision/clean-checkout verification; direct reading of the patient, pump, lifecycle, controller, parameter-definition and license sources; source-location and SHA-256 inventory; dimensional/algebraic inspection of the displayed insulin subsystems; JSON parsing and verification that every inventoried file hash and cited line range matches the checked-out source. These are source/audit checks. Native simulation, numerical convergence, published-figure agreement, assay-conversion verification, independent parameter-origin review and independent human reproduction were not performed in L5. Repository-wide documentation checks are recorded with the enclosing LIT-001 execution rather than asserted here before they run.
