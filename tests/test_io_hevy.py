"""Tests for liftlog.io_hevy (Hevy app CSV export)."""

import pytest

from liftlog.errors import ImportError as PTImportError
from liftlog import io_hevy

HEVY = """\
title,start_time,exercise_title,set_index,weight_kg,reps,rpe
Push Day,2025-02-01 17:30:00,Overhead Press,0,60,5,8
Push Day,2025-02-01 17:30:00,Overhead Press,1,62.5,3,9
Pull Day,2025-02-03 17:30:00,Barbell Row,0,90,8,7
"""


def _w(tmp_path, text, name="hevy.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_count(library_store, tmp_path):
    assert io_hevy.import_hevy(library_store, _w(tmp_path, HEVY)) == 3


def test_import_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_hevy.import_hevy(library_store, tmp_path / "nope.csv")


def test_creates_exercises(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    names = {e.name for e in library_store.exercises.values()}
    assert names == {"Overhead Press", "Barbell Row"}


def test_worksets_logged(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    assert len(list(library_store._inner.list_worksets())) == 3


def test_source(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    assert all(e.source == "hevy" for e in library_store.exercises.values())


def test_best_updated(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    ohp = next(e for e in library_store.exercises.values() if e.name == "Overhead Press")
    assert ohp.best_1rm > 60


def test_blank_skipped(library_store, tmp_path):
    csv = "exercise_title,weight_kg,reps\n,60,5\n"
    assert io_hevy.import_hevy(library_store, _w(tmp_path, csv)) == 0


def test_preview(tmp_path):
    lines = io_hevy.preview(_w(tmp_path, HEVY), limit=1)
    assert lines and "Overhead Press" in lines[0]


def test_preview_missing(tmp_path):
    assert io_hevy.preview(tmp_path / "no.csv") == []


def test_imported_helper(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    assert len(io_hevy.imported(library_store)) == 2


def test_history_summary(library_store, tmp_path):
    io_hevy.import_hevy(library_store, _w(tmp_path, HEVY))
    assert "Hevy exercises" in io_hevy.history_summary(library_store)


def test_history_summary_empty(library_store):
    assert "No Hevy" in io_hevy.history_summary(library_store)


def test_conftest_fixture(library_store, hevy_csv):
    assert io_hevy.import_hevy(library_store, hevy_csv) == 3
