"""One-rep-max estimation and rep/percentage tables.

Several published formulas estimate a 1RM from a weight lifted for ``reps``
reps. They disagree (especially past ~10 reps), so we expose each one plus an
average. All take a weight in whatever unit you track (kg or lb) and an integer
rep count, and return an estimated 1RM in the same unit.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List

# Past this many reps the linear formulas fall apart; clamp for sanity.
MAX_REPS = 36


def _clamp_reps(reps: int) -> int:
    return max(1, min(int(reps), MAX_REPS - 1))


def epley(weight: float, reps: int) -> float:
    """Epley (1985): w * (1 + reps/30). The most common gym-calculator default."""
    r = _clamp_reps(reps)
    if r == 1:
        return float(weight)
    return weight * (1 + r / 30.0)


def brzycki(weight: float, reps: int) -> float:
    """Brzycki: w * 36 / (37 - reps). Tracks Epley closely up to ~10 reps."""
    r = _clamp_reps(reps)
    return weight * 36.0 / (37.0 - r)


def lombardi(weight: float, reps: int) -> float:
    """Lombardi: w * reps^0.10."""
    r = _clamp_reps(reps)
    return weight * (r ** 0.10)


def mcglothin(weight: float, reps: int) -> float:
    """McGlothin/Landers: 100*w / (101.3 - 2.67123*reps)."""
    r = _clamp_reps(reps)
    return 100.0 * weight / (101.3 - 2.67123 * r)


def wathan(weight: float, reps: int) -> float:
    """Wathan: 100*w / (48.8 + 53.8 * e^(-0.075*reps))."""
    r = _clamp_reps(reps)
    return 100.0 * weight / (48.8 + 53.8 * math.exp(-0.075 * r))


FORMULAS: Dict[str, Callable[[float, int], float]] = {
    "epley": epley,
    "brzycki": brzycki,
    "lombardi": lombardi,
    "mcglothin": mcglothin,
    "wathan": wathan,
}


def estimate(weight: float, reps: int, formula: str = "epley") -> float:
    fn = FORMULAS.get(formula.lower(), epley)
    return round(fn(weight, reps), 1)


def average_1rm(weight: float, reps: int) -> float:
    """Mean of all five formulas — steadier than any single one."""
    vals = [fn(weight, reps) for fn in FORMULAS.values()]
    return round(sum(vals) / len(vals), 1)


def all_estimates(weight: float, reps: int) -> Dict[str, float]:
    return {name: round(fn(weight, reps), 1) for name, fn in FORMULAS.items()}


def percent_of_1rm(one_rm: float, reps: int) -> float:
    """Weight you should be able to lift for ``reps`` reps, via inverse Epley."""
    r = _clamp_reps(reps)
    if r <= 1:
        return round(float(one_rm), 1)
    return round(one_rm / (1 + r / 30.0), 1)


def rep_max_table(one_rm: float, max_reps: int = 12) -> Dict[int, float]:
    """Estimated working weights for 1..max_reps reps."""
    return {r: percent_of_1rm(one_rm, r) for r in range(1, max_reps + 1)}


def percent_table(one_rm: float, percents: List[int] | None = None) -> Dict[int, float]:
    pts = percents or [50, 60, 65, 70, 75, 80, 85, 90, 95]
    return {p: round(one_rm * p / 100.0, 1) for p in pts}


def estimate_reps(weight: float, one_rm: float) -> int:
    """Roughly how many reps ``weight`` is good for, given a 1RM (inverse Epley)."""
    if weight <= 0 or one_rm <= 0 or weight >= one_rm:
        return 1
    return max(1, round(30.0 * (one_rm / weight - 1)))


def training_max(one_rm: float, pct: float = 0.90) -> float:
    """5/3/1-style training max: a fraction of the true/estimated 1RM."""
    return round(one_rm * pct, 1)


def relative_intensity(weight: float, one_rm: float) -> float:
    """The %1RM a given working weight represents."""
    if one_rm <= 0:
        return 0.0
    return round(100.0 * weight / one_rm, 1)
