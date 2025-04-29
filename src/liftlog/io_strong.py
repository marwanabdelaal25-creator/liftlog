"""Import a Strong app CSV export.

Strong exports one row per set:

    Date, Workout Name, Exercise Name, Set Order, Weight, Reps, RPE, Notes

Each row becomes a :class:`WorkSet` against an :class:`Exercise` (created on
first sight). The exercise's ``best_1rm`` is bumped whenever a set's estimated
1RM beats it.
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


def _date(raw: str) -> str:
    raw = (raw or "").strip()
    return raw.replace(" ", "T") if raw else ""


def _find_or_create(storage: JsonStorage, name: str, cache: Dict[str, str]) -> Exercise:
    key = name.lower()
    if key in cache:
        return storage.get_exercise(cache[key])
    existing = next((e for e in storage.list_exercises() if e.name.lower() == key), None)
    if existing is None:
        existing = Exercise.create(name, status=LiftStatus.ACTIVE, source="strong")
        storage.upsert_exercise(existing)
    cache[key] = existing.id
    return existing


def import_strong(storage: JsonStorage, path: Path) -> int:
    if not path.exists():
        raise LiftlogImportError("strong", "file not found")
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    cache: Dict[str, str] = {}
    n = 0
    for row in reader:
        name = _col(row, "Exercise Name", "exercise_name")
        if not name:
            continue
        weight = _float(_col(row, "Weight", "weight")) or 0.0
        reps = int(_float(_col(row, "Reps", "reps")) or 0)
        rpe = _float(_col(row, "RPE", "rpe"))
        ex = _find_or_create(storage, name, cache)
        sett = WorkSet.create(
            ex.id, weight=weight, reps=reps, rpe=rpe,
            started_at=_date(_col(row, "Date", "date")) or None,
            notes=_col(row, "Notes"),
        )
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
        out.append("%s: %sx%s" % (_col(row, "Exercise Name") or "?",
                                   _col(row, "Weight") or "?", _col(row, "Reps") or "?"))
    return out


def exercises_seen(storage: JsonStorage) -> int:
    return sum(1 for e in storage.list_exercises() if e.source == "strong")
