"""Tests for liftlog.io_strong (Strong app CSV export)."""

import pytest

from liftlog.errors import ImportError as PTImportError
from liftlog import io_strong

STRONG = """\
Date,Workout Name,Exercise Name,Set Order,Weight,Reps,RPE,Notes
2025-01-10 18:00:00,Push Day,Bench Press,1,100,5,8,
2025-01-10 18:00:00,Push Day,Bench Press,2,105,3,9,top set
2025-01-12 18:00:00,Leg Day,Back Squat,1,140,5,8,
"""


def _w(tmp_path, text, name="strong.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_count(library_store, tmp_path):
    assert io_strong.import_strong(library_store, _w(tmp_path, STRONG)) == 3


def test_import_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_strong.import_strong(library_store, tmp_path / "nope.csv")


def test_creates_exercises(library_store, tmp_path):
    io_strong.import_strong(library_store, _w(tmp_path, STRONG))
    names = {e.name for e in library_store.exercises.values()}
    assert names == {"Bench Press", "Back Squat"}


def test_worksets_logged(library_store, tmp_path):
    io_strong.import_strong(library_store, _w(tmp_path, STRONG))
    assert len(list(library_store._inner.list_worksets())) == 3


def test_best_1rm_updated(library_store, tmp_path):
    io_strong.import_strong(library_store, _w(tmp_path, STRONG))
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    # epley(140,5) = 163.3
    assert squat.best_1rm == pytest.approx(163.3, abs=0.1)


def test_source(library_store, tmp_path):
    io_strong.import_strong(library_store, _w(tmp_path, STRONG))
    assert all(e.source == "strong" for e in library_store.exercises.values())


def test_blank_exercise_skipped(library_store, tmp_path):
    csv = "Date,Exercise Name,Weight,Reps\n2025-01-01,,100,5\n"
    assert io_strong.import_strong(library_store, _w(tmp_path, csv)) == 0


def test_preview(tmp_path):
    lines = io_strong.preview(_w(tmp_path, STRONG), limit=1)
    assert lines and "Bench Press" in lines[0]


def test_preview_missing(tmp_path):
    assert io_strong.preview(tmp_path / "no.csv") == []


def test_exercises_seen(library_store, tmp_path):
    io_strong.import_strong(library_store, _w(tmp_path, STRONG))
    assert io_strong.exercises_seen(library_store) == 2


def test_conftest_fixture(library_store, strong_csv_tmp):
    assert io_strong.import_strong(library_store, strong_csv_tmp) == 3
