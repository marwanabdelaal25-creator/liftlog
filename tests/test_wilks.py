"""Tests for liftlog.wilks (bodyweight-adjusted strength scores)."""

import pytest

from liftlog import wilks


def test_wilks_male_positive():
    # 90kg lifter, 500kg total -> a sane Wilks in the ~300s
    score = wilks.wilks_score(90, 500, "male")
    assert 280 < score < 360


def test_wilks_female_positive():
    score = wilks.wilks_score(60, 300, "female")
    assert score > 0


def test_wilks_zero_inputs():
    assert wilks.wilks_score(0, 500) == 0.0
    assert wilks.wilks_score(90, 0) == 0.0


def test_dots_male_positive():
    score = wilks.dots_score(90, 500, "male")
    assert 280 < score < 380


def test_dots_female_positive():
    assert wilks.dots_score(60, 300, "female") > 0


def test_dots_zero_inputs():
    assert wilks.dots_score(0, 500) == 0.0
    assert wilks.dots_score(90, 0) == 0.0


def test_classify_levels():
    assert wilks.classify(0) == "untrained"
    assert wilks.classify(150) == "beginner"
    assert wilks.classify(250) == "intermediate"
    assert wilks.classify(350) == "advanced"
    assert wilks.classify(450) == "elite"
    assert wilks.classify(600) == "world-class"


def test_total_helper():
    assert wilks.total(180, 120, 220) == 520.0
    assert wilks.total(180, 0, None) == 180.0


def test_sex_aliases():
    assert wilks.wilks_score(60, 300, "f") == wilks.wilks_score(60, 300, "female")
