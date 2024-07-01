"""Tests for liftlog.rating."""

import pytest
from liftlog.errors import ValidationError
from liftlog.rating import Rating, average_rating, histogram


def test_create_rating(sample_rating):
    assert sample_rating.value == 4.0
    assert sample_rating.score == 4.0


def test_score_alias():
    r = Rating.create("b1", score=3.5)
    assert r.score == 3.5


def test_rating_out_of_range():
    with pytest.raises(ValidationError):
        Rating.create("b1", value=6.0)


def test_negative_rating():
    with pytest.raises(ValidationError):
        Rating.create("b1", value=-0.1)


def test_created_at_auto():
    r = Rating.create("b1", value=2.0)
    assert r.created_at


def test_to_dict_roundtrip(sample_rating):
    d = sample_rating.to_dict()
    r2 = Rating.from_dict(d)
    assert r2.value == sample_rating.value


def test_stars_display_full():
    r = Rating.create("b1", value=5.0)
    assert "★" in r.stars_display()


def test_stars_display_empty():
    r = Rating.create("b1", value=0.0)
    assert "☆" in r.stars_display()


def test_stars_display_half():
    r = Rating.create("b1", value=3.5)
    disp = r.stars_display()
    assert "★" in disp


def test_average_rating_empty():
    assert average_rating([]) is None


def test_average_rating_values():
    rs = [Rating.create("b", value=4.0), Rating.create("b", value=2.0)]
    assert average_rating(rs) == 3.0


def test_histogram_buckets():
    rs = [
        Rating.create("b", value=1.0),
        Rating.create("b", value=5.0),
        Rating.create("b", value=5.0),
    ]
    h = histogram(rs)
    assert h[1] == 1
    assert h[5] == 2


def test_histogram_all_keys():
    h = histogram([])
    assert set(h.keys()) == {0, 1, 2, 3, 4, 5}


def test_review_preserved():
    r = Rating.create("b1", value=4.0, review="loved it")
    assert r.review == "loved it"


def test_source_default():
    r = Rating.create("b1", value=3.0)
    assert r.source == "manual"


def test_source_custom():
    r = Rating.create("b1", value=3.0, source="strong")
    assert r.source == "strong"


def test_from_dict():
    d = {"id": "1", "exercise_id": "b", "value": 4.5}
    r = Rating.from_dict(d)
    assert r.value == 4.5


def test_rounding_on_validate():
    r = Rating.create("b1", value=3.333)
    assert r.value == 3.33


def test_id_generated():
    r = Rating.create("b1", value=1.0)
    assert len(r.id) > 0

from liftlog.rating import RatingsManager


def test_rating_summary():
    r = Rating.create("b", value=4.0)
    assert "/5" in r.summary()


def test_ratings_manager_rate(storage_with_exercise, sample_exercise):
    rm = RatingsManager(storage_with_exercise)
    r = rm.rate(sample_exercise.id, 4.5, review="great")
    assert r.value == 4.5


def test_ratings_manager_latest(storage_with_exercise, sample_exercise):
    rm = RatingsManager(storage_with_exercise)
    rm.rate(sample_exercise.id, 3.0)
    rm.rate(sample_exercise.id, 5.0)
    latest = rm.latest_for_exercise(sample_exercise.id)
    assert latest is not None


def test_ratings_manager_distribution(storage_with_exercise, sample_exercise):
    rm = RatingsManager(storage_with_exercise)
    rm.rate(sample_exercise.id, 5.0)
    dist = rm.distribution()
    assert dist[5] >= 1


def test_ratings_manager_top_rated(storage_with_exercise, sample_exercise):
    rm = RatingsManager(storage_with_exercise)
    rm.rate(sample_exercise.id, 5.0)
    top = rm.top_rated(3)
    assert len(top) >= 1


def test_ratings_manager_report(storage_with_exercise, sample_exercise):
    rm = RatingsManager(storage_with_exercise)
    rm.rate(sample_exercise.id, 4.0)
    assert "Ratings" in rm.report()
