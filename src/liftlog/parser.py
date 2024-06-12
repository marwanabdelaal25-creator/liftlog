"""Parse user-facing strings into structured values."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

DURATION_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m(?:in)?)?$", re.I)
DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d")


def parse_duration(text: str) -> int:
    """Return seconds from strings like '1h30m', '45min', or '30' (minutes)."""
    text = text.strip().replace(" ", "")
    if text.isdigit():
        return int(text) * 60
    m = DURATION_RE.match(text)
    if not m:
        raise ValueError("bad duration: %s" % text)
    hrs = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    return (hrs * 3600) + (mins * 60)


def parse_date(text: str) -> date:
    text = text.strip()
    if text.lower() == "today":
        return date.today()
    if text.lower() == "yesterday":
        return date.today() - timedelta(days=1)
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {text}")


def parse_progress(text: str) -> tuple[int, int | None]:
    """Parse '120', '120/350', or '45-320' style minute counts."""
    text = text.strip()
    if "-" in text and "/" not in text:
        a, b = text.split("-", 1)
        return int(a.strip()), int(b.strip())
    parts = text.split("/")
    cur = int(parts[0].strip())
    total = int(parts[1].strip()) if len(parts) > 1 else None
    return cur, total


def parse_datetime(text: str) -> datetime:
    text = text.strip()
    if "T" in text:
        return datetime.fromisoformat(text)
    return datetime.combine(parse_date(text), datetime.min.time())


def parse_key_value_pairs(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        elif ":" in part:
            k, v = part.split(":", 1)
        else:
            continue
        out[k.strip()] = v.strip()
    return out


def parse_bool(raw: str) -> bool:
    return coerce_bool(raw)


def coerce_int(raw: str, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def parse_key_value(line: str) -> tuple[str, str]:
    if ":" in line:
        k, v = line.split(":", 1)
    elif "=" in line:
        k, v = line.split("=", 1)
    else:
        raise ValueError("expected key:value")
    return k.strip(), v.strip()


def parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;#]+", raw)
    tags = [t.strip().lower() for t in parts if t.strip()]
    return list(dict.fromkeys(tags))


def parse_rating(raw: str) -> float:
    text = raw.strip()
    if "/" in text:
        num, den = text.split("/", 1)
        val = float(num.strip()) / float(den.strip()) * 5.0
    else:
        val = float(text)
    if val < 0 or val > 5:
        raise ValueError("rating must be 0-5")
    return round(val * 2) / 2


def split_csv_line(line: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    in_q = False
    for ch in line:
        if ch == '"':
            in_q = not in_q
            continue
        if ch == "," and not in_q:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf).strip())
    return out


def coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).lower()
    return s in ("1", "true", "yes", "y", "on")


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return "%dm" % minutes
    h, m = divmod(minutes, 60)
    return "%dh %dm" % (h, m)


def format_progress(current: int, total: int | None = None) -> str:
    if total is None:
        return str(current)
    return "%d-%d" % (current, total)


def human_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return "%s and %s" % (items[0], items[1])
    return ", ".join(items[:-1]) + ", and " + items[-1]


def parse_musclegroup_list(raw: str) -> list[str]:
    sep = ";" if ";" in raw else ","
    return [p.strip() for p in raw.split(sep) if p.strip()]


def parse_env_flag(raw: str) -> bool | None:
    s = raw.lower().strip()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off"):
        return False
    return None


def parse_import_format(raw: str) -> str:
    m = {
        "gr": "strong",
        "strong": "strong",
        "csv": "csv",
        "jsonl": "jsonl",
        "hevy": "hevy",
        "fitnotes": "fitnotes",
        "ol": "wger",
    }
    return m.get(raw.lower().strip(), raw.lower())


def parse_int_list(raw: str) -> list[int]:
    s = raw.strip().strip("[]")
    if not s:
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def parse_page_range(raw: str) -> tuple[int, int]:
    if "-" in raw:
        a, b = raw.split("-", 1)
        return int(a.strip()), int(b.strip())
    n = int(raw.strip())
    return n, n


def parse_sort_spec(raw: str) -> tuple[str, bool]:
    asc = not raw.startswith("-")
    field = raw.lstrip("+-")
    return field, asc


def parse_year_range(raw: str) -> tuple[int, int]:
    if "-" in raw:
        a, b = raw.split("-", 1)
        return int(a.strip()), int(b.strip())
    y = int(raw.strip())
    return y, y


def tokenize_query(raw: str) -> list[str]:
    return [t for t in raw.split() if t]
