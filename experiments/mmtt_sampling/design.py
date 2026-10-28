"""Method-independent OT-055 schedule selection, before observation analysis.

No interpolation, kinetic estimation or participant-specific fit state belongs here.
"""

import math
from copy import deepcopy

from experiments.observation_analysis.observations import identifier

SCHEMA = "opent1d.mmtt-sampling-design/1"


def times(value):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("A schedule needs at least the observed 0 and 120 minute samples")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in value):
        raise ValueError("Sample times must be finite numbers")
    if any(not 0 <= x <= 120 or not math.isfinite(x) for x in value):
        raise ValueError("Sample times must be finite numbers within 0–120 minutes")
    if value != sorted(set(value)) or value[0] != 0 or value[-1] != 120:
        raise ValueError("Use unique increasing actual times, with endpoints 0 and 120")
    return tuple(value)


def validate_design(design):
    """Validate a design frozen on development identities, never held-out values."""
    if not isinstance(design, dict) or set(design) != {
        "schema",
        "scope",
        "window_minutes",
        "allocation",
        "selection_participants",
        "selection_rationale",
        "full_times_minutes",
        "subsets",
    }:
        raise ValueError("Unexpected sampling design fields")
    if design["schema"] != SCHEMA or design["scope"] != "synthetic-preparation":
        raise ValueError("Only the versioned synthetic preparation design is implemented")
    if times(design["window_minutes"]) != (0, 120):
        raise ValueError("OT-055 retains the same observed 0–120 minute endpoint")
    allocation = design["allocation"]
    if not isinstance(allocation, dict) or not allocation:
        raise ValueError("A participant allocation is required")
    if any(not isinstance(p, str) or not p.strip() for p in allocation):
        raise ValueError("Use nonempty participant identities")
    for participant in allocation:
        identifier(participant, "sampling participant id")
    if any(not isinstance(value, str) for value in allocation.values()) or set(
        allocation.values()
    ) != {"development", "evaluation"}:
        raise ValueError("Both development and held-out evaluation participants are required")
    selection = design["selection_participants"]
    if (
        not isinstance(selection, list)
        or not selection
        or any(not isinstance(p, str) for p in selection)
        or len(selection) != len(set(selection))
        or any(allocation.get(p) != "development" for p in selection)
    ):
        raise ValueError("Choose schedules using development participants only")
    if (
        not isinstance(design["selection_rationale"], str)
        or not design["selection_rationale"].strip()
    ):
        raise ValueError("Record the development selection rationale")
    full = times(design["full_times_minutes"])
    subsets = design["subsets"]
    if not isinstance(subsets, dict) or len(subsets) not in (2, 3):
        raise ValueError("Freeze two or three reduced schedules")
    if any(not isinstance(name, str) or not name.strip() or name == "full" for name in subsets):
        raise ValueError("Use named reduced schedules; full is reserved")
    for name in subsets:
        identifier(name, "sampling schedule id")
    seen = set()
    for subset in subsets.values():
        subset = times(subset)
        if not set(subset) < set(full):
            raise ValueError("Reduced schedules must be proper subsets of actual full times")
        if subset in seen:
            raise ValueError("Reduced schedules must be distinct")
        seen.add(subset)
    return deepcopy(design)


def retained_indices(actual_times, schedule):
    """Select actual observations only; no nearest-time match or interpolation."""
    actual = times(actual_times)
    requested = times(schedule)
    if not set(requested) <= set(actual):
        raise ValueError("A requested time was not actually observed in this visit")
    return tuple(i for i, time in enumerate(actual) if time in requested)


def project_samples(samples, schedule, *, time_key="time_minutes"):
    """Copy retained rows before calling the shared estimator, without fit state.

    The caller supplies raw rows for exactly one visit. Non-sample metadata and
    all estimator parameters must come from the shared core's independently
    frozen analysis plan, never a full-curve participant fit.
    """
    indices = retained_indices([sample[time_key] for sample in samples], schedule)
    return [deepcopy(samples[i]) for i in indices]


def validate_development_times(design, visits):
    """Check schedule support using times only, before held-out data access.

    This bounded design requires exactly two linked visits on the full schedule.
    Later execution still has to check every evaluation visit independently.
    """
    design = validate_design(design)
    if not isinstance(visits, list) or not visits:
        raise ValueError("Supply a development-only visit-time inventory")
    observed = {}
    for visit in visits:
        if not isinstance(visit, dict) or set(visit) != {
            "participant_id",
            "visit_id",
            "times_minutes",
        }:
            raise ValueError("Inventory rows contain only participant, visit and actual times")
        participant, identity = visit["participant_id"], visit["visit_id"]
        if not isinstance(participant, str) or participant not in design["selection_participants"]:
            raise ValueError(
                "Selection inventory must contain development selection participants only"
            )
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("A visit identity is required")
        if times(visit["times_minutes"]) != times(design["full_times_minutes"]):
            raise ValueError("Development visit must support the declared full observed schedule")
        identities = observed.setdefault(participant, set())
        if identity in identities:
            raise ValueError("Duplicate participant/visit identity")
        identities.add(identity)
    if set(observed) != set(design["selection_participants"]):
        raise ValueError("Missing development selection participant")
    if any(len(identities) != 2 for identities in observed.values()):
        raise ValueError("Keep exactly two linked visits per development participant")
    return deepcopy(visits)
