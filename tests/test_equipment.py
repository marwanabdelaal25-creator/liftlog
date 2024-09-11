"""Tests for liftlog.equipment."""

import pytest
from liftlog.errors import ValidationError
from liftlog.equipment import Equipment


def test_equipment_create():
    p = Equipment(name="Tor Exercises")
    assert p.name == "Tor Exercises"


def test_empty_name_fails():
    with pytest.raises(ValidationError):
        Equipment(name="")


def test_to_dict_roundtrip():
    p = Equipment(name="Ace", country="US", website="https://ace.com")
    d = p.to_dict()
    p2 = Equipment.from_dict(d)
    assert p2.name == p.name


def test_matches_name():
    p = Equipment(name="Penguin Random House")
    assert p.matches("penguin") is True


def test_matches_imprint():
    p = Equipment(name="Power Rack", imprint="Rogue")
    assert p.matches("rogue") is True


def test_no_match():
    p = Equipment(name="Small Press")
    assert p.matches("xyz") is False


def test_id_generated():
    p = Equipment(name="Auto")
    assert p.id


def test_country_default_empty():
    p = Equipment(name="X")
    assert p.country == ""


def test_imprint_field():
    p = Equipment(name="Parent", imprint="Child")
    assert p.imprint == "Child"


def test_from_dict_partial():
    p = Equipment.from_dict({"name": "Only Name"})
    assert p.name == "Only Name"


def test_website_stored():
    p = Equipment(name="W", website="http://w.example")
    assert "example" in p.website


def test_matches_case_insensitive():
    p = Equipment(name="Orbit")
    assert p.matches("ORBIT") is True


def test_to_dict_keys():
    keys = set(Equipment(name="K").to_dict().keys())
    assert {"name", "id", "country", "website", "imprint"} <= keys


def test_name_stripped_on_init():
    p = Equipment(name="  Trimmed  ")
    assert p.name == "Trimmed"


def test_from_dict_id_preserved():
    p = Equipment.from_dict({"id": "pub-99", "name": "N"})
    assert p.id == "pub-99"


def test_matches_empty_query():
    p = Equipment(name="X")
    assert p.matches("") is True


def test_multiple_equipment_unique_ids():
    a = Equipment(name="A")
    b = Equipment(name="B")
    assert a.id != b.id


def test_imprint_default_empty():
    assert Equipment(name="Y").imprint == ""

import pytest
from liftlog.errors import NotFoundError
from liftlog.equipment import EquipmentIndex


def test_equipment_index_assign(storage_with_exercise, sample_exercise):
    pi = EquipmentIndex(storage_with_exercise)
    pi.assign_exercise(sample_exercise.id, "Tor Exercises")
    pub = pi.find_or_create("Tor Exercises")
    assert len(pi.exercises_for(pub.id)) == 1


def test_equipment_index_search(storage_with_exercise, sample_exercise):
    pi = EquipmentIndex(storage_with_exercise)
    pi.assign_exercise(sample_exercise.id, "Ace")
    hits = pi.search("ace")
    assert len(hits) >= 1


def test_equipment_index_export_csv(storage_with_exercise, sample_exercise):
    pi = EquipmentIndex(storage_with_exercise)
    pi.assign_exercise(sample_exercise.id, "Orbit")
    lines = pi.export_csv_lines()
    assert lines[0].startswith("name,")


def test_equipment_index_summary(storage_with_exercise, sample_exercise):
    pi = EquipmentIndex(storage_with_exercise)
    pi.assign_exercise(sample_exercise.id, "Del Rey")
    assert "Del Rey" in pi.summary()


def test_equipment_index_get_missing(empty_storage):
    with pytest.raises(NotFoundError):
        EquipmentIndex(empty_storage).get("nope")


def test_equipment_index_list_sorted(storage_with_exercise, sample_exercise):
    pi = EquipmentIndex(storage_with_exercise)
    pi.find_or_create("Zebra")
    pi.find_or_create("Alpha")
    names = [p.name for p in pi.list_all()]
    assert names == sorted(names, key=str.lower)


def test_equipment_invalid_website():
    with pytest.raises(Exception):
        from liftlog.errors import ValidationError
        Equipment(name="Bad", website="not-a-url")
