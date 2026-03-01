"""Tests for the committer module's Firestore path."""

from datetime import date
from unittest.mock import patch, MagicMock

from memory import Memory
from committer import commit_memory_firestore, main


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
    ])

    mock_save.assert_called_once()
    assert mock_save.call_args[1]["doc_id"] == "doc-123"


LONG_CHINESE_MESSAGE = (
    "温馨提醒,\n亲爱的弟兄姊妹们，\n\n"
    "要来周六3/7波士顿区的众圣徒在⭐️牛顿会所，\n"
    "50 Dudley Rd, Newton\n"
    "有现场实体聚会。且先有爱筵相调！\n"
    "12:00 PM 爱筵(potluck)⭐️\n\n"
    "⭐️此次，James Lee弟兄会亲自来现场给我们成全，除了\n"
    "1:00-3:00，成全训练，\n还有\n"
    "3:30-5:00，对在职圣徒特别负担的交通（欢迎提问，事先收集）\n\n"
    "⭐️我们将会进入\u201c主恢复的道路\u201d第九篇 召会的建造，鼓励圣徒们先进入。\n\n"
    "⭐️欢迎把儿童带来，一同蒙恩！\n\n"
    "鼓励圣徒参加现场实体聚会得最大益处！\n\n"
    "Zoom Meeting\nMeeting ID: 233 069 6236\nPasscode: 1234567"
)


@patch("firestore_storage.delete_expired")
@patch("firestore_storage.save_memory")
@patch("firestore_storage.load_memories_by_page")
@patch("committer.call_ai")
def test_commit_long_chinese_message(mock_call_ai, mock_load, mock_save, mock_delete):
    """Ensure commit_memory_firestore handles long Chinese messages with emojis."""
    mock_load.return_value = []
    mock_save.return_value = "new-doc-id"
    mock_delete.return_value = []

    mock_call_ai.return_value = {
        "action": "create",
        "target": "2026-03-07",
        "expires": "2026-04-06",
        "title": "波士顿聚会",
        "time": "12:00",
        "place": "50 Dudley Rd, Newton",
        "content": "成全训练与爱筵相调",
        "attachments": None,
    }

    result = commit_memory_firestore(
        message=LONG_CHINESE_MESSAGE,
        user_id="owner-uid",
        today=date(2026, 3, 1),
        page_id="cambridge-lexington",
    )

    assert result.action == "create"
    assert result.doc_id == "new-doc-id"
    assert result.memory.place == "50 Dudley Rd, Newton"
    assert result.memory.page_id == "cambridge-lexington"

    # Verify the prompt sent to AI contains the full message
    prompt = mock_call_ai.call_args[0][0]
    assert "⭐️" in prompt
    assert "James Lee" in prompt
    assert "50 Dudley Rd" in prompt
