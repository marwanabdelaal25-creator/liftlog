"""Tests for liftlog.recurring."""

from datetime import date, timedelta

import pytest
from liftlog.recurring import RecurringRule, load_rules, due_rules


def test_daily_rule_due():
    r = RecurringRule(name="read daily", cadence="daily")
    assert r.due(date(2025, 5, 1)) is True


def test_daily_rule_done_today():
    r = RecurringRule(name="read daily", cadence="daily", last_done=date(2025, 5, 1))
    assert r.due(date(2025, 5, 1)) is False


def test_weekly_wrong_weekday():
    r = RecurringRule(name="weekend", cadence="weekly", weekdays=[5, 6])
    assert r.due(date(2025, 5, 5)) is False  # Monday


def test_weekly_right_weekday():
    r = RecurringRule(name="weekend", cadence="weekly", weekdays=[5, 6])
    assert r.due(date(2025, 5, 10)) is True  # Saturday


def test_disabled_rule():
    r = RecurringRule(name="off", enabled=False)
    assert r.due() is False


def test_mark_done():
    r = RecurringRule(name="x", cadence="daily")
    r.mark_done(date(2025, 1, 15))
    assert r.last_done == date(2025, 1, 15)


def test_next_due_daily():
    r = RecurringRule(name="x", cadence="daily", last_done=date(2025, 1, 1))
    assert r.next_due() == date(2025, 1, 2)


def test_next_due_weekly():
    r = RecurringRule(name="x", cadence="weekly", weekdays=[0], last_done=date(2025, 1, 5))
    nxt = r.next_due()
    assert nxt.weekday() == 0


def test_to_dict_roundtrip():
    r = RecurringRule(name="x", last_done=date(2025, 2, 1))
    d = r.to_dict()
    r2 = RecurringRule.from_dict(d)
    assert r2.last_done == r.last_done


def test_load_rules():
    data = [{"name": "a", "cadence": "daily"}, {"name": "b", "cadence": "weekly"}]
    rules = load_rules(data)
    assert len(rules) == 2


def test_due_rules_filters():
    rules = [
        RecurringRule(name="a", cadence="daily", last_done=date.today()),
        RecurringRule(name="b", cadence="daily"),
    ]
    due = due_rules(rules)
    assert len(due) == 1
    assert due[0].name == "b"


def test_target_minutes_default():
    r = RecurringRule(name="x")
    assert r.target_minutes == 30


def test_id_generated():
    r = RecurringRule(name="auto")
    assert r.id


def test_from_dict_no_last_done():
    r = RecurringRule.from_dict({"name": "n", "cadence": "daily"})
    assert r.last_done is None


def test_mark_done_default_today():
    r = RecurringRule(name="x")
    r.mark_done()
    assert r.last_done == date.today()


def test_weekdays_default_all():
    r = RecurringRule(name="x")
    assert len(r.weekdays) == 7


def test_next_due_no_last_done():
    r = RecurringRule(name="x", cadence="daily")
    assert r.next_due() >= date.today()


def test_to_dict_last_done_none():
    d = RecurringRule(name="x").to_dict()
    assert "last_done" not in d or d.get("last_done") is None


def test_due_rules_empty():
    assert due_rules([]) == []

from datetime import date

import pytest
from liftlog.errors import NotFoundError
from liftlog.recurring import RecurringRule, RecurringScheduler


def test_recurring_scheduler_flow(empty_storage):
    rs = RecurringScheduler(empty_storage)
    rule = rs.create("Daily read", cadence="daily", target_minutes=20)
    assert len(rs.list_rules()) == 1
    rs.mark_done(rule.id, date.today())
    rs.disable(rule.id)
    assert "Recurring" in rs.report()


def test_recurring_mark_missing(empty_storage):
    with pytest.raises(NotFoundError):
        RecurringScheduler(empty_storage).mark_done("missing")


def test_recurring_rule_to_dict():
    r = RecurringRule(name="R", last_done=date(2024, 1, 1))
    assert r.to_dict()["last_done"] == "2024-01-01"
