"""Tests for liftlog.storage."""

import json

import pytest
from liftlog.exercise import Exercise, LiftStatus
from liftlog.musclegroup import MuscleGroup
from liftlog.errors import NotFoundError, StorageError
from liftlog.workset import WorkSet
from liftlog.routine import Routine
from liftlog.storage import (
    JsonStorage,
    LibraryStore,
    SCHEMA_VERSION,
    open_storage,
    default_storage_path,
    _EMPTY,
)
from liftlog.tag import Tag
from liftlog.rating import Rating


def test_schema_version_constant():
    assert SCHEMA_VERSION == 2


def test_empty_structure_keys():
    assert "exercises" in _EMPTY
    assert "worksets" in _EMPTY


def test_json_storage_load_missing_file(json_storage):
    assert json_storage.list_exercises() == []


def test_json_storage_save_and_reload(tmp_path):
    path = tmp_path / "lib.json"
    st = JsonStorage(path)
    st.load()
    b = Exercise.create("Saved Exercise")
    st.upsert_exercise(b)
    st.save()
    st2 = JsonStorage(path)
    st2.load()
    assert len(st2.list_exercises()) == 1


def test_upsert_exercise_updates(json_storage, sample_exercise):
    json_storage.upsert_exercise(sample_exercise)
    sample_exercise.title = "Renamed"
    json_storage.upsert_exercise(sample_exercise)
    assert json_storage.get_exercise(sample_exercise.id).title == "Renamed"


def test_get_exercise_not_found(json_storage):
    with pytest.raises(NotFoundError):
        json_storage.get_exercise("missing")


def test_delete_exercise(json_storage, sample_exercise):
    json_storage.upsert_exercise(sample_exercise)
    json_storage.delete_exercise(sample_exercise.id)
    with pytest.raises(NotFoundError):
        json_storage.get_exercise(sample_exercise.id)


def test_delete_missing_raises(json_storage):
    with pytest.raises(NotFoundError):
        json_storage.delete_exercise("nope")


def test_list_musclegroups(json_storage, sample_musclegroup):
    json_storage.upsert_musclegroup(sample_musclegroup)
    assert len(json_storage.list_musclegroups()) == 1


def test_upsert_routine(json_storage):
    sh = Routine(name="queue")
    json_storage.upsert_routine(sh)
    assert len(json_storage.list_routines()) == 1


def test_add_workset(json_storage, sample_workset):
    json_storage.add_workset(sample_workset)
    assert len(json_storage.list_worksets()) == 1


def test_list_worksets_filter(json_storage, sample_workset):
    json_storage.add_workset(sample_workset)
    assert len(json_storage.list_worksets(exercise_id=sample_workset.exercise_id)) == 1
    assert json_storage.list_worksets(exercise_id="other") == []


def test_tags_roundtrip(json_storage, sample_tag):
    json_storage.upsert_tag(sample_tag)
    tags = json_storage.list_tags()
    assert tags[0].slug == sample_tag.slug


def test_ratings_filter(json_storage, sample_rating):
    json_storage.add_rating(sample_rating)
    assert len(json_storage.list_ratings(exercise_id=sample_rating.exercise_id)) == 1


def test_raw_get_set(json_storage):
    json_storage.raw_set("custom", [1, 2])
    assert json_storage.raw_get("custom") == [1, 2]


def test_snapshot_is_copy(json_storage, sample_exercise):
    json_storage.upsert_exercise(sample_exercise)
    snap = json_storage.snapshot()
    snap["exercises"] = []
    assert len(json_storage.list_exercises()) == 1


def test_corrupt_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    st = JsonStorage(path)
    with pytest.raises(StorageError):
        st.load()


def test_populated_fixture(populated_json_storage):
    assert len(populated_json_storage.list_exercises()) == 3


def test_library_store_upsert(library_store, sample_exercise):
    library_store.upsert_exercise(sample_exercise)
    assert sample_exercise.id in library_store.exercises


def test_library_store_save_reload(library_store, sample_exercise):
    library_store.upsert_exercise(sample_exercise)
    library_store.save()
    library_store.load()
    assert sample_exercise.id in library_store.exercises


def test_library_store_to_dict(library_store, sample_exercise):
    library_store.upsert_exercise(sample_exercise)
    d = library_store.to_dict()
    assert d["version"] == SCHEMA_VERSION


def test_open_storage(tmp_path):
    p = tmp_path / "x.json"
    st = open_storage(str(p))
    assert st.path == p


def test_default_storage_path():
    p = default_storage_path()
    assert p.name == "library.json"


def test_replace_all(json_storage, sample_library_dict):
    json_storage.replace_all(sample_library_dict)
    assert len(json_storage.list_exercises()) == 3


def test_ensure_defaults_on_empty(json_storage):
    json_storage.raw_set("goals", None)
    json_storage.load()
    assert json_storage.raw_get("goals") is not None or json_storage.raw_get("goals") == []

from liftlog.storage import LibraryFacade


def test_library_facade_add_exercise(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    b = lf.add_exercise("Facade Exercise")
    assert b.name == "Facade Exercise"


def test_library_facade_log_workset(tmp_library_path, sample_exercise):
    lf = LibraryFacade(str(tmp_library_path))
    lf.add_exercise(sample_exercise.name, id=sample_exercise.id, target_1rm=100)
    sess = lf.log_workset(sample_exercise.id, 100, 5)
    assert sess.weight == 100 and sess.reps == 5


def test_library_facade_stats_and_streak(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    assert "Training stats" in lf.stats_text()
    assert isinstance(lf.streak_text(), str)


def test_library_facade_entity_summary(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    assert "exercises" in lf.entity_summary()


def test_library_facade_find_exercise(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    lf.add_exercise("Unique Title XYZ")
    found = lf.find_exercise("Unique")
    assert found is not None


def test_library_facade_mark_retired(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    b = lf.add_exercise("To Finish", target_1rm=50)
    lf.log_workset(b.id, 50, 5)
    done = lf.mark_retired(b.id)
    assert done.status.value == "retired"


def test_library_facade_import_export_csv(tmp_library_path, mini_csv, tmp_path):
    lf = LibraryFacade(str(tmp_library_path))
    n = lf.import_csv(mini_csv)
    assert n >= 1
    out = tmp_path / "out.csv"
    assert lf.export_csv(out) >= 1


def test_entity_dict_get_set_del(empty_storage, sample_exercise, sample_musclegroup):
    empty_storage.upsert_musclegroup(sample_musclegroup)
    empty_storage.exercises[sample_exercise.id] = sample_exercise
    assert empty_storage.exercises[sample_exercise.id].name == sample_exercise.name
    del empty_storage.exercises[sample_exercise.id]
    with pytest.raises(NotFoundError):
        empty_storage.exercises[sample_exercise.id]
