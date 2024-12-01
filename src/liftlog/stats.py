"""Aggregate statistics over a training log."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from liftlog.exercise import LiftStatus
from liftlog.storage import JsonStorage


@dataclass
class LibraryStats:
    total_exercises: int = 0
    by_status: Dict[str, int] = field(default_factory=dict)
    total_volume: float = 0.0
    worksets_count: int = 0
    avg_rating: Optional[float] = None
    musclegroups_count: int = 0

    def summary_lines(self) -> List[str]:
        lines = [
            "Exercises: %d" % self.total_exercises,
            "Muscle groups: %d" % self.musclegroups_count,
            "Sets logged: %d" % self.worksets_count,
        ]
        if self.avg_rating is not None:
            lines.append("Average rating: %.2f / 5" % self.avg_rating)
        lines.append("Lifetime volume: %.0f" % self.total_volume)
        return lines


def count_by_status(storage: JsonStorage) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for e in storage.list_exercises():
        c[e.status.value] += 1
    return dict(c)


def volume_in_range(storage: JsonStorage, start: date, end: date) -> float:
    tot = 0.0
    for w in storage.list_worksets():
        if start <= w.workout_date <= end:
            tot += w.volume()
    return round(tot, 2)


def total_volume(storage: JsonStorage) -> float:
    return round(sum(w.volume() for w in storage.list_worksets()), 2)


def avg_exercise_rating(storage: JsonStorage) -> Optional[float]:
    scores = [e.rating_value for e in storage.list_exercises() if e.rating_value is not None]
    if not scores:
        ratings = storage.list_ratings()
        if not ratings:
            return None
        return round(sum(r.value for r in ratings) / len(ratings), 2)
    return round(sum(scores) / len(scores), 2)


def top_tags(storage: JsonStorage, n: int = 10) -> List[tuple[str, int]]:
    tags = {t.id: t.name for t in storage.list_tags()}
    cnt: Counter[str] = Counter()
    for e in storage.list_exercises():
        for tid in e.tag_ids:
            cnt[tags.get(tid, tid)] += 1
    return cnt.most_common(n)


def training_pace(storage: JsonStorage, days: int = 30) -> Dict[str, float | int]:
    end = date.today()
    start = end - timedelta(days=days)
    vol = volume_in_range(storage, start, end)
    sets = sum(1 for w in storage.list_worksets() if start <= w.workout_date <= end)
    return {
        "volume": vol,
        "sets": sets,
        "volume_per_day": round(vol / max(days, 1), 1),
        "window_days": days,
    }


def compute_stats(storage: JsonStorage) -> LibraryStats:
    exercises = storage.list_exercises()
    worksets = storage.list_worksets()
    return LibraryStats(
        total_exercises=len(exercises),
        by_status=count_by_status(storage),
        total_volume=round(sum(w.volume() for w in worksets), 2),
        worksets_count=len(worksets),
        avg_rating=avg_exercise_rating(storage),
        musclegroups_count=len(storage.list_musclegroups()),
    )


def format_stats(storage: JsonStorage) -> str:
    st = compute_stats(storage)
    pace = training_pace(storage)
    parts = ["Training stats", "  Total exercises: %d" % st.total_exercises]
    parts.append("  By status: %s" % st.by_status)
    if st.avg_rating is not None:
        parts.append("  Avg rating: %.2f" % st.avg_rating)
    parts.append("  At goal: %d" % at_goal_count(storage))
    parts.append("  Lifetime volume: %.0f" % st.total_volume)
    parts.append("  Last 30d volume: %.0f" % pace["volume"])
    return "\n".join(parts)


def at_goal_count(storage: JsonStorage) -> int:
    return sum(1 for e in storage.list_exercises() if e.at_goal())


def category_distribution(storage: JsonStorage) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for e in storage.list_exercises():
        if e.category:
            c[e.category] += 1
    return dict(c)


def musclegroup_distribution(storage: JsonStorage) -> Dict[str, int]:
    names = {m.id: m.name for m in storage.list_musclegroups()}
    c: Counter[str] = Counter()
    for e in storage.list_exercises():
        for mid in e.musclegroup_ids:
            c[names.get(mid, mid)] += 1
    return dict(c)


def top_musclegroups(storage: JsonStorage, n: int = 5) -> List[tuple[str, int]]:
    return Counter(musclegroup_distribution(storage)).most_common(n)


def volume_by_musclegroup(storage: JsonStorage) -> Dict[str, float]:
    names = {m.id: m.name for m in storage.list_musclegroups()}
    ex_groups = {e.id: e.musclegroup_ids for e in storage.list_exercises()}
    out: Dict[str, float] = {}
    for w in storage.list_worksets():
        for mid in ex_groups.get(w.exercise_id, []):
            key = names.get(mid, mid)
            out[key] = round(out.get(key, 0.0) + w.volume(), 2)
    return out


def best_lifts(storage: JsonStorage, n: int = 5) -> List[tuple[str, float]]:
    rows = [(e.name, e.best_1rm) for e in storage.list_exercises() if e.best_1rm]
    rows.sort(key=lambda kv: kv[1], reverse=True)
    return rows[:n]


def exercise_1rm_history(storage: JsonStorage, exercise_id: str) -> List[tuple[str, float]]:
    """Estimated 1RM per day for one exercise (best working set each day)."""
    by_day: Dict[date, float] = {}
    for w in storage.list_worksets():
        if w.exercise_id != exercise_id or not w.is_working():
            continue
        d = w.workout_date
        by_day[d] = max(by_day.get(d, 0.0), w.e1rm())
    return [(d.isoformat(), round(v, 1)) for d, v in sorted(by_day.items())]


def detect_prs(storage: JsonStorage, exercise_id: str) -> List[Dict[str, Any]]:
    """Walk an exercise's sets in time order, flagging each new e1RM best."""
    sets = sorted(
        (w for w in storage.list_worksets() if w.exercise_id == exercise_id and w.is_working()),
        key=lambda w: w.started_at,
    )
    prs: List[Dict[str, Any]] = []
    best = 0.0
    for w in sets:
        est = w.e1rm()
        if est > best:
            best = est
            prs.append({"date": w.workout_date.isoformat(), "weight": w.weight,
                        "reps": w.reps, "e1rm": round(est, 1)})
    return prs


def pr_count(storage: JsonStorage) -> int:
    return sum(len(detect_prs(storage, e.id)) for e in storage.list_exercises())


def format_breakdown(storage: JsonStorage) -> str:
    st = compute_stats(storage)
    pace = training_pace(storage, 30)
    lines = ["=== Detailed stats ===", ""]
    lines.extend(st.summary_lines())
    lines.append("")
    lines.append("At goal: %d" % at_goal_count(storage))
    lines.append("30-day volume: %.0f over %d sets" % (pace["volume"], pace["sets"]))
    cats = category_distribution(storage)
    if cats:
        lines.append("")
        lines.append("By category:")
        for k in sorted(cats):
            lines.append("  %s: %d" % (k, cats[k]))
    groups = top_musclegroups(storage, 8)
    if groups:
        lines.append("")
        lines.append("Top muscle groups:")
        for name, cnt in groups:
            lines.append("  %s (%d)" % (name, cnt))
    lifts = best_lifts(storage, 5)
    if lifts:
        lines.append("")
        lines.append("Best lifts:")
        for name, est in lifts:
            lines.append("  %s: %g" % (name, est))
    return "\n".join(lines)


def monthly_volume(storage: JsonStorage, year: int, month: int) -> float:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return volume_in_range(storage, start, end)


def status_percentages(storage: JsonStorage) -> Dict[str, float]:
    counts = count_by_status(storage)
    total = sum(counts.values()) or 1
    return {k: round(100.0 * v / total, 1) for k, v in counts.items()}


def average_best_1rm(storage: JsonStorage) -> Optional[float]:
    bests = [e.best_1rm for e in storage.list_exercises() if e.best_1rm]
    if not bests:
        return None
    return round(sum(bests) / len(bests), 1)


def volume_by_weekday(storage: JsonStorage) -> Dict[int, float]:
    vol: Dict[int, float] = {i: 0.0 for i in range(7)}
    for w in storage.list_worksets():
        vol[w.workout_date.weekday()] += w.volume()
    return {k: round(v, 1) for k, v in vol.items()}


def at_goal_rate(storage: JsonStorage) -> float:
    targeted = [e for e in storage.list_exercises() if e.target_1rm]
    if not targeted:
        return 0.0
    return round(100.0 * sum(1 for e in targeted if e.at_goal()) / len(targeted), 1)


def benched_rate(storage: JsonStorage) -> float:
    exercises = storage.list_exercises()
    if not exercises:
        return 0.0
    benched = sum(1 for e in exercises if e.status == LiftStatus.BENCHED)
    return round(100.0 * benched / len(exercises), 1)


def average_rpe(storage: JsonStorage) -> Optional[float]:
    rpes = [w.rpe for w in storage.list_worksets() if w.rpe is not None]
    if not rpes:
        return None
    return round(sum(rpes) / len(rpes), 1)


def volume_by_month(storage: JsonStorage, year: int) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for m in range(1, 13):
        v = monthly_volume(storage, year, m)
        if v:
            out[m] = v
    return out


def rating_distribution(storage: JsonStorage) -> Dict[int, int]:
    from liftlog.rating import histogram

    return histogram(storage.list_ratings())


def format_leaderboard(storage: JsonStorage, n: int = 5) -> str:
    lifts = best_lifts(storage, n)
    if not lifts:
        return "No logged lifts yet."
    lines = ["Strongest lifts:"]
    for name, est in lifts:
        lines.append("  %g — %s" % (est, name))
    return "\n".join(lines)


def training_velocity(storage: JsonStorage, weeks: int = 4) -> float:
    pace = training_pace(storage, weeks * 7)
    return float(pace["volume_per_day"])


class StatsReporter:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def full_report(self) -> str:
        return format_breakdown(self.storage)

    def quick(self) -> str:
        return format_stats(self.storage)

    def entity_counts(self) -> Dict[str, int]:
        return self.storage.count_entities()

    def weekday_chart(self) -> str:
        vol = volume_by_weekday(self.storage)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        lines = ["Volume by weekday:"]
        mx = max(vol.values()) or 1
        for i, lbl in enumerate(days):
            bar = "#" * int(20 * vol[i] / mx)
            lines.append("  %s %8.0f %s" % (lbl, vol[i], bar))
        return "\n".join(lines)

    def monthly_table(self, year: int) -> str:
        lines = ["Volume by month (%d)" % year]
        for m in range(1, 13):
            v = monthly_volume(self.storage, year, m)
            if v:
                lines.append("  %02d: %8.0f" % (m, v))
        return "\n".join(lines)

    def musclegroup_chart(self) -> str:
        dist = musclegroup_distribution(self.storage)
        if not dist:
            return "No muscle groups on file yet."
        lines = ["Exercises by muscle group:"]
        for name, cnt in sorted(dist.items(), key=lambda kv: -kv[1]):
            lines.append("  %-18s %d" % (name[:18], cnt))
        return "\n".join(lines)

    def best_lifts_table(self) -> str:
        lifts = best_lifts(self.storage, 10)
        if not lifts:
            return "No lifts logged yet."
        return "\n".join("  %-24s %g" % (n[:24], v) for n, v in lifts)

    def export_json_summary(self) -> Dict[str, Any]:
        st = compute_stats(self.storage)
        return {
            "total_exercises": st.total_exercises,
            "by_status": st.by_status,
            "avg_rating": st.avg_rating,
            "total_volume": st.total_volume,
            "at_goal": at_goal_count(self.storage),
            "at_goal_rate": at_goal_rate(self.storage),
            "pace_30d": training_pace(self.storage, 30),
        }


def exercises_trained_in_year(storage: JsonStorage, year: int) -> int:
    days = {w.workout_date for w in storage.list_worksets() if w.workout_date.year == year}
    return len(days)


def compare_years(storage: JsonStorage, y1: int, y2: int) -> str:
    v1 = volume_in_range(storage, date(y1, 1, 1), date(y1, 12, 31))
    v2 = volume_in_range(storage, date(y2, 1, 1), date(y2, 12, 31))
    return "Volume %d (%.0f) vs %d (%.0f)" % (y1, v1, y2, v2)
