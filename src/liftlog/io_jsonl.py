"""JSON Lines import/export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from liftlog.exercise import Exercise
from liftlog.workset import WorkSet
from liftlog.errors import ExportError, ImportError as LiftlogImportError
from liftlog.storage import JsonStorage


def export_jsonl_exercises(storage: JsonStorage, dest: Path) -> int:
    exercises = storage.list_exercises()
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for exercise in exercises:
                fh.write(json.dumps(exercise.to_dict(), ensure_ascii=False) + "\n")
        return len(exercises)
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc


def export_jsonl_worksets(storage: JsonStorage, dest: Path) -> int:
    worksets = storage.list_worksets()
    with dest.open("w", encoding="utf-8") as fh:
        for sess in worksets:
            fh.write(json.dumps(sess.to_dict(), ensure_ascii=False) + "\n")
    return len(worksets)


def export_full_library(storage: JsonStorage, dest: Path) -> int:
    """One JSON object per line with entity type prefix."""
    n = 0
    with dest.open("w", encoding="utf-8") as fh:
        for exercise in storage.list_exercises():
            fh.write(json.dumps({"_type": "exercise", **exercise.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
        for musclegroup in storage.list_musclegroups():
            fh.write(json.dumps({"_type": "musclegroup", **musclegroup.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
        for sess in storage.list_worksets():
            fh.write(json.dumps({"_type": "workset", **sess.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
    return n


def import_jsonl_exercises(storage: JsonStorage, src: Path) -> int:
    if not src.exists():
        raise LiftlogImportError("jsonl", "missing %s" % src)
    n = 0
    for line in _iter_lines(src):
        data = json.loads(line)
        if data.get("_type") and data["_type"] != "exercise":
            continue
        data.pop("_type", None)
        exercise = Exercise.from_dict(data)
        storage.upsert_exercise(exercise)
        n += 1
    return n


def import_jsonl_worksets(storage: JsonStorage, src: Path) -> int:
    n = 0
    for line in _iter_lines(src):
        data = json.loads(line)
        if data.get("_type") and data["_type"] != "workset":
            continue
        data.pop("_type", None)
        sess = WorkSet.from_dict(data)
        storage.add_workset(sess)
        n += 1
    return n


def import_mixed_jsonl(storage: JsonStorage, src: Path) -> Dict[str, int]:
    counts = {"exercise": 0, "musclegroup": 0, "workset": 0, "skipped": 0}
    for line in _iter_lines(src):
        data = json.loads(line)
        kind = data.pop("_type", "exercise")
        if kind == "exercise":
            storage.upsert_exercise(Exercise.from_dict(data))
            counts["exercise"] += 1
        elif kind == "musclegroup":
            from liftlog.musclegroup import MuscleGroup

            storage.upsert_musclegroup(MuscleGroup.from_dict(data))
            counts["musclegroup"] += 1
        elif kind == "workset":
            storage.add_workset(WorkSet.from_dict(data))
            counts["workset"] += 1
        else:
            counts["skipped"] += 1
    return counts


def _iter_lines(path: Path) -> Iterable[str]:
    with path.open(encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                yield ln


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in _iter_lines(path))
