"""Equipment metadata and lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from liftlog.validators import require_non_empty, validate_url
from liftlog.errors import NotFoundError, ConflictError

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Equipment:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    country: str = ""
    website: str = ""
    imprint: str = ""

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")
        if self.website:
            self.website = validate_url(self.website)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Equipment":
        pid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=pid, name=name.strip(), **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Equipment:
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__ if k in data or k == "name"})

    def matches(self, q: str) -> bool:
        ql = q.lower()
        return ql in self.name.lower() or ql in self.imprint.lower()

    def display(self) -> str:
        if self.imprint and self.imprint != self.name:
            return "%s (%s)" % (self.imprint, self.name)
        return self.name


class EquipmentManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Equipment]:
        return self.storage.list_equipment()

    def get(self, pub_id: str) -> Equipment:
        for p in self.list_all():
            if p.id == pub_id:
                return p
        raise NotFoundError("equipment", pub_id)

    def find_by_name(self, name: str) -> Optional[Equipment]:
        nm = name.lower()
        for p in self.list_all():
            if p.name.lower() == nm:
                return p
        return None

    def create(self, name: str, **kwargs: Any) -> Equipment:
        existing = self.find_by_name(name)
        if existing:
            raise ConflictError("equipment exists: %s" % name)
        pub = Equipment.create(name, **kwargs)
        self.storage.upsert_equipment(pub)
        return pub

    def find_or_create(self, name: str) -> Equipment:
        p = self.find_by_name(name)
        if p:
            return p
        return self.create(name)

    def exercises_for(self, pub_id: str) -> List[str]:
        return [b.id for b in self.storage.list_exercises() if b.equipment_id == pub_id]

    def attach_to_exercise(self, exercise_id: str, equipment_name: str) -> None:
        pub = self.find_or_create(equipment_name)
        exercise = self.storage.get_exercise(exercise_id)
        exercise.equipment_id = pub.id
        self.storage.upsert_exercise(exercise)

    def search(self, query: str) -> List[Equipment]:
        return [p for p in self.list_all() if p.matches(query)]

    def summary(self) -> str:
        lines = ["Equipment (%d)" % len(self.list_all())]
        for p in sorted(self.list_all(), key=lambda x: x.name.lower())[:30]:
            n = len(self.exercises_for(p.id))
            lines.append("  %s — %d exercise(s)" % (p.display(), n))
        return "\n".join(lines)


class EquipmentIndex(EquipmentManager):
    """Index view used by importers and tests."""

    def list_all(self) -> List[Equipment]:
        return sorted(self.storage.list_equipment(), key=lambda p: p.name.lower())

    def assign_exercise(self, exercise_id: str, equipment_name: str) -> None:
        self.attach_to_exercise(exercise_id, equipment_name)

    def export_csv_lines(self) -> List[str]:
        lines = ["name,id,exercises"]
        for p in sorted(self.list_all(), key=lambda x: x.name.lower()):
            lines.append("%s,%s,%d" % (p.name, p.id, len(self.exercises_for(p.id))))
        return lines
