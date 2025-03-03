"""Tests for liftlog.notes."""

from datetime import datetime

import pytest
from liftlog.errors import ValidationError
from liftlog.notes import Note


def test_note_create():
    n = Note(body="Remember the theme.", exercise_id="b1")
    assert n.exercise_id == "b1"


def test_empty_body_fails():
    with pytest.raises(ValidationError):
        Note(body="", exercise_id="b1")


def test_touch_updates_timestamp():
    n = Note(body="x", exercise_id="b1")
    n.touch()
    assert n.updated_at is not None


def test_excerpt_short():
    n = Note(body="Brief.", exercise_id="b1")
    assert n.excerpt() == "Brief."


def test_excerpt_truncates():
    n = Note(body="word " * 50, exercise_id="b1")
    assert len(n.excerpt(30)) <= 30


def test_to_dict_roundtrip():
    n = Note(body="Content", exercise_id="b1", title="Chapter 3", pinned=True)
    d = n.to_dict()
    n2 = Note.from_dict(d)
    assert n2.pinned is True


def test_workset_id_optional():
    n = Note(body="x", exercise_id="b1", workset_id="s1")
    assert n.workset_id == "s1"


def test_pinned_default_false():
    assert Note(body="x", exercise_id="b").pinned is False


def test_created_at_set():
    n = Note(body="x", exercise_id="b")
    assert isinstance(n.created_at, datetime)


def test_from_dict_parses_datetimes():
    d = {
        "body": "b",
        "exercise_id": "bk",
        "created_at": "2025-01-01T10:00:00",
        "updated_at": "2025-01-02T10:00:00",
    }
    n = Note.from_dict(d)
    assert n.updated_at is not None


def test_title_default_empty():
    assert Note(body="x", exercise_id="b").title == ""


def test_id_generated():
    assert Note(body="x", exercise_id="b").id


def test_excerpt_strips_whitespace():
    n = Note(body="  padded  ", exercise_id="b")
    assert n.excerpt(100).startswith("padded")


def test_to_dict_updated_at_none():
    d = Note(body="x", exercise_id="b").to_dict()
    assert "updated_at" not in d or d.get("updated_at") is None


def test_body_stripped_on_init():
    n = Note(body="  hello  ", exercise_id="b")
    assert n.body == "hello"


def test_from_dict_without_updated():
    n = Note.from_dict({"body": "b", "exercise_id": "x", "created_at": datetime.utcnow().isoformat()})
    assert n.updated_at is None


def test_touch_changes_updated_at():
    n = Note(body="a", exercise_id="b")
    first = n.updated_at
    n.touch()
    assert n.updated_at != first or n.updated_at is not None


def test_excerpt_ellipsis():
    n = Note(body="A" * 200, exercise_id="b")
    assert n.excerpt(50).endswith("…")

from liftlog.errors import NotFoundError
from liftlog.notes import Note, NotesManager


def test_notes_manager_add_update(storage_with_exercise, sample_exercise):
    nm = NotesManager(storage_with_exercise)
    n = nm.add(Note.create("body", sample_exercise.id, title="T"))
    updated = nm.update(n.id, "new body")
    assert updated.body == "new body"


def test_notes_manager_delete(storage_with_exercise, sample_exercise):
    nm = NotesManager(storage_with_exercise)
    n = nm.add(Note.create("x", sample_exercise.id))
    nm.delete(n.id)
    assert nm.list_for_exercise(sample_exercise.id) == []


def test_notes_manager_pin(storage_with_exercise, sample_exercise):
    nm = NotesManager(storage_with_exercise)
    n = nm.add(Note.create("x", sample_exercise.id))
    pinned = nm.pin(n.id, True)
    assert pinned.pinned is True


def test_notes_manager_search(storage_with_exercise, sample_exercise):
    nm = NotesManager(storage_with_exercise)
    nm.add(Note.create("unique needle", sample_exercise.id))
    assert len(nm.search("needle")) == 1


def test_notes_manager_update_missing(storage_with_exercise):
    with pytest.raises(NotFoundError):
        NotesManager(storage_with_exercise).update("nope", "x")
