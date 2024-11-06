"""Barbell plate math: what to hang on the bar for a target weight."""

from __future__ import annotations

from typing import Dict, List

# Standard calibrated plate sets (one side worth — you load both).
PLATES_KG = [25.0, 20.0, 15.0, 10.0, 5.0, 2.5, 1.25]
PLATES_LB = [45.0, 35.0, 25.0, 10.0, 5.0, 2.5]
BAR_KG = 20.0
BAR_LB = 45.0


def _plates_for(unit: str) -> tuple[list[float], float]:
    if unit.lower() in ("lb", "lbs", "pound", "pounds"):
        return PLATES_LB, BAR_LB
    return PLATES_KG, BAR_KG


def plate_breakdown(target: float, bar: float | None = None, unit: str = "kg",
                    plates: List[float] | None = None) -> List[float]:
    """Greedy plates *per side* to reach ``target`` (bar included).

    Returns the plates loaded on one side, largest first. If the target can't be
    hit exactly with the available plates, it gets as close as possible without
    going over.
    """
    avail, default_bar = _plates_for(unit)
    plates = sorted(plates or avail, reverse=True)
    bar = default_bar if bar is None else bar
    if target <= bar:
        return []
    per_side = (target - bar) / 2.0
    out: List[float] = []
    remaining = per_side
    for p in plates:
        while remaining >= p - 1e-9:
            out.append(p)
            remaining -= p
    return out


def total_from_plates(per_side: List[float], bar: float | None = None, unit: str = "kg") -> float:
    _, default_bar = _plates_for(unit)
    bar = default_bar if bar is None else bar
    return round(bar + 2 * sum(per_side), 2)


def closest_loadable(target: float, bar: float | None = None, unit: str = "kg",
                     plates: List[float] | None = None) -> float:
    """The achievable weight nearest to (and not above) ``target``."""
    per_side = plate_breakdown(target, bar, unit, plates)
    return total_from_plates(per_side, bar, unit)


def is_loadable(target: float, bar: float | None = None, unit: str = "kg",
                plates: List[float] | None = None) -> bool:
    return abs(closest_loadable(target, bar, unit, plates) - target) < 1e-6


def format_loading(per_side: List[float]) -> str:
    if not per_side:
        return "(empty bar)"
    return " + ".join(_fmt(p) for p in per_side)


def _fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else ("%g" % x)


def warmup_scheme(working: float, sets: int = 4, bar: float | None = None,
                  unit: str = "kg") -> List[float]:
    """A ramp of warmup weights up to (but not including) the working set."""
    if sets <= 0:
        return []
    fracs = [0.4, 0.55, 0.7, 0.85, 0.925][:sets]
    out = []
    for f in fracs:
        out.append(closest_loadable(working * f, bar, unit))
    return out


def loading_plan(target: float, bar: float | None = None, unit: str = "kg") -> Dict[str, object]:
    per_side = plate_breakdown(target, bar, unit)
    achieved = total_from_plates(per_side, bar, unit)
    return {
        "target": target,
        "achieved": achieved,
        "per_side": per_side,
        "loading": format_loading(per_side),
        "exact": abs(achieved - target) < 1e-6,
    }
