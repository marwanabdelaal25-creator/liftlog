# Recipes

Copy-pasteable workflows. All of these assume `liftlog init` has run and
`$LIFTLOG_HOME` points at where you keep `library.json` (defaults to
`~/.liftlog/`).

## Add a lift to the catalog

```bash
liftlog exercise-add "Back Squat" --musclegroup Quadriceps --category compound \
    --target 180 --wger 615
```

## Log your working sets

```bash
liftlog workset-log <exercise-id> 140 5 --rpe 8
liftlog workset-log <exercise-id> 60 5 --warmup
liftlog rate <exercise-id> 5 --note "money lift"
liftlog exercise-show <exercise-id>      # best / target + progress
```

Each set's estimated 1RM is computed; if it beats your best, that's a PR and the
exercise's `best_1rm` moves up.

## What should I train next?

```bash
liftlog report next     # active lifts furthest from their target 1RM
liftlog stats           # at-goal count, lifetime volume, by status
```

## Move your Strong / Hevy history in

```bash
liftlog import strong_export.csv --format strong
liftlog import hevy_export.csv   --format hevy
```

## Pull a canonical name from wger

```bash
liftlog fetch-wger 615
```

## What did I do this year?

```bash
liftlog report year --year 2025
liftlog stats
```

## Find a lift

```bash
liftlog exercise-list -q "squat"
liftlog search "deadlift"
liftlog search --expr "category:compound status:active"
```

## Bar math from Python

```python
from liftlog import plates, onerepmax
plates.plate_breakdown(142.5, bar=20)   # [25, 20, 15, 1.25] per side
onerepmax.rep_max_table(180)            # estimated weights for 1..12 reps
```

## Back up before you do something dumb

```bash
liftlog backup --dir ~/backups
```

## Grep, because you can

```bash
jq '.exercises[] | select(.best_1rm >= 150) | .name' ~/.liftlog/library.json
grep -i "squat" ~/.liftlog/library.json
```
