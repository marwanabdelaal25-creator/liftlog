# Formats

## The library file

One JSON object, schema `version: 2`. The top-level keys are collections:

```json
{
  "version": 2,
  "exercises": [ ... ],
  "musclegroups": [ ... ],
  "worksets": [ ... ],
  "routines": [ ... ],
  "programs": [ ... ],
  "equipment": [ ... ],
  "tags": [ ... ],
  "ratings": [ ... ],
  "quotes": [ ... ],
  "notes": [ ... ],
  "goals": [ ... ],
  "collections": [ ... ],
  "recurring": [],
  "audit": [],
  "plugins": {},
  "meta": { "owner": "Marwan Helmy" }
}
```

### An exercise record

```json
{
  "id": "ex-7c1a2b3c4d5e",
  "name": "Back Squat",
  "musclegroup_ids": ["mg-00"],
  "wger": "615",
  "equipment_id": null,
  "program_id": null,
  "program_index": null,
  "category": "compound",
  "target_1rm": 180.0,
  "best_1rm": 162.5,
  "unit": "kg",
  "bodyweight": false,
  "status": "active",
  "started_at": "2024-09-01",
  "finished_at": null,
  "added_at": null,
  "tag_ids": ["tag-main"],
  "routine_ids": [],
  "demo_url": "",
  "rating": 5.0
}
```

- `best_1rm` is the best estimated 1RM from your logged sets; `target_1rm` is the
  goal. `progress_pct` is `best / target`.
- `wger` is a wger.de exercise id (1-6 digits); used to pull a canonical name.
- `category` is `compound` / `isolation` / `olympic` / `cardio` / `mobility`.
- `unit` is `kg` or `lb`.
- `status` is `learning` → `active` → `maintenance` → `retired` / `benched`.

### A workset record

```json
{
  "id": "…",
  "exercise_id": "ex-…",
  "started_at": "2025-03-15T18:00:00",
  "weight": 140.0,
  "reps": 5,
  "rpe": 8.0,
  "is_warmup": false,
  "unit": "kg",
  "notes": "felt strong"
}
```

`volume()` is `weight x reps`; `e1rm()` is the estimated 1RM (Epley by default).
Logging a set whose `e1rm` beats the exercise's `best_1rm` is a PR.

## Import formats

| `--format`  | Source                  | Shape |
|-------------|-------------------------|-------|
| `strong`    | Strong app export       | CSV: `Date,Workout Name,Exercise Name,Set Order,Weight,Reps,RPE,Notes` |
| `hevy`      | Hevy app export         | CSV: `title,start_time,exercise_title,set_index,weight_kg,reps,rpe` |
| `csv`       | liftlog's own export    | CSV: `name,musclegroup,wger,equipment,category,best_1rm,target_1rm,unit,status,rating,tags` |
| `fitnotes`  | FitNotes sqlite backup  | reads `fitnotes.db` (`training_log` table) |

The Strong, Hevy and FitNotes importers create one `WorkSet` per row, creating
the `Exercise` on first sight and bumping its `best_1rm` whenever a set's
estimated 1RM beats it.

## wger lookup

`liftlog fetch-wger 615` hits the public wger.de API (no key needed), resolves
the id to an exercise, and pulls the canonical name, category, equipment and
primary muscles.
