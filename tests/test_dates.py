"""Tests for timezone-aware date helpers."""

from datetime import date, datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from dates import today, DEFAULT_TZ


def test_today_returns_date():
    """today() returns a date object."""
    result = today()
    assert isinstance(result, date)


def test_today_uses_utc_by_default():
    """today() uses UTC when no tz is passed."""
    fake_utc = datetime(2026, 3, 4, 0, 30, tzinfo=timezone.utc)
    with patch("dates.datetime") as mock_dt:
        mock_dt.now.return_value = fake_utc
        result = today()
    assert result == date(2026, 3, 4)


def test_default_tz_is_utc():
    """DEFAULT_TZ should be UTC."""
    assert DEFAULT_TZ == ZoneInfo("UTC")


def test_today_accepts_explicit_timezone():
    """today(tz=...) uses the given timezone."""
    eastern = ZoneInfo("America/New_York")
    fake_utc = datetime(2026, 3, 4, 0, 30, tzinfo=timezone.utc)
    eastern_time = fake_utc.astimezone(eastern)
    with patch("dates.datetime") as mock_dt:
        mock_dt.now.return_value = eastern_time
        result = today(tz=eastern)
    assert result == date(2026, 3, 3)
