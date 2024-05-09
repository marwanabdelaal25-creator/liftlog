"""Tests for liftlog.wger (wger exercise-id handling)."""

import pytest

from liftlog import wger as wger_mod

WID = "615"


def test_validate_ok():
    assert wger_mod.validate_wger("615") is True
    assert wger_mod.validate_wger("1") is True
    assert wger_mod.validate_wger("123456") is True


def test_validate_garbage():
    assert wger_mod.validate_wger("squat") is False


def test_validate_empty():
    assert wger_mod.validate_wger("") is False
    assert wger_mod.validate_wger(None) is False


def test_validate_zero_and_too_long():
    assert wger_mod.validate_wger("0") is False
    assert wger_mod.validate_wger("1234567") is False  # 7 digits


def test_is_wger():
    assert wger_mod.is_wger("615") is True
    assert wger_mod.is_wger("x") is False


def test_normalize_strips_separators():
    assert wger_mod.normalize_wger("6 15") == "615"
    assert wger_mod.normalize_wger("00615") == "615"  # leading zeros


def test_normalize_bad_raises():
    with pytest.raises(ValueError):
        wger_mod.normalize_wger("nope")


def test_normalize_helper():
    assert wger_mod.normalize("615") == "615"
    assert wger_mod.normalize("junk") is None


def test_parse():
    assert wger_mod.parse("615") == "615"


def test_wger_url():
    assert wger_mod.wger_url("615") == "https://wger.de/en/exercise/615/view/"
    assert wger_mod.wger_url("junk") is None


def test_format_display():
    assert wger_mod.format_display("615") == "wger #615"
    assert wger_mod.format_display("weird") == "weird"


def test_guess_wger():
    assert wger_mod.guess_wger("see wger 615 for form") == "615"
    assert wger_mod.guess_wger("no id here at all !!") is None


def test_clean_id_list():
    assert wger_mod.clean_id_list("615, junk, 73") == ["615", "73"]


def test_batch_validate():
    d = wger_mod.batch_validate(["615", "nope"])
    assert d["615"] is True and d["nope"] is False


def test_compare_wger():
    assert wger_mod.compare_wger("615", "00615") is True
    assert wger_mod.compare_wger("615", "73") is False
    assert wger_mod.compare_wger("615", "junk") is False


def test_explain():
    assert "valid" in wger_mod.explain("615")
    assert wger_mod.explain("##") == "invalid wger id"
    assert wger_mod.explain("") == "empty id"


def test_aliases():
    assert wger_mod.is_valid("615") is True
    assert wger_mod.validate("615") is True
    assert wger_mod.format_wger("615") == "wger #615"
