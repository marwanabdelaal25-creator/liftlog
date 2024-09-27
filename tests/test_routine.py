"""Tests for liftlog.routine."""

import pytest
from liftlog.errors import ValidationError
from liftlog.routine import Routine


def test_routine_create(sample_routine):
    assert sample_routine.name == "Push Day"
    assert sample_routine.id


def test_empty_name_fails():
    with pytest.raises(ValidationError):
        Routine(name="")


def test_slug_from_name():
    sh = Routine(name="maintenance")
    assert sh.slug == "maintenance"


def test_add_exercise():
    sh = Routine(name="favorites")
    assert sh.add_exercise("b1") is True
    assert sh.count() == 1


def test_add_exercise_duplicate():
    sh = Routine(name="favorites")
    sh.add_exercise("b1")
    assert sh.add_exercise("b1") is False


def test_remove_exercise():
    sh = Routine(name="favorites")
    sh.add_exercise("b1")
    assert sh.remove_exercise("b1") is True
    assert sh.count() == 0


def test_remove_missing():
    sh = Routine(name="favorites")
    assert sh.remove_exercise("nope") is False


def test_to_dict_roundtrip():
    sh = Routine(name="queue", description="next up")
    d = sh.to_dict()
    sh2 = Routine.from_dict(d)
    assert sh2.name == sh.name
    assert sh2.description == sh.description


def test_count():
    sh = Routine(name="x")
    sh.exercise_ids = ["a", "b", "c"]
    assert sh.count() == 3


def test_is_default_flag():
    sh = Routine(name="default-routine", is_default=True)
    assert sh.is_default is True


def test_is_public_flag():
    sh = Routine(name="public-list", is_public=True)
    assert sh.is_public is True


def test_sort_order():
    sh = Routine(name="ordered", sort_order=5)
    assert sh.sort_order == 5


def test_created_at_serialized():
    sh = Routine(name="dated")
    d = sh.to_dict()
    assert "created_at" in d


def test_from_dict_parses_created_at():
    sh = Routine(name="x")
    d = sh.to_dict()
    sh2 = Routine.from_dict(d)
    assert sh2.created_at is not None


def test_exercise_ids_list_copy_safe():
    sh = Routine(name="x")
    sh.add_exercise("b1")
    d = sh.to_dict()
    sh2 = Routine.from_dict(d)
    sh2.add_exercise("b2")
    assert sh.count() == 1


def test_description_default_empty():
    sh = Routine(name="minimal")
    assert sh.description == ""


def test_id_generated():
    sh = Routine(name="auto-id")
    assert len(sh.id) >= 8


def test_multiple_exercises_order():
    sh = Routine(name="x")
    for bid in ["c", "a", "b"]:
        sh.add_exercise(bid)
    assert sh.exercise_ids == ["c", "a", "b"]
