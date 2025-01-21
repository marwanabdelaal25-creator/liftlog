"""Search exercises, musclegroups, notes, and quotes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern

from liftlog.musclegroup import MuscleGroup
from liftlog.exercise import Exercise
from liftlog.notes import Note
from liftlog.quotes import Quote
from liftlog.storage import JsonStorage


@dataclass
class SearchHit:
    kind: str
    id: str
    title: str
    score: float
    snippet: str = ""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


# FIXME: tune threshold — 0.15 feels arbitrary in practice

def _score(query: str, text: str) -> float:
    q = _norm(query)
    t = _norm(text)
    if not q or not t:
        return 0.0
    if q == t:
        return 1.0
    if q in t:
        return 0.8 + 0.2 * (len(q) / len(t))
    qt = set(q.split())
    tt = set(t.split())
    if not qt:
        return 0.0
    overlap = len(qt & tt) / len(qt)
    return overlap * 0.6


class SearchEngine:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def search_exercises(self, query: str, limit: int = 20) -> List[SearchHit]:
        if not query or not query.strip():
            return []
        hits: List[SearchHit] = []
        for exercise in self.storage.list_exercises():
            sc = _score(query, exercise.name)
            if exercise.wger and query.replace("-", "") in (exercise.wger or ""):
                sc = max(sc, 0.9)
            if sc > 0.15:
                hits.append(
                    SearchHit("exercise", exercise.id, exercise.name, sc, exercise.status.value)
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def search_musclegroups(self, query: str, limit: int = 10) -> List[SearchHit]:
        out = []
        for a in self.storage.list_musclegroups():
            sc = _score(query, a.name)
            if sc > 0.2:
                out.append(SearchHit("musclegroup", a.id, a.name, sc))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_notes(self, query: str, limit: int = 15) -> List[SearchHit]:
        out = []
        for n in self.storage.list_notes():
            sc = max(_score(query, n.body), _score(query, n.title))
            if sc > 0.2:
                out.append(SearchHit("note", n.id, n.title or n.excerpt(40), sc, n.excerpt(80)))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_quotes(self, query: str, limit: int = 15) -> List[SearchHit]:
        out = []
        for q in self.storage.list_quotes():
            sc = _score(query, q.text)
            if sc > 0.2:
                out.append(SearchHit("quote", q.id, q.preview(50), sc, q.preview(100)))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_all(self, query: str) -> List[SearchHit]:
        hits = self.search_exercises(query, limit=30)
        hits.extend(self.search_musclegroups(query, limit=10))
        hits.extend(self.search_notes(query, limit=10))
        hits.extend(self.search_quotes(query, limit=10))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits

    def filter_exercises(
        self,
        status: Optional[str] = None,
        tag_id: Optional[str] = None,
        routine_id: Optional[str] = None,
    ) -> List[Exercise]:
        exercises = self.storage.list_exercises()
        if status:
            exercises = [b for b in exercises if b.status.value == status]
        if tag_id:
            exercises = [b for b in exercises if tag_id in b.tag_ids]
        if routine_id:
            exercises = [b for b in exercises if routine_id in b.routine_ids]
        return exercises

    def advanced(self, expr: str) -> List[Exercise]:
        """Tiny DSL: status:active tag:main category:compound name:squat wger:615"""
        tokens = expr.split()
        pool = list(self.storage.list_exercises())
        tag_by_name = {t.name.lower(): t.id for t in self.storage.list_tags()}
        for tok in tokens:
            if ":" not in tok:
                q = _norm(tok)
                pool = [b for b in pool if _score(q, b.name) > 0.15 or b.matches(tok)]
                continue
            key, val = tok.split(":", 1)
            key, val = key.lower(), val.lower()
            if key == "status":
                pool = [b for b in pool if b.status.value == val]
            elif key == "tag":
                tid = tag_by_name.get(val)
                if tid:
                    pool = [b for b in pool if tid in b.tag_ids]
            elif key == "name":
                pool = [b for b in pool if val in b.name.lower()]
            elif key == "category":
                pool = [b for b in pool if b.category.lower() == val]
            elif key == "wger":
                pool = [b for b in pool if b.wger and val in b.wger]
        return sorted(pool, key=lambda b: b.name.lower())

    def regex_filter(self, pattern: str, field: str = "name") -> List[Exercise]:
        pat: Pattern[str] = re.compile(pattern, re.IGNORECASE)
        res = []
        for b in self.storage.list_exercises():
            val = getattr(b, field, "") or ""
            if pat.search(str(val)):
                res.append(b)
        return res

    def highlight(self, text: str, query: str) -> str:
        if not query:
            return text
        pat = re.compile(re.escape(query), re.I)
        return pat.sub(lambda m: "**%s**" % m.group(0), text)

    def suggest(self, prefix: str, limit: int = 8) -> List[str]:
        """Title prefix suggestions for interactive CLI."""
        p = prefix.lower()
        titles = sorted({b.name for b in self.storage.list_exercises()})
        out = [t for t in titles if t.lower().startswith(p)]
        if len(out) < limit:
            out.extend([t for t in titles if p in t.lower() and t not in out][: limit - len(out)])
        return out[:limit]

    def recent_exercises(self, days: int = 90) -> List[Exercise]:
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)
        out = []
        for b in self.storage.list_exercises():
            if b.started_at:
                try:
                    if date.fromisoformat(b.started_at[:10]) >= cutoff:
                        out.append(b)
                except ValueError:
                    pass
        return sorted(out, key=lambda b: b.started_at or "", reverse=True)
