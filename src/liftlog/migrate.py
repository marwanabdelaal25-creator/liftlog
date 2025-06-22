"""Schema migrations between library JSON versions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, TYPE_CHECKING

from liftlog.errors import MigrationError
from liftlog.storage import SCHEMA_VERSION

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage

MigratorFn = Callable[[Dict[str, Any]], Dict[str, Any]]


def migrate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    ver = int(data.get("version", 0))
    if ver == SCHEMA_VERSION:
        return data
    if ver > SCHEMA_VERSION:
        raise MigrationError(ver, SCHEMA_VERSION, "future schema not supported")
    cur = dict(data)
    while ver < SCHEMA_VERSION:
        fn = _MIGRATORS.get(ver)
        if fn is None:
            raise MigrationError(ver, SCHEMA_VERSION, "no migrator registered")
        cur = fn(cur)
        ver = int(cur.get("version", ver + 1))
    return cur


def _v0_to_v1(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    exercises = out.get("exercises", [])
    if isinstance(exercises, dict):
        out["exercises"] = list(exercises.values())
    for bk in out.get("exercises", []):
        bk["status"] = _LEGACY_STATUS.get(bk.get("status", ""), bk.get("status", "active"))
    for key in ("collections", "equipment", "program", "recurring", "quotes", "notes"):
        out.setdefault(key, [])
    out.setdefault("audit", [])
    out.setdefault("plugins", {})
    out["version"] = 1
    return out


def _v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    import copy

    out = copy.deepcopy(data)
    exercises = out.get("exercises")
    if exercises is None:
        out["exercises"] = {}
    elif isinstance(exercises, dict):
        for bk in exercises.values():
            _normalize_v1_exercise(bk)
    elif isinstance(exercises, list):
        for bk in exercises:
            _normalize_v1_exercise(bk)
    for key in ("collections", "equipment", "program", "audit"):
        out.setdefault(key, [])
    out.setdefault("plugins", {})
    out.setdefault("recurring", [])
    out["version"] = 2
    return out


_LEGACY_STATUS = {
    "wishlist": "learning", "new": "learning", "practicing": "learning",
    "current": "active", "programmed": "active", "main": "active",
    "accessory": "maintenance", "upkeep": "maintenance",
    "dropped": "retired", "removed": "retired",
    "injured": "benched", "deload": "benched",
}


def _normalize_v1_exercise(bk: Dict[str, Any]) -> None:
    if bk.get("status") in _LEGACY_STATUS:
        bk["status"] = _LEGACY_STATUS[bk["status"]]
    if "rating" in bk and isinstance(bk["rating"], dict):
        bk["rating"] = bk["rating"].get("value") or bk["rating"].get("score")
    if "max" in bk and "best_1rm" not in bk:
        bk["best_1rm"] = bk.pop("max")
    if "goal" in bk and "target_1rm" not in bk:
        bk["target_1rm"] = bk.pop("goal")


_MIGRATORS: Dict[int, MigratorFn] = {
    0: _v0_to_v1,
    1: _v1_to_v2,
}


def needs_migration(data: Dict[str, Any]) -> bool:
    return int(data.get("version", 0)) < SCHEMA_VERSION


def migration_plan(data: Dict[str, Any]) -> List[int]:
    ver = int(data.get("version", 0))
    steps = []
    while ver < SCHEMA_VERSION:
        if ver not in _MIGRATORS:
            break
        steps.append(ver)
        ver += 1
    return steps


def describe(data: Dict[str, Any]) -> str:
    cur = int(data.get("version", 0))
    if cur >= SCHEMA_VERSION:
        return "schema v%d — up to date" % cur
    plan = migration_plan(data)
    return "schema v%d -> v%d (%d step(s))" % (cur, SCHEMA_VERSION, len(plan))


def validate_post_migration(data: Dict[str, Any]) -> List[str]:
    warns: List[str] = []
    if not isinstance(data.get("exercises"), list):
        warns.append("exercises should be a list")
    for bk in data.get("exercises", []):
        if "id" not in bk or "name" not in bk:
            warns.append("exercise missing id/name: %r" % bk.get("name", "?"))
    return warns


def backup_before_migrate(data: Dict[str, Any]) -> Dict[str, Any]:
    import copy

    return copy.deepcopy(data)


def rollback(original: Dict[str, Any], storage_path: Path) -> None:
    import json

    storage_path.write_text(json.dumps(original, indent=2), encoding="utf-8")


def migrate_with_backup(data: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    snap = backup_before_migrate(data)
    new_data = migrate_data(data)
    return new_data, snap


def diff_versions(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    keys = set(before.keys()) | set(after.keys())
    diff: Dict[str, Any] = {"version": (before.get("version"), after.get("version"))}
    for k in keys:
        if k in ("exercises", "musclegroups", "worksets", "tags"):
            b_len = len(before.get(k, []))
            a_len = len(after.get(k, []))
            if b_len != a_len:
                diff[k] = {"before": b_len, "after": a_len}
    return diff


def normalize_exercise_record(bk: Dict[str, Any]) -> Dict[str, Any]:
    if bk.get("status") in _LEGACY_STATUS:
        bk["status"] = _LEGACY_STATUS[bk["status"]]
    if "max" in bk and "best_1rm" not in bk:
        bk["best_1rm"] = bk.pop("max")
    if "pr" in bk and "best_1rm" not in bk:
        bk["best_1rm"] = bk.pop("pr")
    if "goal" in bk and "target_1rm" not in bk:
        bk["target_1rm"] = bk.pop("goal")
    return bk


def normalize_all_exercises(data: Dict[str, Any]) -> int:
    n = 0
    exercises = data.get("exercises", [])
    if isinstance(exercises, dict):
        exercises = list(exercises.values())
        data["exercises"] = exercises
    for bk in exercises:
        normalize_exercise_record(bk)
        n += 1
    return n


class MigrationRunner:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def status(self) -> str:
        return describe(self.storage.snapshot())

    def run(self) -> Dict[str, Any]:
        before = self.storage.snapshot()
        if not needs_migration(before):
            return before
        after, snap = migrate_with_backup(before)
        warns = validate_post_migration(after)
        self.storage.replace_all(after)
        self.storage.save()
        return {"after": after, "backup": snap, "warnings": warns}

    def preview(self) -> Dict[str, Any]:
        before = self.storage.snapshot()
        after = migrate_data(before) if needs_migration(before) else before
        return {
            "plan": migration_plan(before),
            "diff": diff_versions(before, after),
            "warnings": validate_post_migration(after),
        }


def apply_to_file(store) -> bool:
    runner = MigrationRunner(store._inner if hasattr(store, "_inner") else store)
    snap = store.to_dict() if hasattr(store, "to_dict") else store.snapshot()
    if not needs_migration(snap):
        return False
    runner.run()
    if hasattr(store, "_reload"):
        store._reload()
    elif hasattr(store, "load"):
        store.load()
    return True
