#!/usr/bin/env python3
"""Build a small 2025 training history and print the year-in-review summary."""
from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from liftlog.exercise import Exercise, LiftStatus
from liftlog.reports import ReportBuilder
from liftlog.storage import JsonStorage
from liftlog.workset import WorkSet

LIFTS = [
    ("Back Squat", 180.0),
    ("Bench Press", 120.0),
    ("Deadlift", 220.0),
    ("Overhead Press", 80.0),
]


def main() -> None:
    store = JsonStorage(Path(tempfile.mkdtemp()) / "library.json")
    store.load()
    for name, target in LIFTS:
        ex = Exercise.create(name, category="compound", target_1rm=target, status=LiftStatus.ACTIVE)
        store.upsert_exercise(ex)
        # a block of weekly top sets through 2025
        for wk in range(8):
            d = date(2025, 1, 7) + timedelta(days=wk * 7)
            w = round(target * 0.7 + wk * 2.5, 1)
            sett = WorkSet.create(ex.id, weight=w, reps=5, rpe=8.0,
                                  started_at=d.isoformat() + "T18:00:00")
            store.add_workset(sett)
            ex.update_best(sett.e1rm())
        store.upsert_exercise(ex)
    store.save()

    print(ReportBuilder(store).yearly_summary(2025))


if __name__ == "__main__":
    main()
