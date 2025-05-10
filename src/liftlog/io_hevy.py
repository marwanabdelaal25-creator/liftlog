"""Import a Hevy app CSV export.

Hevy exports one row per set with these (lower-cased) columns:

    title, start_time, exercise_title, set_index, weight_kg, reps, rpe

Like the Strong importer, each row becomes a :class:`WorkSet`.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

from liftlog.exercise import Exercise, LiftStatus
from liftlog.workset import WorkSet
from liftlog.errors import ImportError as LiftlogImportError
from liftlog.storage import JsonStorage


def _col(row: Dict[str, str], *names: str) -> str:
    for n in names:
        v = row.get(n)
        if v not in (None, ""):
            return str(v).strip()
    return ""


def _float(raw: str) -> Optional[float]:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def import_hevy(storage: JsonStorage, path: Path) -> int:
    if not path.exists():
        raise LiftlogImportError("hevy", "file not found")
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    cache: Dict[str, str] = {}
    n = 0
    for row in reader:
        name = _col(row, "exercise_title", "Exercise", "exercise_name")
        if not name:
            continue
        weight = _float(_col(row, "weight_kg", "weight")) or 0.0
        reps = int(_float(_col(row, "reps")) or 0)
        rpe = _float(_col(row, "rpe"))
        key = name.lower()
        if key in cache:
            ex = storage.get_exercise(cache[key])
        else:
            ex = next((e for e in storage.list_exercises() if e.name.lower() == key), None)
            if ex is None:
                ex = Exercise.create(name, status=LiftStatus.ACTIVE, source="hevy", unit="kg")
                storage.upsert_exercise(ex)
            cache[key] = ex.id
        started = _col(row, "start_time", "start").replace(" ", "T") or None
        sett = WorkSet.create(ex.id, weight=weight, reps=reps, rpe=rpe, started_at=started)
        storage.add_workset(sett)
        if ex.update_best(sett.e1rm()):
            storage.upsert_exercise(ex)
        n += 1
    return n


def preview(path: Path, limit: int = 5) -> List[str]:
    if not path.exists():
        return []
    reader = csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig")))
    out = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        out.append("%s: %sx%s" % (_col(row, "exercise_title") or "?",
                                   _col(row, "weight_kg") or "?", _col(row, "reps") or "?"))
    return out


def imported(storage: JsonStorage) -> List[Exercise]:
    return [e for e in storage.list_exercises() if e.source == "hevy"]


def history_summary(storage: JsonStorage) -> str:
    rows = imported(storage)
    if not rows:
        return "No Hevy workouts imported."
    lines = ["Hevy exercises (%d):" % len(rows)]
    for e in rows[:20]:
        lines.append("  - %s (best %g)" % (e.name[:40], e.best_1rm))
    return "\n".join(lines)
