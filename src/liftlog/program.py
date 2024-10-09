"""Exercise program tracking."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any, List, Optional, Set
import uuid

from liftlog.validators import require_non_empty
from liftlog.errors import NotFoundError, ConflictError
from liftlog.exercise import LiftStatus

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class Program:
    title: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    musclegroup_id: str | None = None
    total_planned: int | None = None
    description: str = ""
    exercise_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, "title")

    @classmethod
    def create(cls, title: str, **kwargs: Any) -> "Program":
        sid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=sid, title=title.strip(), **kwargs)

    def add_volume(self, exercise_id: str) -> None:
        if exercise_id not in self.exercise_ids:
            self.exercise_ids.append(exercise_id)

    def remove_volume(self, exercise_id: str) -> None:
        if exercise_id in self.exercise_ids:
            self.exercise_ids.remove(exercise_id)

    def completion_pct(self, retired_ids: Set[str]) -> float:
        if not self.exercise_ids:
            return 0.0
        got = sum(1 for bid in self.exercise_ids if bid in retired_ids)
        return round(100.0 * got / len(self.exercise_ids), 1)

    def next_unretired(self, retired_ids: Set[str] | "JsonStorage") -> Optional[str]:
        if hasattr(retired_ids, "list_exercises"):
            retired_ids = {
                b.id for b in retired_ids.list_exercises() if b.status == LiftStatus.RETIRED
            }
        for bid in self.exercise_ids:
            if bid not in retired_ids:
                return bid
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Program:
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


class ProgramManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Program]:
        return self.storage.list_programs()

    def get(self, program_id: str) -> Program:
        for s in self.list_all():
            if s.id == program_id:
                return s
        raise NotFoundError("program", program_id)

    def create(self, title: str, musclegroup_id: Optional[str] = None) -> Program:
        for s in self.list_all():
            if s.title.lower() == title.lower():
                raise ConflictError("program exists: %s" % title)
        ser = Program.create(title, musclegroup_id=musclegroup_id)
        self.storage.upsert_program(ser)
        return ser

    def add_exercise(self, program_id: str, exercise_id: str, index: Optional[float] = None) -> None:
        ser = self.get(program_id)
        ser.add_volume(exercise_id)
        try:
            exercise = self.storage.get_exercise(exercise_id)
            exercise.program_id = program_id
            if index is not None:
                exercise.program_index = index
            self.storage.upsert_exercise(exercise)
        except NotFoundError:
            pass
        self.storage.upsert_program(ser)

    def retired_ids(self) -> Set[str]:
        return {b.id for b in self.storage.list_exercises() if b.status == LiftStatus.RETIRED}

    def progress_report(self) -> str:
        lines = ["=== Program progress ==="]
        read = self.retired_ids()
        for ser in sorted(self.list_all(), key=lambda s: s.title.lower()):
            pct = ser.completion_pct(read)
            nxt = ser.next_unretired(self.storage)
            nxt_title = ""
            if nxt:
                try:
                    nxt_title = self.storage.get_exercise(nxt).name
                except NotFoundError:
                    nxt_title = nxt[:8]
            lines.append(
                "{title}: {pct:.0f}% ({n}/{tot}) next={nxt}".format(
                    title=ser.title,
                    pct=pct,
                    n=sum(1 for b in ser.exercise_ids if b in read),
                    tot=len(ser.exercise_ids),
                    nxt=nxt_title or "-",
                )
            )
        return "\n".join(lines)


class ProgramRegistry(ProgramManager):
    """Test-friendly alias for program operations."""

    def attach_exercise(self, program_id: str, exercise_id: str, index: Optional[float] = None) -> None:
        self.add_exercise(program_id, exercise_id, index=index)

    def find_by_title(self, query: str) -> Optional[Program]:
        ql = query.lower()
        for s in self.list_all():
            if ql in s.title.lower():
                return s
        return None

    def progress_report_lines(self) -> List[str]:
        return self.progress_report().splitlines()
