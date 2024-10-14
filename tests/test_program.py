"""Tests for liftlog.program."""

import pytest
from liftlog.errors import ValidationError
from liftlog.program import Program


def test_program_create():
    s = Program(title="The Expanse")
    assert s.title == "The Expanse"


def test_empty_title_fails():
    with pytest.raises(ValidationError):
        Program(title="")


def test_add_volume():
    s = Program(title="X")
    s.add_volume("b1")
    assert "b1" in s.exercise_ids


def test_add_volume_no_dup():
    s = Program(title="X")
    s.add_volume("b1")
    s.add_volume("b1")
    assert s.exercise_ids.count("b1") == 1


def test_completion_pct_empty():
    s = Program(title="X")
    assert s.completion_pct(set()) == 0.0


def test_completion_pct_partial():
    s = Program(title="X", exercise_ids=["b1", "b2", "b3", "b4"])
    pct = s.completion_pct({"b1", "b2"})
    assert pct == 50.0


def test_completion_pct_full():
    s = Program(title="X", exercise_ids=["b1"])
    assert s.completion_pct({"b1"}) == 100.0


def test_to_dict_roundtrip():
    s = Program(title="S", musclegroup_id="a1", total_planned=7)
    s2 = Program.from_dict(s.to_dict())
    assert s2.total_planned == 7


def test_musclegroup_id_optional():
    s = Program(title="Standalone")
    assert s.musclegroup_id is None


def test_description_field():
    s = Program(title="D", description="Long arc")
    assert "arc" in s.description


def test_exercise_ids_default_empty():
    s = Program(title="New")
    assert s.exercise_ids == []


def test_total_planned_optional():
    s = Program(title="Open", total_planned=None)
    assert s.total_planned is None


def test_id_generated():
    assert len(Program(title="T").id) >= 8


def test_from_dict_preserves_exercise_ids():
    d = {"title": "T", "exercise_ids": ["a", "b"]}
    s = Program.from_dict(d)
    assert s.exercise_ids == ["a", "b"]


def test_completion_rounding():
    s = Program(title="X", exercise_ids=["1", "2", "3"])
    pct = s.completion_pct({"1"})
    assert pct == round(100.0 / 3, 1)


def test_title_required_in_from_dict():
    s = Program.from_dict({"title": "OK"})
    assert s.title == "OK"


def test_multiple_volumes_order():
    s = Program(title="X")
    for bid in ["v3", "v1", "v2"]:
        s.add_volume(bid)
    assert s.exercise_ids == ["v3", "v1", "v2"]


def test_completion_ignores_unknown_reads():
    s = Program(title="X", exercise_ids=["b1"])
    assert s.completion_pct({"b1", "other"}) == 100.0


def test_description_default_empty():
    assert Program(title="Z").description == ""

import pytest
from liftlog.exercise import LiftStatus
from liftlog.errors import NotFoundError
from liftlog.program import ProgramRegistry


def test_remove_volume():
    s = Program(title="S", exercise_ids=["a", "b"])
    s.remove_volume("a")
    assert "a" not in s.exercise_ids


def test_next_unretired():
    s = Program(title="S", exercise_ids=["a", "b"])
    assert s.next_unretired(set()) == "a"
    assert s.next_unretired({"a"}) == "b"


def test_program_registry_create_attach(storage_with_exercise, sample_exercise):
    sr = ProgramRegistry(storage_with_exercise)
    s = sr.create("The Expanse")
    sr.attach_exercise(s.id, sample_exercise.id, index=1.0)
    assert sample_exercise.id in sr.get(s.id).exercise_ids


def test_program_registry_find_by_title(storage_with_exercise):
    sr = ProgramRegistry(storage_with_exercise)
    sr.create("Mistborn")
    assert sr.find_by_title("mist")


def test_program_registry_progress_report(storage_with_exercise, sample_exercise):
    sr = ProgramRegistry(storage_with_exercise)
    s = sr.create("Report Program")
    sr.attach_exercise(s.id, sample_exercise.id)
    assert "Report" in sr.progress_report()


def test_program_registry_get_missing(empty_storage):
    with pytest.raises(NotFoundError):
        ProgramRegistry(empty_storage).get("nope")


def test_progress_report_lines_read(storage_with_exercise, sample_read_exercise):
    sr = ProgramRegistry(storage_with_exercise)
    s = sr.create("Done Program")
    sr.attach_exercise(s.id, sample_read_exercise.id)
    lines = sr.progress_report_lines()
    assert any("100" in ln or "Done" in ln for ln in lines)
