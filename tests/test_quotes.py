"""Tests for liftlog.quotes."""

from datetime import date

import pytest
from liftlog.errors import ValidationError
from liftlog.quotes import Quote


def test_quote_create():
    q = Quote(text="It was a bright cold day.", exercise_id="b1")
    assert q.exercise_id == "b1"


def test_empty_text_fails():
    with pytest.raises(ValidationError):
        Quote(text="  ", exercise_id="b1")


def test_preview_short():
    q = Quote(text="Short.", exercise_id="b1")
    assert q.preview() == "Short."


def test_preview_long():
    long_text = "word " * 50
    q = Quote(text=long_text.strip(), exercise_id="b1")
    assert len(q.preview(40)) <= 40


def test_preview_newlines_collapsed():
    q = Quote(text="line1\nline2", exercise_id="b1")
    assert "\n" not in q.preview()


def test_to_dict_roundtrip():
    q = Quote(text="Hello", exercise_id="b1", scene=42, speaker="Narrator")
    d = q.to_dict()
    q2 = Quote.from_dict(d)
    assert q2.scene == 42


def test_added_at_default():
    q = Quote(text="T", exercise_id="b")
    assert q.added_at == date.today()


def test_tags_list():
    q = Quote(text="T", exercise_id="b", tags=["memorable", "opening"])
    assert len(q.tags) == 2


def test_id_generated():
    q = Quote(text="T", exercise_id="b")
    assert q.id


def test_speaker_default_empty():
    assert Quote(text="T", exercise_id="b").speaker == ""


def test_scene_optional():
    q = Quote(text="T", exercise_id="b", scene=None)
    assert q.scene is None


def test_from_dict_parses_date():
    d = {"text": "T", "exercise_id": "b", "added_at": "2024-06-01"}
    assert Quote.from_dict(d).added_at == date(2024, 6, 1)


def test_preview_ellipsis():
    q = Quote(text="A" * 100, exercise_id="b")
    assert q.preview(20).endswith("…")


def test_tags_default_empty():
    assert Quote(text="T", exercise_id="b").tags == []


def test_to_dict_added_at_iso():
    d = Quote(text="T", exercise_id="b").to_dict()
    assert "added_at" in d


def test_custom_id():
    q = Quote(text="T", exercise_id="b", id="quote-1")
    assert q.id == "quote-1"


def test_preview_exact_length():
    text = "x" * 80
    assert len(Quote(text=text, exercise_id="b").preview(80)) <= 80


def test_exercise_id_required():
    q = Quote(text="words", exercise_id="exercise-xyz")
    assert q.exercise_id == "exercise-xyz"

from liftlog.errors import NotFoundError
from liftlog.quotes import Quote, QuotesManager


def test_quotes_manager_lifecycle(storage_with_exercise, sample_exercise):
    qm = QuotesManager(storage_with_exercise)
    q = qm.add(Quote(text="To be", exercise_id=sample_exercise.id))
    assert qm.get(q.id).text.startswith("To be")
    qm.delete(q.id)
    with pytest.raises(NotFoundError):
        qm.get(q.id)


def test_quotes_manager_stats(storage_with_exercise, sample_exercise):
    qm = QuotesManager(storage_with_exercise)
    qm.add(Quote(text="words here", exercise_id=sample_exercise.id))
    assert qm.stats()["total"] == 1


def test_quotes_manager_daily(storage_with_exercise, sample_exercise):
    qm = QuotesManager(storage_with_exercise)
    qm.add(Quote(text="A", exercise_id=sample_exercise.id))
    assert qm.daily_quote() is not None


def test_quote_word_count():
    assert Quote(text="one two three", exercise_id="b").word_count() == 3
