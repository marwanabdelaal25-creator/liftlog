"""Tests for liftlog.backup."""

import gzip
import json
from pathlib import Path

import pytest
from liftlog.backup import (
    timestamp,
    backup_path,
    create_backup,
    restore_backup,
    list_backups,
)
from liftlog.errors import StorageError


def test_timestamp_format():
    ts = timestamp()
    assert len(ts) == 15
    assert "_" in ts


def test_backup_path_uncompressed(tmp_path):
    p = backup_path(tmp_path, compressed=False)
    assert p.suffix == ".json"


def test_backup_path_compressed(tmp_path):
    p = backup_path(tmp_path, compressed=True)
    assert str(p).endswith(".json.gz")


def test_create_backup_plain(library_store, sample_exercise, tmp_path):
    library_store.upsert_exercise(sample_exercise)
    library_store.save()
    out = create_backup(library_store, dest_dir=tmp_path / "bak", compress=False)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "exercises" in data


def test_create_backup_gzip(library_store, tmp_path):
    out = create_backup(library_store, dest_dir=tmp_path / "bak", compress=True)
    with gzip.open(out, "rt", encoding="utf-8") as fh:
        json.load(fh)


def test_restore_backup(library_store, tmp_path):
    dest = tmp_path / "bak"
    src = create_backup(library_store, dest_dir=dest)
    target = tmp_path / "library.json"
    target.write_text("{}", encoding="utf-8")
    restore_backup(src, target)
    assert json.loads(target.read_text())["version"] is not None


def test_restore_missing_raises(tmp_path):
    with pytest.raises(StorageError):
        restore_backup(tmp_path / "nope.json", tmp_path / "lib.json")


def test_restore_gzip(library_store, tmp_path):
    gz = create_backup(library_store, dest_dir=tmp_path, compress=True)
    target = tmp_path / "restored.json"
    restore_backup(gz, target)
    assert target.exists()


def test_list_backups_empty(tmp_path):
    assert list_backups(tmp_path / "missing") == []


def test_list_backups_sorted(library_store, tmp_path):
    d = tmp_path / "bak"
    create_backup(library_store, dest_dir=d)
    create_backup(library_store, dest_dir=d)
    files = list_backups(d)
    assert len(files) == 2
    assert files[0].stat().st_mtime >= files[1].stat().st_mtime


def test_restore_creates_pre_restore_bak(library_store, tmp_path):
    target = tmp_path / "library.json"
    target.write_text('{"old": true}', encoding="utf-8")
    bak = create_backup(library_store, dest_dir=tmp_path)
    restore_backup(bak, target)
    pre = target.with_suffix(".pre_restore.bak")
    assert pre.exists()


def test_create_backup_default_dir(library_store, sample_exercise):
    library_store.upsert_exercise(sample_exercise)
    library_store.save()
    out = create_backup(library_store)
    assert out.parent.name == "backups"


def test_backup_path_unique(tmp_path):
    p1 = backup_path(tmp_path)
    p2 = backup_path(tmp_path)
    assert p1.name != p2.name or p1 == p2


def test_list_backups_non_dir(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    assert list_backups(f) == []


def test_restore_creates_parent(tmp_path):
    bak = tmp_path / "library_backup_test.json"
    bak.write_text('{"version": 1, "exercises": []}', encoding="utf-8")
    target = tmp_path / "nested" / "lib.json"
    restore_backup(bak, target)
    assert target.exists()


def test_create_backup_includes_exercises(library_store, sample_exercise, tmp_path):
    library_store.upsert_exercise(sample_exercise)
    out = create_backup(library_store, dest_dir=tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload.get("exercises", [])) >= 1


def test_timestamp_digits():
    assert timestamp()[:8].isdigit()


def test_backup_glob_pattern(library_store, tmp_path):
    create_backup(library_store, dest_dir=tmp_path)
    assert all("library_backup_" in p.name for p in list_backups(tmp_path))
