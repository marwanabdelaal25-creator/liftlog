"""Tests for liftlog.tag."""

import pytest
from liftlog.errors import ValidationError
from liftlog.tag import Tag


def test_create_tag(sample_tag):
    assert sample_tag.slug == "posterior-chain"
    assert sample_tag.name == "posterior-chain"


def test_slug_from_name():
    t = Tag.create("Sci Fi")
    assert t.slug == "sci-fi" or "sci" in t.slug


def test_invalid_slug():
    with pytest.raises(ValidationError):
        Tag.create("!!!")


def test_to_dict_roundtrip(sample_tag):
    d = sample_tag.to_dict()
    t2 = Tag.from_dict(d)
    assert t2.slug == sample_tag.slug


def test_bump_increments():
    t = Tag.create("x")
    t.bump(3)
    assert t.usage_count == 3


def test_bump_never_negative():
    t = Tag.create("x")
    t.bump(-10)
    assert t.usage_count == 0


def test_default_color():
    t = Tag.create("plain")
    assert t.color.startswith("#")


def test_custom_color():
    t = Tag.create("c", color="#ff0000")
    assert t.color == "#ff0000"


def test_from_dict_usage_count():
    d = {"id": "1", "name": "n", "slug": "n", "usage_count": 5}
    assert Tag.from_dict(d).usage_count == 5


def test_explicit_slug():
    t = Tag.create("Display Name", slug="custom-slug")
    assert t.slug == "custom-slug"


def test_id_generated():
    t = Tag.create("auto")
    assert t.id


def test_name_stripped():
    t = Tag.create("  spaced  ")
    assert t.name == "spaced"


def test_bump_default_delta():
    t = Tag.create("x")
    t.bump()
    assert t.usage_count == 1


def test_multiple_bumps():
    t = Tag.create("x")
    for _ in range(5):
        t.bump()
    assert t.usage_count == 5


def test_from_dict_default_color():
    d = {"id": "1", "name": "n", "slug": "n"}
    assert Tag.from_dict(d).color == "#718096"


def test_custom_id():
    t = Tag.create("x", id="my-tag-id")
    assert t.id == "my-tag-id"


def test_to_dict_keys():
    d = Tag.create("k").to_dict()
    assert {"id", "name", "slug", "color", "usage_count"} <= set(d.keys())

from liftlog.errors import NotFoundError
from liftlog.tag import Tag, find_tag_by_slug, merge_tags, recalc_usage, tag_cloud


def test_recalc_usage_and_cloud(storage_with_exercise, sample_exercise, sample_tag):
    sample_exercise.tag_ids = [sample_tag.id]
    storage_with_exercise.upsert_tag(sample_tag)
    storage_with_exercise.upsert_exercise(sample_exercise)
    recalc_usage(storage_with_exercise)
    cloud = tag_cloud(storage_with_exercise)
    assert cloud[0][1] >= 1


def test_find_tag_by_slug(storage_with_exercise, sample_tag):
    storage_with_exercise.upsert_tag(sample_tag)
    assert find_tag_by_slug(storage_with_exercise, sample_tag.slug) is not None


def test_merge_tags(storage_with_exercise, sample_exercise):
    t1 = Tag.create("merge-a", id="ta")
    t2 = Tag.create("merge-b", id="tb")
    storage_with_exercise.upsert_tag(t1)
    storage_with_exercise.upsert_tag(t2)
    sample_exercise.tag_ids = [t2.id]
    storage_with_exercise.upsert_exercise(sample_exercise)
    kept = merge_tags(storage_with_exercise, t1.id, t2.id)
    assert kept.id == t1.id


def test_merge_tags_missing(empty_storage):
    with pytest.raises(NotFoundError):
        merge_tags(empty_storage, "a", "b")
