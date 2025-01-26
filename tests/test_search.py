"""Tests for liftlog.search."""

import pytest
from liftlog.exercise import Exercise, LiftStatus
from liftlog.search import SearchEngine, SearchHit, _score, _norm


def test_norm_collapses_whitespace():
    assert _norm("  Hello   World ") == "hello world"


def test_score_exact_match():
    assert _score("barolo", "Barolo") == 1.0


def test_score_substring():
    assert _score("left", "The Left Hand of Darkness") > 0.5


def test_score_no_match():
    assert _score("xyz", "abc") == 0.0


def test_search_exercises_title(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_exercises("Squat")
    assert hits[0].title == "Back Squat"


def test_search_exercises_wger(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_exercises("615")
    assert hits and hits[0].score >= 0.9


def test_search_exercises_limit(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_exercises("e", limit=1)
    assert len(hits) <= 1


def test_search_musclegroups(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_musclegroups("Quadriceps")
    assert hits and hits[0].kind == "musclegroup"


def test_search_all_combines(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_all("Squat")
    kinds = {h.kind for h in hits}
    assert "musclegroup" in kinds or "exercise" in kinds


def test_filter_exercises_status(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    exercises = eng.filter_exercises(status="learning")
    assert all(b.status == LiftStatus.LEARNING for b in exercises)


def test_filter_exercises_tag(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    exercises = eng.filter_exercises(tag_id="tag-001")
    assert len(exercises) >= 1


def test_filter_exercises_routine(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    exercises = eng.filter_exercises(routine_id="routine-001")
    assert len(exercises) >= 1


def test_regex_filter_title(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    exercises = eng.regex_filter("^Back")
    assert len(exercises) == 1


def test_regex_filter_no_match(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    assert eng.regex_filter("^ZZZZZ") == []


def test_search_hit_fields():
    h = SearchHit("exercise", "id1", "Title", 0.9, "snippet")
    assert h.score == 0.9


def test_search_empty_query(json_storage, sample_exercise):
    json_storage.upsert_exercise(sample_exercise)
    eng = SearchEngine(json_storage)
    assert eng.search_exercises("") == []


def test_search_exercises_sorted_by_score(json_storage):
    for title in ["Alpha Exercise", "Beta Exercise", "Alphabet Soup"]:
        json_storage.upsert_exercise(Exercise.create(title))
    hits = SearchEngine(json_storage).search_exercises("Alpha")
    assert hits[0].score >= hits[-1].score


def test_filter_exercises_no_filters(populated_json_storage):
    exercises = SearchEngine(populated_json_storage).filter_exercises()
    assert len(exercises) == 3


def test_search_musclegroups_low_score_filtered(populated_json_storage):
    hits = SearchEngine(populated_json_storage).search_musclegroups("zzzzzzz")
    assert hits == []


def test_regex_filter_description(json_storage):
    b = Exercise.create("X", description="unique phrase here")
    json_storage.upsert_exercise(b)
    hits = SearchEngine(json_storage).regex_filter("unique phrase", field="description")
    assert len(hits) == 1

from liftlog.notes import Note
from liftlog.quotes import Quote
from liftlog.search import SearchEngine, SearchHit, _score


def test_score_exact_match():
    assert _score("hello", "hello") == 1.0


def test_score_empty():
    assert _score("", "text") == 0.0


def test_search_musclegroups(populated_storage, sample_musclegroup):
    populated_storage.upsert_musclegroup(sample_musclegroup)
    hits = SearchEngine(populated_storage).search_musclegroups(sample_musclegroup.name)
    assert hits and hits[0].kind == "musclegroup"


def test_search_notes(populated_storage, sample_exercise):
    populated_storage.add_note(Note.create("needle body", sample_exercise.id, title="T"))
    hits = SearchEngine(populated_storage).search_notes("needle")
    assert len(hits) >= 1


def test_search_quotes(populated_storage, sample_exercise):
    populated_storage.add_quote(Quote(text="to be or not", exercise_id=sample_exercise.id))
    hits = SearchEngine(populated_storage).search_quotes("be or")
    assert len(hits) >= 1


def test_search_all(populated_storage):
    hits = SearchEngine(populated_storage).search_all("Squat")
    assert isinstance(hits, list)


def test_filter_exercises_by_tag(empty_storage, sample_exercise, sample_tag):
    sample_exercise.tag_ids = [sample_tag.id]
    empty_storage.upsert_tag(sample_tag)
    empty_storage.upsert_exercise(sample_exercise)
    exercises = SearchEngine(empty_storage).filter_exercises(tag_id=sample_tag.id)
    assert len(exercises) == 1


def test_advanced_status(empty_storage, sample_exercise):
    empty_storage.upsert_exercise(sample_exercise)
    pool = SearchEngine(empty_storage).advanced("status:active")
    assert len(pool) >= 1


def test_advanced_title_token(empty_storage, sample_exercise):
    empty_storage.upsert_exercise(sample_exercise)
    pool = SearchEngine(empty_storage).advanced("Deadlift")
    assert pool


def test_highlight(empty_storage):
    assert "**foo**" in SearchEngine(empty_storage).highlight("foo bar", "foo")
