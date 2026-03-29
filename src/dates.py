"""Timezone-aware date helpers."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("UTC")


def today(tz: ZoneInfo | None = None) -> date:
    """Return today's date in *tz* (default: UTC)."""
    return datetime.now(tz or DEFAULT_TZ).date()
