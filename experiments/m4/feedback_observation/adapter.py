"""One-time, molar pancreatic-appearance boundary; no kinetic runtime imports."""

from experiments.m4.feedback.contract import number
from experiments.m4.kinetic_inlet.forcing import from_source_samples
from experiments.m4.paired_kinetics.report import matrix


def prepare(p, data, *, step=0.25, signal="pancreatic", scale=1.0):
    if data.get("status") != "completed" or data.get("failure") is not None:
        raise ValueError("A completed parent trajectory is required")
    times = [i * 0.25 for i in range(961)]
    if data["times"] != times or step not in p["diagnostics"]["source_sampling_steps_min"]:
        raise ValueError("Wrong or incomplete source time grid")
    if (
        signal not in ("pancreatic", "liver_fault")
        or isinstance(scale, bool)
        or scale not in (1.0, *p["diagnostics"]["appearance_volume_scales"])
    ):
        raise ValueError("Unsupported boundary or scale diagnostic")
    rates = matrix(data["source_rates"], len(times), 2)
    column = 0 if signal == "pancreatic" else 1
    values = [number(r[column]) * scale for r in rates]
    stride = round(step / 0.25)
    forcing = from_source_samples(times[::stride], values[::stride])
    params = p["cpeptide"]["parameters"].copy()
    params["volume_l_kg"] *= scale
    basal = number(data["baseline"]["Sb_pmol_kg_min"]) * scale
    central = basal / params["k3"]
    initial = [central, params["k1"] / params["k2"] * central, 0.0, 0.0]
    return {
        "times": times,
        "signal": signal,
        "step_min": step,
        "appearance_scale": scale,
        "forcing": forcing.to_dict(),
        "parameters": params,
        "initial": initial,
        "basal_pmol_kg_min": basal,
    }


def diagnostic_inputs(p, reference, tight):
    return {
        "parent_tight": prepare(p, tight),
        "sampling_1": prepare(p, reference, step=1),
        "sampling_0.5": prepare(p, reference, step=0.5),
        "liver_fault": prepare(p, reference, signal="liver_fault"),
        "scale_0.5": prepare(p, reference, scale=0.5),
        "scale_2": prepare(p, reference, scale=2),
    }
