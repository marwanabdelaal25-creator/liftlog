"""wger.de lookups — resolve an exercise id to a canonical name + metadata.

Thin wrapper over the public wger REST API (no key needed for reads). The call
I actually use is :func:`exercise_from_wger` — give it a wger id, get a populated
:class:`Exercise` (name, category, equipment, primary muscles) back.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, List, Optional

from liftlog.exercise import Exercise, LiftStatus
from liftlog.errors import ImportError as LiftlogImportError
from liftlog.wger import validate_wger, normalize_wger
from liftlog.storage import JsonStorage

BASE = "https://wger.de/api/v2"

# wger groups everything into a handful of categories; map to our compound/isolation-ish.
_COMPOUND = {"legs", "back", "chest", "shoulders"}


def _get(path: str, timeout: int = 10) -> dict[str, Any]:
    url = "%s%s" % (BASE, path)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except OSError as exc:
        raise LiftlogImportError("wger", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise LiftlogImportError("wger", "bad json") from exc


def fetch_exercise(wger_id: str) -> dict[str, Any]:
    if not validate_wger(wger_id):
        raise LiftlogImportError("wger", "bad wger id: %s" % wger_id)
    return _get("/exerciseinfo/%s/" % normalize_wger(wger_id))


def _category_name(data: dict[str, Any]) -> str:
    cat = data.get("category")
    if isinstance(cat, dict):
        return str(cat.get("name", ""))
    return str(cat or "")


def _names(items: Any) -> List[str]:
    out = []
    for it in items or []:
        if isinstance(it, dict) and it.get("name"):
            out.append(str(it["name"]))
        elif isinstance(it, str):
            out.append(it)
    return out


def _apply(exercise: Exercise, data: dict[str, Any]) -> None:
    cat = _category_name(data).lower()
    exercise.category = "compound" if cat in _COMPOUND else "isolation"
    meta = dict(exercise.metadata or {})
    if cat:
        meta["wger_category"] = cat
    equip = _names(data.get("equipment"))
    if equip:
        meta["equipment"] = equip
    muscles = _names(data.get("muscles"))
    if muscles:
        meta["muscles"] = muscles
    exercise.metadata = meta
    if data.get("description"):
        exercise.description = str(data["description"])[:500]


def exercise_from_wger(wger_id: str) -> Exercise:
    data = fetch_exercise(wger_id)
    name = data.get("name") or "Unknown Exercise"
    exercise = Exercise.create(name, wger=normalize_wger(wger_id), source="wger",
                               status=LiftStatus.LEARNING)
    _apply(exercise, data)
    return exercise


def search(query: str, limit: int = 5) -> List[dict[str, Any]]:
    try:
        data = _get("/exercise/search/?term=%s" % urllib.parse.quote(query))
    except LiftlogImportError:
        return []
    results = data.get("suggestions") or data.get("results") or []
    return results[:limit]


def enrich_exercise(storage: JsonStorage, exercise_id: str) -> Exercise:
    exercise = storage.get_exercise(exercise_id)
    if not exercise.wger:
        raise LiftlogImportError("wger", "exercise has no wger id")
    data = fetch_exercise(exercise.wger)
    _apply(exercise, data)
    storage.upsert_exercise(exercise)
    return exercise


def bulk_enrich(storage: JsonStorage, limit: int = 10) -> int:
    n = 0
    for exercise in storage.list_exercises():
        if not exercise.wger:
            continue
        try:
            enrich_exercise(storage, exercise.id)
            n += 1
        except LiftlogImportError:
            continue
        if n >= limit:
            break
    return n


def format_search_hit(item: dict[str, Any]) -> str:
    val = item.get("value") or item.get("name") or "Unknown"
    data = item.get("data") or {}
    cat = data.get("category") or ""
    return "%s%s" % (val, (" (%s)" % cat) if cat else "")
