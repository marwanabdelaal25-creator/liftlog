# liftlog

A strength-training log I built because the apps I tried either wanted a
subscription to show me my own history, or buried the one number I actually care
about — an estimated 1RM trend — under streaks and badges. I wanted a plain file
I own, that I can `grep`, and that does the arithmetic a lifter actually needs.

Everything lives in one JSON file (`library.json`) on disk. Define the lifts you
train, log sets as `weight x reps`, and liftlog estimates your 1RM, finds your
PRs, totals your volume, and tells you what to load on the bar.

```bash
pip install .
liftlog init ~/gym/library.json
liftlog exercise-add "Back Squat" --musclegroup Quadriceps --category compound \
    --best 160 --target 180 --wger 615
liftlog workset-log <exercise-id> 140 5 --rpe 8
liftlog rate <exercise-id> 5 --note "money lift"
liftlog stats
```

## What it does

- Track **exercises** with muscle group, equipment, category, an estimated 1RM
  (`best_1rm`), a goal (`target_1rm`), and a status: `learning` → `active` →
  `maintenance` → `retired` / `benched`.
- Log **sets** (`weight x reps`, optional RPE). Every set's **estimated 1RM** is
  computed and your exercise's best is bumped automatically — that's a PR.
- **Real lifting math, not a scaffold:**
  - 1RM estimates from five published formulas (Epley, Brzycki, Lombardi,
    McGlothin, Wathan) plus an average, rep-max tables, and %1RM tables
    (`liftlog.onerepmax`).
  - A barbell **plate calculator**: what to load per side for a target, warmup
    ramps, closest loadable weight (`liftlog.plates`).
  - **Wilks** and **DOTS** bodyweight-adjusted scores (`liftlog.wilks`).
- **Analytics:** total volume (tonnage), volume by muscle group / weekday /
  month, PR history per lift, estimated-1RM progression, best lifts, and a
  "what to train next" picker that surfaces the active lifts furthest from goal.
- Routines (a day's lifts), programs (training blocks), tags, coaching cues, and
  yearly goals (`sets` / `volume` / `sessions`).
- Import from **Strong**, **Hevy**, **FitNotes** (sqlite), a generic CSV, or
  enrich an exercise from **wger** by id.
- A tiny stdlib-only HTTP server so the gym tablet can read the log on the LAN.

## The math, briefly

```python
from liftlog import onerepmax, plates, wilks

onerepmax.estimate(140, 5)            # 163.3  (Epley)
onerepmax.average_1rm(140, 5)         # mean of five formulas
plates.plate_breakdown(140, bar=20)   # [25.0, 25.0, 10.0]  (per side)
plates.warmup_scheme(140)             # ramp up to your working weight
wilks.wilks_score(90, 500, "male")    # bodyweight-adjusted total
```

## What it doesn't do

- Coach you. It does the arithmetic; the programming is on you.
- Sync with Strong/Hevy live — export a CSV and import it.
- Count calories or steps. This is a barbell log, not a health platform.
- Multi-user accounts. This is my training log, not a social feed.

## Storage

One JSON document, pretty-printed, written atomically (temp file + rename, so a
crash mid-save can't shred the log). JSON over SQLite on purpose: I open the
file and fix a typo by hand more often than I'd like to admit. The schema is
versioned and migrates forward automatically — see
[`docs/architecture.md`](docs/architecture.md) and
[`docs/formats.md`](docs/formats.md).

## Importing

```bash
liftlog import strong_export.csv --format strong
liftlog import hevy_export.csv --format hevy
liftlog import ~/FitNotesBackup --format fitnotes   # reads FitNotesBackup/fitnotes.db
liftlog import exercises.csv --format csv
liftlog fetch-wger 615                               # pull a name/category from wger
```

See [`docs/recipes.md`](docs/recipes.md) for end-to-end workflows and
[`docs/faq.md`](docs/faq.md) for the questions people actually ask me.

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT licensed. Personal project, started summer 2024.
