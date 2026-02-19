"""Tests for memory data structures."""

from datetime import date
from pathlib import Path

from memory import Memory


def test_roundtrip(tmp_path: Path):
    """A memory can be saved and loaded back identically."""
    mem = Memory(
        target=date(2026, 3, 15),
        expires=date(2026, 4, 15),
        content="Team standup at 10am.",
        title="Standup",
    )
    path = tmp_path / "standup.md"
    mem.dump(path)
    loaded = Memory.load(path)
    assert loaded == mem


def test_roundtrip_no_title(tmp_path: Path):
    """A memory without a title roundtrips correctly."""
    mem = Memory(
        target=date(2026, 6, 1),
        expires=date(2026, 7, 1),
        content="Summer break starts.",
    )
    path = tmp_path / "summer.md"
    mem.dump(path)
    loaded = Memory.load(path)
    assert loaded == mem


def test_is_expired():
    mem = Memory(
        target=date(2026, 1, 1),
        expires=date(2026, 1, 31),
        content="January event.",
    )
    assert not mem.is_expired(today=date(2026, 1, 15))
    assert not mem.is_expired(today=date(2026, 1, 31))
    assert mem.is_expired(today=date(2026, 2, 1))


def test_file_format(tmp_path: Path):
    """The on-disk format is readable markdown with YAML frontmatter."""
    mem = Memory(
        target=date(2026, 3, 15),
        expires=date(2026, 4, 15),
        content="Meeting notes here.",
        title="Planning",
    )
    path = tmp_path / "planning.md"
    mem.dump(path)
    raw = path.read_text()
    assert raw.startswith("---\n")
    assert "target: '2026-03-15'" in raw or "target: 2026-03-15" in raw
    assert "Meeting notes here." in raw
