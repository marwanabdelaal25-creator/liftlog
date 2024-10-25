"""Named collections — curated groups beyond routines."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from liftlog.validators import require_non_empty
from liftlog.errors import NotFoundError, ConflictError

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Collection:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    description: str = ""
    exercise_ids: list[str] = field(default_factory=list)
    smart_query: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Collection":
        cid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=cid, name=name.strip(), **kwargs)

    def includes(self, exercise_id: str) -> bool:
        return exercise_id in self.exercise_ids

    def add(self, exercise_id: str) -> None:
        if exercise_id not in self.exercise_ids:
            self.exercise_ids.append(exercise_id)

    def remove(self, exercise_id: str) -> None:
        if exercise_id in self.exercise_ids:
            self.exercise_ids.remove(exercise_id)

    def size(self) -> int:
        return len(self.exercise_ids)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        kw = dict(data)
        if kw.get("created_at"):
            kw["created_at"] = datetime.fromisoformat(kw["created_at"])
        return cls(**{k: kw[k] for k in kw if k in cls.__dataclass_fields__})


class CollectionsManager:
    """CRUD wrapper — keeps storage calls in one place."""

    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Collection]:
        return self.storage.list_collections()

    def get(self, coll_id: str) -> Collection:
        for c in self.list_all():
            if c.id == coll_id:
                return c
        raise NotFoundError("collection", coll_id)

    def create(self, name: str, description: str = "") -> Collection:
        for c in self.list_all():
            if c.name.lower() == name.lower():
                raise ConflictError("collection exists: %s" % name)
        coll = Collection.create(name, description=description)
        self.storage.upsert_collection(coll)
        return coll

    def add_exercise(self, coll_id: str, exercise_id: str) -> None:
        coll = self.get(coll_id)
        self.storage.get_exercise(exercise_id)  # validate
        coll.add(exercise_id)
        self.storage.upsert_collection(coll)

    def remove_exercise(self, coll_id: str, exercise_id: str) -> None:
        coll = self.get(coll_id)
        coll.remove(exercise_id)
        self.storage.upsert_collection(coll)

    def exercises_in(self, coll_id: str) -> List[str]:
        return list(self.get(coll_id).exercise_ids)

    def find_by_name(self, name: str) -> Optional[Collection]:
        nm = name.lower()
        for c in self.list_all():
            if c.name.lower() == nm:
                return c
        return None

    # TODO: evaluate smart_query against SearchEngine
