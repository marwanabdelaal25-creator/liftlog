"""Tests for liftlog.io_wger (wger API wrapper)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from liftlog.errors import ImportError as PTImportError
from liftlog import io_wger

WID = "615"

SQUAT = {
    "id": 615,
    "name": "Squat",
    "category": {"name": "Legs"},
    "equipment": [{"name": "Barbell"}],
    "muscles": [{"name": "Quadriceps"}, {"name": "Glutes"}],
    "description": "A compound leg movement.",
}


def _resp(payload):
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    return m


def test_base_url():
    assert io_wger.BASE.startswith("https://")


@patch("urllib.request.urlopen")
def test_fetch_exercise(mock_urlopen):
    mock_urlopen.return_value = _resp(SQUAT)
    assert io_wger.fetch_exercise(WID)["name"] == "Squat"


def test_fetch_bad_id():
    with pytest.raises(PTImportError):
        io_wger.fetch_exercise("not-an-id")


@patch("urllib.request.urlopen")
def test_fetch_network_error(mock_urlopen):
    mock_urlopen.side_effect = OSError("offline")
    with pytest.raises(PTImportError):
        io_wger.fetch_exercise(WID)


@patch("urllib.request.urlopen")
def test_fetch_bad_json(mock_urlopen):
    m = MagicMock()
    m.read.return_value = b"not json"
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = m
    with pytest.raises(PTImportError):
        io_wger.fetch_exercise(WID)


@patch("urllib.request.urlopen")
def test_exercise_from_wger(mock_urlopen):
    mock_urlopen.return_value = _resp(SQUAT)
    ex = io_wger.exercise_from_wger(WID)
    assert ex.name == "Squat"
    assert ex.wger == "615"
    assert ex.category == "compound"  # "Legs" is a compound category
    assert ex.source == "wger"


@patch("urllib.request.urlopen")
def test_exercise_from_wger_metadata(mock_urlopen):
    mock_urlopen.return_value = _resp(SQUAT)
    ex = io_wger.exercise_from_wger(WID)
    assert ex.metadata.get("equipment") == ["Barbell"]
    assert "Quadriceps" in ex.metadata.get("muscles", [])


@patch("urllib.request.urlopen")
def test_exercise_from_wger_isolation(mock_urlopen):
    mock_urlopen.return_value = _resp({"name": "Curl", "category": {"name": "Arms"}})
    assert io_wger.exercise_from_wger(WID).category == "isolation"


@patch("urllib.request.urlopen")
def test_exercise_from_wger_unknown_name(mock_urlopen):
    mock_urlopen.return_value = _resp({"category": {"name": "Legs"}})
    assert io_wger.exercise_from_wger(WID).name == "Unknown Exercise"


@patch("urllib.request.urlopen")
def test_search(mock_urlopen):
    mock_urlopen.return_value = _resp({"suggestions": [{"value": "Squat"}, {"value": "Front Squat"}]})
    assert len(io_wger.search("squat", limit=1)) == 1


@patch("urllib.request.urlopen")
def test_search_network_fail(mock_urlopen):
    mock_urlopen.side_effect = OSError("nope")
    assert io_wger.search("x") == []


@patch("urllib.request.urlopen")
def test_enrich_exercise(mock_urlopen, storage_with_exercise, sample_exercise):
    sample_exercise.wger = WID
    storage_with_exercise.upsert_exercise(sample_exercise)
    mock_urlopen.return_value = _resp(SQUAT)
    enriched = io_wger.enrich_exercise(storage_with_exercise, sample_exercise.id)
    assert enriched.metadata.get("equipment") == ["Barbell"]


def test_enrich_no_wger(empty_storage, sample_exercise):
    sample_exercise.wger = None
    empty_storage.upsert_exercise(sample_exercise)
    with pytest.raises(PTImportError):
        io_wger.enrich_exercise(empty_storage, sample_exercise.id)


@patch("urllib.request.urlopen")
def test_bulk_enrich(mock_urlopen, storage_with_exercise, sample_exercise):
    sample_exercise.wger = WID
    storage_with_exercise.upsert_exercise(sample_exercise)
    mock_urlopen.return_value = _resp(SQUAT)
    assert io_wger.bulk_enrich(storage_with_exercise, limit=5) >= 1


def test_format_search_hit():
    line = io_wger.format_search_hit({"value": "Squat", "data": {"category": "Legs"}})
    assert "Squat" in line and "Legs" in line


def test_format_search_hit_plain():
    assert io_wger.format_search_hit({"name": "Deadlift"}) == "Deadlift"
