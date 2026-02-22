"""Tests for the committer module's Firestore path."""

from datetime import date
from unittest.mock import patch, MagicMock

from memory import Memory
from committer import main


@patch("firestore_storage.delete_expired")
@patch("firestore_storage.save_memory")
@patch("firestore_storage.load_memories")
@patch("committer.call_ai")
def test_main_firestore_create(mock_call_ai, mock_load, mock_save, mock_delete):
    mock_load.return_value = []
    mock_save.return_value = "new-doc-id"
    mock_delete.return_value = []

    mock_call_ai.return_value = {
        "action": "create",
        "target": "2026-03-05",
        "expires": "2026-04-04",
        "title": "Team Meeting",
        "time": "10:00",
        "place": "Room A",
        "content": "Weekly planning session",
    }

    main([
        "--message", "Team meeting next Thursday at 10am in Room A",
        "--today", "2026-02-18",
        "--firestore",
    ])

    mock_load.assert_called_once_with("cambridge-lexington", date(2026, 2, 18))
    mock_save.assert_called_once()
    saved_mem = mock_save.call_args[0][0]
    assert saved_mem.title == "Team Meeting"
    assert saved_mem.time == "10:00"
    assert mock_save.call_args[1]["doc_id"] is None


@patch("firestore_storage.delete_expired")
@patch("firestore_storage.save_memory")
@patch("firestore_storage.find_memory_by_title")
@patch("firestore_storage.load_memories")
@patch("committer.call_ai")
def test_main_firestore_update(mock_call_ai, mock_load, mock_find, mock_save, mock_delete):
    existing = Memory(
        target=date(2026, 3, 5), expires=date(2026, 4, 4),
        content="Old content", title="Team Meeting", user_id="alice",
    )
    mock_load.return_value = [("doc-123", existing)]
    mock_find.return_value = ("doc-123", existing)
    mock_save.return_value = "doc-123"
    mock_delete.return_value = []

    mock_call_ai.return_value = {
        "action": "update",
        "update_title": "Team Meeting",
        "target": "2026-03-05",
        "expires": "2026-04-04",
        "title": "Team Meeting",
        "time": "11:00",
        "place": "Room B",
        "content": "Updated: moved to 11am",
    }

    main([
        "--message", "Move team meeting to 11am",
        "--user-id", "alice",
        "--today", "2026-02-18",
        "--firestore",
    ])

    mock_save.assert_called_once()
    assert mock_save.call_args[1]["doc_id"] == "doc-123"
