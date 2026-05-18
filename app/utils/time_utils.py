from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_est_label() -> str:
    est = datetime.now(ZoneInfo("America/New_York"))
    return est.strftime("%H:%M:%S EST")


def parse_percent(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text.endswith("%"):
        return float(text[:-1])
    return float(text)
