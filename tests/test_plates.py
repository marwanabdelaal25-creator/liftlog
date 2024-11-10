"""Tests for liftlog.plates (barbell plate math)."""

import pytest

from liftlog import plates


def test_breakdown_kg():
    # 140kg on a 20kg bar -> 60 per side -> 25 + 25 + 10
    assert plates.plate_breakdown(140, bar=20, unit="kg") == [25.0, 25.0, 10.0]


def test_breakdown_empty_below_bar():
    assert plates.plate_breakdown(15, bar=20) == []


def test_total_from_plates():
    assert plates.total_from_plates([25.0, 25.0, 10.0], bar=20) == 140.0


def test_closest_loadable_exact():
    assert plates.closest_loadable(140, bar=20) == 140.0


def test_closest_loadable_rounds_down():
    # 141 not loadable with standard kg plates -> nearest below is 140
    assert plates.closest_loadable(141, bar=20) == 140.0


def test_is_loadable():
    assert plates.is_loadable(140, bar=20) is True
    assert plates.is_loadable(141, bar=20) is False


def test_format_loading():
    assert plates.format_loading([25.0, 25.0, 10.0]) == "25 + 25 + 10"
    assert plates.format_loading([2.5]) == "2.5"
    assert plates.format_loading([]) == "(empty bar)"


def test_lb_units():
    # 135lb on a 45lb bar -> 45 per side -> one 45
    assert plates.plate_breakdown(135, unit="lb") == [45.0]
    assert plates.total_from_plates([45.0], unit="lb") == 135.0


def test_warmup_scheme_ascending():
    scheme = plates.warmup_scheme(100, sets=4, bar=20)
    assert len(scheme) == 4
    assert scheme == sorted(scheme)
    assert scheme[-1] < 100


def test_warmup_scheme_zero():
    assert plates.warmup_scheme(100, sets=0) == []


def test_loading_plan():
    plan = plates.loading_plan(140, bar=20)
    assert plan["achieved"] == 140.0
    assert plan["exact"] is True
    assert plan["loading"] == "25 + 25 + 10"


def test_loading_plan_inexact():
    plan = plates.loading_plan(141, bar=20)
    assert plan["exact"] is False
