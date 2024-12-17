"""Daily workset streak tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from liftlog.exercise import LiftStatus
from liftlog.storage import JsonStorage


@dataclass
class StreakInfo:
    current: int
    longest: int
    last_active: str | None
    active_days: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        if self.current == 0:
            return "No active streak (best %d days)" % self.longest
        return "Streak: {0} days (best {1})".format(self.current, self.longest)


def active_dates(storage: JsonStorage) -> set[date]:
    ds: set[date] = set()
    for s in storage.list_worksets():
        if s.volume() > 0:
            ds.add(s.workout_date)
    for b in storage.list_exercises():
        if b.finished_at:
            try:
                ds.add(date.fromisoformat(b.finished_at[:10]))
            except ValueError:
                pass
    return ds


def current_streak(storage: JsonStorage, today: date | None = None) -> int:
    td = today or date.today()
    days = active_dates(storage)
    if td not in days and (td - timedelta(days=1)) not in days:
        return 0
    cur = td if td in days else td - timedelta(days=1)
    streak = 0
    while cur in days:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def longest_streak(storage: JsonStorage) -> int:
    days = sorted(active_dates(storage))
    if not days:
        return 0
    best = run = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def compute_streak(storage: JsonStorage) -> StreakInfo:
    ds = sorted(active_dates(storage))
    day_strs = [d.isoformat() for d in ds]
    return StreakInfo(
        current=current_streak(storage),
        longest=longest_streak(storage),
        last_active=day_strs[-1] if day_strs else None,
        active_days=day_strs,
    )


def streak_summary(storage: JsonStorage) -> str:
    return compute_streak(storage).as_text()
