# FAQ

Questions friends actually ask when I show them this.

### Why not just use Strong or Hevy?

I do, kind of — I export from them. But I wanted my training history in a file I
own, that works without signal in a basement gym, and that won't paywall the one
chart I care about. liftlog is the local copy I trust.

### How is the 1RM estimated?

From a single set (`weight x reps`) via five published formulas — Epley by
default, plus Brzycki, Lombardi, McGlothin and Wathan, and an average. See
`liftlog.onerepmax`. Logging a set whose estimate beats your current best is a
PR, and the exercise's `best_1rm` moves up automatically.

### Is it a tested 1RM or an estimate?

An estimate. It's great for programming percentages and tracking a trend; it is
not a competition single. Don't load `best_1rm` and expect to hit it cold.

### What's RPE?

Rate of perceived exertion, 6–10 — how hard the set felt (10 = no reps left in
the tank). It's optional on every set.

### Does it do plate math?

Yes — `liftlog.plates.plate_breakdown(target, bar=20)` gives the plates per side,
`warmup_scheme(working)` ramps you up, and `closest_loadable(target)` rounds to
what you can actually load.

### What about Wilks / DOTS?

`liftlog.wilks.wilks_score(bodyweight, total, sex)` and `dots_score(...)` give
the bodyweight-adjusted scores, so you can compare a 60kg and a 100kg lifter.

### Does it track cardio or bodyweight?

A bit — an exercise can be `category: cardio` or carry a `bodyweight` flag — but
this is a barbell-first log. If you want a running or step tracker, this isn't
it.

### Can I edit the JSON by hand?

Yes, that's half the point. Keep it valid JSON — the app re-reads it on the next
command, and the migrator tidies/upgrades the shape if needed.

### Will it sync to my other machine?

Put `library.json` in Dropbox/Syncthing (or set `LIFTLOG_HOME`). There's no
conflict resolution beyond "last writer wins", so don't log on two devices at
once mid-workout.

### A lift I stopped doing — delete it?

No, set it `retired` (programmed out) or `benched` (injury/deload). It stays in
your history and stats, it just won't show up in "what to train next".

### Is my data sent anywhere?

Only if you run `fetch-wger`, which calls the public wger.de API. Everything else
is local. No telemetry, no accounts.

### Why "liftlog"?

Lift + log. Also most of the good names on PyPI were taken. I'm not precious
about it.
