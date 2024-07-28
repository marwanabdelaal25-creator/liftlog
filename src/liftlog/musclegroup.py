"""MuscleGroup model and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import uuid

from liftlog.validators import require_non_empty, validate_email
from liftlog.errors import NotFoundError, ConflictError


@dataclass
class MuscleGroup:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bio: str = ""
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    website: str = ""
    email: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    exercise_ids: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "MuscleGroup":
        nm = require_non_empty(name, "name")
        aid = kwargs.pop("id", None) or str(uuid.uuid4())
        email = validate_email(kwargs.get("email"))
        return cls(id=aid, name=nm, email=email, **{k: v for k, v in kwargs.items() if k != "email"})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MuscleGroup":
        return cls(
            id=data["id"],
            name=data["name"],
            bio=data.get("bio", ""),
            birth_year=data.get("birth_year"),
            death_year=data.get("death_year"),
            website=data.get("website", ""),
            email=data.get("email"),
            aliases=list(data.get("aliases", [])),
            exercise_ids=list(data.get("exercise_ids", [])),
        )

    def display_name(self) -> str:
        if self.birth_year:
            return "%s (%d–%s)" % (self.name, self.birth_year, self.death_year or "")
        return self.name

    def add_exercise(self, exercise_id: str) -> None:
        if exercise_id not in self.exercise_ids:
            self.exercise_ids.append(exercise_id)

    def remove_exercise(self, exercise_id: str) -> None:
        if exercise_id in self.exercise_ids:
            self.exercise_ids.remove(exercise_id)

    def merge_aliases(self, other: List[str]) -> None:
        for a in other:
            al = a.strip()
            if al and al not in self.aliases:
                self.aliases.append(al)

    def matches(self, query: str) -> bool:
        q = query.lower()
        if q in self.name.lower():
            return True
        return any(q in a.lower() for a in self.aliases)


class MuscleGroupManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def list_all(self) -> List[MuscleGroup]:
        return sorted(self.storage.list_musclegroups(), key=lambda a: a.name.lower())

    def get(self, musclegroup_id: str) -> MuscleGroup:
        for a in self.list_all():
            if a.id == musclegroup_id:
                return a
        raise NotFoundError("musclegroup", musclegroup_id)

    def find_by_name(self, name: str) -> Optional[MuscleGroup]:
        nm = name.lower()
        for a in self.list_all():
            if a.name.lower() == nm:
                return a
            if any(nm == al.lower() for al in a.aliases):
                return a
        return None

    def create(self, name: str, **kwargs: Any) -> MuscleGroup:
        if self.find_by_name(name):
            raise ConflictError("musclegroup exists: %s" % name)
        au = MuscleGroup.create(name, **kwargs)
        self.storage.upsert_musclegroup(au)
        return au

    def find_or_create(self, name: str) -> MuscleGroup:
        au = self.find_by_name(name)
        if au:
            return au
        return self.create(name)

    def attach_exercise(self, musclegroup_id: str, exercise_id: str) -> None:
        au = self.get(musclegroup_id)
        exercise = self.storage.get_exercise(exercise_id)
        au.add_exercise(exercise.id)
        if musclegroup_id not in exercise.musclegroup_ids:
            exercise.musclegroup_ids.append(musclegroup_id)
        self.storage.upsert_musclegroup(au)
        self.storage.upsert_exercise(exercise)

    def exercises_for(self, musclegroup_id: str) -> List[str]:
        return [b.id for b in self.storage.list_exercises() if musclegroup_id in b.musclegroup_ids]

    def report(self) -> str:
        lines = ["=== MuscleGroups ==="]
        for au in self.list_all():
            n = len(self.exercises_for(au.id))
            lines.append("  %s — %d exercise(s)" % (au.display_name(), n))
        return "\n".join(lines)


def sort_musclegroups(musclegroups: List[MuscleGroup]) -> List[MuscleGroup]:
    return sorted(musclegroups, key=lambda a: a.name.lower())
