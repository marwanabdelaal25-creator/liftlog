"""Text reports for terminal output."""

from __future__ import annotations

from datetime import date
from typing import Optional

from liftlog.exercise import LiftStatus
from liftlog.goals import GoalsManager
from liftlog.stats import compute_stats, volume_in_range, exercises_trained_in_year, best_lifts
from liftlog.streaks import compute_streak
from liftlog.storage import JsonStorage
from liftlog.quotes import QuotesManager
from liftlog.notes import NotesManager
from liftlog.program import ProgramManager
from liftlog.equipment import EquipmentManager


def _bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


class ReportBuilder:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self.goals = GoalsManager(storage)
        self.quotes = QuotesManager(storage)
        self.notes = NotesManager(storage)
        self.program = ProgramManager(storage)
        self.equipment = EquipmentManager(storage)

    def overview(self) -> str:
        st = compute_stats(self.storage)
        streak = compute_streak(self.storage)
        lines = ["=== Liftlog Training Overview ===", ""]
        lines.extend(st.summary_lines())
        lines.append("")
        lines.append("By status:")
        for k, v in sorted(st.by_status.items()):
            lines.append("  {0}: {1}".format(k, v))
        lines.append("")
        lines.append(streak.as_text())
        return "\n".join(lines)

    def status_report(self, status: Optional[str] = None) -> str:
        exercises = self.storage.list_exercises()
        if status:
            exercises = [e for e in exercises if e.status.value == status]
        exercises.sort(key=lambda e: e.name.lower())
        if not exercises:
            return "No exercises match."
        lines = ["Exercise | Status | Best / Target", "-" * 48]
        for e in exercises:
            tgt = ("%g" % e.target_1rm) if e.target_1rm else "-"
            lines.append("{name:<28} | {st:11} | {best:g} / {tgt}".format(
                name=e.name[:28], st=e.status.value, best=e.best_1rm, tgt=tgt,
            ))
        return "\n".join(lines)

    def goals_report(self) -> str:
        goals = self.goals.refresh_all()
        if not goals:
            return "No goals defined. Set one with `liftlog goal-add`."
        lines = ["=== Goals ==="]
        for g in goals:
            pct = g.pct_complete()
            lines.append(
                "{name}: {prog}/{target} {typ} ({pct:.0f}%) {bar}".format(
                    name=g.name, prog=g.progress, target=g.target,
                    typ=g.goal_type, pct=pct, bar=_bar(pct),
                )
            )
        return "\n".join(lines)

    def yearly_summary(self, year: Optional[int] = None) -> str:
        yr = year or date.today().year
        vol = volume_in_range(self.storage, date(yr, 1, 1), date(yr, 12, 31))
        sessions = exercises_trained_in_year(self.storage, yr)
        lines = [
            "Year %d summary" % yr,
            "Training days: %d" % sessions,
            "Total volume: %.0f" % vol,
        ]
        lifts = best_lifts(self.storage, 5)
        if lifts:
            lines.append("")
            lines.append("Best lifts:")
            for name, est in lifts:
                lines.append("  • %s — %g" % (name, est))
        return "\n".join(lines)

    def recent_worksets(self, limit: int = 20) -> str:
        worksets = sorted(
            self.storage.list_worksets(),
            key=lambda s: s.started_at,
            reverse=True,
        )
        by_id = {e.id: e for e in self.storage.list_exercises()}
        lines = ["Recent sets", "-" * 30]
        for s in worksets[:limit]:
            ex = by_id.get(s.exercise_id)
            name = ex.short_label() if ex else s.exercise_id[:8]
            rpe = (" @RPE %g" % s.rpe) if s.rpe is not None else ""
            lines.append(
                "{date} | {name} | {w:g}x{r}{rpe}".format(
                    date=s.started_at[:10], name=name[:26], w=s.weight, r=s.reps, rpe=rpe,
                )
            )
        return "\n".join(lines)

    def what_to_train(self, n: int = 5) -> str:
        """Active lifts furthest from their goal — where the work is."""
        candidates = [
            e for e in self.storage.list_exercises()
            if e.status == LiftStatus.ACTIVE and e.target_1rm and not e.at_goal()
        ]
        if not candidates:
            return "No active lifts are chasing a target right now."
        candidates.sort(key=lambda e: e.gap_to_target() or 0, reverse=True)
        lines = ["Focus next — biggest gap to goal:"]
        for e in candidates[:n]:
            lines.append("  %s — %g / %g (%+g to go)" % (
                e.short_label(), e.best_1rm, e.target_1rm, e.gap_to_target()))
        return "\n".join(lines)

    def quotes_digest(self) -> str:
        return self.quotes.export_text()

    def notes_digest(self, exercise_id: Optional[str] = None) -> str:
        if exercise_id:
            return self.notes.export_markdown(exercise_id)
        lines = ["=== Notes across the log ==="]
        for n in self.storage.list_notes()[:50]:
            lines.append("- %s: %s" % (n.title or n.id[:8], n.excerpt(60)))
        return "\n".join(lines)

    def program_report(self) -> str:
        return self.program.progress_report()

    def equipment_report(self) -> str:
        return self.equipment.summary()

    def export_text(self) -> str:
        chunks = [self.overview(), "", self.goals_report(), "", self.program_report()]
        return "\n".join(chunks)

    def export_markdown(self) -> str:
        chunks = ["# My Training Log\n", "_Generated by liftlog_\n"]
        for e in sorted(self.storage.list_exercises(), key=lambda e: e.name.lower()):
            chunks.append("## %s\n" % e.short_label())
            chunks.append("- Status: %s\n" % e.status.value)
            if e.category:
                chunks.append("- Category: %s\n" % e.category)
            if e.best_1rm:
                chunks.append("- Best e1RM: %g%s\n" % (e.best_1rm, e.unit))
            if e.target_1rm:
                chunks.append("- Target: %g%s\n" % (e.target_1rm, e.unit))
            if e.rating_value is not None:
                chunks.append("- Rating: %s/5\n" % e.rating_value)
            chunks.append("\n")
        return "".join(chunks)

    def compare_years(self, y1: int, y2: int) -> str:
        from liftlog.stats import compare_years

        return compare_years(self.storage, y1, y2)

    def full_digest(self) -> str:
        parts = [
            self.overview(), "", self.goals_report(), "", self.program_report(),
            "", self.equipment_report(), "", self.recent_worksets(15),
        ]
        return "\n".join(parts)
