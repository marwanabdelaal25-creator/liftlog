"""A WorkSet — one logged set of an exercise (weight x reps, with optional RPE)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Dict, Optional
import uuid

from liftlog.errors import ValidationError
from liftlog import onerepmax


@dataclass
class WorkSet:
    exercise_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    weight: float = 0.0
    reps: int = 0
    rpe: Optional[float] = None          # rate of perceived exertion, 6-10
    is_warmup: bool = False
    unit: str = "kg"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValidationError("weight cannot be negative", field="weight")
        if self.reps < 0:
            raise ValidationError("reps cannot be negative", field="reps")
        if self.rpe is not None and not (0 <= self.rpe <= 10):
            raise ValidationError("RPE must be between 0 and 10", field="rpe")

    @classmethod
    def create(cls, exercise_id: str, **kwargs: Any) -> "WorkSet":
        sid = kwargs.pop("id", None) or str(uuid.uuid4())
        return cls(id=sid, exercise_id=exercise_id, **kwargs)

    def volume(self) -> float:
        """Tonnage of this set: weight x reps."""
        return round(self.weight * self.reps, 2)

    def e1rm(self, formula: str = "epley") -> float:
        """Estimated 1RM for this set."""
        if self.reps <= 0 or self.weight <= 0:
            return 0.0
        return onerepmax.estimate(self.weight, self.reps, formula)

    def is_working(self) -> bool:
        return not self.is_warmup and self.reps > 0 and self.weight > 0

    @property
    def workout_date(self) -> date:
        return datetime.fromisoformat(self.started_at[:19]).date()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkSet":
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__ if k in data or k == "exercise_id"})


Session = WorkSet  # older imports
