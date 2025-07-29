"""Recurring training reminders (e.g. deload checks, mobility work)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any, List, Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class RecurringRule:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    cadence: str = "daily"  # daily, weekly
    target_minutes: int = 30
    weekdays: list[int] = field(default_factory=lambda: list(range(7)))
    last_done: date | None = None
    enabled: bool = True
    goal_id: Optional[str] = None
    notes: str = ""

    def due(self, on: date | None = None) -> bool:
        if not self.enabled:
            return False
        today = on or date.today()
        if self.cadence == "weekly":
            if today.weekday() not in self.weekdays:
                return False
        if self.last_done == today:
            return False
        return True

    def mark_done(self, when: date | None = None) -> None:
        self.last_done = when or date.today()

    def next_due(self) -> date:
        base = self.last_done or date.today()
        if self.cadence == "daily":
            return base + timedelta(days=1)
        d = base + timedelta(days=1)
        for _ in range(8):
            if d.weekday() in self.weekdays:
                return d
            d += timedelta(days=1)
        return d

    def streak_days(self) -> int:
        if not self.last_done:
            return 0
        return (date.today() - self.last_done).days

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_done:
            d["last_done"] = self.last_done.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecurringRule":
        kw = dict(data)
        if kw.get("last_done"):
            kw["last_done"] = date.fromisoformat(kw["last_done"])
        return cls(**{k: kw[k] for k in kw if k in cls.__dataclass_fields__})


def load_rules(data: list[dict]) -> list[RecurringRule]:
    return [RecurringRule.from_dict(d) for d in data]


def due_rules(rules: list[RecurringRule]) -> list[RecurringRule]:
    return [r for r in rules if r.due()]


class RecurringScheduler:
    """Persist and evaluate recurring rules alongside goals."""

    KEY = "recurring"

    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def _raw(self) -> list[dict]:
        val = self.storage.raw_get(self.KEY)
        if isinstance(val, list):
            return val
        return []

    def list_rules(self) -> List[RecurringRule]:
        return load_rules(self._raw())

    def save_rules(self, rules: List[RecurringRule]) -> None:
        self.storage.raw_set(self.KEY, [r.to_dict() for r in rules])

    def add(self, rule: RecurringRule) -> None:
        rs = self.list_rules()
        rs.append(rule)
        self.save_rules(rs)

    def create(self, name: str, cadence: str = "daily", target_minutes: int = 30) -> RecurringRule:
        rule = RecurringRule(name=name, cadence=cadence, target_minutes=target_minutes)
        self.add(rule)
        return rule

    def mark_done(self, rule_id: str, when: date | None = None) -> RecurringRule:
        rs = self.list_rules()
        for r in rs:
            if r.id == rule_id:
                r.mark_done(when)
                self.save_rules(rs)
                return r
        from liftlog.errors import NotFoundError

        raise NotFoundError("recurring", rule_id)

    def disable(self, rule_id: str) -> None:
        rs = self.list_rules()
        for r in rs:
            if r.id == rule_id:
                r.enabled = False
                self.save_rules(rs)
                return

    def due_today(self) -> List[RecurringRule]:
        return due_rules(self.list_rules())

    def overdue(self) -> List[RecurringRule]:
        today = date.today()
        out = []
        for r in self.list_rules():
            if not r.enabled or not r.last_done:
                continue
            nxt = r.next_due()
            if nxt < today and r.due(today):
                out.append(r)
        return out

    def summary_text(self) -> str:
        due = self.due_today()
        if not due:
            return "No recurring habits due today — nice work."
        lines = ["Due today:"]
        for r in due:
            lines.append("  - %s (%d min target)" % (r.name, r.target_minutes))
        od = self.overdue()
        if od:
            lines.append("")
            lines.append("Overdue:")
            for r in od:
                lines.append("  ! %s (last %s)" % (r.name, r.last_done))
        return "\n".join(lines)

    def report(self) -> str:
        rules = self.list_rules()
        if not rules:
            return "No recurring rules configured."
        lines = ["=== Recurring habits ==="]
        for r in rules:
            flag = "on" if r.enabled else "off"
            lines.append(
                "[%s] %s — %s, %dm, last=%s" % (
                    flag,
                    r.name,
                    r.cadence,
                    r.target_minutes,
                    r.last_done or "never",
                )
            )
        return "\n".join(lines)

    # TODO: tie goals to recurring rules via goal_id
