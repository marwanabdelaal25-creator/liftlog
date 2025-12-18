#!/usr/bin/env python3
"""Generate large liftlog training-log JSON fixtures (stdlib only)."""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "libraries"

BASE_LIFTS = [
    "Back Squat", "Front Squat", "Bench Press", "Incline Bench Press", "Overhead Press",
    "Deadlift", "Romanian Deadlift", "Barbell Row", "Pull-up", "Chin-up", "Dip",
    "Leg Press", "Leg Curl", "Leg Extension", "Lateral Raise", "Bicep Curl",
    "Tricep Pushdown", "Lat Pulldown", "Hip Thrust", "Calf Raise", "Power Clean",
    "Snatch", "Push Press", "Good Morning", "Face Pull",
]
VARIANTS = ["", "Paused", "Tempo", "Deficit", "Close-grip", "Wide-grip", "Pin", "Beltless"]
MUSCLES = ["Quadriceps", "Hamstrings", "Glutes", "Chest", "Back", "Shoulders",
           "Biceps", "Triceps", "Core", "Calves"]
EQUIPMENT = ["Barbell", "Dumbbell", "Machine", "Cable", "Bodyweight", "Kettlebell", "Smith Machine"]
CATEGORIES = ["compound", "isolation", "olympic"]
STATUSES = ["learning", "active", "active", "maintenance", "retired", "benched"]
PERSONAS = [
    "powerlifter", "bodybuilder", "crossfitter", "beginner", "strongman",
    "olympic_lifter", "calisthenics", "general_fitness", "masters_lifter", "athlete",
]


def _name(rng: random.Random, n: int) -> str:
    base = rng.choice(BASE_LIFTS)
    variant = rng.choice(VARIANTS)
    name = ("%s %s" % (variant, base)).strip()
    return "%s #%d" % (name, n) if rng.random() < 0.3 else name


def _exercise_entry(rng: random.Random, idx: int, year: int) -> dict:
    best = round(rng.uniform(20, 260), 1)
    status = rng.choice(STATUSES)
    started = date(year - rng.randint(0, 3), rng.randint(1, 12), rng.randint(1, 28))
    return {
        "id": "ex-%d-%06d" % (year, idx),
        "name": _name(rng, idx),
        "musclegroups": rng.sample(MUSCLES, rng.randint(1, 2)),
        "wger": "%d" % rng.randint(1, 900) if rng.random() < 0.5 else None,
        "category": rng.choice(CATEGORIES),
        "equipment": rng.choice(EQUIPMENT),
        "unit": "kg",
        "best_1rm": best,
        "target_1rm": round(best + rng.uniform(2.5, 40), 1),
        "status": status,
        "started_on": started.isoformat(),
        "rating": round(rng.uniform(2.5, 5.0), 1) if rng.random() > 0.2 else None,
        "tags": ["tag-%d" % rng.randint(1, 60) for _ in range(rng.randint(0, 3))],
        "notes": "",
    }


def _workset(rng: random.Random, ex_id: str, day: date) -> dict:
    return {
        "exercise_id": ex_id,
        "weight": round(rng.uniform(20, 240), 1),
        "reps": rng.randint(1, 12),
        "rpe": rng.choice([None, 7, 7.5, 8, 8.5, 9, 9.5]),
        "date": day.isoformat() + "T18:00:00",
    }


def _library_blob(rng: random.Random, *, entries: int, label: str) -> dict:
    year = int(label.split("-")[-1]) if label[-4:].isdigit() else 2025
    exercises = [_exercise_entry(rng, i, year) for i in range(entries)]
    worksets = []
    for ex in exercises[: min(len(exercises), 400)]:
        for _ in range(rng.randint(0, 4)):
            d = date(year, rng.randint(1, 12), rng.randint(1, 28))
            worksets.append(_workset(rng, ex["id"], d))
    return {
        "schema": 3,
        "label": label,
        "persona": rng.choice(PERSONAS),
        "generated": True,
        "stats": {
            "exercises": len(exercises),
            "worksets": len(worksets),
            "volume": round(sum(w["weight"] * w["reps"] for w in worksets), 1),
        },
        "exercises": exercises,
        "worksets": worksets,
        "routines": {
            "push": [e["id"] for e in exercises if e["category"] == "compound"][:40],
            "active": [e["id"] for e in exercises if e["status"] == "active"][:120],
        },
    }


def _write_json(path: Path, data: dict) -> int:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for i, entries in enumerate((3600, 4300, 3200), start=1):
        rng = random.Random(2000 + i)
        data = _library_blob(rng, entries=entries, label=f"megalog-{i}")
        n = _write_json(OUT / f"megalog-{i}.json", data)
        total += n
        print(f"megalog-{i}.json: {n / (1024 * 1024):.2f} MB")

    for year in range(2018, 2026):
        rng = random.Random(year)
        snap = {"year": year, "exercises": [_exercise_entry(rng, j, year) for j in range(rng.randint(120, 220))]}
        total += _write_json(OUT / f"snapshot-{year}.json", snap)

    for persona in PERSONAS:
        rng = random.Random(hash(persona) & 0xFFFFFFFF)
        data = _library_blob(rng, entries=rng.randint(180, 350), label=f"persona-{persona}")
        total += _write_json(OUT / f"persona-{persona}.json", data)

    print(f"library fixtures total: {total / (1024 * 1024):.2f} MB raw -> {OUT}")


if __name__ == "__main__":
    main()
