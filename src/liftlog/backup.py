"""Backup and restore helpers for the library file."""

# TODO: incremental backups with checksum diff

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
import shutil
from typing import List, Optional

from liftlog.errors import StorageError
from liftlog.storage import JsonStorage


def timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def backup_path(base: Path, compressed: bool = False) -> Path:
    ext = ".json.gz" if compressed else ".json"
    return base / ("library_backup_%s%s" % (timestamp(), ext))


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def create_backup(storage: JsonStorage, dest_dir: Path | None = None, compress: bool = False) -> Path:
    dest_dir = dest_dir or storage.path.parent / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = backup_path(dest_dir, compress)
    payload = json.dumps(storage.to_dict(), indent=2, ensure_ascii=False)
    meta = {"checksum": checksum(payload), "created": datetime.utcnow().isoformat()}
    if compress:
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            fh.write(payload)
    else:
        out.write_text(payload, encoding="utf-8")
    sidecar = out.with_suffix(out.suffix + ".meta")
    sidecar.write_text(json.dumps(meta), encoding="utf-8")
    return out


def restore_backup(backup_file: Path, target: Path) -> None:
    if not backup_file.exists():
        raise StorageError("backup missing: %s" % backup_file)
    if backup_file.suffix == ".gz" or backup_file.name.endswith(".json.gz"):
        with gzip.open(backup_file, "rt", encoding="utf-8") as fh:
            raw = fh.read()
    else:
        raw = backup_file.read_text(encoding="utf-8")
    sidecar = backup_file.with_suffix(backup_file.suffix + ".meta")
    if sidecar.exists():
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        if meta.get("checksum") and meta["checksum"] != checksum(raw):
            raise StorageError("backup checksum mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    bak = target.with_suffix(".pre_restore.bak")
    if target.exists():
        shutil.copy2(target, bak)
    target.write_text(raw, encoding="utf-8")


def list_backups(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    files = list(folder.glob("library_backup_*"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def prune_old(folder: Path, keep: int = 10) -> int:
    """Delete oldest backups beyond `keep` count."""
    files = list_backups(folder)
    removed = 0
    for f in files[keep:]:
        f.unlink(missing_ok=True)
        meta = f.with_suffix(f.suffix + ".meta")
        meta.unlink(missing_ok=True)
        removed += 1
    return removed


def verify_backup(path: Path) -> bool:
    try:
        if path.suffix == ".gz" or path.name.endswith(".json.gz"):
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                json.loads(fh.read())
        else:
            json.loads(path.read_text(encoding="utf-8"))
        return True
    except (OSError, json.JSONDecodeError):
        return False
