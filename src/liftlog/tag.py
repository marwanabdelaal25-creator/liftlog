"""Tag model for loose categorization."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

from liftlog.validators import validate_slug

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage
from liftlog.errors import NotFoundError


@dataclass
class Tag:
    id: str
    name: str
    slug: str
    color: str = "#718096"
    usage_count: int = 0

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Tag":
        slug = validate_slug(kwargs.pop("slug", None) or name)
        tid = kwargs.pop("id", None) or str(uuid.uuid4())
        return cls(id=tid, name=name.strip(), slug=slug, **kwargs)

    def bump(self, delta: int = 1) -> None:
        self.usage_count = max(0, self.usage_count + delta)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tag":
        return cls(
            id=data["id"],
            name=data["name"],
            slug=data.get("slug", validate_slug(data["name"])),
            color=data.get("color", "#718096"),
            usage_count=data.get("usage_count", 0),
        )


def recalc_usage(storage: "JsonStorage") -> None:
    """Recompute usage_count from exercise tag_ids — slow but accurate."""
    tags = storage.list_tags()
    counts: Dict[str, int] = {t.id: 0 for t in tags}
    for exercise in storage.list_exercises():
        for tid in exercise.tag_ids:
            if tid in counts:
                counts[tid] += 1
    for tag in tags:
        tag.usage_count = counts.get(tag.id, 0)
        storage.upsert_tag(tag)


def tag_cloud(storage: "JsonStorage", limit: int = 20) -> List[tuple[str, int]]:
    recalc_usage(storage)
    tags = sorted(storage.list_tags(), key=lambda t: t.usage_count, reverse=True)
    return [(t.name, t.usage_count) for t in tags[:limit]]


def find_tag_by_slug(storage: "JsonStorage", slug: str) -> Optional[Tag]:
    s = slug.lower()
    for t in storage.list_tags():
        if t.slug == s or t.name.lower() == s:
            return t
    return None


def merge_tags(storage: "JsonStorage", keep_id: str, drop_id: str) -> Tag:
    tags = storage.list_tags()
    keep = next((t for t in tags if t.id == keep_id), None)
    if keep is None:
        raise NotFoundError("tag", keep_id)
    for exercise in storage.list_exercises():
        if drop_id in exercise.tag_ids:
            exercise.tag_ids = [tid for tid in exercise.tag_ids if tid != drop_id]
            if keep_id not in exercise.tag_ids:
                exercise.tag_ids.append(keep_id)
            storage.upsert_exercise(exercise)
    storage.delete_tag(drop_id)
    recalc_usage(storage)
    return keep
