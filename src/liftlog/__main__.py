"""Allow `python -m liftlog` invocation."""

from liftlog.cli import main

__doc__ = """
Entry point for the liftlog CLI.

Examples:
  python -m liftlog init
  python -m liftlog exercise-add "Back Squat" --musclegroup Quadriceps --target 180
  python -m liftlog workset-log <exercise-id> 140 5 --rpe 8
  python -m liftlog report next
  python -m liftlog import strong_export.csv --format strong

Environment:
  LIFTLOG_HOME  Directory for the default library.json (default: ~/.liftlog/)
"""

if __name__ == "__main__":
    raise SystemExit(main())
