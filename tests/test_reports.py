"""Tests for liftlog.reports."""

import pytest

from liftlog.reports import ReportBuilder, _bar
from liftlog.goals import LiftGoal, GoalsManager
from liftlog.exercise import Exercise, LiftStatus


def test_bar_empty():
    assert _bar(0.0) == "[--------------------]"


def test_bar_full():
    assert _bar(100.0) == "[####################]"


def test_bar_half():
    assert _bar(50.0, width=10).count("#") == 5


def test_overview_contains_title(populated_json_storage):
    text = ReportBuilder(populated_json_storage).overview()
    assert "Liftlog Training Overview" in text


def test_overview_status_breakdown(populated_json_storage):
    assert "By status" in ReportBuilder(populated_json_storage).overview()


def test_overview_multiline(populated_json_storage):
    assert ReportBuilder(populated_json_storage).overview().count("\n") >= 3


def test_status_report_all(populated_json_storage):
    text = ReportBuilder(populated_json_storage).status_report()
    assert "Back Squat" in text or "Bench Press" in text


def test_status_report_header(populated_json_storage):
    lines = ReportBuilder(populated_json_storage).status_report().splitlines()
    assert lines[0].startswith("Exercise")


def test_status_report_filtered(populated_json_storage):
    text = ReportBuilder(populated_json_storage).status_report(status="retired")
    assert isinstance(text, str)


def test_status_report_empty(json_storage):
    assert ReportBuilder(json_storage).status_report() == "No exercises match."


def test_goals_report_empty(json_storage):
    assert "No goals" in ReportBuilder(json_storage).goals_report()


def test_goals_report_with_goal(json_storage):
    GoalsManager(json_storage).add_goal(LiftGoal.create("Log 100 sets", "sets", 100, "year"))
    text = ReportBuilder(json_storage).goals_report()
    assert "Log 100 sets" in text and "%" in text


def test_yearly_summary(populated_json_storage):
    text = ReportBuilder(populated_json_storage).yearly_summary(2025)
    assert "2025" in text
    assert "Total volume" in text


def test_yearly_summary_default_year(populated_json_storage):
    assert "summary" in ReportBuilder(populated_json_storage).yearly_summary().lower()


def test_yearly_summary_best_lifts(populated_json_storage):
    assert "Best lifts" in ReportBuilder(populated_json_storage).yearly_summary(2025)


def test_recent_worksets(populated_json_storage):
    text = ReportBuilder(populated_json_storage).recent_worksets(limit=5)
    assert "Recent sets" in text
    assert "140" in text  # the squat set weight


def test_what_to_train(empty_storage):
    a = Exercise.create("Squat", best_1rm=160, target_1rm=200, status=LiftStatus.ACTIVE)
    b = Exercise.create("Bench", best_1rm=118, target_1rm=120, status=LiftStatus.ACTIVE)
    empty_storage.upsert_exercise(a)
    empty_storage.upsert_exercise(b)
    out = ReportBuilder(empty_storage).what_to_train()
    # Squat has the bigger gap (40 vs 2), should come first
    assert out.index("Squat") < out.index("Bench")


def test_what_to_train_none(empty_storage):
    assert "No active lifts" in ReportBuilder(empty_storage).what_to_train()


def test_export_text(populated_json_storage):
    assert "Overview" in ReportBuilder(populated_json_storage).export_text()


def test_export_markdown(populated_json_storage):
    md = ReportBuilder(populated_json_storage).export_markdown()
    assert "# My Training Log" in md
    assert "Rating(" not in md


def test_compare_years(populated_json_storage):
    assert "vs" in ReportBuilder(populated_json_storage).compare_years(2024, 2025)


def test_notes_digest_all(populated_storage, sample_exercise):
    from liftlog.notes import Note

    populated_storage.upsert_exercise(sample_exercise)
    populated_storage.add_note(Note.create("brace harder", sample_exercise.id))
    assert "Notes" in ReportBuilder(populated_storage).notes_digest()


def test_notes_digest_exercise(populated_storage, sample_exercise):
    from liftlog.notes import Note

    populated_storage.upsert_exercise(sample_exercise)
    populated_storage.add_note(Note.create("body", sample_exercise.id, title="N"))
    md = ReportBuilder(populated_storage).notes_digest(sample_exercise.id)
    assert sample_exercise.name in md or "body" in md


def test_quotes_digest(populated_storage, sample_exercise):
    from liftlog.quotes import Quote

    populated_storage.upsert_exercise(sample_exercise)
    populated_storage.add_quote(Quote(text="No pain no gain", exercise_id=sample_exercise.id))
    assert ReportBuilder(populated_storage).quotes_digest()


def test_program_report(populated_storage):
    assert isinstance(ReportBuilder(populated_storage).program_report(), str)


def test_equipment_report(populated_storage):
    assert isinstance(ReportBuilder(populated_storage).equipment_report(), str)


def test_full_digest(populated_storage):
    assert "Overview" in ReportBuilder(populated_storage).full_digest()
