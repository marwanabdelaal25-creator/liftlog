#!/usr/bin/env python3
"""Generate coaching-cue / quote data for liftlog tests."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "quotes"

# (lift slug, the lift, a coaching theme)
LIFTS = [
    ("back-squat", "Back Squat", "bracing"),
    ("bench-press", "Bench Press", "leg drive"),
    ("deadlift", "Deadlift", "lat tension"),
    ("overhead-press", "Overhead Press", "glute squeeze"),
    ("barbell-row", "Barbell Row", "scapular control"),
    ("pull-up", "Pull-up", "full hang"),
    ("front-squat", "Front Squat", "elbow height"),
    ("romanian-deadlift", "Romanian Deadlift", "hip hinge"),
]
CUES = [
    "Big breath, brace like you're about to be punched",
    "Spread the floor with your feet",
    "Pull the slack out of the bar before you pull",
    "Squeeze the bar like you're trying to bend it",
    "Drive your head through the window",
    "Keep the bar over mid-foot",
    "Chest up, leave your ego at the door",
    "Control the eccentric, own the bottom",
    "Glutes hard at lockout, don't hyperextend",
    "Same bar speed every rep until it's not",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(5151)
    corpus = []
    for slug, lift, theme in LIFTS:
        for block in ("hypertrophy", "strength", "peaking"):
            for i in range(rng.randint(120, 200)):
                corpus.append({
                    "exercise_id": slug,
                    "lift": lift,
                    "theme": theme,
                    "block": block,
                    "quote_id": f"{slug}-{block}-{i:04d}",
                    "text": rng.choice(CUES),
                    "rpe_target": rng.choice([7, 8, 8.5, 9]),
                    "tags": rng.sample(["cue", "setup", "bracing", "tempo", "lockout"], rng.randint(0, 3)),
                })

    by_year = {}
    for y in range(2018, 2026):
        by_year[str(y)] = {
            "cues_added": rng.randint(40, 400),
            "top_lifts": [w[0] for w in rng.sample(LIFTS, k=4)],
            "sample": [rng.choice(CUES) for _ in range(rng.randint(30, 60))],
        }

    master = {"schema": 1, "cues": corpus, "by_year": by_year, "cross_refs": []}
    for i, q in enumerate(corpus[::17]):
        master["cross_refs"].append(
            {"from": q["quote_id"], "to": corpus[(i * 31) % len(corpus)]["quote_id"], "relation": "same-block"}
        )

    (OUT / "quotes_master.json").write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    shard_size = 2500
    for idx in range(0, len(corpus), shard_size):
        (OUT / f"quotes_shard_{idx // shard_size:03d}.json").write_text(
            json.dumps(corpus[idx: idx + shard_size], indent=2, ensure_ascii=False), encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.glob("*.json"))
    print(f"cue dump: {len(corpus)} cues, {total / (1024 * 1024):.2f} MB -> {OUT}")


if __name__ == "__main__":
    main()
