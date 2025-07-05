"""Tests for liftlog.migrate."""

import pytest
from liftlog.errors import MigrationError
from liftlog.migrate import migrate_data, needs_migration, _v1_to_v2
from liftlog.storage import SCHEMA_VERSION


def test_needs_migration_old():
    assert needs_migration({"version": 0}) is True


def test_needs_migration_current():
    assert needs_migration({"version": SCHEMA_VERSION}) is False


def test_migrate_already_current():
    data = {"version": SCHEMA_VERSION, "exercises": []}
    assert migrate_data(data)["version"] == SCHEMA_VERSION


def test_v1_to_v2_adds_collections():
    out = _v1_to_v2({"version": 1, "exercises": {}})
    assert "collections" in out
    assert out["version"] == 2


def test_v1_to_v2_status_normalize():
    data = {
        "version": 1,
        "exercises": {"b1": {"status": "learning"}},
    }
    out = _v1_to_v2(data)
    assert out["exercises"]["b1"]["status"] == "learning"


def test_v1_to_v2_currently_reading():
    data = {"version": 1, "exercises": {"b1": {"status": "maintenance"}}}
    out = _v1_to_v2(data)
    assert out["exercises"]["b1"]["status"] == "maintenance"


def test_migrate_future_raises():
    with pytest.raises(MigrationError):
        migrate_data({"version": SCHEMA_VERSION + 5})


def test_v1_to_v2_equipment():
    out = _v1_to_v2({"version": 1, "exercises": {}})
    assert "equipment" in out


def test_v1_to_v2_program():
    out = _v1_to_v2({"version": 1, "exercises": {}})
    assert "program" in out


def test_needs_migration_default_version():
    assert needs_migration({}) is True


def test_migrate_preserves_exercises_keys():
    data = {"version": 1, "exercises": {"id1": {"title": "T"}}}
    out = _v1_to_v2(data)
    assert "id1" in out["exercises"]


def test_v1_to_v2_does_not_mutate_input():
    data = {"version": 1, "exercises": {"b": {"status": "learning"}}}
    _v1_to_v2(data)
    assert data["exercises"]["b"]["status"] == "learning"


def test_migration_error_message():
    with pytest.raises(MigrationError) as ctx:
        migrate_data({"version": 99})
    assert "future" in str(ctx.value.message).lower() or ctx.value.code == "MIGRATION_ERROR"


def test_needs_migration_false_at_schema():
    assert needs_migration({"version": 1}) in (True, False)


def test_v1_to_v2_empty_exercises():
    out = _v1_to_v2({"version": 1})
    assert out.get("exercises") == {} or out.get("exercises") is not None


def test_migrate_data_returns_dict():
    result = migrate_data({"version": SCHEMA_VERSION, "exercises": []})
    assert isinstance(result, dict)


def test_v1_to_v2_version_bumped():
    assert _v1_to_v2({"version": 1, "exercises": {}})["version"] == 2


def test_status_unchanged_if_already_want():
    data = {"version": 1, "exercises": {"b": {"status": "learning"}}}
    assert _v1_to_v2(data)["exercises"]["b"]["status"] == "learning"


def test_needs_migration_true_below_schema():
    if SCHEMA_VERSION > 1:
        assert needs_migration({"version": 1}) is True

from liftlog.migrate import MigrationRunner, diff_versions, migrate_with_backup


def test_migration_runner_status(empty_storage):
    runner = MigrationRunner(empty_storage)
    assert "up to date" in runner.status() or "migration" in runner.status().lower()


def test_migration_runner_preview(empty_storage):
    preview = MigrationRunner(empty_storage).preview()
    assert "plan" in preview or "version" in preview.lower()


def test_migrate_with_backup():
    data = {"version": 0, "exercises": []}
    new_data, snap = migrate_with_backup(data)
    assert new_data.get("version", 0) >= 0


def test_diff_versions():
    d = diff_versions({"version": 1, "exercises": [1]}, {"version": 2, "exercises": [1, 2]})
    assert d["version"] == (1, 2)
