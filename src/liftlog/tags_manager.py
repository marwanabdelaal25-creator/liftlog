"""Higher-level tag CRUD and exercise tagging."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from liftlog.tag import Tag
from liftlog.errors import NotFoundError, ConflictError, ValidationError
from liftlog.validators import require_non_empty, validate_slug

if TYPE_CHECKING:
    from liftlog.exercise import Exercise
    from liftlog.storage import JsonStorage


class TagsManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def create(self, name: str, color: str = "#6b7280") -> Tag:
        name = require_non_empty(name, "name")
        for t in self.storage.list_tags():
            if t.name.lower() == name.lower():
                raise ConflictError("tag already exists: %s" % name)
        tag = Tag.create(name, color=color)
        self.storage.upsert_tag(tag)
        return tag

    def delete(self, tag_id: str) -> None:
        if not any(t.id == tag_id for t in self.storage.list_tags()):
            raise NotFoundError("tag", tag_id)
        for exercise in self.storage.list_exercises():
            if tag_id in exercise.tag_ids:
                exercise.tag_ids.remove(tag_id)
                self.storage.upsert_exercise(exercise)
        self.storage.delete_tag(tag_id)

    def rename(self, tag_id: str, new_name: str) -> Tag:
        tags = self.storage.list_tags()
        for i, tag in enumerate(tags):
            if tag.id == tag_id:
                tag.name = require_non_empty(new_name, "name")
                tag.slug = validate_slug(new_name)
                self.storage.upsert_tag(tag)
                return tag
        raise NotFoundError("tag", tag_id)

    def attach(self, exercise_id: str, tag_ref: str) -> "Exercise":
        exercise = self.storage.get_exercise(exercise_id)
        tag = self.get_by_slug(tag_ref)
        if tag is None:
            tag = self.find_or_create(tag_ref)
        elif not any(t.id == tag.id for t in self.storage.list_tags()):
            self.storage.upsert_tag(tag)
        if tag.id not in exercise.tag_ids:
            exercise.tag_ids.append(tag.id)
            self.storage.upsert_exercise(exercise)
            tag.bump(1)
            self.storage.upsert_tag(tag)
        return exercise

    def detach(self, exercise_id: str, tag_id: str) -> None:
        exercise = self.storage.get_exercise(exercise_id)
        if tag_id in exercise.tag_ids:
            exercise.tag_ids.remove(tag_id)
            self.storage.upsert_exercise(exercise)

    def find_or_create(self, name: str) -> Tag:
        nm = name.strip().lower()
        for t in self.storage.list_tags():
            if t.name.lower() == nm or t.slug == validate_slug(name):
                return t
        return self.create(name)

    def tags_for_exercise(self, exercise_id: str) -> list[Tag]:
        exercise = self.storage.get_exercise(exercise_id)
        by_id = {t.id: t for t in self.storage.list_tags()}
        return [by_id[tid] for tid in exercise.tag_ids if tid in by_id]

    def usage_counts(self) -> Dict[str, int]:
        cnt: Dict[str, int] = {}
        for t in self.storage.list_tags():
            c = sum(1 for b in self.storage.list_exercises() if t.id in b.tag_ids)
            cnt[t.name] = c
        return cnt

    def list_all(self) -> list[Tag]:
        return sorted(self.storage.list_tags(), key=lambda t: t.name.lower())

    get_or_create = find_or_create

    def get_by_slug(self, slug: str) -> Tag | None:
        from liftlog.tag import find_tag_by_slug

        return find_tag_by_slug(self.storage, slug)

    def merge_tags(self, drop_id: str, keep_id: str) -> Tag:
        if drop_id == keep_id:
            raise ValidationError("cannot merge tag with itself")
        from liftlog.tag import merge_tags as _merge

        return _merge(self.storage, keep_id, drop_id)

    def exercises_for_tag(self, tag_ref: str) -> list:
        tag = None
        for t in self.storage.list_tags():
            if t.id == tag_ref or t.slug == tag_ref or t.name.lower() == tag_ref.lower():
                tag = t
                break
        if tag is None:
            return []
        return [b for b in self.storage.list_exercises() if tag.id in b.tag_ids]

    def unused(self) -> list[Tag]:
        used = {tid for b in self.storage.list_exercises() for tid in b.tag_ids}
        return [t for t in self.storage.list_tags() if t.id not in used]
