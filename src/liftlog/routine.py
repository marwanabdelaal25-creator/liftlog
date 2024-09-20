"""Routines — curated lists with optional visibility."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, List, Optional
import uuid

from liftlog.validators import require_non_empty, validate_slug
from liftlog.errors import NotFoundError, ConflictError


@dataclass
class Routine:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    description: str = ""
    exercise_ids: list[str] = field(default_factory=list)
    is_default: bool = False
    is_public: bool = False
    sort_order: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Routine":
        sid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=sid, name=name.strip(), **kwargs)

    @property
    def slug(self) -> str:
        return validate_slug(self.name)

    def add_exercise(self, exercise_id: str) -> bool:
        if exercise_id in self.exercise_ids:
            return False
        self.exercise_ids.append(exercise_id)
        return True

    def remove_exercise(self, exercise_id: str) -> bool:
        try:
            self.exercise_ids.remove(exercise_id)
            return True
        except ValueError:
            return False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Routine:
        created = data.get("created_at")
        if created:
            data = dict(data)
            data["created_at"] = datetime.fromisoformat(created)
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})

    def count(self) -> int:
        return len(self.exercise_ids)


class RoutineManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Routine]:
        return sorted(self.storage.list_routines(), key=lambda s: s.sort_order)

    def get(self, routine_id: str) -> Routine:
        for s in self.list_all():
            if s.id == routine_id or s.id.startswith(routine_id):
                return s
        raise NotFoundError("routine", routine_id)

    def find_by_name(self, name: str) -> Optional[Routine]:
        nm = name.lower()
        for s in self.list_all():
            if s.name.lower() == nm:
                return s
        return None

    def create(self, name: str, description: str = "") -> Routine:
        if self.find_by_name(name):
            raise ConflictError("routine exists: %s" % name)
        sh = Routine.create(name, description=description, sort_order=len(self.list_all()))
        self.storage.upsert_routine(sh)
        return sh

    def add_exercise(self, routine_id: str, exercise_id: str) -> None:
        sh = self.get(routine_id)
        exercise = self.storage.get_exercise(exercise_id)
        sh.add_exercise(exercise.id)
        if sh.id not in exercise.routine_ids:
            exercise.routine_ids.append(sh.id)
        self.storage.upsert_routine(sh)
        self.storage.upsert_exercise(exercise)

    def remove_exercise(self, routine_id: str, exercise_id: str) -> None:
        sh = self.get(routine_id)
        sh.remove_exercise(exercise_id)
        exercise = self.storage.get_exercise(exercise_id)
        if routine_id in exercise.routine_ids:
            exercise.routine_ids.remove(routine_id)
        self.storage.upsert_routine(sh)
        self.storage.upsert_exercise(exercise)

    def default_routine(self) -> Routine:
        for s in self.list_all():
            if s.is_default:
                return s
        sh = Routine.create("To Buy", is_default=True, sort_order=0)
        self.storage.upsert_routine(sh)
        return sh

    def report(self, routine_id: str) -> str:
        sh = self.get(routine_id)
        lines = ["Routine: %s" % sh.name, sh.description or "", ""]
        for bid in sh.exercise_ids:
            try:
                b = self.storage.get_exercise(bid)
                lines.append("  - %s [%s]" % (b.name, b.status.value))
            except NotFoundError:
                lines.append("  - (missing %s)" % bid[:8])
        lines.append("")
        lines.append("Total: %d" % sh.count())
        return "\n".join(lines)
