"""Frozen one-factor IV-001 conditions; no native imports or population assumptions."""

VARIANTS = (
    "baseline",
    "meal-half",
    "meal-one-half",
    "meal-early",
    "meal-late",
    "announcement-none",
    "announcement-half",
    "announcement-late",
    "gap-15",
    "gap-60",
    "gap-evening",
    "parameter-1-low",
    "parameter-1-high",
    "parameter-2-low",
    "parameter-2-high",
    "warmup-0",
    "warmup-48",
)
PARAMETERS = {
    "simglucose": (
        {
            "name": "kabs",
            "unit": "1/min",
            "meaning": "intestinal glucose absorption",
            "source": "patient/t1dpatient.py: native minute-based derivatives",
        },
        {
            "name": "kd",
            "unit": "1/min",
            "meaning": "subcutaneous insulin compartment transfer",
            "source": "patient/t1dpatient.py: native minute-based derivatives",
        },
    ),
    "lt1_cambridge": (
        {
            "name": "SIT",
            "unit": "1/min/mU/l",
            "meaning": "insulin sensitivity of distribution/transport",
            "source": "src/core/models/Cambridge.ts: native parameter description and unit string",
        },
        {
            "name": "tmaxG",
            "unit": "min",
            "meaning": "time-to-maximum of CHO absorption",
            "source": "src/core/models/Cambridge.ts: native parameter description",
        },
    ),
}


def parameter(cfg):
    variant = cfg.get("variant", "baseline")
    if not variant.startswith("parameter-"):
        return None
    _, index, level = variant.split("-")
    return PARAMETERS[cfg["engine"]][int(index) - 1] | {"factor": 0.9 if level == "low" else 1.1}


def available(cfg, minute):
    gap = {"gap-15": (720, 735), "gap-60": (720, 780), "gap-evening": (1080, 1110)}.get(
        cfg.get("variant")
    )
    return gap is None or not gap[0] <= minute - cfg["warmup"] < gap[1]


def change_meals(cfg, events):
    variant = cfg.get("variant")
    factor = {"meal-half": 0.5, "meal-one-half": 1.5}.get(variant, 1)
    shift = {"meal-early": -30, "meal-late": 30}.get(variant, 0)
    return [(t + shift, g * factor) if t >= cfg["warmup"] else (t, g) for t, g in events]


def announcements(cfg, events):
    variant = cfg.get("variant")
    fraction = {"announcement-none": 0, "announcement-half": 0.5}.get(variant, 1)
    delay = 15 if variant == "announcement-late" else 0
    return [
        (t + (delay if t >= cfg["warmup"] else 0), t, g * (fraction if t >= cfg["warmup"] else 1))
        for t, g in events
        if t < cfg["warmup"] or fraction
    ]


def boundary(cfg, events):
    gap = {"gap-15": (720, 735), "gap-60": (720, 780), "gap-evening": (1080, 1110)}.get(
        cfg.get("variant")
    )
    return {
        "meals": [list(x) for x in events],
        "announcements": [list(x) for x in announcements(cfg, events)],
        "gap": [x + cfg["warmup"] for x in gap] if gap else None,
        "parameter": parameter(cfg),
    }
