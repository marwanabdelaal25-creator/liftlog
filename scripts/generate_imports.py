#!/usr/bin/env python3
"""Generate multi-source import fixtures for liftlog (stdlib only).

One sub-folder per app, with per-month chunks across several years. Each app
uses roughly the shape of its real export so the importers (and a curious human)
see something believable.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "imports"

SOURCES = ["strong", "hevy", "fitnotes", "jefit", "wger", "liftin"]
YEARS = list(range(2019, 2026))
LIFTS = ["Back Squat", "Bench Press", "Deadlift", "Overhead Press", "Barbell Row",
         "Pull-up", "Romanian Deadlift", "Front Squat", "Incline Bench Press", "Dip"]
WORKOUTS = ["Push Day", "Pull Day", "Leg Day", "Upper", "Lower", "Full Body"]


def _sets(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for _ in range(n):
        d = date(rng.randint(2019, 2025), rng.randint(1, 12), rng.randint(1, 28))
        rows.append({
            "date": d.isoformat() + " 18:00:00",
            "workout": rng.choice(WORKOUTS),
            "exercise": rng.choice(LIFTS),
            "weight": round(rng.uniform(20, 220), 1),
            "reps": rng.randint(1, 12),
            "rpe": rng.choice(["", 7, 8, 8.5, 9, 9.5]),
        })
    return rows


def _write_strong(path: Path, rows: list[dict]) -> None:
    fields = ["Date", "Workout Name", "Exercise Name", "Set Order", "Weight", "Reps", "RPE", "Notes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({"Date": r["date"], "Workout Name": r["workout"], "Exercise Name": r["exercise"],
                        "Set Order": i % 5 + 1, "Weight": r["weight"], "Reps": r["reps"],
                        "RPE": r["rpe"], "Notes": ""})


def _write_hevy(path: Path, rows: list[dict]) -> None:
    fields = ["title", "start_time", "exercise_title", "set_index", "weight_kg", "reps", "rpe"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow({"title": r["workout"], "start_time": r["date"], "exercise_title": r["exercise"],
                        "set_index": i % 5, "weight_kg": r["weight"], "reps": r["reps"], "rpe": r["rpe"]})


def _write_fitnotes(path: Path, rows: list[dict]) -> None:
    fields = ["Date", "Exercise", "Category", "Weight", "Reps"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({"Date": r["date"][:10], "Exercise": r["exercise"], "Category": "Barbell",
                        "Weight": r["weight"], "Reps": r["reps"]})


def _write_json(path: Path, source: str, rows: list[dict]) -> None:
    path.write_text(json.dumps({"source": source, "version": 2, "sets": rows}, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in SOURCES:
        for year in YEARS:
            year_dir = OUT / source / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            for month in range(1, 13):
                rng = random.Random(hash((source, year, month)) & 0xFFFFFFFF)
                rows = _sets(rng, rng.randint(20, 60))
                stem = f"{source}_{year}_{month:02d}"
                if source == "strong":
                    p = year_dir / f"{stem}.csv"; _write_strong(p, rows)
                elif source == "hevy":
                    p = year_dir / f"{stem}.csv"; _write_hevy(p, rows)
                elif source == "fitnotes":
                    p = year_dir / f"{stem}.csv"; _write_fitnotes(p, rows)
                else:
                    p = year_dir / f"{stem}.json"; _write_json(p, source, rows)
                total += p.stat().st_size
            for q in range(1, 5):
                rng = random.Random(hash((source, year, q, "q")) & 0xFFFFFFFF)
                p = year_dir / f"{source}_{year}_Q{q}.json"
                _write_json(p, source, _sets(rng, rng.randint(80, 140)))
                total += p.stat().st_size
    print(f"import fixtures: {len(SOURCES)} sources, {len(YEARS)} years -> {total / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    main()
