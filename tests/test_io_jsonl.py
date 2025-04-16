"""Tests for liftlog.io_jsonl."""

import json
from pathlib import Path

import pytest
from liftlog.exercise import Exercise
from liftlog.workset import Session
from liftlog.errors import ExportError, ImportError as PTImportError
from liftlog import io_jsonl


def test_export_jsonl_exercises(library_store, sample_exercise, tmp_path):
    library_store.upsert_exercise(sample_exercise)
    dest = tmp_path / "exercises.jsonl"
    n = io_jsonl.export_jsonl_exercises(library_store, dest)
    assert n == 1
    line = dest.read_text(encoding="utf-8").strip()
    assert json.loads(line)["name"] == sample_exercise.name


def test_export_jsonl_worksets(library_store, sample_exercise, sample_workset, tmp_path):
    library_store.upsert_exercise(sample_exercise)
    library_store.worksets[sample_workset.id] = sample_workset
    dest = tmp_path / "sess.jsonl"
    n = io_jsonl.export_jsonl_worksets(library_store, dest)
    assert n == 1


def test_import_jsonl_exercises(library_store, sample_exercise, tmp_path):
    dest = tmp_path / "in.jsonl"
    dest.write_text(json.dumps(sample_exercise.to_dict()) + "\n", encoding="utf-8")
    n = io_jsonl.import_jsonl_exercises(library_store, dest)
    assert n == 1
    assert sample_exercise.id in library_store.exercises


def test_import_jsonl_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_jsonl.import_jsonl_exercises(library_store, tmp_path / "nope.jsonl")


def test_import_jsonl_worksets(library_store, sample_workset, tmp_path):
    dest = tmp_path / "s.jsonl"
    dest.write_text(json.dumps(sample_workset.to_dict()) + "\n", encoding="utf-8")
    n = io_jsonl.import_jsonl_worksets(library_store, dest)
    assert n == 1
    assert sample_workset.id in library_store.worksets


def test_iter_lines_skips_blank(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text("line\n\n  \n", encoding="utf-8")
    lines = list(io_jsonl._iter_lines(p))
    assert lines == ["line"]


def test_export_empty_exercises(library_store, tmp_path):
    n = io_jsonl.export_jsonl_exercises(library_store, tmp_path / "e.jsonl")
    assert n == 0


def test_export_empty_worksets(library_store, tmp_path):
    n = io_jsonl.export_jsonl_worksets(library_store, tmp_path / "e.jsonl")
    assert n == 0


def test_import_multiple_exercises(library_store, tmp_path):
    b1 = Exercise.create("One")
    b2 = Exercise.create("Two")
    dest = tmp_path / "multi.jsonl"
    dest.write_text(
        json.dumps(b1.to_dict()) + "\n" + json.dumps(b2.to_dict()) + "\n",
        encoding="utf-8",
    )
    assert io_jsonl.import_jsonl_exercises(library_store, dest) == 2


def test_roundtrip_exercise(library_store, sample_exercise, tmp_path):
    library_store.upsert_exercise(sample_exercise)
    path = tmp_path / "rt.jsonl"
    io_jsonl.export_jsonl_exercises(library_store, path)
    library_store.exercises.clear()
    io_jsonl.import_jsonl_exercises(library_store, path)
    assert len(library_store.exercises) == 1


def test_export_creates_file(library_store, tmp_path):
    out = tmp_path / "new.jsonl"
    io_jsonl.export_jsonl_exercises(library_store, out)
    assert out.exists()


def test_import_workset_count(library_store, sample_workset, tmp_path):
    dest = tmp_path / "one.jsonl"
    dest.write_text(json.dumps(sample_workset.to_dict()) + "\n", encoding="utf-8")
    assert io_jsonl.import_jsonl_worksets(library_store, dest) == 1


def test_export_utf8(library_store, tmp_path):
    b = Exercise.create("Café résumé")
    library_store.upsert_exercise(b)
    path = tmp_path / "u.jsonl"
    io_jsonl.export_jsonl_exercises(library_store, path)
    assert "Café" in path.read_text(encoding="utf-8")


def test_import_jsonl_exercises_upserts(library_store, sample_exercise, tmp_path):
    dest = tmp_path / "up.jsonl"
    d = sample_exercise.to_dict()
    d["name"] = "Original"
    dest.write_text(json.dumps(d) + "\n", encoding="utf-8")
    io_jsonl.import_jsonl_exercises(library_store, dest)
    d["name"] = "Updated"
    dest.write_text(json.dumps(d) + "\n", encoding="utf-8")
    io_jsonl.import_jsonl_exercises(library_store, dest)
    assert library_store.exercises[sample_exercise.id].name == "Updated"


def test_export_worksets_count(library_store, sample_workset):
    library_store.worksets[sample_workset.id] = sample_workset
    assert len(library_store.worksets) == 1


def test_import_invalid_json_raises(library_store, tmp_path):
    dest = tmp_path / "bad.jsonl"
    dest.write_text("{broken\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        io_jsonl.import_jsonl_exercises(library_store, dest)


def test_export_error_readonly(tmp_path, library_store, monkeypatch):
    dest = tmp_path / "out.jsonl"

    def boom(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "open", boom)
    with pytest.raises(ExportError):
        io_jsonl.export_jsonl_exercises(library_store, dest)
