"""Tests for liftlog.validators."""

import pytest
from liftlog.errors import ValidationError
from liftlog import validators as v

WGER13 = "9780143127741"


def test_require_non_empty_ok():
    assert v.require_non_empty("  hello ", "f") == "hello"


def test_require_non_empty_fail():
    with pytest.raises(ValidationError):
        v.require_non_empty("  ", "title")


def test_validate_slug_ok():
    assert v.validate_slug("sci-fi") == "sci-fi"


def test_validate_slug_bad():
    with pytest.raises(ValidationError):
        v.validate_slug("Bad Slug!")


def test_validate_email_none():
    assert v.validate_email(None) is None


def test_validate_email_ok():
    assert v.validate_email("a@b.co") == "a@b.co"


def test_validate_email_bad():
    with pytest.raises(ValidationError):
        v.validate_email("not-email")


def test_validate_wger_field_none():
    assert v.validate_wger_field(None) is None


def test_validate_wger_field_ok():
    out = v.validate_wger_field("615")
    assert "-" not in out


def test_validate_wger_field_bad():
    with pytest.raises(ValidationError):
        v.validate_wger_field("not-an-id")


def test_validate_rating_value():
    assert v.validate_rating_value(4.256) == 4.26


def test_validate_rating_low():
    with pytest.raises(ValidationError):
        v.validate_rating_value(-1)


def test_validate_load_ok():
    v.validate_load(10, 100)  # no raise


def test_validate_best_1rm_negative():
    with pytest.raises(ValidationError):
        v.validate_load(-1, 100)


def test_validate_load_negative():
    with pytest.raises(ValidationError):
        v.validate_load(-5)


def test_validate_year_none():
    assert v.validate_year(None) is None


def test_validate_year_ok():
    assert v.validate_year(1999) == 1999


def test_validate_year_too_high():
    with pytest.raises(ValidationError):
        v.validate_year(9999)


def test_validate_id_list():
    out = v.validate_id_list(["a", "b", "a"])
    assert out == ["a", "b"]


def test_validate_dict_keys_ok():
    v.validate_dict_keys({"a": 1, "b": 2}, ["a"])


def test_validate_dict_keys_missing():
    with pytest.raises(ValidationError):
        v.validate_dict_keys({"a": 1}, ["b"])


def test_clamp_int():
    assert v.clamp_int(15, 0, 10) == 10
    assert v.clamp_int(-5, 0, 10) == 0
    assert v.clamp_int(5, 0, 10) == 5

from liftlog.validators import (
    merge_errors,
    sanitize_filename,
    soft_validate_slug,
    validate_exercise_payload,
    validate_goal_target,
    validate_hex_color,
    validate_language,
    validate_percent,
    validate_positive_int,
    validate_workset_payload,
    validate_status,
    validate_url,
)


def test_validate_url_ok():
    assert validate_url("https://example.com/x") == "https://example.com/x"


def test_validate_url_bad():
    with pytest.raises(ValidationError):
        validate_url("ftp://bad")


def test_validate_language_default():
    assert validate_language(None) == "en"


def test_validate_hex_color():
    assert validate_hex_color("#abc123") == "#abc123"


def test_validate_positive_int():
    assert validate_positive_int(3, "n") == 3


def test_validate_status():
    assert validate_status("retired", ["retired", "learning"]) == "retired"


def test_validate_percent():
    assert validate_percent(33.333) == 33.33


def test_sanitize_filename():
    assert "/" not in sanitize_filename("a/b")


def test_validate_exercise_payload():
    out = validate_exercise_payload({"name": "Squat", "category": "compound"})
    assert out["name"] == "Squat" and out["category"] == "compound"


def test_validate_workset_payload():
    validate_workset_payload({"exercise_id": "b", "set_low": 1, "set_high": 5})


def test_validate_goal_target():
    assert validate_goal_target(10, "exercises") == 10


def test_merge_errors():
    assert ";" in merge_errors([ValidationError("a"), ValidationError("b")])


def test_soft_validate_slug():
    assert soft_validate_slug("Hello World") == "hello-world"
