"""Liftlog — a personal strength-training log by Marwan Helmy."""

from __future__ import annotations

__version__ = "1.2.0"
__author__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"

from liftlog.errors import (
    LiftlogError,
    StorageError,
    ValidationError,
    NotFoundError,
    ImportError,
    ExportError,
    MigrationError,
    PluginError,
    ConflictError,
    format_error,
)
from liftlog.storage import JsonStorage, LibraryStore, open_storage, LibraryFacade, SCHEMA_VERSION
from liftlog.exercise import Exercise, LiftStatus, ExerciseCatalog
from liftlog.musclegroup import MuscleGroup, MuscleGroupManager
from liftlog.routine import Routine, RoutineManager
from liftlog.workset import WorkSet, Session
from liftlog.rating import Rating, RatingsManager
from liftlog.tag import Tag
from liftlog.goals import LiftGoal, Goal, GoalsManager
from liftlog.collections import Collection, CollectionsManager
from liftlog.quotes import Quote, QuotesManager
from liftlog.notes import Note, NotesManager
from liftlog.program import Program, ProgramManager
from liftlog.equipment import Equipment, EquipmentManager
from liftlog.recurring import RecurringRule, RecurringScheduler
from liftlog.search import SearchEngine
from liftlog.stats import compute_stats, LibraryStats, StatsReporter
from liftlog.streaks import compute_streak, StreakInfo
from liftlog.reports import ReportBuilder
from liftlog.tags_manager import TagsManager
from liftlog.audit_log import AuditLog
from liftlog.plugins import PluginManager
from liftlog.migrate import migrate_data, needs_migration, MigrationRunner
from liftlog.backup import create_backup, restore_backup
from liftlog import onerepmax, plates, wilks

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "LiftlogError",
    "StorageError",
    "ValidationError",
    "NotFoundError",
    "ImportError",
    "ExportError",
    "MigrationError",
    "PluginError",
    "ConflictError",
    "format_error",
    "JsonStorage",
    "LibraryStore",
    "LibraryFacade",
    "open_storage",
    "SCHEMA_VERSION",
    "Exercise",
    "LiftStatus",
    "ExerciseCatalog",
    "MuscleGroup",
    "MuscleGroupManager",
    "Routine",
    "RoutineManager",
    "WorkSet",
    "Session",
    "Rating",
    "RatingsManager",
    "Tag",
    "LiftGoal",
    "Goal",
    "GoalsManager",
    "Collection",
    "CollectionsManager",
    "Quote",
    "QuotesManager",
    "Note",
    "NotesManager",
    "Program",
    "ProgramManager",
    "Equipment",
    "EquipmentManager",
    "RecurringRule",
    "RecurringScheduler",
    "SearchEngine",
    "compute_stats",
    "LibraryStats",
    "StatsReporter",
    "compute_streak",
    "StreakInfo",
    "ReportBuilder",
    "TagsManager",
    "AuditLog",
    "PluginManager",
    "migrate_data",
    "needs_migration",
    "MigrationRunner",
    "create_backup",
    "restore_backup",
    "onerepmax",
    "plates",
    "wilks",
]
