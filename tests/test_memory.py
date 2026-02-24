"""Tests for memory data structures."""

from datetime import date

from memory import Memory, _next_sunday


def test_is_expired():
    mem = Memory(
        target=date(2026, 1, 1),
        expires=date(2026, 1, 31),
        content="January event.",
    )
    assert not mem.is_expired(today=date(2026, 1, 15))
    assert not mem.is_expired(today=date(2026, 1, 31))
    assert mem.is_expired(today=date(2026, 2, 1))


def test_is_expired_ongoing():
    """Ongoing memories still expire based on their expires date."""
    mem = Memory(
        target=None,
        expires=date(2026, 2, 22),
        content="Weekly event.",
    )
    assert not mem.is_expired(today=date(2026, 2, 18))
    assert not mem.is_expired(today=date(2026, 2, 22))
    assert mem.is_expired(today=date(2026, 2, 23))


def test_to_dict():
    mem = Memory(
        target=date(2026, 3, 15),
        expires=date(2026, 4, 15),
        content="Team standup at 10am.",
        title="Standup",
        time="10:00",
        place="Room A",
        user_id="alice",
    )
    d = mem.to_dict()
    assert d["target"] == "2026-03-15"
    assert d["expires"] == "2026-04-15"
    assert d["content"] == "Team standup at 10am."
    assert d["title"] == "Standup"
    assert d["time"] == "10:00"
    assert d["place"] == "Room A"
    assert d["user_id"] == "alice"
    assert d["attachments"] is None


def test_to_dict_ongoing():
    mem = Memory(target=None, expires=date(2026, 2, 22), content="Weekly.")
    d = mem.to_dict()
    assert d["target"] is None


def test_from_dict():
    d = {
        "target": "2026-03-15",
        "expires": "2026-04-15",
        "content": "Team standup.",
        "title": "Standup",
        "time": "10:00",
        "place": "Room A",
        "user_id": "alice",
        "attachments": ["https://example.com/a.pdf"],
    }
    mem = Memory.from_dict(d)
    assert mem.target == date(2026, 3, 15)
    assert mem.expires == date(2026, 4, 15)
    assert mem.title == "Standup"
    assert mem.user_id == "alice"
    assert mem.attachments == ["https://example.com/a.pdf"]


def test_to_dict_from_dict_roundtrip():
    mem = Memory(
        target=date(2026, 3, 15),
        expires=date(2026, 4, 15),
        content="Event.",
        title="Roundtrip",
        time="14:00",
        place="Park",
        attachments=["https://example.com/x.png"],
        user_id="bob",
    )
    restored = Memory.from_dict(mem.to_dict())
    assert restored == mem


def test_from_dict_defaults():
    d = {"expires": "2026-04-15", "content": "Minimal."}
    mem = Memory.from_dict(d)
    assert mem.target is None
    assert mem.user_id == "cambridge-lexington"
    assert mem.title is None
    assert mem.attachments is None


def test_next_sunday():
    # Wednesday 2026-02-18 → Sunday 2026-02-22
    assert _next_sunday(date(2026, 2, 18)) == date(2026, 2, 22)
    # Sunday stays on Sunday
    assert _next_sunday(date(2026, 2, 22)) == date(2026, 2, 22)
    # Monday → next Sunday
    assert _next_sunday(date(2026, 2, 16)) == date(2026, 2, 22)
