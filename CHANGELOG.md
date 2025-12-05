# Changelog

All notable changes to liftlog. Dates are when I actually cut the tag, not when
I meant to.

## 1.2.0
- Training streaks + per-weekday volume, and volume by muscle group.
- `program` progress reports (the next lift to push in a block).
- "What to train next" — active lifts sorted by the gap to their target 1RM.
- Schema bumped to v2 (see Migrations).

## 1.0.0
- First version I'd call usable. Stable JSON schema, CSV import/export, the
  Strong and Hevy importers, ratings with reviews, and the stats page.

## 0.8.0
- wger lookup by exercise id (`fetch-wger`).
- FitNotes sqlite import.
- Coaching cues attached to lifts.

## 0.6.0
- Routines and tags.
- Yearly goals (sets / volume / sessions) + the goals manager.

## 0.5.0
- The plate calculator and Wilks/DOTS scores.

## 0.4.0
- Sets (per-set logging), estimated-1RM history, and the reports builder.

## 0.3.0
- Schema v1: split the flat exercise blob into exercises + muscle groups + sets.

## 0.2.0
- The 1RM estimators (Epley/Brzycki/Lombardi/McGlothin/Wathan) and rep-max tables.

## 0.1.0
- First commit. An `Exercise` dataclass, a JSON store, and `exercise-add`.

## Migrations

The on-disk schema version lives in the top-level `version` key. liftlog
migrates forward automatically on load; there is no downgrade.

- **0 → 1**: legacy status strings (`current`/`programmed` → `active`,
  `dropped` → `retired`, `injured` → `benched`) normalised; introduced the
  `musclegroups`, `programs` and `worksets` collections.
- **1 → 2**: ratings normalised to a single float (older builds stored a nested
  `{value, score}` object); legacy `max` / `goal` promoted to `best_1rm` /
  `target_1rm`.
