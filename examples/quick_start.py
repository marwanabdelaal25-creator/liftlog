#!/usr/bin/env python3
"""30-second smoke test: build a tiny log, log a set, print an estimated 1RM."""
from __future__ import annotations

import tempfile
from pathlib import Path

from liftlog.musclegroup import MuscleGroup
from liftlog.exercise import Exercise, LiftStatus
from liftlog.rating import Rating
from liftlog.storage import JsonStorage
from liftlog.workset import WorkSet


def main() -> None:
    path = Path(tempfile.mkdtemp()) / "library.json"
    store = JsonStorage(path)
    store.load()

    quads = MuscleGroup.create("Quadriceps")
    store.upsert_musclegroup(quads)

    squat = Exercise.create(
        "Back Squat",
        wger="615",
        category="compound",
        target_1rm=180.0,
        status=LiftStatus.ACTIVE,
    )
    squat.musclegroup_ids = [quads.id]
    store.upsert_exercise(squat)

    # log a top set; the estimated 1RM updates the exercise's best
    sett = WorkSet.create(squat.id, weight=140.0, reps=5, rpe=8.0,
                          started_at="2026-03-01T18:00:00")
    store.add_workset(sett)
    squat.update_best(sett.e1rm())
    store.upsert_exercise(squat)
    store.add_rating(Rating.create(squat.id, value=5.0, review="Money lift"))
    store.save()

    print("saved log to", store.path)
    print("  %s -> e1RM %g, best %g, %.0f%% to goal" % (
        squat.name, sett.e1rm(), squat.best_1rm, squat.progress_pct()))


if __name__ == "__main__":
    main()
