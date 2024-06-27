"""Star ratings and aggregates."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

from liftlog.validators import validate_rating_value

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Rating:
    id: str
    exercise_id: str
    value: float
    review: str = ""
    created_at: str = ""
    source: str = "manual"

    def __post_init__(self) -> None:
        self.value = validate_rating_value(self.value)
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    @property
    def score(self) -> float:
        return self.value

    @classmethod
    def create(cls, exercise_id: str, value: float = 0.0, **kwargs: Any) -> "Rating":
        if "score" in kwargs:
            value = float(kwargs.pop("score"))
        rid = kwargs.pop("id", None) or str(uuid.uuid4())
        return cls(id=rid, exercise_id=exercise_id or "", value=value, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rating":
        return cls(
            id=data["id"],
            exercise_id=data["exercise_id"],
            value=float(data.get("value", data.get("score", 0))),
            review=data.get("review", ""),
            created_at=data.get("created_at", ""),
            source=data.get("source", "manual"),
        )

    def stars_display(self) -> str:
        full = int(self.value)
        half = 1 if self.value - full >= 0.5 else 0
        empty = 5 - full - half
        return ("★" * full) + ("½" if half else "") + ("☆" * empty)

    def summary(self) -> str:
        return "{0}/5 {1}".format(self.value, self.stars_display())


def average_rating(ratings: List[Rating]) -> Optional[float]:
    if not ratings:
        return None
    s = sum(r.value for r in ratings)
    return round(s / len(ratings), 2)


def histogram(ratings: List[Rating]) -> Dict[int, int]:
    h = {i: 0 for i in range(6)}
    for r in ratings:
        bucket = int(round(r.value))
        bucket = max(0, min(5, bucket))
        h[bucket] += 1
    return h


class RatingsManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def rate(self, exercise_id: str, value: float, review: str = "") -> Rating:
        r = Rating.create(exercise_id, value, review=review)
        self.storage.add_rating(r)
        return r

    def for_exercise(self, exercise_id: str) -> List[Rating]:
        return self.storage.list_ratings(exercise_id)

    def latest_for_exercise(self, exercise_id: str) -> Optional[Rating]:
        rs = self.for_exercise(exercise_id)
        if not rs:
            return None
        rs.sort(key=lambda r: r.created_at, reverse=True)
        return rs[0]

    def distribution(self) -> Dict[int, int]:
        return histogram(self.storage.list_ratings())

    def top_rated(self, n: int = 10) -> List[tuple[str, float]]:
        exercises = self.storage.list_exercises()
        scored = [(b.id, b.name, b.rating_value) for b in exercises if b.rating_value is not None]
        scored.sort(key=lambda x: x[2], reverse=True)
        return [(t, v) for _, t, v in scored[:n]]

    def report(self) -> str:
        avg = average_rating(self.storage.list_ratings())
        lines = ["=== Ratings ==="]
        if avg is not None:
            lines.append("Average: %.2f" % avg)
        dist = self.distribution()
        for star in range(5, -1, -1):
            if dist[star]:
                lines.append("  %d★: %d" % (star, dist[star]))
        return "\n".join(lines)
