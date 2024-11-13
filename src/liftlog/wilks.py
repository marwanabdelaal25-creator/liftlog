"""Bodyweight-adjusted strength scores (Wilks and DOTS).

Both turn a powerlifting total (or any total kg) plus a lifter's bodyweight into
a single number you can compare across weight classes. Coefficients are the
published ones; everything is in kilograms.
"""

from __future__ import annotations

# Original Wilks coefficients.
_WILKS_MALE = (-216.0475144, 16.2606339, -0.002388645, -0.00113732, 7.01863e-06, -1.291e-08)
_WILKS_FEMALE = (594.31747775582, -27.23842536447, 0.82112226871, -0.00930733913, 4.731582e-05, -9.054e-08)

# DOTS (2020) coefficients: A*bw^4 + B*bw^3 + C*bw^2 + D*bw + E.
_DOTS_MALE = (-0.000001093, 0.0007391293, -0.1918759221, 24.0900756, -307.75076)
_DOTS_FEMALE = (-0.0000010706, 0.0005158568, -0.1126655495, 13.6175032, -57.96288)


def _is_female(sex: str) -> bool:
    return sex.lower() in ("f", "female", "woman", "w")


def wilks_score(bodyweight: float, total: float, sex: str = "male") -> float:
    """Classic Wilks coefficient * total."""
    if bodyweight <= 0 or total <= 0:
        return 0.0
    a, b, c, d, e, f = _WILKS_FEMALE if _is_female(sex) else _WILKS_MALE
    bw = float(bodyweight)
    denom = a + b * bw + c * bw**2 + d * bw**3 + e * bw**4 + f * bw**5
    if denom == 0:
        return 0.0
    return round(total * 500.0 / denom, 2)


def dots_score(bodyweight: float, total: float, sex: str = "male") -> float:
    """DOTS score — the IPF's successor to Wilks for cross-bodyweight comparison."""
    if bodyweight <= 0 or total <= 0:
        return 0.0
    A, B, C, D, E = _DOTS_FEMALE if _is_female(sex) else _DOTS_MALE
    bw = float(bodyweight)
    denom = A * bw**4 + B * bw**3 + C * bw**2 + D * bw + E
    if denom == 0:
        return 0.0
    return round(total * 500.0 / denom, 2)


def classify(score: float) -> str:
    """A rough strength-level label for a Wilks/DOTS score."""
    if score <= 0:
        return "untrained"
    if score < 200:
        return "beginner"
    if score < 300:
        return "intermediate"
    if score < 400:
        return "advanced"
    if score < 500:
        return "elite"
    return "world-class"


def total(*lifts: float) -> float:
    """Sum the contributing lifts (e.g. squat + bench + deadlift)."""
    return round(sum(x for x in lifts if x and x > 0), 2)
