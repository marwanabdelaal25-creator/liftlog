"""Tests for liftlog.parser."""

from datetime import date, datetime

import pytest
from liftlog import parser


def test_parse_date_iso():
    assert parser.parse_date("2025-06-01") == date(2025, 6, 1)


def test_parse_date_slash_eu():
    assert parser.parse_date("15/03/2024") == date(2024, 3, 15)


def test_parse_date_bad():
    with pytest.raises(ValueError):
        parser.parse_date("not-a-date")


def test_parse_datetime_iso_t():
    dt = parser.parse_datetime("2025-01-01T12:30:00")
    assert dt.hour == 12


def test_parse_datetime_date_only():
    dt = parser.parse_datetime("2025-01-01")
    assert dt.date() == date(2025, 1, 1)


def test_parse_duration_minutes_suffix():
    assert parser.parse_duration("45min") == 45 * 60


def test_parse_duration_hms():
    assert parser.parse_duration("1h30m") == 5400


def test_parse_duration_plain_digits():
    assert parser.parse_duration("30") == 30 * 60


def test_parse_duration_bad():
    with pytest.raises(ValueError):
        parser.parse_duration("lots")


def test_parse_rating_slash_form():
    assert parser.parse_rating("4/5") == 4.0


def test_parse_rating_plain():
    assert parser.parse_rating("3.5") == 3.5


def test_parse_rating_out_of_range():
    with pytest.raises(ValueError):
        parser.parse_rating("6/5")


def test_parse_tags_empty():
    assert parser.parse_tags("") == []


def test_parse_tags_mixed_separators():
    tags = parser.parse_tags("sci-fi, fantasy; horror#cozy")
    assert "sci-fi" in tags
    assert "cozy" in tags


def test_parse_tags_dedupes():
    assert parser.parse_tags("a, a, A") == ["a"]


def test_parse_key_value_pairs():
    d = parser.parse_key_value_pairs("name=Squat, status=active")
    assert d["name"] == "Squat"
    assert d["status"] == "active"


def test_parse_progress_single():
    cur, tot = parser.parse_progress("120")
    assert cur == 120 and tot is None


def test_parse_progress_range():
    cur, tot = parser.parse_progress("45-320")
    assert cur == 45 and tot == 320


def test_parse_bool_truthy():
    assert parser.parse_bool("yes") is True
    assert parser.parse_bool("1") is True


def test_parse_bool_falsey():
    assert parser.parse_bool("no") is False


def test_coerce_int_ok():
    assert parser.coerce_int("42") == 42


def test_coerce_int_default():
    assert parser.coerce_int("x", default=7) == 7


def test_split_csv_line():
    parts = parser.split_csv_line('"hello", world, test')
    assert parts[0] == "hello"

from liftlog.parser import (
    format_duration,
    format_progress,
    human_join,
    parse_musclegroup_list,
    parse_env_flag,
    parse_import_format,
    parse_int_list,
    parse_page_range,
    parse_sort_spec,
    parse_year_range,
    tokenize_query,
)


def test_parse_page_range():
    assert parse_page_range("5-15") == (5, 15)


def test_parse_int_list_brackets():
    assert parse_int_list("[1,2]") == [1, 2]


def test_parse_musclegroup_list_semicolon():
    assert parse_musclegroup_list("A; B") == ["A", "B"]


def test_format_duration_minutes():
    assert "m" in format_duration(120)


def test_format_progress_with_total():
    assert format_progress(10, 100) == "10-100"


def test_parse_year_range_single():
    assert parse_year_range("2020") == (2020, 2020)


def test_parse_sort_spec_asc():
    field, asc = parse_sort_spec("+title")
    assert field == "title" and asc is True


def test_tokenize_query():
    assert tokenize_query("  a  b ") == ["a", "b"]


def test_parse_import_format_gr():
    assert parse_import_format("gr") == "strong"


def test_parse_env_flag_unknown():
    assert parse_env_flag("maybe") is None


def test_human_join_two():
    assert human_join(["a", "b"]) == "a and b"
