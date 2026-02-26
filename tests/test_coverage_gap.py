"""Broad coverage tests across the engine, CLI and utility layers."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from liftlog.cli import main
from liftlog.storage import LibraryStore, JsonStorage
from liftlog.exercise import Exercise, LiftStatus
from liftlog.musclegroup import MuscleGroup
from liftlog.workset import WorkSet
from liftlog.errors import NotFoundError, ValidationError


def _cli(data, *args):
    return main(["--data", str(data), *args])


# ---------------------------------------------------------------- CLI workflow

def test_cli_full_workflow(tmp_path):
    data = tmp_path / "lib.json"
    assert _cli(data, "init") == 0
    assert _cli(data, "exercise-add", "Back Squat", "--musclegroup", "Quadriceps",
                "--category", "compound", "--best", "160", "--target", "180",
                "--wger", "615", "--unit", "kg", "--status", "active") == 0
    assert _cli(data, "exercise-add", "Bench Press", "--category", "compound") == 0
    assert _cli(data, "exercise-list") == 0
    assert _cli(data, "exercise-list", "--status", "active", "--query", "Squat") == 0
    assert _cli(data, "search", "Squat") == 0
    assert _cli(data, "search", "--expr", "^Back") == 0
    assert _cli(data, "stats") == 0
    assert _cli(data, "report", "year") == 0
    assert _cli(data, "report", "log") == 0
    assert _cli(data, "report", "md") == 0
    assert _cli(data, "report", "next") == 0
    assert _cli(data, "goal-add", "Log 200 sets", "--kind", "sets", "--target", "200", "--period", "year") == 0
    assert _cli(data, "goal-list") == 0
    assert _cli(data, "tag-add", "main-lift", "--color", "#7b1e3a") == 0

    store = LibraryStore.open(data)
    eid = next(e.id for e in store.exercises.values() if e.name == "Back Squat")
    assert _cli(data, "tag-attach", eid, "main-lift") == 0
    assert _cli(data, "workset-log", eid, "140", "5", "--rpe", "8") == 0
    assert _cli(data, "rate", eid, "4.5", "--note", "money lift") == 0
    assert _cli(data, "exercise-show", eid) == 0
    assert _cli(data, "routine-add", "Push Day", eid) == 0
    assert _cli(data, "routine-list") == 0


def test_cli_import_export(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    src = tmp_path / "imp.csv"
    src.write_text("name,category,best_1rm\nDeadlift,compound,200\n", encoding="utf-8")
    assert _cli(data, "import", str(src), "--format", "csv") == 0
    assert _cli(data, "export", str(tmp_path / "o.csv"), "--format", "csv") == 0
    assert _cli(data, "export", str(tmp_path / "o.jsonl"), "--format", "jsonl") == 0
    assert _cli(data, "export", str(tmp_path / "o.md"), "--format", "md") == 0


def test_cli_import_strong(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    src = tmp_path / "s.csv"
    src.write_text("Date,Exercise Name,Weight,Reps,RPE\n2025-01-10,Bench Press,100,5,8\n", encoding="utf-8")
    assert _cli(data, "import", str(src), "--format", "strong") == 0


def test_cli_import_unknown_format(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    src = tmp_path / "x.dat"
    src.write_text("nope", encoding="utf-8")
    assert _cli(data, "import", str(src)) == 1


def test_cli_export_unknown_format(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "export", str(tmp_path / "o.zzz")) == 1


def test_cli_wger_check(tmp_path):
    data = tmp_path / "lib.json"
    assert _cli(data, "wger-check", "615") == 0
    assert _cli(data, "wger-check", "garbage") == 1


def test_cli_backup_and_migrate(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    _cli(data, "exercise-add", "Squat", "--best", "100")
    assert _cli(data, "backup", "--dir", str(tmp_path / "bk")) == 0
    assert _cli(data, "migrate") == 0


def test_cli_exercise_rm(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    _cli(data, "exercise-add", "Doomed")
    store = LibraryStore.open(data)
    eid = next(iter(store.exercises.values())).id
    assert _cli(data, "exercise-rm", eid) == 0


def test_cli_error_returns_two(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "exercise-show", "missing-id") == 2


@patch("urllib.request.urlopen")
def test_cli_fetch_wger(mock_urlopen, tmp_path):
    payload = {"name": "Squat", "category": {"name": "Legs"}}
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = m
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "fetch-wger", "615") == 0


# ---------------------------------------------------------------- routine

def test_routine_manager(empty_storage):
    from liftlog.routine import RoutineManager, Routine

    empty_storage.upsert_exercise(Exercise.create("Squat", id="e1"))
    rm = RoutineManager(empty_storage)
    r = rm.create("Leg Day", description="quads + posterior chain")
    assert rm.get(r.id).name == "Leg Day"
    assert rm.find_by_name("leg day").id == r.id
    rm.add_exercise(r.id, "e1")
    rm.add_exercise(r.id, "e1")
    assert rm.get(r.id).count() == 1
    rm.remove_exercise(r.id, "e1")
    assert rm.get(r.id).count() == 0
    assert "Leg Day" in rm.report(r.id)
    assert rm.default_routine() is not None


def test_routine_get_missing(empty_storage):
    from liftlog.routine import RoutineManager

    with pytest.raises(NotFoundError):
        RoutineManager(empty_storage).get("nope")


def test_routine_dataclass():
    from liftlog.routine import Routine

    r = Routine.create("Push Day")
    assert r.slug == "push-day"
    assert r.add_exercise("x") is True
    assert r.add_exercise("x") is False
    assert r.remove_exercise("x") is True
    assert Routine.from_dict(r.to_dict()).name == "Push Day"


# ---------------------------------------------------------------- collections

def test_collections_manager(empty_storage):
    from liftlog.collections import CollectionsManager, Collection

    empty_storage.upsert_exercise(Exercise.create("Squat", id="e1"))
    cm = CollectionsManager(empty_storage)
    c = cm.create("Big 3", description="squat bench deadlift")
    cm.add_exercise(c.id, "e1")
    cm.add_exercise(c.id, "e1")
    assert cm.exercises_in(c.id) == ["e1"]
    cm.remove_exercise(c.id, "e1")
    assert cm.exercises_in(c.id) == []
    assert cm.find_by_name("big 3").id == c.id


def test_collection_dataclass():
    from liftlog.collections import Collection

    c = Collection.create("C")
    c.add("a")
    assert c.includes("a") and c.size() == 1
    c.remove("a")
    assert Collection.from_dict(c.to_dict()).name == "C"


# ---------------------------------------------------------------- io_jsonl

def test_io_jsonl_roundtrip(populated_storage, tmp_path):
    from liftlog import io_jsonl

    dest = tmp_path / "e.jsonl"
    assert io_jsonl.export_jsonl_exercises(populated_storage, dest) == 3
    assert io_jsonl.count_lines(dest) == 3
    fresh = JsonStorage(tmp_path / "fresh.json")
    fresh.load()
    assert io_jsonl.import_jsonl_exercises(fresh, dest) == 3


def test_io_jsonl_worksets_and_full(populated_storage, tmp_path):
    from liftlog import io_jsonl

    w = tmp_path / "w.jsonl"
    assert io_jsonl.export_jsonl_worksets(populated_storage, w) >= 1
    fresh = JsonStorage(tmp_path / "f2.json")
    fresh.load()
    assert io_jsonl.import_jsonl_worksets(fresh, w) >= 1
    full = tmp_path / "full.jsonl"
    io_jsonl.export_full_library(populated_storage, full)
    assert isinstance(io_jsonl.import_mixed_jsonl(JsonStorage(tmp_path / "f3.json"), full), dict)


# ---------------------------------------------------------------- musclegroup

def test_musclegroup_manager(empty_storage):
    from liftlog.musclegroup import MuscleGroupManager, sort_musclegroups

    mm = MuscleGroupManager(empty_storage)
    m = mm.create("Quadriceps")
    assert mm.get(m.id).name == "Quadriceps"
    assert mm.find_by_name("quadriceps").id == m.id
    assert mm.find_or_create("Quadriceps").id == m.id
    assert mm.find_or_create("Hamstrings").name == "Hamstrings"
    e = Exercise.create("Squat")
    empty_storage.upsert_exercise(e)
    mm.attach_exercise(m.id, e.id)
    assert e.id in mm.exercises_for(m.id)
    assert isinstance(mm.report(), str)
    assert isinstance(sort_musclegroups(mm.list_all()), list)


def test_musclegroup_methods():
    m = MuscleGroup.create("Chest", email="c@example.com")
    m.add_exercise("e1")
    m.add_exercise("e1")
    m.remove_exercise("e1")
    m.merge_aliases(["Pecs"])
    assert m.matches("chest")
    assert MuscleGroup.from_dict(m.to_dict()).name == "Chest"


# ---------------------------------------------------------------- quotes

def test_quotes_manager(populated_storage, sample_exercise):
    from liftlog.quotes import QuotesManager, Quote

    populated_storage.upsert_exercise(sample_exercise)
    qm = QuotesManager(populated_storage)
    q = qm.add(Quote.create("Light weight, baby", sample_exercise.id, tags=["hype"]))
    assert qm.get(q.id).text.startswith("Light")
    assert qm.list_for_exercise(sample_exercise.id)
    assert qm.search("weight")
    assert qm.by_tag("hype")
    assert qm.random_quote() is not None
    assert qm.daily_quote() is not None
    assert "weight" in qm.export_text()
    assert isinstance(qm.stats(), dict)
    qm.delete(q.id)


def test_quote_dataclass(sample_exercise):
    from liftlog.quotes import Quote

    q = Quote.create("a fairly wordy coaching cue here", sample_exercise.id)
    assert q.word_count() == 6
    assert q.preview(4)
    assert Quote.from_dict(q.to_dict()).text == q.text


# ---------------------------------------------------------------- parser

def test_parser_durations_and_dates():
    from liftlog import parser

    assert parser.parse_duration("90") == 5400
    assert parser.parse_duration("1h30m") == 5400
    with pytest.raises(ValueError):
        parser.parse_duration("xx")
    assert parser.parse_date("2025-01-02").year == 2025
    assert parser.parse_date("today") == date.today()
    with pytest.raises(ValueError):
        parser.parse_date("nope")
    assert parser.parse_datetime("2025-01-02T10:00:00").hour == 10
    assert parser.parse_datetime("2025-01-02").hour == 0


def test_parser_misc():
    from liftlog import parser

    assert parser.parse_progress("150/750") == (150, 750)
    assert parser.parse_progress("45-320") == (45, 320)
    assert parser.parse_progress("100") == (100, None)
    assert parser.parse_key_value_pairs("a=1, b:2, junk") == {"a": "1", "b": "2"}
    assert parser.parse_key_value("k: v") == ("k", "v")
    with pytest.raises(ValueError):
        parser.parse_key_value("noseparator")
    assert parser.parse_tags("legs; #quads, legs") == ["legs", "quads"]
    assert parser.parse_rating("4.5") == 4.5
    assert parser.parse_rating("90/100") == 4.5
    with pytest.raises(ValueError):
        parser.parse_rating("9")
    assert parser.split_csv_line('a,"b,c",d') == ["a", "b,c", "d"]
    assert parser.coerce_int("x", 7) == 7
    assert parser.coerce_bool("yes") is True
    assert parser.parse_bool("no") is False
    assert parser.format_duration(30) == "30m"
    assert parser.format_duration(90) == "1h 30m"
    assert parser.format_progress(150, 750) == "150-750"
    assert parser.format_progress(100) == "100"
    assert parser.human_join([]) == ""
    assert parser.human_join(["a"]) == "a"
    assert parser.human_join(["a", "b"]) == "a and b"
    assert "and" in parser.human_join(["a", "b", "c"])
    assert parser.parse_musclegroup_list("A; B") == ["A", "B"]
    assert parser.parse_env_flag("on") is True
    assert parser.parse_env_flag("off") is False
    assert parser.parse_env_flag("maybe") is None
    assert parser.parse_import_format("csv") == "csv"
    assert parser.parse_int_list("[1, 2, 3]") == [1, 2, 3]
    assert parser.parse_int_list("") == []
    assert parser.parse_page_range("10-20") == (10, 20)
    assert parser.parse_sort_spec("-best") == ("best", False)
    assert parser.parse_year_range("2010-2020") == (2010, 2020)
    assert parser.tokenize_query("a b  c") == ["a", "b", "c"]


# ---------------------------------------------------------------- migrate

def test_migrate_v0_to_v2():
    from liftlog import migrate

    data = {"version": 0, "exercises": [{"name": "Old", "status": "current", "max": 150}]}
    assert migrate.needs_migration(data)
    out = migrate.migrate_data(data)
    assert out["version"] == migrate.SCHEMA_VERSION
    assert out["exercises"][0]["status"] == "active"
    assert isinstance(migrate.migration_plan(data), list)
    assert isinstance(migrate.describe(data), str)
    assert isinstance(migrate.validate_post_migration(out), list)


def test_migrate_helpers():
    from liftlog import migrate

    rec = migrate.normalize_exercise_record({"status": "dropped", "max": 150})
    assert rec["status"] == "retired" and rec["best_1rm"] == 150
    data = {"exercises": [{"status": "injured"}]}
    assert migrate.normalize_all_exercises(data) == 1
    before = {"version": 0, "exercises": []}
    after, snap = migrate.migrate_with_backup(before)
    assert "version" in migrate.diff_versions(before, after)
    assert migrate.backup_before_migrate(before)["version"] == 0


def test_migration_runner(populated_storage):
    from liftlog.migrate import MigrationRunner

    runner = MigrationRunner(populated_storage)
    assert isinstance(runner.status(), str)
    assert isinstance(runner.preview(), dict)


# ---------------------------------------------------------------- backup

def test_backup_roundtrip(populated_storage, tmp_path):
    from liftlog import backup

    out = backup.create_backup(populated_storage, tmp_path / "bk")
    assert out.exists()
    assert backup.verify_backup(out)
    assert backup.list_backups(tmp_path / "bk")
    target = tmp_path / "restored.json"
    backup.restore_backup(out, target)
    assert target.exists()


def test_backup_compressed_and_prune(populated_storage, tmp_path):
    from liftlog import backup

    bkdir = tmp_path / "bk2"
    for _ in range(3):
        backup.create_backup(populated_storage, bkdir, compress=True)
    assert backup.checksum("x") == backup.checksum("x")
    assert backup.prune_old(bkdir, keep=1) >= 0


# ---------------------------------------------------------------- storage

def test_storage_crud_and_errors(empty_storage):
    e = Exercise.create("Squat", id="e1")
    empty_storage.upsert_exercise(e)
    assert empty_storage.get_exercise("e1").name == "Squat"
    with pytest.raises(NotFoundError):
        empty_storage.get_exercise("missing")
    empty_storage.delete_exercise("e1")
    assert empty_storage.list_exercises() == []
    assert "exercises" in empty_storage.snapshot()
    assert isinstance(empty_storage.count_entities(), dict)


# ---------------------------------------------------------------- validators

def test_validators_branches():
    from liftlog import validators as v

    assert v.validate_wger_field(None) is None
    with pytest.raises(ValidationError):
        v.validate_wger_field("not-valid")
    with pytest.raises(ValidationError):
        v.validate_progress(150.0)
    with pytest.raises(ValidationError):
        v.chk_id("x" * 65)
    assert v.chk_id("ok") == "ok"
    with pytest.raises(ValidationError):
        v.validate_hex_color("nope")
    with pytest.raises(ValidationError):
        v.validate_positive_int(0, "n")
    with pytest.raises(ValidationError):
        v.validate_status("weird", ["ok"])
    assert v.sanitize_filename('a/b:c') == "a_b_c"
    assert v.soft_validate_slug("Big Lifts!!") == "big-lifts"
    assert v.validate_id_list(["a", "a", "b"]) == ["a", "b"]
    assert v.validate_percent(50.0) == 50.0
    assert v.validate_goal_target(5, "sets") == 5
    assert v.merge_errors([ValidationError("x", field="f")])
    assert v.validate_url("https://x.io").startswith("https")
    with pytest.raises(ValidationError):
        v.validate_url("ftp://x")
