"""wger exercise-id parsing and validation.

`wger <https://wger.de>`_ is an open-source workout manager with a public
exercise database; every movement has a small positive integer id. We use that
id to pull canonical names/equipment for an exercise. Ids are 1-6 digits.
"""

from __future__ import annotations

import re

_SEP = re.compile(r"[\s\-#]")
MAX_LEN = 6


def _digits(raw: str) -> str:
    return _SEP.sub("", (raw or "").strip())


def is_wger(value: str) -> bool:
    d = _digits(str(value))
    return d.isdigit() and 1 <= len(d) <= MAX_LEN and int(d) > 0


def validate_wger(value: str) -> bool:
    if not value or not str(value).strip():
        return False
    return is_wger(value)


def normalize_wger(value: str) -> str:
    d = _digits(str(value))
    if not (d.isdigit() and 1 <= len(d) <= MAX_LEN and int(d) > 0):
        raise ValueError("not a valid wger id: %r" % value)
    return str(int(d))  # strip leading zeros


def normalize(raw: str) -> str | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return normalize_wger(raw)
    except ValueError:
        return None


def parse(raw: str) -> str | None:
    return normalize(raw)


def wger_url(value: str) -> str | None:
    n = normalize(value)
    if n is None:
        return None
    return "https://wger.de/en/exercise/%s/view/" % n


def format_display(value: str) -> str:
    n = normalize(value)
    return ("wger #%s" % n) if n else value


def guess_wger(text: str) -> str | None:
    for token in re.findall(r"(?:wger[#\s:]*)?(\d{1,6})", text or ""):
        if validate_wger(token):
            return normalize_wger(token)
    return None


def clean_id_list(raw: str) -> list[str]:
    out: list[str] = []
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.append(normalize_wger(p))
        except ValueError:
            continue
    return out


def batch_validate(values: list[str]) -> dict[str, bool]:
    return {v: validate_wger(v) for v in values}


def compare_wger(a: str, b: str) -> bool:
    na, nb = normalize(a), normalize(b)
    if na is None or nb is None:
        return False
    return na == nb


def explain(value: str) -> str:
    if not value or not str(value).strip():
        return "empty id"
    if not validate_wger(value):
        return "invalid wger id"
    return "valid wger id -> %s" % normalize_wger(value)


# aliases some callers reach for
validate = validate_wger
is_valid = validate_wger
format_wger = format_display
clean = _digits
