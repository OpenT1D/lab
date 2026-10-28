# OT-026 kinetic inlet: scale, baseline and evidence boundary

Source review dated 20 September 2026. This document resolves the units and baseline choices for a bounded insulin-kinetic experiment following [BC-001](m4-results.md) and the [OT-015 coupling proposal](m4-coupling.md). It does not resolve the biological interpretation of the secretion reference, supply a human calibration or establish a complete metabolic coupling.

## Primary inlet and incremental baseline

The primary test input is a declared synthetic rate `q_liver(t)` in **pmol/(kg min)**. It enters the liver insulin derivative directly. Native units make a finite pulse or constant-forcing test possible without assuming a total beta-cell mass, transplant size or basal endogenous secretion. The test concerns transport and loss of an added insulin amount.

Let `delta_Ip` and `delta_Il` denote added plasma and liver insulin amounts, both in pmol/kg. Start these increments at zero and set added input to zero outside the declared stimulus. In the nonnegative region of the pinned fixed-coefficient subsystem:

```text
d(delta_Ip)/dt = -(m2+m4)*delta_Ip + m1*delta_Il + q_peripheral
d(delta_Il)/dt = m2*delta_Ip - (m1+m30)*delta_Il + q_liver
delta_plasma_concentration = delta_Ip/Vi
```

The zero added baseline is a **perturbation convention**, not a claim that a person has no circulating insulin. Because these kinetic equations are linear with fixed coefficients, a nonnegative added trajectory can be superposed on an unchanged background trajectory. A separate zero-extension test must preserve native initial states and SC inputs and compare against unmodified simglucose. The equivalence does not extend to the complete nonlinear glucose model or to arbitrary negative states where upstream derivative guards operate.

For the isolated inlet test, no background trajectory is needed: zero insulin inventories deliberately describe an engineered transport experiment. No endogenous basal term is inferred from the virtual patient's pump rate. A later physiological basal study must specify both delivery routes, basal histories and equilibria with appropriate evidence.

## Optional BC-001 mass-rate replay

BC-001 supplies evoked release `SR(t)=mX(t)` in micrograms/minute. A **nominal whole-body-mass interpretation** can be used as an explicitly synthetic replay scenario: treat that illustrated mass rate as an imposed whole-body input, then divide by the selected virtual profile's declared body weight. This is an assumption about scale, not a fitted or demonstrated property of a person or graft. The primary native-unit inlet test does not depend on this assumption.

The rounded human-insulin molar mass used for the dimensional conversion is **5808 g/mol**. The FDA-hosted, May 2018 Humulin R label, section 11, PDF page 6, gives the human-insulin empirical formula and molecular weight 5808. The [fixed label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2018/018780s168lbl.pdf#page=6) was inspected as a primary chemical description, not as a source of dosing, absorption or endogenous-clearance parameters. A [DailyMed manufacturer label, section 11](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b60e8dd0-1d48-4dc9-87fd-e14675255e8c) independently states 5.808 kDa. This agrees with the numeric 5808 appearing in the [Pedersen author file](https://www.dei.unipd.it/~pedersen/secr_model_IVGTT_new.ode); its additional concentration/volume scaling is not adopted.

```text
q_pmol_per_kg_min = SR_microgram_per_min * 10^6 / (5808 * BW_kg)
```

The factor `10^6` combines micrograms-to-grams with moles-to-picomoles. Thus 1 microgram represents approximately 172.1763 pmol under this rounded convention. At the native `adult#001` virtual body weight of 102.32 kg, 1 microgram/minute maps to approximately 1.682724 pmol/(kg min). Use the actual selected profile's recorded `BW`; do not silently substitute a population mean. Retain the original mass trace, conversion constant, profile and converted input in provenance.

Neither the conversion nor a dimensionless amplitude sweep establishes that BC-001's illustrative pool masses describe whole-body T1D secretion. Its unresolved initialization and changing-glucose approximation remain inherited limitations. Basal release stays absent, and the replay remains a prescribed declining-IVGTT stimulus rather than feedback from a newly computed glucose curve. Native `6000 pmol/U` is an exogenous activity convention and is not used to translate this secretion mass into an insulin dose.

## Native parameter and equation ancestry

The inspected simglucose checkout is commit `a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc`. Its patient derivative and parameter CSV match the hashes in the [existing engine audit](lit001-engine-audit.md). Their SHA-256 values are respectively `7ad1302fbf064805e2294bbcffd482e55448e37e48b63e629a1ed7f11c701547` and `662f3b684d160fdf485edd1d7196dd1cd85c14b53650b030fdb86aaa05bb2e50`.

| Quantity | Native `adult#001` value | Meaning |
| --- | --- | --- |
| `m1` | 0.15446 min^-1 | Liver-to-plasma transfer |
| `m2` | 0.225027424083 min^-1 | Plasma-to-liver transfer |
| `m4` | 0.090010969633 min^-1 | Peripheral irreversible loss |
| `m30` | 0.23169 min^-1 | Fixed hepatic irreversible loss |
| `Vi` | 0.054906 L/kg | Plasma insulin distribution volume |
| `BW` | 102.32 kg | Virtual profile's body weight |

These are inherited virtual-profile values from the pinned [parameter CSV](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/params/vpatient_params.csv), not newly estimated human parameters. The [patient derivatives](https://github.com/jxx123/simglucose/blob/a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc/simglucose/patient/t1dpatient.py#L172-L199) establish that state indices 5 and 9 contain plasma/liver amount per body mass and that dividing plasma amount by `Vi` produces pmol/L. The glossary's inconsistent plasma-amount label is not propagated. simglucose's license permits reuse subject to preserving its copyright and license notice.

Dalla Man, Rizza and Cobelli's original [2007 model, DOI 10.1109/TBME.2007.893506](https://doi.org/10.1109/TBME.2007.893506), equation 3 on p. 1742, places secretion into the liver and specifies these amount/rate/volume dimensions. The source also permits time-varying hepatic extraction and includes a direct portal-insulin term in glucose production (equation 10, p. 1744). The relevant pages were visually inspected. This establishes equation ancestry; it does not identify the original clinical fitting record for every native virtual coefficient or make this fixed-coefficient test a reproduction of the full 2007 model.

## Accounting and limits of the result

Native exchange terms transfer insulin rather than remove it. The independent ledger for added amounts is:

```text
delta_Ip + delta_Il + cumulative_peripheral_loss + cumulative_hepatic_loss
    = cumulative_liver_input + cumulative_peripheral_input
```

Initial added amounts are zero. Loss rates are `m4*delta_Ip` and `m30*delta_Il`. No additional first-pass fraction should be applied before liver entry: that would duplicate extraction already represented by `m30`. An added portal transit compartment would change both ownership and inventory accounting and is outside this test.

The inspected native glucose-production equation lacks the original direct portal-insulin term. Consequently, equal-input liver/peripheral kinetic contrasts cannot establish equivalent glucose control, native-pancreas/graft equivalence or reduced external-insulin requirements. The kinetic result can establish only that a specified added rate enters the intended compartment and that transfer, clearance, conservation and numerical communication behave as specified. Biological scaling, dynamic extraction, basal endogenous secretion, C-peptide observations, graft physiology and independent domain review remain open.
