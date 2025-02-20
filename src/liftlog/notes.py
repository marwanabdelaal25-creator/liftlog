"""Free-form notes attached to exercises or worksets."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from liftlog.validators import require_non_empty
from liftlog.errors import NotFoundError

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Note:
    body: str
    exercise_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    workset_id: str | None = None
    pinned: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.body = require_non_empty(self.body, "body")

    @classmethod
    def create(cls, body: str, exercise_id: str, **kwargs: Any) -> "Note":
        nid = kwargs.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(id=nid, body=body.strip(), exercise_id=exercise_id, **kwargs)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def excerpt(self, mx: int = 120) -> str:
        s = self.body.strip()
        return s if len(s) <= mx else s[: mx - 1] + "…"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            d["updated_at"] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Note:
        kw = dict(data)
        kw["created_at"] = datetime.fromisoformat(kw["created_at"])
        if kw.get("updated_at"):
            kw["updated_at"] = datetime.fromisoformat(kw["updated_at"])
        return cls(**{k: kw[k] for k in kw if k in cls.__dataclass_fields__})


class NotesManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def add(self, note: Note) -> Note:
        self.storage.add_note(note)
        return note

    def update(self, note_id: str, body: str, title: Optional[str] = None) -> Note:
        notes_raw = self.storage.raw_get("notes") or []
        for i, nd in enumerate(notes_raw):
            if nd["id"] == note_id:
                n = Note.from_dict(nd)
                n.body = require_non_empty(body, "body")
                if title is not None:
                    n.title = title
                n.touch()
                notes_raw[i] = n.to_dict()
                self.storage.raw_set("notes", notes_raw)
                return n
        raise NotFoundError("note", note_id)

    def delete(self, note_id: str) -> None:
        notes = [n.to_dict() for n in self.storage.list_notes() if n.id != note_id]
        if len(notes) == len(self.storage.list_notes()):
            raise NotFoundError("note", note_id)
        self.storage.raw_set("notes", notes)

    def list_for_exercise(self, exercise_id: str) -> List[Note]:
        notes = self.storage.list_notes(exercise_id)
        notes.sort(key=lambda n: (not n.pinned, n.created_at), reverse=True)
        return notes

    def pinned(self, exercise_id: Optional[str] = None) -> List[Note]:
        pool = self.storage.list_notes(exercise_id)
        return [n for n in pool if n.pinned]

    def search(self, query: str) -> List[Note]:
        q = query.lower()
        return [
            n for n in self.storage.list_notes()
            if q in n.body.lower() or q in n.title.lower()
        ]

    def pin(self, note_id: str, pinned: bool = True) -> Note:
        notes_raw = self.storage.raw_get("notes") or []
        for i, nd in enumerate(notes_raw):
            if nd["id"] == note_id:
                n = Note.from_dict(nd)
                n.pinned = pinned
                n.touch()
                notes_raw[i] = n.to_dict()
                self.storage.raw_set("notes", notes_raw)
                return n
        raise NotFoundError("note", note_id)

    def export_markdown(self, exercise_id: str) -> str:
        try:
            exercise = self.storage.get_exercise(exercise_id)
            title = exercise.name
        except NotFoundError:
            title = exercise_id
        lines = ["# Notes: %s" % title, ""]
        for n in self.list_for_exercise(exercise_id):
            hdr = n.title or n.created_at.date().isoformat()
            pin = " 📌" if n.pinned else ""
            lines.append("## %s%s" % (hdr, pin))
            lines.append("")
            lines.append(n.body)
            lines.append("")
        return "\n".join(lines)

    # HACK: notes_count on exercise can drift if notes deleted out-of-band
