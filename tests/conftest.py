"""Shared pytest fixtures for liftlog."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from liftlog.musclegroup import MuscleGroup
from liftlog.exercise import Exercise, LiftStatus
from liftlog.rating import Rating
from liftlog.workset import WorkSet
from liftlog.routine import Routine
from liftlog.storage import JsonStorage, LibraryStore, SCHEMA_VERSION
from liftlog.tag import Tag

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_LIBRARY = FIXTURES / "sample_library.json"
STRONG_FIXTURE = FIXTURES / "imports" / "strong" / "2025" / "strong_2025_01.csv"

WGER_SQUAT = "615"
WGER_LONG = "123456"
WGER_ALT = "73"


@pytest.fixture
def tmp_library_path(tmp_path):
    return tmp_path / "library.json"


@pytest.fixture
def empty_storage(tmp_library_path):
    st = JsonStorage(tmp_library_path)
    st.load()
    return st


@pytest.fixture
def storage(empty_storage):
    return empty_storage


@pytest.fixture
def library_store(empty_storage):
    return empty_storage


@pytest.fixture
def json_storage(empty_storage):
    return empty_storage


@pytest.fixture
def audit_dir(tmp_path):
    return tmp_path


@pytest.fixture
def populated_storage(empty_storage):
    from liftlog.goals import LiftGoal

    quads = MuscleGroup.create("Quadriceps", id="mg-quads")
    chest = MuscleGroup.create("Chest", id="mg-chest")
    empty_storage.upsert_musclegroup(quads)
    empty_storage.upsert_musclegroup(chest)

    tag = Tag.create("main-lift", id="tag-001")
    empty_storage.upsert_tag(tag)
    routine = Routine(name="Push Day", id="routine-001")
    empty_storage.upsert_routine(routine)

    squat = Exercise.create(
        "Back Squat",
        id="ex-squat",
        wger=WGER_SQUAT,
        category="compound",
        target_1rm=180.0,
        best_1rm=160.0,
        status=LiftStatus.ACTIVE,
    )
    squat.musclegroup_ids = [quads.id]
    squat.tag_ids = ["tag-001"]
    squat.routine_ids = ["routine-001"]
    squat.started_at = "2024-09-01"

    bench = Exercise.create(
        "Bench Press",
        id="ex-bench",
        category="compound",
        target_1rm=120.0,
        best_1rm=110.0,
        status=LiftStatus.ACTIVE,
    )
    bench.musclegroup_ids = [chest.id]
    bench.started_at = "2024-09-01"

    legpress = Exercise.create(
        "Leg Press",
        id="ex-legpress",
        category="compound",
        best_1rm=300.0,
        status=LiftStatus.RETIRED,
    )
    legpress.musclegroup_ids = [quads.id]
    legpress.finished_at = "2025-06-15"
    legpress.rating = 3.5

    for e in (squat, bench, legpress):
        empty_storage.upsert_exercise(e)

    workset = WorkSet.create(
        squat.id,
        weight=140.0,
        reps=5,
        rpe=8.0,
        started_at="2025-03-15T20:00:00",
        notes="felt strong",
    )
    empty_storage.add_workset(workset)
    empty_storage.save_goals([LiftGoal.create("Log 200 sets in 2026", "sets", 200, "year")])
    return empty_storage


@pytest.fixture
def sample_library_dict(populated_storage):
    return populated_storage.snapshot()


@pytest.fixture
def populated_json_storage(populated_storage):
    return populated_storage


@pytest.fixture
def populated_library_store(populated_storage):
    return populated_storage


@pytest.fixture
def wger_id():
    return WGER_SQUAT


@pytest.fixture
def wger_long_id():
    return WGER_LONG


@pytest.fixture
def wger_id_alt():
    return WGER_ALT


@pytest.fixture
def sample_exercise():
    return Exercise.create(
        "Romanian Deadlift",
        id="exercise-test-1",
        category="compound",
        target_1rm=200.0,
        best_1rm=150.0,
        status=LiftStatus.ACTIVE,
    )


@pytest.fixture
def sample_read_exercise():
    e = Exercise.create(
        "Smith Machine Squat",
        id="exercise-read-1",
        category="compound",
        best_1rm=180.0,
        status=LiftStatus.RETIRED,
    )
    e.finished_at = "2025-06-15"
    return e


@pytest.fixture
def sample_reading_exercise(sample_exercise):
    return sample_exercise


@pytest.fixture
def sample_finished_exercise(sample_read_exercise):
    return sample_read_exercise


@pytest.fixture
def sample_musclegroup():
    return MuscleGroup.create("Hamstrings", id="mg-hams", email="hams@example.com")


@pytest.fixture
def sample_tag():
    return Tag.create("posterior-chain", id="tag-pc", color="#7b1e3a")


@pytest.fixture
def sample_routine():
    return Routine(name="Push Day", id="wl-fav")


@pytest.fixture
def sample_workset(sample_exercise):
    return WorkSet.create(
        sample_exercise.id,
        id="workset-fixture",
        weight=100.0,
        reps=8,
        rpe=7.5,
        started_at="2026-05-01T19:00:00",
    )


@pytest.fixture
def sample_rating(sample_exercise):
    return Rating.create(sample_exercise.id, value=4.0, review="Great hinge builder")


@pytest.fixture
def storage_with_exercise(empty_storage, sample_exercise, sample_musclegroup):
    empty_storage.upsert_musclegroup(sample_musclegroup)
    sample_exercise.musclegroup_ids = [sample_musclegroup.id]
    empty_storage.upsert_exercise(sample_exercise)
    return empty_storage


@pytest.fixture
def exercises_batch():
    rows = [
        ("Overhead Press", LiftStatus.ACTIVE),
        ("Pull-up", LiftStatus.MAINTENANCE),
        ("Leg Extension", LiftStatus.RETIRED),
        ("Behind-the-neck Press", LiftStatus.BENCHED),
        ("Snatch", LiftStatus.LEARNING),
    ]
    out = []
    for name, st in rows:
        e = Exercise.create(name, status=st)
        if st == LiftStatus.RETIRED:
            e.mark_done(date(2025, 1, 15))
        out.append(e)
    return out


@pytest.fixture
def mini_csv(tmp_path):
    p = tmp_path / "exercises.csv"
    p.write_text(
        "name,musclegroup,wger,equipment,category,best_1rm,target_1rm,unit,status,rating,tags\n"
        '"Back Squat","Quadriceps",615,Barbell,compound,160,180,kg,active,,main-lift\n'
        '"Bench Press","Chest",,Barbell,compound,110,120,kg,active,4,main-lift\n',
        encoding="utf-8",
    )
    return p


@pytest.fixture
def strong_csv():
    if STRONG_FIXTURE.exists():
        return STRONG_FIXTURE
    pytest.skip("strong fixture file not present")


@pytest.fixture
def strong_csv_tmp(tmp_path):
    p = tmp_path / "strong.csv"
    p.write_text(
        "Date,Workout Name,Exercise Name,Set Order,Weight,Reps,RPE,Notes\n"
        "2025-01-10 18:00:00,Push Day,Bench Press,1,100,5,8,\n"
        "2025-01-10 18:00:00,Push Day,Bench Press,2,100,5,8.5,top set\n"
        "2025-01-12 18:00:00,Leg Day,Back Squat,1,140,5,8,\n",
        encoding="utf-8-sig",
    )
    return p


@pytest.fixture
def hevy_csv(tmp_path):
    p = tmp_path / "hevy.csv"
    p.write_text(
        "title,start_time,exercise_title,set_index,weight_kg,reps,rpe\n"
        "Push Day,2025-02-01 17:30:00,Overhead Press,0,60,5,8\n"
        "Push Day,2025-02-01 17:30:00,Overhead Press,1,60,5,8.5\n"
        "Pull Day,2025-02-03 17:30:00,Barbell Row,0,90,8,7\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def lib(tmp_path):
    p = tmp_path / "library.json"
    st = JsonStorage(p)
    st.load()
    return p


def make_exercise(name: str, **kw) -> Exercise:
    return Exercise.create(name, **kw)


def seed_worksets(store: JsonStorage, exercise_id: str, days: list[date]) -> None:
    for i, d in enumerate(days):
        sess = WorkSet.create(
            exercise_id,
            weight=100.0 + i * 5,
            reps=5,
            started_at=d.isoformat() + "T20:00:00",
        )
        store.add_workset(sess)
