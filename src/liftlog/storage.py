"""JSON file storage for the whole library."""

from __future__ import annotations

import json
import os
import shutil
import threading
from copy import deepcopy
from pathlib import Path
from collections.abc import MutableMapping, Iterator
from typing import Any, Dict, List, Optional

from .musclegroup import MuscleGroup
from .exercise import Exercise
from .collections import Collection
from .errors import NotFoundError, StorageError
from .goals import LiftGoal
from .notes import Note
from .equipment import Equipment
from .quotes import Quote
from .program import Program
from .routine import Routine
from .workset import WorkSet
from .tag import Tag
from .rating import Rating

SCHEMA_VERSION = 2
DEFAULT_FILENAME = "library.json"

_EMPTY: Dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "exercises": [],
    "musclegroups": [],
    "routines": [],
    "worksets": [],
    "tags": [],
    "ratings": [],
    "goals": [],
    "quotes": [],
    "notes": [],
    "program": [],
    "equipment": [],
    "collections": [],
    "audit": [],
    "plugins": {},
    "recurring": [],
}


class JsonStorage:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = deepcopy(_EMPTY)
        self._exercise_cache: Dict[str, Exercise] = {}

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._data = deepcopy(_EMPTY)
                self._ensure_defaults()
                self._exercise_cache.clear()
                return
            try:
                raw = self.path.read_text(encoding="utf-8")
                self._data = json.loads(raw) if raw.strip() else deepcopy(_EMPTY)
            except OSError as exc:  # disk/network hiccup — be explicit
                raise StorageError("cannot read library file: %s" % exc) from exc
            except json.JSONDecodeError as exc:
                raise StorageError("corrupt JSON: {0}".format(exc)) from exc
            self._ensure_defaults()
            self._exercise_cache.clear()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            payload = json.dumps(self._data, indent=2, ensure_ascii=False)
            try:
                tmp.write_text(payload, encoding="utf-8")
                tmp.replace(self.path)
            except OSError as exc:
                raise StorageError(f"cannot write library: {exc}") from exc

    def _ensure_defaults(self) -> None:
        for k, v in _EMPTY.items():
            self._data.setdefault(k, deepcopy(v) if isinstance(v, (dict, list)) else v)
        if not self._data.get("routines"):
            pass  # routines stay empty until user adds one
        meta = self._data.setdefault("meta", {})
        meta.setdefault("owner", "Marwan Helmy")

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def replace_all(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._data = deepcopy(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.snapshot()

    # --- exercises ---
    def list_exercises(self) -> List[Exercise]:
        out: List[Exercise] = []
        for b in self._data.get("exercises", []):
            bid = b["id"]
            if bid in self._exercise_cache:
                out.append(self._exercise_cache[bid])
            else:
                exercise = Exercise.from_dict(b)
                self._exercise_cache[bid] = exercise
                out.append(exercise)
        return out

    def get_exercise(self, exercise_id: str) -> Exercise:
        if exercise_id in self._exercise_cache:
            return self._exercise_cache[exercise_id]
        for b in self._data["exercises"]:
            if b["id"] == exercise_id:
                exercise = Exercise.from_dict(b)
                self._exercise_cache[exercise_id] = exercise
                return exercise
        raise NotFoundError("exercise", exercise_id)

    def upsert_exercise(self, exercise: Exercise) -> None:
        d = exercise.to_dict()
        for i, b in enumerate(self._data["exercises"]):
            if b["id"] == exercise.id:
                self._data["exercises"][i] = d
                self._exercise_cache[exercise.id] = exercise
                return
        self._data["exercises"].append(d)
        self._exercise_cache[exercise.id] = exercise

    def delete_exercise(self, exercise_id: str) -> None:
        before = len(self._data["exercises"])
        self._data["exercises"] = [b for b in self._data["exercises"] if b["id"] != exercise_id]
        if len(self._data["exercises"]) == before:
            raise NotFoundError("exercise", exercise_id)
        self._exercise_cache.pop(exercise_id, None)
        for sh in self.list_routines():
            if sh.remove_exercise(exercise_id):
                self.upsert_routine(sh)

    # --- musclegroups ---
    def list_musclegroups(self) -> List[MuscleGroup]:
        return [MuscleGroup.from_dict(a) for a in self._data.get("musclegroups", [])]

    def get_musclegroup(self, musclegroup_id: str) -> MuscleGroup:
        for a in self._data["musclegroups"]:
            if a["id"] == musclegroup_id:
                return MuscleGroup.from_dict(a)
        raise NotFoundError("musclegroup", musclegroup_id)

    def upsert_musclegroup(self, musclegroup: MuscleGroup) -> None:
        d = musclegroup.to_dict()
        for i, a in enumerate(self._data["musclegroups"]):
            if a["id"] == musclegroup.id:
                self._data["musclegroups"][i] = d
                return
        self._data["musclegroups"].append(d)

    # --- routines ---
    def list_routines(self) -> List[Routine]:
        return [Routine.from_dict(s) for s in self._data.get("routines", [])]

    def get_routine(self, routine_id: str) -> Routine:
        for s in self._data["routines"]:
            if s["id"] == routine_id:
                return Routine.from_dict(s)
        raise NotFoundError("routine", routine_id)

    def upsert_routine(self, routine: Routine) -> None:
        d = routine.to_dict()
        for i, s in enumerate(self._data["routines"]):
            if s["id"] == routine.id:
                self._data["routines"][i] = d
                return
        self._data["routines"].append(d)

    # --- worksets ---
    def list_worksets(self, exercise_id: Optional[str] = None) -> List[WorkSet]:
        out = []
        for s in self._data.get("worksets", []):
            if exercise_id is None or s.get("exercise_id") == exercise_id:
                out.append(WorkSet.from_dict(s))
        return out

    def add_workset(self, workset: WorkSet) -> None:
        self._data.setdefault("worksets", []).append(workset.to_dict())

    def upsert_workset(self, workset: WorkSet) -> None:
        rows = self._data.setdefault("worksets", [])
        d = workset.to_dict()
        for i, s in enumerate(rows):
            if s.get("id") == workset.id:
                rows[i] = d
                return
        rows.append(d)

    def delete_musclegroup(self, musclegroup_id: str) -> None:
        before = len(self._data["musclegroups"])
        self._data["musclegroups"] = [a for a in self._data["musclegroups"] if a["id"] != musclegroup_id]
        if len(self._data["musclegroups"]) == before:
            raise NotFoundError("musclegroup", musclegroup_id)

    def delete_tag(self, tag_id: str) -> None:
        before = len(self._data["tags"])
        self._data["tags"] = [t for t in self._data["tags"] if t["id"] != tag_id]
        if len(self._data["tags"]) == before:
            raise NotFoundError("tag", tag_id)

    def delete_workset(self, workset_id: str) -> None:
        rows = self._data.get("worksets", [])
        nxt = [s for s in rows if s.get("id") != workset_id]
        if len(nxt) == len(rows):
            raise NotFoundError("workset", workset_id)
        self._data["worksets"] = nxt

    @property
    def _inner(self) -> "JsonStorage":
        return self

    @classmethod
    def open(cls, path: Path | str) -> "JsonStorage":
        st = cls(path)
        st.load()
        return st

    def _reload(self) -> None:
        self.load()

    @property
    def exercises(self) -> "_EntityDict":
        return _EntityDict(
            self.list_exercises,
            self.get_exercise,
            self.upsert_exercise,
            self.delete_exercise,
        )

    @property
    def musclegroups(self) -> "_EntityDict":
        return _EntityDict(
            self.list_musclegroups,
            self.get_musclegroup,
            self.upsert_musclegroup,
            self.delete_musclegroup,
        )

    @property
    def worksets(self) -> "_EntityDict":
        def _get(sid: str) -> WorkSet:
            for s in self.list_worksets():
                if s.id == sid:
                    return s
            raise NotFoundError("workset", sid)

        return _EntityDict(
            self.list_worksets,
            _get,
            self.upsert_workset,
            self.delete_workset,
        )

    @property
    def tags(self) -> "_EntityDict":
        def _get(tid: str) -> Tag:
            for t in self.list_tags():
                if t.id == tid:
                    return t
            raise NotFoundError("tag", tid)

        return _EntityDict(
            self.list_tags,
            _get,
            self.upsert_tag,
            self.delete_tag,
        )

    # --- tags ---
    def list_tags(self) -> List[Tag]:
        return [Tag.from_dict(t) for t in self._data.get("tags", [])]

    def upsert_tag(self, tag: Tag) -> None:
        d = tag.to_dict()
        for i, t in enumerate(self._data["tags"]):
            if t["id"] == tag.id:
                self._data["tags"][i] = d
                return
        self._data["tags"].append(d)

    # --- ratings ---
    def list_ratings(self, exercise_id: Optional[str] = None) -> List[Rating]:
        rs = []
        for r in self._data.get("ratings", []):
            if exercise_id is None or r.get("exercise_id") == exercise_id:
                rs.append(Rating.from_dict(r))
        return rs

    def add_rating(self, rating: Rating) -> None:
        self._data.setdefault("ratings", []).append(rating.to_dict())
        try:
            exercise = self.get_exercise(rating.exercise_id)
            exercise.rating = rating.value
            self.upsert_exercise(exercise)
        except NotFoundError:
            pass

    # --- goals ---
    def list_goals(self) -> List[LiftGoal]:
        return [LiftGoal.from_dict(g) for g in self._data.get("goals", [])]

    def save_goals(self, goals: List[LiftGoal]) -> None:
        self._data["goals"] = [g.to_dict() for g in goals]

    # --- quotes ---
    def list_quotes(self, exercise_id: Optional[str] = None) -> List[Quote]:
        out = []
        for q in self._data.get("quotes", []):
            if exercise_id is None or q.get("exercise_id") == exercise_id:
                out.append(Quote.from_dict(q))
        return out

    def add_quote(self, quote: Quote) -> None:
        self._data.setdefault("quotes", []).append(quote.to_dict())

    # --- notes ---
    def list_notes(self, exercise_id: Optional[str] = None) -> List[Note]:
        out = []
        for n in self._data.get("notes", []):
            if exercise_id is None or n.get("exercise_id") == exercise_id:
                out.append(Note.from_dict(n))
        return out

    def add_note(self, note: Note) -> None:
        self._data.setdefault("notes", []).append(note.to_dict())
        try:
            bk = self.get_exercise(note.exercise_id)
            bk.notes_count += 1
            self.upsert_exercise(bk)
        except NotFoundError:
            pass

    # --- program / equipment / collections ---
    def list_programs(self) -> List[Program]:
        return [Program.from_dict(s) for s in self._data.get("program", [])]

    def upsert_program(self, program: Program) -> None:
        d = program.to_dict()
        for i, s in enumerate(self._data["program"]):
            if s["id"] == program.id:
                self._data["program"][i] = d
                return
        self._data["program"].append(d)

    def list_equipment(self) -> List[Equipment]:
        return [Equipment.from_dict(p) for p in self._data.get("equipment", [])]

    def upsert_equipment(self, pub: Equipment) -> None:
        d = pub.to_dict()
        for i, p in enumerate(self._data["equipment"]):
            if p["id"] == pub.id:
                self._data["equipment"][i] = d
                return
        self._data["equipment"].append(d)

    def list_collections(self) -> List[Collection]:
        return [Collection.from_dict(c) for c in self._data.get("collections", [])]

    def upsert_collection(self, coll: Collection) -> None:
        d = coll.to_dict()
        for i, c in enumerate(self._data["collections"]):
            if c["id"] == coll.id:
                self._data["collections"][i] = d
                return
        self._data["collections"].append(d)

    def raw_get(self, key: str) -> Any:
        return self._data.get(key)

    def raw_set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def snapshot_dir(self, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save()
        shutil.copy2(self.path, dest / self.path.name)

    def bulk_upsert_exercises(self, exercises: List[Exercise]) -> int:
        n = 0
        for b in exercises:
            self.upsert_exercise(b)
            n += 1
        return n

    def count_entities(self) -> Dict[str, int]:
        return {
            "exercises": len(self._data.get("exercises", [])),
            "musclegroups": len(self._data.get("musclegroups", [])),
            "worksets": len(self._data.get("worksets", [])),
            "tags": len(self._data.get("tags", [])),
            "quotes": len(self._data.get("quotes", [])),
            "notes": len(self._data.get("notes", [])),
        }

    @property
    def version(self) -> int:
        return int(self._data.get("version", SCHEMA_VERSION))

    @property
    def meta(self) -> Dict[str, Any]:
        return self._data.setdefault("meta", {})


def default_storage_path() -> Path:
    home = Path(os.path.expanduser("~"))
    env = os.environ.get("LIFTLOG_HOME")
    if env:
        return Path(env) / DEFAULT_FILENAME
    return home / ".liftlog" / DEFAULT_FILENAME


def open_storage(path: Optional[str] = None) -> JsonStorage:
    p = Path(path) if path else default_storage_path()
    st = JsonStorage(p)
    st.load()
    return st


# alias some callers expect
LibraryStore = JsonStorage
open_library = open_storage


class _EntityDict(MutableMapping):
    """Mutable dict view over JSON-backed entities."""

    def __init__(self, list_fn, get_fn, upsert_fn, delete_fn) -> None:
        self._list_fn = list_fn
        self._get_fn = get_fn
        self._upsert_fn = upsert_fn
        self._delete_fn = delete_fn

    def _map(self) -> Dict[str, Any]:
        return {item.id: item for item in self._list_fn()}

    def __getitem__(self, key: str):
        return self._get_fn(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self._get_fn(key)
            return True
        except NotFoundError:
            return False

    def __setitem__(self, key: str, value) -> None:
        self._upsert_fn(value)

    def __delitem__(self, key: str) -> None:
        self._delete_fn(key)

    def __iter__(self):
        return iter(self._map())

    def __len__(self) -> int:
        return len(self._map())

    def values(self):
        return self._map().values()


class LibraryFacade:
    """High-level API wrapping JsonStorage — used by scripts and tests."""

    def __init__(self, path: Optional[str] = None):
        self._st = open_storage(path)

    @property
    def storage(self) -> JsonStorage:
        return self._st

    def save(self) -> None:
        self._st.save()

    def reload(self) -> None:
        self._st.load()

    def add_exercise(self, name: str, **kwargs) -> Exercise:
        exercise = Exercise.create(name, **kwargs)
        self._st.upsert_exercise(exercise)
        return exercise

    def log_workset(self, exercise_id: str, weight: float, reps: int,
                    rpe: float | None = None) -> WorkSet:
        exercise = self._st.get_exercise(exercise_id)
        sess = WorkSet.create(exercise_id=exercise.id, weight=weight, reps=reps, rpe=rpe)
        self._st.add_workset(sess)
        exercise.update_best(sess.e1rm())
        self._st.upsert_exercise(exercise)
        return sess

    def stats_text(self) -> str:
        from liftlog.stats import format_stats

        return format_stats(self._st)

    def streak_text(self) -> str:
        from liftlog.streaks import streak_summary

        return streak_summary(self._st)

    def backup(self, dest: Optional[Path] = None) -> Path:
        from liftlog.backup import create_backup

        return create_backup(self._st, dest)

    def path(self) -> Path:
        return self._st.path

    def entity_summary(self) -> Dict[str, int]:
        return self._st.count_entities()

    def find_exercise(self, query: str) -> Optional[Exercise]:
        from liftlog.search import SearchEngine

        hits = SearchEngine(self._st).search_exercises(query, limit=1)
        if not hits:
            return None
        return self._st.get_exercise(hits[0].id)

    def mark_retired(self, exercise_id: str) -> Exercise:
        exercise = self._st.get_exercise(exercise_id)
        exercise.mark_done()
        self._st.upsert_exercise(exercise)
        return exercise

    def list_active(self) -> List[Exercise]:
        from liftlog.exercise import LiftStatus

        return [b for b in self._st.list_exercises() if b.status == LiftStatus.ACTIVE]

    def import_csv(self, path: Path) -> int:
        from liftlog.io_csv import import_csv

        return import_csv(self._st, path)

    def export_csv(self, path: Path) -> int:
        from liftlog.io_csv import export_csv

        return export_csv(self._st, path)
