"""Tests for liftlog.io_csv."""

import pytest

from liftlog.exercise import LiftStatus
from liftlog import io_csv


def test_csv_fields_count():
    assert len(io_csv.CSV_FIELDS) == 11


def test_import_count(library_store, mini_csv):
    assert io_csv.import_csv(library_store, mini_csv) == 2


def test_import_missing(library_store, tmp_path):
    from liftlog.errors import ImportError as PTImportError

    with pytest.raises(PTImportError):
        io_csv.import_csv(library_store, tmp_path / "nope.csv")


def test_import_status(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    assert squat.status == LiftStatus.ACTIVE


def test_import_best_target(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    assert squat.best_1rm == 160 and squat.target_1rm == 180


def test_import_category(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    assert squat.category == "compound"


def test_import_wger(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    squat = next(e for e in library_store.exercises.values() if e.name == "Back Squat")
    assert squat.wger == "615"


def test_import_rating(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    bench = next(e for e in library_store.exercises.values() if e.name == "Bench Press")
    assert bench.rating_value == 4.0


def test_import_creates_musclegroup(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    names = {m.name for m in library_store.musclegroups.values()}
    assert "Quadriceps" in names and "Chest" in names


def test_import_blank_name_skipped(library_store, tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("name,musclegroup\n,Chest\n", encoding="utf-8")
    assert io_csv.import_csv(library_store, p) == 0


def test_import_utf8_sig(library_store, tmp_path):
    p = tmp_path / "sig.csv"
    p.write_bytes("\ufeffname,best_1rm\nDeadlift,200\n".encode("utf-8"))
    assert io_csv.import_csv(library_store, p) == 1


def test_export_count(library_store, mini_csv, tmp_path):
    io_csv.import_csv(library_store, mini_csv)
    dest = tmp_path / "out.csv"
    assert io_csv.export_csv(library_store, dest) == 2


def test_export_includes_musclegroup(library_store, mini_csv, tmp_path):
    io_csv.import_csv(library_store, mini_csv)
    dest = tmp_path / "out.csv"
    io_csv.export_csv(library_store, dest)
    assert "Quadriceps" in dest.read_text(encoding="utf-8")


def test_export_empty(library_store, tmp_path):
    assert io_csv.export_csv(library_store, tmp_path / "e.csv") == 0


def test_validate_headers_ok(mini_csv):
    assert io_csv.validate_csv_headers(mini_csv) == []


def test_validate_headers_missing(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("musclegroup\nChest\n", encoding="utf-8")
    assert "name" in io_csv.validate_csv_headers(p)


def test_validate_headers_no_file(tmp_path):
    assert io_csv.validate_csv_headers(tmp_path / "none.csv") == io_csv.CSV_FIELDS


def test_parse_row():
    assert io_csv.parse_row("Back Squat,Quadriceps,615")["name"] == "Back Squat"


def test_sample_rows(mini_csv):
    assert len(io_csv.sample_rows(mini_csv, n=1)) == 1


def test_sample_rows_no_file(tmp_path):
    assert io_csv.sample_rows(tmp_path / "none.csv") == []


def test_import_update_mode(library_store, tmp_path):
    p = tmp_path / "u.csv"
    p.write_text("name,status,best_1rm\nSquat,active,150\n", encoding="utf-8")
    io_csv.import_csv(library_store, p)
    p.write_text("name,status,best_1rm\nSquat,maintenance,170\n", encoding="utf-8")
    io_csv.import_csv(library_store, p, update=True)
    squats = [e for e in library_store.exercises.values() if e.name == "Squat"]
    assert len(squats) == 1 and squats[0].best_1rm == 170
