"""Tests for liftlog.stats."""

from datetime import date

import pytest

from liftlog.exercise import Exercise, LiftStatus
from liftlog.workset import WorkSet
from liftlog.stats import (
    LibraryStats,
    StatsReporter,
    at_goal_count,
    at_goal_rate,
    average_best_1rm,
    average_rpe,
    avg_exercise_rating,
    benched_rate,
    best_lifts,
    category_distribution,
    compare_years,
    compute_stats,
    count_by_status,
    detect_prs,
    exercise_1rm_history,
    exercises_trained_in_year,
    format_breakdown,
    format_leaderboard,
    format_stats,
    monthly_volume,
    musclegroup_distribution,
    pr_count,
    rating_distribution,
    status_percentages,
    top_musclegroups,
    top_tags,
    total_volume,
    training_pace,
    training_velocity,
    volume_by_month,
    volume_by_musclegroup,
    volume_by_weekday,
    volume_in_range,
)


def test_count_by_status_empty(json_storage):
    assert count_by_status(json_storage) == {}


def test_count_by_status(populated_json_storage):
    c = count_by_status(populated_json_storage)
    assert c.get("active") == 2
    assert c.get("retired") == 1


def test_volume_in_range(populated_json_storage):
    assert volume_in_range(populated_json_storage, date(2025, 1, 1), date(2025, 12, 31)) == 700.0


def test_volume_in_range_empty(json_storage):
    assert volume_in_range(json_storage, date(2099, 1, 1), date(2099, 1, 31)) == 0.0


def test_total_volume(populated_json_storage):
    assert total_volume(populated_json_storage) == 700.0


def test_avg_rating(populated_json_storage):
    assert avg_exercise_rating(populated_json_storage) == 3.5


def test_avg_rating_empty(json_storage):
    assert avg_exercise_rating(json_storage) is None


def test_top_tags(populated_json_storage):
    assert ("main-lift", 1) in top_tags(populated_json_storage)


def test_training_pace_keys(json_storage):
    pace = training_pace(json_storage, days=7)
    assert pace["window_days"] == 7
    assert "volume" in pace and "volume_per_day" in pace


def test_compute_stats(populated_json_storage):
    st = compute_stats(populated_json_storage)
    assert st.total_exercises == 3
    assert st.worksets_count == 1
    assert st.total_volume == 700.0
    assert st.musclegroups_count == 2


def test_library_stats_summary_lines():
    st = LibraryStats(total_exercises=5, musclegroups_count=3, worksets_count=10,
                      avg_rating=4.1, total_volume=12000)
    lines = st.summary_lines()
    assert any("Exercises: 5" in ln for ln in lines)
    assert any("Lifetime volume" in ln for ln in lines)


def test_format_stats(populated_json_storage):
    text = format_stats(populated_json_storage)
    assert "Training stats" in text
    assert "At goal" in text


def test_at_goal_count(populated_json_storage):
    assert at_goal_count(populated_json_storage) == 0


def test_at_goal_count_some(empty_storage):
    empty_storage.upsert_exercise(Exercise.create("A", best_1rm=200, target_1rm=180))
    assert at_goal_count(empty_storage) == 1


def test_category_distribution(populated_json_storage):
    assert category_distribution(populated_json_storage)["compound"] == 3


def test_musclegroup_distribution(populated_json_storage):
    dist = musclegroup_distribution(populated_json_storage)
    assert dist["Quadriceps"] == 2
    assert dist["Chest"] == 1


def test_top_musclegroups(populated_json_storage):
    assert top_musclegroups(populated_json_storage, 3)[0] == ("Quadriceps", 2)


def test_volume_by_musclegroup(populated_json_storage):
    by = volume_by_musclegroup(populated_json_storage)
    assert by.get("Quadriceps") == 700.0


def test_best_lifts(populated_json_storage):
    lifts = best_lifts(populated_json_storage, 3)
    assert lifts[0] == ("Leg Press", 300.0)


def test_exercise_1rm_history(populated_json_storage):
    hist = exercise_1rm_history(populated_json_storage, "ex-squat")
    assert hist == [("2025-03-15", pytest.approx(163.3, abs=0.1))]


def test_detect_prs(empty_storage):
    empty_storage.upsert_exercise(Exercise.create("Squat", id="s1"))
    empty_storage.add_workset(WorkSet.create("s1", weight=100, reps=5, started_at="2025-01-01T10:00:00"))
    empty_storage.add_workset(WorkSet.create("s1", weight=110, reps=5, started_at="2025-01-08T10:00:00"))
    empty_storage.add_workset(WorkSet.create("s1", weight=105, reps=5, started_at="2025-01-15T10:00:00"))
    prs = detect_prs(empty_storage, "s1")
    assert len(prs) == 2  # 100 then 110; 105 is not a new e1RM best


def test_pr_count(populated_json_storage):
    assert pr_count(populated_json_storage) == 1


def test_format_breakdown(populated_storage):
    out = format_breakdown(populated_storage)
    assert "Detailed stats" in out
    assert "By category:" in out
    assert "Top muscle groups:" in out
    assert "Best lifts:" in out


def test_monthly_volume(populated_storage):
    assert monthly_volume(populated_storage, 2025, 3) == 700.0


def test_volume_by_month(populated_storage):
    assert volume_by_month(populated_storage, 2025) == {3: 700.0}


def test_status_percentages(populated_storage):
    pcts = status_percentages(populated_storage)
    assert abs(sum(pcts.values()) - 100.0) < 0.5


def test_average_best_1rm(populated_storage):
    # (160 + 110 + 300) / 3
    assert average_best_1rm(populated_storage) == pytest.approx(190.0, abs=0.1)


def test_average_best_1rm_empty(empty_storage):
    assert average_best_1rm(empty_storage) is None


def test_volume_by_weekday(populated_storage):
    by = volume_by_weekday(populated_storage)
    assert len(by) == 7
    assert by[5] == 700.0  # 2025-03-15 Saturday


def test_at_goal_rate(populated_storage):
    assert at_goal_rate(populated_storage) == 0.0


def test_at_goal_rate_empty(empty_storage):
    assert at_goal_rate(empty_storage) == 0.0


def test_benched_rate_empty(empty_storage):
    assert benched_rate(empty_storage) == 0.0


def test_benched_rate(empty_storage, exercises_batch):
    for e in exercises_batch:
        empty_storage.upsert_exercise(e)
    assert benched_rate(empty_storage) == 20.0


def test_average_rpe(populated_storage):
    assert average_rpe(populated_storage) == 8.0


def test_average_rpe_none(empty_storage):
    assert average_rpe(empty_storage) is None


def test_rating_distribution(populated_storage):
    assert isinstance(rating_distribution(populated_storage), dict)


def test_format_leaderboard(populated_storage):
    assert "Strongest lifts" in format_leaderboard(populated_storage)


def test_format_leaderboard_empty(empty_storage):
    assert "No logged lifts" in format_leaderboard(empty_storage)


def test_training_velocity(populated_storage):
    assert training_velocity(populated_storage) >= 0


def test_exercises_trained_in_year(populated_storage):
    assert exercises_trained_in_year(populated_storage, 2025) == 1


def test_compare_years(populated_storage):
    assert "2025" in compare_years(populated_storage, 2024, 2025)


def test_reporter_full(populated_storage):
    assert "Detailed" in StatsReporter(populated_storage).full_report()


def test_reporter_quick(populated_storage):
    assert "Training stats" in StatsReporter(populated_storage).quick()


def test_reporter_export_json(populated_storage):
    data = StatsReporter(populated_storage).export_json_summary()
    assert "total_volume" in data and "at_goal" in data


def test_reporter_entity_counts(populated_storage):
    assert isinstance(StatsReporter(populated_storage).entity_counts(), dict)


def test_reporter_weekday_chart(populated_storage):
    assert "Mon" in StatsReporter(populated_storage).weekday_chart()


def test_reporter_monthly_table(populated_storage):
    assert "2025" in StatsReporter(populated_storage).monthly_table(2025)


def test_reporter_musclegroup_chart(populated_storage):
    assert "Quadriceps" in StatsReporter(populated_storage).musclegroup_chart()


def test_reporter_musclegroup_chart_empty(empty_storage):
    assert "No muscle groups" in StatsReporter(empty_storage).musclegroup_chart()


def test_reporter_best_lifts_table(populated_storage):
    assert "Leg Press" in StatsReporter(populated_storage).best_lifts_table()


def test_reporter_best_lifts_table_empty(empty_storage):
    assert "No lifts" in StatsReporter(empty_storage).best_lifts_table()
