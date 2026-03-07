"""Second coverage pass: search DSL, storage internals, migrate, plugins, recurring."""

from datetime import date

import pytest

from liftlog.exercise import Exercise, LiftStatus
from liftlog.musclegroup import MuscleGroup
from liftlog.tag import Tag
from liftlog.workset import WorkSet
from liftlog.rating import Rating
from liftlog.errors import NotFoundError, PluginError


# ----------------------------------------------------------------- search DSL

def test_search_advanced_all_branches(empty_storage):
    from liftlog.search import SearchEngine

    empty_storage.upsert_tag(Tag.create("main", id="t1"))
    e = Exercise.create("Back Squat", category="compound", wger="615", status=LiftStatus.ACTIVE)
    e.tag_ids = ["t1"]
    empty_storage.upsert_exercise(e)
    eng = SearchEngine(empty_storage)
    assert eng.advanced("tag:main")
    assert eng.advanced("name:squat")
    assert eng.advanced("category:compound")
    assert eng.advanced("wger:615")
    assert eng.advanced("status:active")
    assert isinstance(eng.advanced("tag:nope"), list)


def test_search_highlight_empty(empty_storage):
    from liftlog.search import SearchEngine

    assert SearchEngine(empty_storage).highlight("text", "") == "text"


def test_search_suggest(empty_storage):
    from liftlog.search import SearchEngine

    for t in ["Back Squat", "Front Squat", "Bench Press"]:
        empty_storage.upsert_exercise(Exercise.create(t))
    eng = SearchEngine(empty_storage)
    assert "Back Squat" in eng.suggest("Back")
    assert any("Bench" in x for x in eng.suggest("ench"))


def test_search_recent_exercises(empty_storage):
    from liftlog.search import SearchEngine

    fresh = Exercise.create("Recent")
    fresh.started_at = date.today().isoformat()
    empty_storage.upsert_exercise(fresh)
    old = Exercise.create("Old")
    old.started_at = "2000-01-01"
    empty_storage.upsert_exercise(old)
    bad = Exercise.create("Bad")
    bad.started_at = "notadate"
    empty_storage.upsert_exercise(bad)
    out = SearchEngine(empty_storage).recent_exercises(days=30)
    assert any(e.name == "Recent" for e in out)


# ----------------------------------------------------------------- storage

def test_storage_missing_lookups(empty_storage):
    with pytest.raises(NotFoundError):
        empty_storage.get_musclegroup("nope")
    with pytest.raises(NotFoundError):
        empty_storage.get_routine("nope")


def test_storage_delete_paths(empty_storage):
    empty_storage.upsert_musclegroup(MuscleGroup.create("Chest", id="m1"))
    empty_storage.delete_musclegroup("m1")
    assert empty_storage.list_musclegroups() == []
    empty_storage.upsert_tag(Tag.create("x", id="tg"))
    empty_storage.delete_tag("tg")
    empty_storage.add_workset(WorkSet.create("e", id="w1"))
    empty_storage.delete_workset("w1")
    assert empty_storage.list_worksets() == []


def test_storage_raw_and_filtered_lists(empty_storage):
    from liftlog.quotes import Quote
    from liftlog.notes import Note

    empty_storage.raw_set("foo", 42)
    assert empty_storage.raw_get("foo") == 42
    e = Exercise.create("Squat", id="e1")
    empty_storage.upsert_exercise(e)
    empty_storage.add_rating(Rating.create("e1", value=4.0))
    assert empty_storage.list_ratings("e1")
    empty_storage.add_quote(Quote.create("cue", "e1"))
    assert empty_storage.list_quotes("e1")
    empty_storage.add_note(Note.create("note body", "e1"))
    assert empty_storage.list_notes("e1")


def test_storage_equipment_program_collection(empty_storage):
    from liftlog.equipment import Equipment
    from liftlog.program import Program
    from liftlog.collections import Collection

    empty_storage.upsert_equipment(Equipment.create("Barbell"))
    assert empty_storage.list_equipment()
    empty_storage.upsert_program(Program.create("5/3/1"))
    assert empty_storage.list_programs()
    empty_storage.upsert_collection(Collection.create("Big 3"))
    assert empty_storage.list_collections()


def test_storage_worksets_by_exercise(empty_storage):
    empty_storage.add_workset(WorkSet.create("e1", id="w1", weight=100, reps=5))
    empty_storage.add_workset(WorkSet.create("e2", id="w2", weight=80, reps=8))
    assert len(empty_storage.list_worksets("e1")) == 1


# ----------------------------------------------------------------- migrate run

def test_migration_runner_run(tmp_path):
    from liftlog.storage import JsonStorage
    from liftlog.migrate import MigrationRunner

    st = JsonStorage(tmp_path / "m.json")
    st.load()
    st.replace_all({
        "version": 0,
        "exercises": [{"name": "Old", "status": "current", "max": 150}],
        "musclegroups": [], "worksets": [], "tags": [],
    })
    assert "after" in MigrationRunner(st).run()


def test_apply_to_file(tmp_path):
    from liftlog.storage import JsonStorage
    from liftlog import migrate

    st = JsonStorage(tmp_path / "a.json")
    st.load()
    st.replace_all({"version": 0, "exercises": [], "musclegroups": [], "worksets": [], "tags": []})
    assert migrate.apply_to_file(st) is True


def test_migrate_rollback(tmp_path):
    from liftlog import migrate

    target = tmp_path / "rb.json"
    migrate.rollback({"version": 1, "exercises": []}, target)
    assert target.exists()


def test_migrate_validate_warnings():
    from liftlog import migrate

    assert isinstance(migrate.validate_post_migration({"version": 99}), list)


# ----------------------------------------------------------------- recurring

def test_recurring_scheduler(empty_storage):
    from liftlog.recurring import RecurringScheduler

    sch = RecurringScheduler(empty_storage)
    rule = sch.create("Deload check", cadence="weekly")
    sch.mark_done(rule.id, when=date(2020, 1, 1))
    assert isinstance(sch.overdue(), list)
    assert isinstance(sch.due_today(), list)
    assert isinstance(sch.summary_text(), str)
    assert isinstance(sch.report(), str)
    assert sch.list_rules()[0].streak_days() >= 0
    sch.disable(rule.id)


def test_recurring_rule_cadences():
    from liftlog.recurring import RecurringRule, due_rules, load_rules

    for cadence in ("daily", "weekly", "monthly"):
        r = RecurringRule(id="r", name="n", cadence=cadence)
        r.mark_done(date(2025, 1, 1))
        assert r.next_due() > date(2025, 1, 1)
    r = RecurringRule(id="r2", name="n", cadence="daily")
    assert r.due() in (True, False)
    assert isinstance(due_rules(load_rules([r.to_dict()])), list)


# ----------------------------------------------------------------- plugins

def _plugin(name="p", hook="on_workset"):
    from liftlog.plugins import Plugin

    return Plugin(name=name, module="m", hooks={hook: lambda *a, **k: "ok-%s" % name})


def test_plugin_manager():
    from liftlog.plugins import PluginManager

    pm = PluginManager()
    pm.register(_plugin("p1"))
    assert pm.run_hook("on_workset") == ["ok-p1"]
    assert pm.run_hook_safe("on_workset")[0].value == "ok-p1"
    assert "p1" in pm.list_plugins()
    assert isinstance(pm.describe(), str)
    pm.disable("p1")
    assert pm.run_hook("on_workset") == []
    pm.enable("p1")
    pm.unload("p1")
    assert pm.list_plugins() == []


def test_plugin_hook_error():
    from liftlog.plugins import Plugin, PluginManager

    boom = Plugin(name="boom", module="m", hooks={"on_workset": lambda *a, **k: 1 / 0})
    pm = PluginManager()
    pm.register(boom)
    with pytest.raises(PluginError):
        pm.run_hook("on_workset")
    assert pm.run_hook_safe("on_workset")[0].error is not None


def test_plugin_load_failure():
    from liftlog.plugins import PluginManager

    with pytest.raises(PluginError):
        PluginManager().load_module("liftlog.__definitely_not_real__")


def test_register_hook_module_level():
    from liftlog import plugins

    plugins.register_hook("on_workset", lambda *a, **k: None, plugin_name="inline")
    assert isinstance(plugins.list_plugins(), list)


# ----------------------------------------------------------------- tags manager

def test_tags_manager_full(empty_storage):
    from liftlog.tags_manager import TagsManager

    tm = TagsManager(empty_storage)
    e = Exercise.create("Squat", id="e1")
    empty_storage.upsert_exercise(e)
    t1 = tm.create("main")
    tm.attach("e1", t1.name)
    assert tm.tags_for_exercise("e1")
    assert tm.usage_counts().get("main") == 1
    tm.detach("e1", t1.id)
    t2 = tm.create("accessory")
    e2 = Exercise.create("Curl", id="e2")
    e2.tag_ids = [t1.id, t2.id]
    empty_storage.upsert_exercise(e2)
    kept = tm.merge_tags(t2.id, t1.id)
    assert kept.id == t1.id
    assert isinstance(tm.unused(), list)
    assert tm.rename(t1.id, "renamed").slug == "renamed"
    assert tm.get_by_slug("nope") is None


# ----------------------------------------------------------------- entity edges

def test_exercise_from_dict_rating_object():
    e = Exercise.create("Squat")
    e.rating = Rating.create(e.id, value=4.0, review="great")
    assert Exercise.from_dict(e.to_dict()).rating_value == 4.0


def test_exercise_onerm_gap_none():
    assert Exercise.create("Squat", best_1rm=100).onerm_gap() is None


def test_quotes_random_empty(empty_storage):
    from liftlog.quotes import QuotesManager

    assert QuotesManager(empty_storage).random_quote() is None
    assert QuotesManager(empty_storage).daily_quote() is None


# ----------------------------------------------------------------- facade

def test_library_facade_methods(tmp_path):
    from liftlog.storage import LibraryFacade

    lf = LibraryFacade(str(tmp_path / "lib.json"))
    lf.add_exercise("Active One", id="o1", status=LiftStatus.ACTIVE)
    lf.add_exercise("Active Two", id="o2", status=LiftStatus.ACTIVE)
    assert len(lf.list_active()) == 2
    assert lf.find_exercise("Active One") is not None
    assert lf.find_exercise("nonexistent zzz") is None
    done = lf.mark_retired("o1")
    assert done.status == LiftStatus.RETIRED
    assert lf.path().name == "lib.json"
    csv_path = tmp_path / "exp.csv"
    assert lf.export_csv(csv_path) >= 1
    assert lf.import_csv(csv_path) >= 1
    assert "exercises" in lf.entity_summary()


def test_facade_backup(tmp_path):
    from liftlog.storage import LibraryFacade

    lf = LibraryFacade(str(tmp_path / "lib.json"))
    lf.add_exercise("Squat")
    assert lf.backup(tmp_path / "bk2").exists()
