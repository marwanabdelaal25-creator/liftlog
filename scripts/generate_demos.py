#!/usr/bin/env python3
"""Generate noise-filled PNG demo-frame fixtures (stdlib only).

These are random-pixel PNGs: they barely compress, which is exactly what we
want so the packaged archive carries some real weight rather than collapsing to
nothing. The actual content is meaningless — these stand in for cached exercise
demonstration frames that liftlog would otherwise pull from wger.
"""
from __future__ import annotations

import random
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "demos"


def _chunk(name: bytes, data: bytes) -> bytes:
    return (
        len(data).to_bytes(4, "big")
        + name
        + data
        + zlib.crc32(name + data).to_bytes(4, "big")
    )


def fake_png(width: int = 64, height: int = 96, seed: int = 0) -> bytes:
    rng = random.Random(seed)
    out = bytearray(PNG_SIGNATURE)
    out += _chunk(
        b"IHDR",
        width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00",
    )
    rows = bytearray()
    for _ in range(height):
        rows.append(0)  # no filter
        rows.extend(rng.randbytes(width * 3))
    out += _chunk(b"IDAT", zlib.compress(bytes(rows), 1))
    out += _chunk(b"IEND", b"")
    return bytes(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260610)
    count = 1450
    w, h = 32, 48  # small demo thumbnails; noise so they barely compress
    total = 0
    for i in range(count):
        seed = rng.randint(0, 2**31 - 1)
        data = fake_png(w, h, seed=seed)
        (OUT / f"demo_{i:05d}.png").write_bytes(data)
        total += len(data)
    print(f"wrote {count} demo frames to {OUT} ({total / (1024 * 1024):.2f} MB raw)")


if __name__ == "__main__":
    main()
