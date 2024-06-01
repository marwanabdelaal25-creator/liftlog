"""Tests for liftlog.onerepmax (1RM estimation)."""

import pytest

from liftlog import onerepmax as orm


def test_epley_known_value():
    # 100 x 5 -> 100 * (1 + 5/30) = 116.67
    assert orm.epley(100, 5) == pytest.approx(116.67, abs=0.01)


def test_epley_single_rep_is_weight():
    assert orm.epley(140, 1) == 140.0


def test_brzycki_known_value():
    # 100 * 36 / (37 - 5) = 112.5
    assert orm.brzycki(100, 5) == pytest.approx(112.5, abs=0.01)


def test_lombardi():
    assert orm.lombardi(100, 1) == pytest.approx(100.0, abs=0.01)
    assert orm.lombardi(100, 5) > 100


def test_mcglothin_and_wathan_positive():
    assert orm.mcglothin(100, 5) > 100
    assert orm.wathan(100, 5) > 100


def test_estimate_default_epley():
    assert orm.estimate(100, 5) == pytest.approx(116.7, abs=0.1)


def test_estimate_unknown_formula_falls_back():
    assert orm.estimate(100, 5, "nonsense") == orm.estimate(100, 5, "epley")


def test_average_1rm_between_formulas():
    avg = orm.average_1rm(100, 5)
    assert 110 < avg < 125


def test_all_estimates_keys():
    est = orm.all_estimates(100, 5)
    assert set(est) == {"epley", "brzycki", "lombardi", "mcglothin", "wathan"}


def test_percent_of_1rm():
    # inverse Epley: 200 / (1 + 5/30) = 171.4
    assert orm.percent_of_1rm(200, 5) == pytest.approx(171.4, abs=0.1)


def test_rep_max_table():
    table = orm.rep_max_table(200, max_reps=5)
    assert len(table) == 5
    assert table[1] == pytest.approx(200.0, abs=0.1)
    assert table[5] < table[1]


def test_percent_table():
    pt = orm.percent_table(200)
    assert pt[50] == 100.0
    assert pt[90] == 180.0


def test_estimate_reps():
    # 171.4 against a 200 1RM should be ~5 reps
    assert orm.estimate_reps(171.4, 200) == 5


def test_estimate_reps_edge():
    assert orm.estimate_reps(200, 200) == 1
    assert orm.estimate_reps(0, 200) == 1


def test_training_max():
    assert orm.training_max(200) == 180.0
    assert orm.training_max(200, 0.85) == 170.0


def test_relative_intensity():
    assert orm.relative_intensity(160, 200) == 80.0
    assert orm.relative_intensity(100, 0) == 0.0


def test_reps_clamped():
    # absurd rep counts shouldn't blow up the linear formulas
    assert orm.brzycki(100, 50) > 0
