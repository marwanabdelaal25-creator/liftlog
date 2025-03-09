"""Memorable quotes from exercises."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import TYPE_CHECKING, Any, List, Optional
import random
import uuid

from liftlog.validators import require_non_empty
from liftlog.errors import NotFoundError

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Quote:
    text: str
    exercise_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scene: int | None = None
    speaker: str = ""
    added_at: date = field(default_factory=date.today)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.text = require_non_empty(self.text, "text")

    @classmethod
    def create(cls, text: str, exercise_id: str, **kwargs: Any) -> "Quote":
        qid = kwargs.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(id=qid, text=text.strip(), exercise_id=exercise_id, **kwargs)

    def preview(self, n: int = 80) -> str:
        t = self.text.replace("\n", " ")
        if len(t) <= n:
            return t
        return t[: n - 1] + "…"

    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["added_at"] = self.added_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Quote:
        kw = dict(data)
        if kw.get("added_at"):
            kw["added_at"] = date.fromisoformat(kw["added_at"])
        return cls(**{k: kw[k] for k in kw if k in cls.__dataclass_fields__})


class QuotesManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def add(self, quote: Quote) -> Quote:
        self.storage.add_quote(quote)
        return quote

    def list_for_exercise(self, exercise_id: str) -> List[Quote]:
        return self.storage.list_quotes(exercise_id)

    def get(self, quote_id: str) -> Quote:
        for q in self.storage.list_quotes():
            if q.id == quote_id:
                return q
        raise NotFoundError("quote", quote_id)

    def search(self, query: str) -> List[Quote]:
        q = query.lower()
        out = []
        for quote in self.storage.list_quotes():
            if q in quote.text.lower() or q in quote.speaker.lower():
                out.append(quote)
        return out

    def random_quote(self, exercise_id: Optional[str] = None) -> Optional[Quote]:
        pool = self.storage.list_quotes(exercise_id)
        if not pool:
            return None
        return random.choice(pool)

    def daily_quote(self) -> Optional[Quote]:
        """Deterministic-ish pick by day — same quote all day."""
        all_q = self.storage.list_quotes()
        if not all_q:
            return None
        idx = date.today().toordinal() % len(all_q)
        return all_q[idx]

    def delete(self, quote_id: str) -> None:
        quotes = [q.to_dict() for q in self.storage.list_quotes() if q.id != quote_id]
        if len(quotes) == len(self.storage.list_quotes()):
            raise NotFoundError("quote", quote_id)
        self.storage.raw_set("quotes", quotes)

    def by_tag(self, tag: str) -> List[Quote]:
        tg = tag.lower()
        return [q for q in self.storage.list_quotes() if tg in [t.lower() for t in q.tags]]

    def export_text(self, exercise_id: Optional[str] = None) -> str:
        lines = ["=== Quotes ==="]
        for q in self.storage.list_quotes(exercise_id):
            exercise = None
            try:
                exercise = self.storage.get_exercise(q.exercise_id)
            except NotFoundError:
                pass
            title = exercise.name if exercise else q.exercise_id[:8]
            lines.append("")
            lines.append('"%s"' % q.preview(200))
            meta = "— %s" % title
            if q.scene:
                meta += ", scene %d" % q.scene
            if q.speaker:
                meta += " (%s)" % q.speaker
            lines.append(meta)
        return "\n".join(lines)

    def stats(self) -> dict[str, int]:
        qs = self.storage.list_quotes()
        return {
            "total": len(qs),
            "exercises_with_quotes": len({q.exercise_id for q in qs}),
            "words": sum(q.word_count() for q in qs),
        }
