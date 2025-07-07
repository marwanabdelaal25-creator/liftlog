"""Audit trail persisted inside library JSON storage."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

if TYPE_CHECKING:
    from liftlog.storage import JsonStorage


@dataclass
class AuditEntry:
    id: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: str
    user: str = "local"
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def record(
        cls,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> "AuditEntry":
        return cls(
            id=str(uuid.uuid4()),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            timestamp=datetime.utcnow().isoformat(),
            details=details or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            action=data["action"],
            entity_type=data.get("entity_type", data.get("entity", "")),
            entity_id=data["entity_id"],
            timestamp=data.get("timestamp", data.get("ts", datetime.utcnow().isoformat())),
            user=data.get("user", "local"),
            details=data.get("details", data.get("detail", {})) or {},
        )


class AuditLog:
    def __init__(self, storage: "JsonStorage", max_entries: int = 1000):
        self.storage = storage
        self.max_entries = max_entries

    def _load(self) -> List[AuditEntry]:
        raw = self.storage.raw_get("audit") or []
        return [AuditEntry.from_dict(e) for e in raw]

    def _save(self, entries: List[AuditEntry]) -> None:
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries :]
        self.storage.raw_set("audit", [e.to_dict() for e in entries])

    def append(self, entry: AuditEntry) -> None:
        entries = self._load()
        entries.append(entry)
        self._save(entries)

    def log_create(self, entity_type: str, entity_id: str, **details: Any) -> AuditEntry:
        entry = AuditEntry.record("create", entity_type, entity_id, details)
        self.append(entry)
        return entry

    def log_update(self, entity_type: str, entity_id: str, **details: Any) -> AuditEntry:
        entry = AuditEntry.record("update", entity_type, entity_id, details)
        self.append(entry)
        return entry

    def log_delete(self, entity_type: str, entity_id: str, **details: Any) -> AuditEntry:
        entry = AuditEntry.record("delete", entity_type, entity_id, details)
        self.append(entry)
        return entry

    def recent(self, limit: int = 50) -> List[AuditEntry]:
        entries = self._load()
        return list(reversed(entries[-limit:]))

    def for_entity(self, entity_type: str, entity_id: str) -> List[AuditEntry]:
        return [
            e
            for e in self.recent(10000)
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]

    def export_text(self, n: int = 30) -> str:
        lines = ["Recent audit events", "-" * 24]
        for e in self.recent(n):
            lines.append(
                "{ts} {action} {entity_type}/{entity_id}".format(
                    ts=e.timestamp,
                    action=e.action,
                    entity_type=e.entity_type,
                    entity_id=e.entity_id,
                )
            )
        return "\n".join(lines)
