"""Tests for the committer module."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from memory import Memory
from committer import commit_memory, find_duplicate, main, slugify


def test_slugify():
    assert slugify("Team Meeting", date(2026, 3, 1)) == "2026-03-01-team-meeting.md"


def test_slugify_special_chars():
    assert slugify("Q&A Session!!", date(2026, 3, 1)) == "2026-03-01-q-a-session.md"


def test_slugify_no_title():
    assert slugify(None, date(2026, 3, 1)) == "2026-03-01.md"


def test_find_duplicate(tmp_path: Path):
    mem = Memory(target=date(2026, 3, 1), expires=date(2026, 4, 1),
                 content="Original", title="Standup")
    mem.dump(tmp_path / "existing.md")

    result = find_duplicate(tmp_path, date(2026, 3, 1), "Standup")
    assert result == tmp_path / "existing.md"


def test_find_duplicate_no_match(tmp_path: Path):
    mem = Memory(target=date(2026, 3, 1), expires=date(2026, 4, 1),
                 content="Something", title="Standup")
    mem.dump(tmp_path / "existing.md")

    assert find_duplicate(tmp_path, date(2026, 3, 2), "Standup") is None
    assert find_duplicate(tmp_path, date(2026, 3, 1), "Other") is None


def test_commit_memory_new(tmp_path: Path):
    path = commit_memory(tmp_path, date(2026, 3, 1), date(2026, 4, 1),
                         "Team sync", title="Standup", time="10:00", place="Room A")

    assert path.exists()
    mem = Memory.load(path)
    assert mem.title == "Standup"
    assert mem.content == "Team sync"
    assert mem.time == "10:00"
    assert mem.place == "Room A"


def test_commit_memory_update(tmp_path: Path):
    # Create an existing memory
    original = Memory(target=date(2026, 3, 1), expires=date(2026, 4, 1),
                      content="Old content", title="Standup")
    original.dump(tmp_path / "existing.md")

    # Commit with same target+title should overwrite
    path = commit_memory(tmp_path, date(2026, 3, 1), date(2026, 4, 1),
                         "Updated content", title="Standup")

    assert path == tmp_path / "existing.md"
    mem = Memory.load(path)
    assert mem.content == "Updated content"


@patch("committer.git_commit_and_push")
def test_main_end_to_end(mock_git, tmp_path: Path):
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()

    main([
        "--memories-dir", str(mem_dir),
        "--target", "2026-03-01",
        "--expires", "2026-04-01",
        "--content", "Spring meetup",
        "--title", "Spring",
        "--time", "14:00",
        "--place", "Park",
        "--no-push",
    ])

    files = list(mem_dir.glob("*.md"))
    assert len(files) == 1
    mem = Memory.load(files[0])
    assert mem.title == "Spring"
    assert mem.content == "Spring meetup"
    assert mem.time == "14:00"
    assert mem.place == "Park"
    mock_git.assert_called_once()
