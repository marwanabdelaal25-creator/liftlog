"""Exercise entity — one movement you train (e.g. "Back Squat")."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Any, List, Optional
import uuid

from liftlog.validators import (
    require_non_empty,
    validate_wger,
    validate_load,
    validate_rating_value,
    validate_progress,
)
from liftlog.rating import Rating


class LiftStatus(str, Enum):
    LEARNING = "learning"        # still grooving the movement
    ACTIVE = "active"            # in the current program
    MAINTENANCE = "maintenance"  # kept in, not pushed
    RETIRED = "retired"          # no longer programmed
    BENCHED = "benched"          # parked (injury / deload)

    def __str__(self) -> str:
        return self.value


CATEGORIES = ("compound", "isolation", "olympic", "cardio", "mobility")


@dataclass
class Exercise:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    musclegroup_ids: list[str] = field(default_factory=list)
    wger: str | None = None
    equipment_id: str | None = None
    program_id: str | None = None
    program_index: float | None = None
    category: str = "compound"
    target_1rm: float | None = None     # strength goal for this lift
    best_1rm: float = 0.0               # best estimated 1RM logged so far
    unit: str = "kg"
    bodyweight: bool = False
    status: LiftStatus = LiftStatus.ACTIVE
    started_at: str | None = None       # first trained
    finished_at: str | None = None      # retired on
    added_at: str | None = None
    tag_ids: list[str] = field(default_factory=list)
    routine_ids: list[str] = field(default_factory=list)
    demo_url: str = ""
    description: str = ""
    source: str = "manual"
    notes_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    _rating_obj: Rating | None = field(default=None, repr=False, compare=False)
    _rating_val: float | None = field(default=None, repr=False, compare=False)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Exercise":
        kw = dict(kwargs)
        if "status" in kw and not isinstance(kw["status"], LiftStatus):
            kw["status"] = LiftStatus(str(kw["status"]))
        eid = kw.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(name=name, id=eid, **kw)

    @classmethod
    def quick(cls, name: str, **kwargs: Any) -> "Exercise":
        return cls.create(name, **kwargs)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")
        self.wger = validate_wger(self.wger)
        if self.target_1rm is not None:
            validate_load(self.best_1rm, self.target_1rm)
        if isinstance(self.status, str):
            self.status = LiftStatus(self.status)

    @property
    def rating(self) -> Rating | None:
        if self._rating_obj is not None:
            return self._rating_obj
        if self._rating_val is not None:
            return Rating.create(self.id, value=self._rating_val)
        return None

    @rating.setter
    def rating(self, val: Rating | float | int | None) -> None:
        self._rating_obj = None
        self._rating_val = None
        if val is None:
            return
        if isinstance(val, Rating):
            self._rating_obj = val
        else:
            self._rating_val = validate_rating_value(float(val))

    @property
    def rating_value(self) -> float | None:
        if self._rating_obj is not None:
            return self._rating_obj.value
        return self._rating_val

    @rating_value.setter
    def rating_value(self, val: float | int | None) -> None:
        self.rating = val

    def progress_pct(self) -> float:
        """How close best_1rm is to the target_1rm goal."""
        if not self.target_1rm:
            return 0.0
        pct = 100.0 * self.best_1rm / self.target_1rm
        return validate_progress(min(100.0, pct))

    @property
    def progress(self) -> float:
        return self.progress_pct()

    def set_targets(self, best: float, target: float | None = None) -> None:
        if target is not None:
            self.target_1rm = target
        validate_load(best, self.target_1rm)
        self.best_1rm = best

    def update_best(self, estimated_1rm: float) -> bool:
        """Bump best_1rm if a new set beats it. Returns True on a new PR."""
        if estimated_1rm > self.best_1rm:
            self.best_1rm = round(estimated_1rm, 1)
            return True
        return False

    def gap_to_target(self) -> Optional[float]:
        if self.target_1rm is None:
            return None
        return round(self.target_1rm - self.best_1rm, 1)

    def at_goal(self) -> bool:
        return self.target_1rm is not None and self.best_1rm >= self.target_1rm

    # --- status transitions ---
    def mark_active(self, when: date | None = None) -> None:
        self.status = LiftStatus.ACTIVE
        self.started_at = self.started_at or (when or date.today()).isoformat()

    def mark_retired(self, when: date | None = None) -> None:
        self.status = LiftStatus.RETIRED
        self.finished_at = (when or date.today()).isoformat()

    def mark_done(self, when: date | None = None) -> None:
        self.mark_retired(when)

    def bench(self, when: date | None = None) -> None:
        self.status = LiftStatus.BENCHED

    def set_status(self, status: LiftStatus | str) -> None:
        self.status = LiftStatus(status) if isinstance(status, str) else status

    def short_label(self) -> str:
        return self.name[:60]

    def summary_line(self) -> str:
        best = (" best %g%s" % (self.best_1rm, self.unit)) if self.best_1rm else ""
        return "{name} | {st}{best}".format(name=self.short_label(), st=self.status.value, best=best)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("_rating_obj", "_rating_val"):
            d.pop(k, None)
        d["status"] = self.status.value
        if self._rating_obj is not None:
            d["rating"] = self._rating_obj.to_dict()
        elif self._rating_val is not None:
            d["rating"] = self._rating_val
        else:
            d["rating"] = None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Exercise":
        kw: dict[str, Any] = {}
        fields = cls.__dataclass_fields__
        for key, val in data.items():
            if key == "rating":
                continue
            if key in fields:
                kw[key] = val
        if "status" in kw and not isinstance(kw["status"], LiftStatus):
            kw["status"] = LiftStatus(str(kw["status"]))
        ex = cls(**{k: kw[k] for k in kw if k in fields})
        rating_raw = data.get("rating")
        if isinstance(rating_raw, dict):
            ex._rating_obj = Rating.from_dict(rating_raw)
        elif rating_raw is not None:
            ex._rating_val = validate_rating_value(float(rating_raw))
        return ex

    def matches(self, query: str) -> bool:
        q = query.lower()
        if q in self.name.lower():
            return True
        if self.category and q in self.category.lower():
            return True
        if self.wger and q in self.wger:
            return True
        return False

    def matches_query(self, query: str) -> bool:
        q = query.lower()
        for hay in (self.name, self.category, self.description):
            if hay and q in hay.lower():
                return True
        if self.wger and q in self.wger:
            return True
        return False

    def is_active(self) -> bool:
        return self.status in (LiftStatus.ACTIVE, LiftStatus.MAINTENANCE)

    def days_active(self) -> Optional[int]:
        if not self.started_at:
            return None
        start = date.fromisoformat(self.started_at[:10])
        end = date.today()
        if self.finished_at:
            end = date.fromisoformat(self.finished_at[:10])
        return max(0, (end - start).days)

    def onerm_gap(self) -> Optional[float]:
        return self.gap_to_target()


class ExerciseCatalog:
    """Query helpers over an exercise list — no storage dependency."""

    def __init__(self, exercises: List[Exercise]):
        self.exercises = exercises

    def by_status(self, status: LiftStatus | str) -> List[Exercise]:
        st = LiftStatus(status) if isinstance(status, str) else status
        return [e for e in self.exercises if e.status == st]

    def by_musclegroup(self, musclegroup_id: str) -> List[Exercise]:
        return [e for e in self.exercises if musclegroup_id in e.musclegroup_ids]

    def active(self) -> List[Exercise]:
        return [e for e in self.exercises if e.status == LiftStatus.ACTIVE]

    def unretired(self) -> List[Exercise]:
        return [e for e in self.exercises if e.status != LiftStatus.RETIRED]

    def by_category(self, category: str) -> List[Exercise]:
        c = category.lower()
        return [e for e in self.exercises if e.category.lower() == c]

    def at_goal(self) -> List[Exercise]:
        return [e for e in self.exercises if e.at_goal()]

    def recently_retired(self, n: int = 10) -> List[Exercise]:
        done = [e for e in self.exercises if e.finished_at]
        done.sort(key=lambda e: e.finished_at or "", reverse=True)
        return done[:n]

    def sort_by_name(self) -> List[Exercise]:
        return sorted(self.exercises, key=lambda e: e.name.lower())

    def sort_by_progress(self) -> List[Exercise]:
        return sorted(self.exercises, key=lambda e: e.progress_pct(), reverse=True)

    def with_wger(self) -> List[Exercise]:
        return [e for e in self.exercises if e.wger]

    def group_by_status(self) -> dict[LiftStatus, List[Exercise]]:
        out: dict[LiftStatus, List[Exercise]] = {}
        for e in self.exercises:
            out.setdefault(e.status, []).append(e)
        return out

    def summary(self) -> str:
        lines = ["Exercises (%d)" % len(self.exercises)]
        groups = self.group_by_status()
        for st in LiftStatus:
            if st in groups:
                lines.append("  %s: %d" % (st.value, len(groups[st])))
        return "\n".join(lines)
