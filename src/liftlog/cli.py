"""Command-line interface for liftlog."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from liftlog.storage import LibraryStore
from liftlog.exercise import Exercise, LiftStatus
from liftlog.musclegroup import MuscleGroup
from liftlog.workset import WorkSet, Session
from liftlog.goals import GoalsManager, LiftGoal
from liftlog.errors import LiftlogError, NotFoundError
from liftlog.audit_log import AuditLog
from liftlog import search as search_mod
from liftlog import stats as stats_mod
from liftlog import streaks
from liftlog import reports
from liftlog import backup
from liftlog import migrate
from liftlog.tags_manager import TagsManager
from liftlog import io_csv, io_strong, io_hevy, io_jsonl, io_fitnotes, io_wger
from liftlog.server import serve

__version__ = "0.1.0"


def _store_path(ns: argparse.Namespace) -> Path | None:
    return Path(ns.data) if getattr(ns, "data", None) else None


def _load(ns: argparse.Namespace) -> LibraryStore:
    p = _store_path(ns)
    return LibraryStore.open(p)


def _save(store: LibraryStore, ns: argparse.Namespace) -> None:
    store.save()
    if getattr(ns, "verbose", False):
        print("saved -> %s" % store.path)


def cmd_init(ns: argparse.Namespace) -> int:
    store = _load(ns)
    _save(store, ns)
    print("Initialized library at %s" % store.path)
    return 0


def cmd_exercise_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    exercise = Exercise.create(
        ns.name,
        wger=ns.wger,
        status=ns.status or "active",
        category=ns.category or "compound",
        unit=ns.unit or "kg",
        best_1rm=ns.best_1rm or 0.0,
        target_1rm=ns.target_1rm,
    )
    if ns.musclegroup:
        mg = next((m for m in store.musclegroups.values() if m.name.lower() == ns.musclegroup.lower()), None)
        if mg is None:
            mg = MuscleGroup.create(ns.musclegroup)
            store.upsert_musclegroup(mg)
        exercise.musclegroup_ids = [mg.id]
    store.upsert_exercise(exercise)
    AuditLog(store._inner).log_create("exercise", exercise.id, title=exercise.name)
    _save(store, ns)
    print("Added %s (%s)" % (exercise.short_label(), exercise.id))
    return 0


def cmd_exercise_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    engine = search_mod.SearchEngine(store._inner)
    exercises = list(store.exercises.values())
    if ns.status:
        exercises = engine.filter_exercises(status=ns.status)
    if ns.query:
        hits = engine.search_exercises(ns.query)
        hit_ids = {h.id for h in hits}
        exercises = [e for e in exercises if e.id in hit_ids]
    exercises = sorted(exercises, key=lambda e: e.name.lower())
    if not exercises:
        print("No exercises found.")
        return 0
    for e in exercises[: ns.limit]:
        tgt = ("%g" % e.target_1rm) if e.target_1rm else "-"
        print(
            "{id} | {name} | {st} | {best:g}/{tgt}".format(
                id=e.id[:8], name=e.name[:40], st=e.status.value, best=e.best_1rm, tgt=tgt,
            )
        )
    return 0


def cmd_exercise_show(ns: argparse.Namespace) -> int:
    store = _load(ns)
    ex = store._inner.get_exercise(ns.id)
    print("Exercise: %s" % ex.name)
    print("Status: %s | category: %s" % (ex.status.value, ex.category))
    if ex.best_1rm:
        print("Best e1RM: %g%s" % (ex.best_1rm, ex.unit))
    if ex.target_1rm:
        print("Target: %g%s (%.0f%%)" % (ex.target_1rm, ex.unit, ex.progress_pct()))
    groups = {m.id: m.name for m in store._inner.list_musclegroups()}
    if ex.musclegroup_ids:
        print("Muscles: %s" % ", ".join(groups.get(g, g) for g in ex.musclegroup_ids))
    if ex.wger:
        print("wger: %s" % ex.wger)
    if ex.rating:
        print("Rating: %s" % ex.rating.stars_display())
    if ex.description:
        print("\n%s" % ex.description[:500])
    return 0


def cmd_exercise_rm(ns: argparse.Namespace) -> int:
    store = _load(ns)
    store._inner.delete_exercise(ns.id)
    store.load()
    AuditLog(store._inner).log_delete("exercise", ns.id)
    _save(store, ns)
    print("Removed %s" % ns.id)
    return 0


def cmd_workset_log(ns: argparse.Namespace) -> int:
    store = _load(ns)
    ex = store._inner.get_exercise(ns.exercise)
    sett = WorkSet.create(
        exercise_id=ex.id,
        weight=ns.weight,
        reps=ns.reps,
        rpe=ns.rpe,
        is_warmup=ns.warmup,
    )
    store._inner.upsert_workset(sett)
    pr = ex.update_best(sett.e1rm())
    if ex.status not in (LiftStatus.ACTIVE, LiftStatus.MAINTENANCE):
        ex.mark_active()
    store.upsert_exercise(ex)
    AuditLog(store._inner).log_create("workset", sett.id)
    _save(store, ns)
    msg = "Logged %g x %d on %s (e1RM %g)" % (sett.weight, sett.reps, ex.short_label(), sett.e1rm())
    if pr:
        msg += " — new PR!"
    print(msg)
    return 0


def cmd_rate(ns: argparse.Namespace) -> int:
    from liftlog.rating import Rating

    store = _load(ns)
    ex = store._inner.get_exercise(ns.exercise)
    ex.rating = ns.score
    store.upsert_exercise(ex)
    store._inner.add_rating(Rating.create(ex.id, value=ns.score, review=ns.note or ""))
    _save(store, ns)
    print("Rated %s: %.1f/5" % (ex.short_label(), ns.score))
    return 0


def cmd_routine_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    routines = sorted(store._inner.list_routines(), key=lambda s: s.sort_order)
    for sh in routines:
        print("%s | %s (%d)" % (sh.id[:8], sh.name, sh.count()))
    return 0


def cmd_routine_add_exercise(ns: argparse.Namespace) -> int:
    store = _load(ns)
    routines = {s.id: s for s in store._inner.list_routines()}
    sh = routines.get(ns.routine)
    if sh is None:
        sh = next((s for s in routines.values() if s.id.startswith(ns.routine)), None)
    if sh is None:
        sh = next((s for s in routines.values() if s.name.lower() == ns.routine.lower()), None)
    if sh is None:
        from liftlog.routine import Routine

        sh = Routine.create(ns.routine)
        store._inner.upsert_routine(sh)
    store._inner.get_exercise(ns.exercise)
    sh.add_exercise(ns.exercise)
    store._inner.upsert_routine(sh)
    _save(store, ns)
    print("Added to routine %s" % sh.name)
    return 0


def cmd_search(ns: argparse.Namespace) -> int:
    store = _load(ns)
    engine = search_mod.SearchEngine(store._inner)
    if ns.expr:
        exercises = engine.regex_filter(ns.expr)
    else:
        hits = engine.search_exercises(ns.query or "")
        id_map = {b.id: b for b in store.exercises.values()}
        exercises = [id_map[h.id] for h in hits if h.id in id_map]
    for e in exercises[:50]:
        print("%s — %s" % (e.id[:8], e.name))
    print("%d result(s)" % len(exercises))
    return 0


def cmd_stats(ns: argparse.Namespace) -> int:
    store = _load(ns)
    print(stats_mod.format_stats(store._inner))
    print(streaks.streak_summary(store))
    return 0


def cmd_report(ns: argparse.Namespace) -> int:
    store = _load(ns)
    rb = reports.ReportBuilder(store._inner)
    if ns.kind == "year":
        print(rb.yearly_summary(ns.year))
    elif ns.kind == "log":
        print(rb.status_report())
    elif ns.kind == "next":
        print(rb.what_to_train())
    else:
        print(rb.export_text())
    return 0


def cmd_goal_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    gm = GoalsManager(store._inner)
    g = LiftGoal.create(ns.name, ns.kind, int(ns.target), ns.period)
    gm.add_goal(g)
    _save(store, ns)
    print("Goal created: %s" % g.id)
    return 0


def cmd_goal_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    gm = GoalsManager(store._inner)
    for g in gm.refresh_all():
        print(
            "{name}: {prog}/{tgt} ({pct:.0f}%)".format(
                name=g.name, prog=g.progress, tgt=g.target, pct=g.pct_complete()
            )
        )
    return 0


def cmd_tag_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    tm = TagsManager(store._inner)
    tag = tm.create(ns.name, color=ns.color or "#6b7280")
    _save(store, ns)
    print("Tag %s (%s)" % (tag.name, tag.id))
    return 0


def cmd_tag_attach(ns: argparse.Namespace) -> int:
    store = _load(ns)
    tm = TagsManager(store._inner)
    tag = tm.find_or_create(ns.tag)
    tm.attach(ns.exercise, tag.id)
    _save(store, ns)
    return 0


def cmd_import(ns: argparse.Namespace) -> int:
    store = _load(ns)
    src = Path(ns.file)
    fmt = ns.format or src.suffix.lstrip(".").lower()
    n = 0
    if fmt == "csv":
        n = io_csv.import_csv(store, src)
    elif fmt == "strong":
        n = io_strong.import_strong(store, src)
    elif fmt == "hevy":
        n = io_hevy.import_hevy(store, src)
    elif fmt == "jsonl":
        n = io_jsonl.import_jsonl_exercises(store, src)
    elif fmt == "fitnotes":
        n = io_fitnotes.import_fitnotes(store, Path(ns.file))
    else:
        print("Unknown format: %s" % fmt, file=sys.stderr)
        return 1
    _save(store, ns)
    print("Imported %d record(s)" % n)
    return 0


def cmd_export(ns: argparse.Namespace) -> int:
    store = _load(ns)
    dest = Path(ns.file)
    fmt = ns.format or dest.suffix.lstrip(".").lower()
    if fmt == "csv":
        n = io_csv.export_csv(store, dest)
    elif fmt == "jsonl":
        n = io_jsonl.export_jsonl_exercises(store, dest)
    elif fmt == "md":
        dest.write_text(reports.ReportBuilder(store._inner).export_text(), encoding="utf-8")
        n = len(store.exercises)
    else:
        print("Unknown export format", file=sys.stderr)
        return 1
    print("Exported %d" % n)
    return 0


def cmd_wger_check(ns: argparse.Namespace) -> int:
    from liftlog.wger import validate_wger

    if validate_wger(ns.wger):
        print("valid: %s" % ns.wger)
        return 0
    print("invalid: %s" % ns.wger, file=sys.stderr)
    return 1


def cmd_fetch_wger(ns: argparse.Namespace) -> int:
    store = _load(ns)
    exercise = io_wger.exercise_from_wger(ns.wger)
    store.upsert_exercise(exercise)
    _save(store, ns)
    print("Fetched: %s" % exercise.name)
    return 0


def cmd_backup(ns: argparse.Namespace) -> int:
    store = _load(ns)
    dest = Path(ns.dir) if ns.dir else None
    out = backup.create_backup(store, dest, compress=ns.gzip)
    print("Backup -> %s" % out)
    return 0


def cmd_restore(ns: argparse.Namespace) -> int:
    store = _load(ns)
    backup.restore_backup(Path(ns.file), store.path)
    store.load()
    print("Restored from %s" % ns.file)
    return 0


def cmd_serve(ns: argparse.Namespace) -> int:
    store = _load(ns)
    serve(store._inner, host=ns.host, port=ns.port)
    return 0


def cmd_migrate(ns: argparse.Namespace) -> int:
    store = _load(ns)
    data = store.to_dict()
    if not migrate.needs_migration(data):
        print("Already at schema v%d" % data.get("version", 1))
        return 0
    new_data = migrate.migrate_data(data)
    store._inner.replace_all(new_data)
    store.load()
    _save(store, ns)
    print("Migrated to v%d" % new_data.get("version", 1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="liftlog", description="Personal strength-training log")
    p.add_argument("--data", help="Path to library.json")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Create empty library")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("exercise-add", help="Add an exercise to the catalog")
    sp.add_argument("name")
    sp.add_argument("--wger", help="wger.de exercise id")
    sp.add_argument("--musclegroup")
    sp.add_argument("--category", choices=["compound", "isolation", "olympic", "cardio", "mobility"])
    sp.add_argument("--unit", choices=["kg", "lb"])
    sp.add_argument("--best", dest="best_1rm", type=float, help="Best e1RM so far")
    sp.add_argument("--target", dest="target_1rm", type=float, help="Goal 1RM")
    sp.add_argument("--status", choices=["learning", "active", "maintenance", "retired", "benched"])
    sp.set_defaults(func=cmd_exercise_add)

    sp = sub.add_parser("exercise-list", help="List exercises")
    sp.add_argument("-q", "--query", default="")
    sp.add_argument("--status")
    sp.add_argument("--limit", type=int, default=100)
    sp.set_defaults(func=cmd_exercise_list)

    sp = sub.add_parser("exercise-show", help="Show exercise details")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_exercise_show)

    sp = sub.add_parser("exercise-rm", help="Remove a exercise")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_exercise_rm)

    sp = sub.add_parser("workset-log", help="Log a set: weight x reps")
    sp.add_argument("exercise", help="Exercise id")
    sp.add_argument("weight", type=float)
    sp.add_argument("reps", type=int)
    sp.add_argument("--rpe", type=float, help="Rate of perceived exertion 6-10")
    sp.add_argument("--warmup", action="store_true")
    sp.set_defaults(func=cmd_workset_log)

    sp = sub.add_parser("rate", help="Score a exercise 0-5")
    sp.add_argument("exercise")
    sp.add_argument("score", type=float)
    sp.add_argument("--note", help="A short review")
    sp.set_defaults(func=cmd_rate)

    sp = sub.add_parser("routine-list")
    sp.set_defaults(func=cmd_routine_list)

    sp = sub.add_parser("routine-add")
    sp.add_argument("routine")
    sp.add_argument("exercise")
    sp.set_defaults(func=cmd_routine_add_exercise)

    sp = sub.add_parser("search")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--expr", help="Advanced query")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("stats")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("report")
    sp.add_argument("kind", choices=["year", "log", "md", "next"], default="year", nargs="?")
    sp.add_argument("--year", type=int)
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("goal-add")
    sp.add_argument("name")
    sp.add_argument("--kind", default="sets", choices=["sets", "volume", "sessions"])
    sp.add_argument("--target", default="12")
    sp.add_argument("--period", default="year")
    sp.set_defaults(func=cmd_goal_add)

    sp = sub.add_parser("goal-list")
    sp.set_defaults(func=cmd_goal_list)

    sp = sub.add_parser("tag-add")
    sp.add_argument("name")
    sp.add_argument("--color", default="#6b7280")
    sp.set_defaults(func=cmd_tag_add)

    sp = sub.add_parser("tag-attach")
    sp.add_argument("exercise")
    sp.add_argument("tag")
    sp.set_defaults(func=cmd_tag_attach)

    sp = sub.add_parser("import")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "strong", "hevy", "jsonl", "fitnotes"])
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("export")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "jsonl", "md"])
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("fetch-wger")
    sp.add_argument("wger")
    sp.set_defaults(func=cmd_fetch_wger)

    sp = sub.add_parser("wger-check")
    sp.add_argument("wger")
    sp.set_defaults(func=cmd_wger_check)

    sp = sub.add_parser("backup")
    sp.add_argument("--dir")
    sp.add_argument("--gzip", action="store_true")
    sp.set_defaults(func=cmd_backup)

    sp = sub.add_parser("restore")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_restore)

    sp = sub.add_parser("serve")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("migrate")
    sp.set_defaults(func=cmd_migrate)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        return ns.func(ns)
    except LiftlogError as exc:
        print("error: %s" % exc.message, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
