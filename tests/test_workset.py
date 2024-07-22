"""Tests for liftlog.workset."""

from datetime import date

import pytest

from liftlog.errors import ValidationError
from liftlog.workset import WorkSet, Session


def test_create():
    w = WorkSet.create("ex1", weight=140.0, reps=5, rpe=8.0)
    assert w.exercise_id == "ex1"
    assert w.volume() == 700.0


def test_e1rm():
    # epley(140, 5) = 163.3
    assert WorkSet.create("ex", weight=140.0, reps=5).e1rm() == pytest.approx(163.3, abs=0.1)


def test_e1rm_zero_when_empty():
    assert WorkSet.create("ex", weight=0, reps=0).e1rm() == 0.0


def test_volume_zero():
    assert WorkSet.create("ex", weight=100, reps=0).volume() == 0.0


def test_is_working():
    assert WorkSet.create("ex", weight=100, reps=5).is_working() is True
    assert WorkSet.create("ex", weight=100, reps=5, is_warmup=True).is_working() is False
    assert WorkSet.create("ex", weight=0, reps=0).is_working() is False


def test_negative_weight_rejected():
    with pytest.raises(ValidationError):
        WorkSet(exercise_id="e", weight=-5)


def test_negative_reps_rejected():
    with pytest.raises(ValidationError):
        WorkSet(exercise_id="e", reps=-1)


def test_bad_rpe_rejected():
    with pytest.raises(ValidationError):
        WorkSet(exercise_id="e", rpe=12)


def test_workout_date():
    w = WorkSet.create("ex", started_at="2025-03-15T20:00:00")
    assert w.workout_date == date(2025, 3, 15)


def test_to_from_dict_roundtrip():
    w = WorkSet.create("ex", weight=100, reps=8, rpe=7.5, is_warmup=False, notes="ok")
    w2 = WorkSet.from_dict(w.to_dict())
    assert w2.weight == 100 and w2.reps == 8 and w2.rpe == 7.5 and w2.notes == "ok"


def test_session_alias():
    assert Session is WorkSet
