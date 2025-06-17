"""Tests for liftlog.io_fitnotes (FitNotes sqlite import)."""

import json
import sqlite3

import pytest

from liftlog.errors import ImportError as PTImportError
from liftlog import io_fitnotes


def _make_db(tmp_path, with_exercises=True):
    lib = tmp_path / "fitnotes"
    lib.mkdir()
    conn = sqlite3.connect(str(lib / "fitnotes.db"))
    conn.execute("CREATE TABLE training_log (date TEXT, exercise TEXT, category TEXT, weight REAL, reps INTEGER)")
    if with_exercises:
        conn.execute("CREATE TABLE exercises (name TEXT, category TEXT)")
        conn.execute("INSERT INTO exercises VALUES ('Back Squat', 'Legs')")
    conn.execute("INSERT INTO training_log VALUES ('2025-01-10','Back Squat','Legs',140,5)")
    conn.execute("INSERT INTO training_log VALUES ('2025-01-12','Back Squat','Legs',145,5)")
    conn.execute("INSERT INTO training_log VALUES ('2025-01-12','Bench Press','Chest',100,5)")
    conn.commit()
    conn.close()
    return lib


def test_missing_db(tmp_path):
    with pytest.raises(PTImportError):
        io_fitnotes._read_db(tmp_path / "empty")


def test_import_count(library_store, tmp_path):
    assert io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path)) == 3


def test_creates_exercises(library_store, tmp_path):
    io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path))
    names = {e.name for e in library_store.exercises.values()}
    assert names == {"Back Squat", "Bench Press"}


def test_worksets_logged(library_store, tmp_path):
    io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path))
    assert len(list(library_store._inner.list_worksets())) == 3


def test_best_1rm_updated(library_store, tmp_path):
    io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path))
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    assert squat.best_1rm > 140


def test_source(library_store, tmp_path):
    io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path))
    assert all(e.source == "fitnotes" for e in library_store.exercises.values())


def test_reuses_exercise(library_store, tmp_path):
    io_fitnotes.import_fitnotes(library_store, _make_db(tmp_path))
    # Back Squat appears twice but should be one exercise
    squats = [e for e in library_store.exercises.values() if e.name == "Back Squat"]
    assert len(squats) == 1


def test_list_exercises(tmp_path):
    lib = _make_db(tmp_path)
    assert "Back Squat" in io_fitnotes.list_fitnotes_exercises(lib)


def test_export_json(library_store, sample_exercise):
    library_store.upsert_exercise(sample_exercise)
    from liftlog.workset import WorkSet
    library_store.add_workset(WorkSet.create(sample_exercise.id, weight=100, reps=5))
    data = json.loads(io_fitnotes.export_fitnotes_json(library_store))
    assert data and data[0]["weight"] == 100


def test_stats(tmp_path):
    s = io_fitnotes.fitnotes_stats(_make_db(tmp_path))
    assert s["sets"] == 3 and s["exercises"] == 2
