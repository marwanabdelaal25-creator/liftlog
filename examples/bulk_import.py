#!/usr/bin/env python3
"""Import a (fake) Strong app export and print the resulting exercises."""
from __future__ import annotations

import tempfile
from pathlib import Path

from liftlog.io_strong import import_strong
from liftlog.reports import ReportBuilder
from liftlog.storage import JsonStorage

EXPORT = """\
Date,Workout Name,Exercise Name,Set Order,Weight,Reps,RPE,Notes
2025-01-06 18:00:00,Lower,Back Squat,1,140,5,8,
2025-01-06 18:00:00,Lower,Back Squat,2,145,3,9,top set
2025-01-08 18:00:00,Upper,Bench Press,1,100,5,8,
2025-01-08 18:00:00,Upper,Bench Press,2,102.5,3,9,
2025-01-10 18:00:00,Pull,Deadlift,1,200,3,9,
"""


def main() -> None:
    workdir = Path(tempfile.mkdtemp())
    export = workdir / "strong_export.csv"
    export.write_text(EXPORT, encoding="utf-8")

    store = JsonStorage(workdir / "library.json")
    store.load()
    n = import_strong(store, export)
    store.save()

    print("imported %d sets from %s" % (n, export.name))
    print()
    print(ReportBuilder(store).status_report())


if __name__ == "__main__":
    main()
