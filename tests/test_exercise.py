"""Tests for liftlog.exercise."""

from datetime import date

import pytest

from liftlog.exercise import Exercise, ExerciseCatalog, LiftStatus
from liftlog.errors import ValidationError
from liftlog.rating import Rating


def test_create_minimal():
    e = Exercise.create("Back Squat")
    assert e.name == "Back Squat"
    assert e.status == LiftStatus.ACTIVE
    assert e.category == "compound"
    assert e.unit == "kg"


def test_create_with_valid_wger():
    assert Exercise.create("Squat", wger="615").wger == "615"


def test_create_with_invalid_wger_raises():
    with pytest.raises(ValidationError):
        Exercise.create("X", wger="not-an-id")


def test_empty_name_rejected():
    with pytest.raises(ValidationError):
        Exercise.create("  ")


def test_progress_pct():
    e = Exercise.create("Squat", best_1rm=160, target_1rm=200)
    assert e.progress_pct() == 80.0


def test_progress_pct_no_target():
    assert Exercise.create("Squat", best_1rm=160).progress_pct() == 0.0


def test_progress_capped_at_100():
    e = Exercise.create("Squat", best_1rm=220, target_1rm=200)
    assert e.progress_pct() == 100.0


def test_set_targets():
    e = Exercise.create("Squat")
    e.set_targets(150, 200)
    assert e.best_1rm == 150 and e.target_1rm == 200


def test_update_best_pr():
    e = Exercise.create("Squat", best_1rm=160)
    assert e.update_best(170) is True
    assert e.best_1rm == 170
    assert e.update_best(165) is False


def test_gap_to_target():
    e = Exercise.create("Squat", best_1rm=160, target_1rm=200)
    assert e.gap_to_target() == 40.0


def test_gap_to_target_none():
    assert Exercise.create("Squat", best_1rm=160).gap_to_target() is None


def test_at_goal():
    assert Exercise.create("Squat", best_1rm=200, target_1rm=180).at_goal() is True
    assert Exercise.create("Squat", best_1rm=160, target_1rm=180).at_goal() is False
    assert Exercise.create("Squat", best_1rm=160).at_goal() is False


def test_mark_active():
    e = Exercise.create("Squat", status=LiftStatus.LEARNING)
    e.mark_active(date(2025, 1, 1))
    assert e.status == LiftStatus.ACTIVE and e.started_at == "2025-01-01"


def test_mark_retired():
    e = Exercise.create("Squat")
    e.mark_retired(date(2025, 1, 1))
    assert e.status == LiftStatus.RETIRED and e.finished_at == "2025-01-01"


def test_mark_done_alias():
    e = Exercise.create("Squat")
    e.mark_done()
    assert e.status == LiftStatus.RETIRED


def test_bench():
    e = Exercise.create("Squat")
    e.bench()
    assert e.status == LiftStatus.BENCHED


def test_set_status_from_string():
    e = Exercise.create("Squat")
    e.set_status("maintenance")
    assert e.status == LiftStatus.MAINTENANCE


def test_short_label():
    assert Exercise.create("Overhead Press").short_label() == "Overhead Press"


def test_summary_line():
    line = Exercise.create("Squat", best_1rm=160).summary_line()
    assert "Squat" in line and "best" in line


def test_rating_float():
    e = Exercise.create("Squat")
    e.rating = 4.5
    assert e.rating_value == 4.5
    assert isinstance(e.rating, Rating)


def test_rating_object():
    e = Exercise.create("Squat")
    e.rating = Rating.create(e.id, value=3.0)
    assert e.rating_value == 3.0


def test_to_from_dict_roundtrip():
    e = Exercise.create("Squat", wger="615", category="compound", best_1rm=160, target_1rm=200)
    e.rating = 4.0
    e2 = Exercise.from_dict(e.to_dict())
    assert e2.name == "Squat" and e2.wger == "615"
    assert e2.best_1rm == 160 and e2.target_1rm == 200 and e2.rating_value == 4.0


def test_matches():
    e = Exercise.create("Back Squat", category="compound", wger="615")
    assert e.matches("squat")
    assert e.matches("compound")
    assert e.matches("615")
    assert not e.matches("curl")


def test_matches_query_description():
    e = Exercise.create("Squat", description="hip drive cue")
    assert e.matches_query("hip drive")


def test_is_active():
    assert Exercise.create("Squat", status=LiftStatus.ACTIVE).is_active()
    assert Exercise.create("Squat", status=LiftStatus.MAINTENANCE).is_active()
    assert not Exercise.create("Squat", status=LiftStatus.RETIRED).is_active()


def test_days_active():
    e = Exercise.create("Squat")
    e.started_at = "2025-01-01"
    e.finished_at = "2025-01-08"
    assert e.days_active() == 7


def _cat():
    es = [
        Exercise.create("Back Squat", category="compound", status=LiftStatus.ACTIVE,
                        best_1rm=160, target_1rm=200),
        Exercise.create("Leg Press", category="compound", status=LiftStatus.RETIRED, best_1rm=300),
        Exercise.create("Curl", category="isolation", status=LiftStatus.MAINTENANCE, best_1rm=40),
    ]
    es[1].finished_at = "2025-05-01"
    es[0].musclegroup_ids = ["mg1"]
    es[0].wger = "615"
    return ExerciseCatalog(es)


def test_catalog_by_status():
    assert len(_cat().by_status("active")) == 1


def test_catalog_by_musclegroup():
    assert len(_cat().by_musclegroup("mg1")) == 1


def test_catalog_active_unretired():
    cat = _cat()
    assert len(cat.active()) == 1
    assert len(cat.unretired()) == 2


def test_catalog_by_category():
    assert len(_cat().by_category("compound")) == 2


def test_catalog_at_goal():
    es = [Exercise.create("A", best_1rm=200, target_1rm=180)]
    assert len(ExerciseCatalog(es).at_goal()) == 1


def test_catalog_recently_retired():
    assert _cat().recently_retired()[0].name == "Leg Press"


def test_catalog_with_wger():
    assert len(_cat().with_wger()) == 1


def test_catalog_sort_and_summary():
    cat = _cat()
    assert [e.name for e in cat.sort_by_name()][0] == "Back Squat"
    assert isinstance(cat.sort_by_progress(), list)
    assert "Exercises (3)" in cat.summary()
    assert isinstance(cat.group_by_status(), dict)
