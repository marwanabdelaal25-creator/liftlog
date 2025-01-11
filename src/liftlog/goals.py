"""Training goals — sets, volume, or sessions over a period."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
import uuid

from liftlog.exercise import Exercise, LiftStatus
from liftlog.workset import WorkSet


@dataclass
class LiftGoal:
    id: str
    name: str
    goal_type: str  # exercises | target_1rm | minutes
    target: int
    period: str  # year | month | week
    start_date: str
    end_date: str
    progress: int = 0
    completed: bool = False
    recurring_id: Optional[str] = None

    @classmethod
    def create(cls, name: str, goal_type: str, target: int, period: str, **kw: Any) -> "LiftGoal":
        gid = kw.pop("id", None) or str(uuid.uuid4())
        today = date.today()
        if period == "year":
            start = date(today.year - 1, 1, 1)
            end = date(today.year, 12, 31)
        elif period == "month":
            start = today.replace(day=1)
            nxt = (start + timedelta(days=32)).replace(day=1)
            end = nxt - timedelta(days=1)
        else:
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        return cls(
            id=gid,
            name=name,
            goal_type=goal_type,
            target=target,
            period=period,
            start_date=kw.get("start_date", start.isoformat()),
            end_date=kw.get("end_date", end.isoformat()),
            **{k: v for k, v in kw.items() if k not in ("start_date", "end_date")},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LiftGoal":
        return cls(**{f: data.get(f) for f in cls.__dataclass_fields__})  # type: ignore

    def pct_complete(self) -> float:
        if self.target <= 0:
            return 100.0
        return min(100.0, 100.0 * self.progress / self.target)

    def in_range(self, d: date) -> bool:
        s = date.fromisoformat(self.start_date)
        e = date.fromisoformat(self.end_date)
        return s <= d <= e

    def days_left(self) -> int:
        end = date.fromisoformat(self.end_date)
        return max(0, (end - date.today()).days)

    def pace_needed(self) -> float:
        """Units per day required to hit target by end_date."""
        left = self.days_left()
        remaining = max(0, self.target - self.progress)
        if left <= 0:
            return float(remaining)
        return round(remaining / left, 2)


class GoalsManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def list_goals(self) -> List[LiftGoal]:
        raw = self.storage.raw_get("goals") or []
        return [LiftGoal.from_dict(g) for g in raw]

    def save_goals(self, goals: List[LiftGoal]) -> None:
        self.storage.raw_set("goals", [g.to_dict() for g in goals])

    def add_goal(self, goal: LiftGoal) -> None:
        gs = self.list_goals()
        gs.append(goal)
        self.save_goals(gs)

    def get(self, goal_id: str) -> LiftGoal:
        for g in self.list_goals():
            if g.id == goal_id:
                return g
        from liftlog.errors import NotFoundError

        raise NotFoundError("goal", goal_id)

    def delete(self, goal_id: str) -> None:
        gs = [g for g in self.list_goals() if g.id != goal_id]
        if len(gs) == len(self.list_goals()):
            from liftlog.errors import NotFoundError

            raise NotFoundError("goal", goal_id)
        self.save_goals(gs)

    def compute_progress(self, goal: LiftGoal) -> int:
        exercises = self.storage.list_exercises()
        worksets = self.storage.list_worksets()
        s = date.fromisoformat(goal.start_date)
        e = date.fromisoformat(goal.end_date)

        in_window = [w for w in worksets if s <= w.workout_date <= e]

        if goal.goal_type == "volume":
            return int(round(sum(w.volume() for w in in_window)))

        if goal.goal_type == "sessions":
            return len({w.workout_date for w in in_window})

        # default ("sets"): number of worksets logged in the window
        return len(in_window)

    def refresh_all(self) -> List[LiftGoal]:
        updated = []
        for g in self.list_goals():
            g.progress = self.compute_progress(g)
            g.completed = g.progress >= g.target
            updated.append(g)
        self.save_goals(updated)
        return updated

    def active_goals(self) -> List[LiftGoal]:
        today = date.today()
        return [g for g in self.list_goals() if g.in_range(today) and not g.completed]

    def summary_line(self, goal: LiftGoal) -> str:
        return "{name}: {p}/{t} ({pct:.0f}%) need {pace}/day".format(
            name=goal.name,
            p=goal.progress,
            t=goal.target,
            pct=goal.pct_complete(),
            pace=goal.pace_needed(),
        )


Goal = LiftGoal  # alias for older imports
