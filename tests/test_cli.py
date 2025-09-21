"""Tests for liftlog.cli."""

import pytest

from liftlog.cli import build_parser, main


def test_build_parser_has_init():
    p = build_parser()
    assert "init" in p._subparsers._group_actions[0].choices


def test_main_help():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_init_creates_library(tmp_path):
    db = tmp_path / "lib.json"
    assert main(["--data", str(db), "init"]) == 0
    assert db.exists()


def test_exercise_add_and_list(tmp_path):
    db = tmp_path / "lib.json"
    main(["--data", str(db), "init"])
    rc = main(["--data", str(db), "exercise-add", "Snow Crash", "--status", "learning"])
    assert rc == 0
    assert main(["--data", str(db), "exercise-list"]) == 0


def test_stats_empty_library(tmp_path):
    db = tmp_path / "lib.json"
    main(["--data", str(db), "init"])
    assert main(["--data", str(db), "stats"]) == 0


def test_wger_check_valid():
    assert main(["wger-check", "615"]) == 0


def test_wger_check_invalid():
    assert main(["wger-check", "not-an-id"]) == 1
