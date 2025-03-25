"""CSV import and export for liftlog exercise catalogs."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Dict, List

from liftlog.exercise import Exercise, LiftStatus
from liftlog.musclegroup import MuscleGroup
from liftlog.errors import ExportError, ImportError as LiftlogImportError
from liftlog.parser import split_csv_line
from liftlog.storage import JsonStorage

CSV_FIELDS = ["name", "musclegroup", "wger", "equipment", "category",
              "best_1rm", "target_1rm", "unit", "status", "rating", "tags"]
IMPORT_STATUS = {
    "learning": LiftStatus.LEARNING,
    "active": LiftStatus.ACTIVE,
    "maintenance": LiftStatus.MAINTENANCE,
    "retired": LiftStatus.RETIRED,
    "benched": LiftStatus.BENCHED,
}


def _parse_status(raw) -> LiftStatus:
    if not raw:
        return LiftStatus.ACTIVE
    return IMPORT_STATUS.get(str(raw).strip().lower(), LiftStatus.ACTIVE)


def _num(raw) -> float | None:
    raw = str(raw or "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def export_csv(storage: JsonStorage, dest: Path) -> int:
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            w.writeheader()
            groups = {m.id: m.name for m in storage.list_musclegroups()}
            tags = {t.id: t.name for t in storage.list_tags()}
            n = 0
            for e in storage.list_exercises():
                w.writerow({
                    "name": e.name,
                    "musclegroup": "; ".join(groups.get(g, g) for g in e.musclegroup_ids),
                    "wger": e.wger or "",
                    "equipment": "",
                    "category": e.category,
                    "best_1rm": e.best_1rm or "",
                    "target_1rm": e.target_1rm if e.target_1rm is not None else "",
                    "unit": e.unit,
                    "status": e.status.value,
                    "rating": e.rating_value if e.rating_value is not None else "",
                    "tags": ", ".join(tags.get(t, t) for t in e.tag_ids),
                })
                n += 1
        return n
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def import_csv(storage: JsonStorage, src: Path, update: bool = False) -> int:
    if not src.exists():
        raise LiftlogImportError("csv", "file not found")
    text = src.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    count = 0
    for row in reader:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        wger = (row.get("wger") or "").strip() or None
        existing = None
        if update:
            existing = next((e for e in storage.list_exercises() if e.name == name), None)
        if existing:
            exercise = existing
            exercise.status = _parse_status(row.get("status"))
        else:
            exercise = Exercise.create(name, wger=wger, status=_parse_status(row.get("status")),
                                       source="csv")
        if row.get("category"):
            exercise.category = row["category"].strip()
        if row.get("unit"):
            exercise.unit = row["unit"].strip()
        best = _num(row.get("best_1rm"))
        if best is not None:
            exercise.best_1rm = best
        target = _num(row.get("target_1rm"))
        if target is not None:
            exercise.target_1rm = target
        rt = _num(row.get("rating"))
        if rt is not None:
            exercise.rating = rt
        group = (row.get("musclegroup") or "").strip()
        if group:
            for part in group.split(";"):
                nm = part.strip()
                if not nm:
                    continue
                mg = next((m for m in storage.list_musclegroups() if m.name == nm), None)
                if mg is None:
                    mg = MuscleGroup.create(nm)
                    storage.upsert_musclegroup(mg)
                if mg.id not in exercise.musclegroup_ids:
                    exercise.musclegroup_ids.append(mg.id)
        storage.upsert_exercise(exercise)
        count += 1
    return count


def parse_row(line: str) -> Dict[str, str]:
    parts = split_csv_line(line)
    return dict(zip(CSV_FIELDS, parts + [""] * (len(CSV_FIELDS) - len(parts))))


def validate_csv_headers(path: Path) -> List[str]:
    if not path.exists():
        return CSV_FIELDS
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    return [h for h in ["name"] if h not in headers]


def sample_rows(path: Path, n: int = 3) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    out = []
    for i, row in enumerate(reader):
        if i >= n:
            break
        out.append(dict(row))
    return out
