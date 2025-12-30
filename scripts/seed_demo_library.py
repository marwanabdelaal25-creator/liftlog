#!/usr/bin/env python3
"""Seed a small demo log + a curated sample_library.json via the real API.

Building these through ``JsonStorage`` (rather than hand-writing JSON) keeps the
fixtures honest: whatever schema the app saves today is exactly what lands on
disk here.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from liftlog.musclegroup import MuscleGroup
from liftlog.exercise import Exercise, LiftStatus
from liftlog.goals import LiftGoal
from liftlog.rating import Rating
from liftlog.storage import JsonStorage
from liftlog.tag import Tag
from liftlog.workset import WorkSet

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
DEMO = FIX / "demo"

# (name, muscle, category, wger, best, target, status, rating)
CURATED = [
    ("Back Squat", "Quadriceps", "compound", "615", 162.5, 180.0, "active", 5.0),
    ("Bench Press", "Chest", "compound", "73", 110.0, 120.0, "active", 4.5),
    ("Deadlift", "Back", "compound", "105", 200.0, 220.0, "active", 5.0),
    ("Overhead Press", "Shoulders", "compound", None, 70.0, 80.0, "active", 4.0),
    ("Barbell Row", "Back", "compound", None, 100.0, 110.0, "maintenance", 4.0),
    ("Pull-up", "Back", "compound", None, 0.0, None, "active", 4.5),
    ("Romanian Deadlift", "Hamstrings", "compound", None, 140.0, 160.0, "active", None),
    ("Leg Press", "Quadriceps", "compound", None, 300.0, None, "retired", 3.0),
]


def _build_sample() -> None:
    path = FIX / "sample_library.json"
    if path.exists():
        path.unlink()
    st = JsonStorage(path)
    st.load()
    groups: dict[str, str] = {}
    tag_main = Tag.create("main-lift", id="tag-main", color="#7b1e3a")
    tag_acc = Tag.create("accessory", id="tag-acc", color="#2d6a4f")
    st.upsert_tag(tag_main)
    st.upsert_tag(tag_acc)
    rng = random.Random(11)
    for i, row in enumerate(CURATED):
        name, muscle, category, wger, best, target, status, rating = row
        if muscle not in groups:
            mg = MuscleGroup.create(muscle, id=f"mg-{i:02d}")
            st.upsert_musclegroup(mg)
            groups[muscle] = mg.id
        ex = Exercise.create(
            name, id=f"ex-{i:02d}", wger=wger, category=category,
            best_1rm=best, target_1rm=target, status=LiftStatus(status),
        )
        ex.musclegroup_ids = [groups[muscle]]
        ex.tag_ids = ["tag-main" if category == "compound" else "tag-acc"]
        ex.started_at = "2024-09-01"
        if status == "retired":
            ex.finished_at = "2025-06-15"
        st.upsert_exercise(ex)
        if rating is not None:
            st.add_rating(Rating.create(ex.id, value=rating, review=""))
        # a few logged sets for the active lifts
        if status == "active" and best:
            for wk in range(3):
                d = date(2025, 1, 10) + timedelta(days=wk * 7)
                w = round(best * 0.85 + wk * 2.5, 1)
                st.add_workset(WorkSet.create(ex.id, weight=w, reps=5, rpe=8.0,
                                              started_at=d.isoformat() + "T18:00:00"))
    st.save_goals([LiftGoal.create("Log 200 sets in 2026", "sets", 200, "year")])
    st.save()


def _build_demo() -> None:
    DEMO.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    today = date.today()
    path = DEMO / "demo_library.json"
    if path.exists():
        path.unlink()
    st = JsonStorage(path)
    st.load()
    mg = MuscleGroup.create("Full Body", id="demo-mg")
    st.upsert_musclegroup(mg)
    lifts = ["Squat", "Bench", "Deadlift", "Press", "Row", "Curl"]
    for i in range(36):
        best = round(rng.uniform(30, 220), 1)
        status = rng.choice(["active", "maintenance", "retired", "learning"])
        ex = Exercise.create(
            f"{rng.choice(lifts)} Variation {i}", id=f"demo-{i:03d}",
            category=rng.choice(["compound", "isolation"]),
            best_1rm=best, target_1rm=round(best + rng.uniform(5, 30), 1),
            status=LiftStatus(status),
        )
        ex.musclegroup_ids = [mg.id]
        st.upsert_exercise(ex)
        if status in ("active", "maintenance"):
            for _ in range(rng.randint(1, 4)):
                d = today - timedelta(days=rng.randint(1, 400))
                st.add_workset(WorkSet.create(ex.id, weight=round(best * 0.8, 1),
                                              reps=rng.randint(3, 10),
                                              started_at=d.isoformat() + "T18:00:00"))
        if status == "retired":
            st.add_rating(Rating.create(ex.id, value=float(rng.randint(3, 5))))
    st.save()

    stats = {
        "generated_on": today.isoformat(),
        "volume_per_week": [rng.randint(2000, 18000) for _ in range(52)],
        "by_category": {"compound": 22, "isolation": 14},
        "by_musclegroup": {"Quadriceps": 8, "Back": 7, "Chest": 6, "Shoulders": 5, "Hamstrings": 4},
    }
    (DEMO / "demo_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    _build_sample()
    _build_demo()
    print(f"seeded sample_library.json + demo fixtures under {FIX}")


if __name__ == "__main__":
    main()
