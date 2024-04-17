"""Field-level validators used across the domain layer."""

from __future__ import annotations

import re
from datetime import date

from liftlog.errors import ValidationError
from liftlog import wger as wger_mod

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_non_empty(value: str, field: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValidationError("must not be empty", field=field)
    return v


def validate_slug(slug: str) -> str:
    s = slug.strip().lower().replace(" ", "-")
    if not SLUG_RE.match(s):
        raise ValidationError("invalid slug format", field="slug")
    return s


def validate_load(value: float, total: float | None = None) -> None:
    if value < 0:
        raise ValidationError("load cannot be negative", field="best_1rm")
    if total is not None and total < 0:
        raise ValidationError("target cannot be negative", field="target_1rm")


def validate_year(y: int | None) -> int | None:
    if y is None:
        return None
    if y < 1000 or y > date.today().year + 2:
        raise ValidationError("year out of range", field="year")
    return y


def validate_wger(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    if not wger_mod.validate_wger(str(raw)):
        raise ValidationError("invalid WGER", field="wger")
    try:
        return wger_mod.normalize_wger(str(raw))
    except ValueError as exc:
        raise ValidationError("invalid WGER", field="wger") from exc


def validate_wger_field(raw: str | None) -> str | None:
    if raw is None or not str(raw).strip():
        return None
    norm = validate_wger(raw)
    if norm is None:
        raise ValidationError("invalid WGER", field="wger")
    return norm.replace("-", "")


def validate_rating(val: float) -> float:
    if val < 0.0 or val > 5.0:
        raise ValidationError("rating must be between 0 and 5", field="rating")
    return float(val)


def validate_rating_value(val: float) -> float:
    v = validate_rating(float(val))
    return round(v, 2)


def validate_email(addr: str | None) -> str | None:
    if not addr:
        return None
    a = addr.strip()
    if not EMAIL_RE.match(a):
        raise ValidationError("bad email", field="email")
    return a


def validate_progress(pct: float) -> float:
    if pct < 0.0 or pct > 100.0:
        raise ValidationError("progress must be 0-100", field="progress")
    return round(pct, 2)


def validate_id_list(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in ids:
        i = require_non_empty(raw, "id")
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def validate_dict_keys(data: dict, required: list[str]) -> None:
    missing = [k for k in required if k not in data]
    if missing:
        raise ValidationError("missing keys: %s" % ", ".join(missing), field="dict")


def clamp_int(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(val)))


def chk_id(val: str, field: str = "id") -> str:
    v = require_non_empty(val, field)
    if len(v) > 64:
        raise ValidationError("id too long", field=field)
    return v


def validate_url(url: str) -> str:
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise ValidationError("bad url", field="url")
    return u


def validate_language(lang: str | None) -> str:
    if not lang:
        return "en"
    return require_non_empty(lang, "language")[:8]


def validate_hex_color(color: str) -> str:
    c = color.strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
        raise ValidationError("bad color", field="color")
    return c.lower()


def validate_positive_int(val: int, field: str) -> int:
    if val <= 0:
        raise ValidationError("must be positive", field=field)
    return val


def validate_status(status: str, allowed: list[str]) -> str:
    s = status.strip().lower()
    if s not in allowed:
        raise ValidationError("bad status", field="status")
    return s


def validate_percent(val: float) -> float:
    return validate_progress(float(val))


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\\\|?*]', "_", name.strip()) or "file"


def validate_exercise_payload(data: dict) -> dict:
    out = dict(data)
    out["name"] = require_non_empty(str(out.get("name", "")), "name")
    if out.get("category"):
        out["category"] = str(out["category"]).strip()[:32]
    return out


def validate_workset_payload(data: dict) -> None:
    require_non_empty(str(data.get("exercise_id", "")), "exercise_id")
    validate_load(float(data.get("weight", 0)))


def validate_goal_target(target: int, kind: str) -> int:
    return validate_positive_int(int(target), kind)


def merge_errors(errs: list[ValidationError]) -> str:
    return "; ".join(str(e) for e in errs)


def soft_validate_slug(text: str) -> str:
    s = text.strip().lower().replace(" ", "-")
    try:
        return validate_slug(s)
    except ValidationError:
        return re.sub(r"[^a-z0-9_-]", "", s) or "tag"
