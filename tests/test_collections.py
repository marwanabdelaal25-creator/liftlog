"""Tests for liftlog.collections."""

from datetime import datetime

import pytest
from liftlog.errors import ValidationError
from liftlog.collections import Collection


def test_collection_create():
    c = Collection(name="2025 reads")
    assert c.name == "2025 reads"


def test_empty_name_fails():
    with pytest.raises(ValidationError):
        Collection(name="")


def test_includes():
    c = Collection(name="x")
    c.add("b1")
    assert c.includes("b1") is True


def test_add_no_dup():
    c = Collection(name="x")
    c.add("b1")
    c.add("b1")
    assert c.exercise_ids.count("b1") == 1


def test_remove():
    c = Collection(name="x")
    c.add("b1")
    c.remove("b1")
    assert c.includes("b1") is False


def test_remove_missing():
    c = Collection(name="x")
    c.remove("nope")  # no raise


def test_to_dict_roundtrip():
    c = Collection(name="c", description="desc", smart_query="status:read")
    d = c.to_dict()
    c2 = Collection.from_dict(d)
    assert c2.smart_query == "status:read"


def test_created_at_serialized():
    d = Collection(name="d").to_dict()
    assert "created_at" in d


def test_from_dict_parses_created_at():
    c = Collection(name="x")
    c2 = Collection.from_dict(c.to_dict())
    assert isinstance(c2.created_at, datetime)


def test_smart_query_optional():
    c = Collection(name="manual")
    assert c.smart_query is None


def test_description_default():
    assert Collection(name="m").description == ""


def test_id_generated():
    assert Collection(name="i").id


def test_exercise_ids_independent():
    c1 = Collection(name="a")
    c2 = Collection.from_dict(c1.to_dict())
    c2.add("x")
    assert c1.includes("x") is False


def test_multiple_adds():
    c = Collection(name="bulk")
    for bid in ["a", "b", "c"]:
        c.add(bid)
    assert len(c.exercise_ids) == 3


def test_name_stripped():
    c = Collection(name="  spaced  ")
    assert c.name == "spaced"


def test_to_dict_exercise_ids():
    c = Collection(name="x")
    c.add("b1")
    assert "b1" in c.to_dict()["exercise_ids"]


def test_from_dict_minimal():
    c = Collection.from_dict({"name": "only"})
    assert c.description == ""


def test_remove_only_one_copy():
    c = Collection(name="x", exercise_ids=["b1"])
    c.remove("b1")
    assert c.exercise_ids == []
