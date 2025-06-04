"""Import from a FitNotes sqlite backup.

FitNotes (Android) keeps a sqlite database; its export/backup has a
``training_log`` table with one row per set:

    date, exercise, category, weight, reps

We rebuild exercises and their sets from that table.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from liftlog.exercise import Exercise, LiftStatus
from liftlog.workset import WorkSet
from liftlog.errors import ImportError as LiftlogImportError
from liftlog.storage import JsonStorage


def _read_db(library: Path) -> Path:
    db = library / "fitnotes.db"
    if not db.exists():
        raise LiftlogImportError("fitnotes", "fitnotes.db not found in %s" % library)
    return db


def import_fitnotes(storage: JsonStorage, library_path: Path) -> int:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT date, exercise, category, weight, reps FROM training_log ORDER BY date"
    )
    cache: Dict[str, str] = {}
    n = 0
    for row in cur:
        name = row["exercise"] or "Unknown Exercise"
        key = name.lower()
        if key in cache:
            ex = storage.get_exercise(cache[key])
        else:
            ex = next((e for e in storage.list_exercises() if e.name.lower() == key), None)
            if ex is None:
                ex = Exercise.create(name, status=LiftStatus.ACTIVE, source="fitnotes",
                                     category=(row["category"] or "compound"))
                storage.upsert_exercise(ex)
            cache[key] = ex.id
        try:
            weight = float(row["weight"] or 0)
            reps = int(row["reps"] or 0)
        except (TypeError, ValueError):
            weight, reps = 0.0, 0
        started = str(row["date"]) + "T12:00:00" if row["date"] else None
        sett = WorkSet.create(ex.id, weight=weight, reps=reps, started_at=started)
        storage.add_workset(sett)
        if ex.update_best(sett.e1rm()):
            storage.upsert_exercise(ex)
        n += 1
    conn.close()
    return n


def list_fitnotes_exercises(library_path: Path, limit: int = 20) -> List[str]:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    cur = conn.execute("SELECT DISTINCT exercise FROM training_log LIMIT ?", (limit,))
    out = [r[0] for r in cur.fetchall()]
    conn.close()
    return out


def export_fitnotes_json(storage: JsonStorage) -> str:
    rows = []
    for w in storage.list_worksets():
        rows.append({"exercise_id": w.exercise_id, "weight": w.weight, "reps": w.reps})
    return json.dumps(rows, indent=2)


def fitnotes_stats(library_path: Path) -> Dict[str, int]:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    sets = conn.execute("SELECT COUNT(*) FROM training_log").fetchone()[0]
    exercises = conn.execute("SELECT COUNT(DISTINCT exercise) FROM training_log").fetchone()[0]
    conn.close()
    return {"sets": sets, "exercises": exercises}
