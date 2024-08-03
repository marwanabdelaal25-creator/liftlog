"""Tests for liftlog.musclegroup."""

import pytest
from liftlog.musclegroup import MuscleGroup
from liftlog.errors import ValidationError


def test_create_musclegroup(sample_musclegroup):
    assert sample_musclegroup.name == "Hamstrings"
    assert sample_musclegroup.id


def test_create_empty_name():
    with pytest.raises(ValidationError):
        MuscleGroup.create("  ")


def test_to_dict_roundtrip(sample_musclegroup):
    d = sample_musclegroup.to_dict()
    a2 = MuscleGroup.from_dict(d)
    assert a2.name == sample_musclegroup.name


def test_display_name():
    a = MuscleGroup.create("Jane Doe")
    assert a.display_name() == "Jane Doe"


def test_add_exercise():
    a = MuscleGroup.create("A")
    a.add_exercise("b1")
    assert "b1" in a.exercise_ids


def test_add_exercise_no_dup():
    a = MuscleGroup.create("A")
    a.add_exercise("b1")
    a.add_exercise("b1")
    assert a.exercise_ids.count("b1") == 1


def test_remove_exercise():
    a = MuscleGroup.create("A")
    a.add_exercise("b1")
    a.remove_exercise("b1")
    assert "b1" not in a.exercise_ids


def test_remove_exercise_missing():
    a = MuscleGroup.create("A")
    a.remove_exercise("nope")  # shouldn't raise


def test_merge_aliases():
    a = MuscleGroup.create("A", aliases=["pen name"])
    a.merge_aliases(["Pen Name", "other"])
    assert len(a.aliases) >= 2


def test_merge_aliases_skips_empty():
    a = MuscleGroup.create("A")
    a.merge_aliases(["", "  "])
    assert a.aliases == []


def test_email_validated():
    a = MuscleGroup.create("A", email="x@y.z")
    assert a.email == "x@y.z"


def test_email_invalid():
    with pytest.raises(ValidationError):
        MuscleGroup.create("A", email="bad")


def test_positional_init():
    a = MuscleGroup(name="Direct")
    assert a.name == "Direct"


def test_aliases_default_empty():
    a = MuscleGroup.create("A")
    assert a.aliases == []


def test_exercise_ids_independent():
    a1 = MuscleGroup.create("A")
    a2 = MuscleGroup.from_dict(a1.to_dict())
    a2.exercise_ids.append("x")
    assert "x" not in a1.exercise_ids


def test_bio_preserved():
    a = MuscleGroup.create("A", bio="Wrote many exercises.")
    assert "many" in a.to_dict()["bio"]


def test_website_field():
    a = MuscleGroup.create("A", website="https://example.com")
    assert a.website.startswith("https")


def test_birth_death_years():
    a = MuscleGroup.create("A", birth_year=1920, death_year=2000)
    assert a.death_year - a.birth_year == 80


def test_from_dict_minimal():
    a = MuscleGroup.from_dict({"id": "1", "name": "N"})
    assert a.bio == ""

from liftlog.errors import ConflictError
from liftlog.musclegroup import MuscleGroup, MuscleGroupManager


def test_musclegroup_manager_create_find(storage_with_exercise):
    am = MuscleGroupManager(storage_with_exercise)
    au = am.create("Brand New")
    assert am.find_by_name("Brand New") is not None


def test_musclegroup_manager_duplicate(storage_with_exercise):
    am = MuscleGroupManager(storage_with_exercise)
    am.create("Dup MuscleGroup")
    with pytest.raises(ConflictError):
        am.create("Dup MuscleGroup")


def test_musclegroup_manager_attach(storage_with_exercise, sample_exercise, sample_musclegroup):
    storage_with_exercise.upsert_musclegroup(sample_musclegroup)
    storage_with_exercise.upsert_exercise(sample_exercise)
    am = MuscleGroupManager(storage_with_exercise)
    am.attach_exercise(sample_musclegroup.id, sample_exercise.id)
    assert sample_exercise.id in am.exercises_for(sample_musclegroup.id)


def test_musclegroup_matches_alias():
    au = MuscleGroup.create("Name", aliases=["Pen Name"])
    assert au.matches("pen") is True
