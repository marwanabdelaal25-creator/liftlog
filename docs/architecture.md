# Architecture

A tour of how liftlog is put together and why. Nothing here is clever; it's a
CLI over a JSON file. The goal was "easy to reason about at midnight", not
"scales to a million users".

## The shape of it

```
cli ──> storage (JsonStorage) ──> library.json
 │            │
 │            ├── migrate          (schema v0 → v1 → v2 on load)
 │            └── models           (Exercise, MuscleGroup, WorkSet, ...)
 │
 ├── onerepmax / plates / wilks                   (the lifting math)
 ├── search / stats / reports / streaks / goals   (read the store, compute things)
 ├── io_* codecs                                  (import / export)
 └── server                                       (read-only HTTP, stdlib only)
```

## Module map

**Core models** — plain dataclasses, no storage dependency:

- `exercise` — the `Exercise` entity + `LiftStatus` + an `ExerciseCatalog` query
  helper. This is where the goal-progress logic lives (`progress_pct`,
  `update_best`, `gap_to_target`, `at_goal`).
- `musclegroup`, `equipment`, `program`, `routine` — the things exercises hang off.
- `workset` — one logged set: `weight x reps` and an optional RPE. Knows its own
  `volume()` and estimated 1RM (`e1rm()`).
- `rating`, `quotes`, `note`, `tag`, `collections`, `goals` — the trimmings.

**The lifting math** — pure functions, no storage:

- `onerepmax` — five 1RM formulas (Epley/Brzycki/Lombardi/McGlothin/Wathan),
  their average, rep-max and %1RM tables, training max.
- `plates` — barbell loading (plates per side), warmup ramps, closest loadable.
- `wilks` — Wilks and DOTS bodyweight-adjusted scores.

**Storage**

- `storage` — `JsonStorage`: load/save (atomic temp-file + rename), per-entity
  CRUD, and a small `LibraryFacade` for scripts.
- `migrate` — forward-only schema migrations keyed off the `version` field.

**Parsing & validation**

- `parser` — dates, durations, key=value pairs, sort specs.
- `validators` — field-level checks shared across the model layer.
- `wger` — wger exercise-id parsing/validation (1-6 digit ids).

**Business logic**

- `search` — fuzzy-ish search across exercises, muscle groups, notes and quotes.
- `stats` — total volume, volume by muscle group / weekday / month, PR
  detection, estimated-1RM progression, best lifts, at-goal rate.
- `reports` — the human-readable text views the CLI prints, including the
  "what to train next" picker.
- `streaks`, `goals`, `recurring` — habit-tracking bits.
- `audit_log`, `backup`, `plugins` — operational odds and ends.

**I/O codecs** — each import source in its own module:

- `io_csv`, `io_jsonl` — the generic in/out formats.
- `io_strong`, `io_hevy`, `io_fitnotes`, `io_wger` — app-specific imports.

**Surface**

- `cli` — argparse subcommands wiring everything together.
- `server` — a stdlib `http.server` handler for LAN browsing.

## Why JSON, not SQLite

I went back and forth. SQLite would give me indexes and real queries for free.
But:

- I open `library.json` in an editor more often than I'd like to admit, to fix a
  muscle group's name or paste in a target I looked up. You can't do that with a
  binary `.db` without a tool.
- `grep` and `jq` are my query engine. "Which lifts did I PR in March?" is a
  one-liner against text.
- The whole log is a few MB even after years. Loading it all into memory is
  fine; I'm not a gym chain.

The cost is that every write rewrites the file. I make that safe with an atomic
write (temp file + `os.replace`) so a crash can't leave a half-written log.

## Things I'd do differently

- `best_1rm` is an *estimated* max from your logged sets (via Epley by default),
  not a tested single. It's good enough for programming percentages; don't take
  it to a meet.
- The plugin registry is more scaffolding than feature — I've written exactly
  one plugin and it lives in my dotfiles.
