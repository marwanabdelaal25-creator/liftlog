#!/usr/bin/env python3
"""Package liftlog for submission — includes .git/, skips __pycache__."""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

PROJECT = "liftlog"
SKIP_DIRS = {"__pycache__", ".pytest_cache", "htmlcov", ".ruff_cache", "build", "dist", ".history_snapshot"}
SKIP_FILES = {".coverage"}
SKIP_SUFFIXES = (".pyc",)


def package(project_dir: Path, output: Path | None = None) -> Path:
    output = output or project_dir.parent / f"{PROJECT}.zip"
    project_dir = project_dir.resolve()

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.endswith(".egg-info")
            ]
            for fname in files:
                if fname in SKIP_FILES or fname.endswith(SKIP_SUFFIXES):
                    continue
                full = Path(root) / fname
                rel = full.relative_to(project_dir.parent)
                zf.write(full, rel.as_posix())

    return output


def verify(output: Path) -> None:
    prefix = f"{PROJECT}/"
    with zipfile.ZipFile(output) as zf:
        ents = zf.namelist()
        joined = "\n".join(ents)
        packed = ""
        if f"{prefix}.git/packed-refs" in ents:
            packed = zf.read(f"{prefix}.git/packed-refs").decode("utf-8", "ignore")
    # main ref may be loose or packed after gc — accept either
    main_ok = (f"{prefix}.git/refs/heads/main" in ents) or ("refs/heads/main" in packed)
    if not main_ok:
        print("VERIFY FAIL: main ref missing", file=sys.stderr)
        sys.exit(1)
    checks = [
        (f"{prefix}.git/", "any .git entry"),
        (f"{prefix}tests/", "tests/"),
        (f"{prefix}.git/HEAD", "HEAD"),
        (f"{prefix}Dockerfile", "Dockerfile"),
        (f"{prefix}README.md", "README"),
        (f"{prefix}tests/conftest.py", "conftest"),
    ]
    for needle, label in checks:
        ok = (needle in joined) if needle.endswith("/") else (needle in ents)
        if not ok:
            print(f"VERIFY FAIL: {label} missing", file=sys.stderr)
            sys.exit(1)
    size_mb = output.stat().st_size / 1_048_576
    print(f"OK: {len(ents)} entries, {size_mb:.2f} MB compressed")
    if size_mb < 10:
        print("WARNING: compressed size below 10 MB floor", file=sys.stderr)
    elif size_mb > 30:
        print("WARNING: compressed size above 30 MB soft ceiling", file=sys.stderr)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = package(root)
    print(f"Wrote {out}")
    verify(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
